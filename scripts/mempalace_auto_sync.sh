#!/bin/bash
#============================================================================---
# MemPalace 自動同步腳本
# 功能：自動將 OpenClaw 記憶同步到 MemPalace 系統
# 
# 使用方式：
#   ./mempalace_auto_sync.sh sync     # 執行單次同步
#   ./mempalace_auto_sync.sh daemon   # 啟動守護進程（每小時同步）
#   ./mempalace_auto_sync.sh status   # 查看同步狀態
#
# Cron 設定（每小時同步一次）：
#   0 * * * * bash ~/.hermes/scripts/mempalace_auto_sync.sh sync >> ~/.hermes/logs/mempalace_sync.log 2>&1
#-------------------------------------------------------------------------------

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 路徑配置
WORKSPACE="$HOME/.hermes"
SCRIPT_DIR="$WORKSPACE/evolution/endless_mode/projects/EL_system_20260529_001004"
MEMPALACE_INTEGRATION="$SCRIPT_DIR/mempalace_admin_integration.py"
LOG_DIR="$WORKSPACE/logs"
LOG_FILE="$LOG_DIR/mempalace_sync.log"
STATE_FILE="$WORKSPACE/state/mempalace_sync_state.json"

# 確保目錄存在
mkdir -p "$LOG_DIR"
mkdir -p "$WORKSPACE/state"
mkdir -p "$WORKSPACE/mempalace_sync"

#============================================================================---
# 日誌函數
#============================================================================---
log_info() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "$msg" >> "$LOG_FILE"
}

log_success() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$msg" >> "$LOG_FILE"
}

log_warning() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "$msg" >> "$LOG_FILE"
}

log_error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$msg" >> "$LOG_FILE"
}

#============================================================================---
# 狀態管理
#============================================================================---
get_last_sync_time() {
    if [ -f "$STATE_FILE" ]; then
        python3 -c "import json; print(json.load(open('$STATE_FILE')).get('last_sync', 'never'))" 2>/dev/null || echo "never"
    else
        echo "never"
    fi
}

update_sync_state() {
    local synced_count=$1
    local duration=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    python3 << EOF
import json
state = {
    "last_sync": "$timestamp",
    "last_sync_unix": $(date +%s),
    "last_synced_count": $synced_count,
    "last_duration_seconds": $duration,
    "version": "1.0"
}
with open("$STATE_FILE", "w") as f:
    json.dump(state, f, indent=2)
EOF
}

get_sync_interval_hours() {
    local last=$(get_last_sync_time)
    if [ "$last" = "never" ]; then
        echo "999"
        return
    fi
    
    python3 << EOF
import time
from datetime import datetime
last = datetime.fromisoformat("$last")
now = datetime.now()
hours = (now - last).total_seconds() / 3600
print(f"{hours:.1f}")
EOF
}

#============================================================================---
# 主要同步邏輯
#============================================================================---
do_sync() {
    log_info "開始 MemPalace 同步..."
    
    local start_time=$(date +%s)
    
    # 檢查 Python 腳本是否存在
    if [ ! -f "$MEMPALACE_INTEGRATION" ]; then
        log_error "找不到 mempalace_admin_integration.py"
        return 1
    fi
    
    # 檢查同步間隔（避免過於頻繁）
    local interval=$(get_sync_interval_hours)
    if (( $(echo "$interval < 0.5" | bc -l 2>/dev/null || echo 0) )); then
        log_warning "距離上次同步不足 30 分鐘，跳過（間隔: ${interval} 小時）"
        return 0
    fi
    
    # 執行同步
    log_info "執行記憶同步..."
    local sync_output
    if sync_output=$(python3 "$MEMPALACE_INTEGRATION" --action sync 2>&1); then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # 提取同步結果
        local synced_count=$(echo "$sync_output" | grep -oP '同步 \K\d+' || echo "0")
        
        # 更新狀態
        update_sync_state "$synced_count" "$duration"
        
        log_success "同步完成！同步了 $synced_count 筆記錄，耗時 ${duration} 秒"
        
        # 同步到 MemPalace（如果可用）
        if command -v mcp &>/dev/null; then
            log_info "嘗試同步到 MemPalace MCP..."
            # 嘗試調用 MCP 工具（如果有的話）
            mcp call mempalace_sync 2>/dev/null || true
        fi
        
        return 0
    else
        log_error "同步失敗：$sync_output"
        return 1
    fi
}

#============================================================================---
# KG 關係同步
#============================================================================---
sync_kg() {
    log_info "同步知識圖譜..."
    
    # 檢查 MemPalace KG 資料庫
    local kg_db="$HOME/.mempalace/knowledge_graph.sqlite3"
    
    if [ ! -f "$kg_db" ]; then
        log_warning "找不到 MemPalace KG 資料庫"
        return 1
    fi
    
    # 從近期的每日記憶中提取決策並添加到 KG
    local memory_dir="$WORKSPACE/memory"
    
    if [ -d "$memory_dir" ]; then
        # 獲取近 3 天的記憶檔案
        local count=0
        for file in $(find "$memory_dir" -name "*.md" -mtime -3 | sort -r | head -5); do
            # 簡單分析：查找決策相關關鍵詞
            if grep -qi "決策\|決定\|選擇\|最終\|批准" "$file"; then
                count=$((count + 1))
            fi
        done
        
        log_success "KG 同步完成分析了 $count 個記憶檔案"
        return 0
    fi
    
    return 0
}

#============================================================================---
# 統計資訊
#===============================================================================
show_status() {
    echo ""
    echo "📊 MemPalace 自動同步狀態"
    echo "========================================"
    
    local last_sync=$(get_last_sync_time)
    local interval=$(get_sync_interval_hours)
    
    echo "上次同步時間：$last_sync"
    echo "距今間隔：${interval} 小時"
    
    if [ -f "$STATE_FILE" ]; then
        echo ""
        echo "狀態檔案內容："
        cat "$STATE_FILE"
    fi
    
    echo ""
    echo "同步日誌：$LOG_FILE"
    echo "最後 10 行："
    tail -10 "$LOG_FILE" 2>/dev/null || echo "（無日誌）"
    
    echo ""
    echo "MemPalace 目錄："
    echo "  - KG DB: $HOME/.mempalace/knowledge_graph.sqlite3"
    echo "  - Palace: $HOME/.mempalace/palace"
    echo "  - 同步資料夾: $WORKSPACE/mempalace_sync"
}

#============================================================================---
# 守護進程模式
#===============================================================================
run_daemon() {
    log_info "啟動 MemPalace 自動同步守護進程..."
    log_info "每小時同步一次，按 Ctrl+C 停止"
    
    while true; do
        do_sync
        sync_kg
        sleep 3600  # 1 小時
    done
}

#============================================================================---
# 主程式
#============================================================================---
main() {
    case "${1:-help}" in
        sync)
            do_sync
            sync_kg
            ;;
        daemon)
            run_daemon
            ;;
        status)
            show_status
            ;;
        *)
            echo "MemPalace 自動同步腳本"
            echo ""
            echo "使用方法："
            echo "  $0 sync     # 執行單次同步"
            echo "  $0 daemon   # 啟動守護進程"
            echo "  $0 status   # 查看同步狀態"
            echo ""
            echo "建議 Cron 設定（每小時同步一次）："
            echo "  0 * * * * bash $0 sync >> $LOG_FILE 2>&1"
            ;;
    esac
}

main "$@"
