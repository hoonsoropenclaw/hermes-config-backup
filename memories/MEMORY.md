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

> **清理原則**（2026-06-06 修訂）：本檔只放**跨 session 仍有用的抽象知識**。
> - ✅ 留：高層架構、環境事實、穩定決策原則、If→Then 抽象規則
> - 📦 移：具體工具試誤條目 → `trial-and-error` skill 的 `references/by-category/`
> - 🗑️ 刪：任務進度、commit/PR 編號、單次 session 結果、過時技術細節（用 `session_search` 撈）

## 🗓️ 更新記錄（只留近 3 條，歷史可從 session_search/git 撈）
- 2026-06-10: **market-strategist 身份重塑為 consumer-researcher**（使用者觀察:實際專案瓶頸是「消費者需求 + 標竿功能盤點」不是市場分析）。重建 profile、砍 192→41 個 skill、改 persona 跟 SOUL、新建 web-worker-template / summarizer-worker-template、修正 v1/v2/v2 修正版三方比對 → 見 `~/shared-infra/CONSUMER_RESEARCHER_V2_ARCHITECTURE_REPORT.md` + `CONSUMER_RESEARCHER_CONVERSION_v1_REPORT.md`
- 2026-06-10: **v2 Orchestrator + Worker 平行架構設計與驗證**——主 session 不跑 web 抓取、改派 `hermes chat -q ... --cli` 獨立 hermes session(context 完全隔離)+ summarizer 整合。**v2 原始版漏 SkillSwap.io + 換 Persona**,**v2 修正版**(必抓清單 + _plan.md 保留使用者原意 Persona)涵蓋完整。L3 教訓:「LLM sub-agent 是無狀態的、必抓清單 + _plan.md 是 Orchestrator 跟 sub-agent 的介面契約」
- 2026-06-10: **notify_on_complete 通知延遲 10-14 分鐘是常態**——v2 架構派 4 worker + 1 summarizer,實際 11 分鐘跑完但通知 10-14 分鐘才送達。L3 教訓:「Hermes 通知是『最終確認』不是『即時 polling』,用 `ls <output_dir>` 撈實際產出比等通知更可靠」。**If** 派 background process **Then** 主動用 ls 監聽、不依賴 notify

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

## 🧭 抽象決策原則（跨領域適用）

### 「常駐子代理」= `hermes profile + tmux`，**不是**舊 agents/ 方案（2026-06-09 確立）
- 舊方案（2026-05-31 ~ 2026-06-08）：`~/.hermes/agents/*.yaml` 身份檔 + `persistent-subagent` skill 派遣 → 已在 2026-06-09 全清（見備份策略檔歷史註記）
- 新方案（2026-06-09 起）：`hermes profile create <name> --clone` 建獨立 profile，內含 persona.md + 專屬 skill + 隔離記憶 + 可用 tmux 持久化對話
- **If** 使用者說「建一個常駐子代理」「常駐策略代理」「幫我做一個長期監控代理」**Then** 走 profile + tmux 路線，**不要**再回頭用 agents/ 身份檔方案
- **If** 使用者說「派遣 subagent」但語意是一次性任務 **Then** 走 `delegate_task`（這是不同概念，工具本身還在）
- 區分：「常駐代理」= 跨 session 持續運作的代理（profile）；「派遣 subagent」= 一次性背景任務（delegate_task，工具層）

### 卸載/清理前先看「這個概念現在還活著嗎」（2026-06-09 修訂）
- 看到舊 skill `persistent-subagent`、舊目錄 `~/.hermes/agents/`、舊字眼「常駐 Subagent」時，**不要憑印象保留**——先確認目前採用的方案（profile + tmux）是否已建立，再決定刪除
- 卸載/刪除前要驗證 3 件事：(1) 現有方案已可運作（不是「規劃中」）、(2) 沒有其他 skill/script 引用將被刪除的檔、(3) trial-and-error 等參考檔內的目錄清單同步更新
- **If** 卸載/清理任何跟「常駐/持久/代理架構」相關的東西 **Then** 順便 grep `~/.hermes/skills/` + `~/.hermes/memories/` + `~/.hermes/config.yaml` 確認沒有殘留引用，**不要**只刪本體就以為完成

### 精瘦 profile 原則：常駐代理 = 30-60 個 skill，不是 194（2026-06-09 確立）
- `hermes profile create <name> --clone` 從 default 帶 194 個 skill → 磁碟多吃 344 MB、context 被無關技能污染、代理「身份混淆」
- **精瘦後 30-60 個就夠**：自己專屬 skill（1-5 個）+ 赫米斯基礎設施（general-workflow / trial-and-error / user-collaboration-style / workspace-folder-layout / anti-panic-protocol 等）+ 角色相關的 20-30 個
- **If** 建新常駐子代理（profile + tmux 路線）**Then** clone 完成後**立即**跑「精瘦 SOP」：`hermes skills opt-out --remove --yes`（自動刪 65 個 bundled）+ Python 白名單刪除（再刪 100-130 個 user-edited/hub/local）。完整 SOP 在 `~/.hermes/skills/trial-and-error/references/sops/profile-slimming-sop.md`
- **If** 看到新常駐 profile 有 194 個 skill **Then** 表示 clone 後沒跑精瘦、馬上補跑
- **If** 驗證 skill 數量 **Then** 用 `ls ~/.hermes/profiles/<p>/skills/ | wc -l` 看磁碟，不要用 `hermes skills list`（CLI 會把子目錄也算成 enabled，數字膨脹 3-4 倍）

