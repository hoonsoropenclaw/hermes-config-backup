#!/usr/bin/env bash
# sysmonitor install — 註冊 systemd service + timer
#
# 設計：timer（不是 cron）的優勢是能看到上次跑了多久、是否成功、下次何時跑。
# 劣勢是 unit 檔需要 sudo 寫到 /etc/systemd/system。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SRC="$SCRIPT_DIR/deployment/systemd/sysmonitor.service"
TIMER_SRC="$SCRIPT_DIR/deployment/systemd/sysmonitor.timer"

# dry-run 模式
DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    echo "DRY RUN — 不會修改系統"
fi

run() {
    if [[ $DRY_RUN -eq 1 ]]; then
        echo "  → $@"
    else
        eval "$@"
    fi
}

echo "=== sysmonitor systemd 安裝 ==="

# 1. 確認 Python 3 路徑
PY=$(command -v python3)
[[ -x "$PY" ]] || { echo "ERROR: python3 not found"; exit 1; }
echo "Python: $PY"

# 2. 確認 psutil
if ! "$PY" -c "import psutil" 2>/dev/null; then
    echo "WARNING: psutil 沒裝，跑：$PY -m pip install psutil"
    [[ $DRY_RUN -eq 0 ]] && exit 1
fi

# 3. 確保 log 目錄存在
run "mkdir -p $SCRIPT_DIR/logs"
run "mkdir -p $SCRIPT_DIR/reports"

# 4. 確認 /var/log 讀權限
if [[ ! -r /var/log/syslog ]] && [[ $DRY_RUN -eq 0 ]]; then
    echo "WARNING: 無法讀 /var/log/syslog — 加使用者到 adm 群組："
    echo "  sudo usermod -aG adm \$(whoami)"
    echo "  （需重新登入生效）"
fi

# 5. 複製 unit
if [[ $DRY_RUN -eq 0 ]]; then
    run "sudo cp $SERVICE_SRC /etc/systemd/system/sysmonitor.service"
    run "sudo cp $TIMER_SRC /etc/systemd/system/sysmonitor.timer"
    run "sudo systemctl daemon-reload"
fi

# 6. 啟用 timer
if [[ $DRY_RUN -eq 0 ]]; then
    run "sudo systemctl enable --now sysmonitor.timer"
fi

echo ""
echo "=== 安裝完成 ==="
echo "  檢查狀態：  systemctl list-timers sysmonitor.timer"
echo "  立即跑一次：  systemctl start sysmonitor.service"
echo "  看 journal：  journalctl -u sysmonitor.service -f"
echo "  解除安裝：  bash $SCRIPT_DIR/deployment/uninstall.sh"
