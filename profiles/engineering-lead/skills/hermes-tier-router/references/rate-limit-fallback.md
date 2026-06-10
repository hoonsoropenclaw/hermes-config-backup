# Rate Limit Fallback — MiniMax 額度耗盡時的備援機制

> **建立時間**：2026-06-07
> **觸發情境**：MiniMax Token Plan Plus（9.692M tokens/5 小時額度）在高峰時段耗盡，導致 HTTP 429 `usage limit exceeded`
> **目標**：當 MiniMax 額度耗盡時，自動或手動切換到備援 provider

---

## 問題識別

### 症狀

當 MiniMax 額度耗盡時，錯誤日誌會出現：

```
HTTP 429: usage limit exceeded, 5-hour usage limit reached for Token Plan Plus (9692000/9692000 used)
```

這不是普通的 rate limit（短暫擁擠），而是**額度本身用完了**。

### 受影響範圍

2026-06-06 觀察：48 次 429 錯誤/24 小時，集中在 10am-6pm 高峰時段。
`metacognitive-learner-24h` cron job 是主要受影響者，因為它每 2 小時執行一次。

### 為什麼 jittered_backoff 無法解決

`agent/conversation_loop.py:3347` 的 jittered_backoff 邏輯：

```python
wait_time = _retry_after if _retry_after else jittered_backoff(retry_count, base_delay=2.0, max_delay=60.0)
```

這是設計給「等一下就會好」的暫時性 rate limit。當額度本身耗盡時，無論等多久，下次請求還是會失敗。

---

## 解決方案：fallback_providers

### 設定步驟

**Step 1：確認 OpenRouter API key**

```bash
# 在 ~/.hermes/.env 加入
OPENROUTER_API_KEY=sk-or-v1-...
```

**Step 2：編輯 ~/.hermes/config.yaml**

```yaml
fallback_providers:
  - provider: openrouter
    model: anthropic/claude-sonnet-4-20250514
```

**Step 3：驗證設定**

```bash
hermes chat --provider openrouter --model 'anthropic/claude-sonnet-4-20250514' -q "ping"
```

**Step 4：檢查 fallback 是否生效**

當 MiniMax 返回 429 時，觀察 hermes logs：

```bash
hermes logs --level warning | grep -i fallback
```

---

## 已知問題：Issue #27719

**描述**：當 primary provider（MiniMax）額度耗盡時，fallback provider 激活時可能出現 NameError：

```
NameError: name '_pool_may_recover_from_rate_limit' is not defined
```

**影響**：fallback 無法正常激活，agent 直接失敗。

**目前 workaround**：
1. 重啟 hermes（`/exit` 後再進）
2. 手動執行 `hermes config set fallback_providers [...]`
3. 或等待 MiniMax 額度重置（5 小時 window）

**修復狀態**：已回報 GitHub，等待官方修復。

---

## 額度監控腳本

```bash
#!/bin/bash
# rate_limit_check.sh — 檢查 429 錯誤頻率
COUNT=$(grep -c "429\|rate.limit" ~/.hermes/logs/errors.log 2>/dev/null || echo "0")
echo "429 errors in errors.log: $COUNT"
if [ "$COUNT" -gt 10 ]; then
  echo "⚠️ Rate limit errors elevated — consider checking MiniMax quota"
fi
```

---

## If→Then 規則

- **If** MiniMax 返回 429 且訊息包含 `9692000/9692000` **Then** 這是額度耗盡，jittered_backoff 無效，需要設定 fallback provider
- **If** fallback 激活失敗且錯誤是 NameError **Then** 這是 Issue #27719，嘗試重啟 hermes 或手動等待額度重置
- **If** 需要驗證 fallback provider 是否正常 **Then** 執行 `hermes chat --provider openrouter --model 'claude-sonnet-4' -q "ping"`

---

## 跨 session 驗證

| 日期 | 觀察 | 修復 |
|------|------|------|
| 2026-06-06 上午 | 48 次 429/24h，集中在 10am-6pm | 設定 fallback_providers（待驗證） |
| 2026-06-07 | 驗證 fallback 是否生效 | 待確認 |

---

## 相關檔案

- `agent/conversation_loop.py:3347` — jittered_backoff 實作
- `agent/retry_utils.py` — jittered_backoff 函式
- `~/.hermes/config.yaml` — fallback_providers 設定位置
- `~/.hermes/logs/errors.log` — 429 錯誤日誌