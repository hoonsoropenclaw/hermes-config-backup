---
name: hermes-tier-router
description: "赫米斯 2-tier model 路由決策表。赫米斯主 session 在呼叫 delegate_task 前讀這份，依任務難度從 standard / premium 兩層選 model。standard→minimax/MiniMax-M2.7（預設，不指定就走這層）、premium→minimax/MiniMax-M3（需明確指定）。2026-06-06 第三次修訂：放棄 deepseek cheap tier（hermes 內建沒 deepseek provider，會靜默 fallback）。"
version: 3.0.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [model-routing, cost-optimization, delegation, sub-agent, tier]
    triggers: [delegate_task, model-selection, batch-tasks]
---

# 2-Tier Model 路由（赫米斯自用版）

# ⚠️ 必讀：4 個驗證手段（避免 ping pong 假接）

**If** 看到「簡單 ping 通過 → 認為 provider 接好」**Then** 提醒自己：那不算驗證。

完整 4 個驗證手段（詳見 `trial-and-error/references/by-category/hermes-config-tuning.md` 的「Provider 真的接上 ≠ 設了 API key」條目）：

1. **直接打原生 API** 驗證 key 有效（`curl -H "Authorization: Bearer *** <provider>/v1/models`）
2. **看 hermes 源碼** 有沒有該 provider 註冊（`grep -rni <provider> hermes-agent/agent/ hermes-agent/hermes_cli/`）
3. **派 sub-agent 跑真實任務**、對照該 model 的**輸出特徵**（DeepSeek `<think>` 標籤、minimax 沒 thinking 區塊）
4. **比對耗時 / 價格指標**（cheap tier 應該快很多）

歷史教訓：2026-06-06 v1.0 寫「deepseek 接好」實際是 hermes 靜默 fallback 到 minimax 跑出來。

# ⚠️ 2026-06 模型版本現況

DeepSeek 在 2026/6 已經**沒有 V3.2**（這是早期 2025 末到 2026 初的版本）：
- **deepseek-v4-flash**（便宜、快）
- **deepseek-v4-pro**（高品質、有 reasoning mode）

**If** 看到外部文件提到「DeepSeek V3.2」**Then** 那是 2025 末/2026 初的版本，2026/6 起的 model id 已經是 v4-flash / v4-pro。

**If** 要在 sub-agent 內用 curl 直接打 DeepSeek **Then** 用 `https://api.deepseek.com/v1/chat/completions` 跟 `model: "deepseek-chat"`（這個 id 在 V3/V4 都對應到當前 default chat model，會路由到 v4-flash 或 v4-pro）。

給赫米斯主 session 自己在呼叫 `delegate_task` 時當決策表用。

## 為什麼 2-tier 不是 3-tier

**歷史**（2026-06-06）：
- v1.0：嘗試 3-tier，cheap=deepseek-v3.2、standard=minimax-M2.7、premium=minimax-M3
- 測試發現：`delegate_task(..., provider="deepseek")` 會**靜默 fallback**到 `delegation.model`，cheap tier 完全沒生效
- **根因**：`hermes-agent` 源碼沒 deepseek provider 註冊，dispatcher 對不認得的 provider 自動 fallback
- 結論：放棄 cheap tier，剩 standard/premium 兩層（都走 minimax，hermes 內建支援）

## 2-Tier 對照（2026-06-06 最終版）

| Tier | Provider | Model | 適用任務 | 何時用 |
|------|----------|-------|---------|--------|
| **standard**（預設） | minimax | MiniMax-M2.7 | 一般程式碼生成、bug 修復、單檔重構、單元測試、文件撰寫、結構化資料萃取、批次轉換 | 任務是「單一檔案修改」或「明確輸出格式」 |
| **premium** | minimax | MiniMax-M3 | 跨檔重構、架構決策、複雜除錯、安全審查、需要 SOP 服從的後設認知 | 任務影響多檔、需要跨模組推理、有架構決策、SOP 服從性要求高 |

**預設行為**：`delegation.model = MiniMax-M2.7` 已經是全域預設，**不主動給 model 參數就會走 standard**。要升 premium 才需要明確指定 `model="MiniMax-M3"`。

## 版本演進（給未來赫米斯）

| 版本 | 日期 | 結構 | 結果 |
|---|---|---|---|
| v1.0 | 2026-06-06 早 | 3-tier（cheap=DeepSeek、standard=M2.7、premium=M3）| ❌ DeepSeek 沒接上、3 個 sub-agent 全跑 M2.7 |
| v2.0 | 2026-06-06 中 | 同上 + 加「已知問題」章節 | 知道 root cause 但沒降階 |
| v3.0 | 2026-06-06 晚 | 2-tier（放棄 cheap）| ✅ 乾淨，僅留標準 + 進階 |
| v4.0 | 2026-06-07 | 2-tier + Tier-0 fallback（當 MiniMax 額度耗盡時）| 新增 fallback provider 機制 |

