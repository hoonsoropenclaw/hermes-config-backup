# weather_bot.py — Telegram 天氣機器人

## 用途

Telegram 機器人,接收使用者文字 → 解析城市名 → 呼叫 OpenWeatherMap API → 回傳格式化天氣。

## 設計原則(基於 Antigravity Architect 2026-07-25 回饋)

1. **善用現成方案** — 用 `python-telegram-bot 22.6`(已裝在 hermes venv) + 標準 `urllib`,不重造輪子
2. **預設安全** — 缺 token → 拒絕啟動;`--check` 模式只驗證不通報;`--mock` 模式完全離線
3. **結構化日誌** — JSONL,便於 log aggregator / journald / 自家工具解析
4. **Root cause not just mitigation** — 失敗分類為 `network|timeout|4xx|5xx|parse|empty|invalid`,每類訊息附補救建議
5. **自我驗證** — `test-weather-bot.py` 提供 44 個 unittest 涵蓋輸入清洗、城市啟發式、失敗格式化、Logger、Settings、build_application

## 環境變數

| 變數 | 必要 | 預設 | 說明 |
|------|------|------|------|
| `TELEGRAM_BOT_TOKEN` | 正式啟動必填 | — | BotFather 給的 token |
| `OPENWEATHER_API_KEY` | 正式啟動必填 | — | https://openweathermap.org/api 免費 key |
| `OWM_UNITS` | 選填 | `metric` | `metric`/`imperial`/`standard` |
| `OWM_LANG` | 選填 | `zh_tw` | `zh_tw`/`zh_cn`/`en` |
| `HTTP_TIMEOUT` | 選填 | `10` | API 逾時秒數 |
| `LOG_FILE` | 選填 | — | JSONL 日誌路徑(預設無檔案,只到 stderr) |

## CLI

```bash
# 正式啟動
TELEGRAM_BOT_TOKEN=... OPENWEATHER_API_KEY=... \
  ~/.hermes/hermes-agent/venv/bin/python3 weather_bot.py

# 離線檢查(驗證環境/網路/日誌可寫)
~/.hermes/hermes-agent/venv/bin/python3 weather_bot.py --check

# 離線模擬互動(不打 Telegram/OWM)
~/.hermes/hermes-agent/venv/bin/python3 weather_bot.py --mock

# 跑單元測試
~/.hermes/hermes-agent/venv/bin/python3 test-weather-bot.py
```

## 路由器 vs 系統服務

- **本機長時間運行**:`~/.local/bin/weather-bot` wrapper 即可,或用 `systemd --user` service
- **背景 long-polling**:PTB 22 內建 reconnect,不需要額外 supervisor
- **備援 / Webhook**:若改用 webhook 模式,需 reverse proxy(Nginx/Caddy),留待未來實作

## 已知限制

- 單一天氣 API provider(OpenWeatherMap);rate limit 60/min on free plan
- 訊息上限 200 字,城市名啟發式 80 字
- JSON 解析依賴 OWM 回傳格式;若回傳重大 schema change 會走 `parse` 錯誤分支
- 不支援 inline mode / group privacy 進階設定

## 為什麼選擇 python-telegram-bot 而非其他

- 22.6 已在 hermes venv 內,不需新裝
- PTB v22 內建 `Application` + `run_polling` 自動 reconnect
- 跟 Architect 提到的「善用現成方案」原則一致
- 自寫 raw Bot API 會失去 dialog handler / persistence / context typing 等功能
