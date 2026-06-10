#!/usr/bin/env python3
"""
sync_evaluations.py
每天自動檢查評價網站的新評價，下載並寫入長期記憶（MM mémoire）
"""

import urllib.request, json, datetime, sys, re, subprocess
from pathlib import Path

LOG_FILE = Path("/home/hoonsoropenclaw/sync_evaluations.log")
MEMORY_FILE = Path("/home/hoonsoropenclaw/.hermes/memories/EVALUATIONS_MEMORY.md")
HERMES_ENV = Path("/home/hoonsoropenclaw/.hermes/.env")
PORTAL_ENV = Path("/home/hoonsoropenclaw/permanent-projects/hermes-portal/.env.local")

# Use the stable alias (auto-points to current production deployment)
# 2026-06-06: switched from akqkd6vpj hash URL after forced rebuild
API_URL = "https://hermes-portal.vercel.app/api/evaluations/sync"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_api_key():
    """Read AGENT_API_KEY from portal .env.local (primary) or hermes .env (fallback)"""
    for env_path in [PORTAL_ENV, HERMES_ENV]:
        if not env_path.exists():
            continue
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                # Handle both real keys (AGENT_API_KEY=sk-xxx) and masked keys (AGENT_API_KEY=***)
                if line.startswith("AGENT_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key and key != "***":  # Skip redaction markers
                        return key
    return None

def load_last_sync():
    """Load last synced evaluation ID from memory file"""
    if not MEMORY_FILE.exists():
        return None
    with open(MEMORY_FILE) as f:
        content = f.read()
    m = re.search(r'last_synced_id:\s*([^\s\n]+)', content)
    return m.group(1) if m else None

def save_last_sync(eval_id):
    """Append new evaluations to memory and update last_synced_id"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE) as f:
            existing = f.read()
    else:
        existing = "# 評價回饋長期記憶\n\n"
    
    # Update last_synced_id marker
    if "last_synced_id:" in existing:
        existing = re.sub(r'last_synced_id:\s*[^\s\n]+', f'last_synced_id: {eval_id}', existing)
    else:
        existing = f"<!-- last_synced_id: {eval_id} -->\n" + existing
    
    with open(MEMORY_FILE, "w") as f:
        f.write(existing)

def append_evaluation(eval_data):
    """Append a single evaluation to EVALUATIONS_MEMORY.md"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"""

## 評價記錄 [{eval_data['id']}] - {eval_data.get('work_title', 'Unknown')}

- **時間**: {ts}
- **作品**: [{eval_data.get('work_title', 'Unknown')}](https://hermes-portal.vercel.app/work.html?id={eval_data['work_id']})
- **設計感**: {eval_data.get('score_design', '?')}/10
- **實用性**: {eval_data.get('score_practical', '?')}/10
- **直覺性**: {eval_data.get('score_intuitive', '?')}/10
- **平均**: {round(sum(filter(None, [eval_data.get('score_design'), eval_data.get('score_practical'), eval_data.get('score_intuitive')])), 1) if eval_data.get('score_design') else '?'}/10
"""
    feedback = eval_data.get('feedback')
    if feedback:
        entry += f"- **回饋**: {feedback}\n"
    
    with open(MEMORY_FILE, "a") as f:
        f.write(entry)
    
    # Also write a structured analysis entry for the AI to reason about
    analysis_file = Path("/home/hoonsoropenclaw/.hermes/memories/EVAL_ANALYSIS.json")
    if analysis_file.exists():
        with open(analysis_file) as f:
            analysis = json.load(f)
    else:
        analysis = {"evaluations": [], "insights": []}
    
    analysis["evaluations"].append({
        "id": eval_data["id"],
        "work_id": eval_data["work_id"],
        "work_title": eval_data.get("work_title", ""),
        "scores": {
            "design": eval_data.get("score_design"),
            "practical": eval_data.get("score_practical"),
            "intuitive": eval_data.get("score_intuitive"),
        },
        "feedback": feedback,
        "timestamp": eval_data.get("created_at", ""),
    })
    
    with open(analysis_file, "w") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

def main():
    log("===== 評價同步開始 =====")
    
    api_key = get_api_key()
    if not api_key:
        log("ERROR: AGENT_API_KEY not found in portal .env.local or ~/.hermes/.env")
        sys.exit(1)
    
    # Fetch all evaluations
    req = urllib.request.Request(
        API_URL,
        headers={"X-Agent-Key": api_key},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        log(f"ERROR: failed to fetch evaluations: {e}")
        sys.exit(1)
    
    evals = result.get("data", {}).get("evaluations", [])
    log(f"取得 {len(evals)} 筆評價")
    
    if not evals:
        log("沒有新評價")
        log("===== 評價同步完成 =====\n")
        return
    
    last_synced = load_last_sync()
    new_evals = []
    
    for ev in evals:
        if last_synced is None or ev["id"] != last_synced:
            new_evals.append(ev)
        else:
            break  # already synced
    
    if not new_evals:
        log("沒有新評價")
        log("===== 評價同步完成 =====\n")
        return
    
    log(f"發現 {len(new_evals)} 筆新評價")
    
    for ev in reversed(new_evals):  # oldest first
        append_evaluation(ev)
        log(f"  新評價: [{ev['id'][:8]}] {ev.get('work_title','?')} "
            f"設計={ev.get('score_design')} 實用={ev.get('score_practical')} 直覺={ev.get('score_intuitive')}")
    
    # Update last synced
    save_last_sync(evals[0]["id"])
    
    log("===== 評價同步完成 =====\n")

if __name__ == "__main__":
    main()