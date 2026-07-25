# Vercel CLI / API / 部署相關踩雷

> 觸發:任何 vercel CLI 指令、Vercel REST API 呼叫、env 變數管理、部署流程
> 建立時間: 2026-06-05
> 條目數: **8**（2026-06-08 新增：vercel env pull masks API keys irreversibly）

---

### vercel env pull irreversibly masks sensitive API keys (2026-06-08)
**發現時間**: 2026-06-08
**觸發情境**: `eval-sync` cron job 失敗 — `AGENT_API_KEY not found`，但 `.env.local` 內有此變數
**症狀**:
- `cat hermes-portal/.env.local` 顯示 `AGENT_API_KEY=***`（3 個星號）
- `sync_evaluations.py` 的 `get_api_key()` 找到這個 key，但 `***` 不是有效 API token
- 腳本認為 key 是 `***`，條件 `if key:` 通過（truthy），所以回傳 `None` → exit(1)
- 從 Vercel dashboard 看，AGENT_API_KEY 的 value 也是被 mask 的 `***`

**根因**:
- `vercel env pull` 對**所有** env 變數執行「敏感值遮蔽」行為
- 「敏感」判定標準：Vercel 內部邏輯，AGENT_API_KEY 類（看起來像 key 的）預設被遮蔽
- 遮蔽後的 `***` **看起來像**有值（`if key:` 為 true），但**不是有效憑證**
- 最重要：**原始值被永久刪除**，無法從 Vercel 恢復，只能 regenerate

**解法**（2 步）：
1. **在 Vercel dashboard regenerate key**：Vercel dashboard → project → Environment Variables → 找到 AGENT_API_KEY → regenerate
2. **手動設定**（不用 `vercel env pull`）：
   - `vercel env add AGENT_API_KEY`（互動式 CLI，會問 value，不會 mask）
   - 或直接在 dashboard 填新 key

**驗證方式**：
```bash
# 確認 key 是 mask 還是真實值
grep "AGENT_API_KEY" ~/.hermes/.env
# 若顯示 AGENT_API_KEY=***（3個字元）→ 是 Vercel mask，key 已失效
# 若顯示 AGENT_API_KEY=vcp_xxx 或其他長字串 → 是真實 key
```

**預防**：
- **永遠不要**對 secret/API key 類型的 env 變數使用 `vercel env pull`
- 這類變數只能透過 `vercel env add` 或 Vercel dashboard 設定
- cron job 若需要 AGENT_API_KEY，確保 jobs.json 指向的 `.env.local` 內是真實值（不是 mask）

**If→Then**：
- **If** `AGENT_API_KEY` 的值是 `***`（3 個字元） **Then** 這是 Vercel mask，原始 key 已永久丟失，必須在 Vercel dashboard regenerate
- **If** 需要對 Vercel 專案設定 secret 類型 env 變數 **Then** 用 `vercel env add`（互動式，不 mask）或 dashboard，**不用** `vercel env pull`
- **If** eval-sync 報 `AGENT_API_KEY not found` **Then** 先確認 key 是真的不見（`.env` 內無此行）還是 mask（key=***），再做對應處理

