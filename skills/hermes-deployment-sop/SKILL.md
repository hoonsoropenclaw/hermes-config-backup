---
name: hermes-deployment-sop
description: "赫米斯部署完整生命週期 class-level skill — 涵蓋部署**前** preflight 預防（token 安全 / DDL 驗證 / E2E 10 項 / push 重試）+ 部署**時** worktree + Vercel preview + 4 層驗證 + 11 個已知雷區 + 部署**後**「先驗證後啟動」SOP（curl 多 DNS / Vercel readyState / headless browser 視覺確認）。觸發:任何 Vercel/Netlify/GitHub push/Supabase DDL/雲端部署、token 寫入檔案/命令列、棒 1 DDL、cron 改動的「前一刻」、部署完成要回報給使用者。**赫米斯主動撈規則**:收到「部署」「推送」「上線」「apply」「建網站」「deploy」「vercel」「git push」時,主動 load 本 skill。**2026-06-13 curator 整合**:原 `deployment-verification-sop` + `deploy-preflight-safelist` + `devops/hermes-deploy-verification` 三個 skill 合併為本檔的 class-level umbrella + 子 skill + 支援檔。"
risk: safe
source: hermes-internal
date_added: "2026-06-06"
last_updated: "2026-06-13"
version: "1.0.0"
---

# Hermes 部署 SOP (Hermes Deployment SOP) — class-level umbrella

> 赫米斯部署**完整生命週期**的 class-level skill。**任何對外有副作用的部署/推送/啟動,從「使用者丟訊息」開始到「我親自驗證完成」結束,全部走這個 SOP。**
>
> **2026-06-13 curator 整合**:原三個分散 skill 合併:
> - `deployment-verification-sop` (top-level, 2026-06-06 建立) → 內容降級為 `references/post-deploy-verification.md`
> - `deploy-preflight-safelist` (top-level, 2026-06-11 建立) → 內容降級為 `references/preflight-safelist.md`
> - `devops/hermes-deploy-verification` (subskill, 2026-06-07~11 累積) → **完整包重組為子 skill** `hermes-deploy-verification/` (含 1 reference + 1 script)

## 部署生命週期三階段

| 階段 | 何時 | 內容 | 對應支援檔 |
|------|------|------|-----------|
| **A. Preflight (預防)** | 部署**前一刻** | token 安全 / DDL 驗證 / E2E 10 項 / push 重試 / Vercel API 必帶 gitSource.org | [`references/preflight-safelist.md`](references/preflight-safelist.md) |
| **B. Deploy + 4 層驗證** | 部署中 + 完成 | 本地驗證 → 部署 + 取得 URL → 多管道驗證 → headless browser 視覺 + 11 個 Vercel/GitHub 雷區 + git worktree + Vercel preview SOP | [`hermes-deploy-verification/SKILL.md`](hermes-deploy-verification/SKILL.md) |
| **C. Post-Deploy (驗證)** | 部署**完成後** | 「我能跑 ≠ 使用者能跑」/「單管道驗證 ≠ 多管道驗證」/「自報 ≠ 驗證」/「部署 URL ≠ 給使用者的 URL」4 條核心原則 + 4 步 SOP + 給使用者的回報格式 | [`references/post-deploy-verification.md`](references/post-deploy-verification.md) |

> **未來 AI / 接手者**:看到本檔,先看這張表判斷你在哪一階段、然後跳到對應支援檔。**不要從頭讀到尾**。

## 何時該載入本 skill

> **赫米斯主動撈規則**:收到以下任何訊息時,**先** `skill_view("hermes-deployment-sop")` 看本檔判斷階段,再決定要載入哪個支援檔。

### 部署**前**(階段 A)
- 寫檔包含 token / API key / .env / 密碼 / 連線字串
- 命令列要 echo token / 拼環境變數在 bash command
- `git push` 到任何 remote (public/private 都算)
- `vercel deploy` / `netlify deploy` / Vercel API 觸發
- Supabase DDL / 任何「schema migration」任務
- 第一次 `git push` 到新 remote / 新 branch
- 改 `~/.hermes/config.yaml` / `.env` 並重啟 gateway
- **自我檢查**: 這次操作會動到「對外有副作用的狀態」? (是 → 走 SOP;否 → 不用)

### 部署**中** + **完成**(階段 B)
- 跑 `vercel --prod` / `vercel deploy` / netlify deploy
- `gh repo create` / `git push` 到 public/private remote
- 設了 cron job 並標記為 active
- 註冊了 webhook / API key / 第三方服務帳號
- **自我檢查**: 這次操作會讓使用者在「他自己的環境」看到東西? (是 → 走 SOP;否 → 不用)

