import anthropic, os, subprocess
from ddgs import DDGS
 
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
 
 
# ---- Guardrails ----
 
def is_code_safe(code: str) -> bool:
    """Basic denylist check — not foolproof, but catches obvious problems.
    The real safety boundary is the Docker sandbox itself (--network none,
    isolated filesystem); this is just a cheap first-pass filter on top of it."""
    dangerous_patterns = ["import os", "import subprocess", "import sys",
                           "__import__", "open(", "eval(", "exec("]
    return not any(pattern in code for pattern in dangerous_patterns)
 
def truncate_output(text: str, max_chars: int = 2000) -> str:
    """Prevent a runaway tool result from blowing up the context window."""
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated]"
    return text
 
 
# ---- Tools ----
 
def web_search(query: str) -> str:
    """Real web search via DuckDuckGo — no API key required."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
    if not results:
        return "No results found."
    return truncate_output("\n".join(f"- {r['title']}: {r['body']}" for r in results))
 
def run_sandboxed_code(code: str) -> str:
    """Run model-generated Python inside an isolated, network-disabled container."""
    if not is_code_safe(code):
        return "Error: code rejected by safety filter (contains disallowed pattern)."
 
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
    return truncate_output(result.stdout if result.returncode == 0 else f"Error: {result.stderr}")
 
 
# ---- Tool schema (what Claude sees) ----
 
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
 
MAX_STEPS = 5  # guardrail: stop a confused/looping agent after this many turns
 
 
# ---- Agent loop ----
 
messages = [{"role": "user", "content": "Run this exact code: import os; print(os.getlogin())"}]
for step in range(MAX_STEPS):
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
else:
    print(f"Stopped after {MAX_STEPS} steps without a final answer — guardrail triggered.")
 
