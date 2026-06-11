# browser-use SDK 研究摘要（2026-06-11）

## 核心發現

**browser-use** 是 2026 年最熱門的開源 AI 瀏覽器自動化庫（GitHub 90k+ stars，MIT license）。

### 與 Camofox/Playwright 的核心差異

| | Camofox | browser-use |
|---|---|---|
| 驅動方式 | CDP direct（Firefox）| LLM + 電腦視覺（self-healing）|
| 指令格式 | `curl -X POST http://camofox:9377/navigate` | 自然語言：`"點擊提交按鈕"` |
| 維護成本 | 網站改版 = 可能失效 | LLM 能理解新佈局並適應 |
| 適用場景 | 截圖、DOM 提取、Cookie 管理 | 複雜多步驟互動、CAPTCHA |

### Stealth Benchmark（71 網站，含 Cloudflare/Akamai/PerimeterX/DataDome）

| Provider | Success Rate |
|----------|-------------|
| Browser Use Cloud | **81%** |
| Anchor | 77% |
| Onkernel | 67% |
| Steel | 47% |
| Browserbase | 42% |
| Hyperbrowser | 40% |

開源庫（`pip install browser-use`）需要自己提供 LLM API key + compute，適合 self-hosted。

## 程式碼範例

### Basic Scrape（Firecrawl）
```python
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key="fc-YOUR_API_KEY")
result = app.scrape("https://example.com", formats=["markdown"])
# 回傳乾淨 markdown，無需解析 HTML
```

### Interactive（AI agent 自然語言驅動）
```python
from browser_use_sdk.v3 import AsyncBrowserUse
client = AsyncBrowserUse(api_key="YOUR_API_KEY")
result = await client.run(
    "Go to amazon.com, search for 'wireless headphones', "
    "filter by price under $100, and extract top results with prices and ratings"
)
# 回傳結構化資料（16 筆，包含價格、評分、評論數）
```

## 與 Camofox 的互補關係

- **Camofox**（Firefox-based，CDP 直接通訊）：仍是赫米斯主力瀏覽器方案（headless、noVNC、Cookie 管理）
- **browser-use SDK**：適合需要「AI 理解複雜 UI」的場景，例如學校行政系統登入、動態表單填寫
- **分工原則**：截圖/監控/Cookie 延續 → Camofox；複雜互動/CAPTCHA/自修復 → browser-use

## If→Then

**If** 任務需要處理複雜政府/學校 portal（多步驟登入、動態表單、CAPTCHA）**Then** 評估 browser-use SDK 而非純 Camofox 指令

**If** 任務只需要截圖 + DOM 提取 + Cookie 管理（現行 Camofox use case）**Then** 繼續用 Camofox

**If** 要整合 browser-use SDK **Then** 需要 `pip install browser-use` + LLM API key + 在 config.yaml 設定 provider

## 參考資源

- 官方文檔：https://docs.browser-use.com/cloud/quickstart
- GitHub：https://github.com/browser-use/browser-use
- 完整引導：https://browser-use.com/posts/web-scraping-guide-2026