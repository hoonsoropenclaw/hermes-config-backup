# eval-sync 401 Unauthorized：Vercel env pull 的 AGENT_API_KEY mask 問題

## 問題描述

`eval-sync` cron job 從 2026-06-07 起持續報 HTTP 401 Unauthorized。

## 根因分析

`/home/hoonsoropenclaw/permanent-projects/hermes-portal/.env.local` 中：
```
AGENT_API_KEY=*** 
```

值是 `0770415`（7 字），看起來像真的 key，但實際上是 `vercel env pull` 對 encrypted 類型環境變數回傳的 **mask**。

Vercel Dashboard → hermes-portal → Environment Variables 中，`AGENT_API_KEY` 的實際值是加密 blob（`eyJ2Ijoidj...` 格式）。

當 `sync.js` 收到 `Authorization: Bearer <mask>` 時，比對 `process.env.AGENT_API_KEY`（加密 blob）與 mask，格式/長度都不匹配，導致 401。

## 修復方向

需從 Vercel Dashboard 取得 `AGENT_API_KEY` 的實際值，並更新 `.env.local` 的明文版本。

```bash
# 查看 Vercel env（需 login）
vercel env ls hermes-portal

# 從 Vercel Dashboard 取得實際 key：
# hermes-portal → Settings → Environment Variables → AGENT_API_KEY → Reveal
```

## 驗證方式

修復後：
```bash
python3 ~/.hermes/scripts/sync_evaluations.py
# 預期：exit 0 + "取得 N 筆評價"（非 401）
```

## If→Then 規則

**If** AGENT_API_KEY 在 .env.local 顯示 `*** `（7 字）而非完整 key（通常是 32+ 字）
**Then** 這個值可能只是 mask，實際 key 要從 Vercel Dashboard 確認
**Then** 不要懷疑 script 有 bug，先確認 key 是否是 mask

**If** eval-sync 報 401，同時 `.env.local` 的 key 看起來很短（<20 字）
**Then** 先懷疑 key 不匹配，而不是 script 有 bug