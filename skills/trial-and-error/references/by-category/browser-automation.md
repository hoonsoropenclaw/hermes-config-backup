# 瀏覽器自動化踩坑目錄

## nodriver 生態調研（2026-06-12）

### 核心定位

nodriver = async Chrome automation via direct Chrome DevTools Protocol (CDP)。無 WebDriver、無 Selenium、不依賴任何中介層。

**Why it beats Playwright**: Playwright 在 startup 時執行 `Runtime.enable` 等 CDP 命令序列，產生可被檢測的指紋。nodriver 跳過這段，瀏覽器指紋看起來像真實用戶。

**Architecture**:
```
Python → CDP WebSocket → Chrome process (directly)
         (no Playwright shim, no WebDriver)
```

**Benchmark result** (2026-06, ianlpaterson.com): 7 種工具測 31 個 Cloudflare 目標，nodriver 是唯一零封鎖（28 OK / 0 blocked）。

### 安裝方式

```bash
# 需要隔離 venv（不在 hermes venv 裝，避免汙染）
python3 -m venv /tmp/nodriver-test
/tmp/nodriver-test/bin/pip install nodriver
# 依賴: mss, websockets>=14, deprecated, wrapt<3
```

**系統需求**: 需要系統有 Chrome binary。若無，安裝時會 `FileNotFoundError: could not find a valid chrome browser binary`。

### 常用 API

```python
import nodriver as driver
import asyncio

async def example():
    browser = await driver.start()
    tab = await browser.get('https://example.com')
    print(await tab.title())
    await browser.stop()

asyncio.run(example())
```

**指定 Chrome 路徑**:
```python
browser = await driver.start(browser_executable_path='/path/to/chrome')
```

### camofox vs nodriver vs Camoufox 生態對比（2026-06）

| Tool | Base | 優勢 | 劣勢 |
|------|------|------|------|
| nodriver | Chrome (direct CDP) | 零封鎖、async 高效能、內建 Turnstile solver | 需系統 Chrome binary |
| Camoufox | Firefox fork | 專為 Firefox 反檢測優化 | 生態比 nodriver 小 |
| Camofox | Firefox (hermes skill) | 已有 watchdog script 每分鐘監控 | 依賴 Docker container |

### Watchdog 部署驗證（2026-06-12）

Camofox watchdog 腳本存在於 `~/.hermes/skills/browser/camofox/scripts/camofox-watchdog.sh`，已部署至 `/tmp/camofox-watchdog.sh`，crontab 確認每分鐘執行：

```bash
# Crontab line（已部署）
* * * * * /tmp/camofox-watchdog.sh >> /tmp/camofox-watchdog.log 2>&1

# Watchdog script 功能
# 1. curl http://localhost:9377/health
# 2. 若 "browserConnected":false → docker restart camofox-browser
```

**驗證命令**:
```bash
# 看 watchdog log 行數（正常應該有累積）
wc -l /tmp/camofox-watchdog.log  # 2026-06-12: 1784 行（每分鐘 +1）

# 看 docker 是否活著
ps aux | grep camofox | grep -v grep | wc -l  # 正常應有 1+ 行
```

**Phase 1.5 必查**: 若某個 cron job 有對應的 watchdog script，必須同時確認：
1. script 檔案存在
2. cron entry 存在（`crontab -l | grep <name>`）
3. script 權限可被 cron 執行者讀取

### 若需要 nodriver 實測（未來有機會時）

1. 先確認系統有 Chrome: `which google-chrome` 或 `which chromium`
2. 若無，需安裝 Chrome（不在本次 learning scope）
3. 隔離 venv 內測試（`/tmp/nodriver-test`）
4. 參考: https://github.com/ultrafunkamsterdam/nodriver

### 相關條目

