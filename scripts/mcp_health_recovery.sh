#!/bin/bash
# MCP Health Recovery Script
# 自動檢測並復原失敗的 MCP 服務

set -e

LOG_FILE="/tmp/openclaw/openclaw-$(date '+%Y-%m-%d').log"
STATE_DIR="$HOME/.openclaw/mcp_health"
LAST_STATE="$STATE_DIR/last_check.json"

mkdir -p "$STATE_DIR"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 讀取上次狀態
load_last_state() {
    if [ -f "$LAST_STATE" ]; then
        cat "$LAST_STATE"
    else
        echo '{"failed_servers": {}, "timestamp": 0}'
    fi
}

# 保存狀態
save_state() {
    echo "$1" > "$LAST_STATE"
}

# 檢查單一 MCP 服務是否健康
check_mcp_server() {
    local server_name="$1"
    local expected_path="$2"
    
    # 檢查進程是否存在
    if pgrep -f "$expected_path" > /dev/null 2>&1; then
        echo "running"
        return 0
    fi
    
    # 檢查日誌中最近的錯誤（過去5分鐘）
    local recent_error=$(grep -E "failed to start server \"$server_name\"" "$LOG_FILE" 2>/dev/null | tail -1)
    if [ -n "$recent_error" ]; then
        # 解析時間戳
        local log_time=$(echo "$recent_error" | grep -oE '"time":"[^"]+"' | cut -d'"' -f4)
        if [ -n "$log_time" ]; then
            local log_epoch=$(date -d "${log_time/T/ }" +%s 2>/dev/null || echo 0)
            local now_epoch=$(date +%s)
            local diff=$((now_epoch - log_epoch))
            
            if [ $diff -lt 300 ]; then
                echo "failed"
                return 1
            fi
        fi
    fi
    
    echo "unknown"
    return 2
}

# 嘗試復原單一服務
recover_server() {
    local server_name="$1"
    local restart_cmd="$2"
    
    log_warn "嘗試復原 MCP 服務: $server_name"
    
    if [ -n "$restart_cmd" ]; then
        eval "$restart_cmd" && log_info "$server_name 復原成功" || log_error "$server_name 復原失敗"
        return $?
    else
        log_error "無法復原 $server_name：未知的啟動方式"
        return 1
    fi
}

# 主檢查流程
main() {
    log_info "=== MCP 健康檢查開始 ==="
    
    local now=$(date +%s)
    local last_state=$(load_last_state)
    
    # 定義需要監控的 MCP 服務
    declare -A MCP_SERVERS
    MCP_SERVERS=(
        ["slack"]="/home/hoonsoropenclaw/.npm-global/bin/mcp-server-slack"
        ["brave-search"]="/home/hoonsoropenclaw/.npm-global/bin/mcp-server-brave-search"
        ["supabase"]="supabase-mcp-server"
        ["notebooklm"]="notebooklm-mcp server"
        ["filesystem"]="/home/hoonsoropenclaw/.npm-global/bin/mcp-server-filesystem"
        ["github"]="/home/hoonsoropenclaw/.npm-global/bin/mcp-server-github"
        ["mempalace"]="python3 -m mempalace.mcp_server"
    )
    
    local new_state='{"failed_servers": {}, "timestamp": '$(date +%s)'}'
    local any_failed=0
    
    for server in "${!MCP_SERVERS[@]}"; do
        local path="${MCP_SERVERS[$server]}"
        local status=$(check_mcp_server "$server" "$path")
        
        case $status in
            "running")
                log_info "[✓] $server: 正常運行"
                ;;
            "failed")
                log_warn "[✗] $server: 連線失敗，需要復原"
                recover_server "$server" ""
                any_failed=1
                ;;
            "unknown")
                log_info "[?] $server: 狀態未知"
                ;;
        esac
    done
    
    if [ $any_failed -eq 0 ]; then
        log_info "所有 MCP 服務運行正常 ✓"
    else
        log_warn "部分 MCP 服務需要關注"
    fi
    
    log_info "=== MCP 健康檢查完成 ==="
    return $any_failed
}

# 顯示摘要
show_summary() {
    echo ""
    echo "=== MCP 服務狀態摘要 ==="
    echo ""
    
    # 使用 openclaw mcp list 獲取配置列表
    local config_servers=$(openclaw mcp list 2>/dev/null | grep -E "^\s*-\s+" | sed 's/^\s*-\s+//' || echo "mcp list unavailable")
    
    echo "配置的 MCP 服務:"
    echo "$config_servers" | while read -r line; do
        [ -n "$line" ] && echo "  - $line"
    done
    
    echo ""
    echo "當前运行的 MCP 相關進程:"
    ps aux | grep -E "mcp|mempalace" | grep -v grep | awk '{print "  PID:"$2, $11, $12, $13}' | head -20
}

# 緊急復原（重啟 Gateway）
emergency_recover() {
    log_error "執行緊急 Gateway 重啟..."
    openclaw gateway restart
    sleep 5
    log_info "Gateway 重啟完成"
}

# 根據參數執行
case "${1:-check}" in
    check)
        main
        ;;
    summary)
        show_summary
        ;;
    recover)
        log_warn "手動觸發緊急復原..."
        emergency_recover
        ;;
    loop)
        log_info "啟動持續監控模式 (每60秒檢查一次)..."
        while true; do
            main
            sleep 60
        done
        ;;
    *)
        echo "用法: $0 {check|summary|recover|loop}"
        echo "  check   - 執行單次健康檢查"
        echo "  summary - 顯示服務狀態摘要"
        echo "  recover - 緊急復原 Gateway"
        echo "  loop    - 持續監控模式"
        exit 1
        ;;
esac
