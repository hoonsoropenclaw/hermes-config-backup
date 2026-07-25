---
name: hermes-deploy-verification
description: 標準化的部署前/中/後驗證流程，覆蓋本地驗證、production 多管道測試、DNS 同步、alias propagation、JS 注入陷阱等常見雷區。**任何時候要把網站/應用部署到 Vercel/Netlify/GitHub Pages 之前必須先載入此 skill**。Trigger：gh repo create 後、vercel --prod 前、收到「部署」「發佈」「push 並部署」「上線」等指令時。
---

# Hermes Deploy Verification SOP

> **核心原則**：自我報告 ≠ 驗證。從 N100 內網 curl 成功 ≠ 從使用者電腦打得開。

---

## 🎯 何時使用此 skill

任何時候滿足以下任一條件：

- 使用者說「部署」「發佈」「push 並部署」「上線」
- 即將跑 `vercel --prod` / `gh repo create` / `firebase deploy` / `netlify deploy`
- 部署後要回報 URL 給使用者
- 使用者反映「看不到」「打不開」「空白」

**不要在還沒部署前就派 subagent 評估** — 2026-06-07 教訓:user 叫我修改網站,我立刻派 subagent 評 A/B,user 中途說「不用評分」,浪費了一次 subagent + token。**如果任務需要 subagent 評估結果才能繼續,先問 user 確認**。

---

## 🚨 4 層驗證流程（缺一不可）

### Layer 1 — 本地驗證（commit 前）

目標：捕捉語法錯誤、邏輯錯誤、缺資源檔。

```bash
# 1. 語法檢查
node --check dist/ 2>/dev/null || python3 -c "import html.parser; ..."

# 2. 本地 HTTP server
cd <project> && python3 -m http.server 8765 &  # 用 background=true

# 3. 驗證所有資源 200
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" http://localhost:8765/ http://localhost:8765/css/styles.css http://localhost:8765/js/app.js

# 4. headless browser 開 + 確認關鍵元素
browser_navigate http://localhost:8765/
browser_console "document.querySelectorAll('.key-element').length"
```

### Layer 2 — 部署 + 取得 URL

```bash
cd <project>
vercel --token "$VERCEL_API_TOKEN" --yes --prod 2>&1 | tail -15
```

Vercel 會回傳 2 種 URL：
- **主要 domain**（固定，例如 `xxx.vercel.app`）— **這是給使用者的 URL**
- **隨機 alias**（`xxx-xxxxx-xxx.vercel.app`）— 5-10 分鐘後才通，**短期內會 401**

### Layer 3 — Production 多管道驗證

```bash
# 3a. 主要 domain HTTP 200
curl -s -o /dev/null -w "HTTP %{http_code}, time %{time_total}s, size %{size_download}B\n" \
  https://<main-domain>.vercel.app

# 3b. 隨機 alias 短期 401 是正常（propagation delay），不是 bug
curl -s -o /dev/null -w "%{http_code}\n" \
  https://<random-alias>.vercel.app

# 3c. 多 DNS 解析
for dns in 1.1.1.1 8.8.8.8 9.9.9.9; do
  ip=$(dig +short @${dns} <main-domain>.vercel.app A | head -1)
  echo "  $dns: $ip"
done

# 3d. 確認 GitHub 端
gh api repos/<owner>/<repo>/contents/ | grep '"name"'  # 公開 repo 從 N100 看得到
```

### Layer 4 — Production 瀏覽器渲染（最終保險）

```bash
# 從主要 domain 進入（不是單獨打子檔案）
browser_navigate https://<main-domain>.vercel.app/

# 驗證關鍵 DOM 元素真的 render 出來
browser_console "JSON.stringify({blocks: document.querySelectorAll('.cmd-block').length, sections: document.querySelectorAll('.section').length, data_loaded: typeof COMMANDS !== 'undefined'})"
```

**只用 `browser_console` 回傳值不夠**——你看到 `polygon 存在`不代表使用者看得到。要驗證**從使用者角度**走完整頁面流程。

---

## ⚠️ 部署前 SOP 必查清單

