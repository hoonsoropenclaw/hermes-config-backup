# 🧠 MEMORY.md - 長期記憶

## 📖 說明
這是赫米斯的長期記憶檔案，記錄重要的學習成果、經驗教訓和系統知識。

## 🌍 環境事實（跨 session 不變的事實）

### Google Drive API 配額（2026-06-06 從 rclone stderr 確認）
- **配額上限 = 840,000 單位/分鐘/專案**（`drive.googleapis.com/default`）
- rclone sync 每個小檔 ≈ 3-5 個 API 單位
- 10000+ 小檔 = 50000+ API 單位 → **幾分鐘內秒殺配額**
- 看到 `RATE_LIMIT_EXCEEDED` 就是硬限制、不要忽略
- 配額重置週期 = 1 分鐘
- 申請提高配額：https://cloud.google.com/docs/quotas/help/request_increase

**If** 對 Drive 用 rclone sync 跑 10000+ 小檔目錄
**Then** 預期必爆 API 配額、speed 會從 MB/s 掉到 KB/s
**Then** 解法：加 `--tpslimit 5 --transfers 1 --checkers 1`（1-2 小時跑完）
**Then** 或改 tar.gz（雖然大、但只需 1 個 API request、穩定）

### 備份架構觀念：rebuild 優先、可重建的不備（2026-06-06 確立，2026-06-09 清理）
- **If** 設計任何備份架構 **Then** 先問「每個資料類型有沒有辦法 rebuild」、不要憑印象答
- 具體架構（v4.1 雙雲端 Tier 1 GitHub / Tier 2 Drive + GPG 加密）細節在 `trial-and-error/references/by-category/hermes-backup-strategy.md`（MEMORY 不重複）

### Keyword 符號分工（2026-06-11 確立）
- **`^` = handoff pipeline 觸發**（例：`^專案 我想做技能交換平台`）—— 赫米斯 default 串接多個常駐代理（consumer-researcher → product-planner → system-architect → engineering-lead → test-engineer，鏈長動態）
- **`@` = skill 觸發**（例：`@學習 rclone 配額`）—— 載入單一 skill 進 context（`@學習` = `trial-and-error` skill）
- **無前綴 = 一般對話**
- 完整 SOP：`~/.hermes/memories/references/sops/keyword-triggers-sop.md`
- 觸發判斷在 AGENTS.md keyword 表，**看到 `^xxx`/`@xxx` 開頭訊息就對應觸發**
- **If** 設計新 keyword **Then** 先決定走 `^`（handoff 鏈）還是 `@`（skill），**不要混用前綴**（多義前綴會造成判斷混淆）

> **清理原則**（2026-06-06 修訂）：本檔只放**跨 session 仍有用的抽象知識**。
> - ✅ 留：高層架構、環境事實、穩定決策原則、If→Then 抽象規則
> - 📦 移：具體工具試誤條目 → `trial-and-error` skill 的 `references/by-category/`
> - 🗑️ 刪：任務進度、commit/PR 編號、單次 session 結果、過時技術細節（用 `session_search` 撈）

## 🗓️ 更新記錄（只留近 2 條，歷史可從 session_search/git 撈）
- 2026-06-11: **`^專案` keyword 替換 `@專案`**——`^` = handoff pipeline、`@` = skill trigger、無前綴 = 一般對話。keyword 設計要避免多義前綴（視覺符號差異是 zero-cost 防呆機制）。完整 SOP 在 `keyword-triggers-sop.md`
- 2026-06-11: **handoff chain 收尾必跑「PRD 對照驗收」4 步**——school-bulletin 跑 4 棒 handoff、9 個 Must 只實作 5 個。完整 SOP 在 `handoff-chain-acceptance-sop.md`

---

## 🚨 重要系統規範

