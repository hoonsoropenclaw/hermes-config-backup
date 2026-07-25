---
name: site-qa-checklist
description: "赫米斯狀態網站部署前 / 卸載後 / process state QA 檢查清單 — 結合 dogfood 探索測試、程式碼審查、Playwright 瀏覽器自動化測試、與 process 驗證 SOP。當使用者說「部署前檢查」「QA check」「上線前」「網站檢查」「部署網站」「卸載後驗證」「process 驗證」「pgrep 驗證」等關鍵字時喚醒此技能。"
risk: safe
source: hermes-internal
date_added: "2026-05-30"
last_updated: "2026-06-06"
---

# Site QA Checklist (Hermes Status Site)

## 觸發關鍵字
「部署前檢查」「QA check」「上線前」「網站檢查」「部署網站」「卸載後驗證」「process 驗證」「pgrep 驗證」「反安裝驗證」

---

## ⚠️ 部署後驗證陷阱（2026-06-06 新增 — 親身踩雷教訓）

> **核心原則：自我審查 ≠ 驗證。「我跑了部署指令，沒看到錯誤」≠「使用者能正常打開」**

### 陷阱 A：假設 git push 會自動觸發 Vercel 部署

**症狀：** 改完 → `git push` → 等 5 秒 → curl production URL → size 跟舊版一樣、新檔案 404

**根本原因：** Vercel **不會** 自動從 git push 觸發 production 部署，除非你在 Vercel 後台勾選「Git 整合 → Production Branch」並開啟 auto-deploy。**預設是手動的**。

**修正：** git push 完**一定要手動跑**：
```bash
cd <project-dir>
vercel --token "$VERCEL_API_TOKEN" --yes --prod
```

**驗證方式：** curl 抓**新加的 asset**（不是 index.html 本身，例如新加的 `js/chat-commands.js`）確認 size 變了、HTTP 200。如果還是 404 表示沒 deploy。

---

### 陷阱 B：Vercel 隨機 alias URL 會暫時 401

**症狀：** 部署成功後，vercel CLI 吐出 `https://<project>-<random>-hoonsors-projects.vercel.app`，但 curl 這個 URL 回 401，size ~15KB（Authentication Required 頁面）

**根本原因：** Vercel 每次 production 部署會生成新隨機 alias（如 `dashboard-seven-lac-35`），這個新 domain **需要 5-10 分鐘** 全球 DNS 同步才會通。

**修正：**
- **不要用隨機 alias URL 驗證部署** — 那是過渡狀態
- 用**固定名字的 alias**（如 `projectname.vercel.app`）驗證 — 這個會立刻指向最新部署
- 隨機 alias 等 5-10 分鐘後自己會通

**如何看固定 alias：** `vercel ls --token "$VERCEL_API_TOKEN"` → 看 `Production URL` 欄

---

### 陷阱 C：N100 內網 curl 200 ≠ 使用者打得開（DNS cache）

**症狀：** 從 N100 自己 curl 部署的 URL 回 200、size 正確、檔案內容正確，但使用者截圖顯示「ERR_NAME_NOT_RESOLVED」

**根本原因：**
1. 部署到 Vercel 後，domain 註冊到 Vercel 邊緣 DNS 伺服器
2. 不同 DNS resolver（Cloudflare 1.1.1.1、Google 8.8.8.8、ISP DNS）同步新 domain 需要 5-30 分鐘
3. 你的 curl 走 N100 的 DNS，可能在同步完成後才跑；但**使用者在他家/公司網路**，DNS cache 可能還沒更新

**驗證 SOP（多管道、必做）：**
```bash
# 1. 多 DNS 查詢（確認 domain 真的註冊了）
for dns in 1.1.1.1 8.8.8.8 9.9.9.9; do
  echo "$dns: $(dig +short @$dns <domain> A | head -1)"
done

# 2. N100 內網 curl 確認 200
curl -sI <url> | head -3

# 3. 給使用者時，主動告知：
#    「URL 是 X，建議用無痕模式（Ctrl+Shift+N）繞過 DNS cache，
#     或改 DNS 為 1.1.1.1，等 5-10 分鐘 DNS 自然同步」
```

**自我審查 SOP（強制）：**
- ❌ 不可只做「N100 curl 200」就回報部署成功給使用者
- ✅ 必做：多 DNS 解析 + 給使用者建議（無痕/換 DNS/等 5-10 分鐘）

---

### 陷阱 D：從「單元檔案驗證」誤判為「整體流程驗證」

**症狀：** 在本地 `python3 -m http.server` 跑 `tabs/overview.html`，**單獨**打開該檔時 SVG/JS 都正常 render，於是回報「部署成功」。但 production 上從首頁點 tab 後，**該 tab 內容是空的**。