| 項目 | 為何 | 怎麼查 |
|------|------|--------|
| 程式碼含 `<script>` 注入 | 會被 `innerHTML` 注入失效 | `grep -rn "appendChild\|innerHTML.*=" src/ js/` |
| 頁面有用 `fetch()` 載入 tab HTML | 注入的 HTML 內 `<script>` 不會跑 | 確認 SPA 載入機制是 `innerHTML` 還是 `createElement` |
| 隨機數字/alphanumeric alias | 5-10 分鐘 propagation 期間使用者可能打不開 | 不要給使用者隨機 alias URL，**只給固定 domain** |
| DNS cache | 使用者瀏覽器/ISP cache 還沒更新 | 主動告知「用 1.1.1.1 DNS」或「無痕模式」 |
| `.env` / API token | 會被 git push 上公開 repo | `git status` + `grep -rE "ghp_\|sk_live" .` |
| `.gitignore` 排除 `node_modules` `dist` | 不然 push 會爆 | 確認 `.gitignore` 有這兩行 |
| **確認目標 Vercel 專案已存在** | 預設 `vercel --yes` 會用「資料夾名」建新專案 | `vercel projects ls` 先看 `projectName` 是什麼;目標專案要 `vercel link --project <name>` 才能打到對的 |
| **確認 Vercel 環境變數存在** | 後端 API 部署上去連不到 Supabase 會 500 | `vercel env ls --token $VERCEL_API_TOKEN` 看 SUPABASE_URL / API key 等 |

## 🌳 Git worktree + Vercel preview SOP（user 強制要求,2026-06-07 確立）

> **核心原則**：不要直接編輯 main、不要直接打 production。任何網站/前端修改必走這個流程。

### 為什麼要這個

- 直接編輯 main → 沒有「上線前最後確認」機會
- `vercel --prod` 一推,**所有使用者立刻看到**
- 一個 vercel deployment 壞了,其他專案的 production 都不受影響(Vercel project 隔離)
- 改 A 順便發現 B 壞了 → 來不及獨立評估每個改動的效果
- **整個工作流靠運氣不是靠 SOP**

### 完整 SOP

#### Step 1 — 建立 git worktree

```bash
cd /path/to/project
git worktree add ../<project>-<feature> -b feature/<name> main
cd ../<project>-<feature>
```

- 改檔完全不動原本 main
- 沒 git 的專案(如 hermes-portal)改用 `cp -r` 複製到 `../<project>-deploy/`,排除 `node_modules / .env.local / .vercel`

#### Step 2 — 修改 + commit feature branch

```bash
git add -A
git commit -m "fix: <description>"
git push -u origin feature/<name>
```

#### Step 3 — 部署到 Vercel preview(不是 prod)

```bash
cd ../<project>-<feature>
vercel link --project <target-project-name> --yes --token "$VERCEL_API_TOKEN"  # 必加,見雷 6
vercel --yes --token "$VERCEL_API_TOKEN"  # 不加 --prod = preview
```

- 預設會拿到 `xxx-<random-hash>.vercel.app` URL — **這是 preview,預設要登入才能看(401)**
- 短時間(2-5 分鐘)preview 會被 Vercel 保護機制擋,**這是正常不是 bug**
- 真的要測 preview 用 `vercel curl /api/path --deployment <url> --token $VERCEL_API_TOKEN`(Vercel CLI 帶 token 自動 bypass 保護)

#### Step 4 — 跑完整 4 層驗證

- Layer 1:本地跑 http server + curl 12+ 個 tab
- Layer 3:Production 不動,**只驗證 preview URL 的 12 個路徑 + 4 個資產 + API 端點**全 200
- Layer 4:browser 親自看 preview,**至少點 4 個不同 tab**,不是只看首頁

#### Step 5 — 通過才 merge + 部署 production

```bash
cd /path/to/project
git checkout main
git merge --ff-only feature/<name>
git push origin main
cd ../<project>-<feature>
vercel --prod --yes --token "$VERCEL_API_TOKEN"
```

#### Step 6 — 清理

```bash
git worktree remove ../<project>-<feature> --force
git branch -D feature/<name>
git push origin --delete feature/<name>  # 刪遠端
```

### **If → Then 規則**

- **If** 任何網站/前端專案要修改 **Then** 必先用 git worktree + feature branch + vercel preview
- **If** 改完才發現 bug **Then** 不用 revert production,只要刪 feature branch + preview deployment
- **If** 評審(A/B test) **Then** 評 preview URL 不是 production URL
- **If** 專案沒 git **Then** 用 `cp -r` 排除 node_modules / .env.local / .vercel

### 已驗證情境(2026-06-07)