### Hermes Agent 安裝方式
- **主機**: N100 迷你電腦 (hoonsoropenclaw@100.88.38.80)
- **安裝方式**: **使用者層安裝**（`~/.local/bin/hermes` wrapper、125 bytes、2026-05-30 建立）→ **不是**系統級 npm -g
- **Hermes 版本**: v0.16.0（upstream 57775e9e）
- **Hermes 家目錄**: `~/.hermes/hermes-agent/`（原始碼/venv 家，wrapper 從這跑）
- **npm 全域狀態**: **沒裝** hermes（`npm ls -g` 找不到）
- **PATH 設定**: `~/.bashrc` 末行 `export PATH="$HOME/.local/bin:$PATH"`（2026-06-09 補的）
- **工作區**: `~/.hermes/`
- **配置路徑**: `~/.hermes/config.yaml`
- **技能路徑**: `~/.hermes/skills/`
- **記憶路徑**: `~/.hermes/memories/`

**If** 「hermes command not found」**Then** 先 `which hermes` + `ls ~/.local/bin/hermes` + `tail -5 ~/.bashrc` 三件套確認 wrapper 跟 PATH，**不要預設是 npm -g 路徑沒設**（這個系統本來就不是 npm -g 裝的）
**If** 未來要升級 hermes **Then** `cd ~/.hermes/hermes-agent && git pull && pip install -e .` 才是 user-local 的正確升級路徑（不是 `npm update -g`）
**If** `which hermes` 回 `~/.hermes/hermes-agent/venv/bin/hermes` 而不是 `~/.local/bin/hermes` **Then** 該 shell session 已經進了 venv（不是「找到錯誤的 hermes」），新 shell 預設走 `~/.local/bin/hermes`

### 與前任拉斐爾 OpenClaw 套件代理的協作關係 — **2026-06-08 結束,名字併入赫米斯**
- **前任拉斐爾 OpenClaw 套件代理**已於 2026-06-08 反安裝完成（見 `~/shared-infra/OPENCLAW_REMOVAL_REPORT_v1.md`、詳細試誤在 `trial-and-error/references/by-category/hermes-internal.md`）
- **前任拉斐爾 7 份「重要檔案」** 備份在 `~/shared-infra/raphael-workspace-docs/AGENTS.original.md` 等
- **AGENTS.md 內仍有「前任拉斐爾 OpenClaw 時代」的歷史紀錄**（赫米斯自己內建的 `openclaw-migration` skill 描述的一部分,跟外部 OpenClaw 無關,**不需修**）

### MemPalace 三層備援搜尋
- **路徑**: `~/.hermes/mempalace/` 或 `~/.mempalace/`
- **用途**: 當 session_search 搜尋不到時的備援語意搜尋
- **MCP 工具**: `mempalace__mempalace_search`
- **觸發條件**: session_search 空結果或分數 < 0.3 時使用

**三層搜尋流程**：
1. Phase 1 - session_search：先用本地對話記錄搜尋
2. Phase 2 - mempalace__mempalace_search：若 Phase 1 分數 < 0.3，自動觸發向量語意搜尋
3. Phase 3 - LLM Re-rank：若 Phase 2 結果仍 < 0.4 或結果過多，使用 MiniMax LLM 對候選結果重新排序

---

## 🔒 智能環境安全與執行規範 (Smart Execution Protocol)

### 🚨 紅區攔截 (Red Zones) - 強制人類授權
當你的指令嘗試修改、刪除或覆蓋以下目錄與檔案時，【必須】暫停並詢問人類 (Y/N)：
1. **系統核心**：`/etc`, `/var`, `/usr`, `/boot` 及任何系統層級配置檔。
2. **專案核心**：任何包含 `SOUL.md`, `SKILL.md`, `.env`, `docker-compose.yml` 的資料夾。
3. **記憶資料庫**：`/data`, `/shared_workspace` 根目錄，以及任何包含 `nmem` 或資料庫掛載的路徑。
4. **危險操作**：任何使用遞迴強制刪除且路徑不明確的指令（例如單純的 `rm -rf *` 或指向根目錄 `/`）。

### 🟢 綠區放行 (Safe Zones) - 全自動靜默執行
你獲准在以下情境【自動靜默執行】刪除或清理動作，不需人類介入：
1. **暫存資料夾**：`/tmp`, `./node_modules` (僅限重新安裝時), `./.cache`, `./__pycache__`。
2. **測試沙盒**：明確被標記為「拋棄式測試區」的容器內部或特定子資料夾（如 `./sandbox_tests/`）。
3. **建置產物**：如 `./build`, `./dist` 等在編譯前需要清理的常規目錄。

