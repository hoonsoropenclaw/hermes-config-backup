import subprocess
import datetime
import json
import os

TELEMETRY_PATH = "/home/hoonsoropenclaw/.hermes/telemetry_report_latest.md"

def get_hermes_status():
    try:
        res = subprocess.run(["/home/hoonsoropenclaw/.local/bin/hermes", "status"], capture_output=True, text=True)
        return res.stdout
    except Exception as e:
        return f"Error getting status: {e}"

def get_hermes_sessions():
    try:
        res = subprocess.run(["/home/hoonsoropenclaw/.local/bin/hermes", "sessions", "list"], capture_output=True, text=True)
        return res.stdout
    except Exception as e:
        return f"Error getting sessions: {e}"

def generate_report():
    timestamp = datetime.datetime.now().isoformat()
    status = get_hermes_status()
    sessions = get_hermes_sessions()
    
    report = f"""# 📡 Raphael (N100) Telemetry Report
**Generated At**: {timestamp}

## 📊 System Status
```text
{status}
```

## 🧠 Recent Learning Sessions & Activities
```text
{sessions}
```
"""
    
    with open(TELEMETRY_PATH, "w") as f:
        f.write(report)
    print(f"Telemetry report generated at {TELEMETRY_PATH}")

if __name__ == "__main__":
    generate_report()
