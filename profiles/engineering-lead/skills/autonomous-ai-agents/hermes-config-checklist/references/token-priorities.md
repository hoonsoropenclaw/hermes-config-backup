# Token 優先順序詳細說明

## 目前狀態（2026-05-30 更新）

### ✅ 已設定並驗證正常
- **MiniMax API Key** — 主模型供應商
- **GitHub PAT** (`ghp_ak...`) — @hoonsor
- **Vercel** (`vcp_...`) — @hoonsor (hobby plan)
- **Alpha Vantage** — AAPL 即時報價 ✅
- **FRED** — 聯邦基金利率 DFF=1.13% ✅
- **Finnhub** — AAPL 即時報價 ✅
- **Twelve Data** — MSFT=$448.64 ✅
- **ClawHub Token** — AI 技能市場認證 ✅

### ⚠️ 已停用
- **FMP (Financial Modeling Prep)** — v4 已全面付費，免費版停用

### ❌ 未設定
- Tavily, Firecrawl, OpenAI, DeepSeek, Gemini, Discord Bot

---

## P0 — 立竿見影（設定後立即能用）

### 1. GitHub (`gh` CLI)
```
設定指令: gh auth login
啟用技能: github, github-pr-workflow, github-issues, github-code-review
價值: 程式碼管理、PR review、工作自動化
```

### 2. Tavily 搜尋
```
取得: https://tavily.com → 免費額度 1000/月
設定: hermes config set secrets.tavily.key your_key
價值: 網路搜尋、增強 web_search 底層
```

### 3. Vercel
```
設定指令: vercel login
價值: 前端部署能力
```

## P1 — 開啟高階功能

### 4. OpenAI
```
取得: https://platform.openai.com
價值: Codex CLI 编程 agent、高品質程式碼生成
```

### 5. DeepSeek
```
取得: https://platform.deepseek.com
價值: 便宜的國產模型、程式碼任務
```

### 6. Google Gemini
```
取得: https://aistudio.google.com
價值: 多模態模型（圖片/影片分析）
```

### 7. Firecrawl
```
取得: https://firecrawl.dev
價值: 將網站轉換為 LLM 可讀格式，適用於政府/學校網站抓取
```

## P2 — 工作流強化

### 8. Discord Bot
```
取得: https://discord.com/developers
價值: 整合 Discord 通知/自動化
```

### 9. 金融 API（2026-05-30 已驗證）

#### Twelve Data ✅
```
端點: https://api.twelvedata.com/price?symbol=AAPL&apikey=YOUR_KEY
注意: 不是 /v1/ — 錯誤的 endpoint 會 404
免費額度: 800 API calls/day
驗證: MSFT=$448.64 ✅
```

#### Alpha Vantage ✅
```
端點: https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_KEY
免費額度: 25 requests/day, 5/min
驗證: AAPL=$312.06 ✅
```

#### FRED ✅
```
端點: https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=YOUR_KEY&file_type=json
免費額度: 無限制（但需申請 key）
驗證: DFF=1.13% ✅
```

#### Finnhub ✅
```
端點: https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_KEY
免費額度: 60 calls/min
驗證: AAPL=$312.06 ✅
```

#### FMP ❌ 停用
```
狀態: v4 已全面付費，免費版停用
不要再設定
```

#### Yahoo Finance
```
不需要 key，是 Python 套件
pip install yfinance
直接用 terminal + Python 呼叫
```

---

## 驗證工具命令

```bash
# 驗證 GitHub
gh auth status

# 驗證 Tavily
curl -s "https://api.tavily.com/search?query=test&api_key=$TAVILY_KEY" | head -50

# 驗證 Vercel
vercel whoami

# 驗證 Twelve Data（注意：不是 /v1/ endpoint）
curl "https://api.twelvedata.com/price?symbol=AAPL&apikey=YOUR_KEY"

# 驗證 Alpha Vantage
curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_KEY"

# 驗證 FRED
curl "https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=YOUR_KEY&file_type=json&limit=1"

# 驗證 Finnhub
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_KEY"

# 查看當前所有狀態
hermes status
```

---

## 寫入 .env 的標準流程

1. 先 `cat ~/.hermes/.env` 確認目前狀態
2. 用 `hermes config set` 或直接 `echo >> ~/.hermes/.env` 追加
3. 環境變數格式：`UPPER_SNAKE_CASE_API_KEY=your_k...
4. 寫入後立即用 curl/Python 測試，不要只靠 `hermes status`
