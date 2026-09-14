import anthropic, os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

with open("../recon-scripts/injection_test.html") as f:
    page_content = f.read()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=300,
    system="You summarize webpage content in one sentence for a user.",
    messages=[{"role": "user", "content": f"Summarize this webpage:\n\n{page_content}"}],
)

print(response.content[0].text)
