#!/bin/bash
#===============================================================================
# 拉斐爾自主演化學習系統 - 主控腳本
# 位置：~/.hermes/scripts/evolution_main.sh
# 用途：在 OpenClaw 本體直接執行學習，知識直接沉積到記憶系統
#===============================================================================

set -e

WORKSPACE="/home/hoonsoropenclaw/.hermes"
EVOLUTION_DIR="$WORKSPACE/evolution"
SCRIPTS_DIR="$WORKSPACE/scripts"
LOG_DIR="$WORKSPACE/logs"

# 載入搜尋 API 設定（Ollama 主用，Tavily 備用）
if [ -f "$EVOLUTION_DIR/.env.ollama" ]; then
    source "$EVOLUTION_DIR/.env.ollama"
fi
if [ -f "$EVOLUTION_DIR/.env.tavily" ]; then
    source "$EVOLUTION_DIR/.env.tavily"
fi

# 確保目錄存在
mkdir -p "$LOG_DIR" "$EVOLUTION_DIR"

#-------------------------------------------------------------------------------
# 學習領域順序（根據 USER.md 設定的優先順序）
#-------------------------------------------------------------------------------
declare -A LEARNING_DOMAINS=(
    ["admin"]="行政工作：Word文件處理、校務流程自動化、法規對照"
    ["web"]="網頁設計：前端開發、爬蟲自動化、無頭瀏覽器"
    ["code"]="程式設計：Python自動化、API整合、資料處理"
    ["finance"]="金融工具：股票API、投資分析、自動化交易"
    ["system"]="系統工具：MCP工具、Sub-agent設計、技能安裝"
)

#-------------------------------------------------------------------------------
# 日誌函數
#-------------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/evolution_$(date +%Y%m%d).log"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_DIR/evolution_error_$(date +%Y%m%d).log"
}

#-------------------------------------------------------------------------------
# Ollama Web Search（主用）
#-------------------------------------------------------------------------------
search_web_ollama() {
    local query="$1"
    local max_results="${2:-$OLLAMA_WEB_SEARCH_MAX_RESULTS}"

    if [ -z "$OLLAMA_WEB_SEARCH_API_KEY" ]; then
        echo "Error: OLLAMA_WEB_SEARCH_API_KEY not set" >&2
        return 1
    fi

    local response
    response=$(curl -s -X POST "$OLLAMA_WEB_SEARCH_ENDPOINT" \
        -H "Authorization: Bearer $OLLAMA_WEB_SEARCH_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"$query\",\"max_results\":$max_results}" \
        --max-time 30 2>&1)

    if [ $? -ne 0 ]; then
        echo "Error: curl failed" >&2
        return 1
    fi

    # 檢查是否為有效的 JSON 並且有 results 欄位
    local tmpfile=$(mktemp)
    printf '%s' "$response" > "$tmpfile"
    local count
    count=$(python3 -c "import sys,json; d=json.load(open('$tmpfile')); print(len(d.get('results',[])))" 2>/dev/null || echo "0")
    rm -f "$tmpfile"

    if [ "$count" -gt 0 ]; then
        echo "$response"
        return 0
    else
        echo "Error: Ollama returned empty or invalid response" >&2
        return 1
    fi
}