**根本原因：** 單元驗證跟整體驗證的路徑**完全不同**：
- 單元：`http://localhost:PORT/tabs/xxx.html` → 直接開啟 → 頁面所有 `<script>` 都會跑
- 整體：`http://localhost:PORT/` → `loadTab('xxx')` → `contentDiv.innerHTML = html` → **`<script>` 不會跑**（HTML5 spec）

**驗證 SOP（強制）：**
- ✅ 必做：先驗證整體流程（從首頁進入，點 tab，檢查內容）→ 再驗證單元
- ❌ 不可只驗證單元就回報「整個網站正常」

**特別注意：** 任何用了 `loadTab()` / `innerHTML` 注入的 SPA 結構，**所有需要在 tab 內執行的 JS 必須用 `window.*` 命名空間 + inline event handler，不能放 `<script>` 標籤**（這個 pitfall 已在下方「Bug: loadTab() innerHTML skips sibling scripts」記載，**但這裡是從單元 vs 整體這個角度補充**）

---

### 陷阱 E：Vercel auto-deploy 設定檢查方法

```bash
# 看 GitHub repo 是否有 Vercel webhook
gh api repos/<owner>/<repo>/hooks 2>&1 | grep -A 2 vercel

# 看 Vercel project 的 git integration
vercel inspect <project-url> --token "$VERCEL_API_TOKEN" 2>&1 | grep -i git
```

如果 webhook 不存在或 git integration 沒啟用 → 永遠要手動 `vercel --prod`。

### 陷阱 F：本地 server 渲染通過 ≠ 部署完成（2026-06-06 新增）

**症狀：** 跑 `python3 -m http.server` 開本地 server，headless browser 開 `http://127.0.0.1:PORT/` 看到新元素、互動正常、截圖正確，於是回報「完成」。但使用者去 production URL 看不到。

**根本原因：**
- 本地 server 跑的是「現在檔案系統的內容」，沒經過 build、沒經過 CDN、沒經過 cache
- 即使 `git push` 成功，Vercel 還沒 build 完、CDN 還沒同步
- 即使 build 完了，CDN edge cache 可能還在吐舊版（5-30 分鐘）
- 即使 cache 過了，**所有步驟（git push + vercel --prod + 等 DNS + 等 cache）都做齊才能從 production 端看到**

**修正（不可跳 SOP）：**
1. 本地 server 渲染通過 → 證明「code 沒寫壞」（必要、不足夠）
2. `git add -A && git commit -m "..." && git push origin main`（必要、不足夠）
3. `vercel --token "$VERCEL_API_TOKEN" --yes --prod` 手動部署（必要、不足夠）
4. `sleep 30` 等 DNS / CDN 穩定
5. **headless browser 開 production URL 實測**（必要 + 足夠）
6. **回報完成必須附上「從 production 端觀察到的具體輸出」**，不是「我在本地測過了」

**自我審查 checklist（部署任務必過）：**
- [ ] git push 成功（看 push 輸出）
- [ ] `vercel --prod` 成功（看 `Aliased: ...` 行）
- [ ] `curl https://production/.../xxx.html` 抓到新內容（grep 我的新元素應該 > 0）
- [ ] headless browser 開 production URL 看到新元素
- [ ] 截圖或文字輸出證明「使用者視角」看到的內容

**If** 這 5 項有任一沒做 **Then** 不能回報「完成」給使用者

**If** 被使用者糾正「我查看了，但沒看到」**Then** 立即回頭補做 layer 3-5，不要辯解「我本地測過」

---

## 🚦 完整部署 + 驗證 SOP（更新版）

1. **本地驗證**（必做、不可跳）：
   - 從首頁進入（不是單元檔案）走完整流程
   - 多 DNS 查詢（如有自訂 domain）
   - 確認所有 JS 該跑的都有跑、SVG/React 都 render
2. **git push**（同步到 GitHub）
3. **手動 `vercel --prod`**（不可跳過，git push 不會自動觸發）
4. **部署後多層驗證**：
   - 主要 domain HTTP 200 + size 預期
   - 新加的 asset 檔案也 200
   - 隨機 alias URL **不要**用來驗證（會暫時 401）
   - headless browser 從首頁進、點 tab、檢查內容
5. **回報給使用者**：
   - 給固定名字的 domain（不是隨機 alias）
   - 主動告知「建議無痕模式繞過 DNS cache」
   - 不要假裝「從 N100 看得見 = 你也看得見」

---

## 前置搜尋：歷史問題 Recall（MemPalace Fallback）

**目的：** 在開始 QA 前，先搜尋是否有類似的歷史問題，避免重蹈覆轍。