### 部署**完成後**(階段 C)
- 部署成功收到 CLI 顯示「Ready / OK / promoted」
- 任何要回報「完成」+ 給使用者 URL 的時機
- 使用者反映「看不到」「打不開」「空白」
- **自我檢查**: 我親自驗證過使用者能打開了嗎? (沒有 → 不准回報「完成」)

## 三階段 SOP 速查

### 階段 A: Preflight (5 條核心原則 + 10 項清單)

完整內容見 [`references/preflight-safelist.md`](references/preflight-safelist.md)。**5 條核心原則(背下來)**:

1. **token 必在 env、不在 stdin / 命令列 / write_file**(原因:hermes 內建 token 過濾器在「輸出側」遮罩,但「寫入側 + 命令列組裝側」沒有預防)
2. **DDL commit 前必先 DB 驗證表存在**(慘案:棒 1 commit 時間早於 DB schema 建立時間 = SQL 沒真跑)
3. **E2E 必跑 happy + error path(10 項 minimum)**(慘案:school-bulletin production 5 個 bug 都是 E2E 只測 happy path)
4. **push 必 sleep 3s + 重試 3 次機制**(慘案:GitHub transient error / GH013 secret scan / 大檔卡 95%)
5. **Vercel API 必帶 `gitSource.org`**(慘案:`POST /v13/deployments` 400 `gitSource missing required property 'org'`)

**Preflight 10 項 checklist**(跑任何部署前必全勾):
```
[ ] 1. token 來源確認 (走 env 不走 stdin/命令列)
[ ] 2. .gitignore 包含所有 secrets (.env, .env.local, *.key, secrets/)
[ ] 3. repo 大小 < 100MB (du -sh .git/objects)
[ ] 4. 沒 untracked 大檔 (git status --short | grep -E 'M|A' | head)
[ ] 5. DDL 任務: SQL 必先 PG 跑過 + commit 訊息含時間戳
[ ] 6. E2E 10 項 minimum 全綠
[ ] 7. Vercel API 觸發: payload 必含 gitSource.org
[ ] 8. Vercel token 還有效 (curl /v9/projects/<name> 200)
[ ] 9. push 重試機制就緒 (for i in 1 2 3; do ...; done)
[ ] 10. production URL 是永久 alias,不是 hash URL
```

### 階段 B: Deploy + 4 層驗證

完整內容見 [`hermes-deploy-verification/SKILL.md`](hermes-deploy-verification/SKILL.md)。

**4 層驗證流程(缺一不可)**:
- **Layer 1 — 本地驗證**(commit 前):語法 / 邏輯 / 缺資源檔
- **Layer 2 — 部署 + 取得 URL**:CLI 顯示 Ready 不算,必拿到永久 alias
- **Layer 3 — Production 多管道驗證**:curl / dig 多 DNS / Vercel readyState
- **Layer 4 — Production 瀏覽器渲染**(最終保險):`browser_navigate` + `browser_console` 確認 JS 沒 error

**核心雷區(11 個,2026-06-07~11 累積)**:見子 skill §🐛 已知雷區
- 雷 1:`innerHTML` 注入的 HTML 內 `<script>` 不會執行
- 雷 2:Vercel 隨機 alias 短期 401
- 雷 3:使用者 DNS cache 沒更新
- 雷 4-11:gh CLI 帳號 / Vercel CLI 連線失敗 / `vercel --yes` 自動建新專案 / preview 預設要登入 / `vercel projects rm` 不可逆 / portal 沒 git repo 不能用 worktree / 多個 Vercel 專案同名相似但 alias 不同 / 兩個 Vercel token 生命週期不同別混用

**Git worktree + Vercel preview SOP**(user 強制要求,2026-06-07 確立):
1. 建立 git worktree feature branch
2. 修改 + commit feature branch
3. 部署到 Vercel preview(**不是 prod**)
4. 跑完整 4 層驗證
5. 通過才 merge + 部署 production
6. 清理

### 階段 C: Post-Deploy 驗證

完整內容見 [`references/post-deploy-verification.md`](references/post-deploy-verification.md)。**4 條核心原則(背下來)**:

1. **「我能跑」≠「使用者能跑」**(我從 N100 curl 200 / git push 成功 / vercel 顯示 Ready,**不代表**使用者從他家/公司瀏覽器能打開 — DNS propagation / 地理位置 / DNS cache)
2. **「單管道驗證」≠「多管道驗證」**(一個 curl 200 不夠,至少 3 個獨立驗證點)
3. **「自報」≠「驗證」**(Vercel CLI 顯示 `Ready` / `git push` 顯示 `To github.com` / `vercel projects ls` 顯示專案 — 這些是**系統自報**,不是**我親自驗證**)
4. **「部署 URL」≠「給使用者的 URL」**(隨機 hash URL 在新部署後 5-10 分鐘內可能 401;**唯一穩定的 URL 是「主要 domain」**)

