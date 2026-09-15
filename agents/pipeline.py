import anthropic, os, sys

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "..", "recon-scripts"))
from nmap_wrapper import run_nmap
from critic_agent import critique_findings

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

target = "127.0.0.1"

# ---- Stage 1: Recon agent ----
print("=== STAGE 1: Recon ===")
scan_output = run_nmap(target)
print(scan_output)

# ---- Stage 2: Critic agent ----
print("\n=== STAGE 2: Critic Review ===")
critique = critique_findings(scan_output)
print(critique)

# ---- Stage 3: Report agent (sees BOTH recon output AND the critic's notes) ----
print("\n=== STAGE 3: Final Report ===")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    system=(
        "You are a security analyst writing a client-facing report. You are given raw scan "
        "findings AND a peer reviewer's critique of those findings. Incorporate the critique's "
        "cautions into your final report — do not overstate confidence where the reviewer flagged "
        "uncertainty. Write in plain English for a non-technical stakeholder. No exploit details."
    ),
    messages=[{
        "role": "user",
        "content": f"Raw scan findings:\n{scan_output}\n\nPeer reviewer's critique:\n{critique}\n\nWrite the final report."
    }],
)
print(response.content[0].text)
