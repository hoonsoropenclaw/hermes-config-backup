# MiniMax Model 目錄速查

> 來源：platform.minimax.io/docs/api-reference/text-anthropic-api（2026-06 抓取）

## 支援的 Model ID（同 MINIMAX_API_KEY + 同 base_url 即可切換）

| Model ID | Context | 備註 |
|----------|---------|------|
| `MiniMax-M3` | 1,000,000（config 設定） | 旗艦，支援 text/image/video/tool use/thinking |
| `MiniMax-M2.7` | 204,800 | daily driver |
| `MiniMax-M2.7-highspeed` | 204,800 | **100 tps**，同 M2.7 品質 |
| `MiniMax-M2.5` | — | 比 M2.7 便宜 |
| `MiniMax-M2.5-highspeed` | — | M2.5 + 速度 |
| `MiniMax-M2.1` | — | 簡單任務 |
| `MiniMax-M2.1-highspeed` | — | M2.1 + 速度 |
| `MiniMax-M2` | — | 最便宜 |
| `MiniMax-M2-Her` | — | 變體 |

## 價格（截至 2026-06，pricepertoken.com 抓取）

| Model | Input ($/M) | Output ($/M) |
|-------|-------------|--------------|
| MiniMax M2.7 | 0.279 | 1.20 |
| MiniMax M3 | 較 M2.7 高 | 較 M2.7 高 |

## 各 model 支援的 content block 類型

| Model | text | image | video | tool use | tool result | thinking |
|-------|------|-------|-------|----------|-------------|----------|
| `MiniMax-M3` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `MiniMax-M2.7/2.5/2.1/2` | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |

**⚠️ 重要限制**：M2.7 及以下**不支援 image/video input**。如果任務需要看圖，必須用 M3。

## 設定範例（用戶 .env 現狀）

```bash
# 從 ~/.hermes/.env 抓取（已 redacted）
MINIMAX_API_KEY=<redacted>
MINIMAX_BASE_URL=<redacted>
```

當前 `config.yaml`：
```yaml
model:
  default: MiniMax-M3
  provider: minimax
  base_url: https://api.minimax.io/anthropic
  context_length: 1000000
```

## 切換 model 的 3 種方式

```bash
# 1. 改主 session default（要 /reset）
hermes config set model.default MiniMax-M2.7

# 2. 開新 session 時指定
hermes chat -m MiniMax-M2.7

# 3. cron job 自帶 model 參數
hermes cron create --name "rss" --schedule "0 9 * * *" --model MiniMax-M2.7 --prompt "..."
```

## 驗證 model 是否可用

```bash
# 列舉所有可用 model
curl -s https://api.minimax.io/v1/models \
  -H "Authorization: Bearer $MINIM...EY" | jq '.data[].id'

# 簡單 ping 測試
curl -s https://api.minimax.io/v1/messages \
  -H "x-api-key: $MINIM...EY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M2.7","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' | jq '.content[0].text'
```

## 與 Anthropic SDK 相容性

✅ 赫米斯走 Anthropic API 格式（`api_mode="anthropic"`），所以 MiniMax 自家 model 全部用 `messages` 格式（不是 OpenAI chat.completions）。
