#!/bin/bash
# Connection Monitor - 每分鐘檢查系統健康狀態
# 作者：拉斐爾連線保護系統
# 版本：1.0.0

LOG_FILE="/home/hoonsoropenclaw/.openclaw/workspace/logs/connection_monitor.log"
STATUS_FILE="/home/hoonsoropenclaw/.openclaw/workspace/skills/connection-resilience/status_tracker.json"
GATEWAY_URL="http://localhost:18789"
ALERT_THRESHOLD=30  # 秒
LOCK_THRESHOLD=300  # 5分鐘

# 日誌函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 寫入狀態JSON
write_status() {
    cat > "$STATUS_FILE" << EOF
{
    "last_check": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "gateway_alive": $1,
    "gateway_latency": $2,
    "session_locked": $3,
    "active_subagents": $4,
    "api_quota_percent": $5,
    "status": "$6"
}
EOF
}

# 檢查 Gateway 響應
check_gateway() {
    local start=$(date +%s%N)
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$GATEWAY_URL/api/status" 2>/dev/null || echo "000")
    local end=$(date +%s%N)
    local latency=$(( (end - start) / 1000000 ))
    
    if [ "$response" == "200" ]; then
        echo "alive:$latency"
    else
        echo "dead:0"
    fi
}

# 檢查 Session 鎖定
check_session_locks() {
    local lock_count=0
    local lock_dir="/home/hoonsoropenclaw/.openclaw/sessions/"
    
    if [ -d "$lock_dir" ]; then
        # 找出鎖定超時的 session
        while IFS= read -r lockfile; do
            if [ -f "$lockfile" ]; then
                local age=$(($(date +%s) - $(stat -c %Y "$lockfile" 2>/dev/null || echo 0)))
                if [ "$age" -gt "$LOCK_THRESHOLD" ]; then
                    ((lock_count++))
                    log "WARN: Stale lock detected: $lockfile (age: ${age}s)"
                fi
            fi
        done < <(find "$lock_dir" -name "*.lock" 2>/dev/null)
    fi
    
    echo $lock_count
}

# 檢查子代理狀態
check_subagents() {
    openclaw sessions 2>/dev/null | grep -c "subagent" || echo 0
}

# 檢查 API 額度
check_api_quota() {
    local counter_file="/home/hoonsoropenclaw/.openclaw/workspace/evolution/endless_mode/counter_20260507_080000.txt"
    if [ -f "$counter_file" ]; then
        local count=$(cat "$counter_file")
        local percent=$((count * 100 / 4500))
        echo $percent
    else
        echo 100
    fi
}

# 主檢查流程
main() {
    local mode="${1:-check}"
    
    log "=== 開始連線監控檢查 ==="
    
    # 1. Gateway 狀態
    local gw_result=$(check_gateway)
    local gw_alive=$(echo "$gw_result" | cut -d: -f1)
    local gw_latency=$(echo "$gw_result" | cut -d: -f2)
    
    if [ "$gw_alive" == "alive" ]; then
        log "Gateway: 正常 (延遲: ${gw_latency}ms)"
    else
        log "ERROR: Gateway: 無回應!"
    fi
    
    # 2. Session 鎖定檢查
    local lock_count=$(check_session_locks)
    if [ "$lock_count" -gt 0 ]; then
        log "WARN: 發現 $lock_count 個過時的 Session 鎖定"
    else
        log "Session 鎖定: 無異常"
    fi
    
    # 3. 子代理狀態
    local active_sa=$(check_subagents)
    log "活躍子代理: $active_sa 個"
    
    # 4. API 額度
    local quota_percent=$(check_api_quota)
    log "API 額度剩余: ${quota_percent}%"
    
    # 寫入狀態檔
    local status="healthy"
    if [ "$gw_alive" != "alive" ]; then
        status="gateway_down"
    elif [ "$lock_count" -gt 0 ]; then
        status="locked_sessions"
    elif [ "$quota_percent" -lt 5 ]; then
        status="quota_low"
    fi
    
    write_status "$gw_alive" "$gw_latency" "$lock_count" "$active_sa" "$quota_percent" "$status"
    
    # 5. 根據狀態決定行動
    case "$status" in
        gateway_down)
            log "ERROR: Gateway 無回應，嘗試重啟..."
            bash /home/hoonsoropenclaw/.openclaw/workspace/skills/connection-resilience/recover.sh gateway
            ;;
        locked_sessions)
            log "WARN: 清理過時的 Session 鎖定..."
            bash /home/hoonsoropenclaw/.openclaw/workspace/skills/connection-resilience/recover.sh locks
            ;;
        quota_low)
            log "ALERT: API 額度即將用盡 (< 5%)"
            # 發送 Telegram 警報
            echo "⚠️ API 額度低於 5%！" >> /home/hoonsoropenclaw/.openclaw/workspace/evolution/endless_mode/pending_telegram_messages.log
            ;;
        healthy)
            log "系統狀態: 健康 ✅"
            ;;
    esac
    
    log "=== 監控檢查完成 ==="
    echo ""
}

# 顯示狀態
show_status() {
    if [ -f "$STATUS_FILE" ]; then
        cat "$STATUS_FILE"
    else
        echo "{\"status\": \"no_data\", \"message\": \"尚未執行監控\"}"
    fi
}

case "$mode" in
    status)
        show_status
        ;;
    *)
        main "$mode"
        ;;
esac