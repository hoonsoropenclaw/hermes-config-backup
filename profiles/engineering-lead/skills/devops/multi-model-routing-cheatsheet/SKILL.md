---
name: multi-model-routing-cheatsheet
description: "赫米斯多模型路由速查 — 當用戶問「按任務難度切換 model」「省 tokens」「用便宜 tier」「cheap model」「MiniMax 2.7 vs M3」「deepseek」「claude opus vs sonnet」時喚醒。本 skill 涵蓋赫米斯 2 條官方 routing 路徑、MiniMax 自家 cheap tier 切換、multi-provider 場景、3-tier 任務模型矩陣、3 個常見用戶誤區。"
version: 1.0.0
author: Hermes Agent (metacognitive-learner 2026-06-06)
metadata:
  hermes:
    tags: [cost-optimization, model-routing, delegation, miniMax, cron]
    triggers: [切換模型, 換 model, 便宜模型, 省 tokens, cheap model, model routing, multi-model, 2.7 vs M3, deepseek, sonnet, opus, haiku]
---

# Multi-Model Routing 速查

## 何時用這個 skill

- 用戶說「能不能按任務難度自動切換模型」
- 用戶說「想省 tokens」/「怎麼降低 API 費用」
- 用戶問「MiniMax 2.7、M3、DeepSeek V3.2 怎麼選」
- 用戶問「Claude Opus vs Sonnet vs Haiku 怎麼選」
- 用戶問「能不能對話中中途切換 model」
- 任何 cron / sub-agent 任務需要 cheap model 路由

## 核心原則（先講結論）

**省 token 的真正槓桿不是「找便宜模型」，而是「不該用 LLM 的部分就別用」**。三條優化路徑按效益排序：

| 路徑 | 成本節省 | 適用場景 | 觸發方式 |
|------|---------|---------|---------|
| 1️⃣ `no_agent=True` 跑 script | **100%（零 LLM token）** | 固定時間丟訊息、撈 RSS、跑 curl、查硬碟、查 log | cron job 用 `script=<path>` + `no_agent=true` |
| 2️⃣ `delegation.model` 設 cheap tier | **sub-agent 50-60%** | 簡單子任務（格式化、commit message、boilerplate） | `hermes config set delegation.model MiniMax-M2.7` |
| 3️⃣ cron job 自帶 `model` 參數 | **該 job 50-60%** | 該 cron 任務是 AI 介入但簡單 | `cronjob(action="create", model="MiniMax-M2.7", ...)` |

**If** 用戶問「省 tokens」→ **先問清楚任務本質**：
- 不需要 AI 判斷？→ 路徑 1️⃣
- 需要 AI 但很簡單？→ 路徑 2️⃣/3️⃣
- 需要 AI 且很複雜？→ 不必切換，用 M3/Opus

## 赫米斯 2 條官方 Routing 路徑

### 路徑 A：sub-agent delegation（影響 `delegate_task` 派出去的子代理）

```bash
# 設定 cheap model 給所有 sub-agent
hermes config set delegation.model MiniMax-M2.7
hermes config set delegation.provider minimax

# 驗證
hermes config show | grep -A 1 delegation
```

- **影響範圍**：主 session 透過 `delegate_task` 派出去的子代理
- **不影響**：主 session 自己的 model（見下面「主 session 不能中途切換」）
- **預設**：當前是空的，子代理會繼承主 session 的 model

### 路徑 B：cron job model 參數（影響該 cron job）

```bash
# 用 cronjob tool 建立
cronjob(
  action="create",
  schedule="0 9 * * *",
  prompt="總結昨天的 RSS 摘要",
  model="MiniMax-M2.7"   # ← 寫在這裡
)

# 或用 CLI
hermes cron create \
  --name "rss-summary" \
  --schedule "0 9 * * *" \
  --prompt "..." \
  --model MiniMax-M2.7
```

- **影響範圍**：僅該 cron job
- **限制**：同個 provider 內的 model 才能切（見下面「multi-provider 場景」）

## MiniMax 自家 Cheap Tier 速查（同 KEY 同 base_url 就能切）

**關鍵事實**：以下 model 全部用同一個 `MINIMAX_API_KEY` 同一個 `base_url`，**不需要多 provider 配置**：

| Model ID | Input ($/M) | Output ($/M) | 速度 | 適用 |
|----------|-------------|--------------|------|------|
| `MiniMax-M3`（旗艦） | 高 | 高 | 中 | 複雜推理、架構設計、security audit |
| `MiniMax-M2.7` | $0.279 | $1.20 | 中 | 通用 daily driver（70-80% 任務） |
| `MiniMax-M2.7-highspeed` | $0.279 | $1.20 | **100 tps** | 同 M2.7 但速度優先 |
| `MiniMax-M2.5` | 較 M2.7 便宜 | 較 M2.7 便宜 | 中 | 簡單任務 |
| `MiniMax-M2.1` | 最低 | 最低 | 中 | 最簡單任務 |

**價格對比**（來自 Infralovers 2026-02-19 實測 n=18）：
- Sonnet 4.6 替換 Opus 4.6：**57% 成本下降**
- 100% workflow compliance（沒有 step-skip）
- Sonnet 4.6 在 MCP-Atlas 61.3% **超越** Opus 4.6 59.5%

## 3-Tier 任務矩陣（適用 MiniMax、Claude、Anthropic SDK 相容模型）

