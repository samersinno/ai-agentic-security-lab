import anthropic, os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def critique_findings(recon_output: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=(
            "You are a skeptical senior security reviewer. You are given raw nmap scan output. "
            "Your job is NOT to summarize it — it's to critique it. Specifically:\n"
            "- Flag anything that might be a false positive or needs manual verification\n"
            "- Note any services where the version info is missing/incomplete and shouldn't be assumed safe\n"
            "- Point out anything a junior analyst might over-claim or under-claim as risk\n"
            "- Do NOT provide exploit details or attack instructions\n"
            "Be concise and specific — bullet points, not prose."
        ),
        messages=[{"role": "user", "content": f"Review this raw scan output critically:\n\n{recon_output}"}],
    )
    return response.content[0].text