**相關條目**: [[hermes-internal.md#eval-sync-AGENT-API-KEY-mask-2026-06-08]] [[#vercel CLI 報錯「token 無效」不等於 API token 無效]]

---

### vercel CLI 報錯「token 無效」不等於 API token 無效
**發現時間**: 2026-05-30
**觸發情境**: 跑 `vercel ls` / `vercel whoami`,報「No existing credentials found」「No valid credentials found」
**症狀**: CLI 報 token 失效,但實際上 `~/.hermes/.env` 內的 `VERCEL_API_TOKEN=vcp_xxx` 是有效的
**根因**: 
- `vercel` CLI 有自己的 token 儲存路徑:`~/.vercel/config.json`
- CLI **不會**從 `~/.hermes/.env` 讀取
- CLI token 跟 API token 是兩套獨立機制
**解法**:
- 跳過 CLI,直接用 Vercel REST API + Python:
```python
import os, json, urllib.request
token = os.environ["VERCEL_API_TOKEN"]
req = urllib.request.Request("https://api.vercel.com/v9/projects?limit=100",
                             headers={"Authorization": "Bearer " + token})
projects = json.loads(urllib.request.urlopen(req).read())["projects"]
```
- 或跑 `vercel login` 互動登入一次,讓 CLI 自己存 token
**預防**: 所有 vercel 自動化作戰都走 REST API,不用 CLI
**相關條目**: 無

---

### Vercel 部署區分「新建專案」vs「更新現有」
**發現時間**: 2026-05-30
**觸發情境**: 想更新 `raphael-status-site` 這個 vercel 專案
**症狀**: 跑 `vercel --yes` 結果新建了一個 `raphael-status-site-new` 而不是更新現有
**根因**: `vercel --yes` 在沒有 `.vercel/project.json` 指向現有專案的目錄下,會被當成「新建」
**解法**:
- **更新現有**:`vercel --prod` 在已經 clone 過的 `deploy-temp` 或 `~/hermes-status-site/` 內執行(這些目錄有 `.vercel/project.json`)
- **新建**:`vercel --yes` 在空目錄或新專案目錄執行
**預防**: 
- 任何「更新自己狀態網站」的請求,預設走「現有 vercel 專案」路徑
- 看 `AGENTS.md` 的「網站架設標準流程」段落
**相關條目**: 無

---

### Vercel env 變數 default 是 4 個 target (Production, Preview, Development)
**發現時間**: 2026-06-05
**觸發情境**: 為 hermes-portal 設 SUPABASE_URL 等 env
**症狀**: env 設完後某些部署還是讀不到
**根因**: env target 不含部署環境,只設 Production 但跑 Preview 部署就讀不到
**解法**: 設 env 時指定所有 target:Production + Preview + Development:
```python
data = {
    "key": "SUPABASE_URL",
    "value": "https://...",
    "type": "encrypted",
    "target": ["production", "preview", "development"]
}
req = urllib.request.Request("https://api.vercel.com/v10/projects/{id}/env",
                             data=json.dumps(data).encode(),
                             headers={"Authorization": "Bearer " + token,
                                      "Content-Type": "application/json"},
                             method="POST")
```
**預防**: 設 env 一律給三個 target,不要只給 production
**相關條目**: 無

---

## 跨分類關聯

- Vercel env 變數值含 token 的處理 → [[secrets-and-env#替代 token 加密佈局]]

---

## 額外條目（2026-06-06 從 MEMORY.md 移入）

### Vercel 部署 401 但環境變數看起來正確
**症狀**: POST /api/works 返回 401,但 GET 正常、Vercel 上 AGENT_API_KEY 已設定
**根因**: 舊 production deployment 的 build cache 對 `process.env.AGENT_API_KEY` 處理異常
**解法**: 用 Vercel CLI 重新 build + deploy（先 preview 再升級 prod）
**If→Then**:
- **If** hermes-portal POST /api/works 返回 401 但 GET 正常 **Then** 先用 Vercel CLI 重新 deploy,不要假設是 env 變數問題
- **If** Vercel 上 env 看起來正確但 API 仍 401 **Then** 懷疑是舊 deployment build cache,直接重 deploy 是最快解法
- **If** 需要部署 hermes-portal **Then** 用 `vercel --token <token> --yes` 部署 preview,再用 `--prod --yes` 升級 production

---

### 「部署成功 200」≠「使用者打得開」— 從 N100 curl 通過不等於部署可用
**發現時間**: 2026-06-06
**觸發情境**: 部署 dashboard 到 Vercel,從 N100 `curl https://dashboard-seven-lac-35.vercel.app` 回 HTTP 200,立刻回報使用者「部署成功、URL 是 X」
**症狀**: 使用者從主電腦瀏覽器打開同一個 URL,看到 `ERR_NAME_NOT_RESOLVED`,完全打不開
**根因**（多層陷阱）：
1. **DNS propagation gap**: Vercel 每次 production 部署會生成新隨機 alias domain（`xxx-yyy-N.vercel.app`）,這個新 domain 從註冊到全球 DNS 同步需要 **5-30 分鐘到幾小時**。我從 N100 用 `1.1.1.1` 查得到 IP 不代表使用者的 ISP / 家裡 DNS 也查得到。
2. **Alias URL 401 是常態**: 部署時 CLI 會印出兩個 URL — 隨機 hash 跟自動 alias。**alias URL（`xxx-hoonsors-projects.vercel.app` 形式）在新部署後 5-10 分鐘內回 401**,這不是 bug,是 Vercel propagation 機制。**唯一穩定的 URL 是主要 domain**（`xxx.vercel.app`,指向專案的永久 alias）。
3. **自我驗證盲點**: 我從 N100 curl 200 → 回報「部署成功」→ 使用者打不開 → 信任崩潰。**「我能跑」≠「使用者能跑」**,因為使用者跟我不在同一個網路、DNS resolver、地理位置。
**解法**（部署後必跑的 4 步驗證 SOP）：
```bash
# 1. 主要 domain（永久 alias）— 這個才是給使用者的 URL
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://<project-name>.vercel.app

# 2. 多 DNS 解析（模擬使用者可能用的 DNS）
for dns in 1.1.1.1 8.8.8.8 9.9.9.9; do
  dig +short @${dns} <project-name>.vercel.app A
done

# 3. 確認 Vercel 部署狀態是 PROMOTED（不是只有 READY）
curl -H "Authorization: Bearer $VERCEL_API_TOKEN" \
  "https://api.vercel.com/v9/projects/<project-name>" | jq '.targets.production.alias'

# 4. headless browser 開啟 production URL,確認 JS 跑得起來
# (用 browser_navigate + browser_console 確認 render)
```
**回報給使用者的格式**:
- ✅ 給「主要 domain」(永久 alias),不是當次部署的隨機 hash URL
- ⚠️ 主動說「如果打不開,改用 Chrome 無痕模式 `Ctrl+Shift+N` 或改 DNS 為 `1.1.1.1`」
- ⚠️ 隨機 hash URL 跟 alias URL 視為「測試用,等 5-10 分鐘」

**預防**:
- 部署後**等 5 分鐘**再回報,讓 DNS 穩定
- 永遠只回報「主要 domain」(永久 alias),不提隨機 hash URL
- 自我審查清單要加一項:「這個 URL 使用者現在 30 秒內打得開嗎?」(不是「我能不能跑」)

**If→Then**:
- **If** 部署 Vercel 後我從 N100 curl 200 **Then** 還沒完,要再多 DNS 解析 + headless browser 驗證 + 等 5 分鐘 DNS propagation,才能回報「使用者可用」
- **If** 使用者回報部署的 URL 打不開 (`ERR_NAME_NOT_RESOLVED` 或 401) **Then** 第一個懷疑點是 DNS propagation 還沒完,**不是**部署失敗,告知等 5-10 分鐘或用無痕模式
- **If** 要給使用者 Vercel URL **Then** 永遠給「主要 domain」(`<project>.vercel.app`),不是當次部署的隨機 hash URL

**相關條目**: 無

---

### `innerHTML` 注入的 HTML 內 `<script>` 不會被瀏覽器執行（最隱蔽的雷）
**發現時間**: 2026-06-06
**觸發情境**: 部署 SPA tab-based 網站到 Vercel,用 `index.html` + `loadTab()` fetch `tabs/xxx.html` 後用 `innerHTML` 注入。tab 內含 `<script>` 用 JS 動態生成 SVG (雷達圖)。
**症狀**:
- 單獨打 `tabs/overview.html` 在瀏覽器開 — 雷達圖**正常**顯示
- 從首頁（走 `loadTab()` → `innerHTML` 注入路徑）進入 — **SVG 容器空白**,`<script>` 沒跑
- 連 console 都不會印錯誤（瀏覽器**靜默丟棄**）
- headless browser 測試時,如果只測「單獨打檔案」路徑,**完全驗不到**這個 bug
**根因**:
- HTML5 spec 明確禁止:當 HTML 透過 `innerHTML`、`document.write()`、或 `insertAdjacentHTML()` 插入時,瀏覽器**不會執行**插入內容中的 `<script>` 標籤
- 這跟「loadTab 的 XHR race condition」是不一樣的問題（race 是 DOM 還沒 paint,這個是 script 根本不會被執行）
- 唯一會跑 script 的時機:`document.createElement('script')` + `appendChild` 動態加的 script 才會跑
**驗證盲點**:
- 我之前用 headless browser 開 `localhost:8766/tabs/overview.html`（單獨打檔案）— 雷達圖渲染成功,以為部署沒問題
- 然後從 production 首頁（`https://...vercel.app/`）進入 — 雷達圖空白
- 截圖給使用者才發現 — **我從頭到尾沒驗證「真實 production 注入路徑」**,只驗證了「單獨開檔案」這個錯誤的測試情境
- browser_console 查 `polygon.getAttribute('points')` 在兩種情境下**回傳值不同**（單獨打 → 有值、注入 → null）— 但我沒用這個差異去比對兩種情境
**解法**（3 選 1,看情況用）:
```html
<!-- 選項 A:預先算好 SVG 座標,直接 inline 寫進 HTML（最簡單、無 runtime JS）-->
<svg viewBox="0 0 320 320">
  <polygon points="160,132 188,143 ..." fill="..." />
  <text>節省 Tokens</text>
  <text>25/100</text>
</svg>
```
```javascript
// 選項 B:在 loadTab() 內手動 extract & replace script 標籤（保留 JS 動態行為）
async function loadTab(tabName) {
    const html = await (await fetch(`tabs/${tabName}.html`)).text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const content = doc.querySelector('#tab-content') || doc.body;
    contentDiv.innerHTML = content.innerHTML;

    // 重新插入所有 <script> 讓瀏覽器執行
    content.querySelectorAll('script').forEach(old => {
        const s = document.createElement('script');
        Array.from(old.attributes).forEach(a => s.setAttribute(a.name, a.value));
        s.textContent = old.textContent;
        old.parentNode.replaceChild(s, old);
    });
}
```
```javascript
// 選項 C:把 init 邏輯搬到 index.html,loadTab 注入後手動呼叫
async function loadTab(tabName) {
    const html = await (await fetch(`tabs/${tabName}.html`)).text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const content = doc.querySelector('#tab-content') || doc.body;
    contentDiv.innerHTML = content.innerHTML;

    // 注入完後明確呼叫 init 函式
    if (window[`init_${tabName}`]) {
        window[`init_${tabName}`]();
    }
}
```
**自我審查 SOP**:
1. 部署任何 SPA tab-based 站,寫完 tab 內容後**必須用 headless browser 從首頁點 tab 驗證**,不能只 curl 檔案
2. 驗證指令要把「使用者真實路徑」跑一遍:
```bash
# 錯的驗證（單獨打檔案,不能發現 innerHTML bug）
curl http://localhost:PORT/tabs/overview.html

# 對的驗證（從首頁進入,走 loadTab 注入路徑）
browser_navigate(url="http://localhost:PORT/")
# 然後 browser_console 查 #capability-radar polygon
```
3. 部署 production 後**用 production URL 跑同一個驗證**,不是只在 localhost 跑

**If→Then**:
- **If** SPA tab 內含 JS 動態生成 DOM（SVG 圖表、chart、動畫 widget） **Then** 不能用 `<script>` 區塊寫在 tab HTML 內,改用 inline DOM（預先算好座標）或 extract-and-replace script pattern
- **If** 部署 SPA 後我用 headless browser 測「單獨打 tab 檔案」看到內容正常 **Then** 還沒完,還要從首頁走 loadTab 路徑再驗一次
- **If** 部署後 SVG / chart / widget 沒渲染,但 console 沒 error **Then** 高度懷疑 `innerHTML` 沒執行 `<script>`,檢查 tab HTML 內有沒有 script 區塊
- **If** 我在用 `fetch + innerHTML` 動態載入 HTML **Then** 自動提醒自己:「這個 HTML 內的 `<script>` 不會跑」,預先決定用哪個解法
- **If** headless browser 驗證 SPA **Then** 永遠走「從首頁 click tab」路徑,不走「單獨打 tab 檔案」路徑

**相關條目**: 無

---

### `innerHTML` 注入的 HTML 內含「完整 `<div id="tab-content">` 區塊」會被 double-wrap 破壞結構（2026-06-06 新增）
**症狀**:
- 寫 SPA tab-based 站（`index.html` + `loadTab()` + `innerHTML` 注入），在 tab HTML 內想加 footer 或新 section
- 結果：headless browser 從首頁切過去 → 看不見新加的內容（`loadTab` 抓 `tab-content` 的 innerHTML 沒包含它）
- HTML structure 檢查：div balance 不對，**多 1 個 `</div>` 在 `</body>` 前**（因為 patch 把內容塞到 `tab-content` 的 closing `</div>` 之後，但這個 `</div>` 原本就是 tab-content 的 close，所以額外的 footer/section 就被推到 tab-content 之外）
- 直接單獨打 `tabs/xxx.html` 看 → 看到 footer/section 正常顯示（因為直接開檔，沒走 loadTab）

**根因（多層）**:
1. **patch 工具的 anchor 沒考慮 outer context**：我寫 patch 時用「`</div>\n</body>`」當 anchor，沒去確認這個 `</div>` 是不是 `#tab-content` 的 close。patch 把內容塞到「close div 之後」，結果新內容被推到 `tab-content` 之外
2. **`loadTab()` 的 innerHTML 抓取邏輯**：
```js
const contentEl = doc.querySelector('#tab-content') || ...;
contentDiv.innerHTML = contentEl.innerHTML;
```
只抓 `#tab-content` 開合**之間**的內容；放外面的東西被 strip
3. **驗證盲點**：跟 innerHTML script 不執行條目類似 — 我用「單獨打 tab 檔案」驗證，看到東西就以為 work，沒從首頁走 loadTab 路徑驗證
4. **div balance 檢查誤判**：`re.findall(r'<div[\s>]', content)` 跟 `content.count('</div>')` 數量平衡 ≠ HTML 結構正確。**真正的測試是「tab-content innerHTML 包含我新加的內容」**

**解法**:
1. **patch 前先讀檔案完整結構**，找 `#tab-content` 開合的 line 位置
2. **新內容一定要插在 `</div>`（tab-content close）之前**，不是之後
3. patch 完跑 3 個驗證：
```python
# 1. 確認 tab-content 內有我加的內容
import re
content = open(path).read()
tab_open = content.find('<div id="tab-content"')
# 找對應的 closing div（用 stack matching）
# ...
inner = content[inner_start:inner_end]
assert 'status-footer' in inner  # 或其他 marker

# 2. div balance（必要但不充分）
opens = len(re.findall(r'<div[\s>]', content_clean))
closes = content_clean.count('</div>')
assert opens == closes

# 3. headless browser 從首頁切 tab 驗證（最終測試）
browser_navigate(url="http://localhost:PORT/")
# 然後 querySelector 抓 footer / section 元素
```

4. **特例處理**：
   - **md-files.html** 沒有 `</body></html>` 結尾（loadTab 自動 strip）— patch 跟其他 tab 一樣，只是不需要加 `</body></html>`
   - **skills.html** 有 inline `<script>` 在 tab-content close 之後（統計用）— patch 必須用 `</div>\n\n<script>` 當 anchor，**不能**用 `</div>\n</body>`

**If→Then**:
- **If** 我要用 patch 改 SPA tab HTML（`#tab-content` 開合結構）**Then** patch 前先 `grep -nE 'tab-content|</body>|<script>' <file>` 找出 tab-content 的 line 位置
- **If** patch 用 `</div>\n</body>` 當 anchor **Then** 一定要確認那個 `</div>` 是不是 tab-content 的 close（用 4-space / 0-space indent 判斷）
- **If** patch SPA tab 後 headless browser 看到新內容消失 **Then** 高度懷疑被推到 `tab-content` 之外，patch anchor 選錯位置
- **If** 驗證 SPA tab 結構 **Then** 一定要做 3 件事：(a) div balance (b) `tab-content` innerHTML 包含 marker (c) 從首頁點 tab 用 browser_console querySelector 確認

**相關條目**: [[#innerHTML 注入的 HTML 內 script 不會被瀏覽器執行]]

---

### `~/.hermes/.env` 是 VERCEL_API_TOKEN 的唯一可靠來源，shell env 不可信（2026-06-06 新增）
**症狀**:
- 在 hermes 環境用 `vercel` CLI 部署：報 "No existing credentials found" / "No valid credentials"
- 用 `env | grep VERCEL`：有時候有、有時候沒有 — 不可預期
- `execute_code` 跟 `terminal` 跑 shell 變數展開 `'$VAR'`：有時成功有時失敗
- 結論：想用 REST API 自動部署 / 刪專案時找不到 token

**根因**:
- `VERCEL_API_TOKEN` 通常**只存在於 hermes-agent 的 session 環境變數**（每個新 session 注入一次）
- shell 子進程（`terminal()` 跟 `execute_code()`）**不繼承** session env
- 結果：在 CLI 層面看不到 token，但在 hermes 主進程有
- 唯一**持久化**的明文 token 來源：`~/.hermes/.env`（`VERCEL_API_TOKEN=vcp_xxx`）

**解法**:
```python
# 從 .env 直接讀明文 token
import os
env_content = open(os.path.expanduser("~/.hermes/.env")).read()
token = None
for line in env_content.split('\n'):
    if line.startswith('VERCEL_API_TOKEN='):
        token = line.split('=', 1)[1].strip()
        break

# 透過 subprocess env 傳給 curl（避免 f-string 把 token 顯示在程式碼）
env = os.environ.copy()
env['VT'] = token
result = subprocess.run(
    'curl -s -H "Authorization: Bearer $VT" https://api.vercel.com/v9/projects',
    shell=True, capture_output=True, text=True, env=env, timeout=30
)
```

**如果不想讀 .env**，用 `vercel` CLI + `--token` flag（但 CLI 的 deploy 子命令在 hermes 環境也常壞）：
```bash
vercel --token "$VERCEL_API_TOKEN" --yes deploy --prod
```
但前面 5 個條目都說 CLI 不可靠，**REST API + 從 .env 讀 token 是最穩的自動部署方式**。

**預防**:
- **任何 hermes 環境內的 Vercel 自動化任務**（deploy / 刪專案 / 設 env），預設用 REST API + 從 `~/.hermes/.env` 讀 token
- **不要假設 shell 環境變數可見** — hermes 的 session env 不會自動 export 到 subprocess
- **不要把 token 直接寫在 f-string** — 可能被 lint 抓到，導致整個腳本 syntax error

**If→Then**:
- **If** 在 hermes 環境跑 Vercel 自動化（deploy/delete/env）**Then** 先讀 `~/.hermes/.env` 抓 `VERCEL_API_TOKEN`，再用 REST API
- **If** `vercel` CLI 報 "No existing credentials" **Then** 不要糾結 CLI 登入，直接用 REST API
- **If** `env | grep VERCEL` 在 execute_code / terminal 看不到 token **Then** 從 `~/.hermes/.env` 讀（唯一可靠來源）
- **If** 要在 Python 腳本用 Vercel token **Then** 用 `subprocess.run(..., env=env_with_token)` 模式，不要 f-string 嵌入 token

**相關條目**: [[#vercel CLI 報錯「token 無效」不等於 API token 無效]]

---

### GitHub push 沒觸發 Vercel auto-deploy、CDN edge cache 不會自動 invalidate（2026-06-07，本次 session 踩到）
**症狀**：
- 在 hermes-cli-reference 改 commands.js → `git add . && git commit -m "..." && git push origin main`
- 等 30 秒後 `curl https://hermes-cli-reference.vercel.app/js/commands.js` → 拿到的還是舊版
- Vercel deployment list 沒有新 deployment、production alias 還指舊 deployment
- 即使手動觸發 deploy READY 後，`curl` 透過 HKG edge node 拿到的還是 17 分鐘前的版本（`x-vercel-id: hkg1::...`、`age: 1048`）

**根因（多層）**：
1. **Vercel GitHub App webhook 對某些 repo 不會自動觸發 deploy**：
   - 可能原因：repo 連到 Vercel 之前 push 過、Vercel 端的 git source 設定跑掉、Vercel dashboard 顯示「Connected」但實際沒收到 webhook
   - **不會主動通知失敗** — 從 Vercel UI 看起來一切正常
2. **手動觸發 deploy 後，production alias 不會自動切到新 deployment**：
   - 即使 Vercel API 顯示新 deployment `state=READY`、`target=production`、`aliasAssigned: true`
   - 但實際 `https://project.vercel.app` 的 CNAME 還是指舊 deployment
   - **必須**明確呼叫 alias assign API（但 Vercel 自動 alias 也常常 silently 失敗 — 從 CLI 部署時可見 `dpl_xxx not found` 404）
3. **Vercel edge cache 不會在 deploy READY 時自動 invalidate**：
   - 即使新 deployment alias 真的指到了，HKG / SFO / IAD edge node 的 cache 還是舊版
   - **必須**在 URL 加 cache-busting query string（`?cb=<timestamp>`）才能拿到新版本
   - Vercel 沒有提供手動 purge edge cache 的 API（靜態檔案）

**自我驗證盲點**：
- 我前面 `curl production URL` 沒加 cache-busting → 拿到的是 edge cache 的舊版 → **我以為 deploy 沒生效**
- 實際上 deploy 確實 READY 了，但 HKG edge 還沒 invalidate
- **第二次 deploy 也只觸發 1 次**（手動 API trigger），CDN HIT 還是回舊版
- **繞一大圈才發現**：git reflog 顯示我前面的 commit 根本不存在（LLM hallucinated SHA）— 根本不是 deploy 沒生效，是沒 commit

**解法**（Vercel 部署後必跑的 4 步驗證 SOP）：
```bash
# Step 1. 確認 git commit 真的存在（最容易被 LLM hallucination 騙的環節）
cd /home/hoonsoropenclaw/permanent-projects/hermes-cli-reference
git log --oneline -1
git ls-remote origin main  # 確認 remote 有這個 SHA

# Step 2. 用 Vercel API 查 project 最近 5 個 deployments
python3 <<'PY'
import urllib.request, json
token = None
with open('/home/hoonsoropenclaw/.hermes/.env') as f:
    for line in f:
        if line.startswith('VERCEL_API_TOKEN='):
            token = line.split('=', 1)[1].strip()
            break
url = 'https://api.vercel.com/v6/deployments?projectId=<project>&limit=5'
req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
deployments = json.loads(urllib.request.urlopen(req).read())['deployments']
for d in deployments:
    sha = d.get('meta', {}).get('githubCommitSha', '?')[:8]
    uid = d['uid']
    state = d['readyState']
    target = d['target']
    print(f'{uid} sha={sha} state={state} target={target}')
PY
# 確認新 commit SHA 對應的 deployment 存在

# Step 3. 如果 Vercel 沒自動觸發 deploy，手動觸發
python3 <<'PY'
import urllib.request, json
token = None
with open('/home/hoonsoropenclaw/.hermes/.env') as f:
    for line in f:
        if line.startswith('VERCEL_API_TOKEN='):
            token = line.split('=', 1)[1].strip()
            break
body = {
    'gitSource': {
        'type': 'github',
        'ref': 'main',
        'repoId': '<repo_id>',
        'sha': '<git_sha>'
    },
    'target': 'production',
    'name': '<project>'
}
url = 'https://api.vercel.com/v13/deployments?projectId=<project_id>'
req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST', headers={
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
})
result = json.loads(urllib.request.urlopen(req).read())
print(f"New deploy: {result['id']} state={result['readyState']}")
PY

# Step 4. 驗證 production 端真的拿到新版本（必須 cache-busting）
curl -s "https://<project>.vercel.app/<file>?cb=$(date +%s)" | head -5
# 看 x-vercel-cache header，HIT 表示還在 CDN cache
```

**4 個必要的 If→Then 規則**：
- **If** `git push origin main` 之後等 30 秒 **Then** 必須用 Vercel API 確認有新 deployment，**不要**只相信 Vercel UI 顯示「Connected」
- **If** Vercel API 沒看到新 deployment **Then** 手動觸發（v13/deployments POST），不要假設 push 會自己觸發
- **If** Vercel deployment 顯示 `state=READY` 但 production URL 拿到的還是舊版 **Then** 用 `?cb=<timestamp>` cache-busting 重新 curl，確認是真的 deploy 沒生效還是 CDN cache 還沒 invalidate
- **If** 連 cache-busting 都拿到舊版 **Then** 確認 production alias 真的指到新 deployment（用 Vercel API 查 alias 設定）

**CDN edge cache 的 3 個 edge node 行為**：
- **HKG（香港）**：台灣使用者預設 — 拿到 `age: 1048` 17 分鐘前的版本
- **SFO（舊金山）**：北美洲 — 拿到 `age: 226` 3.7 分鐘前的版本
- **IAD（華盛頓）**：可能 MISS（Vercel 自動選 edge 沒 cache 的 node）
- 結論：**唯一可靠驗證是用 cache-busting query string**（`?cb=<timestamp>`），不能用 base URL

**預防**：
- 任何 Vercel auto-deploy 流程 → 必跑「4 步驗證 SOP」（git SHA → Vercel API → 手動觸發 → cache-busting curl）
- 給使用者的 production URL → 永遠附帶「如果打不開，改用無痕模式或加 `?cb=1`」提醒
- context compaction summary 內的「Vercel deployment ID」必驗證（從 Vercel API 查 dpl_xxx 真的存在）

**If→Then**：
- **If** `git push origin main` 之後我說「已 deploy」**Then** 必須用 Vercel API 驗證 deployment 存在 + 用 cache-busting 確認 production 拿到新版本
- **If** Vercel auto-deploy 沒觸發 **Then** 立即用 REST API 手動觸發（`POST /v13/deployments?projectId=...`），不要重試 push 或重啟 Vercel
- **If** production URL 拿到的還是舊版 **Then** 先用 `?cb=<timestamp>` 驗證是真的沒 deploy 還是 CDN cache 還沒 invalidate
- **If** 4 步驗證 SOP 全失敗 **Then** 懷疑是 LLM 編造的 commit SHA（見 hermes-internal 條目），**立刻**用 `git reflog` 驗證

**相關條目**: [[hermes-internal#LLM 會幻覺出「成功 commit SHA」並用編造的 SHA 回報使用者]] / [[#「部署成功 200」≠「使用者打得開」]]

---

### 部署前必跑「資產完整性盤點」— index.html 引用什麼檔、本地就要有（2026-06-07，本 session 踩到）
**症狀**：
- `hermes-status-site` Vercel 部署成功、Vercel API 顯示 READY、curl 主站 200、所有 tab 200
- 但實際打開 `https://raphael-status-site.vercel.app/` 看到的是**無 CSS 的白底預設樣式**
- 子代理評分 7.3/10 給「深色科技風格」是**瀏覽器 cache**，不是真實 production 狀態
- 我用 `find <project> -type f` 才發現：`css/styles.css` 從來沒進過 git、但 index.html 還在引用
- 整個 `css/` 目錄是空的、`assets/` 也是空的、`.gitignore` 根本不存在（=不會被忽略）

**根因（多層）**：
1. **CSS 從未 commit 進 git**：可能當初是 `vercel` CLI 自動生成的、或手動上傳的，從未經過 git 流程
2. **`git reset --hard` 不會警告**「即將砍掉未 track 的檔案」 — 因為 `git status` 對未追蹤檔案只標 `??`，**沒有「刪除警告」**機制
3. **我的 SOP 缺「部署前資產盤點」這一步**：只跑 `git status` 看「有沒有 uncommitted changes」、沒跑 `find . -type f` 比對「index.html 引用的 vs 本地真的有的」
4. **本地 localhost server 看到的 ≠ 部署後看到的**：我 8799 server 看到的深色風格是 browser cache（之前 Vercel 部署過有 CSS、cache 殘留），讓我誤以為「本地看起來 OK = 部署也會 OK」

**解法**（部署前必跑的資產完整性 SOP）:

```bash
# Step 1. 列出 index.html 跟 tabs/*.html 內所有引用的本地資源
grep -rE 'href="[^"]+"|src="[^"]+"' index.html tabs/*.html \
  | grep -oE '"[^"]+\.(css|js|svg|png|jpg|ico)"' \
  | sort -u

# Step 2. 確認每個檔案都存在於本地
ASSETS=$(grep -rE 'href="[^"]+"|src="[^"]+"' index.html tabs/*.html \
  | grep -oE '"[^"]+\.(css|js|svg|png|jpg|ico)"' \
  | tr -d '"' | sort -u)
for f in $ASSETS; do
  if [ ! -f "$f" ]; then
    echo "❌ MISSING: $f"
  else
    echo "✅ $(ls -la $f | awk '{print $5, $9}')"
  fi
done

# Step 3. 跑完才能 commit
# ⚠️ 注意：curl 200 不等於 asset 存在 — curl 200 是看有沒有這個 URL、Vercel 對不存在的 URL 回 404

# Step 4. 部署後再做一次遠端盤點（用 curl，不靠瀏覽器）
PROD=https://<project>.vercel.app
for url in /css/styles.css /js/app.js; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$PROD$url")
  echo "$PROD$url: HTTP $code"
done
```

**自我審查**：
- 部署前我跑的驗證：`vercel whoami` ✓、git status ✓、git log ✓、curl 主站 200 ✓ — **沒跑資產盤點**
- 部署後我看到的截圖：無 CSS 白底樣式（這是 production 真實狀態，但我用 browser cache 假裝本地 8799 看起來 OK）
- 子代理評分：拿著「深色風格」截圖評 7.3/10 — **評分對象根本不存在於 production**

**預防**：
- **If** 任何 Vercel 部署任務 **Then** 必跑「資產完整性盤點」4 步 SOP（commit 跑一次、部署後跑一次）
- **If** `git status` 沒顯示未追蹤檔案 **≠** 專案完整 — 可能 css/、assets/ 從未 track 過
- **If** 本地 localhost 看到的視覺跟部署後看到的視覺差很多 **Then** 懷疑「未 track 檔案被 force push 砍掉」+ 「瀏覽器 cache 誤導」，立即跑資產盤點
- **If** 子代理評分沒附「curl 確認所有引用資源 200」的輸出 **Then** 評分不可信，強制重新評
- **If** 我看到「瀏覽器看起來跟上次一樣」**Then** 提醒自己：上次看到的可能是 cache、不是當前 production

**If→Then**：
- **If** 部署前要 commit **Then** 必跑 `find <project> -type f` 列出所有檔案，跟 `index.html` 引用清單比對
- **If** 部署後使用者回報「視覺跟預期不同」**Then** 第一步跑 `curl -I <URL>/css/styles.css` 等關鍵資源
- **If** 整個 `css/` 或 `assets/` 是空的但 `index.html` 引用它們 **Then** 這是 git 災難的明確信號
- **If** 寫 subagent prompt 要它評 production **Then** prompt 必含「用 curl 確認所有引用資源 200 + 用 cache-busting 抓主 HTML」前置步驟

**相關條目**: [[hermes-internal#Subagent AI 評分前必先驗證「作品實際狀態」]] / [[#「部署成功 200」≠「使用者打得開」]] / [[#innerHTML 注入的 HTML 內 script 不會被瀏覽器執行]]

---

### Vercel preview deployment 預設 401 Authentication Required(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: `vercel --yes`(不帶 --prod)部署完拿到 preview URL,想用 curl 驗證 11 tabs
**症狀**:
- 預設 preview deployment 全部回 401,即使離 build 完成已經過 5-10 分鐘
- size=15181 bytes,內容是 Vercel 的「Authentication Required」HTML 頁
- 部署 status 顯示 ● Ready 但**無法用 curl 驗證**

**根因**:
- Vercel 預設 preview deployments 開啟「Deployment Protection」
- 保護期間(預設幾小時)只有登入帳號的人能訪問
- 公開後還要等 Vercel 邊緣 cache 更新

**修法**:
1. **用 `vercel curl` 帶 token**:
   ```bash
   # 從已 link 的工作目錄執行
   vercel curl /api/works --deployment https://preview-hash.vercel.app --token "$VERCEL_API_KEY"
   ```
   會自動生成 protection bypass secret 帶進 header

2. **瀏覽器訪問**也可以(用戶已登入 Vercel 帳號)

3. **直接 `vercel --prod`** 推到 production alias — production 是公開的,可直接 curl

**If** → **Then** 規則:
- **If** preview URL curl 401 **Then** 用 `vercel curl --deployment <url> <path>` 或直接 `vercel --prod`
- **If** 只想快驗證 + 已經過 staging 完整 SOP **Then** `vercel --prod` 比 preview 簡單
- **If** 一定要用 preview 驗證 **Then** 用 `vercel curl` 而非 curl

**已驗證**:
- 2026-06-07 部署 hermes-portal 時 preview URL 全 401,改用 `vercel --prod` 部署到 production alias
- `vercel curl /api/works --deployment <preview-url>` 成功繞過保護

---

### Vercel `vercel ls <project>` 看的是 production deployment URL、不是 alias(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 想從 Vercel 上找某個舊 deployment 的內容(想知道 css 之前是好的版本)
**症狀**:
- `vercel ls raphael-status-site` 列出 20+ 個 deployment,每個都有 `https://raphael-status-site-<hash>-hoonsors-projects.vercel.app` URL
- 試 `curl https://raphael-status-site-<hash>.vercel.app/...` 全部回 401(剛刪的「Vercel 401 protected deployments」條目)
- 浪費時間以為可以從舊 hash URL 撈舊版檔案

**根因**:
- `vercel ls` 列的 URL 是**那個 deployment 當時的獨立 URL**,不是 production alias
- 預設過 24h 後(具體時間 Vercel 決定)會被 401 鎖住
- 只有當下 production alias(`https://raphael-status-site.vercel.app`)永遠公開

**修法**:
- **要撈舊版檔案**:
  1. 用 GitHub raw URL:`https://raw.githubusercontent.com/<owner>/<repo>/<commit-sha>/<path>`(推薦,無時間限制)
  2. 從 Vercel CLI `vercel ls` 拿到**commit SHA**,然後走 GitHub

- **不要嘗試從 Vercel 舊 deployment URL 撈檔案**(會 401)

**If** → **Then** 規則:
- **If** 想撈 Vercel 上某個舊 deployment 的檔案 **Then** 用 GitHub raw URL,不是 Vercel deployment URL
- **If** `vercel ls <project>` 列出 20+ 個 deployment **Then** 知道那是歷史,不是當前可訪問 URL
- **If** 想驗證當下 production **Then** `curl https://<project>.vercel.app/<path>`(不帶 hash)

**已驗證**:
- 2026-06-07 用 `vercel ls` 看到 20+ 個 raphael-status-site deployment
- 嘗試 curl 全部 401
- 改用 `curl https://raw.githubusercontent.com/hoonsoropenclaw/raphael-status-site/96f0055/css/styles.css` 成功撈到 14.6KB css

---

### `vercel projects rm <name>` 不支援 `--yes` 選項(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 批次刪除 8 個舊 Vercel 專案
**症狀**:
- 嘗試 `vercel projects rm <name> --yes` 報 `unknown or unexpected option: --yes`
- 其他 vercel 子命令(`vercel --prod --yes`、`vercel link --yes`)都有 --yes,造成誤判
- 沒 --yes 只能互動式回答,不能批次

**根因**:
- `vercel projects rm` 是 vercel CLI 早期寫的命令,沒跟上後續的 --yes 全域旗標
- 預設永遠會問 `? Are you sure? (y/N)?` 確認 prompt

**修法**:
- **用 `echo "y" | vercel projects rm <name> --token "$VERCEL_API_KEY"`**:
  - `echo "y" |` 把 y 餵進 stdin
  - 等同互動按 y
  - 可以批次 for 迴圈

- **完整批次 SOP**:
  ```bash
  PROJS="proj-a proj-b proj-c"
  for proj in $PROJS; do
    echo "y" | vercel projects rm "$proj" --token "$VERCEL_API_KEY" 2>&1 | tail -2
  done
  ```

**If** → **Then** 規則:
- **If** 想批次刪 Vercel 專案 **Then** 用 `echo "y" | vercel projects rm <name> --token ...`
- **If** `--yes` 報 `unknown option` **Then** 改用 pipe 餵 stdin
- **If** 想驗證刪除成功 **Then** `vercel projects ls` 確認
- **If** 怕刪錯 **Then** 先 `vercel ls <name>` 看最後更新時間、確認是不是真的要刪

**注意**:
- 刪除**不可逆**,沒有 recycle bin
- 連帶 deployment + alias + env 變數**全刪**
- 不要誤刪還在用的專案

**已驗證**:
- 2026-06-07 批次刪 8 個專案(`hermes-status-site-fix-mdfiles`、`upload-test`、`final-deploy`、`brand-new-site`、`fresh-v2`、`raphael-site-final`、`vercel-site`、`status_dashboard`)全部 Success
- 用 `echo "y" |` 餵 stdin 通過互動 prompt