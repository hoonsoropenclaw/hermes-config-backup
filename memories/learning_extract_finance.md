# 金融領域學習經驗萃取 (If→Then 格式)
# 來源: SKILL_CATALOG.md + progress.md
# 建立時間: 2026-05-30

---

## 股票技術分析

###技術指標計算
- **If** 需要計算 MA/RSI/MACD/Bollinger Bands 技術指標 **Then** 使用 pandas_ta (v0.3.x) 或 yfinance (v1.3.0) 內建函數
- **If** 需要 K 線圖繪製與技術分析 **Then** 使用 StockAnalyzer 類別整合 Twelve Data API，支援 MA5/MA10/MA20/RSI/MACD/Bollinger Bands
- **If** 需要進階技術指標（KDJ、ATR、成交量分布） **Then** 使用 stock_technical_analysis.py工具，包含支撐/阻力位識別

### 技術分析框架
- **If** 需要即時股價查詢與技術分析 **Then** 優先使用 LINE股票查詢 Bot v2.0（LINE Bot + 即時報價 + 技術分析 + LIFF 前端 + 虛擬交易 + 價格警示）
- **If** 需要股票買賣訊號 **Then** 整合多指標（RSI + MACD + MA）給出 BUY/SELL/HOLD 訊號

---

##金融 API 整合

### 多源故障轉移
- **If**單一金融 API 不穩定 **Then** 實作多源故障轉移：十二Data → Alpha Vantage → Finnhub → yfinance 四層備援
- **If** 需要無需 API Key 的金融數據 **Then** 使用 xFinance（Stooq/SEC/ECB/Binance/CoinGecko 備援）或 FinMind（75+ 台股資料集，REST API 無需 Key）
- **If** 需要台股即時/歷史股價 **Then** 使用 twstock（證交所 API，每 5 秒 3 次限制）或證交所 TWSE OpenAPI（官方，無需 API Key）

### API選擇策略
- **If** 需要即時報價 **Then** 優先 Finnhub（60 calls/min）或 Twelve Data（800 calls/day）
- **If** 需要基本面/財務報表 **Then** 使用 Alpha Vantage（25 req/day）或 Financial Modeling Prep（250 req/day）
- **If** 需要台股完整資料 **Then** 使用 FinMind（75+ 資料集，技術面+基本面+籌碼面）
- **If** 需要免費且無需 API Key **Then** 使用 xFinance 或 Stooq（無限歷史）

---

## 量化回測與交易

### 回測框架
- **If** 需要 Python 原生回測引擎 **Then** 使用 Backtrader（10k+ ⭐），支援技術指標與策略開發
- **If** 需要超高速回測（pandas 向量化） **Then** 使用 vectorbt（9k+ ⭐），比傳統回測快10-100x
- **If** 需要加密貨幣量化回測 **Then** 使用 CCXT 框架，支援事件驅動回測引擎與均值回歸+趨勢追蹤+突破策略

### 交易策略
- **If** 需要選擇權策略分析 **Then** 使用 options_strategy_analyzer.py，支援 7 種策略（Covered Call, Protective Put, Bull/Bear Spread, Straddle, Strangle, Iron Condor）+ Black-Scholes 定價 + Greeks（Delta, Gamma, Theta, Vega, Rho）
- **If** 需要投資組合再平衡 **Then** 使用 portfolio_rebalancer.py，計算 drift 分析並自動調整
- **If** 需要風險平價優化 **Then** 使用 risk_parity_optimizer.py，計算各資產風險貢獻權重

---

## 投資組合管理

### 組合分析
- **If** 需要多帳戶投資組合追蹤 **Then** 使用 portfolio_analytics_engine（支援 PEA/CTO/PEE/儲蓄帳戶）+ FIFO 成本基礎追蹤 + 股票分割調整
- **If** 需要投資組合風險指標 **Then** 計算 VaR/CVaR/最大回落/夏普比率/蒙特卡羅模擬
- **If** 需要殖利率篩選 **Then** 使用 DividendScreener 整合 Finnhub/Alpha Vantage/Twelve Data，自動化備援機制

### 保險與理財
- **If** 需要退休規劃計算 **Then** 使用 4% 法則（每年提領 4% 作為退休金的安心提領率）
- **If** 需要月薪理財規劃 **Then** 計算緊急預備金（3-6 個月支出）+ 殖利率監控

---

## 加密貨幣與區塊鏈

### 加密技術分析
- **If** 需要加密貨幣技術分析 **Then** 使用 CryptoAnalyzer 整合 CoinGecko API，計算 SMA/EMA/RSI/MACD/Bollinger/ATR
- **If** 需要鯨魚追蹤 **Then** 使用 WhaleTracker 監控多鏈（ETH/BTC/BSC）大額轉帳，配合 LINE/Telegram 警報

### 交易 Bot
- **If** 需要加密貨幣交易 Bot **Then** 使用 Freqtrade（24k+ ⭐），支援所有主流交易所與 Telegram 控制
- **If** 需要加密貨幣回測 **Then** 使用 CCXT 框架，支援均值回歸+趨勢追蹤+突破策略

---

## LINE Bot 金融應用

### LINE股票 Bot
- **If** 需要 LINE 股票查詢功能 **Then** 使用 line_stock_bot_v4，支援即時報價 +技術分析 + Flex Message + Quick Reply + Postback 處理
- **If** 需要 LINE虛擬交易功能 **Then** 整合 LIFF 前端 + SQLite資料庫 + 虛擬持仓管理
- **If** 需要價格警示 **Then** 設定 RSI/價格門檻，觸發時透過 LINE Notify 推播

---

## Python金融工具實作

### 工具清單
- **If** 需要完整金融工具包 **Then** 使用 finance_toolkit.py（含 backtesting、技術分析、投資組合管理）
- **If** 需要台股專用工具 **Then** 使用 taiwan_stock.py（台股專用，證交所 API）
- **If** 需要金融框架 **Then** 使用 finance_framework.py（含統一的數據模型與 API整合）

### 框架選擇
- **If** 需要 AI 量化 **Then** 使用 Python_ML_Quant_Trading（Backtrader 回測 + XGBoost/LSTM +因子分析）
- **If** 需要自然語言交易 **Then** 使用 Vibe-Trading（自然語言 →市場數據 → 策略 → 回測 → 報告）

---

## 實作作品清單

| 作品 |檔案 | 功能 |
|------|------|------|
| 選擇權策略分析器 | options_strategy_analyzer.py | 7種策略+Greeks+Payoff Diagram |
| 股票技術分析工具 | stock_technical_analysis.py | K線+MA+RSI+MACD+布林帶+KDJ |
| 投資組合再平衡 | portfolio_rebalancer.py | drift 分析+自動調整 |
| 風險平價優化器 | risk_parity_optimizer.py | 風險權重計算 |
| 券商同步 | portfolio_sync.py | 即時持仓同步 |
| 加密技術分析 | crypto_technical_analyzer.py | 技術指標+鯨魚追蹤 |
| 金融工具包 | finance_toolkit.py | 完整金融工具整合 |

---

## 驗證要點

- **If** API故障轉移測試 **Then** 模擬主要 API 失敗，驗證備援機制是否正常切換
- **If** 回測驗證 **Then** 使用歷史數據跑完策略，確認夏普比率/最大回撤符合預期
- **If** LINE Bot測試 **Then** 確認 Flex Message 格式正確，Postback 動作正常處理
- **If**投資組合再平衡 **Then** 確認 drift 計算正確（偏離百分比），調整後持仓符合目標權重
