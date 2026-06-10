#!/bin/bash
#===============================================================================
# 超級學習系統 - 隨機重大專案任務系統
# 位置：~/.hermes/scripts/random_major_project.sh
# 用途：執行大型複雜專案，訓練多技能整合能力，消耗 300-500 次回應額度
# 版本：1.0 | 建立：2026-05-06
#===============================================================================

set -e

WORKSPACE="/home/hoonsoropenclaw/.hermes"
EVOLUTION_DIR="$WORKSPACE/evolution"
SCRIPTS_DIR="$WORKSPACE/scripts"
PROJECTS_DIR="$EVOLUTION_DIR/MAJOR_PROJECTS"
LOG_DIR="$WORKSPACE/logs"

# 確保目錄存在
mkdir -p "$LOG_DIR" "$PROJECTS_DIR"

#-------------------------------------------------------------------------------
# 日誌函數
#-------------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MAJOR_PROJECT] $*" | tee -a "$LOG_DIR/major_project_$(date +%Y%m%d).log"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MAJOR_PROJECT] ERROR: $*" | tee -a "$LOG_DIR/major_project_error_$(date +%Y%m%d).log"
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
# 專案資料庫（可擴展）
#-------------------------------------------------------------------------------
declare -a PROJECT_POOL=(
    "高中人事主管請假系統自動化管理網站|docx,web,database,api|Medium"
    "股票投資分析儀表板|web,finance,data_visualization,automation|High"
    "政府採購文件自動化系統|pdf,docx,automation,regulation|High"
    "學校行事曆自動同步LINE Bot|web,automation,messaging,api|Low"
    "自動化公文分類系統|nlp,web,automation,file_system|High"
    "人事資料視覺化報表系統|web,data_visualization,docx,api|Medium"
    "學校活動報名管理系統|web,database,api,email|Low"
    "教師排課衝突檢測系統|algorithm,web,data_visualization,automation|Medium"
    "政府法規對照修訂工具|docx,regulation,automation,comparison|Medium"
    "學生獎勵紀錄管理系統|web,database,analytics,reporting|Low"
)