### 三層搜尋策略
1. **Phase 1 - session_search**：先用本地對話記錄搜尋（快速、低成本）
2. **Phase 2 - mempalace__mempalace_search**：若 Phase 1 分數 < 0.3 或無結果，自動觸發，向量語意搜尋
3. **Phase 3 - LLM Re-rank**：若 Phase 2 分數 < 0.4 或結果 > 10，使用內建 LLM 對候選記憶重排序

### 觸發條件（If→Then）
- If：`session_search(query="網站 tab 問題 HTML div 結構", limit=3)` 結果分數 < 0.3 或結果數 = 0
- Then：自動呼叫 `mempalace__mempalace_search(query="網站 tab 切換 JavaScript 選擇器", limit=5)`
- If：mempalace_search 分數仍 < 0.4
- Then：使用下方的 Prompt 讓 LLM re-rank，取分數最高的 3 條

### LLM Re-rank Prompt
```
你是記憶檢索助手。請根據以下查詢和候選記憶，評估每條記憶的相關性並重新排序。

原始查詢：{query}

候選記憶：
{index}. [{source}] 相似度={score}
{text_preview}

請以 JSON 格式輸出：
{{"ranked": [{{"index": N, "reason": "為什麼相關", "new_score": 0-1}}]}}
只輸出 JSON，不要其他文字。
```

### 常見 QA 相關關鍵字搜尋
- `session_search("hermes-status-site tab 問題")` → 查過往對話
- `mempalace_search("網站部署 HTML div 結構 空白")` → 語意備援
- `session_search("frontend-dev 程式碼檢查流程")` → 檢查 SOP 遵循情況

---

## 檢查流程

### Phase 1: 檔案結構驗證
確認新架構完整：
```
hermes-status-site/
├── index.html          # 主檔案（含所有 Tab 內容 + 清晰區塊註解）
├── css/styles.css      # 樣式檔
├── js/app.js           # JS（含修復後的 showTab 函式）
├── tabs/               # 備份用 Tab 內容（方便日後重構為多檔案部署）
│   ├── overview.html
│   ├── memory.html
│   └── ...
└── SPEC.md             # 實作規格文件
```

### Phase 2: Tab 功能測試（使用 browser 工具）
目標 URL：`https://raphael-status-site.vercel.app/`

使用 `dogfood` 技能的流程，但聚焦以下核心檢查：

**1. Tab 切換驗證（使用 onclick 屬性）**
```js
// 在 browser_console 中執行
const tabs = ['overview','memory','delegation','tools','skills','soul','mdfiles','scheduler','learning','sysinfo','dashboard'];
tabs.forEach(t => {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.getAttribute('onclick').includes("showTab('" + t + "')")) btn.click();
    });
    const el = document.getElementById('tab-' + t);
    const ok = el && getComputedStyle(el).display === 'block';
    console.log(t + ': ' + (ok ? '✅' : '❌'));
});
```

**2. 所有 Tab 內容非空白驗證（使用 onclick 比對）**
```js
tabs.forEach(t => {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.getAttribute('onclick').includes("showTab('" + t + "')")) btn.click();
    });
    const el = document.getElementById('tab-' + t);
    const len = el ? el.innerText.length : 0;
    console.log(t + ': ' + len + ' chars');
});
```

**3. JS Console 無 Error**
```js
JSON.stringify({
  errors: document.querySelectorAll('[data-tab]').length,
  memory_chars: document.getElementById('tab-memory').innerText.length
});
```

### Phase 3: 程式碼審查（使用 agent-skills-audit）
針對 `index.html` 執行 `agent-skills-audit` 技能的重點審查：

**必查項目：**
- `showTab` 函式使用 `onclick` 屬性比對（`getAttribute('onclick').includes(...)`）而非 CSS 選擇器，避免特殊字符轉義問題
- 所有 Tab ID（如 `tab-mdfiles`）與 `showTab('name')` 中的 name 一致
- CSS `display: none` / `display: block` 切換正常
- `addEventListener` vs `onclick` 一致性
- ⚠️ 注意：網站使用 `mdfiles`（不是 `md-files`）作為 tab ID 和按鈕名稱

### Phase 4: 部署後驗證
1. Vercel API 確認 `readyState: READY`
2. curl 驗證 HTTP 200
3. browser_navigate 確認頁面標題正確
4. 再次執行 Tab 切換測試

---

## Phase 5: Playwright 瀏覽器自動化測試（深度 QA）

**目的：** 用 Playwright 在無頭瀏覽器中執行完整的功能測試，確保 Tab 切換、DOM 結構、Console 錯誤都被檢測到。這是獨立於 `browser` 工具的更深層測試。