- [[hermes-internal.md#stale-state]] — cron job 狀態同步問題
- [[hermes-backup-strategy.md]] — 若瀏覽器自動化涉及備份

---

## Playwright/Camofox 已知坑（2026-06-12 前）

### `browser_tools` 的 CDP 指紋問題

標準 Playwright 在 startup 時執行 `Runtime.enable` 等 CDP 命令序列，產生可被 Cloudflare 等檢測的指紋。若需要繞過 Cloudflare，優先考慮 nodriver。

### Camofox Docker container 掛掉時的恢復

Camofox watchdog 每分鐘檢查 `localhost:9377/health`。若發現 `browserConnected: false` 或 API unreachable，會重啟 container。

**手動重啟**:
```bash
docker restart camofox-browser
```

**驗證恢復**:
```bash
curl -s http://localhost:9377/health | grep browserConnected
# 應顯示 "browserConnected":true
```

---

### 多頁面網站爬取整合決策樹（2026-06-14）

**核心問題**：赫米斯有 `scrapling`、`reverse-engineering`、`url_to_d2.py` 等工具，但缺乏「何時串接什麼」的標準流程。

**工具現況（已驗證）**：
- `scrapling` v0.4.8 ✅（adaptive parsing、`auto_save` + `adaptive=True`）
- `url_to_d2.py` ✅（playwright → D2 → SVG，24346 bytes 驗證成功）
- `d2` v0.7.1 ✅
- nodriver ✅（CDP 直連，31 個 Cloudflare 目標 28/31 零封鎖）

**整合決策樹**：

```
目標網站類型
│
├─ **簡單靜態頁面**（無 JS、無 anti-bot）
│   └─ Fetcher.fetch() → CSS/XPath 解析
│
├─ **會變化的網站結構**（擔心結構變更）
│   └─ StealthyFetcher + adaptive=True（自動學習元素重定位）
│
├─ **anti-bot 嚴格**（Cloudflare 等）
│   ├─ 測試階段 → nodriver（CDP 直連，規避最強）
│   └─ 生產階段 → StealthyFetcher（Scrapling 內建繞過）
│
├─ **需要生成架構圖**
│   └─ url_to_d2.py（python3.12 + playwright → D2 → SVG）
│       使用：`python3.12 /tmp/url_to_d2.py "<URL>" /tmp/output.d2`
│
├─ **多頁面爬蟲**（需追連結、遍歷）
│   └─ Spider 框架（Scrapling 內建）
│       1. 定義 start_urls
│       2. parse()  yield follow() 追頁面
│       3. concurrent_requests 控制並發
│
└─ **複雜網站**（認證登入、SPA、需理解整體結構）
    └─ reverse-engineering skill（TRACE 協議）
        1. Triage → Record → Abstract → Challenge → Explain
        2. 搭配 Scrapling 抓取
        3. 搭配 D2 生成架構圖
```

**If→Then**：
- **If** 目標網站會動態變化且需長期維護爬蟲 **Then** 用 Scrapling 的 `auto_save=True` 建立指紋，`adaptive=True` 自動重定位
- **If** 需要生成網站架構圖 **Then** 直接跑 `python3.12 /tmp/url_to_d2.py "<URL>" /tmp/output.d2"`（D2 已在 /tmp）
- **If** 多頁面爬蟲 + anti-bot **Then** Scraping Spider 框架 + StealthyFetcher
- **If** 複雜網站（認證、SPA）需理解整體結構 **Then** reverse-engineering skill（TRACE 協議）→ Scrapling → D2

## Dribbble 三層 DOM 結構（2026-07-30，learning_1785404409_2 歸納）

Dribbble list 頁（`/shots/popular`）的資料藏在三個層級，每層可拿到的欄位不同：

| 層級 | 觸發條件 | wrapper | 可拿到的欄位 |
|------|---------|---------|-------------|
| 1. SSR HTML | curl 直接抓 | `<li id="screenshot-N" class="shot-thumbnail ...">` | title、image、shot.id |
| 2. Hydrated DOM | JS 跑完 | `<div class="shot-thumbnail js-thumbnail ...">` | + `.display-name`、`.js-shot-likes-count`、`.js-shot-views-count`、PRO badge |
| 3. Hover state | mouse hover 才顯示 | `.shot-thumbnail-overlay` | + tag chips、shot-byline |

**If→Then**：
- **If** 抓 Dribbble 只需要 title/image **Then** `requests` + BeautifulSoup 就夠
- **If** 還要 author + 互動數 **Then** 用 Playwright `page.evaluate()` 直接讀 hydrated DOM
- **If** 還要 tags **Then** 必須在 Playwright 觸發 hover（hover 觸發的 React state 才有 tags）

**Dribbble anti-bot 行為**：
- `requests` 抓 `https://dribbble.com/shots/popular` 回 **HTTP 202 + 空 body**（不是 403、不是 200）
- Selenium/Playwright 執行 JS 後才有完整 HTML — 純 requests 永遠拿不到 list
- `window.__INITIAL_STATE__` 注入 `props.contentBlocks`（圖片陣列）但**不含** likes/views/comments
- shot 詳情頁的 `__INITIAL_STATE__` 也只有 `contentBlocks` + `isCaseStudy` 旗標，互動數藏在後續 AJAX

**Dribbble robots.txt 守門重點**：
- 公開 `/robots.txt` 沒給 Allow，只有 39 條 Disallow
- 採「Disallow-only」政策 → 沒說不行的路徑仍可爬
- 自定黑名單必加 `/messages`, `/auth`, `/account/edit`, `/admin`, `/ads`, `/jobs/`
- 自定 Crawl-delay 至少 3 秒（官方未指定）

**Playwright + Dribbble 踩坑**：
- `page.content()` 回 hydrated 後 HTML，但 `.shot-title` 在某些 case study 是空字串
  → **fallback**：從 img alt 拿（格式 "Title concept dark theme ..."，取第一段）或 `.accessibility-text`（"View <Title>"）
- 抓 author 用 `.display-name`（優先）或 `.user-information` 內的第一個 `<a href="/...">`
- 抓 likes：`.js-shot-likes-container .color-deep-blue-sea-light-20` 內的文字（"146"）或 `[data-shot-like-count]`
- 抓 views：`.js-shot-views-count` 內文字（含 "k" / "m" 縮寫，需自寫 parser）
- 抓 comments：`.js-shot-comments-count` 或 `shot-statistics` 區塊內的第三個數字
- 用 `page.evaluate("window.scrollTo(0, document.body.scrollHeight)")` 觸發 lazy load 後再 evaluate

**為什麼「高評分」用 likes 當代理**：
- Dribbble 沒公開「評分」欄位（不像 Behance 的 Appreciations）
- likes 是設計師社群共識品質訊號（按讚 = 認可）
- 評分公式：`likes * 1 + views * 0.0001 + comments * 3 + (30 if PRO)`
- comments 權重高於 views（高互動 = 高品質；views 可能灌水）
- PRO 徽章 +30（付費設計師，作品品質通常較高）

**為什麼環境 chromedriver auto-discovery 會 work**：
- N100 環境有內建 chromedriver（系統包裝），`webdriver.Chrome()` 不傳 service 也能跑
- 但 Selenium 拿的是 SSR HTML（page_source），沒 author → 仍要走 Playwright 拿 hydrated DOM
- 解法：雙驅動抽象 — Selenium 當 fallback，Playwright 當主力（page.evaluate 拿 React 狀態）