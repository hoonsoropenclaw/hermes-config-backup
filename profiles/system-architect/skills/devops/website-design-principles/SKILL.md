---
name: website-design-principles
description: 網站建構 SOP — 多目錄多檔案分工，反對單一巨大 index.html
triggers:
  - build website
  - create web project
  - redesign web app
  - refactor web structure
---

# 網站建構 SOP

## 核心原則：多目錄多檔案分工

### 正確的目錄結構
```
project/
├── index.html              # 乾淨的 shell，只做路由和布局
├── css/
│   ├── base.css            # 重置、變數、通用樣式
│   └── components/         # 按功能拆分的 component CSS
├── js/
│   ├── app.js              # SPA 路由、tab 切換
│   └── tabs/               # 每個 tab 的邏輯各自獨立
│       ├── dashboard.js
│       ├── skills.js
│       └── memory.js
├── tabs/                   # HTML 片段（可被 JS 動態載入）
│   ├── dashboard.html
│   ├── skills.html
│   └── memory.html
└── assets/
```

### 禁止的結構
- ❌ 單一 `index.html` 內嵌所有 tab 內容（hermes-status-site 的教訓）
- ❌ 所有 JS/CSS 全部寫在一個檔案
- ❌ 用「倒數第 N 個」heuristic 找 HTML 插入點
- ❌ 部署-驗證迴圈太長（超過 5 分鐘就要優化）

### 每個檔案不超過 300 行，超過就拆

---

## 相關資料
- `references/sync-md-files.md` — sync_md_files.py 腳本規格、Cron Job 設定、md-files.html UI 設計

### 為什麼這種架構能成功
1. `index.html` 只有 89 行，是純 shell（不含任何 tab 內容）
2. 每個 tab 是獨立的 `.html` 檔案，放在 `tabs/` 目錄
3. `index.html` 的 `loadTab(tabName)` 用 `fetch('tabs/' + tabName + '.html')` 動態載入
4. 載入後自動剝離 `DOCTYPE` / `<html>` / `<head>` / `<body>` 包裝層，只取 `#tab-content` 內的內容

### 具體範例（hermes-status-site 重構結果）
```
hermes-status-site/
├── index.html          89行  ← 乾淨 shell
├── css/styles.css      298行
├── js/app.js           23行
└── tabs/
    ├── overview.html   108行
    ├── skills.html      227行
    └── ...（11個 tab）
```

### 備份指令（重構前必做）
```bash
cp -r hermes-status-site hermes-status-site.bak.$(date +%Y%m%d%H%M%S)
```

### Tab 命名對照表（容易搞錯）
| `data-tab` 屬性 | 實際檔名 |
|----------------|---------|
| `mdfiles` | `tabs/md-files.html` |
| `sysinfo` | `tabs/system-info.html` |
| （其他） | `tabs/{data-tab}.html` |

### ❗ SPA 分離時的命名陷阱（今天學到的教訓）
當 `index.html` 的按鈕 `data-tab` 屬性和實際檔名不一致時，fetch 會 404。
**修復方式**：在 `loadTab()` 的 fetch 路徑加 mapping：
```javascript
const filename = tabName === 'mdfiles' ? 'md-files'
    : tabName === 'sysinfo' ? 'system-info'
    : tabName;
fetch(`tabs/${filename}.html`)
```

### ❗ 樣式一致性原則
- 改區塊時優先用現有的 CSS class 系統（`.card`、`.tag tag-green`、`.grid`）
- **不要**自訂 `.skill-domain` / `.skill-tag-learned` 這類一次性樣式
- 否則和網站其他部分風格脫節，而且要寫很多重複的 CSS
- 今天技能領域分類本來用自訂樣式，現在改成 `.card` + `.tag` 就和其餘區塊一致了

### ❗ 重構時順手刪除廢棄 CSS
每次改完一個區塊的 HTML/樣式，順便搜尋「原本那些 class 還有人在用嗎？」
沒用的就砍掉，避免累積技術債。

---

## 錯誤的插入點策略（教訓）

### ❌ 失敗的 heuristic
「往上倒數 N 個 `</div>`」——這是地獄級錯誤：
- 當 HTML 結構稍微改變（多一個 div、少一個 div），N 就對不上
- `<!-- Tab: Soul -->` anchor 和 tab-skills 的關閉 `</div>` 中間差了 1500 行
- 用倒數計數找到的位置，會插入到 `tab-content` **關閉之後**，導致 stats 在所有 tab 都可見

### ✅ 正確策略
1. Tab HTML 是獨立檔案時：在 `<!-- SKILL_STATS_MARKER -->` 之前插入
2. Tab HTML 在同一檔案時：找 `<!-- Tab: NAME -->` 下一行的 `depth=1` 位置
3. 每次插入前用 Python 追蹤 depth，確認在正確的父元素內