**給未來赫米斯的提醒**：如果未來想再加 cheap tier（不論是 DeepSeek 或其他 provider），**先讀 `metacognitive-learner/references/provider-verify-pitfalls.md`**。本 skill 從 v1.0 到 v3.0 的 3 次修訂就是踩了那份文件列的坑。

## 決策流程（赫米斯 dispatch sub-agent 時跑這套）

```
接到要 delegate 的任務,先問:
│
├─ 任務是「標準 coding」(單檔、可預測結果)?
│   ├─ 寫單元測試、簡單重構、文件生成、批次資料處理
│   └─ → 不指定 model（繼承全域 M2.7，standard）
│
└─ 任務是「跨檔、架構、複雜」?
    ├─ 影響多檔、需要細緻判斷、SOP 服從性要求高
    └─ → 明確指定 model="MiniMax-M3"（premium）
```

## ⚠️ 重要限制（2026-06-06 新增）：delegate_task model 參數不生效

**發現**：`delegate_task(goal=..., model="MiniMax-M3")` 這個語法**接受但完全忽略** model 參數。
sub-agent 永遠走 parent session 的 model 或 `delegation.model`。

**根因**：`delegate_tool.py` 的 `DELEGATE_TASK_SCHEMA` 任務屬性中沒有 `model` 欄位（第 2438-2463 行），
所有 model 參數被靜默忽略後 fallback 到 parent model。

**受影響的 issue**：#17685、#35409、#11999、#12440（全部確認為同一 bug）

**現在怎麼做 premium routing**：  
唯一繞過方式是**在赫米斯主 session 發送 task 前**，先把 `delegation.model` 改成 M3，
派完後再改回 M2.7。語法：
```python
# 派 premium task 前
import subprocess
subprocess.run(['hermes', 'config', 'set', 'delegation.model', 'MiniMax-M3'], check=True)
# 派 task
delegate_task(goal="重構這 3 個檔案的 auth 中間件", toolsets=["file", "terminal", "search"])
# 派完改回 standard
subprocess.run(['hermes', 'config', 'set', 'delegation.model', 'MiniMax-M2.7'], check=True)
```

**代價**：這是破壞性全域改動，中間所有 sub-agent 都走 M3，無法同時跑 standard + premium 並行。

**結論**：目前 2-tier routing 的 premium 語法（`model="MiniMax-M3"`）是假的。  
hermes-tier-router skill 目前的價值：**標準 tier 有效（全域預設 M2.7），premium tier 無法用**。  
等官方修好 #17685 後再更新這份 skill。

## 實作語法（delegate_task 呼叫）

**standard（不指定 model，繼承全域 M2.7）**：✅ 有效
```
delegate_task(
  goal="幫這個 Python 函式寫單元測試",
  toolsets=["file", "terminal"]
)
```

**premium（明確指定 M3）**：❌ currently broken（model 參數被忽略）
```
delegate_task(
  goal="重構這 3 個檔案的 auth 中間件、保持向後相容",
  model="MiniMax-M3",
  provider="minimax",
  toolsets=["file", "terminal", "search"]
)
```

## 路由決策的 If→Then 規則

- **If** 任務是「單一檔案修改」（bug 修、加 feature、寫 test、批次處理）**Then** 用 standard（不指定）
- **If** 任務影響多檔、需要跨模組推理、有架構決策 **Then** 用 premium
- **If** 任務是「需要 SOP 服從性」（如後設認知、技能學習）**Then** 用 premium
- **If** 不知道選哪個 **Then** 用 standard（預設安全）

## ⚠️ 重要事實：不要加第三層 cheap tier

**這份 skill 2026-06-06 v1.0 創建時**曾經嘗試加 deepseek-v3.2 當 cheap tier。測試證明：

| 驗證方式 | 結果 |
|---------|------|
| `hermes chat -q "ping" --provider deepseek` | 回 pong 6 秒 ✅（但這是 fallback 到 minimax 跑出來的） |
| `delegate_task(..., provider="deepseek", model="deepseek-chat")` | sub-agent 回報「用 M2.7 跑的」 ❌（靜默 fallback） |
| `curl https://api.deepseek.com/v1/models` | 回 200，2 個 model ✅（key 真的有效） |

**結論**：
- DeepSeek API key 真的有效
- 但 hermes 內建**沒有** deepseek provider 註冊
- `delegate_task` 對不認得的 provider 會靜默 fallback
- 真要 deepseek 進 cheap tier 需要：(1) patch hermes source 加 provider 註冊、(2) 或裝 LiteLLM proxy 包成 OpenAI 相容 API、(3) 或在 sub-agent 內用 terminal 直接 curl deepseek API

**目前決定**：放棄 cheap tier，等未來需要時再做 (1) 或 (2)。

