# 評價同步腳本參考

## 腳本位置
`/home/hoonsoropenclaw/.hermes/scripts/sync_evaluations.py`

## 功能
- 每日 10:00（cron: `eval-sync`，Job ID `591838105a4b`）自動執行
- 呼叫 `GET /api/evaluations/sync` 下載新評價
- 新評價寫入 `~/.hermes/memories/EVALUATIONS_MEMORY.md`
- 另存 `~/.hermes/scripts/EVAL_ANALYSIS.json`（含評價分析）

## 依賴
- `AGENT_API_KEY` 環境變數（位於 `/home/hoonsoropenclaw/hermes-portal/.env.local`）
- Header 名稱：`X-Agent-Key`

## ⚠️ 常見錯誤：401 Unauthorized（持續性，2026-06-04 更新）

### 典型徵兆

| 測試 | 結果 | 意義 |
|------|------|------|
| `GET /api/evaluations/sync` | 200 | server 正常，env var 有讀到 |
| `POST /api/works` | 401 `Invalid or missing X-Agent-Key` | `process.env.AGENT_API_KEY` 比對失敗 |

### 根本原因

`POST` handler 呼叫 `key === process.env.AGENT_API_KEY`，當後者為 `undefined` 或含隱形字元時，永遠比對失敗。明明 Vercel Dashboard 已設定，deployment 也是 Ready，但 server function 執行時的注入值有問題。

### 排查步驟

```bash
# Step 1: 確認本機 key
cat /home/hoonsoropenclaw/hermes-portal/.env.local | grep AGENT_API_KEY

# Step 2: 測試 GET（不需要 auth）
curl -s -w "\nHTTP_CODE: %{http_code}\n" \
  "https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works"

# Step 3: 測試 POST（需要 auth）
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST \
  "https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works" \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: hms_hermes_portal_secret_key_2026" \
  -d '{"title": "test"}'
```

### 診斷矩陣

| GET | POST | 原因 |
|-----|------|------|
| 200 | 401 | `AGENT_API_KEY` 注入值有隱形字元/編碼問題（最常見）|
| 200 | 200 | ✅ 正常，問題解決 |
| 401/500 | - | server 有問題，env var 完全讀不到 |

### 解決方向（按順序）

1. **刪除後重建**：Vercel Dashboard → 刪除 `AGENT_API_KEY` row → 重新新增（確保值乾淨）
2. **確認 Scope**：Scope 必須包含 `Production`（不能只設在 Preview）
3. **等待生效**：redeploy 後等 2-3 分鐘再測，不要立刻測
4. **加 logging**：在 API handler 加入 `console.log('AGENT_API_KEY:', process.env.AGENT_API_KEY)`，redeploy 後查 Vercel logs 看實際注入值
5. **檢查本機檔案**：用 `xxd /home/hoonsoropenclaw/hermes-portal/.env.local | tail` 確認無 BOM/隱形字元

## 現有 Cron Jobs 相關

| Job ID | 名稱 | 頻率 | 腳本 |
|--------|------|------|------|
| `1f8020b9485e` | 評價網站每日檢查 | 0 9 * * * | portal_upload_check.sh |
| `591838105a4b` | eval-sync | 0 10 * * * | sync_evaluations.py |

## 輸出格式

寫入 `EVALUATIONS_MEMORY.md` 的格式：
```
## YYYY-MM-DD HH:MM 評價記錄

- **作品**: [title]
- **三項分數**: 視覺 4/5, 功能 4/5, 性價比 3/5
- **回饋**: [feedback text]
- **評價時間**: ISO timestamp
```

寫入 `EVAL_ANALYSIS.json` 的格式：
```json
{
  "evaluations": [
    {
      "id": "eval_xxx",
      "work_id": "work_xxx",
      "work_title": "...",
      "scores": {"visual": 4, "functionality": 4, "value": 3},
      "feedback": "...",
      "created_at": "..."
    }
  ]
}
```