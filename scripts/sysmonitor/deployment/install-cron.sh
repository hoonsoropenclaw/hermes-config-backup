#!/usr/bin/env bash
# sysmonitor install — 透過 cron（不需要 sudo）
#
# 在目前使用者的 crontab 註冊每分鐘跑一次。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/../sysmonitor.py"
LOG_DIR="$SCRIPT_DIR/../logs"

# 確認檔案在
[[ -f "$SCRIPT" ]] || { echo "ERROR: $SCRIPT 不存在"; exit 1; }

# 確保 log 目錄存在
mkdir -p "$LOG_DIR/cron"

# 組 crontab 行
CRON_LINE="* * * * * /usr/bin/python3 $SCRIPT --once >> $LOG_DIR/cron/cron.log 2>&1"

# 檢查重複
if (crontab -l 2>/dev/null | grep -qF "$SCRIPT"); then
    echo "=== sysmonitor cron 已存在，更新 ==="
    (crontab -l 2>/dev/null | grep -vF "$SCRIPT" || true) | crontab -
fi

# 加進去
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

echo "=== cron 安裝完成 ==="
echo "  目前 crontab："
crontab -l | grep -F "sysmonitor" || echo "  (沒找到，請手動檢查)"
echo ""
echo "  Log 位置：$LOG_DIR/cron/cron.log"
echo "  解除：crontab -e 把 sysmonitor 那行刪掉"
