#!/usr/bin/env bash
# sysmonitor uninstall — 撤掉 systemd + cron
set -euo pipefail

echo "=== 卸載 sysmonitor ==="

# systemd
if systemctl list-unit-files sysmonitor.service 2>/dev/null | grep -q sysmonitor.service; then
    sudo systemctl disable --now sysmonitor.timer 2>/dev/null || true
    sudo systemctl stop sysmonitor.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/sysmonitor.service
    sudo rm -f /etc/systemd/system/sysmonitor.timer
    sudo systemctl daemon-reload
    echo "  systemd units removed"
else
    echo "  （沒找到 systemd units）"
fi

# cron
if crontab -l 2>/dev/null | grep -q "sysmonitor"; then
    (crontab -l 2>/dev/null | grep -vF "sysmonitor") | crontab -
    echo "  cron entry removed"
else
    echo "  （沒找到 cron entry）"
fi

echo "=== 完成 ==="
echo "  程式檔案保留在：$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "  解除安裝乾淨：rm -rf $(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
