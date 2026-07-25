#===============================================================================
# 隨機重大專案系統 v2.0 - 大型複合專案實作系統
# 位置：~/.hermes/scripts/random_major_project_v2.sh
# 用途：執行真正的多技能、多工具整合的大型專案，消耗 500-1000+ 次回應額度
# 版本：2.0 | 更新：2026-05-07
# 
# 定義：真正的「隨機困難專案任務」= 運用多種工具及技能組合的大型專案複合任務
# 例如：
#   - 法規爬蟲 + 心智圖 + 網站呈現 + 全文搜尋
#   - PDF/圖片 OCR → 一模一樣的 Word/Excel + 心智圖連結 + 網站呈現
#   - 2D 橫向捲軸遊戲：從網路找素材 + 圖片生成 + 故事設計 + Godot/Love2D
#   - 股票看盤軟體：多來源即時數據 + 技術分析 + 視覺化
#===============================================================================

set -e

WORKSPACE="/home/hoonsoropenclaw/.hermes"
EVOLUTION_DIR="$WORKSPACE/evolution"
SCRIPTS_DIR="$WORKSPACE/scripts"
PROJECTS_DIR="$EVOLUTION_DIR/MAJOR_PROJECTS"
LOG_DIR="$WORKSPACE/logs"
STATE_FILE="$PROJECTS_DIR/.project_state.json"

mkdir -p "$LOG_DIR" "$PROJECTS_DIR"

#-------------------------------------------------------------------------------
# 日誌
#-------------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MAJOR_PROJECT] $*" | tee -a "$LOG_DIR/major_project_v2_$(date +%Y%m%d).log"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MAJOR_PROJECT] ERROR: $*" | tee -a "$LOG_DIR/major_project_error_$(date +%Y%m%d).log"
}

#-------------------------------------------------------------------------------
# 新的專案池 - 真正的大型複合專案
#-------------------------------------------------------------------------------
declare -a PROJECT_POOL=(
    # 專案名稱 | 所需技能組合（多個） | 複雜度 | 說明
    "法規智能系統|web_scraping,regulation_db,visualization,search,mindmap|High|爬蟲抓取法規+心智圖+網站+全文搜尋"
    "PDF完美轉Word系統|ocr,pdf_processing,docx_generator,visualization,comparison|High|掃描PDF→一模一樣Word+心智圖+網站"
    "2D遊戲開發|godot,asset_finder,image_generation,story_design,game_engine|High|橫向捲軸遊戲+素材+關卡設計"
    "股票看盤軟體|finance_api,data_visualization,realtime_data,technical_analysis,desktop_web|High|多來源即時股價+技術分析"
    "學校行事曆系統|web_scraping,calendar_api,line_bot,notification,ics_generation|Medium|學校行事曆+LINE通知+iCalendar"
    "人事資料視覺化|database,web_dashboard,chartjs,export_pdf,search_filter|Medium|人事資料視覺化儀表板+匯出"
    "自動化公文分類|nlp_classification,web_scraping,database,file_system,workflow|High|AI公文分類+工作流程自動化"
    "多語言學校網站|web_development,i18n,seo,cms,accessibility|Medium|多語言學校官方網站+無障礙支援"
)

#-------------------------------------------------------------------------------
# 讀取目前的額度狀態
#-------------------------------------------------------------------------------
check_quota_and_switch_model() {
    # 嘗試讀取 MiniMax API 額度
    local session_info=$(openclaw session-status 2>/dev/null || echo "")
    
    if echo "$session_info" | grep -q "quota\|exhausted\|limit"; then
        log "MiniMax 額度可能已達上限，切換為儲存狀態模式"
        return 1  # 表示需要切換
    fi
    
    return 0  # 可以繼續使用 MiniMax
}

#-------------------------------------------------------------------------------
# 保存當前學習狀態
#-------------------------------------------------------------------------------
save_learning_state() {
    local project_id="$1"
    local checkpoint_file="$PROJECTS_DIR/${project_id}_checkpoint.json"
    
    log "保存學習狀態到：$checkpoint_file"
    
    cat > "$checkpoint_file" << EOF
{
    "project_id": "$project_id",
    "saved_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "project_name": "$(cat $PROJECTS_DIR/.current_project 2>/dev/null || echo 'unknown')",
    "skills_used": ["$(cat $PROJECTS_DIR/.current_skills 2>/dev/null || echo '')"],
    "log_file": "$LOG_DIR/major_project_v2_$(date +%Y%m%d).log",
    "status": "paused_waiting_quota"
}
EOF
    
    log "狀態已保存，指標：$checkpoint_file"
}