- **rss-status-site fix/mdfiles-restore**:worktree → preview URL `hermes-status-site-fix-mdfiles.vercel.app` → browser 驗 7 卡片展開 → merge main → prod 部署 → cleanup。整個 production 0 風險
- **hermes-status-site-deploy branch**:`vercel --yes` 沒加 `vercel link` 自動建了一個新專案 `hermes-status-site-deploy`,這是 bug — 之後必先 link

---

## 🐛 已知雷區（過去踩過）

### 雷 1：`innerHTML` 注入的 HTML 內 `<script>` 不會執行

**症狀**：本地單獨開檔看得見，production 走 SPA 注入後空白。
**根因**：HTML5 spec 明確禁止 `innerHTML` 內的 `<script>` 執行（避免 XSS）。
**修法**：

- **方案 A**（推薦）：用 Python 預先算好 SVG/動態內容，**直接 inline 寫進 HTML**
- **方案 B**：改用 `DOMParser` + 取出 script 內容用 `eval()` 執行（有 XSS 風險，只在完全受信任的內容用）
- **方案 C**：每個 tab 改用 `<iframe src="tabs/xxx.html">`（沙箱化但增加複雜度）

**如果是 SVG/圖表**：純 SVG 不需要 JS，直接寫進 HTML 是最簡單的。

### 雷 2：Vercel 隨機 alias 短期 401

**症狀**：部署後 curl 隨機 alias URL 回 401，size ~15KB。
**根因**：Vercel 自動產生的 alias domain（如 `xxx-yyy-N.vercel.app`）DNS 還沒全球同步。
**不是 bug**——主要 domain（`xxx.vercel.app`）會 200。
**使用者體驗**：使用者打開主 domain 看到的內容跟 alias 一致，只是 alias 入口暫時不通。

### 雷 3：使用者 DNS cache 沒更新

**症狀**：使用者截圖 `ERR_NAME_NOT_RESOLVED`，但 N100 跟其他 DNS 都能解析。
**根因**：使用者電腦 / ISP / Chrome cache 還在用舊 DNS。
**解法（依快慢）**：
1. 最快：Chrome 按 `Ctrl+Shift+N` 無痕模式
2. 次快：把電腦 DNS 改 `1.1.1.1`
3. 標準：等 5-30 分鐘自然同步

**自我審查**：「我從 N100 curl 200 不代表使用者打得開」——這個盲點踩過 2 次（dashboard、hermes-cli-reference），每次都是使用者截圖才抓到的。

### 雷 4：gh CLI 預設帳號不是你以為的那個

```bash
gh auth status  # 看 Logged in to ... account
```

如果顯示備用帳號，要顯式切：
```bash
gh auth switch --user hoonsoropenclaw
```

但**部署到 Vercel 用備用帳號是正常的**——hermes-portal/hermes-status-site 都在 `hoonsors-projects` team（備用帳號 hoonsor 擁有）。**這不是 bug，是工作流設計**。

### 雷 5：Vercel CLI 預設連 GitHub 失敗

```bash
vercel --prod
# Error: Failed to connect <owner>/<repo> to project
```

Vercel CLI 走當前 gh 帳號（hoonsor），而 GitHub repo 在主帳號（hoonsoropenclaw）。**這是預期錯誤，部署本身仍會成功**——只是 GitHub webhook 不會自動連。要接 GitHub → Vercel auto-deploy，**到 Vercel dashboard 點 Import Project**。

### 雷 6：`vercel --yes` 預設會用「資料夾名」建新專案(2026-06-07 踩到)

**症狀**：你想 deploy 到現有專案 `hermes-status-site`,但跑完 `vercel --yes` 後 Vercel 多了一個新專案 `hermes-status-site-deploy`,然後 **alias 還是 alias 到新的**。
**根因**:`vercel` CLI 預設 `.vercel/project.json` 沒指到目標專案時,用「目錄名」當新專案名建一個新的。
**修法**:在 deploy 前先 `link` 到目標專案:

```bash
vercel link --project <target-project-name> --yes --token "$VERCEL_API_TOKEN"
```

確認 `.vercel/project.json` 裡 `projectName` 是你要的:

```bash
cat .vercel/project.json
# {"projectId":"prj_xxx","orgId":"team_xxx","projectName":"actual-name"}
```

**然後**才能 `vercel --yes` 部署到對的專案。
**預防**:deploy 任何專案前第一個 todo 必是 `vercel projects ls` 看目標專案名 + `vercel link` link 過去。

### 雷 7:Vercel preview deployment 預設要登入(401),跟正式 alias 不一樣(2026-06-07 確認)

