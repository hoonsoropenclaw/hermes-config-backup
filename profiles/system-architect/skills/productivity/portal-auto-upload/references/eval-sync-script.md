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

## ⚠️ 已知問題：401 Unauthorized

**現象**：本機 `.env.local` 的 `AGENT_API_KEY` 無法通過 Vercel 部署的 hermes-portal 驗證

**可能原因**：
1. Vercel Dashboard 未設定 `AGENT_API_KEY` 環境變數
2. Vercel 上的值與 `.env.local` 不同步
3. Header 名稱可能不是 `X-Agent-Key`

**排查步驟**：
1. 登入 Vercel Dashboard → hermes-portal → Settings → Environment Variables
2. 確認是否有 `AGENT_API_KEY`，值是否與 `.env.local` 一致
3. 若無，建立並填入相同值
4. 重新部署 hermes-portal

**驗證方式**：
```bash
cd /home/hoonsoropenclaw
python3 .hermes/scripts/sync_evaluations.py
# 成功：輸出下載的評價數量
# 失敗：401 Unauthorized
```

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