# Cron Job 模型選擇決策樹

> 用途：建立 cron job 時，怎麼決定用哪個 model（或不用 LLM）

---

## 決策樹

```
[你的 cron 任務需要 LLM 嗎？]
  │
  ├── ❌ 不需要（固定邏輯、撈資料、跑命令）
  │   └─→ ✅ 用 no_agent=True 跑 script
  │         零 token 消耗、100% 節省
  │
  └── ✅ 需要 LLM 介入
      │
      [任務複雜度？]
        │
        ├── 簡單（Q&A、摘要、固定格式產出）
        │   └─→ model = MiniMax-M2.1 或 M2.5
        │         cheap tier，$0.279/M input
        │
        ├── 標準（多步分析、總結、簡單決策）
        │   └─→ model = MiniMax-M2.7
        │         daily driver
        │
        └── 複雜（多輪推理、架構、security）
            └─→ model = MiniMax-M3
                  旗艦，必要時才用
```

---

## 三種 cron 模式對比

| 模式 | config | Token 成本 | LLM 判斷 | 適用 |
|------|--------|-----------|---------|------|
| `no_agent=True` + script | `"no_agent": true, "script": "run_*.sh", "prompt": null` | **0** | ❌ | 固定邏輯任務 |
| `no_agent=False` + model=M2.7 | `"model": "MiniMax-M2.7"` | 中 | ✅ | 標準 AI 任務 |
| `no_agent=False` + model=M3 | `"model": "MiniMax-M3"`（或預設） | 高 | ✅ | 複雜 AI 任務 |

---

## 範例：3 種實際的 cron job 設定

### 範例 1：RSS 摘要（標準 AI 任務，用 M2.7）

```json
{
  "id": "abc123",
  "name": "rss-daily-summary",
  "schedule": "0 9 * * *",
  "prompt": "讀取 ~/.hermes/data/rss.json，總結昨天的新條目，列前 5 條",
  "model": "MiniMax-M2.7",
  "no_agent": false
}
```

**Token 預估**（假設 prompt 1K + response 2K）：
- 每天 3K tokens
- 一個月 90K tokens
- M2.7: $0.025（input）+ $2.40（output）= **$2.43/月**
- M3: 假設 3-5x → $7-$12/月
- **省 $5-10/月**

### 範例 2：每日 GitHub 通知（不需要 LLM，no_agent）

```bash
# ~/.hermes/scripts/run_github_notify.sh
#!/bin/bash
# 撈 GitHub notifications，發 Telegram
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/notifications | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for n in data[:5]:
    print(f\"{n['repository']['full_name']}: {n['subject']['title']}\")
" | telegram-send --stdin
```

```json
{
  "id": "def456",
  "name": "github-notify",
  "schedule": "*/30 * * * *",
  "script": "run_github_notify.sh",
  "no_agent": true,
  "prompt": null
}
```

**Token 成本：$0**（零 LLM 消耗）

### 範例 3：每日 PR 風險分析（複雜 AI，用 M3）

```json
{
  "id": "ghi789",
  "name": "pr-risk-analyzer",
  "schedule": "0 18 * * *",
  "prompt": "分析今天所有 open PR 的 diff，識別 high-risk 變更（auth、migration、security），產出風險報告",
  "model": "MiniMax-M3",
  "no_agent": false
}
```

**為什麼用 M3**：
- 需要多步推理（讀 diff、識別 pattern、評估 blast radius）
- 出錯成本 > token 成本（漏掉 high-risk PR 可能線上出事）

---

## ⚠️ `hermes cron edit --script` Bug 提醒

**不要用 `hermes cron edit --script`** 改 no_agent jobs——會觸發 bug，script 欄位會被寫成 shebang+多行命令。

正確做法：直接編輯 `~/.hermes/cron/jobs.json`。

**詳細 bug 與修法**：見 metacognitive-learner skill 的 `hermes cron edit --script` bug 段落。

---

## 模型選擇速查表

| 任務類型 | 推薦 model | 範例 |
|---------|----------|------|
| RSS / log 摘要 | M2.7 | 「列前 5 條 RSS」「統計昨天 error 數量」 |
| 資料分析 | M2.7 | 「計算這週 sales 趨勢」「找 outlier」 |
| 格式轉換 | M2.5 | 「把 CSV 轉 JSON」「reformat log」 |
| 簡單決策 | M2.7 | 「這個 PR 要不要 merge」「哪個方案比較好」 |
| 多步推理 | M3 | 「分析架構 trade-off」「找 security 漏洞」 |
| 創意生成 | M3 | 「幫我想 3 個 slogan」「設計對話流程」 |

---

## 何時**不該**切換 model

- 任務需要看圖（image input）→ **M2.7 不支援**，必須用 M3
- 任務需要多輪深度推理 → 不要切 cheap tier
- 任務失敗成本高（security、financial）→ 不要切 cheap tier
- 任務已有 prompt caching 累積（cron 連續跑 7 天以上）→ 切換會失效 cache，反而更貴

---

## 驗證方法

```bash
# 跑一個 cheap tier cron job，確認正常
hermes cron list | grep "cheap-job-name"

# 過 24 小時後看 token 消耗
hermes config show | grep -A 5 "Token"
```