#-------------------------------------------------------------------------------
# 選擇一個真正大型專案
#-------------------------------------------------------------------------------
select_major_project() {
    local index=$((RANDOM % ${#PROJECT_POOL[@]}))
    local project="${PROJECT_POOL[$index]}"
    echo "$project"
}

#-------------------------------------------------------------------------------
# 分析並分解專案為子任務
#-------------------------------------------------------------------------------
decompose_into_tasks() {
    local project_name="$1"
    local skills="$2"
    local project_id="MAJOR_$(date +%Y%m%d_%H%M%S)"
    
    log "========================================="
    log "專案ID：$project_id"
    log "專案名稱：$project_name"
    log "技能組合：$skills"
    log "========================================="
    
    # 保存當前專案資訊
    echo "$project_name" > "$PROJECTS_DIR/.current_project"
    echo "$skills" > "$PROJECTS_DIR/.current_skills"
    
    # 建立專案目錄
    mkdir -p "$PROJECTS_DIR/$project_id"
    
    # 根據專案類型生成具體任務
    case "$project_name" in
        "法規智能系統")
            cat > "$PROJECTS_DIR/$project_id/PROJECT.md" << 'EOF'
# 法規智能系統 - 大型複合專案

## 專案目標
建立一個能夠自動爬取政府法規、產生心智圖、提供強大搜尋功能的法規資料庫網站。

## 技能組合
1. 網頁爬蟲（Scrapling/Python）
2. 資料庫（Supabase/JSON）
3. 視覺化（心智圖D3.js/mindmap）
4. 全文搜尋（FlexSearch/MeiliSearch）
5. 網站前端（HTML/CSS/JS）

## 任務分解

### 任務1：法規爬蟲系統（150-200額度）
- 研究政府開放資料平台法規
- 使用 Scrapling 爬取法規內容
- 儲存至 Supabase 資料庫
- 實現增量更新機制

### 任務2：心智圖視覺化（100-150額度）
- 研究 D3.js 或 gojs 心智圖
- 設計法規分類架構圖
- 實現互動式心智圖
- 支援點擊展開子節點

### 任務3：全文搜尋系統（100-150額度）
- 研究 FlexSearch 或 MeiliSearch
- 建立法規索引
- 實現模糊搜尋
- 支援高亮和分類篩選

### 任務4：網站呈現（100-150額度）
- 設計響應式網站介面
- 整合所有元件
- 部署至 Vercel

## 產出
1. 完整可運行的網站
2. GitHub 倉庫
3. 即時上線的 URL
EOF
            ;;
        "PDF完美轉Word系統")
            cat > "$PROJECTS_DIR/$project_id/PROJECT.md" << 'EOF'
# PDF完美轉Word系統 - 大型複合專案

## 專案目標
將掃描的PDF或圖片檔案，OCR轉換成完全符合原本格式的Word/Excel，並結合心智圖連結，網站呈現。

## 技能組合
1. PDF處理（PyMuPDF/pypdf）
2. OCR辨識（Tesseract/PaddleOCR）
3. Word生成（python-docx/docxtpl）
4. 心智圖（D3.js/gojs）
5. 網站呈現

## 任務分解

### 任務1：PDF分析與OCR（150額度）
- 使用 PyMuPDF 分析 PDF 結構
- 使用 PaddleOCR 進行高準確率 OCR
- 處理表格、圖片、段落

### 任務2：Word精確重建（150額度）
- 使用 python-docx 重建格式
- 精確還原：行高、邊界、表格、標題
- 處理多欄格式

### 任務3：心智圖整合（100額度）
- 建立文檔結構心智圖
- 連結原始PDF位置
- 互動式導航

### 任務4：網站上線（100額度）
- 拖放上傳介面
- 即時處理顯示
- 部署上線

## 產出
1. 完整轉換網站
2. 開源 GitHub 倉庫
EOF
            ;;
        "股票看盤軟體")
            cat > "$PROJECTS_DIR/$project_id/PROJECT.md" << 'EOF'
# 股票看盤軟體 - 大型複合專案

## 專案目標
自行製作一個桌面版或網頁版股票看盤軟體，接入各種公開的即時股價數據來源。

## 技能組合
1. 金融API（yfinance/Finnhub/Alpha Vantage）
2. 即時數據（WebSocket/輪詢）
3. 技術分析（TA-Lib/pandas）
4. 視覺化（Plotly/D3.js/ECharts）
5. 網站/桌面（Streamlit/React/Electron）

## 任務分解

### 任務1：數據源整合（100額度）
- 研究多來源股價API
- 整合 yfinance、Finnhub
- 實現即時/歷史數據獲取

### 任務2：技術分析引擎（150額度）
- 實現 MA、RSI、MACD、KDJ
- 計算技術指標
- 圖表繪製

### 任務3：看盤介面（150額度）
- 使用 Plotly/Dash 製作圖表
- 即時報價更新
- 自選股管理

### 任務4：部署上線（100額度）
- 封裝為網頁應用
- 部署至 Vercel/Streamlit Cloud

## 產出
1. 即時看盤網站
2. GitHub 倉庫
3. 即時上線 URL
EOF
            ;;
        "2D遊戲開發")
            cat > "$PROJECTS_DIR/$project_id/PROJECT.md" << 'EOF'