**教訓**（已在 `hermes-config-tuning` 試誤檔 L3 條目化）：
- 簡單 ping 通過 ≠ provider 接好
- 驗證要附真實任務的真實輸出 + 對照該 model 輸出特徵
- API key 在 .env ≠ hermes dispatcher 認得該 provider
- 任何「✅」聲稱要附驗證命令的真實輸出

## Tier-0：Rate Limit Fallback（2026-06-07 新增）

**問題**：MiniMax Token Plan Plus 的 9.692M tokens/5 小時額度在高峰時段（10am-6pm）會耗盡，
此時 HTTP 429 訊息是 `usage limit exceeded (9692000/9692000 used)`，
jittered_backoff 無法解決「額度本身不足」的問題，只會浪費 retry 預算。

**解決方案**：設定 `fallback_providers` 讓 Hermes 在 MiniMax 額度耗盡時自動切換到備援 provider。

### 設定方式

在 `~/.hermes/config.yaml` 加入：

```yaml
fallback_providers:
  - provider: openrouter
    model: anthropic/claude-sonnet-4-20250514
    # 或其他備援 model
```

並在 `~/.hermes/.env` 設定 `OPENROUTER_API_KEY`。

### 驗證方式

```bash
# 測試 OpenRouter 連線
hermes chat --provider openrouter --model 'anthropic/claude-sonnet-4-20250514' -q "ping"
```

### 已知限制

- Hermes 的 fallback 機制在**額度耗盡（daily quota exhausted）** 時可能觸發 Issue #27719（NameError bug in credential pool logic）
- fallback 激活路徑在 `agent/conversation_loop.py`，當 primary 429 時會嘗試切換到 `fallback_providers`
- 如果 fallback 也失敗，會進入第二層 fallback（需確認 config.yaml 的 `fallback_providers` 順序正確）

### If→Then 規則

- **If** MiniMax 返回 HTTP 429 且訊息包含 `usage limit exceeded`（9692000/9692000）**Then** 這是額度耗盡，jittered_backoff 無法解決，需要等額度重置（5 小時 window）或手動切換到 fallback provider
- **If** 需要驗證 fallback 是否生效**Then** 檢查 `hermes logs --level warning` 看是否有 `fallback` 相關訊息
- **If** fallback activation 失敗且錯誤是 NameError**Then** 這是 Issue #27719，需要重啟 hermes 或手動設定備援

## 與 claude-flow `intelligence-route` skill 的關係

`intelligence-route` skill（裝在 sparc-methodology 套件裡）背後的 `hooks_route` / `hooks_model-route` 是 **claude-flow MCP 工具**，本機沒裝，無法直接呼叫。
那份 skill 內建的 Tier 表是 Haiku/Sonnet/Opus（Anthropic 三層），跟我們的 minimax/M2.7 vs minimax/M3 不同 provider。

**結論**：
- 不要靠 `intelligence-route` 的 MCP 工具（沒裝）
- 赫米斯自己依這份決策表 dispatch 即可
- 未來如果裝了 claude-flow，可考慮 patch 它內建的 Tier 表對應到 minimax 兩層

## 配套工具

- `~/.hermes/.env` 有 minimax key ✅（已驗證 A 階段測試 ping pong 6 秒）
- `~/.hermes/config.yaml` 的 `delegation.model = MiniMax-M2.7` ✅
- `hermes cron list` 確認 cron jobs 用對的 model（metacognitive-learner-24h 已改 M2.7）✅
- `~/.hermes/.env` 有 `DEEPSEEK_API_KEY` ✅（已驗證可 curl 200），但**沒接進 hermes dispatcher**，不要靠它
- Rate limit 監控：`grep -c "429\|rate.limit" ~/.hermes/logs/errors.log`（2026-06-07 測試：48 次/24 小時）

## 支援檔案

- `references/delegate-tool-model-bug.md` — `delegate_task model` 參數不生效的已確認 bug 記錄（根因、影響範圍、目前無 workaround）
- `references/provider-verify-pitfalls.md`（在 `metacognitive-learner` skill）— provider 設定時的驗證陷阱，設定前必讀
- `references/rate-limit-fallback.md`（2026-06-07 新增）— MiniMax 額度耗盡时的 fallback 設定步驟與已知問題

## 自我審查

- **是否被遵守？** 2026-06-06 v3.0 最終版，下次赫米斯 dispatch sub-agent 套用
- **可量測效益？** standard 全域預設 = 所有 sub-agent 自動降階；premium 升級需明確指定 = 重要任務仍走 M3
- **若用錯 model 出包？** 走 `delegate_task` 失敗 → 看 sub-agent 回覆品質 → 下次重分類
- **歷史教訓**：v1.0 失敗的 deepseek 整合已記進 trial-and-error `hermes-config-tuning.md`，避免重蹈覆轍