### 用 Python 驗證插入點（depth 追蹤）
```python
lines = open('tabs/skills.html').readlines()
depth = 0
for i, line in enumerate(lines, 1):
    depth += line.count('<div') - line.count('</div')
    # marker 或插入點必須在 depth=1 或更深的子元素中
    if 'SKILL_STATS_MARKER' in line and depth < 2:
        print(f'ERROR: marker at depth {depth} (line {i}) — likely outside tab-content')
```

---

## 部署前驗證清單

1. **本地測試**：`python3 -m http.server 8080`（background 模式）確認功能正常
2. **每個 tab 單獨檢查**：在瀏覽器手動點每個 tab 按鈕，確認內容正確載入
3. **確認 committed 並 pushed**：不在未驗證的 local commit 上部署
4. **驗證插入點**：用 Python depth 追蹤確認插入位置在正確的 DOM 節點內

---

## SPA Tab 路由常見錯誤（重要！）

### ❌ tab 名稱與檔名不一致時的 404 陷阱
常見問題：按鈕 `data-tab="sysinfo"` 但 fetch 的是 `tabs/sysinfo.html`，但實際檔名是 `tabs/system-info.html`。

**症狀**：某些 tab 載入失敗，console 顯示 `Failed to load: sysinfo`

**原因**：`loadTab()` 直接把 tabName 拼成 fetch URL，但 tabName（來自 `data-tab`）未必等於檔名。

**正確做法**：在 fetch 前做 name mapping。
```javascript
async function loadTab(tabName) {
    // Map data-tab values to actual filenames
    const filenameMap = {
        'mdfiles': 'md-files',    // hyphenated filename
        'sysinfo': 'system-info'  // verbose filename
    };
    const filename = filenameMap[tabName] || tabName;
    const response = await fetch(`tabs/${filename}.html`);
    // ... rest of logic
}
```

---

## Vercel 部署調試（重要！）

### 常見問題：環境變數沒進去導致 FUNCTION_INVOCATION_FAILED

**症狀**：`curl` 訪問 API 端點返回 `FUNCTION_INVOCATION_FAILED`，但 local 測試正常。

**診斷方法**：先部署一個 `api/test.js` 快速確認環境變數狀態：
```javascript
module.exports = async (req, res) => {
  return res.status(200).json({
    env: {
      VAR_NAME: !!process.env.VAR_NAME,  // !! 確認是否存在
    }
  })
}
```
部署後 `curl https://<url>/api/test` 檢查每個變數。

**原因 1：Vercel Dashboard 設定後沒有 Redeploy**
在 Dashboard 新增/修改環境變數後，**必須 Redeploy** 才能生效。Settings → Environment Variables → 設定完成後，去 Deployments 頁面重新部署。

**原因 2：Sensitive 類型的環境變數需要 Redeploy**
就算是已經存在的 redeploy，如果修改了 sensitive 變數，也要再 Redeploy 一次。

**原因 3：`.vercel/project.json` 的專案 ID 用舊的**
新 token 可能因為 scope 不同，只能部署到同一個 orgId 的專案。確認 `.vercel/project.json` 的 `orgId` 和新 token 的 org 對應。

### Vercel Authentication Protection 阻擋

**症狀**：訪問網站或 API 跳轉到 Vercel 登入頁 `Authentication Required`。

**解決**：在 Dashboard 關閉 Authentication：
Settings → Protection → Authentication → 選擇 **Public**（或加入 Trusted Users）。

### Vercel CLI Token 失效

**症狀**：`vercel --token <token>` 回 `The token provided via --token argument is not valid`。

**解決**：在 https://vercel.com/account/tokens 建立新 token（新格式 `vcp_` 開頭），更新腳本中的 token。

### ✅ 部署後必測清單
1. `curl https://<url>/api/test` — 確認環境變數都進去了
2. `curl https://<url>/api/works` — 確認 API 正常運作（不是登入頁）
3. 用瀏覽器打開網站首頁 — 確認不是 Vercel 登入頁

**驗證**：部署前在本地 Server 測試每一個 tab，尤其是名稱帶 hyphen 或與 `data-tab` 值不同時。

### hermes-portal POST /api/works 持續 401 但 GET 正常（2026-06-04）

**症狀**：
- `GET /api/works` → 200（正常）
- `POST /api/works` → 401 Unauthorized
- Vercel Dashboard 上環境變數 `AGENT_API_KEY` 值已與本地 `.env.local` 完全一致（都是 `0770415`，長度 7）
- Deployment 狀態是 Ready
- Redeploy 完成後問題依舊

