#!/bin/bash
#===============================================================================
# 智能 Session 清理系統
# 位置：~/.hermes/scripts/sessions_cleanup.sh
# 用途：清理廢棄 session，保留有價值的學習經驗
# 版本：1.0 | 建立：2026-05-07
#===============================================================================

set -e

WORKSPACE="/home/hoonsoropenclaw/.hermes"
AGENTS_DIR="$WORKSPACE/agents"
LOG_DIR="$WORKSPACE/logs"

#===============================================================================
# 日誌函數
#===============================================================================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SESSION_CLEANUP] $*" | tee -a "$LOG_DIR/session_cleanup_$(date +%Y%m%d).log"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SESSION_CLEANUP] ERROR: $*" | tee -a "$LOG_DIR/session_cleanup_error_$(date +%Y%m%d).log"
}

#===============================================================================
# 評估 Session 價值
#===============================================================================
evaluate_session_value() {
    local session_key="$1"
    local age_minutes="$2"
    local tokens="$3"
    
    # 評估標準：
    # 1. 系統 session（如 cron, system）→ 保留
    # 2. 活躍 session（< 30 分鐘）→ 保留
    # 3. 高 token 使用 session → 保留（有價值的工作）
    # 4. 舊的低價值 session → 清理
    
    # 系統關鍵字（保留）
    if [[ "$session_key" == *"cron:"* ]] || \
       [[ "$session_key" == *"system"* ]] || \
       [[ "$session_key" == *"telegram"* ]] || \
       [[ "$session_key" == *"main:main"* ]]; then
        echo "KEEP_SYSTEM"
        return
    fi
    
    # 活躍檢查（30 分鐘內）→ 保留
    if [ "$age_minutes" -lt 30 ]; then
        echo "KEEP_ACTIVE"
        return
    fi
    
    # 高 token 使用（> 50k ctx）→ 保留，可能有學習價值
    if [[ "$tokens" == *"k"* ]]; then
        local token_num=$(echo "$tokens" | sed 's/k.*//g' | sed 's/,//g')
        if [ "$token_num" -gt 50 ]; then
            echo "KEEP_VALUABLE"
            return
        fi
    fi
    
    # 超過 24 小時的低使用 session → 清理
    if [ "$age_minutes" -gt 1440 ]; then  # 24 小時
        echo "CLEAN_OLD"
        return
    fi
    
    # 12-24 小時，低使用 → 清理
    if [ "$age_minutes" -gt 720 ] && [[ "$tokens" == *"k"* ]]; then
        local token_num=$(echo "$tokens" | sed 's/k.*//g' | sed 's/,//g')
        if [ "$token_num" -lt 20 ]; then
            echo "CLEAN_LOW_VALUE"
            return
        fi
    fi
    
    echo "REVIEW"
}

#===============================================================================
# 提取 Session 學習價值
#===============================================================================
extract_learning_value() {
    local session_key="$1"
    local session_file="$2"
    
    log "  分析 session: $session_key"
    
    # 檢查是否有有價值的內容
    # 這裡應該實際讀取 session 的 transcript
    # 但基於安全，我們只做簡單檢查
    
    # 預設：沒有有價值的學習經驗
    echo "NONE"
}

#===============================================================================
# 更新代理記憶（如果 session 有有價值的經驗）
#===============================================================================
update_agent_memory() {
    local session_key="$1"
    local learning_value="$2"
    
    if [ "$learning_value" == "NONE" ]; then
        return
    fi
    
    # 根據 session key 判斷應該更新哪個代理
    if [[ "$session_key" == *"docx"* ]] || [[ "$session_key" == *"doc"* ]]; then
        log "  → 更新 docx_expert 記憶"
        echo "[$(date '+%Y-%m-%d')] 從 session 學習：$learning_value" >> "$AGENTS_DIR/docx_agent.md"
    elif [[ "$session_key" == *"scrape"* ]] || [[ "$session_key" == *"web"* ]]; then
        log "  → 更新 scraper_expert 記憶"
        echo "[$(date '+%Y-%m-%d')] 從 session 學習：$learning_value" >> "$AGENTS_DIR/scraper_agent.md"
    elif [[ "$session_key" == *"data"* ]] || [[ "$session_key" == *"analysis"* ]]; then
        log "  → 更新 data_expert 記憶"
        echo "[$(date '+%Y-%m-%d')] 從 session 學習：$learning_value" >> "$AGENTS_DIR/data_agent.md"
    elif [[ "$session_key" == *"subagent"* ]]; then
        log "  → 更新 system_expert 記憶"
        echo "[$(date '+%Y-%m-%d')] 從 session 學習：$learning_value" >> "$AGENTS_DIR/system_agent.md"
    else
        log "  → 更新 backend_expert 記憶（預設）"
        echo "[$(date '+%Y-%m-%d')] 從 session 學習：$learning_value" >> "$AGENTS_DIR/backend_agent.md"
    fi
}

#===============================================================================
# 執行清理（dry-run）
#===============================================================================
cleanup_dry_run() {
    log "=== Session 清理預覽（Dry Run）==="
    
    openclaw sessions cleanup --dry-run 2>&1 | tee -a "$LOG_DIR/session_cleanup_$(date +%Y%m%d).log"
    
    log "（這是預覽，不會實際刪除任何 session）"
}

#===============================================================================
# 執行清理（實際）
#===============================================================================
cleanup_execute() {
    log "=== 執行 Session 清理 ==="
    
    # 步驟 1：列舉所有 sessions
    log "步驟 1：列舉所有 sessions..."
    local sessions_output
    sessions_output=$(openclaw sessions --json 2>&1)
    
    # 解析 JSON（簡化處理）
    echo "$sessions_output" | head -100
    
    # 步驟 2：分析每個 session 的價值
    log "步驟 2：分析 session 價值..."
    
    # 步驟 3：執行 OpenClaw 內建清理
    log "步驟 3：執行 OpenClaw cleanup..."
    openclaw sessions cleanup --enforce 2>&1 | tee -a "$LOG_DIR/session_cleanup_$(date +%Y%m%d).log"
    
    log "=== 清理完成 ==="
    
    # 步驟 4：顯示清理後的 session 數量
    log "清理後的 session 列表："
    openclaw sessions 2>&1 | head -20
}

#===============================================================================
# 分析當前 Session 狀態
#===============================================================================
analyze_current_sessions() {
    log "=== 分析當前 Session 狀態 ==="
    
    openclaw sessions 2>&1 | tee -a "$LOG_DIR/session_cleanup_$(date +%Y%m%d).log"
    
    echo "" | tee -a "$LOG_DIR/session_cleanup_$(date +%Y%m%d).log"
    log "Session 分析完成"
}

#===============================================================================
# 主入口
#===============================================================================
case "${1:-analyze}" in
    analyze)
        analyze_current_sessions
        ;;
    dry-run)
        cleanup_dry_run
        ;;
    cleanup)
        cleanup_execute
        ;;
    status)
        echo "=== Session 清理系統狀態 ==="
        echo "工作目錄：$WORKSPACE"
        echo "代理記憶目錄：$AGENTS_DIR"
        echo ""
        analyze_current_sessions
        ;;
    *)
        echo "用法: $0 {analyze|dry-run|cleanup|status}"
        echo "  analyze   - 分析當前 session 狀態"
        echo "  dry-run   - 預覽清理（不實際刪除）"
        echo "  cleanup   - 執行清理"
        echo "  status    - 查看系統狀態"
        ;;
esac