**症狀**:worktree SOP 跑 `vercel --yes`(沒加 --prod)拿到 preview URL,curl 卻回 401 + 15KB HTML 認證頁。
**根因**:Vercel 自動給 preview deployment 加了保護機制,只有專案 owner 能看,防止外人偷看未公開的部署。
**不是 bug**。兩個選擇:

1. **直接 `vercel --prod` 推 production alias** — alias 永遠公開,但失去 staging 階段
2. **用 `vercel curl` 帶 token**:`vercel curl /api/path --deployment <preview-url> --token $VERCEL_API_TOKEN`(Vercel CLI 自動生成 bypass secret)

**如果用 worktree SOP 嚴格跑**,preview 是「只有你能看」的 staging 環境,**這正是 worktree 想要的隔離**。preview 401 反而是好事。

### 雷 8:`vercel projects rm <name>` 不可逆 + 不吃 `--yes`(2026-06-07 確認)

**症狀**:批次刪除測試專案時 `vercel projects rm xxx --yes` 報 `unknown or unexpected option: --yes`。
**根因**:`--yes` 不是全域 flag,`projects rm` 沒實作。
**修法**:用 stdin 餵 "y":

```bash
echo "y" | vercel projects rm <project-name> --token "$VERCEL_API_TOKEN"
```

會看到 3 次 prompt 都被 "y" 答掉,然後 `Success! Project <name> removed`。
**警告**:刪除不可逆,沒有 recycle bin。**部署跟 alias 一起刪**。刪前必先 `vercel projects ls` 確認列表。

### 雷 9:portal 沒 git repo → 不能用 worktree → 用 cp -r(2026-06-07 確認)

**症狀**:`cd hermes-portal && git status` 報 `fatal: not a git repository`。
**解法**:用 `cp -r` 複製到 deploy dir,排除不該部署的:

```bash
cp -r /path/to/project ../project-deploy
rm -rf ../project-deploy/node_modules
rm -f ../project-deploy/.env.local
rm -rf ../project-deploy/.vercel
```

**別忘了排除 .env.local** — 內含 SUPABASE_SERVICE_ROLE_KEY 等 secrets,推上 Vercel 雖然會被 build ignore,但不該在 deploy dir 留著。
**Vercel 環境變數已經存在的話**:`vercel env ls` 確認,不要重新設;**若要確認一致性**:`vercel env pull .vercel-check-env --environment=production --yes --token $VERCEL_API_TOKEN`,然後比對 `.env.local` 開頭幾個字元(不要 echo 完整值比 md5)。

### 雷 10:多個 Vercel 專案同名相似但 alias 不同(2026-06-07 確認)

**症狀**:`hermes-status-site` 跟 `raphael-status-site` 是 Vercel 上**兩個獨立專案**,不是 alias 關係。你 deploy 到其中一個不會影響另一個。
**教訓**:
- 部署前必先 `vercel projects ls` 看專案清單
- 用戶說「部署到 X」要明確確認 X 是哪個 URL 對應的 Vercel project
- 不要假設「同個目錄名 = 同個專案」(`hermes-status-site-deploy/` 跟 `hermes-status-site/` 是兩個不同的東西)
- 如果 deploy 之後用戶問「網址是?」你回答錯的網址,user 會打開另一個專案的舊版本看不到新東西

**驗證 alias 跟目標專案匹配**:
```bash
vercel inspect <deployment-url> --token $VERCEL_API_TOKEN
# 確認顯示的 project 是目標
```

---

## 🛠️ 環境工具配置（hoonsoropenclaw@N100）

| 工具 | 位置 | 認證 |
|------|------|------|
| `gh` CLI | `~/.local/bin/gh` 或系統 | `gh auth status` 查；主 `hoonsoropenclaw` / 備 `hoonsor` |
| `vercel` CLI | `~/.npm-global/bin/vercel` | 環境變數 `$VERCEL_API_TOKEN`（已設） |
| Git remote 協定 | SSH（`git@github.com:...`） | 看 `git remote -v` |
| Vercel team | `team_FhyeReXMTNCeyU6qkghsNatY` = `hoonsors-projects` | 用備用帳號 hoonsor 部署 |

**Vercel 環境變數位置**：`VERCEL_API_TOKEN` 已在 shell env（已自動遮罩），不需要重新設定。

