# Scraping Decision Tree（2026-06-14）

## 工具現況（已驗證）

| 工具 | 版本 | 驗證 | 用途 |
|------|------|------|------|
| `scrapling` | v0.4.8 | ✅ import 成功 | 自適應爬蟲框架 |
| `d2` | v0.7.1 | ✅ `/tmp/d2 version` 成功 | 架構圖渲染 |
| `url_to_d2.py` | — | ✅ 實測產出 24346 bytes SVG | URL → D2 → SVG pipeline |

## 決策樹

```
目標網站類型
│
├─ **簡單靜態頁面**（無 JS、無 anti-bot）
│   └─ `Fetcher.fetch()` → CSS/XPath 解析
│
├─ **會變化的網站結構**（需長期維護爬蟲）
│   └─ `StealthyFetcher` + `adaptive=True`（自動學習元素重定位）
│       - 首次：`Fetcher.fetch(url, auto_save=True)` 建立指紋
│       - 之後：`Fetcher.fetch(url, adaptive=True)` 自動重定位
│
├─ **anti-bot 嚴格**（Cloudflare 等）
│   ├─ 測試階段 → nodriver（CDP 直連，規避最強）
│   └─ 生產階段 → `StealthyFetcher`（Scrapling 內建繞過）
│
├─ **需要生成架構圖**
│   └─ `python3.12 /tmp/url_to_d2.py "<URL>" /tmp/output.d2`
│       產出：`/tmp/output.d2` + `/tmp/output.svg`
│
├─ **多頁面爬蟲**（需追連結、遍歷）
│   └─ Scrapling Spider 框架
│       ```python
│       from scrapling.spiders import Spider, Response
│       class MySpider(Spider):
│           name = "my-crawler"
│           start_urls = ["https://example.com"]
│           async def parse(self, response: Response):
│               for item in response.css('.item'):
│                   yield {"title": item.css('h2::text').get()}
│               # 追下一頁
│               next_page = response.css('.next::attr(href)').get()
│               if next_page:
│                   yield response.follow(next_page)
│       MySpider().start()
│       ```
│
└─ **複雜網站**（認證登入、SPA、需理解整體結構）
    └─ reverse-engineering skill（TRACE 協議）
        1. Triage → Record → Abstract → Challenge → Explain
        2. 搭配 Scrapling 抓取
        3. 搭配 D2 生成架構圖
```

## If→Then 速查

| If | Then |
|----|------|
| 目標網站會動態變化且需長期維護 | `auto_save=True` + `adaptive=True` |
| 需要生成網站架構圖 | `python3.12 /tmp/url_to_d2.py "<URL>" /tmp/output.d2` |
| 多頁面爬蟲 + anti-bot | Spider 框架 + `StealthyFetcher` |
| 複雜網站（認證、SPA）需理解整體結構 | reverse-engineering skill → Scrapling → D2 |
| anti-bot 嚴格（Cloudflare）測試階段 | nodriver（CDP 直連） |

## 抉擇樹（完整版）

見 `scrapling/SKILL.md` §抉擇樹：

| 工具 | 引擎 | 何時用 | 安裝方式 |
|------|------|--------|---------|
| **Scrapling** | 自適應解析 | 網站結構會變化、Cloudflare Turnstile | `uv venv /tmp/se --python 3.12 && uv pip install --python /tmp/se/bin/python scrapling` |
| **Playwright** | Chromium | 一般爬蟲、QA、已驗證穩定 | `/usr/bin/python3.12` 已內含 |
| **Camofox** | Firefox (Docker) | 需要 cookies 認證（Google/YouTube） | `docker ps` 確認 `camofox-browser` 運行中 |
| **nodriver** | Chrome CDP | 最高規避（31/31 Cloudflare 零封鎖） | `uv venv /tmp/nd --python 3.12 && uv pip install --python /tmp/nd/bin/python nodriver` |

抉擇：
- anti-bot 嚴格 → nodriver
- 一般爬蟲 / QA → Playwright
- 需要 cookies 認證 → Camofox
- 網站結構會動態變化 → Scrapling

## 驗證命令

```bash
# scrapling 安裝驗證
python3.12 -c "import scrapling; print(scrapling.__version__)"

# d2 安裝驗證
/tmp/d2 version

# url_to_d2.py 實測
python3.12 /tmp/url_to_d2.py "https://httpbin.org/html" /tmp/test.d2
```