### ⚙️ 執行工具守則
當你呼叫 `execute_bash` 或修改檔案的工具時，系統底層會自動檢查路徑。如果你的操作不在綠區範圍內，系統將會報錯或觸發人類審查。請在編寫腳本時優先在綠區進行測試。
---

## 🧭 抽象決策原則（跨領域適用，L3 細節 → trial-and-error）

**完整內容（117 行）已遷移到** `trial-and-error/references/by-category/abstract-decision-principles-20260628.md`

本節僅保留摘要索引：
- 常駐子代理 = profile + tmux（非 agents/ 舊方案）
- 卸載前必先查「概念現在還活著嗎」
- 精瘦 profile 原則：30-60 個 skill 不是 194
- 跨 profile handoff pipeline（orchestrator 串接 SOP）
- 架構優先於速度、三層分離原則
- 自我審查：驗證命令不可缺
- 備份：單靠本地金鑰不算備份、rsync exclude 需覆蓋同形子目錄
- sub-agent 無狀態、_plan.md 是必備介面契約

---

## 🚨 Google OAuth 在 headless 環境的 4 條鐵律（2026-06-07 試誤總結）

### 鐵律 1：client 類型決定一切
- **「電腦應用程式」client → 不能用 Device Code Flow**（回 401）
- **必須選「TV 和 limited-input devices」client 類型** → 才能用 Device Code Flow
- Device Code Flow 是 N100 headless 跑 OAuth 的**唯一乾淨解**（使用者在自己電腦開 Chrome 輸入 user_code 即可）
- **不要**浪費時間在電腦 client 上找 hack（改 scope、改 grant_type、SSH tunnel + VNC + noVNC 都不乾淨）

### 鐵律 2：Device Code Flow 的 scope 限制
- ✅ 合法：`youtube.readonly`、`openid`、`email`、`profile`
- ❌ **不合法**：`youtube.force-ssl`（要 HTTPS only environment，Device Flow 不接受）
- ❌ `subscriptions.readonly`（Device Flow endpoint 不接受，雖然其他 OAuth flow 接受）
- **「讀取 YouTube 訂閱」用 `youtube.readonly` 就夠**（Google 允許 read-only scope 讀取訂閱資料）
- **寫 OAuth script 時先一個個 scope 測**，別一次送一堆

### 鐵律 3：Device Code polling 三個 error code 要分開處理
- `authorization_pending` → 繼續 polling（使用者在想/輸代碼）
- `slow_down` → **不是錯**！interval += 5，繼續 polling
- `access_denied` → 使用者按拒絕，break
- **不要用 `raise_for_status()` 在 polling loop**（400/403/428 都是「正常等待狀態」不是 HTTP error）

### 鐵律 4：重新拿 device_code 會作廢舊的
- Google 同 client 同時間只允許一個 active device_code
- 重拿時**必須明確告訴使用者「舊代碼作廢」**（Google 會對舊代碼回「驗證碼不正確」）
- 顯示 user_code 時**大字、唯一有效**標示
- background script **寫到 file log 而非 stdout**（避免 Hermes background tool 的 buffer 問題，使用者看不到「最新」代碼）

---

## 📁 YouTube OAuth 環境事實（2026-06-07 確認）

- **OAuth client JSON**：`~/.local/share/hermes/secrets/youtube_client.json`（mode 600）
- **OAuth tokens**：`~/.hermes/youtube_tokens.json`（mode 600，存 access_token + refresh_token + scope + expires_at）
- **Google Cloud 專案 ID**：`enki-489612`（顯示名稱「Raphael」、專案編號 `200915391477`）
- **目前 active OAuth client_id**：`200915391477-dcc1nipuoq77frnl5o8s434tkntmju82`（TV/limited-input 類型，2026-06-07 由使用者建立）
- **active scope**：`youtube.readonly`（**夠用**：能讀訂閱、頻道、影片 metadata）
- **重跑 OAuth 腳本**：`/tmp/oauth_poll.py`（背景 polling，log 寫到 `/tmp/oauth_poll.log`）
- **可重複使用的 OAuth 腳本**：`~/.hermes/scripts/youtube_oauth_device.py`（已寫好，給未來任何 Google OAuth 用）
- **公開 RSS feed URL**：`https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxx`（不需任何 token 就能抓最新影片）

