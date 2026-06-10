---
name: financial-data
description: "金融資料 API 選擇決策框架：根據需求類型（價格/技術指標/基本面/總經/情緒）自動選擇最適合的資料來源。整合 Twelve Data、Finnhub、Alpha Vantage、FRED、Yahoo Finance (stocks 技能) 和 TradingAgents。"
version: 1.0.0
author: Hermes metacognitive-learner
platforms: [linux]
metadata:
  hermes:
    tags: [finance, market-data, stock, economic-data, api-selection]
    triggers: [股票, 股價, 報價, 金融資料, market data, stock price, financial data, technical indicators, FRED, macro economic]
---

# Financial Data API Decision Framework

## Role
當用戶需要金融/市場資料時，根據需求類型自動選擇最適合的資料來源，避免 API quota 浪費和隨機嘗試。

## 觸發條件
使用者提到以下關鍵字時，主動喚醒此技能：
- 「股票」、「股價」、「報價」、「報一個價」
- 「技術指標」（MACD、EMA、RSI、BBands 等）
- 「歷史 K 線」、「歷史價格」
- 「總經數據」、「利率」、「CPI」、「GDP」、「失業率」
- 「基本面」、「財報」、「營收」
- 「新聞情緒」、「分析師評級」
- 「股票分析」、「我要看某檔股票的 XX」

## 核心決策樹

```
需求類型 → 來源優先順序
─────────────────────────────────────────────────────
即時股價（日常監控）
  └→ stocks 技能（Yahoo Finance，完全免費）✅
       若回傳 null 或用戶需要技術指標
       └→ Finnhub（即時，60 calls/min）

技術指標（MACD、EMA、RSI、BBands、ADX 等）
  └→ Twelve Data（60+ 內建指標，800 calls/day）

20 年+ 歷史 K 線（日/週/月維度）
  └→ Alpha Vantage（25 calls/day，**珍貴額度**）

宏觀經濟數據（利率、GDP、CPI、失業率、聯準會數據）
  └→ FRED（完全免費，無上限）

新聞情緒、分析師評級、券商目標價
  └→ Finnhub（news_sentiment、price_target 端點）

同時分析多個標的
  └→ TradingAgents（多代理框架）

快速報價（無技術指標需求）
  └→ stocks 技能（Yahoo Finance，0 API cost）
```

## API 特性速查表

| API | 強項 | 弱項 | 免費額度 | 赫米斯驗證 |
|-----|------|------|----------|------------|
| **stocks 技能** | 完全免費、不需 key | 非官方、可能 rate-limit | 無限 | ✅ |
| **Finnhub** | 即時報價、新聞情緒 | 免費版非美股覆蓋少 | 60 calls/min | ✅ |
| **Twelve Data** | 技術指標、期貨/外匯 | 免費版無即時報價 | 800 calls/day | ✅ |
| **Alpha Vantage** | 20 年歷史、交易所授權 | **每日僅 25 次**，5/min | 25/day | ✅（但珍貴） |
| **FRED** | 宏觀經濟數據 | 僅總經，無股價 | 無限 | ✅ |
| **TradingAgents** | 多代理協作分析 | 需自備 API key | N/A | ✅ 框架 |

## ⚠️ 重要警告

### Alpha Vantage 額度極少
- 免費版**每天只有 25 次**請求，5 次/分鐘
- **嚴禁**用迴圈批量查詢
- 只用在「需要 20 年歷史深度且 Twelve Data 的 10 年不夠」時
- 日常股價查詢絕對不要用 Alpha Vantage

### Twelve Data 免費版限制
- 無即時報價（延遲）
- 歷史資料僅 10 年
- 每日 800 calls 上限

### 優先順序原則
1. **日常監控** → stocks 技能（免費）
2. **需要技術指標** → Twelve Data
3. **20 年歷史** → Alpha Vantage（但先確認 quota）
4. **總經數據** → FRED
5. **新聞情緒** → Finnhub

## 實際調用方式

### stocks 技能（Yahoo Finance）
```bash
SCRIPT=~/.hermes/hermes-agent/optional-skills/finance/stocks/scripts/stocks_client.py
python3 $SCRIPT quote AAPL
python3 $SCRIPT quote AAPL MSFT GOOGL  # 批量報價
```

### Twelve Data（即時報價 + 技術指標）
```bash
# 即時報價（注意：不是 /v1/ endpoint）
curl "https://api.twelvedata.com/price?symbol=AAPL&apikey=$TWELVE_DATA_KEY"

# 技術指標（以 EMA 為例）
curl "https://api.twelvedata.com/ema?symbol=AAPL&interval=1day&apikey=$TWELVE_DATA_KEY"

# 其他指標：macd, rsi, bbands, adx, sma, atr, stoch, obv
```

### Finnhub（即時報價 + 新間情緒）
```bash
# 即時報價
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_KEY"

# 新聞情緒
curl "https://finnhub.io/api/v1/news-sentiment?symbol=AAPL&token=$FINNHUB_KEY"

# 分析師評級
curl "https://finnhub.io/api/v1/stock/price-target?symbol=AAPL&token=$FINNHUB_KEY"
```

### Alpha Vantage（20 年歷史）
```bash
# 每日 K 線（20 年歷史）
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=$ALPHA_VANTAGE_KEY&outputsize=full"

# 全球報價
curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=$ALPHA_VANTAGE_KEY"
```

### FRED（宏觀經濟數據）
```bash
# 聯準會基金利率（聯邦基金利率）
curl "https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=$FRED_KEY&file_type=json&limit=1"

# 其他常用指標：
# DFF — 聯準會基金利率
# GDP — 美國 GDP
# CPIAUCSL — 消費者物價指數
# UNRATE — 失業率
# FEDFUNDS — 聯邦基金利率（同 DFF）
# M2SL — M2 貨幣供給
```

## 環境變數
```
TWELVE_DATA_KEY=    # Twelve Data API key
FINNHUB_KEY=        # Finnhub API key
ALPHA_VANTAGE_KEY=  # Alpha Vantage API key（珍貴，勿浪費）
FRED_KEY=           # FRED API key
```

## 與其他技能的關係

- **tradingagents**：多代理分析框架，當用戶需要「完整分析」而非只是「拿資料」時使用
- **stocks**：Yahoo Finance 實作，日常報價首選（0 API cost）
- **variance-analysis**（anthropic finance）：財務變異分析，需要用到實際財務資料時

## 決策速記

> **日常監控 = stocks 技能**
> **技術指標 = Twelve Data**
> **20年歷史 = Alpha Vantage（但別浪費在日常查詢）**
> **總經 = FRED**
> **情緒/評級 = Finnhub**

---

*Created: 2026-06-03 by metacognitive-learner*