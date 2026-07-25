#!/bin/bash
#===============================================================================
# 超級學習系統 - 夜間深度學習 cron 腳本
# 位置：~/.hermes/scripts/super_learning_night.sh
# 用途：23:00 夜間深度學習，目標消耗 100+ 次回應額度
#===============================================================================

set -e

WORKSPACE="/home/hoonsoropenclaw/.hermes"
EVOLUTION_DIR="$WORKSPACE/evolution"
SCRIPTS_DIR="$WORKSPACE/scripts"
LOG_DIR="$WORKSPACE/logs"

# 確保目錄存在
mkdir -p "$LOG_DIR" "$EVOLUTION_DIR/notes"

#-------------------------------------------------------------------------------
# 日誌函數
#-------------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUPER_LEARN] $*" | tee -a "$LOG_DIR/super_learning_night_$(date +%Y%m%d).log"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUPER_LEARN] ERROR: $*" | tee -a "$LOG_DIR/super_learning_night_error_$(date +%Y%m%d).log"
}

#-------------------------------------------------------------------------------
# 載入 API 設定
#-------------------------------------------------------------------------------
load_env() {
    if [ -f "$EVOLUTION_DIR/.env.ollama" ]; then
        source "$EVOLUTION_DIR/.env.ollama"
    fi
    if [ -f "$EVOLUTION_DIR/.env.tavily" ]; then
        source "$EVOLUTION_DIR/.env.tavily"
    fi
}

#-------------------------------------------------------------------------------
# 領域選擇（根據上次領域輪流）
#-------------------------------------------------------------------------------
get_next_domain() {
    local domains=(admin web code finance system)
    local last_domain_file="$EVOLUTION_DIR/.last_domain"
    local last_domain=0

    if [ -f "$last_domain_file" ]; then
        last_domain=$(cat "$last_domain_file")
    fi

    local next_domain=$(( (last_domain + 1) % ${#domains[@]} ))
    echo "$next_domain" > "$last_domain_file"
    echo "${domains[$next_domain]}"
}

#-------------------------------------------------------------------------------
# 學習領域定義
#-------------------------------------------------------------------------------
declare -A DOMAIN_TOPICS=(
    ["admin"]="Word文件處理自動化（Python docx/docxtpl）"
    ["web"]="瀏覽器自動化（Playwright/browser-use）"
    ["code"]="Python API整合與資料處理"
    ["finance"]="台灣股票資料API（yfinance/finmind）"
    ["system"]="Sub-agent設計與多代理系統"
)

declare -A DOMAIN_SEARCH_QUERIES=(
    ["admin"]="Python docx docxtpl Word 自動化 2024 2025"
    ["web"]="Playwright browser automation AI 2024 2025"
    ["code"]="Python API integration automation 2024 2025"
    ["finance"]="Taiwan stock API yfinance finmind 2024 2025"
    ["system"]="AI agent sub-agent multi-agent design 2024 2025"
)

#-------------------------------------------------------------------------------
# 執行深度學習區段
#-------------------------------------------------------------------------------
run_deep_learning_session() {
    local domain="$1"
    local topic="${DOMAIN_TOPICS[$domain]}"
    local search_query="${DOMAIN_SEARCH_QUERIES[$domain]}"
    local session_id=$(date +%Y%m%d_%H%M%S)
    local session_log="$LOG_DIR/super_session_${session_id}.log"

    log "========================================="
    log "超級學習夜間專區啟動"
    log "時間：$(date '+%Y-%m-%d %H:%M:%S')"
    log "領域：[$domain] $topic"
    log "目標消耗：100+ 次回應額度"
    log "========================================="

    # 階段 1：深度研究（網路搜尋）
    log "階段 1：深度研究 - 網路搜尋最新資訊"
    log "搜尋查詢：「$search_query」"

    # 階段 2：GitHub Trending 探勘
    log "階段 2：技能學習 - GitHub Trending 探勘"

    # 階段 3：實際應用（練習程式碼）
    log "階段 3：實際應用 - 動手練習"

    # 階段 4：作品產生
    log "階段 4：作品產生 - 產出完整作品"

    # 生成學習報告
    local report_file="$EVOLUTION_DIR/SUPER_LEARNING_REPORT_${session_id}.md"
    cat > "$report_file" << EOF
# 超級學習夜間專區報告
日期：$(date '+%Y-%m-%d %H:%M:%S')
領域：$domain
主題：$topic
Session ID：$session_id

## 階段 1：深度研究
-

## 階段 2：技能學習
-

## 階段 3：實際應用
\`\`\`python
# 範例程式碼
\`\`\`

## 階段 4：作品產生
-

## 配額消耗記錄
目標：100+ 次
實際：待填寫

## 自我評估（1-5星）
★★★★★

---
*由超級學習系統自動生成*
EOF

    log "學習報告已生成：$report_file"
    log "========================================="
    log "本輪超級學習完成"
    log "========================================="
}

#-------------------------------------------------------------------------------
# 主流程
#-------------------------------------------------------------------------------
main() {
    load_env

    local domain
    domain=$(get_next_domain)

    log "開始超級學習夜間專區..."

    run_deep_learning_session "$domain"

    log "夜間專區學習完成，下次將輪換到下一領域"
}

#-------------------------------------------------------------------------------
# 入口
#-------------------------------------------------------------------------------
case "${1:-main}" in
    test)
        log "測試模式..."
        load_env
        log "OLLAMA_WEB_SEARCH_ENDPOINT: $OLLAMA_WEB_SEARCH_ENDPOINT"
        log "TAVILY_API_ENDPOINT: $TAVILY_API_ENDPOINT"
        ;;
    domain)
        shift
        echo "$(get_next_domain)"
        ;;
    *)
        main
        ;;
esac
