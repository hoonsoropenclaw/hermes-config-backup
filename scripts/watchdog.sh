#!/bin/bash
# ==============================================
# watchdog.sh - Gateway 看門狗機制
# 功能：每 5 分鐘檢查 openclaw gateway 是否活著
#       若 crash，自動重啟並發 Telegram 通知
# 建立：2026-05-25
# 修改：2026-05-26 - 只有出錯時才發 Telegram
# ==============================================

set -euo pipefail

LOG_DIR="/home/hoonsoropenclaw/.hermes/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/watchdog.log"

GATEWAY_PORT="${GATEWAY_PORT:-18789}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

send_telegram() {
    local msg="$1"
    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
        curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${msg}" \
            -d "parse_mode=HTML" > /dev/null 2>&1 || true
    fi
}

check_gateway() {
    # 嘗試讀取 gateway 狀態
    if hermes gateway status 2>&1 | grep -q "running"; then
        return 0
    else
        return 1
    fi
}

restart_gateway() {
    local restart_result=0
    log "Gateway is DOWN. Attempting restart..."
    
    # 停止 gateway（如果存在的話）
    hermes gateway stop 2>/dev/null || true
    sleep 2
    
    # 啟動 gateway
    hermes gateway start
    sleep 5
    
    # 檢查是否啟動成功
    if check_gateway; then
        log "Gateway restarted successfully."
        send_telegram "🔧 <b>Hermes 看門狗</b>\nGateway 崩潰後已自動重啟 ✅"
    else
        log "Gateway restart FAILED."
        send_telegram "🚨 <b>Hermes 看門狗</b>\nGateway 重啟失敗，需要手動介入！"
        restart_result=1
    fi
    
    return $restart_result
}

# 主程式
main() {
    local exit_code=0
    log "=== Watchdog Check Started ==="
    
    if check_gateway; then
        log "Gateway is healthy."
        # 更新 heartbeat（不發 Telegram）
        /home/hoonsoropenclaw/.hermes/scripts/update_heartbeat.sh "watchdog" "healthy"
    else
        log "Gateway is DOWN!"
        restart_gateway
        exit_code=$?
    fi
    
    log "=== Watchdog Check Completed (exit: $exit_code) ==="
    return $exit_code
}

main "$@"