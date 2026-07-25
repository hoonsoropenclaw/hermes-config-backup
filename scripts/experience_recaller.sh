#!/bin/bash
# ==============================================
# experience_recaller.sh - 經驗自動召回觸發
# 功能：根據任務關鍵字，從 EXPERIENCE.md 召回相關的 If→Then 經驗
#       輸出給 subagent 作為額外 context注入
# 使用：./experience_recaller.sh "bulk import 停了"
# 建立：2026-05-25
# ==============================================

set -euo pipefail

EXPERIENCE_FILE="/home/hoonsoropenclaw/.hermes/evolution/EXPERIENCE.md"
OUTPUT_FILE="/tmp/recalled_experience.txt"

# 預設閾值
MIN_SCORE=0.3

usage() {
    echo "Usage: $0 <keywords> [--score N]"
    echo "  keywords  : 搜尋關鍵字（多個以空白分隔，會自動用 + 連接成 AND 搜尋）"
    echo "  --score N : 最小相似度分數（0-1，預設 0.3）"
    echo ""
    echo "Example:"
    echo "  $0 \"bulk import queue\""
    echo "  $0 \"crud localStorage\" --score 0.5"
    exit 1
}

# 解析參數
if [[ $# -lt 1 ]]; then
    usage
fi

KEYWORDS=""
SCORE="$MIN_SCORE"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --score)
            SCORE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "$KEYWORDS" ]]; then
                KEYWORDS="$1"
            else
                KEYWORDS="$KEYWORDS $1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$KEYWORDS" ]]; then
    usage
fi

# 讀取 EXPERIENCE.md 並根據關鍵字召回相關章節
recall_experience() {
    local keywords="$1"
    local content
    
    if [[ ! -f "$EXPERIENCE_FILE" ]]; then
        echo "WARNING: EXPERIENCE.md not found at $EXPERIENCE_FILE" >&2
        return 1
    fi
    
    content=$(cat "$EXPERIENCE_FILE")
    
    # 轉換關鍵字為大寫（用於簡單匹配）
    local upper_keywords
    upper_keywords=$(echo "$keywords" | tr '[:lower:]' '[:upper:]')
    
    # 提取章節標題（用於識別不同的模式）
    local sections
    sections=$(echo "$content" | grep -E "^##? (模式|[A-Z][a-z]|.*模式)" | head -20)
    
    # 簡單關鍵字匹配：如果關鍵字出現在內容中，就提取該區塊
    # 由於是 bash script，我們用 grep 找相關內容
    local matched_content=""
    
    # 拆解關鍵字為個別詞
    for keyword in $keywords; do
        # 找包含這個關鍵字的行
        local relevant_lines
        relevant_lines=$(echo "$content" | grep -i -B2 -A5 "$keyword" | head -100 || true)
        
        if [[ -n "$relevant_lines" ]]; then
            matched_content="$matched_content

#### 關鍵字「$keyword」的相關內容：

$relevant_lines

"
        fi
    done
    
    if [[ -z "$matched_content" ]]; then
        echo "# 無相關經驗召回（關鍵字：$keywords）"
        echo ""
        echo "⚠️ 沒有在 EXPERIENCE.md 中找到與「$keywords」相關的內容。"
        echo "可能需要："
        echo "  1. 檢查 EXPERIENCE.md 是否存在"
        echo "  2. 嘗試不同的關鍵字"
        echo "  3. 如果是新領域，考慮建立新的經驗記錄"
        return 0
    fi
    
    # 輸出召回的經驗
    cat << EOF
# 🔄 從經驗庫召回的相關內容（關鍵字：$keywords）

$matched_content

---
EOF

}

# 主程式
main() {
    echo "召回經驗中... 關鍵字：$KEYWORDS"
    
    # 執行召回並寫入輸出檔
    recall_experience "$KEYWORDS" | tee "$OUTPUT_FILE"
    
    echo ""
    echo "✅ 已召回相關經驗，輸出至：$OUTPUT_FILE"
}

main "$@"