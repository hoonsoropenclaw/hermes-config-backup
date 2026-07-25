#!/bin/bash
#===============================================================================
# 拉斐爾網路搜尋工具 - Ollama Web Search API 包裝
# 位置：~/.hermes/scripts/ollama_web_search.sh
# 用途：整合 Ollama Web Search API 到演化系統
#===============================================================================

# 讀取 API 設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
EVOLUTION_DIR="$WORKSPACE_DIR/evolution"

if [ -f "$EVOLUTION_DIR/.env.ollama" ]; then
    source "$EVOLUTION_DIR/.env.ollama"
fi

OLLAMA_API_KEY="${OLLAMA_WEB_SEARCH_API_KEY:-6bfcfaaf3ddd4b8785d20402589d38c2.xQObO0l_5yBtaOARqnwESdau}"
OLLAMA_ENDPOINT="${OLLAMA_WEB_SEARCH_ENDPOINT:-https://ollama.com/api/web_search}"
MAX_RESULTS="${OLLAMA_WEB_SEARCH_MAX_RESULTS:-5}"

#-------------------------------------------------------------------------------
# 執行網路搜尋
# Usage: ollama_web_search "搜尋關鍵字" [max_results]
# Output: JSON array of results
#-------------------------------------------------------------------------------
ollama_web_search() {
    local query="$1"
    local max_results="${2:-$MAX_RESULTS}"
    
    if [ -z "$query" ]; then
        echo "Error: query is required" >&2
        return 1
    fi
    
    local response
    response=$(curl -s -X POST "$OLLAMA_ENDPOINT" \
        -H "Authorization: Bearer $OLLAMA_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"$query\",\"max_results\":$max_results}" \
        --max-time 30 2>&1)
    
    if [ $? -ne 0 ]; then
        echo "Error: curl failed" >&2
        return 1
    fi
    
    # 檢查是否為有效的 JSON
    if echo "$response" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "$response"
        return 0
    else
        echo "Error: invalid response from Ollama API" >&2
        echo "$response" >&2
        return 1
    fi
}

#-------------------------------------------------------------------------------
# 執行網路搜尋（格式化輸出）
#-------------------------------------------------------------------------------
ollama_web_search_pretty() {
    local query="$1"
    local max_results="${2:-$MAX_RESULTS}"
    
    local json_result
    json_result=$(ollama_web_search "$query" "$max_results") || return 1
    
    echo "$json_result" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    
    if not results:
        print('No results found.')
        return
    
    print(f'找到 {len(results)} 個結果：\n')
    for i, r in enumerate(results, 1):
        title = r.get('title', 'N/A')
        url = r.get('url', 'N/A')
        content = r.get('content', '')[:200]
        print(f'--- 結果 {i} ---')
        print(f'標題：{title}')
        print(f'網址：{url}')
        print(f'摘要：{content}...')
        print()
except Exception as e:
    print(f'Parse error: {e}')
    import sys
    sys.stdin.seek(0)
    print(sys.stdin.read()[:500])
" 2>/dev/null
}

#-------------------------------------------------------------------------------
# 主入口點
#-------------------------------------------------------------------------------
case "${1:-search}" in
    search)
        ollama_web_search "$2" "${3:-5}"
        ;;
    pretty)
        ollama_web_search_pretty "$2" "${3:-5}"
        ;;
    test)
        echo "Testing Ollama Web Search API..."
        ollama_web_search_pretty "OpenClaw AI assistant" 3
        ;;
    *)
        echo "Usage: $0 {search|pretty|test} \"query\" [max_results]"
        echo "  search  - Raw JSON output"
        echo "  pretty  - Formatted output"
        echo "  test    - Test with default query"
        ;;
esac
