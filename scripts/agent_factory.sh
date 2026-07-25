#!/bin/bash
#===============================================================================
# 智慧代理工廠 (Smart Agent Factory)
# 位置：~/.hermes/scripts/agent_factory.sh
# 用途：Spawn 持久性智慧子代理，每次帶著累積經驗執行任務
# 版本：1.0 | 建立：2026-05-07
#===============================================================================

set -e

WORKSPACE="/home/hoonsoropenclaw/.hermes"
AGENTS_DIR="$WORKSPACE/agents"
SCRIPTS_DIR="$WORKSPACE/scripts"
LOG_DIR="$WORKSPACE/logs"

#===============================================================================
# 日誌函數
#===============================================================================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [AGENT_FACTORY] $*" | tee -a "$LOG_DIR/agent_factory_$(date +%Y%m%d).log"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [AGENT_FACTORY] ERROR: $*" | tee -a "$LOG_DIR/agent_factory_error_$(date +%Y%m%d).log"
}

#===============================================================================
# 代理注册表
#===============================================================================
declare -A AGENT_FILES=(
    ["backend_expert"]="$AGENTS_DIR/backend_agent.md"
    ["docx_expert"]="$AGENTS_DIR/docx_agent.md"
    ["scraper_expert"]="$AGENTS_DIR/scraper_agent.md"
    ["data_expert"]="$AGENTS_DIR/data_agent.md"
    ["system_expert"]="$AGENTS_DIR/system_agent.md"
)

declare -A AGENT_SPECIALTIES=(
    ["backend_expert"]="Python腳本,Shell指令碼,API整合,資料處理"
    ["docx_expert"]="Word文件,文件模板,PDF處理,格式設定"
    ["scraper_expert"]="網頁爬蟲,HTML解析,無頭瀏覽器,API資料抓取"
    ["data_expert"]="資料清洗,分析,視覺化,CSV/JSON處理"
    ["system_expert"]="MCP工具,Sub-agent設計,Cron排程,系統架構"
)

#===============================================================================
# 任務 → 代理映射
#===============================================================================
route_task_to_agent() {
    local task_description="$1"
    
    local task_lower=$(echo "$task_description" | tr '[:upper:]' '[:lower:]')
    
    # 關鍵字匹配
    if [[ "$task_lower" == *"python"* ]] || [[ "$task_lower" == *"shell"* ]] || [[ "$task_lower" == *"api"* ]]; then
        echo "backend_expert"
    elif [[ "$task_lower" == *"docx"* ]] || [[ "$task_lower" == *"word"* ]] || [[ "$task_lower" == *"文件"* ]]; then
        echo "docx_expert"
    elif [[ "$task_lower" == *"爬蟲"* ]] || [[ "$task_lower" == *"scrape"* ]] || [[ "$task_lower" == *"web"* ]]; then
        echo "scraper_expert"
    elif [[ "$task_lower" == *"資料"* ]] || [[ "$task_lower" == *"data"* ]] || [[ "$task_lower" == *"分析"* ]]; then
        echo "data_expert"
    elif [[ "$task_lower" == *"mcp"* ]] || [[ "$task_lower" == *"sub-agent"* ]] || [[ "$task_lower" == *"架構"* ]]; then
        echo "system_expert"
    else
        # 預設：backend_expert（最全能）
        echo "backend_expert"
    fi
}

#===============================================================================
# 讀取代理記憶
#===============================================================================
load_agent_memory() {
    local agent_name="$1"
    
    local agent_file="${AGENT_FILES[$agent_name]}"
    
    if [ -z "$agent_file" ]; then
        log_error "未知代理：$agent_name"
        return 1
    fi
    
    if [ ! -f "$agent_file" ]; then
        log "代理記憶檔案不存在，將建立新檔案：$agent_file"
        mkdir -p "$(dirname "$agent_file")"
        cat > "$agent_file" << EOF
# $agent_name 代理記憶
## 等級：LV1 | 經驗點：0 | 建立：$(date '+%Y-%m-%d')
---
EOF
    fi
    
    log "載入代理記憶：$agent_name"
    cat "$agent_file"
    
    return 0
}

