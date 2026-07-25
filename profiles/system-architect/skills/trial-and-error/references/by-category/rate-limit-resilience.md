# Rate Limit Resilience（費率限制復原能力）

> **建立時間**：2026-06-07
> **觸發情境**：MiniMax Token Plan Plus 9.692M tokens/5 小時額度在高峰時段耗盡，HTTP 429 `usage limit exceeded` 連續出現
> **條目數**：1

---

## MiniMax 額度耗盡時的 fallback 機制

**發現時間**：2026-06-07

**症狀**：
```
HTTP 429: usage limit exceeded, 5-hour usage limit reached for Token Plan Plus (9692000/9692000 used)
```

48 次/24 小時，集中在 10am-6pm 高峰時段。

**根因**：MiniMax Token Plan Plus 的額度是固定的 9.692M tokens/5 小時，不是動態調整的 rate limit。
當額度用完時，無論等多久下次請求都會失敗。

**解法**：

1. **設定 fallback_providers**（`~/.hermes/config.yaml`）：
```yaml
fallback_providers:
  - provider: openrouter
    model: anthropic/claude-sonnet-4-20250514
```

2. **在 `~/.hermes/.env` 設定 OpenRouter API key**

3. **驗證**：`hermes chat --provider openrouter --model 'anthropic/claude-sonnet-4-20250514' -q "ping"`

**預防**：
- 監控 `grep -c "429\|rate.limit" ~/.hermes/logs/errors.log`，超過 10 次/天就要考慮設定 fallback
- 考慮升級 MiniMax 額度或使用多個 provider

**相關條目**：[[hermes-internal#jittered_backoff 實作在 agent/conversation_loop.py:3347]]

---

## Quota Exhaustion vs Transient Rate Limit

**發現時間**：2026-06-07

**兩種不同的 429 處理方式**：

| 類型 | 錯誤訊息 | 解決方案 |
|------|----------|----------|
| **Transient rate limit** | `rate limit exceeded, Retry-After: 5` | jittered_backoff（等一下就好） |
| **Quota exhausted** | `usage limit exceeded (9692000/9692000 used)` | fallback_providers 或等額度重置 |

**If→Then**：
- **If** 看到 429 且訊息包含 `9692000/9692000` **Then** 這是 quota exhaustion，jittered_backoff 無法解決
- **If** 看到 429 且有 `Retry-After` header **Then** 這是 transient rate limit，jittered_backoff 有效

**已知問題**：Issue #27719 — fallback activation 時的 NameError bug，fallback 可能無法正常激活

**相關條目**：[[hermes-tier-router#Tier-0：Rate Limit Fallback（2026-06-07 新增）]]