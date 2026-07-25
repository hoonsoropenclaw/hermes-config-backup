#!/usr/bin/env python3
"""
HR Document Automation — Python wrapper for DOCX generation.
Detects available DOCX pipeline (dotnet OpenXML or minimax-docx CLI),
falls back gracefully.
"""
import subprocess, sys, os, shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
MINIMAX_DOCX_DIR = os.path.expanduser("~/.hermes/skills/minimax-docx")

def find_dotnet():
    """Check if dotnet is available for OpenXML generation."""
    for cmd in ["dotnet", "/usr/bin/dotnet", "/usr/local/bin/dotnet"]:
        if shutil.which(cmd):
            return cmd
    return None

def check_minimax_docx():
    """Check if minimax-docx setup.sh has been run."""
    env_check = os.path.join(MINIMAX_DOCX_DIR, "scripts", "env_check.sh")
    if not os.path.exists(env_check):
        return False
    r = subprocess.run(["bash", env_check], capture_output=True, text=True)
    return r.returncode == 0

def run_dotnet_offer(candidate, position, salary, start_date, school, output):
    dotnet = find_dotnet()
    if not dotnet:
        return False, "dotnet not found"
    cs_path = os.path.join(SCRIPT_DIR, "generate_offer_letter.cs")
    if not os.path.exists(cs_path):
        return False, f"C# script not found: {cs_path}"
    try:
        r = subprocess.run(
            [dotnet, "script", cs_path, candidate, position, salary, start_date, school, output],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            return True, r.stdout.strip()
        else:
            return False, r.stderr.strip()
    except Exception as e:
        return False, str(e)

def run_dotnet_contract(candidate, subject, hourly_rate, sub_reason, period, school, output):
    dotnet = find_dotnet()
    if not dotnet:
        return False, "dotnet not found"
    cs_path = os.path.join(SCRIPT_DIR, "generate_contract_substitute.cs")
    if not os.path.exists(cs_path):
        return False, f"C# script not found: {cs_path}"
    try:
        r = subprocess.run(
            [dotnet, "script", cs_path, candidate, subject, hourly_rate, sub_reason, period, school, output],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            return True, r.stdout.strip()
        else:
            return False, r.stderr.strip()
    except Exception as e:
        return False, str(e)

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_docs.py offer <name> <position> <salary> <start_date> <school> [output]")
        print("       generate_docs.py contract <name> <subject> <hourly_rate> <sub_reason> <period> <school> [output]")
        print("       generate_docs.py check")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "check":
        dotnet_ok = find_dotnet() is not None
        minimax_ok = check_minimax_docx()
        print(f"dotnet OpenXML:   {'✅' if dotnet_ok else '❌ (install dotnet-sdk)'}")
        print(f"minimax-docx CLI: {'✅' if minimax_ok else '❌ (run minimax-docx/setup.sh first)'}")
        sys.exit(0 if (dotnet_ok or minimax_ok) else 1)

    if cmd == "offer":
        if len(sys.argv) < 7:
            print("Error: offer requires <name> <position> <salary> <start_date> <school> [output]", file=sys.stderr)
            sys.exit(1)
        name, position, salary, start_date, school = sys.argv[2:7]
        output = sys.argv[7] if len(sys.argv) > 7 else f"/tmp/offer_letter_{name.replace(' ', '_')}.docx"
        ok, msg = run_dotnet_offer(name, position, salary, start_date, school, output)
        if ok:
            print(f"✅ {msg}")
        else:
            print(f"❌ dotnet path failed ({msg}), checking minimax-docx fallback...", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if cmd == "contract":
        if len(sys.argv) < 8:
            print("Error: contract requires <name> <subject> <hourly_rate> <sub_reason> <period> <school> [output]", file=sys.stderr)
            sys.exit(1)
        name, subject, hourly_rate, sub_reason, period, school = sys.argv[2:8]
        output = sys.argv[8] if len(sys.argv) > 8 else f"/tmp/contract_{name.replace(' ', '_')}.docx"
        ok, msg = run_dotnet_contract(name, subject, hourly_rate, sub_reason, period, school, output)
        if ok:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