**根本原因**：
舊的 production deployment 的 build 對 `process.env.AGENT_API_KEY` 的 runtime 處理異常。環境變數在 Dashboard 看起來正確，但在該 deployment 的 runtime 中可能未正確載入（可能是空字串、null 或編碼問題）。Redeploy 不夠——需要完整重建部署。

**解決方式**：
1. 建立 debug endpoint 直接觀察 runtime 環境變數：
```javascript
// api/debug.js
module.exports = async (req, res) => {
  const key = req.headers['x-agent-key']
  return res.status(200).json({
    received_key: key,
    env_key: process.env.AGENT_API_KEY,
    comparison_result: key === process.env.AGENT_API_KEY,
  })
}
```
2. 部署 debug endpoint，測試後確認是否 key 比對成功
3. 若比對成功（`comparison_result: true`）但舊 endpoint 仍 401 → 確認是舊 deployment 的 runtime 問題
4. 用 `vercel --prod` 完整重建部署（而非只 Redeploy）：
```bash
vercel --token <token> --yes              # 先 preview
vercel --token <token> --prod --yes       # 再 production
```
5. 確認成功後刪除 debug.js，再部署一次乾淨的 production

**If→Then 規則**：
- **If** hermes-portal 的 POST /api/works 返回 401，但 GET 正常，且 Dashboard 環境變數看起來正確
- **Then** 懷疑是舊 deployment 的 runtime 環境變數注入問題（並非程式碼邏輯錯誤）
- **Then** 建立 debug endpoint 部署到相同專案，直接觀察 runtime 的 `process.env.AGENT_API_KEY` 值
- **Then** 若 debug 顯示 `comparison_result: true`（key 比對成功），確認是舊 deployment 的 runtime 狀態异常
- **Then** 用 `vercel --prod` 完整重建部署，不要只靠 Dashboard Redeploy
- **Then** 清理：確認成功後立即刪除 debug.js 並重新部署

**部署相關資料**：
- Vercel CLI token: `vcp_***REDACTED***`
- 本機路徑: `/home/hoonsoropenclaw/hermes-portal/`
- 專案名: `hoonsors-projects/hermes-portal`
- Production URL: `https://hermes-portal.vercel.app`
- API endpoint: `POST /api/works`，Header: `x-agent-key: <AGENT_API_KEY>`

### Vercel CLI Token 失效

**症狀**：`vercel --token <token>` 回 `The token provided via --token argument is not valid`。

**解決**：嘗試備用 token（從歷史对话中找到的：`vcp_***REDACTED***`），若都失敗則在 https://vercel.com/account/tokens 建立新 token（新格式 `vcp_` 開頭）。

### ✅ 技能領域分類的 styling 正確做法
不要自己發明 `.skill-domain` / `.skill-tag learned/explored/pending` 等 custom CSS。用系統既有的：
- `.card` 作為容器
- `.tag tag-green` / `tag-yellow` / `tag-orange` 作為狀態 tag（綠=已學、黃=探索中、橙=待開始）
- `.grid` + `grid-template-columns: repeat(auto-fill, minmax(340px, 1fr))` 做響應式多欄佈局

這樣技能領域分類和其他區塊（系統總覽、記憶系統等）視覺上完全一致。

---

## Skill Usage Stats 排程腳本設計

### v3 實際做法（最終版本）
舊版用「倒數第 N 個 `</div>`」heuristic 找插入點，導致 stats 插入到 tab-content 關閉之後。
**v3 的安全策略**：不插入整個 section，只替換 `<tbody>` 的內容。
1. 統計生成 → 寫入 `~/.hermes/skills/skill_stats.json`
2. 讀取 stats JSON → 生成新的 `<tr>` rows
3. 用正則 `(<tbody>)\s*\n(.*?)\s*(</tbody>)` 找到舊 tbody，整個替換
4. commit + push + `vercel --prod --token $VERCEL_API_TOKEN`

### 為什麼只替換 tbody 最安全
- 不需要計算 div 深度
- 不依賴行號或 heuristic
- 不用管 HTML 結構怎麼變
- idempotent：只改 rows，不動周圍的 HTML

### 排程 cron
- 每日午夜：`0 0 * * *`
- Job ID：`skill-usage-daily-v3`
- 觸發：`python3 ~/.hermes/scripts/skill_usage_stats.py && git add && commit && push && vercel`

### 驗證 HTML 結構的 Python 指令
```python
lines = open('tabs/skills.html').readlines()
depth = 0
for i, line in enumerate(lines, 1):
    depth += line.count('<div') - line.count('</div')
    if '<!-- SKILL_STATS_MARKER -->' in line and depth < 2:
        print(f'ERROR: marker at depth {depth} (line {i})')
```