**工具：** `~/.local/bin/playwright`（路徑已確認）

### 測試脚本：完整的 Tab + DOM + Console 驗證

```python
#!/usr/bin/env python3
"""
hermes-status-site Playwright QA 測試
測試目標：Tab 切換、DOM 結構完整性、Console 錯誤檢測
"""
import asyncio
from playwright.async_api import async_playwright

TABS = ['overview', 'memory', 'delegation', 'tools', 'skills',
        'soul', 'mdfiles', 'scheduler', 'learning', 'sysinfo', 'dashboard']

async def run_qa(url: str) -> dict:
    results = {
        'url': url,
        'tabs': {},
        'console_errors': [],
        'dom_issues': [],
        'passed': True
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 攔截 console errors
        page.on('console', lambda msg: results['console_errors'].append({
            'type': msg.type, 'text': msg.text
        }) if msg.type == 'error' else None)

        # 攔截 page errors
        page.on('pageerror', lambda err: results['console_errors'].append({
            'type': 'pageerror', 'text': str(err)
        }))

        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            results['dom_issues'].append(f'導航失敗: {e}')
            results['passed'] = False
            await browser.close()
            return results

        # 測試每個 Tab 切換
        for tab_name in TABS:
            tab_id = f'tab-{tab_name}'
            tab_content = page.locator(f'#{tab_id}')
            tab_btn = page.locator(f'[data-tab="{tab_name}"]')

            # 檢查 Tab 內容元素存在
            content_exists = await tab_content.count() > 0
            btn_exists = await tab_btn.count() > 0

            if not content_exists:
                results['dom_issues'].append(f'缺少 tab content: #{tab_id}')
                results['tabs'][tab_name] = '❌ 缺少 content 元素'
                continue

            # 點擊 Tab 按鈕
            if btn_exists:
                await tab_btn.click()
                await page.wait_for_timeout(300)  # 等待動畫/過渡
            else:
                # 嘗試用 onclick 方式點擊
                all_btns = page.locator('.tab-btn')
                count = await all_btns.count()
                clicked = False
                for i in range(count):
                    btn = all_btns.nth(i)
                    onclick = await btn.get_attribute('onclick') or ''
                    if f"showTab('{tab_name}')" in onclick or f'showTab("{tab_name}")' in onclick:
                        await btn.click()
                        await page.wait_for_timeout(300)
                        clicked = True
                        break
                if not clicked:
                    results['dom_issues'].append(f'找不到 tab 按鈕: {tab_name}')

            # 檢查內容是否顯示
            display = await tab_content.evaluate('el => getComputedStyle(el).display')
            inner_len = await tab_content.evaluate('el => el.innerText.length')

            if display == 'none':
                results['tabs'][tab_name] = f'❌ display={display}, chars={inner_len}'
                results['passed'] = False
            elif inner_len == 0:
                results['tabs'][tab_name] = f'⚠️ display={display}, chars=0 (空白內容)'
            else:
                results['tabs'][tab_name] = f'✅ display={display}, chars={inner_len}'

        # 檢查 HTML 結構（</html> 後不應有內容）
        html_content = await page.content()
        html_end = html_content.rfind('</html>')
        if html_end != -1:
            after_html = html_content[html_end + len('</html>'):].strip()
            if after_html:
                results['dom_issues'].append(f'</html> 後有多餘內容: {after_html[:100]}')

        # 檢查是否有未閉合的 div
        div_open = html_content.count('<div')
        div_close = html_content.count('</div>')
        if div_open != div_close:
            results['dom_issues'].append(f'DOM 結構問題: <div> 數量={div_open}, </div> 數量={div_close}')

        await browser.close()
        return results

if __name__ == '__main__':
    import sys, json

    test_url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'

    result = asyncio.run(run_qa(test_url))

    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result['passed'] and not result['dom_issues'] else 1)
```

### 執行方式
```bash
# 方式 1: Python 直接執行
python3 ~/.hermes/skills/productivity/site-qa-checklist/scripts/playwright_qa.py http://localhost:8765/

# 方式 2: 使用 playwright CLI
playwright test --browser=chromium --reporter=line  # 需要先先有測試檔案

# 方式 3: 整合进部署流程
cd /home/hoonsoropenclaw/hermes-status-site
python3 ~/.hermes/skills/productivity/site-qa-checklist/scripts/playwright_qa.py http://localhost:8765/
echo "Exit code: $?"  # 0 = 通過, 1 = 有問題
```

## 赫米斯網站部署相關

**重要參考文檔：** `references/vercel-deploy-path-pitfalls.md`

