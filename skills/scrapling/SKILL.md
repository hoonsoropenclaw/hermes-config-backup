---
name: scrapling
description: Scrapling - 自適應網頁爬蟲框架，45k+ Stars。支援自動元素重定位、Cloudflare Turnstile 繞過、隱形抓取、蜘蛛框架、MCP Server 整合。適用於政府開放資料抓取、法規監控、競爭資訊收集。
---

# Scrapling - 自適應網頁爬蟲框架

## 概述

Scrapling 是一個強大的自適應網頁爬蟲框架，GitHub 45,969 ⭐。其核心特色是能自動學習並重新定位元素位置，應對網站結構變更。

**GitHub**: https://github.com/D4Vinci/Scrapling  
**文檔**: https://scrapling.readthedocs.io  
**安裝**: `pip install scrapling`

## 核心特色

### 1. 自適應解析（Adaptive Parsing）

當網站結構變更時，Scrapling 能自動重新定位元素：

```python
from scrapling.fetchers import Fetcher, StealthyFetcher

# 首次抓取（自動保存元素指紋）
p = Fetcher.fetch('https://example.com')
products = p.css('.product', auto_save=True)

# 之後網站結構變了？加 adaptive=True
products = p.css('.product', adaptive=True)
# Scrapling 會自動學習重新定位！
```

### 2. 隱形抓取（Bypass Anti-Bot）

內建繞過機制：
- ✅ Cloudflare Turnstile
- ✅ 基本反爬蟲機制
- ✅ 自動化檢測

```python
# StealthyFetcher - 隱形抓取模式
p = StealthyFetcher.fetch(
    'https://example.com',
    headless=True,           # 無頭模式
    network_idle=True        # 等待網路閒置
)
```

### 3. 蜘蛛框架（Spider Framework）

支援大規模爬蟲：

```python
from scrapling.spiders import Spider, Response

class MySpider(Spider):
    name = "demo"
    start_urls = ["https://example.com/"]

    async def parse(self, response: Response):
        for item in response.css('.product'):
            yield {"title": item.css('h2::text').get()}

MySpider().start()
```

功能：
- 異步並發爬取
- 暫停/恢復功能
- 自動代理輪換
- 即時統計

## 爬取方法（5 種）

| 方法 | 說明 | 語法 |
|------|------|------|
| **CSS 選擇器** | 最常用 | `p.css('.product')` |
| **XPath 選擇器** | 複雜定位 | `p.xpath('//div[@class="item"]')` |
| **過濾器搜尋** | 條件搜尋 | `p.find_all(class_='active')` |
| **文字內容搜尋** | 找含特定文字的元素 | `p.find(content='關鍵字')` |
| **正規表達式** | 模式匹配 | `p.find_all(pattern=r'\d+')` |

## 基本使用

### 安裝

**重要：PEP 668 限制** — 系統 python3 無法直接 `pip install`，需要建立 venv：
```bash
# 正確方式（建立 venv）
uv venv /tmp/scrapling-env --python 3.12
uv pip install --python /tmp/scrapling-env/bin/python scrapling

# 錯誤方式（會失敗）
pip install scrapling  # → externally-managed-environment error
```

### 基本抓取

```python
from scrapling.fetchers import Fetcher

# 簡單 HTTP 抓取
p = Fetcher.fetch('https://example.com')

# 取得標題
title = p.css('h1::text').get()

# 取得所有連結
links = p.css('a::attr(href)').getall()

# 取得多個元素
for item in p.css('.product'):
    print(item.css('h2::text').get())
```

### CSS 選擇器特殊語法

```python
# 取得文字內容
p.css('h1::text').get()           # 元素文字
p.css('p::text').getall()         # 所有文字

# 取得屬性值
p.css('img::attr(src)').get()    # 圖片 URL
p.css('a::attr(href)').getall()   # 所有連結

# 組合使用
p.css('.product h2::text').get()  # 巢狀選擇
```

### XPath 使用

```python
# XPath 選擇器
p.xpath('//div[@class="item"]').get()
p.xpath('//a[@href="/detail"]/@href').getall()
```

### 過濾器條件

```python
# 找所有 class 為 active 的元素
p.find_all(class_='active')

# 找第一個 id 為 header 的元素
p.find(id='header')

# 複合條件
p.find_all(class_='item', attrs={'data-active': 'true'})
```

### 正規表達式

```python
import re

# 找所有數字
p.find_all(pattern=r'\d+')

# 找符合日期格式的文本
p.find_all(pattern=r'\d{4}-\d{2}-\d{2}')

# 找 Email
p.find_all(pattern=r'[\w.-]+@[\w.-]+\.\w+')
```

## Fetcher 類型

| 類型 | 特色 | 使用場景 |
|------|------|----------|
| `Fetcher` | 基本 HTTP 抓取 | 簡單頁面 |
| `AsyncFetcher` | 異步抓取 | 大量 URL |
| `StealthyFetcher` | 隱形模式繞過反爬 | 被反爬蟲的網站 |
| `DynamicFetcher` | 支援 JavaScript 渲染 | SPA 網站 |

```python
from scrapling.fetchers import Fetcher, AsyncFetcher, StealthyFetcher, DynamicFetcher

# 基本
p = Fetcher.fetch('https://example.com')

# 隱形（繞過 Cloudflare 等）
p = StealthyFetcher.fetch('https://example.com', headless=True)

# 動態（JavaScript 渲染）
p = DynamicFetcher.fetch('https://example.com', wait_for='.content-loaded')
```

## 蜘蛛框架（Spider）

### 基本蜘蛛

