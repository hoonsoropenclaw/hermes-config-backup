# Stealth Browser Automation 生態系（2026-06 更新）

## 核心問題

傳統 Playwright/Puppeteer 使用 WebDriver binary，會留下可被檢測的指紋。2026 年的 anti-detection benchmark 中，標準工具大量失敗。

---

## 工具選擇優先序

### 1. nodriver（Python，async）— benchmark 最強
- **原理**：直接用 CDP（Chrome DevTools Protocol）溝通，繞過 WebDriver binary
- **Benchmark**：31 個 Cloudflare 目標零封鎖（ianlpaterson.com/blog/anti-detect-browser-benchmark）
- **優點**：async 支援、極度隱蔽、程式碼簡潔（1-2 行啟動）
- **基本用法**：
```python
import nodriver as driver
import asyncio

async def main():
    browser = await driver.start()
    tab = await browser.get("https://target-site.com")
    elem = await tab.find("input[name='q']", timeout=5)
    await elem.type("search query")

asyncio.run(main())
```

### 2. Camofox（Docker Firefox）— 赫米斯已部署
- **原理**：Camoufox（Firefox 修改版）+ Docker 隔離
- **URL**：`http://localhost:9377`
- **健康檢查**：`curl -s http://localhost:9377/health`
- **用途**：Firefox 系目標、cookie import 已認證 session
- **注意**：容器正常運行但瀏覽器未啟動時（`browserConnected: false`），所有 API 端點返回 404

### 3. agent-browser（Node.js，CLI）— 赫米斯已安裝
- **安裝**：`npm install -g agent-browser`（~/.npm-global/bin/）
- **容器環境標配用法**：`agent-browser open <url> --args "--no-sandbox"`
  - 在 Linux 容器/VM 中執行若遇到「No usable sandbox」錯誤，加上 `--args "--no-sandbox"` 即可
- **用途**：快速任務、無嚴格 anti-bot 的網站

---

## 安裝方式（2026-06 實測更新）

### nodriver
```bash
# 建立獨立 venv（推薦，不影響 hermes-agent venv 和系統 python3）
python3 -m venv /tmp/nodriver-env
/tmp/nodriver-env/bin/pip install nodriver
```

**常見問題**：
- 赫米斯 venv（`~/.hermes/hermes-agent/venv/bin/python3`）：沒有 pip，`No module named pip`
- 系統 python3（`/usr/bin/python3`，Python 3.12，Ubuntu 24.04）：PEP 668 `externally-managed-environment`，不能直接 pip install
- **不要用 `--break-system-packages`**，會破壞系統 Python 的 PEP 668 保護
- nodriver 需要系統有 Chrome/Chromium 可執行檔。若無，agent-browser 是替代方案

### agent-browser
```bash
# 容器/VM 環境必須加 --args "--no-sandbox"
agent-browser open <url> --args "--no-sandbox"

# 正常工作流程
agent-browser open <url> --args "--no-sandbox"
agent-browser snapshot -i
agent-browser click @e1
agent-browser close
```

---

## If→Then 選擇決策樹

```
If：任務需要繞過 Cloudflare/anti-bot
And：目標是 Chrome 系網站
And：系統有 Chrome 可執行檔
Then：使用 nodriver（/tmp/nodriver-env/bin/python 執行）

If：任務需要繞過 Cloudflare/anti-bot
And：目標是 Chrome 系網站
And：系統無 Chrome 可執行檔
Then：使用 agent-browser（已知繞過方式有限但可用）

If：任務需要 Firefox 且已有 Camofox Docker 容器
Then：使用 Camofox（先 curl http://localhost:9377/health 確認 browserConnected:true）

If：傳統 Playwright/Puppeteer 可行（目標無嚴格 anti-bot）
Then：使用 agent-browser（已安裝，最快）
```

---

## Anti-Detection 原理

| 層面 | 標準 Playwright | Stealth（nodriver/camoufox）|
|------|-----------------|---------------------------|
| WebDriver binary | 有，指紋可檢測 | 無，直接 CDP |
| CDP handshake | 標準指紋 | 修改過的指紋 |
| 自動化特徵 | 明確（navigator.webdriver=true）| 消除或偽造 |
| TLS fingerprint | 標準指紋 | 修改過 |

---

## 外部驗證資料

- **nodriver benchmark**：[ianlpaterson.com/blog/anti-detect-browser-benchmark](https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi)
  - 7 個工具測試，31 個 Cloudflare 目標
  - nodriver 是唯一零封鎖的工具
- **Camoufox 文件**：[github.com/nickcis/camoufox](https://github.com/nickcis/camoufox)
- **相關文章**：[proxies.sx/blog/ai-browser-automation-camoufox-nodriver-2026](https://proxies.sx/blog/ai-browser-automation-camoufox-nodriver-2026)

---

## 與赫米斯現有技能的整合

| 現有技能 | 建議 |
|---------|------|
| `browser/camofox` | nodriver 為 Chrome 系替代方案，已更新章節 |
| `browser/agent-browser` | 加入容器環境 --no-sandbox 參考，已更新 SKILL.md |
| `metacognitive-learner` | Phase 3 工具搜尋時的瀏覽器自動化選項，已更新本文檔 |

---

## 重點提醒

⚠️ **不要將「venv 無 pip」固化為「nodriver 無法使用」**。赫米斯 venv 確實沒有 pip，但可以建立獨立 venv（`python3 -m venv /tmp/nodriver-env`）。這是環境設定問題，不是工具能力限制。

⚠️ **不要將「API key 過期」固化為「工具無法使用」**。API key 過期是環境/憑證問題，可通過更換 key 解決。

⚠️ **不要將「Camofox API 404」固化為「Camofox 壞了」**。`browserConnected: false` 時容器正常運行但瀏覽器引擎未啟動，所有 API 端點返回 404 是預期行為，需要 `docker restart camofox-browser` 恢復。