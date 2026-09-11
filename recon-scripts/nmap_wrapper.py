import subprocess

def run_nmap(target: str) -> str:
    """Read-only, safe-flags-only nmap scan. No aggressive/exploit scripts."""
    result = subprocess.run(
        ["nmap", "-sV", "--top-ports", "100", target],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout
