#!/bin/bash
# ==============================================
# update_heartbeat.sh - 任務狀態回報
# 功能：寫入 heartbeat_status.json，確保所有 cron
#       任務的執行進度都有踪蹟
# 建立：2026-05-25
# ==============================================

set -euo pipefail

STATUS_FILE="/home/hoonsoropenclaw/.hermes/heartbeat_status.json"
LOG_DIR="/home/hoonsoropenclaw/.hermes/logs"
mkdir -p "$LOG_DIR"

# 預設值
COMPONENT="${1:-manual}"
STATUS="${2:-running}"
MESSAGE="${3:-}"

update_json() {
    local component="$1"
    local status="$2"
    local message="$3"
    local now
    now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # 讀取現有 json（如果存在的話）
    if [[ -f "$STATUS_FILE" ]]; then
        local content
        content=$(cat "$STATUS_FILE")
    else
        content="{}"
    fi
    
    # 使用 node.js 更新 json（更安全）
    node - << EOF
const fs = require('fs');
let data;
try {
    data = JSON.parse(\`${content}\`);
} catch(e) {
    data = {};
}

data.last_heartbeat = "${now}";
data.last_component = "${component}";
data.last_status = "${status}";

if (!data.components) data.components = {};
data.components["${component}"] = {
    status: "${status}",
    message: "${message}",
    last_update: "${now}"
};

fs.writeFileSync("${STATUS_FILE}", JSON.stringify(data, null, 2));
console.log("Updated heartbeat:", JSON.stringify(data));
EOF
}

# 主程式
main() {
    update_json "$COMPONENT" "$STATUS" "$MESSAGE"
}

main "$@"