**找 Vercel project 連結**：每個專案根目錄的 `.vercel/project.json` 是**名稱真實來源**（不是資料夾名）：
```json
{"projectId":"prj_xxx","orgId":"team_xxx","projectName":"actual-name"}
```

### 路徑對應(2026-06-07 確認)

| 主電腦 (Windows Y:\) | N100 (Linux) |
|------|------|
| `Y:\` | `/home/hoonsoropenclaw/` |
| `Y:\permanent-projects\hermes-status-site` | `/home/hoonsoropenclaw/permanent-projects/hermes-status-site` |
| `Y:\permanent-projects\hermes-portal` | `/home/hoonsoropenclaw/permanent-projects/hermes-portal` |

**If** 使用者提到 Y:\、Y槽、Windows 路徑 **Then** 直接轉成 /home/hoonsoropenclaw/ 開頭的 Linux 路徑
**If** 不確定路徑對應 **Then** 先 `ls /home/hoonsoropenclaw/` 或 `find / -maxdepth 4 -name "<專案名>" -type d` 確認

### Vercel 帳號下常見專案(2026-06-07 確認)

每個 Vercel 專案有獨立 alias 網域,**部署前必先確認目標專案名**。常見的有用專案:
- `hermes-portal` → `hermes-portal.vercel.app`
- `hermes-status-site` → `hermes-status-site.vercel.app`
- `raphael-status-site` → `raphael-status-site.vercel.app`(歷史 alias,跟 hermes-status-site 是兩個獨立專案)
- `hermes-cli-reference` → `hermes-cli-reference.vercel.app`

**若同個程式碼要 deploy 到多個專案**:用 `vercel link --project <每個不同的 name>` 分別建 deploy dir。**不要假設「hermes-status-site 跟 raphael-status-site 是同一個」** — 它們是獨立專案,改其中一個不會影響另一個。

---

## 📋 部署後要回報使用者的資訊

**主動回報 — 不要等使用者問**(2026-06-07 教訓:user 問「請問你部署好的網址是?」代表我沒主動給):

```markdown
### 部署完成
- **主要 domain（這個給使用者）**:https://<name>.vercel.app
- 隨機 alias(5-10 分鐘後才通,不用管):https://<name>-xxxxx-xxx.vercel.app
- GitHub:https://github.com/<owner>/<repo>

### 驗證結果
- Layer 1(本地):✅
- Layer 2(deploy):✅
- Layer 3(production HTTP + DNS):✅
- Layer 4(production browser):✅

### 使用者看到的話
1. 強制 reload(`Ctrl+Shift+R`)清 Vercel 60s cache
2. 如果還是看不到,Chrome 無痕模式 `Ctrl+Shift+N`
3. 如果還是不行,把電腦 DNS 改 1.1.1.1
```

**如果部署多個專案**(例如同時 deploy hermes-status-site + hermes-portal),每個都列:**目標專案 → 部署到的 alias → 驗證結果**。不要合併成「部署完成」一句話帶過。

---

## 🔗 相關入口

- `~/.hermes/RULES.md` — 檔案總管分層規則（permanent-projects/、tools/、scripts/）
- `~/.hermes/memories/MEMORY.md` — 抽象決策原則
- `~/.hermes/skills/trial-and-error/` — 具體 L2 bug 解法庫

---

## 📂 支援檔案

- `references/deployment-history-2026-06.md` — 本次 session 三個專案的具體部署 trace（dashboard、status-site 雷達圖修正、hermes-cli-reference）
- `scripts/verify-deployment.sh` — 部署後一鍵跑 4 層驗證（curl + DNS + 內容檢查）+ Layer 5 多 tab/資產批次 + Layer 6 API smoke test

---

## 📝 變更記錄

- 2026-06-06: 初版（dashboard、status-site 雷達圖、hermes-cli-reference 三次部署累積的 SOP）
- 2026-06-07: 加 git worktree + vercel preview SOP 完整 section(user 強制要求,2026-06-07 session 確立);加 5 個新雷區(6: `vercel --yes` 預設建新專案、7: preview 401 是正常、8: `projects rm` 不吃 --yes、9: portal 沒 git 用 cp -r、10: 多 Vercel 專案同名相似但 alias 不同);加路徑對應表(Y:\ = /home/hoonsoropenclaw/) + 多專案現實;部署後回報模板加「主動給網址 + 多專案分別列」;觸發條件加「subagent 評估前要問 user」;驗證 script 加 Layer 5 多 tab/資產批次 + Layer 6 API smoke test
