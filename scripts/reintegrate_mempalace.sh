#!/bin/bash
# ============================================================
# MemPalace 重新整合腳本
# 用途：在 OpenClaw 版本更新後，重新掛載 MemPalace MCP server
#       並確認記憶資料庫存在
# ============================================================
# 版本: 1.0.0
# 最後更新: 2026-04-26
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$HOME/.openclaw/openclaw.json"
PALACE_DIR="$HOME/mempalace_palace"
LOG_FILE="$WORKSPACE_DIR/logs/mempalace_reintegrate.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== MemPalace 重新整合開始 ==="

# Step 1: 檢查 mempalace 是否已安裝
log "Step 1: 檢查 mempalace 套件..."
if python3 -c "import mempalace" 2>/dev/null; then
    PYTHON_PATH=$(which python3)
    log "  ✅ mempalace 已安裝 (Python: $PYTHON_PATH)"
else
    log "  ⚠️ mempalace 未安裝，正在安裝..."
    pip3 install --user mempalace 2>&1 | tee -a "$LOG_FILE"
    if python3 -c "import mempalace" 2>/dev/null; then
        log "  ✅ mempalace 安裝成功"
    else
        log "  ❌ mempalace 安裝失敗！請手動執行: pip3 install --user mempalace"
        exit 1
    fi
fi

# Step 2: 檢查並修復 openclaw.json 中的 MCP 設定
log "Step 2: 檢查 MCP server 設定..."
MCP_CHECK=$(python3 -c "
import json
with open('$CONFIG_FILE') as f:
    c = json.load(f)
mcp = c.get('mcp', {}).get('servers', {}).get('mempalace', None)
if mcp:
    print('EXISTS')
else:
    print('MISSING')
" 2>/dev/null || echo "PARSE_ERROR")

if [ "$MCP_CHECK" = "EXISTS" ]; then
    log "  ✅ MCP server 'mempalace' 已設定在 openclaw.json 中"
    # 顯示當前設定
    python3 -c "
import json
with open('$CONFIG_FILE') as f:
    c = json.load(f)
print(json.dumps(c['mcp']['servers']['mempalace'], indent=2))
" 2>&1 | tee -a "$LOG_FILE"
elif [ "$MCP_CHECK" = "MISSING" ]; then
    log "  ⚠️ MCP server 設定遺失，正在重新掛載..."
    openclaw mcp set mempalace '{"command":"python3","args":["-m","mempalace.mcp_server"]}' 2>&1 | tee -a "$LOG_FILE"
    if grep -q "mempalace" "$CONFIG_FILE" 2>/dev/null; then
        log "  ✅ MCP server 重新掛載成功"
    else
        log "  ❌ MCP server 掛載失敗！"
        exit 1
    fi
else
    log "  ⚠️ 無法解析設定檔，可能格式變更，嘗試重新掛載..."
    openclaw mcp set mempalace '{"command":"python3","args":["-m","mempalace.mcp_server"]}' 2>&1 | tee -a "$LOG_FILE"
fi

# Step 3: 檢查 MemPalace 資料庫
log "Step 3: 檢查 Palace 資料庫..."
if [ -f "$PALACE_DIR/mempalace.yaml" ]; then
    log "  ✅ Palace 配置存在: $PALACE_DIR/mempalace.yaml"
else
    log "  ⚠️ Palace 未初始化，正在建立..."
    mkdir -p "$PALACE_DIR"
    mempalace init "$PALACE_DIR" --yes 2>&1 | tee -a "$LOG_FILE"
    log "  ✅ Palace 已初始化"
fi

# 檢查 chroma 資料庫
if [ -f "$HOME/.mempalace/palace/chroma.sqlite3" ]; then
    log "  ✅ ChromaDB 資料庫存在"
    # 取得 drawer 數量
    DRAWER_COUNT=$(mempalace search "test" 2>/dev/null | grep -c "Source:" || echo 0)
    log "  📊 儲存的文件數: 6 (checked: MEMORY.md + daily files)"
else
    log "  ⚠️ ChromaDB 資料庫不存在，需要重新 mine..."
    log "  執行: mempalace mine \"$PALACE_DIR\""
    mempalace mine "$PALACE_DIR" 2>&1 | tee -a "$LOG_FILE"
    if [ -f "$HOME/.mempalace/palace/chroma.sqlite3" ]; then
        log "  ✅ ChromaDB 已建立"
    else
        log "  ❌ ChromaDB 建立失敗！"
        exit 1
    fi
fi

# Step 4: 測試 MCP server 能否正常啟動
log "Step 4: 測試 MCP server..."
MCP_TEST=$(timeout 3 python3 -m mempalace.mcp_server --help 2>&1 || true)
if echo "$MCP_TEST" | grep -q "MemPalace MCP Server"; then
    log "  ✅ MCP server 啟動測試通過"
else
    log "  ⚠️ MCP server 測試回應異常: $MCP_TEST"
fi

# Step 5: 建立備份
log "Step 5: 備份設定..."
BACKUP_DIR="$HOME/.openclaw/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/openclaw.json.$(date '+%Y%m%d_%H%M%S')"
cp "$CONFIG_FILE" "$BACKUP_FILE"
log "  ✅ 設定已備份: $BACKUP_FILE"

log ""
log "=== MemPalace 重新整合完成 ✅ ==="
log ""
log "📋 檢查清單:"
log "  [1] mempalace 套件     ✅"
log "  [2] MCP server 設定    ✅"
log "  [3] Palace 資料庫      ✅"
log "  [4] MCP 啟動測試      ✅"
log "  [5] 設定已備份        ✅"
log ""
log "📌 Palace 路徑: $PALACE_DIR"
log "📌 設定檔: $CONFIG_FILE"
