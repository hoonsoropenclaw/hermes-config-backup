#!/usr/bin/env bash
# run-linux-ops-monitor.sh — cron / systemmd timer 用的薄殼 wrapper
# 用途：每 5 分鐘跑一次 linux_ops_monitor.py，告警只進 log（不在 stdout spam）
#
# 推薦安裝：
#   1) cron：把下面這行加到 `crontab -e`
#      */5 * * * * /home/hoonsoropenclaw/.hermes/scripts/run-linux-ops-monitor.sh
#
#   2) 或 systemd timer：建立 ~/.config/systemd/user/linux-ops-monitor.timer
#
# 設計：
#   - 退出碼反映 severity（0/1/2/3）
#   - 只在 WARN/CRITICAL 時輸出（不刷無聊的 OK）
#   - 鎖檔避免重疊（daemon 模式 + 同時 cron 會撞）
#
set -euo pipefail

SCRIPT="/home/hoonsoropenclaw/.hermes/scripts/linux_ops_monitor.py"
LOCK="/tmp/linux_ops_monitor.lock"
LOG_DIR="$HOME/.hermes/logs"
RUN_LOG="$LOG_DIR/linux_ops_monitor_cron.log"
ALERT_LOG="$LOG_DIR/linux_ops_monitor_alerts.log"

# 環境檢查
if [[ ! -f "$SCRIPT" ]]; then
  echo "[$(date -Iseconds)] FATAL: $SCRIPT not found" >> "$RUN_LOG" 2>/dev/null || true
  exit 3
fi

# 鎖檔（flock 不可得就退出、不堆積）
exec 9>"$LOCK"
if ! flock -n 9; then
  # 上一輪還在跑（daemon 模式），跳過
  exit 0
fi

# 跑
EXIT=0
python3 "$SCRIPT" --once --since 15m >> "$RUN_LOG" 2>&1 || EXIT=$?

# 把告警 log 的最近 50 行做 snapshot 給 cron 收信（mail-on-warn pattern）
if [[ $EXIT -ge 1 ]]; then
  {
    echo "--- $(date -Iseconds) linux_ops_monitor exit=$EXIT ---"
    tail -n 50 "$ALERT_LOG" 2>/dev/null || echo "(no alert log yet)"
  } >> "$RUN_LOG"
fi

# 退出碼反映原 severity（讓 cron 收信 / 可以用 onfailure= 觸發更多動作）
exit $EXIT

# Note：lock fd 會在腳本 exit 時自動釋放（exec 9> 跟著 process 走）
# flock 是 fd 級鎖、不檢查 PID；舊 process 若 SIGKILL 死掉、新 flock 仍可搶
# /tmp/linux_ops_monitor.lock 留著沒事（inode 仍在）