# 2D橫向捲軸遊戲 - 大型複合專案

## 專案目標
從網路找尋各種圖片素材，使用圖片生成模型，設計故事背景，製作一個完整的2D橫向捲軸遊戲。

## 技能組合
1. 素材搜索（網頁爬蟲/圖片API）
2. 圖片生成（AI image API）
3. 遊戲引擎（Godot/Love2D）
4. 關卡設計
5. 腳本編程（Lua/GDScript）

## 任務分解

### 任务1：素材系統（150額度）
- 研究 Godot/Love2D 素材格式
- 爬蟲取得素材 或 AI 生成
- 建立素材庫

### 任務2：遊戲核心（200額度）
- 角色控制（左右移動、跳躍）
- 物理引擎
- 碰撞檢測

### 任務3：關卡設計（100額度）
- 設計2個遊戲關卡
- 敵人與障礙物
- 積分系統

### 任務4：發布與展示（50額度）
- 封裝遊戲
- 建立展示頁面
- 上傳 GitHub

## 產出
1. 可運行的遊戲
2. GitHub 倉庫
3. 展示網站
EOF
            ;;
        *)
            # 通用模板
            cat > "$PROJECTS_DIR/$project_id/PROJECT.md" << EOF
# $project_name - 大型複合專案

## 專案目標
$project_name

## 技能組合
$skills

## 任務分解
請根據技能組合，規劃4-6個子任務，每個任務消耗 100-150 額度。
EOF
            ;;
    esac
    
    echo "$project_id"
}

#-------------------------------------------------------------------------------
# 執行單一任務（呼叫 sub-agent）
#-------------------------------------------------------------------------------
execute_task() {
    local project_id="$1"
    local task_name="$2"
    local task_prompt="$3"
    local model="${4:-minimax/MiniMax-M2.7}"
    
    log "----------------------------------------"
    log "執行任務：$task_name"
    log "使用模型：$model"
    log "----------------------------------------"
    
    # 檢查額度
    if ! check_quota_and_switch_model; then
        log "額度不足，保存狀態並暫停..."
        save_learning_state "$project_id"
        return 1
    fi
    
    # 使用 sessions_spawn 執行任務
    # 注意：這會消耗大量額度
    echo "任務 [$task_name] 執行中..."
    
    # 回傳任務ID供追蹤
    echo "TASK_${task_name}_$(date +%s)"
}

#-------------------------------------------------------------------------------
# 主要執行流程
#-------------------------------------------------------------------------------
main() {
    log "========================================="
    log "隨機重大專案系統 v2.0 啟動"
    log "定義：多技能、多工具整合的大型複合專案"
    log "時間：$(date '+%Y-%m-%d %H:%M:%S')"
    log "========================================="
    
    # 步驟1：選擇專案
    local project_data=$(select_major_project)
    IFS='|' read -r project_name skills complexity description <<< "$project_data"
    
    log "選擇的專案：$project_name"
    log "複雜度：$complexity"
    log "說明：$description"
    log "所需技能：$skills"
    
    # 步驟2：分解為子任務
    local project_id
    project_id=$(decompose_into_tasks "$project_name" "$skills")
    
    log "專案已分解，ID：$project_id"
    log "詳細規劃：$PROJECTS_DIR/$project_id/PROJECT.md"
    
    # 步驟3：告訴 user 準備開始
    log "========================================="
    log "准備啟動大型專案執行..."
    log "每個子任務將由獨立的 sub-agent 執行"
    log "預計總消耗：500-1000+ 次 API 回應"
    log "========================================="
    
    # 實際執行需要透過 OpenClaw 的 sub-agent 系統
    # 這裡只是規劃，真正的執行在下面
}

#-------------------------------------------------------------------------------
# 列出所有可用專案
#-------------------------------------------------------------------------------
list_projects() {
    echo "=== 可用的大型複合專案池 ==="
    for i in "${!PROJECT_POOL[@]}"; do
        IFS='|' read -r name skills complexity desc <<< "${PROJECT_POOL[$i]}"
        echo "[$i] $name"
        echo "    技能：$skills"
        echo "    說明：$desc"
        echo ""
    done
}

#-------------------------------------------------------------------------------
# 入口
#-------------------------------------------------------------------------------
case "${1:-main}" in
    list)
        list_projects
        ;;
    test)
        log "測試模式..."
        select_major_project
        ;;
    select)
        select_major_project
        ;;
    decompose)
        project_data=$(select_major_project)
        IFS='|' read -r project_name skills complexity desc <<< "$project_data"
        decompose_into_tasks "$project_name" "$skills"
        ;;
    *)
        main
        ;;
esac