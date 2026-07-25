# 部署後自我驗證失敗的真實案例（2026-06-06）

> 本檔收錄「我以為我驗證過了，但使用者打開網站才發現沒成功」的真實場景。
> 每個案例都附「症狀 / 為什麼我以為 OK / 真正失敗原因 / 修正 SOP」。

---

## 案例 1：能力雷達圖 SVG 渲染失敗（status-site）

### 症狀
部署完成、回報給使用者「部署成功」。使用者截圖顯示網站上「能力雷達圖」整個區塊**完全空白**，沒有任何 SVG 線條、文字、標籤。

### 為什麼我以為 OK
- 本地 `python3 -m http.server 8765` 跑起來
- Headless browser 開 `http://localhost:8765/tabs/overview.html`
- browser_console 顯示 `polygon.getAttribute('points')` 拿得到 6 個座標
- 我把「headless browser 拿得到 polygon 座標」當成「使用者看得到雷達圖」

### 真正失敗原因
- 雷達圖的 SVG 是**用 JS 動態生成**的（`document.createElementNS` 加 circle、polygon、text）
- 生成 JS 寫在 `tabs/overview.html` 最底下的 `<script>` 區塊
- 但 `index.html` 的 `loadTab()` 用 `contentDiv.innerHTML = html` 注入 tab HTML
- **HTML5 spec 明確禁止 innerHTML 注入時執行 `<script>` 標籤**（安全機制）
- 結果：production 上 SVG 容器是空的，**所有動態生成的元素都沒跑**
- 我驗證的 `tabs/overview.html` 單元檔**直接開啟**，跟 production 走 `loadTab()` 注入的路徑**完全不同**

### 修正
把 SVG 座標用 Python 預先算好，**直接 inline 寫進 HTML**，不靠 JS 生成。`diff -130 +36`，純靜態 SVG。

### 教訓（已寫入 SKILL.md 陷阱 D）
- **單元驗證 ≠ 整體驗證**
- SPA 用 innerHTML 注入的 tab HTML，所有 JS 必須用 `window.*` 命名空間 + inline event handler
- 不能放 `<script>` 標籤

---

## 案例 2：dashboard 部署後使用者打不開（DNS cache）

### 症狀
部署完成、回報「URL 是 `https://dashboard-seven-lac-35.vercel.app`」。使用者截圖：**ERR_NAME_NOT_RESOLVED**（DNS 找不到這個 domain）。

### 為什麼我以為 OK
- 從 N100 內網 `curl https://dashboard-seven-lac-35.vercel.app` → HTTP 200
- size 254868 bytes = 跟 `dist/index.html` 一模一樣
- 我把「N100 curl 200」當成「部署成功」

### 真正失敗原因
1. 部署到 Vercel 後，domain 註冊到 Vercel 邊緣 DNS
2. 不同 DNS resolver 同步新 domain 需要 5-30 分鐘
3. **N100 自己的 DNS 已經更新了**（可能我用 N100 跑驗證的時間點剛好 > 30 分鐘）
4. **使用者在他家/公司網路**，DNS cache 還沒更新
5. `ERR_NAME_NOT_RESOLVED` = 使用者的電腦完全找不到這個 domain 的 IP

### 修正
1. 重新設計驗證 SOP：必做多 DNS 查詢（1.1.1.1 / 8.8.8.8 / 9.9.9.9 都要查到才算「domain 真的註冊了」）
2. 回報給使用者時**主動告知**：「建議用無痕模式（Ctrl+Shift+N）繞過 DNS cache，或改 DNS 為 1.1.1.1，等 5-10 分鐘 DNS 自然同步」

### 教訓（已寫入 SKILL.md 陷阱 C）
- **N100 內網 curl 200 ≠ 使用者打得開**
- 自我審查 SOP：不可只做 N100 curl 就回報部署成功
- 必做：多 DNS 解析 + 給使用者明確建議

---

## 案例 3：git push 後沒自動部署

### 症狀
改完程式碼 → `git add . && git commit && git push origin main` → 等 5 秒 → `curl https://hermes-cli-reference.vercel.app/js/chat-commands.js` → **HTTP 404**

### 為什麼我以為 OK
- git push 成功
- 沒看到錯誤訊息
- 我以為 Vercel 會自動從 GitHub 抓新版本部署

### 真正失敗原因
- Vercel **預設不會**自動從 git push 觸發 production 部署
- 必須在 Vercel 後台勾選「Git 整合 → Production Branch → Deploy on push」才會自動
- 沒勾選 → 每次都要手動 `vercel --prod`

### 修正
- git push 完**一定要手動跑** `vercel --token "$VERCEL_API_TOKEN" --yes --prod`
- 驗證：抓**新加的 asset 檔案**（不是 index.html）確認 size 變了 / HTTP 200

### 教訓（已寫入 SKILL.md 陷阱 A）
- **git push ≠ Vercel deploy**
- 預設是手動的

---

## 案例 4：Vercel 隨機 alias URL 暫時 401

### 症狀
部署完看到 vercel CLI 吐 `https://hermes-cli-reference-j7gago3x3-hoonsors-projects.vercel.app`，curl 這個 URL → **HTTP 401**, "Authentication Required"

### 為什麼我以為 OK
- vercel CLI 自己吐的 URL
- 上一次部署的相同格式 URL 有成功
- 我以為這次也會成功

### 真正失敗原因
- 每次 production 部署會生成新隨機 alias
- 新 domain **需要 5-10 分鐘**全球 DNS 同步才會通
- 5-10 分鐘內 curl 會回 401

### 修正
- **不要用隨機 alias URL 驗證部署**
- 用**固定名字的 alias**（如 `hermes-cli-reference.vercel.app`）驗證
- 隨機 alias 等 5-10 分鐘自己會通

### 教訓（已寫入 SKILL.md 陷阱 B）
- 隨機 alias URL 部署後會暫時 401
- 用固定 alias 驗證

---

## 通用 SOP（避免重蹈覆轍）

部署到 Vercel 任何網站後，**必做 4 步驗證**：

```bash
# 1. 多 DNS 解析（確認 domain 真的註冊了）
for dns in 1.1.1.1 8.8.8.8 9.9.9.9; do
  echo "$dns: $(dig +short @$dns <domain> A | head -1)"
done

# 2. 固定名字的 alias HTTP 200（不要用隨機 alias）
curl -sI https://<project>.vercel.app | head -3

# 3. 新加的 asset 也 200（不只是 index.html）
curl -sI https://<project>.vercel.app/js/<new-file>.js | head -3

# 4. Headless browser 從首頁進入（不是單元檔案）走真實流程
#    從首頁 → 點 tab → 檢查內容 render 正確
```

**回報給使用者時一定要附：**
- 固定名字的 domain URL
- 主動告知「建議無痕模式繞過 DNS cache」
- 不要說「我這邊看得到你也一定看得到」