內容包括：
- 赫米斯 vs 拉斐爾網站路徑差異（防止腳本更新錯誤目標）
- 完整部署 SOP（git push + vercel --prod）
- 驗證技能統計區塊存在的指令
- Cron job 自動部署需求說明
- **2026-06-06 新增** 5 個部署後驗證陷阱（A-E）

### 讀取結果並決策
```python
import json, subprocess

result = subprocess.run(
    ['python3', '~/.hermes/skills/productivity/site-qa-checklist/scripts/playwright_qa.py', url],
    capture_output=True, text=True
)
data = json.loads(result.stdout)

if data['passed']:
    print("✅ Playwright QA 全部通過")
else:
    print("❌ 發現問題：")
    for issue in data['dom_issues']:
        print(f"  - {issue}")
    for tab, status in data['tabs'].items():
        if '❌' in status or '⚠️' in status:
            print(f"  - {tab}: {status}")
```

### 插入位置修復 SOP
**目標:** 將內容正確插入到 `#tab-skills` 容器內，而非其外部

**步驟：**
1. 找到 `tab-skills` 的內容區結尾（倒數第二個 `</div>` 之前）
2. 不要用 `<!-- Tab: Soul -->` 當插入點（那個 comment 在 tab-skills 外部）
3. 用 regex 找到 `<div id="tab-skills"` 區塊的開始和結尾，在結尾 `</div>` **之前**插入

**Python 實作：**
```python
import re

with open('index.html', 'r') as f:
    html = f.read()

pattern = r'(<div id="tab-skills"[^>]*>.*?)(\s*</div>\s*)(<!-- Tab: Soul -->)'
match = re.search(pattern, html, re.DOTALL)
if match:
    insert_pos = match.start(2)
    html = html[:insert_pos] + STATS_BLOCK + html[insert_pos:]
```

### 常見 Bug 修復參考

### Bug: 本機打開 index.html Tab 內容空白
**原因:** 使用 `fetch()` 動態載入 tab 檔案，但 `file://` 協定有 CORS 限制
**修復:** 將所有 Tab 內容直接內嵌在 `index.html` 中，用清楚區塊註解標記
**折衷:** 保留 `tabs/*.html` 供日後重構為真正多檔案部署

### Bug: 插入內容不見了（插入位置在容器外）
**症狀:** 直接用 `curl` 看 HTML 原始碼有內容，但瀏覽器 tab 切換後看不到該內容。
**根本原因:** 插入標記（comment）位於 `</div>` 關閉標籤**之後**，導致新內容變成容器的兄弟節點，而非子節點。

```html
<!-- 錯誤的結構：插入點在 tab-skills 的 </div> 之後 -->
<div id="tab-skills" class="tab-content">
    <!-- 技能生態系內容 -->
</div>
    <!-- ↑ 插入點在這裡（錯誤） -->
<div>統計區塊</div>   ← 跑到外面了

<!-- 正確的結構：插入點在 </div> 之前 -->
<div id="tab-skills" class="tab-content">
    <!-- 技能生態系內容 -->
    <!-- ↑ 插入點在這裡（正確） -->
</div>
```

**驗證方法（browser_console）：**
```js
const tab = document.getElementById('tab-skills');
tab.innerHTML.includes('🦞'); // 應為 true
```

**修復方法：** 使用倒數第二個 `</div>` 之前的位置作為插入點，或用更精確的 DOM 解析（如 `regex` 匹配 `id="tab-skills"` 區塊的開關）。

### Bug: Tab loads but data/script is undefined — loadTab() innerHTML skips sibling scripts

**症狀：** Tab 看起來有載入（有 DOM 結構），但功能不正常。例如：
- `tabs/md-files.html` 的卡片不展開（所有卡片同時 visible 或完全看不見）
- 某個 tab 的 JS 變數是 `undefined`，但直接開啟該 HTML 檔案是正常的

**根本原因：** `loadTab()` 的實作只取 `innerHTML`：

```javascript
// index.html 中的 loadTab()
const contentEl = doc.querySelector('#tab-content') || doc.body.firstElementChild
contentDiv.innerHTML = contentEl.innerHTML  // ← 只複製 innerHTML！
```

如果 `tabs/xxx.html` 的結構是：

```html
<div id="tab-content">
    <!-- 卡片內容（由 sync 腳本注入） -->
</div>
<script>const MD_FILES_DATA = [...];</script>  ← 這個在 #tab-content 外面！
                                                        // loadTab() 完全忽略了它
```

則 `MD_FILES_DATA` 永遠是 `undefined`，依賴它的 `renderFiles()` 不會執行。

**修復方向（二選一）：**

