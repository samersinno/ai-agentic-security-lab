import anthropic, os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def fake_tool(query: str) -> str:
    """Pretend tool — in reality you'd call an API or run code."""
    return f"[fake result for: {query}]"

messages = [{"role": "user", "content": "What's the weather in Zurich? Use the tool if you need to."}]

for step in range(5):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system="If you need current info, respond ONLY with: TOOL_CALL: <query>. Otherwise answer directly.",
        messages=messages,
    )
    text = response.content[0].text
    print(f"[Step {step}] Model said: {text}")

    if text.startswith("TOOL_CALL:"):
        query = text.replace("TOOL_CALL:", "").strip()
        result = fake_tool(query)
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": f"Tool result: {result}"})
    else:
        print("Final answer:", text)
        break
