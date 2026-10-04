#!/usr/bin/env bash
# Hermes no-agent 看門狗：只有出問題時才輸出（空輸出 = 不通知）。
# 由 install-hermes.sh 複製到 ~/.hermes/scripts/raphael-watchdog.sh 後排程（Hermes 只接受該目錄下的腳本）。
cd "/home/hoonsoropenclaw/raphael-harness" || exit 0
[ -f .venv/bin/activate ] && source .venv/bin/activate
python - <<'PY'
import json, shutil, subprocess, sys
r = json.loads(subprocess.run([sys.executable, "-m", "harness", "run", "status"], capture_output=True, text=True).stdout)
lock = r.get("lock", {})
if lock.get("locked") and lock.get("stale"):
    print(f"⚠️ 拉斐爾學習流程疑似卡住：run {lock.get('run_id')}，{lock.get('heartbeat_age_min')} 分鐘無心跳（最後在做：{lock.get('note','?')}）。下次排程會自動接手。")
du = shutil.disk_usage("/")
if du.free / du.total < 0.10:
    print(f"⚠️ N100 磁碟剩 {du.free / 2**30:.1f} GB（{du.free / du.total:.0%}），請清理，否則備份與排程會失敗。")
PY
