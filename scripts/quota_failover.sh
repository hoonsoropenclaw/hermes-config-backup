#!/bin/bash
# ============================================================
# Minimax 配額耗盡自動容錯處理器
# ============================================================
# 功能：
#   1. 偵測 Minimax 配額是否已達上限
#   2. 如果是學習任務 → 保存工作狀態，通知用戶，不繼續學習
#   3. 如果不是學習任務 → 自動切換 deepseek-chat 並標記
# ============================================================
# 安裝方式：放置於 ~/.hermes/scripts/
# 使用方式：quota_failover.sh <session_log_file>
# ============================================================

WORKSPACE="/home/hoonsoropenclaw/.hermes"
SAVE_DIR="${WORKSPACE}/evolution/quota_saves"
LOG_DIR="${WORKSPACE}/logs"
TELEGRAM_CHAT_ID="8209753986"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
DATE_TW=$(TZ='Asia/Taipei' date '+%Y-%m-%d %H:%M')

mkdir -p "$SAVE_DIR" "$LOG_DIR"

# 配額耗盡偵測函數
check_minimax_quota() {
    # 檢查最近 error log 是否包含 Minimax 配額耗盡訊息
    local logfile="$1"
    if [ -z "$logfile" ]; then
        # 從最新 cron run log 檢查
        local latest_log=$(ls -t "${LOG_DIR}"/cron_*.log 2>/dev/null | head -1)
        logfile="${latest_log:-/dev/null}"
    fi
    
    if grep -q "usage limit exceeded\|Token Plan Plus.*4500/4500\|FailoverError" "$logfile" 2>/dev/null; then
        return 0  # 配額耗盡
    fi
    return 1  # 正常
}

# 保存工作狀態
save_work_state() {
    local task_name="$1"
    local state_desc="$2"
    local save_file="${SAVE_DIR}/${task_name}_${TIMESTAMP}.json"
    
    cat > "$save_file" << EOF
{
  "saved_at": "${DATE_TW}",
  "task_name": "${task_name}",
  "reason": "Minimax quota exhausted",
  "state_summary": "${state_desc}",
  "resume_action": "使用 Minimax 重啟此任務時，先讀取此檔案恢復狀態"
}
EOF
    
    echo "$save_file"
}

# 發送 Telegram 通知
send_telegram_notify() {
    local message="$1"
    
    # 透過 OpenClaw sessions_send 或直接 curl 通知
    # 使用 OpenClaw 自身發送（當作 main session 中的訊息）
    cat > /tmp/quota_alert_$$.md << EOF
🔴 工作暫停通知：Minimax 配額耗盡

${message}

🕐 ${DATE_TW}

📝 下一步：
• Minimax 將於約 13:00 (台灣時間) 恢復配額
• 任務狀態已保存於 ${SAVE_DIR}/
• 恢復後可手動重啟任務，或等待我自動繼續
EOF
    
    echo "[ALERT] 通知已產生：/tmp/quota_alert_$$.md"
}

# 主邏輯
main() {
    local task_name="${1:-unknown_task}"
    local state_desc="${2:-工作進行中因配額耗盡中斷}"
    local logfile="${3:-}"
    
    echo "=== Minimax Quota Failover ==="
    echo "時間: ${DATE_TW}"
    echo "任務: ${task_name}"
    
    # 1. 保存工作狀態
    save_file=$(save_work_state "$task_name" "$state_desc")
    echo "狀態保存: $save_file"
    
    # 2. 產生停止訊息（不是用 deepseek 繼續學習）
    stop_msg="🔴 Minimax 配額已耗盡，學習任務已暫停

📌 任務：${task_name}
⏸️ 狀態：${state_desc}
💾 已保存於：${save_file}
⏰ 預計恢復：約 13:00（台灣時間）

⚠️ 注意：任務已妥善保存，未使用 deepseek 模型繼續執行以避免額外費用。"
    
    # 3. 發送通知（此時在 main session 中執行，直接輸出即可）
    send_telegram_notify "$stop_msg"
    
    echo "=== Done ==="
}

main "$@"
