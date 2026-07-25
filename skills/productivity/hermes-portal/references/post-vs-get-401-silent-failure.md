# POST vs GET: 401 Silent Failure Pattern (2026-06-17)

## 事件摘要

cron `評價網站每日檢查` (run_portal_upload_check.sh) 連續多天 `last_status: ok`，但從未實際上傳過任何作品到 portal。

## 根因鏈

```
1. .env.local 有多行 AGENT_API_KEY
   AGENT_API_KEY=***              ← mask 值（Hermes filter 產物）
   AGENT_API_KEY=***              ← 真實 key（base64/various encoding 變體）

2. grep | cut 無 exit → 讀到第一行 = mask 值
   AGENT_API_KEY=$(grep AGENT_API_KEY .env.local | cut -d'=' -f2 | tr -d ' ')
   → "***"（7 字）

3. cron script 的 API_URL 仍是舊 deployment URL
   https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works
   → 該 URL 已 401 protected（不存在的 deployment hash）

4. GET /api/works 只驗格式 → "***" 被視為有效格式 → HTTP 200
   POST /api/works 需要真實 key → "***" → HTTP 401

5. cron script 的 set -e + curl 的 -s (silent) → 401 不阻斷 script
   → script 看似成功（exit 0），實際上所有 PUT/POST 都失敗
```

## 實測驗證

```bash
# 測試 GET（驗格式）
curl -s -o /dev/null -w "%{http_code}" \
  -X GET "https://hermes-portal.vercel.app/api/works" \
  -H "X-Agent-Key: ***"   # mask 值
# HTTP 200 ✅ — GET 只驗格式

# 測試 POST（需要真實 key）
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "https://hermes-portal.vercel.app/api/works" \
  -H "X-Agent-Key: ***" \
  -d '{"title":"test","description":"test"}'
# HTTP 401 ❌ — POST 需要真實 key

# 舊 deployment URL（已廢棄）
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works" \
  -H "X-Agent-Key: $REAL_KEY"
# HTTP 401 ❌ — deployment 已過時
```

## 修復清單

| 檔案 | 修復內容 |
|------|---------|
| `~/.hermes/scripts/portal_upload_check.sh` | URL → `hermes-portal.vercel.app`；`cut` → `awk ... exit` |
| `~/.hermes/skills/productivity/portal-auto-upload/SKILL.md` | curl 範例 URL + Python 範例 URL + awk path + 已知限制第 4 條 |
| `permanent-projects/hermes-portal/.env.local` | 需要 `vercel env pull` 重新取得真實 AGENT_API_KEY（目前是 mask） |

## If→Then 規則

**If** cron 顯示 ok 但從未實際上傳東西  
**Then** 分別測試 GET 和 POST 的 HTTP status code，不要只看 cron exit code

**If** `grep AGENT_API_KEY .env.local | cut -d'=' -f2` 出來的值 < 10 字  
**Then** 是 mask 值，改用 `awk -F= '/^AGENT_API_KEY=*** $2; exit}' .env.local`

**If** 更新了 skill 的 canonical URL  
**Then** 同步改 curl 範例 + Python 範例 + cron script + 驗證指令，四處都要改

**If** 懷疑 .env.local 有多行同名變數  
**Then** `grep -c "^AGENT_API_KEY=" .env.local` → > 1 確認

## 驗證命令

```bash
# 確認 key 不是 mask
KEY=$(awk -F= '/^AGENT_API_KEY=/{print $2; exit}' /home/hoonsoropenclaw/permanent-projects/hermes-portal/.env.local | tr -d ' ')
echo "KEY length: ${#KEY}"   # 預期 > 20

# 確認 GET 和 POST 狀態
curl -s -o /dev/null -w "GET: %{http_code}\n" -X GET "https://hermes-portal.vercel.app/api/works" -H "X-Agent-Key: $KEY"
curl -s -o /dev/null -w "POST: %{http_code}\n" -X POST "https://hermes-portal.vercel.app/api/works" \
  -H "X-Agent-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"title":"verification-test","description":"cron verify","status":"published","tags":["test"],"skill_used":["test"]}'
```

## 受影響的 Cron Jobs

- `評價網站每日檢查` (run_portal_upload_check.sh) — URL 錯誤 + awk 讀 key 錯誤 → POST 從未成功
- `eval-sync` (sync_evaluations.py) — 可能同樣問題，需要交叉檢查