1. **修改 loadTab() 同時注入 script**（複雜度低，但要避免重複執行）：
   ```javascript
   // 在 innerHTML 注入後，手動執行 script 標籤內容
   const scripts = doc.querySelectorAll('#tab-content + script');
   scripts.forEach(s => {
       const newScript = document.createElement('script');
       newScript.textContent = s.textContent;
       contentDiv.appendChild(newScript);
   });
   ```

2. **將資料改為 window 命名空間**（推薦，更穩定）：
   ```html
   <!-- 在 index.html <head> 中宣告，全域可見 -->
   <script>window.__MD_FILES__ = window.__MD_FILES__ || [];</script>

   <!-- tabs/md-files.html 只負責 UI，不宣告資料 -->
   <div id="tab-content">...</div>
   <script>
       // 讀取 window.__MD_FILES__ 而非本地 const
       renderFiles(window.__MD_FILES__);
   </script>
   ```

**驗證方法：**
```js
typeof MD_FILES_DATA  // 應該是 'undefined'（沒有宣告）
typeof window.__MD_FILES__  // 應該是 'object'（已在 head 宣告）
```

**預防原則：** 動態載入的 tab HTML 內容，所有 JS 資料必須透過 `window.*` 命名空間傳遞，不能依賴同檔案的 `<script>` 標籤。

### Bug: Tab 點擊後內容不切換
**原因:** `querySelector` 使用 `\'` 匹配 HTML 中的 `'`，兩者不一致
**修復:** 使用 `data-tab` 屬性 + `getAttribute` 比對，完全繞過字串跳脫問題

```js
// 錯誤（舊版）
document.querySelector('.tab-btn[onclick="showTab(\'' + name + '\')"]')

// 正確（新版）
document.querySelectorAll('.tab-btn').forEach(btn => {
    if (btn.getAttribute('data-tab') === name) btn.classList.add('active');
});
```

### Bug: 本機打開 index.html Tab 內容空白
**原因:** 使用 `fetch()` 動態載入 tab 檔案，但 `file://` 協定有 CORS 限制
**修復:** 將所有 Tab 內容直接內嵌在 `index.html` 中，用清楚區塊註解標記
**折衷:** 保留 `tabs/*.html` 供日後重構為真正多檔案部署

## 部署指令
```python
import urllib.request, json, base64, os

BASE = '/home/hoonsoropenclaw/hermes-status-site'
files = []
for root, dirs, filenames in os.walk(BASE):
    for fname in filenames:
        if '.git' in os.path.join(root, fname): continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        files.append({"file": os.path.relpath(fpath, BASE), "data": data, "encoding": "base64"})

with open('/home/hoonsoropenclaw/.hermes/.env') as f:
    token = next(l for l in f if 'VERCEL_API_TOKEN' in l).split('=', 1)[1].strip()

payload = {
    "name": "raphael-status-site",
    "files": files,
    "projectSettings": {"framework": None, "buildCommand": None, "outputDirectory": None, "installCommand": None},
    "target": "production"
}
req = urllib.request.Request("https://api.vercel.com/v13/deployments",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST")
with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read())
print(result['id'], result['url'], result['readyState'])
```

### 插入內容到 SPA index.html 的正確方法

**目標：** 將內容（如技能呼叫統計）插入到 `#tab-skills` 容器內

**錯誤做法（已造成 Bug）：**
```python
# ❌ 用 <!-- Tab: Soul --> 當插入點（這個 comment 在 tab-skills 的 </div> 之後）
parts = html.split('<!-- Tab: Soul -->')
html = parts[0] + stats_block + parts[1]
# 結果：stats_block 變成 tab-skills 的兄弟節點，不是子節點
```

**正確做法：**
```python
import re
pattern = r'(<div id="tab-skills"[^>]*>(?:(?!</div>).)*)(\s*</div>\s*)(<!-- Tab: Soul -->)'
match = re.search(pattern, html, re.DOTALL)
if match:
    insert_pos = match.start(2)  # 在倒數第一個 </div> 之前
    html = html[:insert_pos] + stats_block + html[insert_pos:]
```

**驗證方法：**
```bash
# 正確的縮排結構：統計區塊應該是 12 空格（tab-skills 的子元素）
grep -n "🦞 技能呼叫統計" /home/hoonsoropenclaw/hermes-status-site/index.html
```

**正確的 HTML 結構：**
```html
        <div id="tab-skills" class="tab-content">
            <!-- 技能生態系內容 -->
            <div class="section" style="margin-top:24px;">  <!-- 12 空格，tab-skills 內 -->
                🦞 技能呼叫統計
            </div>
        </div>
    <!-- Tab: Soul -->  <!-- 0 空格，tab-content 的兄弟 -->
```

---

### Cron Job 更新頻率

