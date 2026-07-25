# Browser Automation — Stealth Browsers & nodriver 實測經驗

## 2026-06-21 nodriver 實測（Cycle 2026-06-21 16:29）

### nodriver v0.50.3 核心發現

**原理**：直接用 CDP（Chrome DevTools Protocol）溝通，不經 WebDriver/Selenium/Playwright。
- Benchmark：31 個 Cloudflare 目標零封鎖（唯一全過的工具）
- 對比：Playwright/Camoufox/Patchright 全部在同樣測試失敗

**安裝方式**（赫米斯 N100 環境）：
```bash
# 赫米斯 venv 沒有 pip，用獨立 venv
python3 -m venv /tmp/nodriver-env
/tmp/nodriver-env/bin/pip install nodriver

# nodriver v0.50.3 已通過測試
```

**必備參數**（N100 無 root/sandbox 環境）：
```python
browser = await driver.start(
    browser_executable_path='/path/to/chrome',
    headless=True,
    sandbox=False   # 必須 False，否則 "Failed to connect to browser"
)
```

**可用 Chrome 二進位**（Playwright 快取，nodriver 可直接用）：
- `/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`（推薦，較新）
- `/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`

**API 注意點**（v0.50.3）：
- `tab.title` 是 property（非 method），直接 access
- `tab.content()` 不存在 → 用 `tab.evaluate('document.documentElement.outerHTML')`
- `browser.stop()` 後 event loop 會 closed，asyncio cleanup 有 warning（正常）

**成功測試腳本**：
```python
import asyncio, nodriver as driver

async def main():
    browser = await driver.start(
        browser_executable_path='/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',
        headless=True,
        sandbox=False
    )
    tab = await browser.get('https://example.com')
    print(f'URL: {tab.url}, title: {tab.title}')
    html = await tab.evaluate('document.documentElement.outerHTML')
    print(f'HTML length: {len(str(html))}')
    await browser.stop()

asyncio.run(main())
```

---

### Camofox vs nodriver 選用決策

| 場景 | 推薦 |
|------|------|
| Firefox 系目標 | Camofox |
| Chrome 系 + anti-bot 嚴格 | nodriver |
| 快速任務 + 無 anti-bot | agent-browser（已安裝）|
| YouTube 認證瀏覽 | Camofox（Cookie import 已支援）|
| Cloudflare 嚴格站點 | nodriver（benchmark 唯一全過）|

**nodriver 的限制**：
1. 需要 Chrome/Chromium 可執行檔（Camofox 是 Docker 隔離，nodriver 直接跑系統 Chrome）
2. N100 無 root 必須 `sandbox=False`
3. 無內建 cookie management（需自己刻）

---

### nodriver 環境差異陷阱

| 問題 | 原因 | 解法 |
|------|------|------|
| `FileNotFoundError: could not find a valid chrome browser` | 預設 find_chrome_executable() 找不到路徑 | 明確指定 `browser_executable_path=` |
| `Failed to connect to browser` + `running as root` hint | `sandbox=True` 在 root 環境被拒 | `sandbox=False` |
| `AttributeError: 'Tab' has no attribute 'content'` | v0.50.3 API 差異 | 用 `tab.evaluate('document.documentElement.outerHTML')` |
| `TypeError: object NoneType can't be used in 'await'` | `browser.stop()` 已觸發 loop cleanup | `await browser.stop()` 放最後一行 |

---

### If→Then

**If** 要自動化 Chrome 系目標且有 anti-bot（Cloudflare 等）
**Then** 用 nodriver（venv: `/tmp/nodriver-env`）+ Playwright 快取 Chrome + `sandbox=False` + `browser_executable_path=` 明確指定

**If** nodriver 啟動失敗並報 `running as root`
**Then** 確認 `sandbox=False` 已傳入，不是 `no_sandbox=True`

**If** nodriver 報 `FileNotFoundError: could not find a valid chrome browser`
**Then** 明確指定 `browser_executable_path='/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'`

**If** 需要在赫米斯 autonomous cycle 安裝 nodriver
**Then** 用 `python3 -m venv /tmp/nodriver-env && /tmp/nodriver-env/bin/pip install nodriver`，不要用 hermes venv（無 pip）