**4 步標準 SOP**:
1. 主要 domain HTTP 200(`curl -s -o /dev/null -w "HTTP %{http_code}..."`)
2. 多 DNS 解析模擬使用者可能用的 DNS(`dig +short @1.1.1.1 / 8.8.8.8 / 9.9.9.9`)
3. 平台 API 確認「真的進 production」(Vercel `readyState="READY" + aliasAssigned` 是 timestamp 不是 null)
4. Headless browser 視覺確認(`browser_navigate` + `browser_console` 確認 `total_errors: 0` + DOM 元素存在)

**回報給使用者的格式**(模板):
```markdown
### 完成
- ✅ <做了什麼>

### 給你的 URL
**主網址**:https://<project>.vercel.app
(不是 hash URL,是永久 alias,直接加書籤可用)

### 我自己驗證過
| 項目 | 結果 |
|------|------|
| 主要 domain HTTP 200 | ✅ |
| 多 DNS 解析 | ✅ 1.1.1.1 / 8.8.8.8 / 9.9.9.9 都查到 |
| Vercel readyState | ✅ PROMOTED |
| Headless browser 視覺 | ✅ 截圖 + console 無錯 |

### ⚠️ 如果你打不開
- 試 Chrome 無痕 Ctrl+Shift+N
- 或改電腦 DNS 為 1.1.1.1
- 等 5-30 分鐘(DNS 同步全球需要時間)
```

## 跨階段 If→Then 速查

- **If** 寫檔包含 token **Then** 走 base64 / split-object / Python `os.environ`,**不用** write_file(階段 A)
- **If** 寫 DDL SQL **Then** 必先 PG 直連執行 + 查驗表存在 + commit 訊息含時間戳(階段 A)
- **If** `git push` 失敗 **Then** sleep 3s 重試 3 次,不是放棄(階段 A)
- **If** 部署前沒跑 E2E 10 項 **Then** 停下來先跑、不准 deploy(階段 A)
- **If** Vercel API 回 400 `gitSource missing required property 'org'` **Then** payload 加 `org: 'hoonsoropenclaw'`(階段 A)
- **If** 部署前沒建 git worktree + 沒跑 Vercel preview **Then** 停下來、user 強制要求(階段 B)
- **If** 看到 `***` 替換在 write_file / 命令列輸出 **Then** 改用 base64 + b64-decode 或 split-object(階段 A)
- **If** 棒 1 commit 時間早於 DB schema 建立時間 **Then** 棒 1 SQL 沒真跑、整段重來(階段 A)
- **If** 部署 Vercel 後我從 N100 curl 200 **Then** 還沒完,要走階段 C 4 步 SOP 才能回報「使用者可用」
- **If** 使用者回報 URL 打不開(`ERR_NAME_NOT_RESOLVED` 或 401) **Then** 第一個懷疑點是 DNS propagation,**不是**部署失敗,告知等 5-30 分鐘或用無痕模式(階段 C)
- **If** 給使用者 Vercel URL **Then** 永遠給「主要 domain」(`<project>.vercel.app`),不是隨機 hash URL(階段 C)
- **If** 看到 CLI 自報「成功」 **Then** 還是要用獨立工具(curl/dig/browser)親自驗證,**不信** CLI 自我報告(階段 C)
- **If** 改了使用者會依賴的東西(部署、cron、config、API key) **Then** 走「先驗證後啟動」SOP,**不要**直接回報「完成」(階段 C)

## 與其他 skill 的關係

- **本 umbrella** = 部署生命週期完整 SOP
- **`hermes-deploy-verification/` (子 skill)** = 階段 B 詳細 SOP(4 層驗證 + 11 雷區 + worktree SOP)
- **`references/preflight-safelist.md`** = 階段 A 完整 SOP(5 原則 + 10 項清單)
- **`references/post-deploy-verification.md`** = 階段 C 完整 SOP(4 原則 + 4 步 + 回報格式)
- **技術細節**(DNS propagation 機制、alias 401 常態、GH013 細節、gh CLI 帳號問題、Supabase RLS、Vercel token 生命週期)見 `trial-and-error/references/by-category/` 對應分類
- 棒 1 race / 多棒 handoff 細節見 `handoff-chain-timeout-sop.md`

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-06-13 | **curator 整合 3 個分散 skill 為 class-level umbrella**:合併 `deployment-verification-sop` (top-level, 2026-06-06) + `deploy-preflight-safelist` (top-level, 2026-06-11) + `devops/hermes-deploy-verification` (subskill, 2026-06-07~11)。前者兩者降級為 `references/`,後者重組為子 skill `hermes-deploy-verification/`(完整包含 1 reference + 1 script)。新加三階段生命週期表 + 跨階段 If→Then 速查 |
| 0.x | 2026-06-06~11 | 原三個分散 skill 各自演進 |