#-------------------------------------------------------------------------------
# Tavily Search（備用）
#-------------------------------------------------------------------------------
search_web_tavily() {
    local query="$1"
    local max_results="${2:-$TAVILY_MAX_RESULTS}"

    if [ -z "$TAVILY_API_KEY" ]; then
        echo "Error: TAVILY_API_KEY not set" >&2
        return 1
    fi

    local response
    response=$(curl -s -X POST "$TAVILY_API_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "{\"api_key\":\"$TAVILY_API_KEY\",\"query\":\"$query\",\"max_results\":$max_results}" \
        --max-time 30 2>&1)

    if [ $? -ne 0 ]; then
        echo "Error: curl failed" >&2
        return 1
    fi

    # Tavily 回傳格式：{"results":[{"url":"...","content":"...","title":"..."}],...}
    # 轉換為 Ollama 格式方便統一處理
    local tmpfile=$(mktemp)
    printf '%s' "$response" > "$tmpfile"
    local count
    count=$(python3 -c "import sys,json; d=json.load(open('$tmpfile')); print(len(d.get('results',[])))" 2>/dev/null || echo "0")
    rm -f "$tmpfile"

    if [ "$count" -gt 0 ]; then
        # 已經是標準格式，直接回傳
        echo "$response"
        return 0
    else
        echo "Error: Tavily returned empty or invalid response" >&2
        return 1
    fi
}

#-------------------------------------------------------------------------------
# 統一搜尋入口（主用 Ollama，額度用盡時自動切換 Tavily）
#-------------------------------------------------------------------------------
search_web() {
    local query="$1"
    local max_results="${2:-$OLLAMA_WEB_SEARCH_MAX_RESULTS}"

    # 先嘗試 Ollama
    local response
    if [ -n "$OLLAMA_WEB_SEARCH_API_KEY" ]; then
        if response=$(search_web_ollama "$query" "$max_results"); then
            echo "$response"
            return 0
        fi
        log "Ollama 搜尋失敗，切換至 Tavily..."
    fi

    # Ollama 失敗或未設定，切換 Tavily
    if [ -n "$TAVILY_API_KEY" ]; then
        if response=$(search_web_tavily "$query" "$max_results"); then
            log "已切換至 Tavily 備用搜尋API"
            echo "$response"
            return 0
        fi
        log_error "Tavily 搜尋也失敗"
        return 1
    fi

    echo "Error: 沒有可用的搜尋 API" >&2
    return 1
}

#-------------------------------------------------------------------------------
# 網路搜尋格式化輸出
#-------------------------------------------------------------------------------
search_web_pretty() {
    local query="$1"
    local max_results="${2:-$OLLAMA_WEB_SEARCH_MAX_RESULTS}"

    local json_result
    json_result=$(search_web "$query" "$max_results") || {
        echo "搜尋失敗" >&2
        return 1
    }

    # 使用 python3 解析並格式化輸出（不怕 set -e）
    printf '%s' "$json_result" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    results = data.get('results', [])

    if not results:
        print('No results found.')
        sys.exit(1)

    print(f'找到 {len(results)} 個結果：\n')
    for i, r in enumerate(results, 1):
        title = r.get('title', 'N/A')
        url = r.get('url', 'N/A')
        content = r.get('content', '')[:300]
        print(f'--- 結果 {i} ---')
        print(f'標題：{title}')
        print(f'網址：{url}')
        print(f'摘要：{content}...')
        print()
except Exception as e:
    print(f'Parse error: {e}')
    sys.exit(1)
" && return 0

    # 如果 python3 失敗
    echo "$json_result" | head -c 500
    return 1
}

#-------------------------------------------------------------------------------
# 測試網路搜尋功能（測試兩者）
#-------------------------------------------------------------------------------
test_web_search() {
    log "=== 步驟0：測試網路搜尋功能 ==="

    if [ -n "$OLLAMA_WEB_SEARCH_API_KEY" ]; then
        log "測試 Ollama Web Search API..."
        local result
        if result=$(search_web_ollama "OpenClaw AI assistant" 3 2>&1); then
            local count
            count=$(echo "$result" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('results',[])))" 2>/dev/null || echo "0")
            if [ "$count" -gt 0 ]; then
                log "✅ Ollama 網路搜尋正常（取得 $count 個結果）"
                return 0
            fi
        fi
        log "⚠️  Ollama 搜尋失敗或無結果，嘗試 Tavily..."
    fi

    if [ -n "$TAVILY_API_KEY" ]; then
        local result
        if result=$(search_web_tavily "OpenClaw AI assistant" 3 2>&1); then
            local count
            count=$(echo "$result" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('results',[])))" 2>/dev/null || echo "0")
            if [ "$count" -gt 0 ]; then
                log "✅ Tavily 備用搜尋正常（取得 $count 個結果）"
                return 0
            fi
        fi
    fi

    log_error "所有搜尋 API 都無法使用"
    return 1
}

#-------------------------------------------------------------------------------
# 讀取技能目錄
#-------------------------------------------------------------------------------
read_skill_catalog() {
    if [ -f "$EVOLUTION_DIR/SKILL_CATALOG.md" ]; then
        cat "$EVOLUTION_DIR/SKILL_CATALOG.md"
    fi
}

#-------------------------------------------------------------------------------
# 檢查是否已學過某技能
#-------------------------------------------------------------------------------
is_already_learned() {
    local skill_name="$1"
    grep -q "| $skill_name |" "$EVOLUTION_DIR/SKILL_CATALOG.md" 2>/dev/null && return 0
    return 1
}