**問題：** 插入點在 `</div>` 之後，導致內容變成容器的兄弟節點而非子節點

**修復步驟：**
1. 不要用 `<!-- Tab: Soul -->` 當插入點（它在 tab-skills 外部）
2. 用 regex 找到 `<div id="tab-skills"` 區塊，在倒數第一個 `</div>` 之前插入

**Python 實作：**
```python
import re
with open('index.html', 'r') as f:
    html = f.read()
pattern = r'(<div id="tab-skills"[^>]*>(?:(?!</div>).)*)(\s*</div>\s*)(<!-- Tab: Soul -->)'
match = re.search(pattern, html, re.DOTALL)
if match:
    insert_pos = match.start(2)  # 在 </div> 之前
    html = html[:insert_pos] + stats_block + html[insert_pos:]
```

**驗證：**
```bash
grep -n "🦞 技能呼叫統計" index.html
# 正確：12 空格縮排（在 tab-skills 內）
# 錯誤：0 空格縮排（在 tab-skills 外）
```

---

## ⚠️ 卸載 / 反安裝後 process state 驗證 SOP（2026-06-08 新增 — 親身踩雷教訓）

> **核心原則：卸載某個套件 / service 後，必須驗證「相關 process 都真的清乾淨」**。**「卸載指令回報成功」≠「沒有殘留 process / unit / PID」**。

### 陷阱 G：`pgrep -f <name>` 對「path 含子字串」的 process 會誤報

**症狀：** 卸載某個套件（例如 OpenClaw、某個 npm 套件）後，跑 `pgrep -f openclaw` 報 6 個進程，嚇一跳以為漏網之魚。

**根本原因：** `pgrep -f` 對**完整 command line** 做 regex 匹配，任何 path 含 `openclaw` 子字串的 process 都會中：
- `~/.hermes/hermes-agent/` 內某些子字串（hermes-agent 內建 OpenClaw 遷移工具）
- sshd
- 跑 `pgrep` 自己的 bash
- 任何曾經用過 OpenClaw API 的 subagent

**正確查法（任選一）：**
```bash
# 1. 更精準的完整 path 比對
pgrep -f 'openclaw/dist/index.js'   # 只比對 openclaw 套件自己的 process
# 2. 看完整指令辨識
pgrep -af openclaw | head -20       # -a 顯示完整 command line
# 3. 找真正的 openclaw node 進程
ps -ef | grep -E 'node.*openclaw|openclaw.*dist' | grep -v grep
```

**If** 用 `pgrep -f <name>` 確認 process 已清乾淨 **Then** 至少用 `pgrep -af` 看完整指令、不要只看數字、不要看到數字 > 0 就誤報漏網之魚

### 陷阱 H：卸載前用 PPID 查「真正 owner」才能避免誤刪（2026-06-08 親身驗證）

**症狀：** 準備卸載某個 service X，猶豫「X 是被誰啟動的？是 A service 還是 B service ？」

**錯誤做法：** 從 config 檔讀「誰提到 X」就推論誰管 → 可能推論錯

**正確做法：**
```bash
# 1. 找 X 的 process
pgrep -f X
# 2. 看 X 的 PPID（parent process ID）
ps -o pid,ppid,cmd -p <X_pid>
# 3. 確認 PPID 是哪個 long-running 服務（例如 hermes 主進程 pid 1872192）
ps -o pid,ppid,cmd -p <X_ppid>
```

**真實案例（2026-06-08 OpenClaw 反安裝）：** 預期 mempalace MCP 是 OpenClaw 啟動 → 查 PPID 才發現是赫米斯主進程 → 卸載 OpenClaw 不會影響 mempalace、**整個「卸載前要改 hermes MCP 設定加 env var」的方案變成不需要**。

**If** 卸載前猶豫「A 跟 B 哪個才是 X 的 owner」 **Then** `ps -ef | grep X` + `ps -o pid,ppid,cmd` 查 PPID 鏈，不要從 config 檔讀「誰提到 X」就推論誰管

### 陷阱 I：套件卸載 100% 會清 CLI binary、但 user-installed systemd unit 殘檔要手動清

**症狀：** 跑 `npm uninstall -g <package>` 或套件自帶的 `uninstall` 指令，CLI 跟 lib 都刪了、systemd service 也 disable 了，但 `~/.config/systemd/user/<package>*.{service,timer}` 還在。

**根本原因：** 套件卸載只清 `default.target.wants/` 跟 `timers.target.wants/` 內的 symlink，沒清 unit 檔本體（uninstall 邏輯 bug，不是預期行為）。