**If** 你 N100 想抓 YouTube 訂閱頻道新影片
**Then** 直接用公開 RSS（**不需 OAuth**），一行 curl 就好
**Then** 但要先有 channel_id 清單（從 OAuth `subscriptions.list` API 拿，或手動維護）
**Then** 訂閱清單**已抓過一次**存在赫米斯 session 內（8 個頻道：泛科學院 / Debug 土撥鼠 / 技术爬爬虾 / HC AI說人話 / 工程師下班有約 / AI学长小林 / AI超元域 / PAPAYA 電腦教室）

---

## 📋 抽象知識索引（具體細節在 skill）

### 工具試誤條目 → trial-and-error skill
- GPG / 加密 / 簽章 → `skills/trial-and-error/references/by-category/gpg-encryption.md`
- gh CLI / GitHub API / 雙帳號 / token → `skills/trial-and-error/references/by-category/gh-cli-and-github.md`
- Vercel CLI / API / 部署 → `skills/trial-and-error/references/by-category/vercel-deployment.md`
- Python sandbox / token 字串遮罩 → `skills/trial-and-error/references/by-category/python-sandbox.md`
- 環境變數 / .env / 憑證管理 → `skills/trial-and-error/references/by-category/secrets-and-env.md`
- 瀏覽器自動化 / Playwright / headless → `skills/trial-and-error/references/by-category/browser-automation.md`
- Hermes 內部 cron / 工具 / 架構 → `skills/trial-and-error/references/by-category/hermes-internal.md`

### 任務進度 / 單次 session 結果
- 用 `session_search` 撈（會跨所有過去 session 搜，沒真的消失）
- 7 天內過期的東西不入本檔

---

## 🔁 MEMORY.md 自我清理規範

- **觸發閾值**：本檔超過 25 KB 時赫米斯主動建議掃一次
- **清理方向**：見檔頭「清理原則」三類
- **流程**：赫米斯**不直接動手**清理，先列「建議刪除/移動的條目 + 為什麼」給使用者看，確認後才動手
- **驗證**：清理後跑 `wc -c` 確認縮減幅度

---

