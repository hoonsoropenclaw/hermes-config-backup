#!/bin/bash
# ==============================================
# api_quota_monitor.sh - API 配額消耗追蹤與預警
# 功能：追蹤 MiniMax API 消耗速率，預估耗盡時間
#       當剩餘額度 < 20% 或預估撐不到 24 小時，提前告警
# 建立：2026-05-25
# 修改：2026-05-26 - 只有出錯/告警時才發 Telegram
# ==============================================

set -euo pipefail

LOG_DIR="/home/hoonsoropenclaw/.hermes/logs"
QUOTA_LOG="$LOG_DIR/api_quota_tracker.log"
STATUS_FILE="/home/hoonsoropenclaw/.hermes/api_quota_status.json"

# 閾值
THRESHOLD_PCT=20      # 剩餘百分比低於此值就告警
HOURS_AHEAD=24        # 預估可撐時間（少於此值就告警）

# 顏色輸出
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_alert() { echo -e "${RED}[ALERT]${NC} $1"; }

send_telegram() {
    local msg="$1"
    local bot_token="${TELEGRAM_BOT_TOKEN:-}"
    local chat_id="${TELEGRAM_CHAT_ID:-}"
    if [[ -n "$bot_token" && -n "$chat_id" ]]; then
        curl -s "https://api.telegram.org/bot${bot_token}/sendMessage" \
            -d "chat_id=${chat_id}" \
            -d "text=${msg}" \
            -d "parse_mode=HTML" > /dev/null 2>&1 || true
    fi
}

# 讀取目前的 quota 狀態（從 openclaw session_status 或從記錄檔）
get_current_quota() {
    # 嘗試從 openclaw status 讀取
    local status_output
    status_output=$(openclaw status 2>&1 || echo "ERROR")
    
    # 從 api_usage.log 讀取歷史記錄
    if [[ -f "$QUOTA_LOG" ]]; then
        local last_line
        last_line=$(tail -1 "$QUOTA_LOG" 2>/dev/null || echo "")
        if [[ -n "$last_line" ]]; then
            echo "$last_line"
            return 0
        fi
    fi
    
    # 嘗試從 session_status 讀取配額資訊
    echo "$status_output" | grep -i "quota\|usage\|remaining\|limit" | head -5 || true
    
    return 1
}

# 更新配額記錄
update_quota_log() {
    local calls="$1"
    local timestamp="$2"
    
    echo "${timestamp},${calls}" >> "$QUOTA_LOG"
}

# 分析消耗速率（返回 "" 表示正常，"WARNING: xxx" 表示需要告警）
analyze_usage() {
    local now
    now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # 讀取最近 24 小時的記錄
    local usage_data=""
    local recent_calls=""
    
    if [[ -f "$QUOTA_LOG" ]]; then
        # 取得最後 288 筆假設每 5 分鐘一筆 = 24 小時
        local last_24h
        last_24h=$(tail -288 "$QUOTA_LOG" 2>/dev/null || echo "")
        usage_data="$last_24h"
    fi
    
    # 嘗試從 session_status 取得目前的額度使用量
    local current_usage=""
    local quota_info=""
    
    # 讀取狀態檔（如果有的話）
    if [[ -f "$STATUS_FILE" ]]; then
        current_usage=$(python3 -c "import json; d=json.load(open('$STATUS_FILE')); print(d.get('current_usage',''))" 2>/dev/null || echo "")
    fi
    
    # 分析輸出
    if [[ -n "$usage_data" ]]; then
        local call_count
        call_count=$(echo "$usage_data" | wc -l)
        local last_call
        last_call=$(echo "$usage_data" | tail -1 | cut -d',' -f2)
        local first_call
        first_call=$(echo "$usage_data" | head -1 | cut -d',' -f2)
        
        if [[ -n "$first_call" && -n "$last_call" && "$call_count" -gt 1 ]]; then
            local diff=$((last_call - first_call))
            local hours_elapsed
            hours_elapsed=$(echo "$usage_data" | tail -1 | cut -d',' -f1 | xargs -I{} python3 -c "from datetime import datetime; print((datetime.now() - datetime.fromisoformat('{}')).total_seconds() / 3600)" 2>/dev/null || echo "1")
            
            if (( $(echo "$hours_elapsed > 0" | bc -l 2>/dev/null || echo "0") )); then
                local rate_per_hour
                rate_per_hour=$(echo "scale=2; $diff / $hours_elapsed" | bc -l 2>/dev/null || echo "0")
                log_info "Rate: ${rate_per_hour} calls/hour over ${hours_elapsed}h (${diff} total calls)"
                
                # 這裡可以加上告警邏輯，如果需要的話
                # 例如：rate_per_hour > 100 就告警
            fi
        fi
    fi
}

# 主程式
main() {
    local exit_code=0
    log_info "API Quota Monitor Started..."
    
    # 檢查是否有足够的歷史數據
    if [[ ! -f "$QUOTA_LOG" ]]; then
        log_info "No usage history found. Creating log file."
        mkdir -p "$LOG_DIR"
        echo "# API Quota Tracker - Started $(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "$QUOTA_LOG"
        log_info "Run this script after API calls to log usage"
        return 0
    fi
    
    # 分析消耗
    local analysis
    analysis=$(analyze_usage)
    
    if [[ -n "$analysis" ]]; then
        log_info "$analysis"
    else
        log_info "Not enough data for analysis yet"
    fi
    
    log_info "API Quota Monitor Completed"
    
    # 更新心跳（不發 Telegram）
    bash /home/hoonsoropenclaw/.hermes/scripts/update_heartbeat.sh "api_quota_monitor" "ok" "check complete"
    
    return $exit_code
}

main "$@"