**修正（不可跳）：**
```bash
# 1. 找殘檔
ls -la ~/.config/systemd/user/ | grep <package>
# 2. 手動刪 unit 檔 + symlink
rm -f ~/.config/systemd/user/<package>*.{service,timer}
rm -f ~/.config/systemd/user/default.target.wants/<package>*.service
rm -f ~/.config/systemd/user/timers.target.wants/<package>*.timer
# 3. reload + reset-failed
systemctl --user daemon-reload
systemctl --user reset-failed
# 4. 驗證（必須空）
find ~/.config/systemd -name '*<package>*' 2>&1 | head
```

**If** 套件卸載後看到 systemd `not-found inactive dead` 但 unit 檔還在 **Then** 這是套件卸載 bug、要手動 `rm -f` unit 檔 + `daemon-reload` + `reset-failed`

### 陷阱 J：卸載前必先 `--dry-run` 或 list target

**症狀：** 直接下 `npm uninstall -g X` 或 `apt remove Y` 或 `rm -rf Z`，卸載後才發現有 5 個依賴套件一起被砍、3 個 systemd service 一起被停、2 GB 資料夾被刪。

**預防 SOP：**
```bash
# 任何卸載指令前必先看 help 找 --dry-run
<uninstall_cmd> --help | grep -i 'dry-run\|--all'

# 沒 --dry-run 也要先 list target
which X                            # 找 binary 在哪
readlink -f $(which X)             # 找真實路徑
dpkg -L X | head                   # Debian 套件看裝了哪些檔（apt 系列）
npm list -g --depth=0              # npm 全域看裝了什麼
```

**If** 卸載指令有 `--dry-run` flag **Then** 必先跑確認會動什麼，不要直接看 help 就下指令

### 卸載後 process state 完整驗證 SOP

當卸載某個套件 / service 完，**不可只回報「卸載指令成功」就交差**。必做 5 步驗證：

```bash
# 1. 確認套件本身已刪
command -v <package> 2>&1 || echo "✓ CLI 找不到"
which <package> 2>&1 || echo "✓ 套件路徑找不到"

# 2. 確認沒殘留 process（用陷阱 G 的精準查法）
pgrep -f '<package>/dist' 2>&1 || echo "✓ 無 <package> process"
pgrep -af <package> 2>&1 | head -5  # 假陽性逐一辨識

# 3. 確認 systemd 沒殘檔（用陷阱 I）
find ~/.config/systemd -name '*<package>*' 2>&1 || echo "✓ 無 <package> unit 殘檔"
systemctl --user list-unit-files | grep <package> || echo "✓ systemd 不認得 <package>"

# 4. 確認依賴該套件的關鍵服務仍活（用陷阱 H 找真正的 owner）
# 例如：卸載 OpenClaw 後跑 mcp_mempalace_search 確認 mempalace 仍能用
# 例如：卸載某個 CLI 後跑 <other_cli> whoami 確認 CLI 認證檔未被誤刪

# 5. 確認使用者面向的功能仍正常（從 production / public URL 測）
# 例如：卸載 Vercel CLI 不會影響已部署的 status site 公開 URL
```

**自我審查 checklist（卸載 / 反安裝任務必過）：**
- [ ] 卸載指令跑成功（看 exit code 0、實際輸出）
- [ ] CLI binary 跟 lib 都刪了
- [ ] `pgrep -f <package>/dist` 無結果（精準查法）
- [ ] `find ~/.config/systemd -name '*<package>*'` 為空
- [ ] 依賴套件 / MCP 工具 / CLI 認證 仍可用（用工具實際呼叫一次）
- [ ] 生產端服務（公開 URL、cron job）仍正常

**If** 這 6 項有任一沒做 **Then** 不能回報「完成」給使用者

### 卸載前必問 3 件套

開始任何卸載任務前，**先問使用者這 3 個問題**（或自己查清楚再決定）：

1. **「X 是被誰啟動的」**（用 `ps -o ppid -p <X_pid>` 查）
2. **「X 的卸載會動到哪些檔 / 服務 / process」**（用 `--dry-run` 或 list target）
3. **「X 卸載後有誰會被連帶影響、需要備份 / 轉移 / 重啟」**（用「卸載後 process state 完整驗證 SOP」的步驟 4-5）

**If** 這 3 個問題沒答案 **Then** 不要開始卸載，先查清楚再說

---

## 支援檔案

- `references/vercel-deploy-path-pitfalls.md` — Vercel 部署流程 + 路徑陷阱
- `references/deploy-self-verification-failures.md` — 自我審查失敗案例
- `references/process-uninstall-verification.md` — 卸載後 process state 完整驗證 SOP（2026-06-08 新增，含 pgrep 精準查法、PPID 查 owner、套件卸載 systemd 殘檔、卸載前必 dry-run 4 個新陷阱）