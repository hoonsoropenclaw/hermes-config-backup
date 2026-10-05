#!/usr/bin/env bash
# Hermes no-agent 看門狗：只有出問題時才輸出（空輸出 = 不通知）。
# 由 install-hermes.sh 複製到 ~/.hermes/scripts/raphael-watchdog.sh 後排程（Hermes 只接受該目錄下的腳本）。
# 同一個問題只通知一次（記在 state/watchdog.json），避免每 30 分鐘重複洗版。
cd "/home/hoonsoropenclaw/raphael-harness" || exit 0
[ -f .venv/bin/activate ] && source .venv/bin/activate
python - <<'PY'
import json, shutil, subprocess, sys
from pathlib import Path
seen_path = Path("state/watchdog.json")
try:
    seen = json.loads(seen_path.read_text(encoding="utf-8"))
except Exception:
    seen = {}
msgs, now_keys = [], {}
r = json.loads(subprocess.run([sys.executable, "-m", "harness", "run", "status"], capture_output=True, text=True).stdout)
lock = r.get("lock", {})
if lock.get("locked") and lock.get("stale"):
    key = f"stale:{lock.get('run_id')}:{lock.get('heartbeat')}"
    now_keys["stale"] = key
    if seen.get("stale") != key:
        msgs.append(f"⚠️ 拉斐爾學習流程中斷：run {lock.get('run_id')} 停在「{lock.get('note','?')}」之後"
                    f"（{lock.get('heartbeat_age_min')} 分鐘無心跳）。下一次排程會自動從斷點接續。")
du = shutil.disk_usage("/")
if du.free / du.total < 0.10:
    now_keys["disk"] = "low"
    if seen.get("disk") != "low":
        msgs.append(f"⚠️ N100 磁碟剩 {du.free / 2**30:.1f} GB（{du.free / du.total:.0%}），請清理，否則備份與排程會失敗。")
if msgs:
    print("\n".join(msgs))
seen_path.parent.mkdir(parents=True, exist_ok=True)
seen_path.write_text(json.dumps(now_keys), encoding="utf-8")
PY
