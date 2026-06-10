# API 驗證結果（2026-05-30 實測）

## 金融 API 驗證

| API | Endpoint 關鍵點 | 驗證結果 |
|-----|---------------|---------|
| Twelve Data | `https://api.twelvedata.com/price` — **不是 `/v1/`**，否則 404 | ✅ MSFT=$448.64 |
| Alpha Vantage | `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=` | ✅ AAPL=$312.06 |
| FRED | `https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=&file_type=json` | ✅ DFF=1.13% |
| Finnhub | `https://finnhub.io/api/v1/quote?symbol=AAPL&token=` | ✅ AAPL=$312.06 |
| FMP | — | ❌ v4 免費版已停用，勿設定 |

## 搜尋 API 驗證

| API | Endpoint | 驗證結果 |
|-----|----------|---------|
| Ollama Web Search | `POST https://ollama.com/api/web_search`（無 `/v1/`） | ✅ 3 results |
| Tavily | `POST https://api.tavily.com/search` | ✅ 3 results |

## 認證 API 驗證

| API | 驗證方式 | 結果 |
|-----|---------|------|
| GitHub PAT | `curl -H "Authorization: token ghp_..." https://api.github.com/user` | ✅ @hoonsor |
| Vercel | `curl -H "Authorization: Bearer vcp_..." https://api.vercel.com/v2/user` | ✅ @hoonsor (hobby) |
| ClawHub | Token 格式檢查 `clh_...` | ✅ 格式正確 |

## approvals.mode YAML 陷阱

`hermes config set approvals.mode off` 會寫成 YAML 布林 `false`，而不是字串 `'off'`。

**正確做法**：直接用 `sed` 寫入單引號包住的字串：
```bash
sed -i "s/^  mode: false$/  mode: 'off'/" ~/.hermes/config.yaml
```

驗證：`python3 -c "import yaml; print(repr(yaml.safe_load(open('~/.hermes/config.yaml'))['approvals']['mode']))"`
應輸出：`'off'`

## 寫入 .env 流程（2026-05-30 確認）

1. `cat ~/.hermes/.env` 確認目前狀態
2. 直接 `echo >> ~/.hermes/.env` 追加（避免 `hermes config set` 寫错格式）
3. 寫入後立即用 curl/Python 測試，不要只靠 `hermes status`
4. API keys 統一寫入 `~/.hermes/.env`，不是 `~/.openclaw/...`
