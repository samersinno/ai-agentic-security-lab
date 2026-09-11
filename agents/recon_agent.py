import anthropic, os, sys

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "..", "recon-scripts"))
from nmap_wrapper import run_nmap

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

target = "127.0.0.1"
scan_output = run_nmap(target)

print("=== Raw nmap output ===")
print(scan_output)

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=800,
    system="You are a security analyst assistant. Summarize nmap scan results in plain English for a non-technical stakeholder. For each open port, briefly note what the service is and whether the version looks outdated or potentially risky, without providing exploit details.",
    messages=[{"role": "user", "content": f"Summarize this nmap scan:\n\n{scan_output}"}],
)

print("\n=== Agent summary ===")
print(response.content[0].text)