### 跨 profile handoff pipeline（我當 orchestrator，2026-06-09 確立）
- 觸發：使用者說「走 handoff 流程」或交辦明確多階段、需要角色分工的任務。**不是全自動**——交辦時我就要在視線下跑 N 次工具呼叫（**N = 鏈上代理數**，由任務動態決定）
- 流程（**核心 SOP**，由 default 我手動串，**鏈長動態不寫死**）：
  1. **解析任務 → 決定代理鏈**（讀使用者訊息、對應到現有常駐代理 `hermes profile list`、缺哪個提示先建）
  2. `terminal` 依序跑每段代理：`terminal(command="<wrapper> chat -q \"請做 <這段任務>...\" --cli", timeout=600)`（用 wrapper 不用 `hermes -p`、加 `--cli` non-interactive 模式）
  3. `terminal` 撈最新一筆 session 報告、寫到 `~/.hermes/handoff/<project-slug>/<這段產出>.md`
  4. 對下段代理重複 2-3，直到鏈尾
  5. 撈最終產出給使用者看
- **檔案串接介面**：`~/.hermes/handoff/<project-slug>/`（`market-research.md` → `prd.md` → `code.md` → ... 視鏈長動態）
- 兩個 agent 之間**不互通**（profile 記憶隔離是設計）——我（default）是唯一的 orchestrator/串接者
- **If** 使用者沒明確說「走 handoff」**Then** 預設**不**自動串——只在主 session 處理（避免濫用工具呼叫、避免 context 爆）
- **If** 使用者丟的任務**只要**某段（例：只要市場調研、不要 PRD）**Then** 鏈長自動縮短、停在該段產出
- **未來改用 tmux 持久化**：目前 `chat -q --cli` 是 foreground、跑完就退；改用 `tmux new-session -d -s <name> '<wrapper> chat ...'` 可以背景跑、但要等 session 結束才能撈報告（複雜度+1，**現在不建議**）
- wrapper 已備好：`~/.local/bin/market-strategist` / `~/.local/bin/product-planner`（新增常駐代理時也照 SOP `hermes profile create <name> --clone` + 自動建 wrapper `/usr/local/bin/<name>`）

### 架構優先於速度（2026-06-04 確立）
- **反模式**：發現 bug → 找最快能跑通的方案 → 把代碼堆在同一檔案 → 後續 DEBUG 困難
- **正確模式**：遇到問題時先問「這個修改會讓系統變更複雜還是更簡單？」需要把所有東西塞同一檔案才能解決 → 停下來重新思考架構
- **三層分離原則**（適用前端）：`structure/`（純 HTML + data-*）+ `style/`（CSS）+ `logic/`（JS + JSON），每檔一責
- **If** 直覺想做「捷徑」方案 **Then** 先查記憶/對話摘要，確認沒有違反之前說過的原則

### 語意型 Bug 防範
- 「程式碼表面正確，瀏覽器運行時才失敗」→ 純 code review 無法發現
- **If** 前端功能不正常但 JS 函式存在 **Then** 先確認 DOM 是否已更新（用 setTimeout 或手動觸發）
- **If** SPA loadTab 後 XHR 回報 element not found **Then** 檢查 loadTab 是否在 DOM 更新後才觸發 XHR
- **預防**：部署前用 headless browser 實際執行 UI 測試

### 自我審查：自我報告 ≠ 驗證（2026-06-06 確立）
- 修復類任務完成前必須親自驗證 3 件事：(1) 重新觸發失敗場景看 exit code 0、(2) 外部系統狀態檢查、(3) 附上真實命令輸出
- **If** 你是 sub-agent 在寫修復報告 **Then** 自我審查必須包含 3 個親自跑過的驗證命令 + 真實輸出（不是 ✅ emoji）

### MEMORY 寫「X 是 Y」也要寫「怎麼驗證」(2026-06-09)
- **If** 寫進 MEMORY/AGENTS 任何「X 是 Y 裝法 / X 在 Z 路徑 / X 是 N 版本」這種**結論型事實** **Then** **必同步寫一條「怎麼驗證」**（`which X` / `npm ls -g` / `ls -la <path>` 這類一鍵指令）
- 沒有「驗證命令」的 MEMORY 紀錄**可能錯好幾個月、直到 CLI 真的爆才被發現**（本來 MEMORY 寫「N100 的 hermes 是 npm -g」結果是 user-local、錯到 2026-06-09 才修正）
- 驗證命令 = 跨 session 的「自我審查機制」、讓未來 agent / 週期性驗證腳本能主動挑出錯誤

