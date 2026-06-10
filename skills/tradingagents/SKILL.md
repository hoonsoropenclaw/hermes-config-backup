---
name: tradingagents
description: TradingAgents - 多智能體 LLM 金融交易框架。包含基本面分析師、情感分析師、技術分析師、交易員、風險管理團隊等多種角色。支援 GPT-5.x、Gemini、Claude、DeepSeek 等模型。提供股票研究與策略實驗功能。
---

# TradingAgents - 多智能體 LLM 金融交易框架

## 概述

TradingAgents 是一個受現實世界中交易公司運作模式啟發的多智能體交易框架。透過部署專門的 LLM 驅動代理進行協作分析市場狀況並提供交易建議。

**GitHub**: https://github.com/TauricResearch/TradingAgents  
**中文版**: https://github.com/hsliuping/TradingAgents-CN  
**論文**: [arXiv:2412.20138](https://arxiv.org/abs/2412.20138)  
**License**: Apache 2.0（開源部分）

---

## 核心代理架構

```
┌─────────────────────────────────────────────────────────┐
│                    TradingAgents 架構                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────────┐    ┌─────────────┐                    │
│   │ Bull        │    │ Bear        │  研究員代理        │
│   │ Researcher  │    │ Researcher  │  (多空分析)        │
│   └──────┬──────┘    └──────┬──────┘                    │
│          │                   │                          │
│          └─────────┬─────────┘                          │
│                    ▼                                     │
│          ┌─────────────────┐                            │
│          │  Research       │                            │
│          │  Manager        │                            │
│          └────────┬────────┘                            │
│                   ▼                                      │
│   ┌──────────────────────────────────┐                   │
│   │ 交易員 (Trader)                   │                   │
│   │ - 保守型 (Conservative)          │                   │
│   │ - 進取型 (Aggressive)            │                   │
│   └──────────────┬───────────────────┘                   │
│                  ▼                                       │
│   ┌──────────────────────────────────┐                   │
│   │ 風險管理團隊 (Risk Management)    │                   │
│   │ - 倉位監控                       │                   │
│   │ - 曝險管理                       │                   │
│   └──────────────────────────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 代理角色說明

### 1. 基本面分析師 (Fundamentals Analyst)
- 評估公司財務和業績指標
- 識別內在價值和潛在風險

### 2. 情感分析師 (Sentiment Analyst)
- 分析社交媒體和公眾情感
- 使用情感評分演算法判斷市場情緒

### 3. 新聞分析師 (News Analyst)
- 監控全球新聞和總體經濟
- 評估新聞對市場的潛在影響

### 4. 技術分析師 (Technical Analyst)
- 分析價格趨勢和圖表模式
- 識別支撐/阻力位

### 5. Bull/Bear 研究員
- Bull Researcher：評估做多機會
- Bear Researcher：評估做空機會

### 6. 交易員 (Trader)
- 保守型交易員：低風險偏好
- 進取型交易員：高風險偏好

### 7. 風險管理團隊 (Risk Management Team)
- 監控倉位曝險
- 執行風險控制措施

## 支援模型

| 模型系列 | 支援狀態 |
|----------|----------|
| GPT-5.x | ✅ 完整支援 |
| Gemini 3.x | ✅ 完整支援 |
| Claude 4.x | ✅ 完整支援 |
| DeepSeek | ✅ 完整支援 |
| Qwen | ✅ 完整支援 |
| GLM | ✅ 完整支援 |
| Azure OpenAI | ✅ 完整支援 |

## 安裝方式

### 英文原版

```bash
# 克隆倉庫
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# 安裝依賴
pip install tradingagents

# 或使用 Docker
docker run -e OPENAI_API_KEY=your-key tradingagents
```

### 中文增強版 (TradingAgents-CN)

```bash
# 克隆中文版本
git clone https://github.com/hsliuping/TradingAgents-CN.git
cd TradingAgents-CN

# Docker 部署（推薦）
docker-compose up -d

# 或手動安裝
pip install -r requirements.txt
```

## 基本使用

### Python API

```python
from tradingagents import TradingAgent

# 初始化交易代理
agent = TradingAgent(
    model="gpt-5",
    risk_profile="balanced"  # conservative, aggressive, balanced
)

# 分析股票
result = agent.analyze("AAPL")

print(f"建議: {result.recommendation}")
print(f"信心: {result.confidence}")
print(f"理由: {result.reasoning}")
```

### CLI 使用

```bash
# 初始化配置
tradingagents init

# 分析股票
tradingagents analyze --ticker AAPL --model gpt-5

# 批量分析
tradingagents batch-analyze --tickers AAPL,TSLA,MSFT
```

### Docker 部署 (TradingAgents-CN)

```bash
# 啟動服務
docker-compose up -d

# 訪問 Web UI
# http://localhost:8501 (Streamlit)
# 或 http://localhost:8000 (FastAPI)
```

## 主要功能

| 功能 | 說明 |
|------|------|
| 📊 多代理協作分析 | 多個專業代理協同工作 |
| 📰 新聞監控 | 即時監控全球財經新聞 |
| 📈 技術分析 | 圖表模式和趨勢識別 |
| 💼 風險管理 | 倉位監控和曝險管理 |
| 🔄 回測系統 | 歷史資料回測交易策略 |
| 📝 報告生成 | 專業分析報告導出 |

## 輸出範例

```json
{
  "ticker": "AAPL",
  "recommendation": "BUY",
  "confidence": 0.85,
  "analysts": {
    "fundamentals": {
      "score": 8.5,
      "metrics": ["P/E ratio", "Revenue growth", "Debt ratio"]
    },
    "sentiment": {
      "score": 7.2,
      "social_buzz": "positive",
      "news_tone": "bullish"
    },
    "technical": {
      "score": 8.0,
      "signals": ["MA crossover", "RSI oversold"]
    }
  },
  "risk_assessment": {
    "overall_risk": "MEDIUM",
    "max_drawdown_estimate": "12%"
  },
  "trading_strategy": {
    "entry_point": 175.50,
    "stop_loss": 170.00,
    "take_profit": 190.00
  }
}
```

## 重要聲明

⚠️ **風險提示**：

1. TradingAgents 框架僅為**研究目的**設計
2. 交易表現會因多種因素而變化（模型、溫度、資料品質等）
3. **不構成金融、投資或交易建議**
4. 請勿用於實際交易

## 與 TradingAgents-CN 的差異

| 特性 | 英文原版 | 中文增強版 |
|------|----------|------------|
| 介面語言 | 英文 | 繁體/簡體中文 |
| 後端框架 | Streamlit | FastAPI + Vue |
| 數據庫 | 單一數據庫 | MongoDB + Redis |
| 市場支援 | 美股為主 | A股/港股/美股 |
| 部署方式 | Docker | 完整 Docker 支援 |

## 學習資源

- 📄 [論文](https://arxiv.org/abs/2412.20138)：詳細架構說明
- 📺 [Demo 影片](https://www.youtube.com/watch?v=90gr5lwjIho)
- 📚 TradingAgents-CN 學習中心：AI基礎、提示詞工程、模型選擇

---

*最後更新：2026-05-07*
*提醒：本工具僅供學習研究，不構成投資建議*