```python
from scrapling.spiders import Spider, Response

class SchoolSpider(Spider):
    name = "school-regulations"
    start_urls = ["https://www.dgpa.gov.tw/regulations"]
    
    async def parse(self, response: Response):
        # 爬取法規列表
        for item in response.css('.regulation-item'):
            yield {
                'title': item.css('h3::text').get(),
                'date': item.css('.date::text').get(),
                'url': item.css('a::attr(href)').get()
            }
        
        # 追蹤分頁
        next_page = response.css('.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page)

SchoolSpider().start()
```

### 蜘蛛進階功能

```python
# 設定並發數
class MySpider(Spider):
    concurrent_requests = 5  # 預設 16
    
    # 設定代理
    proxy = "http://proxy.example.com:8080"
    
    # 設定請求間隔（秒）
    download_delay = 1.0

# 暫停/恢復
spider = MySpider()
spider.start()
spider.pause()
spider.resume()
```

## MCP Server 整合

Scrapling 提供 MCP Server，可與 AI Agent 整合：

### 安裝 MCP Server

```bash
# 安裝 scrapling 並啟用 MCP
pip install 'scrapling[mcp]'
```

### MCP 工具列表

Scrapling MCP Server 提供 10 個工具：

1. `fetch_url` - 基本 HTTP 抓取
2. `stealth_fetch` - 隱形抓取
3. `dynamic_fetch` - 動態抓取
4. `parse_html` - 解析 HTML
5. `extract_text` - 提取文字
6. `extract_links` - 提取連結
7. `extract_images` - 提取圖片
8. `search_content` - 搜尋內容
9. `extract_tables` - 提取表格
10. `adaptive_parse` - 自適應解析

### 使用範例

```python
# MCP Server 設定（for Claude Desktop 等）
# 在 claude_desktop_config.json 中設定：
{
  "mcpServers": {
    "scrapling": {
      "command": "scrapling-mcp",
      "args": ["--port", "3000"]
    }
  }
}
```

## 學校應用場景

### 與其他瀏覽器工具的抉擇

| 工具 | 引擎 | 何時用 | 安裝方式 |
|------|------|--------|---------|
| **Scrapling** | 自適應解析 | 網站結構會變化、Cloudflare Turnstile | `uv venv /tmp/se --python 3.12 && uv pip install --python /tmp/se/bin/python scrapling` |
| **Playwright** | Chromium | 一般爬蟲、QA、已驗證穩定 | `/usr/bin/python3.12` 已內含 |
| **Camofox** | Firefox (Docker) | 需要 cookies 認證（Google/YouTube） | `docker ps` 確認 `camofox-browser` 運行中 |
| **nodriver** | Chrome CDP | 最高規避（31/31 Cloudflare 零封鎖） | `uv venv /tmp/nd --python 3.12 && uv pip install --python /tmp/nd/bin/python nodriver` |

**抉擇樹**：
- anti-bot 嚴格（Cloudflare）→ nodriver（需 venv + Chrome binary）
- 一般爬蟲 / QA → Playwright（`/usr/bin/python3.12` 最穩）
- 需要 cookies 認證 → Camofox（先 `curl -s http://localhost:9377/health`）
- 網站結構會動態變化 → Scrapling（自適應解析）

---

### 1. 政府開放資料抓取

```python
from scrapling.fetchers import Fetcher

def fetch_education_data():
    p = Fetcher.fetch('https://stats.moe.gov.tw/')
    
    # 抓取最新統計資料
    for row in p.css('table tr'):
        yield {
            'year': row.css('td:nth-child(1)::text').get(),
            'students': row.css('td:nth-child(2)::text').get(),
            'teachers': row.css('td:nth-child(3)::text').get()
        }
```

### 2. 法規異動監控

```python
from scrapling.spiders import Spider, Response
import schedule

class RegulationMonitor(Spider):
    name = "regulation-monitor"
    start_urls = ["https://www.dgpa.gov.tw"]
    
    async def parse(self, response: Response):
        new_regulations = []
        for item in response.css('.regulation-item'):
            title = item.css('h3::text').get()
            date = item.css('.date::text').get()
            new_regulations.append({'title': title, 'date': date})
        
        # 比對舊資料，發送通知
        return new_regulations

# 定時執行
schedule.every().day.at("09:00").do(
    lambda: RegulationMonitor().start()
)
```

### 3. 競爭學校資訊收集

```python
from scrapling.fetchers import StealthyFetcher

def collect_competition_info():
    p = StealthyFetcher.fetch(
        'https://competitor-school.edu.tw/news',
        headless=True,
        network_idle=True
    )
    
    news = []
    for item in p.css('.news-item'):
        news.append({
            'title': item.css('h4::text').get(),
            'date': item.css('.date::text').get(),
            'category': item.css('.tag::text').get()
        })
    
    return news
```

## 法律與倫理考量

- ✅ 遵守網站的 `robots.txt`
- ✅ 不要過度頻繁地爬取
- ✅ 不要爬取個人隱私資料
- ✅ 使用於合法目的

## 資源連結

- 📖 文檔：https://scrapling.readthedocs.io
- 🐙 GitHub：https://github.com/D4Vinci/Scrapling
- 🤖 MCP Server：https://scrapling.readthedocs.io/en/latest/ai/mcp-server.html

---

## 參考資料

- 📖 [stealth-browser-2026.md](references/stealth-browser-2026.md) — 2026 年 stealth browser benchmark（nodriver 28/31 零封鎖）、三層指紋原理、抉擇樹更新

---

*最後更新：2026-06-12*