## 📁 路徑對應(2026-06-07 確認)
- **Y:\** = **/home/hoonsoropenclaw/**(主電腦跟 N100 之間的對應)
- 副檔名對應:Y:\permanent-projects\hermes-status-site = /home/hoonsoropenclaw/permanent-projects/hermes-status-site
- 副檔名對應:Y:\permanent-projects\hermes-portal = /home/hoonsoropenclaw/permanent-projects/hermes-portal
- 副檔名對應:Y:\hermes-portal = /home/hoonsoropenclaw/hermes-portal(非永久,可能已被 verify 過)
- **If** 使用者提到 Y:\、Y槽、Windows 路徑 **Then** 直接轉成 /home/hoonsoropenclaw/ 開頭的 Linux 路徑
- **If** 不確定路徑對應 **Then** 先 `ls /home/hoonsoropenclaw/` 或 `find / -maxdepth 4 -name "<專案名>" -type d` 確認

---

## 🌐 Vercel 網址 vs 永久路徑(2026-06-07 釐清)
- 永久路徑(磁碟):`Y:\permanent-projects\hermes-status-site` = `/home/hoonsoropenclaw/permanent-projects/hermes-status-site`
- Vercel 專案名:`raphael-status-site` (不是我剛誤以為的 `hermes-status-site`)
- Vercel 網址:`https://raphael-status-site.vercel.app/`
- **永久路徑名稱**(`hermes-status-site`)跟**Vercel 專案名稱**(`raphael-status-site`)是**兩回事**,由歷史決定(可能是建立 Vercel 專案時選錯了)
- **If** 使用者叫我「把 X 部署到 hermes-status-site」 **Then** 部署到 `raphael-status-site` Vercel 專案、別建立新專案、別用 `--yes`(會建新的)
- **If** 想驗證目前狀態 **Then** `vercel projects ls` + `vercel projects rm <name>` 才能操作
- 2026-06-07 23:20 我曾誤把 Vercel 上的 `hermes-status-site` 當成是 status site 的 Vercel 專案、用 `--yes` 自動建了 `hermes-status-site-deploy` 廢專案,後來使用者手動刪 `hermes-status-site` Vercel 專案
- **注意**:`/home/hoonsoropenclaw/hermes-status-site`(非 permanent 根目錄)還在,可能是早期 clone,不要動

---

## 🤖 Agent Reach 認證摘要（2026-06-08 確立，2026-06-09 收成索引）

- **路徑**：`~/.local/bin/agent-reach`（user-local 安裝,跟 hermes 一樣的 wrapper 模式）
- **venv**：`~/.agent-reach-venv/`（建立日 2026-06-08 21:09）
- **SKILL.md 註冊**：`~/.agents/skills/agent-reach/SKILL.md`（OpenClaw 反安裝後、`~/.openclaw/skills/` 已刪）
- **查認證狀態**：`agent-reach doctor`（v1.4.0 沒 `list` 子命令）
- **完整渠道/認證清單**：`agent-reach doctor` 即時跑、或看 `~/.agents/skills/agent-reach/SKILL.md` 17 平台說明
- **N100 出口 IP**：`118.231.136.116` / AS9674 Far EastTone（**真住宅 IP,不是 datacenter**）
- **If** 提到 agent-reach / twitter-cli / rdt-cli / headless cookies **Then** 載入 `trial-and-error/references/by-category/headless-cookie-import.md`
- **If** 提到 `~/.bash_env` / `~/.bash_profile` 互動式 return **Then** 載入 `trial-and-error/references/by-category/hermes-internal.md`「bash_profile 從 bashrc 抄 skeleton 帶互動式 return 阻擋」條目

---

## 🧭 重要檔職責分離（從 2026-06-10 SOUL.md 重寫 6 個衝突歸納, L3 抽象）

7 個重要檔是「人格系統」、各有職責、不能塞在一起：

| 檔案 | 職責 | 編輯時改 |
|------|------|---------|
| `SOUL.md` | **人格宣言**（耗盡配額、Core Truths、Vibe、行為原則） | 改根目錄那份（`~/.hermes/SOUL.md`, hermes `prompt_builder.load_soul_md()` hardcode 讀這） |
| `USER.md` | **使用者偏好**（INTJ 風格、效率優先、要求完整） | 改 `memories/USER.md` |
| `MEMORY.md` | **長期記憶**（抽象教訓 L3、決策記錄、env facts） | 改 `memories/MEMORY.md`（25KB 警戒線） |
| `AGENTS.md` | **工作區規範**（啟動程序、keyword 觸發、身份赫米斯＝拉斐爾） | 改 `memories/AGENTS.md` |
| `IDENTITY.md` | **代理身份卡**（5 大能力、使命） | 改 `memories/IDENTITY.md` |
| `TOOLS.md` | **本機環境設定**（Python uv、hermes 安裝、API 憑證） | 改 `memories/TOOLS.md` |
| `HEARTBEAT.md` | **任務清單**（兩階段記憶搜尋、系統性流程缺陷修復） | 改 `memories/HEARTBEAT.md` |

**If 改任何重要檔 Then**：
- 確認改對位置（用 `ls -la` + grep hermes 程式碼）
- 跟其他重要檔交叉比對（不要寫重複內容到不對的檔）
- 改完跑 `hermes --version` + `hermes status` 確認 hermes 仍能正常啟動

**If 任何 multi-file 同步設計 Then** 必建「INVENTORY.md single source of truth + 改檔對照表」（從 2026-06-10 備份 v4.6 升級歸納）：

- 一個檔案 = 一個 single source of truth（如 `~/.hermes/docs/INVENTORY.md`）
- 改檔對照表寫進該領域 SKILL.md 的「修改影響對照表」段（如 `agent-system-backup/SKILL.md §14.1`）
- 變更記錄寫 INVENTORY.md §「變更記錄」段
