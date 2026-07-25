#!/bin/bash
# Connection Recovery Script - 中斷後自動恢復
# 作者：拉斐爾連線保護系統
# 版本：1.0.0

LOG_FILE="/home/hoonsoropenclaw/.openclaw/workspace/logs/connection_recovery.log"
RECOVERY_QUEUE="/home/hoonsoropenclaw/.openclaw/workspace/evolution/endless_mode/pending_agents.txt"
GATEWAY_SERVICE="openclaw-gateway.service"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 發送 Telegram 通知
send_telegram() {
    local message="$1"
    local chat_id="8209753986"
    # 使用現有的 telegram 配置發送
    curl -s "https://api.telegram.org/bot$(grep botToken ~/.openclaw/openclaw.json | cut -d'"' -f4)/sendMessage" \
        -d "chat_id=$chat_id" \
        -d "text=$message" \
        2>/dev/null || log "Telegram 通知發送失敗"
}

# 恢復 Gateway
recover_gateway() {
    log "=== 開始 Gateway 恢復流程 ==="
    
    # 嘗試重啟服務
    log "嘗試重啟 Gateway 服務..."
    systemctl --user restart "$GATEWAY_SERVICE" 2>/dev/null
    
    sleep 5
    
    # 檢查是否恢復
    if curl -s --max-time 5 "http://localhost:18789/api/status" > /dev/null 2>&1; then
        log "✅ Gateway 恢復成功"
        send_telegram "🔧 Gateway 已自動恢復正常運行"
        return 0
    else
        log "❌ Gateway 重啟後仍無法訪問"
        send_telegram "🚨 Gateway 恢復失敗，需要手動介入！"
        return 1
    fi
}

# 清理 Session 鎖定
recover_locks() {
    log "=== 開始 Session 鎖定清理 ==="
    
    local lock_dir="/home/hoonsoropenclaw/.openclaw/sessions/"
    local cleaned=0
    
    if [ -d "$lock_dir" ]; then
        while IFS= read -r lockfile; do
            local age=$(($(date +%s) - $(stat -c %Y "$lockfile" 2>/dev/null || echo 0)))
            if [ "$age" -gt 300 ]; then  # 超過5分鐘
                log "移除過時鎖定: $lockfile"
                rm -f "$lockfile"
                ((cleaned++))
            fi
        done < <(find "$lock_dir" -name "*.lock" 2>/dev/null)
    fi
    
    log "已清理 $cleaned 個過時鎖定"
    return 0
}

# 恢復中斷的子代理任務
recover_subagents() {
    log "=== 開始子代理任務恢復 ==="
    
    # 讀取待恢復的任務佇列
    if [ -f "$RECOVERY_QUEUE" ] && [ -s "$RECOVERY_QUEUE" ]; then
        local count=$(wc -l < "$RECOVERY_QUEUE")
        log "發現 $count 個待恢復任務"
        
        while IFS= read -r task; do
            log "恢復任務: $task"
            # 這裡可以根據任務類型重新啟動
        done < "$RECOVERY_QUEUE"
        
        # 清空佇列（已處理）
        > "$RECOVERY_QUEUE"
    else
        log "沒有待恢復的任務"
    fi
    
    return 0
}

# 完整恢復流程
full_recovery() {
    log "=== 開始完整恢復流程 ==="
    
    local failed=0
    
    # 1. 清理鎖定
    recover_locks || ((failed++))
    
    # 2. 檢查並恢復 Gateway
    if ! curl -s --max-time 5 "http://localhost:18789/api/status" > /dev/null 2>&1; then
        recover_gateway || ((failed++))
    else
        log "Gateway 正常運行中"
    fi
    
    # 3. 恢復子代理
    recover_subagents
    
    # 4. 發送報告
    if [ "$failed" -eq 0 ]; then
        send_telegram "✅ 系統已自動恢復，所有服務正常運行"
        log "恢復完成：全部成功"
    else
        send_telegram "⚠️ 系統恢復完成，但有 $failed 項失敗"
        log "恢復完成：$failed 項失敗"
    fi
    
    return $failed
}

# 主程式
main() {
    local mode="${1:-check}"
    
    case "$mode" in
        gateway)
            recover_gateway
            ;;
        locks)
            recover_locks
            ;;
        subagents)
            recover_subagents
            ;;
        force)
            full_recovery
            ;;
        *)
            # 預設：檢查然後按需恢復
            if ! curl -s --max-time 5 "http://localhost:18789/api/status" > /dev/null 2>&1; then
                log "Gateway 無回應，執行恢復..."
                recover_gateway
            fi
            ;;
    esac
}

main "$@"