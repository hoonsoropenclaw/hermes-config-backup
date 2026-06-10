# Provider / Model 設定的驗證陷阱（2026-06-06 教訓）

Phase 1.5 跟 Phase 4 跑出「設定完成」結論時，**必讀這份**。列舉設定 provider / model 時容易誤判通過的場景。

## ❌ 不可信的「驗證通過」

| 你以為的驗證 | 為什麼不可信 |
|---|---|
| `hermes chat -q "ping" --provider X` 回 pong | minimax 對 "ping" 也能回 pong，這是 fallback 跑出來的 |
| 跑單一 LLM-driven cron job 看沒報錯 | cron 失敗不阻斷、只標 `skipped` |
| sub-agent 回報「我用了 X model」 | hermes dispatcher 對不認得的 provider 會靜默 fallback、卻回報用了指定 model |
| 設定檔加了 `provider: deepseek` 跟 `model: deepseek-chat` | .env 有 key 不代表 hermes 內建有該 provider 註冊（看 `hermes_cli/config.py`） |
| 跑 `curl https://api.provider.com/v1/models` 回 200 | 只代表 API key 有效，不代表 hermes 真的會走那個 provider |
| 看 token 統計顯示某些 model 有消耗 | 可能 dispatcher 真的寫了該 model 名稱但實際 fallback |

## ✅ 真的驗證

1. **直接打 provider 原生 API 驗證 key 有效**（排除 .env 拼錯）
2. **看 hermes 源碼有沒有 provider 註冊**（`grep -rni <provider> hermes-agent/agent/ hermes-agent/hermes_cli/`）
3. **派 sub-agent 跑真實任務、看輸出風格對不對**：
   - DeepSeek 典型 `<think>` 標籤、有 reasoning chain
   - Anthropic 會有 reasoning 區塊
   - OpenAI 不會有 thinking 標籤
   - minimax M3 跟 M2.7 風格差異小（兩個都是 minimax 家族）
4. **比對耗時 / 價格指標**：cheap tier 應該明顯比 premium 快 5-10x
5. **交叉驗證** sub-agent 真實輸出內容（不是只看 dispatcher 回報的「model 欄位」）

## If→Then 規則

- **If** 接到任務「把 X provider 加進 dispatch」**Then** 走完整 5 步驗證，**不要只 ping**
- **If** 「ping pong」測試通過就以為接好 **Then** 提醒自己：簡單 prompt 連 fallback 都能回
- **If** sub-agent 回報「用了 X model」但 LLM 輸出風格不像 X **Then** 標記為「routing 失敗」並走 5 步驗證
- **If** 發現 hermes 沒內建某 provider **Then** 給使用者三個解法（patch source / proxy / 放棄），不要默默 fallback 還自報告成功
- **If** 配置聲稱的「✅（已設）」**Then** 一律附驗證命令的真實輸出

## 對話範例（2026-06-06 真實失敗案例）

```
Step 1: 規劃三層 tier（cheap=DeepSeek、standard=M2.7、premium=M3）
Step 2: 設 .env DEEPSEEK_API_KEY、跑 `hermes chat -q "ping" --provider deepseek` → pong 6 秒
        ⚠️ 這裡就誤判「接好了」
Step 3: 派 3 個 sub-agent 跑 3 個不同 tier
        ❌ 3 個全部回退到 M2.7（tier 1 跟 tier 3 都沒生效）
Step 4: 追查 4 個並行手段：
        - curl https://api.deepseek.com/v1/models → 200（key 真有效）
        - grep deepseek hermes-agent/agent/ hermes-agent/hermes_cli/ → 找不到
          → 根因：hermes 沒 deepseek provider 註冊
        - 3 個 sub-agent 耗時分別 27s/31s/134s，但全部跑同一 model
Step 5: 接受現實、放棄 cheap tier、降階到 2-tier
```

## 跟其他 Phase 的關聯

- Phase 1.5：cron jobs 健康掃描時也適用（cron 失敗只標 `skipped` 不阻斷，要用 `hermes cron list | grep error` 才看得到）
- Phase 3 工具軌：測試 AI 工具時，「工具能跑」不等於「工具產生我預期的輸出」
- Phase 4.5 SOP validator：只檢查輸出**格式**，不檢查**真實性**（自我審查要看真實命令輸出）

## 教訓溯源

完整 5-step 設定失敗根因追查 SOP，記在 `trial-and-error/references/by-category/hermes-config-tuning.md` 的「完整 L3 教訓：Tier routing 設定→驗證→失敗循環」章節。

## ⚠️ 2026-06-07 新增：Quota Exhaustion vs Transient Rate Limit

這是另一種「設定看起來沒問題但實際上失效」：

| 類型 | 原因 | 解決方案 |
|------|------|----------|
| **Transient rate limit**（暫時性） | 服務暫時擁擠、短暫超載 | jittered_backoff（等一下就好）|
| **Quota exhausted**（額度耗盡） | MiniMax 9.692M tokens/5 小時額度用完 | fallback_providers 設定備援 provider |

### 如何區分

```
# Transient 429 — 有 Retry-After header，等一下就好
HTTP 429: rate limit exceeded, Retry-After: 5

# Quota exhausted 429 — 無 Retry-After，永遠失敗
HTTP 429: usage limit exceeded, 5-hour usage limit reached for Token Plan Plus (9692000/9692000 used)
```

### 為什麼這個陷阱更危險

- **Transient rate limit**：jittered_backoff 真的能解決，等幾秒到幾十秒就好
- **Quota exhausted**：jittered_backoff 會瘋狂 retry，每秒都在燒僅剩的 retry 預算，卻永遠失敗

### 如果你的 quota 經常耗盡

考慮設定 `fallback_providers` 指向 OpenRouter 作為備援：

```yaml
fallback_providers:
  - provider: openrouter
    model: anthropic/claude-sonnet-4-20250514
```

詳見 `hermes-tier-router/references/rate-limit-fallback.md`。
