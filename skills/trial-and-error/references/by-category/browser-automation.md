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