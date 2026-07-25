#!/bin/bash
#===============================================================================
# 每日憑證檢查提醒 v2.0
# 檢查 CREDENTIAL_VAULT.md 中尚待提供的憑證，發出提醒
#===============================================================================

VAULT_FILE="/home/hoonsoropenclaw/.hermes/evolution/CREDENTIAL_VAULT.md"
LOG_FILE="/home/hoonsoropenclaw/.hermes/logs/credential_reminder_$(date +%Y%m%d).log"

echo "=== 每日憑證檢查 $(date '+%Y-%m-%d %H:%M:%S') ===" > "$LOG_FILE"

# 檢查待提供項目（忽略錯誤）
PENDING=$(grep -c "⏳" "$VAULT_FILE" 2>/dev/null || echo 0)

if [ "$PENDING" -gt 0 ]; then
    grep "⏳\|待提供" "$VAULT_FILE" 2>/dev/null | while read -r line; do
        echo "🔔 $line" >> "$LOG_FILE"
    done
    
    cat >> "$LOG_FILE" << EOF

📋 提醒：還有 $PENDING 項憑證需要提供
請透過 Telegram 告訴拉斐爾以下資訊：
1. ClawHub 帳號（用於下載社群技能）
2. 股票/投資平台 API（如有需要自動化投資工具）
3. 其他你想整合的服務帳號
EOF
    echo "⚠️ 發現 $PENDING 個待提供憑證"
else
    echo "✅ 所有憑證已齊備，無需提醒"
fi

echo "檢查完成"
exit 0