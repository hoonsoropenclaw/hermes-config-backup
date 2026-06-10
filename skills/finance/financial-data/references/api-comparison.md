# Financial Data API Reference Notes

## Research Sources (2026-06-03)

### API Comparison Research
- **FinancialData.net comparison** (github.com/financialdatanet/financial-data-api-comparison): Best overall choice for most users, but we already have multiple established APIs configured
- **Alpha Vantage docs** (alphavantage.co/documentation): 20+ years historical data, exchange-licensed, but 25 requests/day is extremely limiting
- **Twelve Data docs** (twelvedata.com/docs): 60+ technical indicators, 800 calls/day, NOT /v1/ in endpoint path (common mistake)
- **Finnhub docs** (finnhub.io/docs/api): Real-time quote, news sentiment, analyst price targets — only source for sentiment data

### FRED Integration
- **fredapi** (pypi.org/project/fredapi): Official Python wrapper for FRED
- **Tutorial** (datons.com): Step-by-step FRED API + pandas integration
- **Kaggle notebook**: Economic analysis with pandas and FRED API
- Common series IDs: DFF (fed funds rate), GDP, CPIAUCSL (CPI), UNRATE (unemployment), M2SL (M2 money supply)

### Alpha Vantage Rate Limit Workaround
- 25 requests/day is dangerously low
- **Strategy**: Save for when 20-year history is specifically needed; all other uses should use Twelve Data or Finnhub
- Can combine with ALPHA_VANTAGE_KEY enrichment in stocks_client.py when Yahoo crumb fails

### Twelve Data Common Pitfall
- **WRONG**: `https://api.twelvedata.com/v1/price?symbol=AAPL`
- **CORRECT**: `https://api.twelvedata.com/price?symbol=AAPL` (no /v1/)
- This caused 404 errors in early testing

### Finnhub Capabilities
- **news_sentiment**: Returns buzz, sentiment, sector sentiment
- **price_target**: analyst price targets, consensus, rating
- **recommendation_trend**: buy/hold/sell consensus
- **company_news**: news articles for a symbol between dates

## Hermes-Validated API Results (from token-priorities.md)

| API | Endpoint | Test Result |
|-----|----------|-------------|
| Twelve Data | `price?symbol=MSFT` | MSFT=$448.64 ✅ |
| Alpha Vantage | `GLOBAL_QUOTE` | AAPL=$312.06 ✅ |
| FRED | `series/observations?series_id=DFF` | DFF=1.13% ✅ |
| Finnhub | `quote?symbol=AAPL` | AAPL=$312.06 ✅ |

## Decision Framework in Practice

When user asks "請報個股價" or similar:
1. First try: stocks skill (Yahoo Finance, 0 cost)
2. If null/fail: Finnhub (60 calls/min, real-time)
3. If user specifically asks for technical indicators: Twelve Data
4. If user asks for 20+ years history: Alpha Vantage (but warn about 25/day limit)

When user asks "幫我看一下總經數據":
- Always FRED — it's unlimited and specifically designed for this