| 任務類型 | 推薦 tier | 範例 | 為什麼 |
|---------|----------|------|--------|
| **簡單** | Haiku / M2.1 / M2.5 | commit message、formatting、boilerplate CRUD、string ops、Q&A、regex | 不需要 multi-step 推理 |
| **標準** | Sonnet / M2.7 | landing page、API route、test、refactor、content writing、standard code review、bug fix（有 repro） | 70-80% 日常開發工作 |
| **複雜** | Opus / M3 | architecture design、multi-file debug、security audit、framework upgrade、novel reasoning | 出錯成本 > token 成本 |

**反面教材**：用 Opus 跑 commit message → 60x 成本、零品質提升。

## 3 個常見用戶誤區（先講清楚避免誤導）

### 誤區 1：對話中能中途切換 model
**❌ 錯。** Hermes 設計上主 session 鎖死 model（prompt caching 考量）。切換只能：
- `/reset` 重置 session
- 開新 session：`hermes chat -m MiniMax-M2.7`
- Telegram/Discord 重啟 gateway

### 誤區 2：可以「自動依難度」切換主 session
**❌ 錯（就目前設計）。** 主 session 不能依任務切換。能切換的只有：
- sub-agent 透過 `delegate_task` 帶 `model` 參數
- cron job 自帶 `model` 參數

**If** 用戶堅持要主 session 自動切換
**Then** 解釋 prompt caching 失效成本（cache 重建可能比省下的還貴），建議改走 sub-agent 路由

### 誤區 3：DeepSeek / Claude / GPT 可以同個 key 通用
**❌ 錯。** 這是 multi-provider 場景：
- DeepSeek V3.2：自己的 API key + base_url
- Claude：自己的 API key + base_url（Anthropic API 或 Bedrock）
- MiniMax：自己的 API key + base_url

赫米斯主 session 同時間只能綁 1 個 provider。sub-agent / cron job 可平行跨 provider。

## Multi-Provider 場景怎麼處理

**If** 用戶想用 3 個 provider（MiniMax + DeepSeek + Claude）
**Then** 需要：
1. 三組 API key 都進 `.env`：`MINIMAX_API_KEY` / `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY`
2. config.yaml `providers:` 區段設定 3 個 provider entry
3. 主 session 仍只綁 1 個（建議用最強的 M3/Opus）
4. sub-agent / cron job 可指定不同 provider：
   ```python
   delegate_task(
     goal="...",
     model="MiniMax-M2.7",
     provider="minimax"
   )
   ```

## 驗證方法

```bash
# 1. 確認當前主 session model
hermes config show | grep -A 1 "◆ Model"

# 2. 確認 delegation 設定
hermes config show | grep -A 1 delegation

# 3. 確認 API key 與 base_url
grep -E "MINIMAX|DEEPSEEK|ANTHROPIC" ~/.hermes/.env | sed -E 's/=.{8,}$/=<redacted>/'

# 4. 確認 minimax 同 key 可用的 model（透過 curl 測試）
curl -s https://api.minimax.io/v1/models \
  -H "Authorization: Bearer $MINIMAX_API_KEY" | jq '.data[].id'
```

## 對話 SOP（用戶問「省 tokens」時的標準回應）

1. **先問任務本質**：
   - 「你說的任務是固定時間跑的（cron），還是對話中臨時跑的？」
   - 「這個任務需要 AI 判斷，還是固定邏輯？」
2. **按路徑推薦**：
   - 不需要 AI → 路徑 1️⃣（`no_agent=True`）
   - 需要 AI 但簡單 → 路徑 2️⃣/3️⃣（cheap tier）
   - 需要 AI 且複雜 → 不必切換
3. **明確告知限制**：
   - 主 session 不能中途切換
   - 同 provider 才能切 cheap tier（MiniMax 自家 OK）
   - multi-provider 場景需多組 key
4. **給具體指令**（不要只講原理）：
   - `hermes config set delegation.model MiniMax-M2.7`
   - cron job 建立時帶 `model="MiniMax-M2.7"`
5. **驗證**：
   - `hermes config show` 確認設定生效

## 外部驗證來源

- **Infralovers 2026-02-19**：Sonnet 4.6 vs Opus 4.6 實測 n=18，cheap tier 達 57% 成本下降、100% workflow compliance
- **duet.so 2026**：3-tier 模型路由指南，明確分 Haiku/Sonnet/Opus 任務對應
- **MiniMax API 文件**（platform.minimax.io/docs/api-reference/text-anthropic-api）：列出 M2.7-highspeed、M2.5、M2.1 同 key 可用
- **赫米斯內部**：`sparc-methodology/.../intelligence-route` skill 的 3-tier 設計（注意：這是 sparc 套件路由，**不是赫米斯內建 delegation**，兩者不同）

## 相關檔案

- `references/minimax-model-catalog.md` — MiniMax 自家 model 完整目錄、價格、context length
- `references/cost-optimization-2026.md` — 2026 年 LLM 模型路由成本優化研究彙整（含 Infralovers、duet 實測數據）
- `references/cheap-model-quickstart.md` — 5 分鐘設定 cheap tier 的 step-by-step（含驗證指令）
- `references/cron-no-agent-vs-cheap-model.md` — cron job 三種模式（no_agent / full_agent_cheap / full_agent_premium）決策樹
