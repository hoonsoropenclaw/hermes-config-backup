#!/bin/bash
# ============================================================
# verify-deployment.sh
# 部署後的 4 層驗證腳本（給 hermes-deploy-verification skill 用）
# 使用方式：./verify-deployment.sh <main-domain> [random-alias]
# 範例：./verify-deployment.sh hermes-cli-reference.vercel.app
#       ./verify-deployment.sh raphael-status-site.vercel.app raphael-status-site-cff3cpte4-...
# ============================================================

set -e

MAIN_DOMAIN="$1"
RANDOM_ALIAS="$2"

if [ -z "$MAIN_DOMAIN" ]; then
    echo "❌ 用法：$0 <main-domain> [random-alias]"
    echo "   範例：$0 hermes-cli-reference.vercel.app"
    exit 1
fi

echo "════════════════════════════════════════════════════════════"
echo "  部署驗證: $MAIN_DOMAIN"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Layer 3: Production HTTP + DNS ────────────────────────

echo "── Layer 3a: 主要 domain HTTP 200 ──"
MAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$MAIN_DOMAIN")
MAIN_SIZE=$(curl -s -o /dev/null -w "%{size_download}" "https://$MAIN_DOMAIN")
echo "  HTTP $MAIN_STATUS, size ${MAIN_SIZE}B"
if [ "$MAIN_STATUS" = "200" ]; then
    echo "  ✅ 主要 domain 200 OK"
else
    echo "  ❌ 主要 domain 不是 200，部署可能失敗"
    exit 1
fi
echo ""

if [ -n "$RANDOM_ALIAS" ]; then
    echo "── Layer 3b: 隨機 alias（短期 401 是正常的）──"
    ALIAS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$RANDOM_ALIAS")
    echo "  HTTP $ALIAS_STATUS"
    if [ "$ALIAS_STATUS" = "401" ]; then
        echo "  ⚠️  Alias 401（5-10 分鐘 propagation，預期行為）"
    elif [ "$ALIAS_STATUS" = "200" ]; then
        echo "  ✅ Alias 200 OK（已 propagation 完成）"
    else
        echo "  ❓ Alias HTTP $ALIAS_STATUS（檢查 deployment 狀態）"
    fi
    echo ""
fi

echo "── Layer 3c: 多 DNS 解析 ──"
for dns in 1.1.1.1 8.8.8.8 9.9.9.9; do
    ip=$(dig +short "@${dns}" "$MAIN_DOMAIN" A 2>/dev/null | head -1)
    if [ -n "$ip" ]; then
        echo "  $dns: $ip ✅"
    else
        echo "  $dns: (timeout) ⚠️"
    fi
done
echo ""

# ── Layer 4: Production 內容驗證 ────────────────────────

echo "── Layer 4: Production 內容驗證（curl 抓 HTML）──"
PROD_HTML=$(curl -s "https://$MAIN_DOMAIN" 2>/dev/null)
if echo "$PROD_HTML" | grep -q "DOCTYPE html"; then
    echo "  ✅ HTML 結構正確"
else
    echo "  ❌ HTML 結構異常"
fi
echo ""

# ── 摘要 ────────────────────────────────────────────────

echo "════════════════════════════════════════════════════════════"
echo "  驗證結果摘要"
echo "════════════════════════════════════════════════════════════"
echo "  Layer 1（本地）：需要 agent 自行確認"
echo "  Layer 2（deploy）：vercel CLI 已回報成功"
echo "  Layer 3（HTTP+DNS）：$MAIN_DOMAIN → HTTP $MAIN_STATUS"
if [ -n "$RANDOM_ALIAS" ]; then
    echo "  Layer 3b（alias）：$RANDOM_ALIAS → HTTP $ALIAS_STATUS"
fi
echo "  Layer 4（browser）：請用 headless browser 開啟後手動確認"
echo ""
echo "  給使用者的 URL：https://$MAIN_DOMAIN"
echo "  提醒使用者："
echo "    1. 強制 reload (Ctrl+Shift+R) 清 Vercel 60s cache"
echo "    2. 如果看不到，無痕模式 (Ctrl+Shift+N)"
echo "    3. 還是不行：電腦 DNS 改 1.1.1.1"
