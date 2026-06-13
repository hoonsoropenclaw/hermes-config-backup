# Deployment History — 2026-06-06 Session

> 三次 Vercel 部署的具體 trace 與踩雷紀錄。用於未來部署時比對、估算 propagation 時間、知道哪個帳號/team 對應哪個專案。

---

## 1. `dashboard-seven-lac-35` (raphael-workspace-dashboard)

**時間**：2026-06-06 14:04 部署，14:05 自驗證
**URL 類型**：Vercel 自動產生（隨機）

| 項目 | 結果 |
|------|------|
| 主要 alias（隨機） | `https://dashboard-seven-lac-35.vercel.app` |
| 自動 alias | `https://dashboard-hoonsors-projects.vercel.app`、`https://dashboard-hoonsor-hoonsors-projects.vercel.app` |
| 部署帳號 | hoonsor（hoonsors-projects team） |
| GitHub repo | `hoonsoropenclaw/raphael-workspace-dashboard` |

**踩雷**：
- ❌ 一開始只從 N100 curl 200 就回報「部署成功」
- ❌ 沒主動告知使用者 DNS cache / 無痕模式 繞過
- ✅ 使用者截圖 `ERR_NAME_NOT_RESOLVED` 才發現

**教訓**：**「從 N100 curl 200 ≠ 使用者打得到」**——這條 SOP 從此建立。

---

## 2. `raphael-status-site` 雷達圖修正

**時間**：2026-06-06 15:43-16:13
**URL 類型**：Vercel 自動 + 主要 domain

| 項目 | 結果 |
|------|------|
| 主要 domain | `https://raphael-status-site.vercel.app` |
| 隨機 alias（部署後） | `https://raphael-status-site-cff3cpte4-...vercel.app` |
| Alias HTTP 200 延遲 | 5-10 分鐘 |
| Vercel build time | 2s |

**踩雷**：
- ❌ 用 `<script>` 動態生成 SVG，沒考慮 `loadTab()` 用 `innerHTML` 注入
- ❌ HTML5 spec 明確禁止 `innerHTML` 內的 `<script>` 執行
- ❌ 我自己被 `browser_console` 回傳的 polygon 座標騙了（單獨開 tabs/overview.html 看得見 → 走注入後看不見）
- ❌ **沒走真實 production 流程驗證**（從 `index.html` 首頁進入的注入路徑）

**教訓**：
- **「自我報告 ≠ 驗證」**——必須走完整 production 流程
- 修法：刪 `<script>` 區塊，改用 Python 預算 SVG 座標直接 inline 寫進 HTML
- 整個 patch：-130 行 JS、+36 行 inline SVG

**現在結構**：
```html
<svg id="capability-radar" viewBox="0 0 320 320">
  <!-- 4 grid circles, 6 axis lines, 12 text, 1 polygon, 7 circles -->
  <!-- 全部 inline，沒有 JS -->
</svg>
```

---

## 3. `hermes-cli-reference`

**時間**：2026-06-06 21:48-21:55
**URL 類型**：固定（`hermes-cli-reference.vercel.app`）

| 項目 | 結果 |
|------|------|
| 主要 domain | `https://hermes-cli-reference.vercel.app` |
| 隨機 alias | `https://hermes-cli-reference-j7gago3x3-...vercel.app` |
| Alias 401 持續時間 | 短期（5-10 分鐘）|
| Vercel build time | 22ms（純靜態）|
| 內容規模 | 29 個指令、104 個 subcommand |

**驗證完整流程**（這次終於做對了）：
1. ✅ 本地 server + headless browser 渲染 29 blocks / 104 rows
2. ✅ Production HTTP 200 + 檔案結構驗證
3. ✅ 多 DNS 解析（1.1.1.1 / 8.8.8.8 / 9.9.9.9）
4. ✅ Production headless browser 123 互動元素

**這次沒踩雷**——因為有 SOP 了。

---

## 觀察到的 Vercel 機制

### Alias propagation
- **新部署的隨機 alias**：5-10 分鐘內可能 401，**不影響主 domain**
- **主 domain（`xxx.vercel.app`）**：永遠穩定
- **自動 alias（`xxx-hoonsors-projects.vercel.app`）**：建立後穩定，永久保留

### Vercel build 速度
- 純靜態（HTML/CSS/JS，無 build step）：**20-30ms**
- 有 build step（如 Vite、Next.js）：**2-10s**

### GitHub 連線錯誤
```
Error: Failed to connect hoonsoropenclaw/raphael-workspace-dashboard to project.
```
這是**預期錯誤**——Vercel CLI 用 hoonsor 帳號，但 repo 在主帳號。部署本身仍成功。要接 GitHub → Vercel auto-deploy：到 Vercel dashboard 點 Import Project。

---

## Vercel token 使用注意

- 環境變數：`$VERCEL_API_TOKEN`（已設，自動遮罩）
- **永遠不要 echo 出來** 或寫進檔案
- 部署指令：`vercel --token "$VERCEL_API_TOKEN" --yes --prod`

---

## Vercel project ID 對照

| Project Name | Project ID | GitHub Repo |
|---|---|---|
| hermes-portal | `prj_uUsJw3x4NZCofkO1KKFT7viCNvLD` | (本地，無 GitHub) |
| raphael-status-site | `prj_6FcNdvnHwPoXdkjr5csknUVJ5bUX` | `hoonsoropenclaw/raphael-status-site` |
| dashboard | `prj_Qsa9zeG8qNq7Y8DUg5xgPnig3UMM` | `hoonsoropenclaw/raphael-workspace-dashboard` |
| hermes-cli-reference | (查 `vercel projects ls` 確認) | `hoonsoropenclaw/hermes-cli-reference` |

---

## 自我審查 checklist（部署前 5 項 + 部署後 4 項）

**部署前**：
- [ ] 程式碼無硬編碼 API key（`grep -rE "ghp_|sk_live|sk-|api[_-]key" src/ js/`）
- [ ] `.gitignore` 排除 `node_modules`、`dist`、`.env`
- [ ] 本地 server + headless browser 跑過
- [ ] 沒用 `<script>` 動態生成關鍵內容（除非確認不是 innerHTML 注入）
- [ ] Vercel 部署是固定 domain，不是隨機 alias 給使用者

**部署後**：
- [ ] 主要 domain HTTP 200
- [ ] 隨機 alias 401 是預期（propagation）
- [ ] 多 DNS 解析（1.1.1.1 / 8.8.8.8 / 9.9.9.9）
- [ ] Production browser 走完整頁面流程，**不是**單獨打子檔案
