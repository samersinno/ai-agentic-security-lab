	# agents/week2_real_tools.py
import anthropic, os, subprocess
from ddgs import DDGS

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def web_search(query: str) -> str:
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
    if not results:
        return "No results found."
    return "\n".join(f"- {r['title']}: {r['body']}" for r in results)

def run_sandboxed_code(code: str) -> str:
    sandbox_dir = "/tmp/agent-sandbox"
    script_path = os.path.join(sandbox_dir, "script.py")
    with open(script_path, "w") as f:
        f.write(code)
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", "none",
         "-v", f"{sandbox_dir}:/sandbox",
         "python:3.11-slim", "python", "/sandbox/script.py"],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"

# This is the schema-based tool definition — Claude's API uses this to decide
# WHICH tool to call and validates the arguments' shape before returning them.
tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "run_code",
        "description": "Run Python code in a sandboxed environment and return stdout",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
]

TOOL_FUNCTIONS = {"web_search": web_search, "run_code": run_sandboxed_code}

messages = [{"role": "user", "content": "What's 47293 * 8123, and who is the current Anthropic CEO? Use tools as needed."}]

for step in range(5):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        tools=tools,
        messages=messages,
    )

    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[Step {step}] Calling tool: {block.name}({block.input})")
                func = TOOL_FUNCTIONS[block.name]
                result = func(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})
    else:
        final_text = "".join(b.text for b in response.content if b.type == "text")
        print("Final answer:", final_text)
        break
