# Stealth Browser Benchmark 2026（2026-06-12 更新）

**來源**: [Anti-detect browser benchmark 2026: 7 stealth tools, 31 targets](https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi) — Ian L. Paterson，31 個 Cloudflare 目標 × 3 次實測。

---

## Benchmark 結果

| 瀏覽器 | 通過 | 被擋 | 引擎 | 零封鎖？ |
|--------|------|------|------|---------|
| **nodriver** | **28** | **0** | Chrome 148（直接 CDP） | ✅ 是 |
| CloakBrowser | 26 | 2 | Chromium 145 | ❌ |
| curl_cffi | 26 | 2 | curl-impersonate | ❌ |
| Patchright | 25 | 3 | Chrome 148（channel=chrome） | ❌ |
| Camoufox | 25 | 3 | Firefox 135 | ❌ |
| Playwright | 24 | 5 | Chromium 147 | ❌ |
| rebrowser | 24 | 5 | Chromium 136 | ❌ |

---

## 核心原理：三層指紋檢測

| 層 | 檢測目標 | 修補有效？ | 工具 |
|----|---------|-----------|------|
| TLS/JA4 | 握手形狀、cipher suite | ❌ | curl_cffi 只能 HTTP |
| JS 指紋 | navigator/platform/canvas/WebGL | ❌ | Patchright/Camoufox 只修這個 |
| **自動化協議指紋** | CDP 連線特徵（Runtime.enable 等） | ✅ **只有 nodriver** | nodriver 直接 CDP |

**關鍵 insight**: 大多數 stealth 工具修復了 TLS 和 JS 層，但忽略了**自動化協議指紋**這第三層。Cloudflare 等 gate 會檢測 `Runtime.enable` + `Target.setAutoAttach` 這類 Playwright 專用序列。

---

## nodriver 為何零封鎖

nodriver 直接用 WebSocket 對 system Chrome 的 DevTools port，**沒有 Playwright 中間層**：
- 不走 `Runtime.enable` + `Target.setAutoAttach` 序列
- 沒有 CDP handshake 的 Playwright 指紋
- 不經過任何 accessibility layer

```python
# nodriver 核心模式（成功繞過 Cloudflare Turnstile）
import nodriver as driver

async def bypass_turnstile():
    browser = await driver.start()
    page = await browser.new_page()
    await page.goto('https://example.com', timeout=30000)
    # Cloudflare Turnstile checkbox 自動通過
```

---

## 適用場景（赫米斯）

- **赫米斯 Portal 登入** — Cloudflare Turnstile（`canadianinsider` 是唯一通過的目標）
- **HR 系統自動化** — 有些學校用 Cloudflare 保護內部系統
- **政府開放資料** — 某些網站有嚴格反爬

---

## 安裝與限制

```bash
# 安裝 nodriver（AGPL-3.0，需系統 Chrome）
uv venv /tmp/nd --python 3.12
uv pip install --python /tmp/nd/bin/python nodriver

# 限制：AGPL-3.0（如果商業使用需注意授權）
# 限制：需要系統 Chrome（不能用在純 headless server 無 Chrome 的環境）
```

**curl_cffi 替代方案**（HTTP-only，無 JS）：
```bash
uv venv /tmp/cf --python 3.12
uv pip install --python /tmp/cf/bin/python curl_cffi

# 使用
from curl_cffi import requests
requests.get(url, impersonate="chrome")  # TLS impersonate Chrome 145/146
```

---

## 抉擇樹更新（2026-06-12）

```
任務需要繞過 Cloudflare？
│
├─ 嚴格目標（Turnstile、管理挑戰）→ nodriver（28/31 零封鎖）
│   └─ 安裝：uv venv /tmp/nd --python 3.12 && uv pip install --python /tmp/nd/bin/python nodriver
│
├─ HTTP-only（無 JS 渲染需求）→ curl_cffi（TLS impersonate）
│   └─ 安裝：uv venv /tmp/cf --python 3.12 && uv pip install --python /tmp/cf/bin/python curl_cffi
│
├─ 需要 JS 渲染 + 一般嚴格 → Patchright（Playwright fork，修 CDP 指紋）
│
├─ 需要 cookies 認證（Google/YouTube）→ Camofox（Firefox）
│   └─ 先 curl -s http://localhost:9377/health 確認
│
└─ 一般 QA / 無 anti-bot → Playwright（最穩，/usr/bin/python3.12 內含）
```

---

## 參考資料

- [Anti-detect browser benchmark 2026](https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi)
- [nodriver GitHub](https://github.com/ultrafunkamsterdam/nodriver)
- [How to Bypass Cloudflare When Web Scraping in 2026](https://scrapfly.io/blog/posts/how-to-bypass-cloudflare-anti-scraping)
- [EzSolver - Cloudflare Turnstile solver](https://github.com/ismoiloffS/EzSolver)（nodriver + Turnstile）