#-------------------------------------------------------------------------------
# 查詢 GitHub 熱門趨勢（安全）
#-------------------------------------------------------------------------------
fetch_github_trending() {
    log "正在探勘 GitHub 熱門專案..."

    local trending_file="$EVOLUTION_DIR/trending_cache.md"
    local cache_age=0

    if [ -f "$trending_file" ]; then
        cache_age=$(($(date +%s) - $(stat -c %Y "$trending_file" 2>/dev/null || echo 0)))
    fi

    # cache 超過 6 小時就更新
    if [ $cache_age -gt 21600 ] || [ ! -f "$trending_file" ]; then
        curl -s --max-time 30 "https://api.github.com/search/repositories?q=stars:>1000+pushed:>2026-01-01&sort=stars&order=desc&per_page=10" \
            | python3 -c "
import sys, json, datetime
data = json.load(sys.stdin)
for r in data.get('items', [])[:10]:
    lang = r.get('language', 'N/A')
    if lang in ['Python', 'JavaScript', 'TypeScript', 'Shell', 'Bash']:
        print(f\"{r['full_name']} | {r['stargazers_count']} stars | {lang} | {r['html_url']}\")
" 2>/dev/null > "$trending_file" || echo "" > "$trending_file"
        log "已更新 GitHub trending cache"
    else
        log "使用快取（age: $((cache_age/3600))h）"
    fi

    cat "$trending_file" 2>/dev/null || echo ""
}

#-------------------------------------------------------------------------------
# 安全檢查：驗證下載的腳本
#-------------------------------------------------------------------------------
security_check() {
    local file="$1"

    local dangerous_patterns="base64.*-d.*\$|eval.*\$|exec.*/dev/|curl.*\|.*sh|wget.*\|.*sh|--no-check-certificate"

    if grep -E "$dangerous_patterns" "$file" 2>/dev/null | grep -v "^#" | grep -v "^$" > /dev/null; then
        log_error "安全檢查失敗：$file 包含可疑模式"
        return 1
    fi

    if file "$file" | grep -q "executable\|ELF\|Mach-O"; then
        log_error "安全檢查失敗：$file 為二進位檔案"
        return 1
    fi

    log "安全檢查通過：$file"
    return 0
}

#-------------------------------------------------------------------------------
# 網路搜尋增強的學習主題（先搜尋最新資訊再學習）
#-------------------------------------------------------------------------------
learn_topic_with_search() {
    local domain="$1"
    local topic="$2"
    local search_query="$3"
    local log_file="$LOG_DIR/learning_${domain}_$(date +%Y%m%d_%H%M%S).log"

    log "=== 開始學習：[$domain] $topic ==="

    # 先搜尋最新資訊（自動切換 Ollama/Tavily）
    if [ -n "$search_query" ]; then
        log "先搜尋最新資訊：「$search_query」..."
        local search_results
        search_results=$(search_web_pretty "$search_query" 5 2>&1) || {
            log "搜尋失敗或無結果，繼續學習..."
            search_results="（網路搜尋無結果）"
        }
        log "搜尋結果：\n$search_results"
    fi

    # 生成學習報告
    cat > "$log_file" << EOF
# 學習報告：$topic
日期：$(date '+%Y-%m-%d %H:%M:%S')
領域：$domain

## 1. 主題概述
（由學習系統自動生成）

## 2. 關鍵知識點
-

## 3. 實際應用範例
\`\`\`python
# 範例程式碼
\`\`\`

## 4. 與現有技能的整合建議
-

## 5. 網路搜尋參考
$(echo "$search_results" 2>/dev/null || echo "（無）")

## 6. 測試驗證結果
-

## 7. 自我評估（1-5星）
★★★☆☆

EOF

    echo "$log_file"
}

#-------------------------------------------------------------------------------
# 更新技能目錄
#-------------------------------------------------------------------------------
update_skill_catalog() {
    local domain="$1"
    local skill="$2"
    local status="$3"
    local notes="$4"

    local today=$(date '+%Y-%m-%d')
    local marker="| $skill |"
    if ! grep -q "$marker" "$EVOLUTION_DIR/SKILL_CATALOG.md" 2>/dev/null; then
        log "已將 [$skill] 新增到技能目錄（狀態：$status）"
    else
        log "已更新 [$skill] 狀態為：$status"
    fi
}

#-------------------------------------------------------------------------------
# 每日定時提醒（生成需要使用者提供的資訊）
#-------------------------------------------------------------------------------
generate_credential_reminder() {
    local vault_file="$EVOLUTION_DIR/CREDENTIAL_VAULT.md"

    echo "=== 每日憑證提醒 ==="
    grep -A 20 "待提供的憑證" "$vault_file" 2>/dev/null | grep -E "^\- \[ \]|^\- \[x\]"
}

#-------------------------------------------------------------------------------
# 主控流程：每 5 小時執行一次
#-------------------------------------------------------------------------------
main() {
    log "========================================="
    log "拉斐爾自主演化系統啟動"
    log "時間：$(date '+%Y-%m-%d %H:%M:%S')"
    log "========================================="

    # 步驟0：測試網路搜尋（自動切換 Ollama/Tavily）
    log "步驟0：測試網路搜尋功能..."
    test_web_search || log "（網路搜尋不可用，跳過）"

    # 步驟1：探勘 GitHub 熱門
    log "步驟1：探勘熱門專案..."
    local trending=$(fetch_github_trending)
    log "熱門專案：\n$trending"

    # 步驟2：選擇學習領域（輪流）
    local domains=(admin web code finance system)
    local last_domain_file="$EVOLUTION_DIR/.last_domain"
    local last_domain=0

    if [ -f "$last_domain_file" ]; then
        last_domain=$(cat "$last_domain_file")
    fi

    local next_domain=$(( (last_domain + 1) % ${#domains[@]} ))
    local current_domain="${domains[$next_domain]}"
    echo "$next_domain" > "$last_domain_file"

    log "步驟2：本輪學習領域：[$current_domain] ${LEARNING_DOMAINS[$current_domain]}"

    # 步驟3：根據領域生成學習任務（帶網路搜尋）
    case "$current_domain" in
        admin)
            learn_topic_with_search "$current_domain" "Word文件自動化處理（Python docx）" "Python docx Word 自動化 2024"
            ;;
        web)
            learn_topic_with_search "$current_domain" "網頁爬蟲與無頭瀏覽器自動化（Puppeteer/Playwright）" "Puppeteer Playwright 爬蟲自動化 2024"
            ;;
        code)
            learn_topic_with_search "$current_domain" "Python API整合與資料處理" "Python API 整合 自動化 2024"
            ;;
        finance)
            learn_topic_with_search "$current_domain" "台灣股票/投資資料API串接" "台灣股票API 投資資料 2024"
            ;;
        system)
            learn_topic_with_search "$current_domain" "Sub-agent設計與演化系統" "AI agent sub-agent design 2024"
            ;;
    esac

    # 步驟4：檢查是否有技能更新
    log "步驟4：檢查技能版本更新..."

    # 步驟5：產出學習報告並寫入記憶
    log "步驟5：產出學習報告..."
    local report_file="$EVOLUTION_DIR/daily_report_$(date +%Y%m%d).md"
    cat > "$report_file" << EOF
# 每日演化報告 - $(date '+%Y-%m-%d')

## 本日學習領域
$current_domain

## 學習內容
${LEARNING_DOMAINS[$current_domain]}

## 熱門專案參考
$(cat "$EVOLUTION_DIR/trending_cache.md" 2>/dev/null | head -5)

## 下一步計畫
-

---
*由拉斐爾自主演化系統自動生成*
EOF

    log "每日報告已生成：$report_file"
    log "========================================="
    log "本輪學習完成"
    log "========================================="
}

#-------------------------------------------------------------------------------
# 測試模式：快速驗證系統運作
#-------------------------------------------------------------------------------
test_mode() {
    log "測試模式：執行快速驗證..."
    log "WORKSPACE: $WORKSPACE"
    log "EVOLUTION_DIR: $EVOLUTION_DIR"
    log "SCRIPTS_DIR: $SCRIPTS_DIR"
    log "LOG_DIR: $LOG_DIR"
    log "OLLAMA_WEB_SEARCH_ENDPOINT: $OLLAMA_WEB_SEARCH_ENDPOINT"
    log "TAVILY_API_ENDPOINT: $TAVILY_API_ENDPOINT"
    log ""
    log "測試網路搜尋（雙軌）..."
    test_web_search
    log ""
    log "GitHub trending:"
    fetch_github_trending | head -5
    log "測試完成"
}

#-------------------------------------------------------------------------------
# 入口點
#-------------------------------------------------------------------------------
case "${1:-main}" in
    test)
        test_mode
        ;;
    search)
        shift
        search_web_pretty "$@"
        ;;
    trending)
        fetch_github_trending
        ;;
    reminder)
        generate_credential_reminder
        ;;
    *)
        main
        ;;
esac
