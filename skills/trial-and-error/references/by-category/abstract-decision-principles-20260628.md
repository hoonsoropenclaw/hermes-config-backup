# 抽象決策原則（跨領域適用，2026-06-28 從 MEMORY.md 遷移）

> 遷移理由：MEMORY.md 超過 25 KB 警戒線，這 117 行純 L3 抽象原則遷移到 trial-and-error 長期積累。原位置保留摘要。

---

### 「常駐子代理」= `hermes profile + tmux`，**不是**舊 agents/ 方案（2026-06-09 確立）
- 舊方案（2026-05-31 ~ 2026-06-08）：`~/.hermes/agents/*.yaml` 身份檔 + `persistent-subagent` skill 派遣 → 已在 2026-06-09 全清（見備份策略檔歷史註記）
- 新方案（2026-06-09 起）：`hermes profile create <name> --clone` 建獨立 profile，內含 persona.md + 專屬 skill + 隔離記憶 + 可用 tmux 持久化對話
- **If** 使用者說「建一個常駐子代理」「常駐策略代理」「幫我做一個長期監控代理」**Then** 走 profile + tmux 路線，**不要**再回頭用 agents/ 身份檔方案
- **If** 使用者說「派遣 subagent」但語意是一次性任務 **Then** 走 `delegate_task`（這是不同概念，工具本身還在）
- 區分：「常駐代理」= 跨 session 持續運作的代理（profile）；「派遣 subagent」= 一次性背景任務（delegate_task，工具層）

---

### 卸載/清理前先看「這個概念現在還活著嗎」（2026-06-09 修訂）
- 看到舊 skill `persistent-subagent`、舊目錄 `~/.hermes/agents/`、舊字眼「常駐 Subagent」時，**不要憑印象保留**——先確認目前採用的方案（profile + tmux）是否已建立，再決定刪除
- 卸載/刪除前要驗證 3 件事：(1) 現有方案已可運作（不是「規劃中」）、(2) 沒有其他 skill/script 引用將被刪除的檔、(3) trial-and-error 等參考檔內的目錄清單同步更新
- **If** 卸載/清理任何跟「常駐/持久/代理架構」相關的東西 **Then** 順便 grep `~/.hermes/skills/` + `~/.hermes/memories/` + `~/.hermes/config.yaml` 確認沒有殘留引用，**不要**只刪本體就以為完成

---

### 精瘦 profile 原則：常駐代理 = 30-60 個 skill，不是 194（2026-06-09 確立）
- `hermes profile create <name> --clone` 從 default 帶 194 個 skill → 磁碟多吃 344 MB、context 被無關技能污染、代理「身份混淆」
- **精瘦後 30-60 個就夠**：自己專屬 skill（1-5 個）+ 赫米斯基礎設施（general-workflow / trial-and-error / user-collaboration-style / workspace-folder-layout / anti-panic-protocol 等）+ 角色相關的 20-30 個
- **If** 建新常駐子代理（profile + tmux 路線）**Then** clone 完成後**立即**跑「精瘦 SOP」：`hermes skills opt-out --remove --yes`（自動刪 65 個 bundled）+ Python 白名單刪除（再刪 100-130 個 user-edited/hub/local）。完整 SOP 在 `~/.hermes/skills/trial-and-error/references/sops/profile-slimming-sop.md`
- **If** 看到新常駐 profile 有 194 個 skill **Then** 表示 clone 後沒跑精瘦、馬上補跑
- **If** 驗證 skill 數量 **Then** 用 `ls ~/.hermes/profiles/<p>/skills/ | wc -l` 看磁碟，不要用 `hermes skills list`（CLI 會把子目錄也算成 enabled，數字膨脹 3-4 倍）

---

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

---

### 架構優先於速度（2026-06-04 確立）
- **反模式**：發現 bug → 找最快能跑通的方案 → 把代碼堆在同一檔案 → 後續 DEBUG 困難
- **正確模式**：遇到問題時先問「這個修改會讓系統變更複雜還是更簡單？」需要把所有東西塞同一檔案才能解決 → 停下來重新思考架構
- **三層分離原則**（適用前端）：`structure/`（純 HTML + data-*）+ `style/`（CSS）+ `logic/`（JS + JSON），每檔一責
- **If** 直覺想做「捷徑」方案 **Then** 先查記憶/對話摘要，確認沒有違反之前說過的原則

---

### 語意型 Bug 防範
- 「程式碼表面正確，瀏覽器運行時才失敗」→ 純 code review 無法發現
- **If** 前端功能不正常但 JS 函式存在 **Then** 先確認 DOM 是否已更新（用 setTimeout 或手動觸發）
- **If** SPA loadTab 後 XHR 回報 element not found **Then** 檢查 loadTab 是否在 DOM 更新後才觸發 XHR
- **預防**：部署前用 headless browser 實際執行 UI 測試

---

### 自我審查：自我報告 ≠ 驗證（2026-06-06 確立）
- 修復類任務完成前必須親自驗證 3 件事：(1) 重新觸發失敗場景看 exit code 0、(2) 外部系統狀態檢查、(3) 附上真實命令輸出
- **If** 你是 sub-agent 在寫修復報告 **Then** 自我審查必須包含 3 個親自跑過的驗證命令 + 真實輸出（不是 ✅ emoji）

---