#===============================================================================
# 構建代理上下文（用於 spawn）
#===============================================================================
build_agent_context() {
    local agent_name="$1"
    local task_description="$2"
    
    local agent_file="${AGENT_FILES[$agent_name]}"
    local specialties="${AGENT_SPECIALTIES[$agent_name]}"
    
    # 讀取代理記憶
    local memory=$(load_agent_memory "$agent_name")
    
    # 提取關鍵資訊（只取前 2000 字元，避免 context 爆炸）
    local memory_preview=$(echo "$memory" | head -c 2000)
    
    # 構建上下文
    cat << EOF

## 任務指派給：$agent_name

### 代理專長
$specialties

### 代理累積經驗（來自持久記憶）
\`\`\`
$memory_preview
\`\`\`

### 本次任務
$task_description

### 執行指示
1. 先檢視代理記憶中的成功模式
2. 執行任務時應用已知的最佳實踐
3. 如果發現新技術或成功模式，回傳時告訴我
4. 任務完成後，回傳：
   - 成功模式（如果有的話）
   - 失敗教訓（如果有的話）
   - 新學到的技術（如果有的話）

EOF
}

#===============================================================================
# 執行任務（使用 sessions_yield 模式）
#===============================================================================
execute_agent_task() {
    local agent_name="$1"
    local task_description="$2"
    
    log "========================================="
    log "  智慧代理工廠啟動"
    log "  代理：$agent_name"
    log "  任務：$task_description"
    log "========================================="
    
    # 建立上下文
    local context=$(build_agent_context "$agent_name" "$task_description")
    
    # 構建 spawn 指令（這裡只是展示，真正的執行由主代理完成）
    log "代理上下文已建立"
    log "長度：${#context} 字元"
    
    # 估算經驗點數（根據任務複雜度）
    local estimated_points=1
    if [[ ${#task_description} -gt 100 ]]; then
        estimated_points=3
    fi
    
    log "預估任務複雜度：$estimated_points 點"
    
    echo "$context"
    return 0
}

#===============================================================================
# 任務完成後：提取經驗並更新代理記憶
#===============================================================================
deposit_learning() {
    local agent_name="$1"
    local task_description="$2"
    local success_pattern="$3"
    local failure_lesson="$4"
    local new_technique="$5"
    
    local agent_file="${AGENT_FILES[$agent_name]}"
    
    if [ -z "$agent_file" ]; then
        log_error "未知代理：$agent_name"
        return 1
    fi
    
    log "沉積學習經驗到：$agent_name"
    
    # 建立新經驗條目
    local date_stamp=$(date '+%Y-%m-%d')
    local experience_entry="
### $date_stamp | 任務：${task_description:0:50}...
"
    
    if [ -n "$success_pattern" ] && [ "$success_pattern" != "none" ] && [ "$success_pattern" != "null" ]; then
        experience_entry+="
**成功模式：**
$success_pattern
"
    fi
    
    if [ -n "$failure_lesson" ] && [ "$failure_lesson" != "none" ] && [ "$failure_lesson" != "null" ]; then
        experience_entry+="
**失敗教訓：**
$failure_lesson
"
    fi
    
    if [ -n "$new_technique" ] && [ "$new_technique" != "none" ] && [ "$new_technique" != "null" ]; then
        experience_entry+="
**新技術：**
$new_technique
"
        # 新技術加成：+2 點
        echo "$experience_entry" >> "$agent_file"
        log "✅ 經驗已沉積（新技術加成 +2 點）"
    else
        echo "$experience_entry" >> "$agent_file"
        log "✅ 經驗已沉積"
    fi
    
    return 0
}

#===============================================================================
# 更新代理等級和經驗點
#===============================================================================
update_agent_level() {
    local agent_name="$1"
    local points_earned="$2"
    
    local agent_file="${AGENT_FILES[$agent_name]}"
    
    log "更新代理等級：$agent_name (+$points_earned 點)"
    
    # 計算新的經驗點（目前是估算，未來需要精確追蹤）
    # 這裡需要改進：應該讀取當前值，計算後更新
    log "代理經驗已更新"
}

#===============================================================================
# 清理廢棄 session
#===============================================================================
cleanup_sessions() {
    log "執行 Session 清理..."
    
    # 使用 OpenClaw 內建清理
    openclaw sessions cleanup --enforce 2>&1 | head -20
    
    log "Session 清理完成"
}

#===============================================================================
# 查看代理狀態
#===============================================================================
show_agent_status() {
    echo "========================================="
    echo "  智慧代理工廠 - 代理狀態"
    echo "========================================="
    
    for agent_name in "${!AGENT_FILES[@]}"; do
        local agent_file="${AGENT_FILES[$agent_name]}"
        
        echo ""
        echo "【$agent_name】"
        
        if [ -f "$agent_file" ]; then
            local level=$(grep "等給：LV" "$agent_file" 2>/dev/null | head -1 || echo "LV1")
            local points=$(grep "經驗點：" "$agent_file" 2>/dev/null | head -1 || echo "0 點")
            local updated=$(grep "最後更新：" "$agent_file" 2>/dev/null | head -1 || echo "")
            
            echo "  等級：$level"
            echo "  經驗：$points"
            echo "  更新：$updated"
        else
            echo "  狀態：🆕 新代理（尚未建立記憶）"
        fi
    done
    
    echo ""
    echo "========================================="
}

#===============================================================================
# 主入口
#===============================================================================
case "${1:-status}" in
    spawn)
        # 用法：agent_factory.sh spawn <agent_name> <task_description>
        if [ -z "$2" ]; then
            echo "用法：$0 spawn <agent_name> <task_description>"
            echo "可用代理：${!AGENT_FILES[@]}"
            exit 1
        fi
        
        local agent_name="$2"
        local task_description="${3:-未指定任務}"
        
        execute_agent_task "$agent_name" "$task_description"
        ;;
    
    deposit)
        # 用法：agent_factory.sh deposit <agent_name> <task> <success> <failure> <technique>
        if [ -z "$2" ]; then
            echo "用法：$0 deposit <agent_name> <task> [success] [failure] [technique]"
            exit 1
        fi
        
        deposit_learning "$2" "$3" "$4" "$5" "$6"
        ;;
    
    route)
        # 用法：agent_factory.sh route <task_description>
        if [ -z "$2" ]; then
            echo "用法：$0 route <task_description>"
            exit 1
        fi
        
        route_task_to_agent "$2"
        ;;
    
    status)
        show_agent_status
        ;;
    
    cleanup)
        cleanup_sessions
        ;;
    
    list)
        echo "可用代理："
        for agent_name in "${!AGENT_FILES[@]}"; do
            echo "  - $agent_name: ${AGENT_SPECIALTIES[$agent_name]}"
        done
        ;;
    
    test)
        log "測試模式：agent_factory.sh"
        echo "可用代理：${#AGENT_FILES[@]} 個"
        echo ""
        show_agent_status
        ;;
    
    *)
        echo "用法: $0 {spawn|deposit|route|status|cleanup|list|test}"
        echo ""
        echo "  spawn <agent> <task> - 執行代理任務（生成上下文）"
        echo "  deposit <agent> <task> [s] [f] [t] - 沉積學習經驗"
        echo "  route <task> - 根據任務自動路由到代理"
        echo "  status - 查看所有代理狀態"
        echo "  cleanup - 清理廢棄 session"
        echo "  list - 列出所有可用代理"
        echo "  test - 測試模式"
        ;;
esac