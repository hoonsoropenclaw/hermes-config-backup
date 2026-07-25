#!/bin/bash
# cleanup_sessions.sh - 臨時代理 session 清理腳本
# 用於清理已完成且無價值的臨時 session，保留專家代理 session

set -e

WORKSPACE_DIR="$HOME/.hermes"
EXPERTS_DIR="$WORKSPACE_DIR/experts"
LOG_FILE="$WORKSPACE_DIR/logs/cleanup_sessions_$(date +%Y%m%d_%H%M%S).log"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗${NC} $1" | tee -a "$LOG_FILE"
}

# 建立日誌目錄
mkdir -p "$(dirname "$LOG_FILE")"

log "=============================================="
log "開始 session 清理程序"
log "=============================================="

# 1. 獲取所有 sessions
log "正在獲取所有 openclaw sessions..."
SESSIONS=$(openclaw sessions list 2>/dev/null || echo "")
if [ -z "$SESSIONS" ]; then
    log_warning "無法獲取 sessions 或沒有 sessions"
    exit 0
fi

# 2. 分析 sessions
log "分析 sessions..."

# 專家代理關鍵詞
EXPERT_KEYWORDS="backend-expert|frontend-expert|docx-expert|data-expert|expert"

# 臨時任務關鍵詞
TEMP_TASK_KEYWORDS="temp-|tmp-|anonymous|ephemeral|subagent-[0-9]"

# 3. 分類 sessions
TEMP_SESSIONS=()
EXPERT_SESSIONS=()
OTHER_SESSIONS=()

while IFS= read -r line; do
    if [ -z "$line" ]; then
        continue
    fi
    
    SESSION_ID=$(echo "$line" | awk '{print $1}' | head -1)
    SESSION_LABEL=$(echo "$line" | awk '{print $2" "$3" "$4}' | head -c 50)
    
    if echo "$SESSION_ID" | grep -qE "$TEMP_TASK_KEYWORDS"; then
        TEMP_SESSIONS+=("$SESSION_ID")
        log "  發現臨時 session: $SESSION_ID"
    elif echo "$SESSION_LABEL" | grep -qE "$EXPERT_KEYWORDS"; then
        EXPERT_SESSIONS+=("$SESSION_ID")
        log "  發現專家代理 session: $SESSION_ID (保留)"
    else
        OTHER_SESSIONS+=("$SESSION_ID")
    fi
done <<< "$SESSIONS"

# 4. 處理臨時 sessions
log ""
log "=============================================="
log "處理臨時 sessions"
log "=============================================="

if [ ${#TEMP_SESSIONS[@]} -eq 0 ]; then
    log_success "沒有需要清理的臨時 sessions"
else
    log "發現 ${#TEMP_SESSIONS[@]} 個臨時 sessions"
    
    for SESSION_ID in "${TEMP_SESSIONS[@]}"; do
        log "處理 session: $SESSION_ID"
        
        # 嘗試執行 /compact 摘要
        log "  執行 /compact 摘要..."
        if openclaw sessions cmd "$SESSION_ID" "/compact" 2>/dev/null; then
            log "  摘要完成"
        else
            log_warning "  摘要失敗或session已結束"
        fi
        
        # 刪除 session
        log "  刪除 session..."
        if openclaw sessions delete "$SESSION_ID" 2>/dev/null; then
            log_success "  已刪除 session: $SESSION_ID"
        else
            log_warning "  刪除失敗或session已不存在"
        fi
    done
fi

# 5. 專家代理 sessions 維護
log ""
log "=============================================="
log "專家代理 sessions 維護"
log "=============================================="

if [ ${#EXPERT_SESSIONS[@]} -eq 0 ]; then
    log_warning "沒有發現專家代理 sessions"
    log "提示: 專家代理sessions應定期更新其記憶文件"
else
    log_success "發現 ${#EXPERT_SESSIONS[@]} 個專家代理 sessions"
    for SESSION_ID in "${EXPERT_SESSIONS[@]}"; do
        log "  - $SESSION_ID (保持活躍)"
    done
fi

# 6. 其他 sessions 摘要
log ""
log "=============================================="
log "其他 sessions 狀態"
log "=============================================="

if [ ${#OTHER_SESSIONS[@]} -eq 0 ]; then
    log "沒有其他 sessions"
else
    log "發現 ${#OTHER_SESSIONS[@]} 個其他 sessions:"
    for SESSION_ID in "${OTHER_SESSIONS[@]}"; do
        log "  - $SESSION_ID"
    done
    log ""
    log "提示: 這些 sessions 如需清理，請手動處理"
fi

# 7. 總結
log ""
log "=============================================="
log "清理完成"
log "=============================================="
log "臨時 sessions 處理: ${#TEMP_SESSIONS[@]}"
log "專家代理 sessions: ${#EXPERT_SESSIONS[@]}"
log "其他 sessions: ${#OTHER_SESSIONS[@]}"
log "日誌檔案: $LOG_FILE"

log_success "Session 清理完成！"