### MEMORY 寫「X 是 Y」也要寫「怎麼驗證」(2026-06-09)
- **If** 寫進 MEMORY/AGENTS 任何「X 是 Y 裝法 / X 在 Z 路徑 / X 是 N 版本」這種**結論型事實** **Then** **必同步寫一條「怎麼驗證」**（`which X` / `npm ls -g` / `ls -la <path>` 這類一鍵指令）
- 沒有「驗證命令」的 MEMORY 紀錄**可能錯好幾個月、直到 CLI 真的爆才被發現**（本來 MEMORY 寫「N100 的 hermes 是 npm -g」結果是 user-local、錯到 2026-06-09 才修正）
- 驗證命令 = 跨 session 的「自我審查機制」、讓未來 agent / 週期性驗證腳本能主動挑出錯誤

---

### 卸載前用 `ps -o ppid=` 查「真正 owner」可顛覆整個方案（2026-06-08）
- 反安裝前猶豫「A 跟 B 哪個才是 X 的 owner」時,**`ps -o pid,ppid,cmd` 查 PPID 鏈**,不要從 config 檔讀「誰提到 X」就推論誰管
- 實例：mempalace MCP 預期是前任拉斐爾 OpenClaw 套件代理啟動,實測 PPID 是赫米斯主進程 → OpenClaw 死了 mempalace 也不受影響 → 整個「卸載前要改 hermes MCP 設定加 env var」的方案變成不需要
- **If** 卸載前要評估 X 服務的連帶影響 **Then** `ps -ef | grep X` + `ps -o pid,ppid,cmd` 驗證 X 的真正 parent 是誰,再決定要備份/轉移/重啟誰

---

### 卸載任何東西前必先 `--dry-run` 或 list target（2026-06-08）
- **`openclaw uninstall --all --dry-run`** 會列印「remove gateway service / remove ~/.openclaw / remove ~/.openclaw/workspace」三個動作,實測真的會動這些
- **If** 卸載指令有 `--dry-run` flag **Then** 必先跑確認會動什麼,不要直接看 help 就下指令
- **If** 卸載指令沒 `--dry-run` **Then** 至少先 `which X` + `readlink -f $(which X)` + `dpkg -L X | head` 知道會被動到哪些檔
- 套件卸載後看到 systemd `not-found inactive dead` 但 unit 檔還在 = **套件卸載 bug,手動清**（`rm -f unit 檔` + `daemon-reload` + `reset-failed`）

---

### 「單靠本地金鑰不算備份」(2026-06-10,從 v4.5 雙層 GPG 加密修補歸納)
- **情境**:v4.0 ~ v4.4 把 .env / auth.json / state.db 用 GPG 加密成 `secrets-bundle-*.tar.gpg` 推到 Drive,金鑰是本地 `~/Documents/hermes-keys/.hermes_backup_passphrase`。**但 passphrase 檔從未備份**——N100 硬碟壞掉時,130MB 加密檔**完全無法解開**
- **If** 設計任何「加密檔推雲端、金鑰留本地」的架構 **Then** 必加 **第二層離線副本**:金鑰也加密備份到雲端獨立目錄(或實體離線媒介),金鑰的金鑰(USER_KEY)由使用者記憶
- 推廣:**任何 backup 設計,recovery chain 必須形成迴路——每一層都必須有「不在同一個 failure domain」的副本**

---

### 「備份腳本要同步過濾『同形但不同位置』的目錄」(2026-06-10,從 v4.2 4 修補歸納)
- **情境**:v4 rsync 用 `~/.hermes/skills/` 排除清單保護 `.curator_backups/` 不進 staging,**但** 沒想到 `~/.hermes/profiles/*/skills/.curator_backups/` 也有這個目錄,結果 125MB `skills.tar.gz` 透過 profiles 漏進 git history、push 卡 95%
- **If** 寫 rsync 排除清單 **Then** **所有「同形子目錄」都要列**:不只是 `skills/.curator_backups/`,還要 `profiles/*/skills/.curator_backups/`
- 推廣:**rsync 的 `--exclude` 不支援 glob 跨層級**——`*/skills/.curator_backups/` 也不會匹配,必須明確列每個路徑,**或** 用 `--max-size=50m` 從大小端加一層保險

---

### 「修改影響對照表」要寫進技能才算閉環(2026-06-10,從備份 v4.5 完整化歸納)
- **情境**:這次從 v4.1 升 v4.5 過程中,使用者反覆問「改 X 會不會漏改 Y」,赫米斯每次回答都要先 `grep` 全工作區,容易漏。**解法**:把「改 X 必同步改 A/B/C/D」直接寫進技能 SKILL.md §14,未來 AI 載入技能時自動看到
- **If** 設計任何「跨多個檔案/多個 SOP 的技能」**Then** 必含「修改影響對照表」段:
  - 「改這個檔 → 必同步改那幾個檔」清單
  - 對應的驗證命令(語法檢查、push 測試、grep 驗證)
  - 「常見遺漏」警示(過去踩過的坑)
- **If** 還原說明檔要給「未來 AI」看 **Then** 必含 7 個元素(架構圖、預期輸出、決策樹、debug 對照表、FAQ、驗證清單、自動化驗證 script)
- 推廣:**技能的「完整性」= 設計意圖 + 流程 SOP + 修改影響對照 + 驗證方式 + 還原說明 5 段都寫進去**——不是只寫「怎麼做」也要寫「改了會影響什麼」跟「給接手者看」

---

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

---

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