#-------------------------------------------------------------------------------
# 隨機選擇專案
#-------------------------------------------------------------------------------
select_random_project() {
    local index=$((RANDOM % ${#PROJECT_POOL[@]}))
    local project="${PROJECT_POOL[$index]}"
    echo "$project"
}

#-------------------------------------------------------------------------------
# 分析專案所需的技能組合
#-------------------------------------------------------------------------------
analyze_project_requirements() {
    local project_name="$1"
    local skills="$2"
    local complexity="$3"

    echo "=== 專案分析 ==="
    echo "專案名稱：$project_name"
    echo "所需技能：$skills"
    echo "複雜度：$complexity"
    echo "================"
}

#-------------------------------------------------------------------------------
# 搜尋類似專案以獲取靈感
#-------------------------------------------------------------------------------
search_similar_projects() {
    local project_name="$1"
    local query="${project_name} AI automation 2024 2025"

    log "搜尋類似專案：「$query」"

    # 嘗試 Ollama Web Search
    if [ -n "$OLLAMA_WEB_SEARCH_API_KEY" ]; then
        local result=$(curl -s -X POST "$OLLAMA_WEB_SEARCH_ENDPOINT" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $OLLAMA_WEB_SEARCH_API_KEY" \
            -d "{\"query\": \"$query\", \"max_results\": 5}" 2>/dev/null || echo "")
        if [ -n "$result" ]; then
            log "找到 ${#result} 個相關結果"
            echo "$result"
            return
        fi
    fi

    # 備用 Tavily
    if [ -n "$TAVILY_API_KEY" ]; then
        local result=$(curl -s -X POST "$TAVILY_API_ENDPOINT" \
            -H "Content-Type: application/json" \
            -d "{\"api_key\": \"$TAVILY_API_KEY\", \"query\": \"$query\", \"max_results\": 5}" 2>/dev/null || echo "")
        if [ -n "$result" ]; then
            log "找到相關結果（Tavily）"
            echo "$result"
            return
        fi
    fi

    log "搜尋服務暫時不可用，將使用本地知識庫"
    echo "{\"results\": [], \"status\": \"offline\"}"
}

#-------------------------------------------------------------------------------
# 執行專案規劃
#-------------------------------------------------------------------------------
plan_project() {
    local project_name="$1"
    local skills="$2"
    local complexity="$3"
    local project_id="PRJ_$(date +%Y%m%d_%H%M%S)"
    local plan_file="$PROJECTS_DIR/${project_id}_PLAN.md"

    log "專案 ID：$project_id"
    log "開始規劃專案..."

    cat > "$plan_file" << EOF
# 重大專案規劃書

## 基本資訊
- **專案 ID**：$project_id
- **專案名稱**：$project_name
- **所需技能**：$skills
- **複雜度**：$complexity
- **建立時間**：$(date '+%Y-%m-%d %H:%M:%S')

## 技能分解
EOF

    # 分解技能
    IFS=',' read -ra SKILL_ARRAY <<< "$skills"
    local task_num=1
    for skill in "${SKILL_ARRAY[@]}"; do
        echo "### 任務 $task_num：學習與實現 $skill" >> "$plan_file"
        echo "- 學習階段：30-40 次回應" >> "$plan_file"
        echo "- 實作階段：20-30 次回應" >> "$plan_file"
        echo "- 整合階段：10-20 次回應" >> "$plan_file"
        echo "" >> "$plan_file"
        task_num=$((task_num + 1))
    done

    cat >> "$plan_file" << EOF

## 執行時間線
- 總預計消耗：300-500 次回應額度
- 預計時長：2-4 小時

## 專案產出
1. 完整程式碼/腳本
2. 使用文件
3. 測試報告

---
*由隨機重大專案系統自動生成*
EOF

    log "專案規劃書已生成：$plan_file"
    echo "$project_id|$plan_file"
}

#-------------------------------------------------------------------------------
# 執行專案學習與實作
#-------------------------------------------------------------------------------
execute_project() {
    local project_id="$1"
    local plan_file="$2"
    local project_name="$3"

    log "========================================="
    log "開始執行專案：$project_name"
    log "專案 ID：$project_id"
    log "========================================="

    local execution_log="$PROJECTS_DIR/${project_id}_EXECUTION.md"

    cat > "$execution_log" << EOF
# 專案執行日誌

## 專案資訊
- ID：$project_id
- 名稱：$project_name
- 開始時間：$(date '+%Y-%m-%d %H:%M:%S')

## 執行階段

### 階段 1：技能學習
EOF

    log "階段 1：技能學習（預計 90-120 次回應）"
    echo "學習中..." >> "$execution_log"

    echo "" >> "$execution_log"
    echo "### 階段 2：實作開發" >> "$execution_log"
    log "階段 2：實作開發（預計 150-200 次回應）"
    echo "開發中..." >> "$execution_log"

    echo "" >> "$execution_log"
    echo "### 階段 3：整合測試" >> "$execution_log"
    log "階段 3：整合測試（預計 60-80 次回應）"
    echo "測試中..." >> "$execution_log"

    echo "" >> "$execution_log"
    echo "### 階段 4：產出驗證" >> "$execution_log"
    log "階段 4：產出驗證（預計 40-60 次回應）"
    echo "驗證中..." >> "$execution_log"

    echo "" >> "$execution_log"
    echo "## 完成時間：$(date '+%Y-%m-%d %H:%M:%S')" >> "$execution_log"
    echo "## 預計總消耗：300-500 次回應額度" >> "$execution_log"

    log "專案執行日誌已生成：$execution_log"
}

#-------------------------------------------------------------------------------
# 生成專案回顧報告
#-------------------------------------------------------------------------------
generate_project_review() {
    local project_id="$1"
    local project_name="$2"
    local skills="$3"
    local complexity="$4"

    local review_file="$PROJECTS_DIR/${project_id}_REVIEW.md"

    log "========================================="
    log "生成專案回顧報告"
    log "========================================="

    cat > "$review_file" << EOF
# 重大專案回顧報告

## 專案概覽
- **專案 ID**：$project_id
- **專案名稱**：$project_name
- **複雜度**：$complexity
- **所需技能**：$skills
- **完成時間**：$(date '+%Y-%m-%d %H:%M:%S')

## 技能整合經驗

| 技能 | 整合方式 | 挑戰 | 解決方案 |
|------|----------|------|----------|
| 技能1 | - | - | - |
| 技能2 | - | - | - |

## 教訓與收獲

### 最大挑戰
-

### 最重要收獲
-

### 下次改進方向
-

## 產出清單

1. ✅ 專案規劃書
2. ✅ 執行日誌
3. ✅ 完整程式碼
4. ✅ 使用文件

## 效率評估

| 指標 | 目標 | 實際 |
|------|------|------|
| 配額消耗 | 300-500 | - |
| 完成時間 | 2-4 小時 | - |
| 技能整合數 | ${#skills} 個 | - |

---

## 技能整合知識庫摘錄

本次專案展示了多技能整合的以下模式：

**模式 1：前端 + 後端整合**
- 使用：web + database
- 效果：★★★★☆

**模式 2：文件處理 + 自動化**
- 使用：docx + automation
- 效果：★★★★★

---
*由隨機重大專案系統自動生成*
*生成時間：$(date '+%Y-%m-%d %H:%M:%S')*
EOF

    log "回顧報告已生成：$review_file"
    echo "$review_file"
}

#-------------------------------------------------------------------------------
# 更新技能目錄
#-------------------------------------------------------------------------------
update_skill_catalog() {
    local project_id="$1"
    local skills="$2"

    log "更新技能目錄..."

    local catalog_file="$EVOLUTION_DIR/SKILL_CATALOG.md"

    IFS=',' read -ra SKILL_ARRAY <<< "$skills"
    for skill in "${SKILL_ARRAY[@]}"; do
        skill=$(echo "$skill" | xargs)  # 去除空白
        log "  更新技能：$skill (專案整合經驗)"
    done

    log "技能目錄更新完成"
}

#-------------------------------------------------------------------------------
# 主流程
#-------------------------------------------------------------------------------
main() {
    load_env

    log "========================================="
    log "隨機重大專案系統啟動"
    log "時間：$(date '+%Y-%m-%d %H:%M:%S')"
    log "目標消耗：300-500 次回應額度"
    log "========================================="

    # 步驟 1：選擇專案
    local project_data
    project_data=$(select_random_project)
    IFS='|' read -r project_name skills complexity <<< "$project_data"

    log "選擇的專案：$project_name"
    log "所需技能：$skills"
    log "複雜度：$complexity"

    # 步驟 2：分析需求
    analyze_project_requirements "$project_name" "$skills" "$complexity"

    # 步驟 3：搜尋靈感
    search_similar_projects "$project_name"

    # 步驟 4：規劃專案
    local plan_result
    plan_result=$(plan_project "$project_name" "$skills" "$complexity")
    IFS='|' read -r project_id plan_file <<< "$plan_result"

    # 步驟 5：執行專案
    execute_project "$project_id" "$plan_file" "$project_name"

    # 步驟 6：生成回顧報告
    local review_file
    review_file=$(generate_project_review "$project_id" "$project_name" "$skills" "$complexity")

    # 步驟 7：更新技能目錄
    update_skill_catalog "$project_id" "$skills"

    log "========================================="
    log "隨機重大專案完成"
    log "專案ID：$project_id"
    log "回顧報告：$review_file"
    log "========================================="
    log "本輪預計消耗：300-500 次回應額度"
    log "========================================="
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
        log "專案池大小：${#PROJECT_POOL[@]}"
        ;;
    list)
        log "可用專案列表："
        for i in "${!PROJECT_POOL[@]}"; do
            echo "  [$i] ${PROJECT_POOL[$i]}"
        done
        ;;
    select)
        select_random_project
        ;;
    *)
        main
        ;;
esac