### 卸載前用 `ps -o ppid=` 查「真正 owner」可顛覆整個方案（2026-06-08）
- 反安裝前猶豫「A 跟 B 哪個才是 X 的 owner」時,**`ps -o pid,ppid,cmd` 查 PPID 鏈**,不要從 config 檔讀「誰提到 X」就推論誰管
- 實例：mempalace MCP 預期是前任拉斐爾 OpenClaw 套件代理啟動,實測 PPID 是赫米斯主進程 → OpenClaw 死了 mempalace 也不受影響 → 整個「卸載前要改 hermes MCP 設定加 env var」的方案變成不需要
- **If** 卸載前要評估 X 服務的連帶影響 **Then** `ps -ef | grep X` + `ps -o pid,ppid,cmd` 驗證 X 的真正 parent 是誰,再決定要備份/轉移/重啟誰

### 卸載任何東西前必先 `--dry-run` 或 list target（2026-06-08）
- **`openclaw uninstall --all --dry-run`** 會列印「remove gateway service / remove ~/.openclaw / remove ~/.openclaw/workspace」三個動作,實測真的會動這些
- **If** 卸載指令有 `--dry-run` flag **Then** 必先跑確認會動什麼,不要直接看 help 就下指令
- **If** 卸載指令沒 `--dry-run` **Then** 至少先 `which X` + `readlink -f $(which X)` + `dpkg -L X | head` 知道會被動到哪些檔
- 套件卸載後看到 systemd `not-found inactive dead` 但 unit 檔還在 = **套件卸載 bug,手動清**（`rm -f unit 檔` + `daemon-reload` + `reset-failed`）

### LLM sub-agent 是無狀態的——必抓清單 + _plan.md 是 Orchestrator 跟 sub-agent 的介面契約（2026-06-10）
- 觀察:Orchestrator + Worker 平行架構跑 4 個 web-worker + 1 個 summarizer,summarizer **自動從 _raw/ 歸納 Persona** 換掉 v1 推測的「跨國」「退休族」客群,並**漏掉 SkillSwap.io**(v1 有、v2 原始漏)
- 根因:LLM sub-agent 看到 prompt 只看 prompt 內列的內容、**不會主動繼承 Orchestrator 還沒寫進 prompt 的「使用者原意」**,也不會主動補抓 prompt 沒列的「必抓清單」
- 解法(雙保險):
  1. **web-worker-template 加「必抓清單」段** — 即使 prompt 沒列、必抓清單有,worker 主動 web_search 補抓
  2. **summarizer-worker-template 加「讀 _plan.md」步驟** — summarizer 第一步先讀 Orchestrator 寫的 _plan.md,保留 Orchestrator 指定的 Persona 跟必抓清單
  3. **Orchestrator persona 加「保留使用者原意 Persona」段** — _plan.md 必填,即使 _raw/ 抓不到對應評論也要保留 Persona 框架
- **If** 設計任何 Orchestrator + sub-agent 架構 **Then** 必規劃「資訊傳遞契約」(例:_plan.md、_intermediate/、_raw/),sub-agent 不會繼承 Orchestrator 的 context
- **If** v2 架構跑出來跟 v1 比對發現內容缺漏 **Then** 檢查 web-worker prompt 有無「必抓清單」+ summarizer 有無讀 _plan.md,不要直接判定 v2 失敗
- 驗證:2026-06-10 v2 修正版涵蓋 SkillSwap.io + 保留 3 個 v1 使用者原意 Persona(小美/佐藤/陳媽媽)+ 新增 2 個 _raw/ 歸納 Persona(阿哲/Lily),共 5 個 Persona

### notify_on_complete 是「最終確認」不是「即時 polling」(2026-06-10)
- 觀察:派 4 worker + 1 summarizer(2026-06-10 11:43 啟動、11:51 全部寫入完成),但 Hermes 的「Background process completed」通知在 12:00~12:01 才陸續送達,**延遲 10-18 分鐘**
- 根因(推測):Hermes gateway 通知機制可能是批次輪詢(不是 process exit 立即觸發),或某個 background hook 在固定週期才掃描
- 解法:**不要**把 `notify_on_complete=true` 當 polling 機制。實際工作流:
  1. 派遣時**同時**用 `ls <output_dir>` 主動監聽(不等通知)
  2. notify 來時**確認**產出真的存在(用 `wc -c`、`find` 驗證)
  3. notify 延遲 10-14 分鐘是常態,看到延遲**不要慌**
- exit code 解讀(2026-06-08 既有):
  - 0 = 正常結束
  - 124 = timeout(terminal 預設 600s)
  - 143 = SIGTERM(我手動 kill 或 hermes 正常 lifecycle,**常見**)
  - 130 = SIGINT(Ctrl+C)
  - 137 = SIGKILL(OOM 或強制)
- **If** 派 background process **Then** 主動用 `ls` 監聽、不依賴 notify
- **If** 想知道某 worker 是否還在跑 **Then** `ps -ef | grep "hermes chat" | grep -v grep` 看 pid
- 驗證:2026-06-10 11:43 派遣 4 worker、11:51 全部 _raw/ 寫入完成,延遲 10-18 分鐘後才陸續收到 notify,但工作流沒被通知延遲影響(主動 `ls` 確認產出)

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
