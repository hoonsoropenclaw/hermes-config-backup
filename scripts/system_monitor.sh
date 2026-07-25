#!/bin/bash
# ==============================================
# system_monitor.sh - N100 硬體監控
# 功能：檢查磁碟空間、記憶體、CPU 負載
#       超過閾值時發 Telegram 告警
# 建立：2026-05-25
# 修改：2026-05-26 - 只有出錯時才發 Telegram
# 閾值：磁碟 >90%, 記憶體 >85%, Load >4
# ==============================================

set -euo pipefail

LOG_DIR="/home/hoonsoropenclaw/.hermes/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/system_monitor.log"

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# 閾值
DISK_THRESHOLD=90
MEM_THRESHOLD=85
LOAD_THRESHOLD=4

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

get_disk_usage() {
    df -h / | tail -1 | awk '{print $5}' | sed 's/%//'
}

get_mem_usage() {
    free -m | grep Mem | awk '{printf "%.0f", ($3/$2)*100}'
}

get_load_avg() {
    uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//'
}

get_uptime_days() {
    awk '{print int($1/86400)}' /proc/uptime
}

check_disk() {
    local usage
    usage=$(get_disk_usage)
    if (( usage > DISK_THRESHOLD )); then
        log "WARNING: Disk usage is ${usage}%"
        send_telegram "💾 <b>磁碟空間警告</b>\nN100 磁碟使用率：${usage}%\n儘早清理空間！"
        return 1
    fi
    return 0
}

check_memory() {
    local usage
    usage=$(get_mem_usage)
    if (( usage > MEM_THRESHOLD )); then
        log "WARNING: Memory usage is ${usage}%"
        send_telegram "🧠 <b>記憶體警告</b>\nN100 記憶體使用率：${usage}%\n注意可能記憶體洩漏！"
        return 1
    fi
    return 0
}

check_load() {
    local load
    load=$(get_load_avg)
    # 去除小數點比較
    load=${load%.*}
    if (( load > LOAD_THRESHOLD )); then
        log "WARNING: Load average is high: $load"
        send_telegram "⚠️ <b>負載警告</b>\nN100 負載：${load}（>${LOAD_THRESHOLD}）"
        return 1
    fi
    return 0
}

# 主程式
main() {
    local exit_code=0
    log "=== System Monitor Check Started ==="
    
    local issues=0
    check_disk || ((issues++))
    check_memory || ((issues++))
    check_load || ((issues++))
    
    local uptime_days
    uptime_days=$(get_uptime_days)
    
    if (( issues == 0 )); then
        log "All checks passed. Uptime: ${uptime_days} days"
        # 更新 heartbeat（不發 Telegram）
        /home/hoonsoropenclaw/.hermes/scripts/update_heartbeat.sh "system_monitor" "ok" "all_good"
    else
        log "Found ${issues} issues."
        exit_code=1
    fi
    
    log "=== System Monitor Check Completed (issues: $issues) ==="
    
    # 也更新 heartbeat
    return $exit_code
}

main "$@"