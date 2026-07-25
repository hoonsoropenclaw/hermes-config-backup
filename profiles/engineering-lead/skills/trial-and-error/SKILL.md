---
name: trial-and-error
description: "赫米斯踩過的坑目錄 — **MUST LOAD BEFORE EXECUTION**。當使用者交辦任何執行類任務或赫米斯即將對系統做變更時,必須**第一時間** `skill_view` 這個 skill,看有沒有踩過的雷。**HARD TRIGGER 詞**(命中任一必須載入):vercel / deploy / Vercel / CDN / cloudflare / git push / filter-branch / BFG / GH013 / GH001 / force push / large file / GPG / gpg / encrypt / decrypt / 簽章 / passphrase / rclone / Drive / 備份 / backup / purge / crypt / token / .env / API key / process.env / execute_code / python3.12 / pip install / uv venv / uv pip / pyproject.toml / hatchling / wheel / editable install / subprocess / sandbox / browser / playwright / headless / camofox / for f in / 2>&1 / pipefail / set -e / hermes cron / hermes status / config / gateway / **openclaw / uninstall / 反安裝 / cookies / Cookie-Editor / twitter-cli / rdt-cli / yt-dlp / X.json / reddit.json / patch / write_file / fuzzy / cascade / SKILL.md / MEMORY.md / AGENTS.md / cross_profile**。**判斷性問題**也必須查(使用者問「X 可以不備嗎」「X 是 Y 還是 Z」「X 真的能砍嗎」時不要憑印象答)。**懲罰**:跳過載入 = 使用者事後審查發現 = 信任扣分。"
version: 1.2.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
---

### session_search MCP Tool 不可用的備援程序（2026-06-09）
**症狀**: `session_search` 呼叫時收到「Tool not found」或「Skill not found」
**根因**: session_search 是 MCP 工具，非核心依賴，可能被標記為 `skipped` 或根本未啟用
**觸發情境**: metacognitive-learner 每 2 小時啟動，Phase 1 需要搜尋最近 10 個 session

**備援路徑**（按順序）：
1. 直接搜尋 `~/.hermes/memories/*.md`（`read_file` + `search_files`）
2. 搜尋 `~/.hermes/skills/` 目錄結構
3. 讀取 `HEARTBEAT.md`、`MEMORY.md`、`USER.md` 等核心記憶檔案
4. 搜尋 `~/.hermes/cron/jobs.json` 了解排程任務模式
5. 若仍無足夠線索，搜尋 `~/.hermes/sessions/sessions.json`（會話索引）

**驗證命令**：
```bash
hermes cron list 2>&1 | head -20  # 基本系統狀態
ls ~/.hermes/memories/            # 記憶檔案存在
wc -l ~/.hermes/memories/MEMORY.md  # 確認可讀
```

**If→Then**: **If** session_search 工具呼叫失敗 **Then** 立即切換備援路徑，不要中斷學習流程

> **不要在這裡塞踩雷條目** — 完整條目依分類放在 `references/by-category/`。
> 本檔只放「怎麼用這個 skill」的入口。

## 何時使用

**觸發條件**（任一符合即觸發）:

- 任何涉及 gpg / gh CLI / Vercel / Python sandbox / 加密 / token / 部署 / 認證 / 權限 / **rclone / Drive / GitHub** / bash script / cron / 異機還原的任務
- 使用者明確說「這以前踩過」「為什麼又壞了」「上次怎麼解的」時
- hermes CLI / gateway / config / cron jobs 內部行為問題
- **使用者問判斷性問題**（「X 可以不備嗎」「X 是 rebuild 還是 cache」「X 真的可以砍掉嗎」）— 先看 `hermes-backup-design-pitfalls#Rule 12`（rebuild 判斷要先查）

### 🚨 強制載入 SOP（2026-06-07 新增,根據使用者回饋）

**觸發檢查點**（每個任務第一個 tool call 之前**必須**完成）:

1. **掃使用者訊息** 是否有 HARD TRIGGER 詞（vercel / git push / GPG / rclone / token / execute_code / bash script / cron / browser / hermes CLI）
2. **命中任一** → 立即 `skill_view(name='trial-and-error', file_path='references/by-category/<分類>.md')` 載入對應分類
3. **判斷性問題**（使用者問「X 可以不備嗎」「X 是 Y 還是 Z」）→ 必查 `hermes-backup-design-pitfalls.md` Rule 12
4. 載入完成後才開始第一個 tool call（patch / write_file / terminal / execute_code）

### 新增條目 SOP（2026-06-09 從 `@學習` 觸發場景歸納）

**觸發情境**:
- 使用者說「`@學習`」/「把這次當 SOP 存起來」/「這個以後會用到」
- metacognitive-learner cycle 結束時 Phase 4 分流到 L3 隔離
- 任何 `write_file` 寫進 `references/by-category/*.md` 之前

**4 步流程**:
1. **掃對話** → 列候選條目
2. **去重** → 跑 `search_files` FTS5 找相似概念
3. **判斷層級** → L2 寫 references/、L3 寫 MEMORY.md
4. **驗證寫入** → `grep`/`wc`/`bash -c` 必跑

**完整版（含判斷範例、常見錯誤、決策樹）** → 見 **`references/adding-entries-sop.md`**

**If→Then 規則**:
- **If** 要串接多個常駐代理形成 chain **Then** 用 bash wrapper script + `hermes -p <profile> chat --cli --no-input` 模式（見 `hermes-resident-agent/references/chain-automation.md`）
- **If** 訊息含 vercel / deploy / CDN / github pages 任一字 **Then** 必載入 `vercel-deployment.md`
- **If** 訊息含 git push / GH013 / filter-branch 任一字 **Then** 必載入 `gh-cli-and-github.md`
- **If** 訊息含 patch / write_file / edit / fuzzy / cascade 任一字 **Then** 必載入 `references/execution-sop.md` SOP-5（patch 工具防 cascade damage SOP）——**這條 2026-06-09 親身踩到、SOP-5 早就存在但這次沒主動載入**
- **If** 訊息含 SKILL.md / MEMORY.md / AGENTS.md / cross_profile 任一字 **Then** 必載入 `references/execution-sop.md` SOP-5 + SOP-6（patch + 跨 profile soft-guard 兩條 SOP）
- **If** 使用者訊息含 GPG / encrypt / 簽章 任一字 **Then** 必載入 `gpg-encryption.md`
- **If** 使用者訊息含 rclone / Drive / 備份 任一字 **Then** 必載入 `hermes-backup-strategy.md` + `hermes-backup-design-pitfalls.md`
- **If** 使用者訊息含 token / .env / API key 任一字 **Then** 必載入 `secrets-and-env.md`
- **If** 使用者訊息含 pip install / uv venv / uv pip / pyproject.toml / hatchling / editable install 任一字 **Then** 必載入 `python-sandbox.md`(uv venv 無 pip、force-include 衝突、editable fallback)
- **If** 使用者訊息含 cookies / Cookie-Editor / X.json / reddit.json / twitter-cli / rdt-cli / yt-dlp / agent-reach 任一字 **Then** 必載入 `headless-cookie-import.md`(N100 headless 平台 CLI 認證通用 SOP)
- **If** 判斷性問題（「X 可以不備嗎」「X 是 Y 還是 Z」「X 真的能砍嗎」）**Then** 必載入 `hermes-backup-design-pitfalls.md` Rule 12
- **If** 赫米斯在第 5 個 tool call 內遇到「看起來以前踩過的雷」症狀 **Then** 立即停止、回頭載入 trial-and-error、不是繼續 debug

**為什麼需要這條**（2026-06-07 案例）:
使用者交付「hermes-cli-reference 網站搜尋『更新』沒結果」任務,赫米斯直接開始 patch + deploy + 驗證,結果在第 15 個 tool call 才發現 git reflog 沒有那個 commit（其實是 LLM hallucination 成功 SHA）。**如果一開始就 `skill_view(vercel-deployment.md)`,會看到「部署成功 200 ≠ 使用者打得開」、「.env 是 token 唯一可靠來源」等條目,提早發現問題**。使用者審查後明確要求:赫米斯必須**強制主動撈 trial-and-error**,不要等出事了才撈。

**已知分類**（2026-06-07 更新）:

- `hermes-internal` — hermes CLI / gateway / cron jobs / config / skill 機制的坑
- `gpg-encryption` — GPG 加密 / 簽章 / key 管理
- `gh-cli-and-github` — gh CLI / GitHub API / 雙帳號 / token / **GH013 / GH001 / filter-branch**
- `vercel-deployment` — Vercel CLI / API / 部署 / env 變數
- `python-sandbox` — Python sandbox / token 字串遮罩 / 程式碼寫法 / **uv venv 無 pip / pyproject force-include 衝突 / venv CLI PATH 不可見 / yt-dlp JS runtime**
- `headless-cookie-import` — **N100 headless 把 Cookie-Editor JSON 餵給 X/Reddit/小紅書/微博/雪球 CLI 的完整 SOP**（twitter-cli 用 env、rdt-cli 用 credential.json、yt-dlp 用 Netscape 檔、agent-reach 內建 configure 直接吃 cookie header）
- `secrets-and-env` — .env / 憑證管理 / GPG 加密佈局
- `browser-automation` — Playwright / headless browser / 反檢測
- `bash-defensive-patterns` — Bash 函式 stdout 污染、for+2>/dev/null 語法、array+regex、**2>&1 | grep 吞 exit code**、**set -o pipefail + head -1 對空 grep 觸發 silent exit**
- `hermes-backup-strategy` — 備份架構演進（v1 → v2 → v3 → **v4.1 雙雲端** → **v4.2 明文 Drive**）
- `hermes-backup-design-pitfalls` — 備份設計盲點（**Rule 8-15**：Drive 配額、rebuild 判斷、rclone purge、偽 mkdir、偽 .gpg 目錄）
- `hermes-backup-sop` — 備份執行 SOP
- `hermes-config-tuning` — model / provider / **wakeAgent gate 控制 cron silent/not**

## 最近新增條目（2026-06-07 v3 → v4 → v4.1 演進；2026-06-08 agent-reach 完整啟用）

### headless-cookie-import（2026-06-08 新分類）
N100 headless 把 Cookie-Editor JSON 餵給各平台 CLI 的通用 SOP。涵蓋：
- **Twitter/X** (twitter-cli 用 `TWITTER_AUTH_TOKEN` + `TWITTER_CT0` 環境變數 → 寫進獨立 `~/.bash_env` 避免 bash_profile 互動式 return 阻擋)
- **Reddit** (rdt-cli 用 `~/.config/rdt-cli/credential.json` JSON 檔 → 必含 `reddit_session` + 建議含 `token_v2` → N100 沒瀏覽器所以 `rdt login` 失敗、要手動寫)
- **YouTube** (yt-dlp 用 Netscape cookie 檔 → `#HttpOnly_` prefix 容易被忽略)
- **小紅書 / 微博 / 雪球** (走 `agent-reach configure <platform>-cookies "header string"`)
- 完整「N100 平台 CLI 認證通用 SOP」流程 + 平台對照表 + 通用 If→Then 規則

### python-sandbox
- 2026-06-08 大幅擴充（從 6 → 9 條）：
  - **`force-include` 衝突 → editable install fallback**（hatchling wheel 失敗 SOP）
  - **venv CLI PATH 不可見 → `~/.local/bin` symlink 是標準解**（為何不用 pipx 自動處理）
  - **yt-dlp `--js-runtimes node` 是 2026+ 最小配置**（配 EJS 處理更難 challenge）
  - **`uv venv` 預設不含 `pip`**（要 `uv pip install --python <path> pip` 才會有）
  - **N100 出口 IP 是真住宅 IP（遠傳 ADSL）但 YouTube 仍 429**（AS-level 黑名單的概念 + Webshare 是最便宜的乾淨解）
  - **`execute_code` sanitization 連 patch 工具都觸發**（寫 token 用 f-string 會被靜默替換成 `***`、Python 還不報錯）

### hermes-internal
- **2026-06-10 新增**：Scheduler `_get_script_timeout()` 的四層優先級（HERMES_CRON_SCRIPT_TIMEOUT env > config.yaml cron.script_timeout_seconds > jobs.json timeout_seconds 是無效的）— 這解釋了為何 jobs.json 設 3600 但仍 timeout after 600s。**If** 要修復 cron script timeout **Then** 改 `.env` + `config.yaml`，jobs.json 的 `timeout_seconds` 無法覆蓋 Scheduler 的 timeout
- **2026-06-10 新增**：**跨 profile handoff pipeline context 累積風險**（@專案 派 consumer-researcher 跑 30+ 消費者聲音、10 分鐘後 context 108K、LLM 進入 5 分鐘 thinking loop 無新 log）。**If** `@專案` 派代理跑高資料量任務 **Then** 必用 `terminal(background=true, notify_on_complete=true)` + 主動 monitor log;5 分鐘沒新 API call 且 in_tokens > 100K **Then** 立即 kill + default 接手（保留已抓 URL、從 log 撈 chars 累計、不要浪費已花的成本）。詳見 `references/sops/keyword-triggers-sop.md`「Context 累積風險」段

### hermes-backup-strategy
- v4.2 明文 Drive + client-side GPG（響應 rclone crypt 不實用）
- v4.1 修正：state.db 跟 hermes-agent 分類重新檢視
- v4 雙雲端演進：從 v3.0 半成品到 v4 雙雲端

### hermes-backup-design-pitfalls
- [[hermes-backup-design-pitfalls#Rule 15：`rclone mkdir ... 2>/dev/null || true` 偽成功 + Drive 上 .gpg 顯示成「偽目錄」陷阱]]
- [[hermes-backup-design-pitfalls#Rule 14：`rclone purge <remote>:` = 砍整個 remote 內容到垃圾桶（不是清垃圾桶）]]
- [[hermes-backup-design-pitfalls#Rule 13：rclone crypt 對大檔（>50 MB）加密是反模式]]
- [[hermes-backup-design-pitfalls#Rule 12：對任何資料備份前，**先查能不能 rebuild**（不要憑印象答）]]
- [[hermes-backup-design-pitfalls#Rule 11：v4 備份腳本**完全漏掉 skills/ 同步**、剛加的條目沒進 GitHub（2026-06-07 踩到）]]
- [[hermes-backup-design-pitfalls#Rule 10：「先查上游、不要假設本地是 source of truth」— sparc-methodology 是 upstream clone 不是本地維護]]
- [[hermes-backup-design-pitfalls#Rule 9：備份檔不該被備份（備份悖論）]]
- [[hermes-backup-design-pitfalls#Rule 8：Drive API 配額 840K/分鐘/專案、13,611 小檔必爆（從 stderr 拿到 Google 官方配額數字）]]

### gh-cli-and-github
- [[gh-cli-and-github#GH001 Large files > 100MB + filter-branch 從歷史移除的陷阱（2026-06-07 踩到）]]
- [[gh-cli-and-github#GH013 push protection 觸發時的完整修復 SOP（2026-06-07 第二次踩到）]]
- [[gh-cli-and-github#`gh repo create --source=. --push` 要求目錄已是 git repo + 至少一次 commit]]
- [[gh-cli-and-github#`vercel whoami` 跟 `gh auth status` 顯示的帳號可能不同 — 兩者不互通]]
- [[gh-cli-and-github#gh auth status 顯示 Failed 但 GH_TOKEN 環境變數仍可走 API]]
- [[gh-cli-and-github#gh CLI 對缺 read:org scope 的 token 會拒絕 auth login --with-token]]

### bash-defensive-patterns
- [[bash-defensive-patterns#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]]
- [[bash-defensive-patterns#bash `[[ "$array[@]" "regex" =~ "pattern" ]]` 在 array expansion + regex 比對會炸]]
- [[bash-defensive-patterns#bash `for f in glob 2>/dev/null` 在 for 結構內不支援 stderr 重導]]
- [[bash-defensive-patterns#Bash 函式內 echo 會被當成回傳值汙染 $(func) 結果]]

### hermes-config-tuning
- v4.1 完整敘述（Rule 11：v3 限制催生 v4 雙雲端）
- wakeAgent=false gate 控制 cron 腳本 stdout 是不是 silent

### hermes-internal
- **`hermes profile create --clone` 會從 default 帶全部 skill（~194 個），常駐代理需要 30-60 個就夠（2026-06-09）**：--clone 的副作用：1) 磁碟多吃 344 MB、2) context 會被無關技能污染、3) 代理可能試著用跟自己角色無關的技能而「身份混淆」。**修法**：`hermes skills opt-out --remove --yes`（自動刪 65 個 bundled） + Python 跑白名單精準刪（保留 50-60 個）。**完整 SOP 見 `references/sops/profile-slimming-sop.md`**。**If** 建新常駐子代理（profile + tmux 路線）**Then** clone 完成後**立即**跑這個 SOP，**不要**直接交付「建好可用」狀態
- **`hermes skills list` 數字跟磁碟 `ls` 數字不一致（2026-06-09）**：CLI 把 skill 子目錄裡的 `references/`、`scripts/` 也算成「enabled」，所以 CLI 報 638、磁碟實際只有 194。**If** 確認 profile 內 skill 數量 **Then** 用 `ls ~/.hermes/profiles/<p>/skills/ | wc -l` 看磁碟為準，不要信 CLI 數字
- **精瘦 profile 的 keep-list 行尾加註解會讓 `comm` match 0 個（2026-06-10）**：寫 keep 清單時為了好讀加 `# 客戶/消費者研究方法論` 這種行尾註解，導致 `comm -12` 比對時 `anthropic-customer-research   # ...` 跟 `anthropic-customer-research` 視為不同字串、比對 0 match、要砍全部 194 個。**修法**：`awk '{print $1}'` 取第一個欄位；或註解放獨立 `# 開頭` 行不要放行尾。**If** 精瘦 profile 後 `comm -12` 顯示 0 match 但 keep.txt 內明明有該 skill **Then** 檢查行尾註解、`awk '{print $1}'` 處理
- **`hermes profile delete` 需要 PTY 餵確認字串，普通 stdin 會被視為 cancel（2026-06-10）**：`hermes profile delete <name>` 提示「Type '<name>' to confirm:」時，普通 `echo "<name>" | hermes ...` 餵 stdin → 直接「Cancelled.」退出。`hermes` 用 `input()` 讀確認字串、pipe 模式 stdin 被視為 EOF。**修法**：用 `pty=true` 餵，或在 python/expect 內送。**If** 跑 hermes 互動式 CLI(`profile delete`、`setup`、`install`)需要餵確認字串 **Then** 用 `pty=true`、不要用普通 stdin
- **hermes curator 會自動把刪掉的 bundled skill 補回來（2026-06-10）**：精瘦後 skill 數從 194 → 41，過幾分鐘磁碟上又變回 54，多 13 個。**根因**：curator 背景 cron 比對 `~/.hermes/profiles/<name>/skills/.bundled_manifest` 跟磁碟、缺了自動補回。**三選一**：接受 + 每次驗證前再砍、`hermes skills opt-out` 逐個 opt-out、改 `config.yaml` 加 `curator.enabled: false`（未驗證副作用）。**If** 精瘦 profile 是為了「永久精瘦」**Then** 用 opt-out；**If** 是「暫時省磁碟」**Then** 接受 curator 補回
- **身份重塑 ≠ 身份繼承（2026-06-10 L3 抽象教訓）**：身份繼承是「前任死了、新代理接名字」、身份重塑是「現有代理要 pivot」。差異：繼承要 7 份重要檔案同步、重塑要 profile + skill 庫 + handoff + 下游 4 個層面同步。**If** 接到「重塑代理 / 重新定位 / 換個角色」類任務 **Then** 載入 `agent-identity-management` 走 Role Pivot 段(不要走 7 份重要檔案的繼承 SOP)、列出 6 個決策點讓使用者選 A/B/C/D。**If** pivot 範圍 ≥ 4 個維度(profile 名 / skill 庫 / SOP / 交付物命名) **Then** 整個重建 `hermes profile create <new> --clone`、不要原地改 persona。**完整 SOP**：`agent-identity-management/references/role-pivot-sop.md`
- **SOP 寫「設計變數」不寫「現況快照」（2026-06-09）**：寫 handoff pipeline SOP 時一開始把鏈寫成「`market-strategist` → 撈 → `product-planner` → 撈 PRD」這種「目前 2 段、剛好走到 PRD」的版本，被使用者當下糾正「限制應該是因為目前只有建立到 PRD 常駐代理，之後如果有建立出寫程式的代理，就會交到下一棒了，所以可能不用寫死」。**修法**：核心 SOP 改寫成「解析任務 → 決定代理鏈 → 對 N 個代理重複跑 N 次 → 撈最終產出」+「N = 鏈上代理數、新增代理後自動增加、不需改 SOP」。具體 bash 範例（寫死的 2 段範例）保留但標「範例」。**If** 寫任何 SOP/persona/流程文件時發現自己列「具體步驟 1/2/3/4」對應**目前**的代理或工具 **Then** 重新抽象成動態迴圈或條件判斷，把現況放在「範例」或「觸發情境」段（OK），不要放在「核心 SOP」段。**驗證**：「今天現況是 A→B→C 三段、明天加 D 段，這份文件需要改嗎？」需要改 = 寫死（壞）；不需要 = 抽象成變數（好）
- **卸載前用 `ps -o ppid=` 查 PPID 判斷「真正 owner」可顛覆整個方案（2026-06-08）**：使用者問「mempalace MCP 是前任拉斐爾 OpenClaw 套件代理啟動嗎？不能改由赫米斯（繼承後的現任拉斐爾）啟動嗎？」→ 查 `ps -o pid,ppid,cmd` 發現 mempalace.mcp_server 的 PPID 是赫米斯主進程（1872192），不是 OpenClaw。整個「卸載前要改赫米斯 MCP 設定加 env var」的方案變成不需要（PPID 證明 mempalace 本來就赫米斯管、前任拉斐爾 OpenClaw 套件代理死了也不影響）。**If** 卸載前猶豫「A 跟 B 哪個才是 X 的 owner」**Then** `ps -ef | grep X` + `ps -o pid,ppid,cmd` 查 PPID 鏈，不要從 config 檔讀「誰提到 X」就推論誰管
- **卸載會 kill child process 觸發「副作用波」+ 赫米斯自動 re-spawn（2026-06-08）**：前任拉斐爾 OpenClaw 套件代理卸載 `openclaw uninstall --all` 跑完後，mempalace MCP 從 PID 1872205 換成 1896464 — 卸載動作觸發 kill 整個 process group，赫米斯偵測 MCP 死掉自動 re-spawn 新進程。**對 MCP 工具鏈零 down-time**，但需要驗證：「卸載後 PID 是否換了」 = 系統健康訊號，反之「PID 沒換」 = 卸載沒動到、可能有問題。**If** 卸載某個 parent process **Then** 預期 child MCP 會重 spawn、PID 會變，要用「工具呼叫仍可用」驗證
- **套件卸載 100% 會清 CLI binary、但 user-installed systemd unit 殘檔要手動清（2026-06-08）**：前任拉斐爾 OpenClaw 套件代理的 `openclaw uninstall --all` 只清 `default.target.wants/` 跟 `timers.target.wants/` 內的 symlink，沒清 `~/.config/systemd/user/<service>.{service,timer}` 本身。**If** 套件卸載後看到 systemd `not-found inactive dead` 但 unit 檔還在 **Then** 這是套件卸載 bug、要手動 `rm -f` unit 檔 + `daemon-reload` + `reset-failed`。驗證：`find ~/.config/systemd -name '*<X>*'` 必須空
- **卸載前必先 `--dry-run`（2026-06-08）**：前任拉斐爾 OpenClaw 套件代理的 `openclaw uninstall --all --dry-run` 會列印「remove gateway service / remove ~/.openclaw / remove ~/.openclaw/workspace」三個動作。**任何 `npm uninstall`、`pip uninstall`、`apt remove`、`rm -rf` 前必先 dry-run 或 list target**。**If** 卸載指令有 `--dry-run` flag **Then** 必先跑確認會動什麼，不要直接看 help 就下指令。**If** 卸載指令沒 `--dry-run` **Then** 至少先 `which X` + `readlink -f $(which X)` + `dpkg -L X | head` 知道會被動到哪些檔
- **Vercel CLI auth.json 在套件卸載時可能被觸碰（2026-06-08）**：前任拉斐爾 OpenClaw 套件代理的 `openclaw uninstall --all` 後 `~/.local/share/com.vercel.cli/auth.json` 從原本的完整 OAuth token 變成 3 bytes 雜湊。**不影響**已部署的 status site 公開 URL（Vercel CDN 不依賴 CLI token），但未來要 `vercel --prod` 重新部署時需 `vercel login` 重新登入。**If** 卸載某個 CLI 工具後 `vercel whoami`/`gh auth status`/其他 CLI 認證指令報「no credentials」**Then** 該 CLI 的 auth.json 可能被卸載觸碰、跑 `vercel login`/`gh auth login` 重新登入。**If** 認證檔可能被卸載觸碰 **Then** 提前備份（`cp auth.json auth.json.pre-uninstall-20260608`）
- **`pgrep -f <name>` 對「path 含子字串」的 process 會誤報（2026-06-08 結尾）**：結尾驗證「前任拉斐爾 OpenClaw 套件代理完全清除」時 `pgrep -f openclaw` 報 6 個進程，嚇一跳以為漏網之魚。實際是 false positive — `pgrep -f` 對**完整 command line** 做 regex 匹配，任何 path 含 `openclaw` 子字串的 process 都會中（包括 `~/.hermes/hermes-agent/` 內某些子字串、sshd、跑 `pgrep` 自己的 bash）。正確查法：`pgrep -f 'openclaw/dist/index.js'`（更精準的完整 path）、或 `pgrep -af openclaw` 看完整指令辨識。**If** 用 `pgrep -f <name>` 確認 process 已清乾淨 **Then** 至少用 `pgrep -af` 看完整指令，不要只看數量
- **Background process 結束通知的 exit code 語意（2026-06-08）**：用 `terminal(background=true)` 啟動的 process 跑完，Hermes 自動通知 `Background process proc_xxx completed (exit code N)`。**N 的語意**:124 = timeout、130 = SIGINT（Ctrl+C）、137 = SIGKILL（OOM 或強制）、**143 = SIGTERM（被 pkill/kill 正常關掉）**。**If** 收到 background process 結束通知 **Then** 先看 exit code：124 → 該調大 timeout 或拆批；130/137 → 看 log 找原因；**143 → 通常是測試用 process 跑完被主動 kill、是預期內 lifecycle、不要當失敗重跑**。驗證方式：grep 自己 `pkill/kill` 紀錄 + `ps -ef` 看 process 是否還在 + `tail log` 看有沒有 panic
- **bash_profile 從 bashrc 複製會帶進「互動式 return」阻擋 login shell 的 export（2026-06-08）**：想把 export 寫到 `~/.bash_profile` 給 login shell 用，從 `~/.bashrc` 複製 skeleton 過去時，bashrc 開頭的「若非互動式 shell 則 return」區塊也跟著被複製。`bash -lc` 登入 shell 雖然是互動的，但 `bash -c "command"` 啟動的 subprocess 進到 bash_profile 會被 `case $- in *i*) ;; *) return;; esac` 提前 return，後面所有 export 都不執行。**症狀**：檔案裡 export 確實有值（`TWITTER_CT0` 160 chars 都在），但 `bash -lc 'echo ${TWITTER_CT0:0:10}'` 印出 `TWITTER_CT0 actual: `（空字串）。**修法 — 用獨立 `~/.bash_env` 純放 credentials**：在 `~/.bash_profile` / `~/.profile` / `~/.bashrc` 開頭（**在任何互動式判斷之前**）加 `[ -f ~/.bash_env ] && . ~/.bash_env`，credentials 寫在 `~/.bash_env`（mode 600）。這樣不論互動/非互動、login shell 與否、subprocess 與否，**只要 shell 啟動就一定 source 到**。**If** 寫 export 到 `~/.bash_profile` 從 `.bashrc` 抄過來 **Then** 改用獨立 `~/.bash_env` + 在三個 startup 檔案最開頭 source，不要把 bashrc 整份複製到 bash_profile

（更早的 hermes-internal 條目見下方「完整條目列表」段）

### vercel-deployment
- **GitHub push 沒觸發 Vercel auto-deploy、CDN edge cache 不會自動 invalidate（2026-06-07）** — 4 步驗證 SOP（git SHA → Vercel API → 手動觸發 → cache-busting curl）

## 完整條目列表

所有踩雷條目依分類存在 `references/by-category/` 下:

| 分類 | 檔案 | 條目數 | 觸發情境 |
|------|------|-------|----------|
| hermes-internal | `references/by-category/hermes-internal.md` | **24** | hermes CLI / cron / config 行為 / **驗證閉環失敗 (2026-06-09)** / **OpenClaw 反安裝 (2026-06-08)** / **bash_profile 互動式 return 阻擋 (2026-06-08)** / **SOP 寫設計變數不寫現況快照 (2026-06-09)** / **跨 profile handoff context 累積風險與 kill 接手 (2026-06-10)** |
| **profile-slimming-sop** | `references/sops/profile-slimming-sop.md` | — | **2026-06-09 新建**：常駐代理的 skill 精瘦 SOP（4 階段、必驗證 4 項） |
| gpg-encryption | `references/by-category/gpg-encryption.md` | — | GPG 對稱/非對稱加密、key 管理 |
| gh-cli-and-github | `references/by-category/gh-cli-and-github.md` | **6** | **GH013、GH001、filter-branch 從這次學到** |
| vercel-deployment | `references/by-category/vercel-deployment.md` | — | Vercel CLI / API / 部署 |
| python-sandbox | `references/by-category/python-sandbox.md` | **9** | Python sandbox / token 遮罩 / **uv venv 無 pip / pyproject force-include 衝突 / venv CLI PATH 不可見 / yt-dlp JS runtime / N100 住宅 IP AS-level 黑名單 / f-string sanitization 靜默替換** |
| headless-cookie-import | `references/by-category/headless-cookie-import.md` | **1** | **N100 headless 平台 CLI 認證（Twitter/Reddit/小紅書/微博/雪球）— 2026-06-08 新建** |
| secrets-and-env | `references/by-category/secrets-and-env.md` | — | .env / 憑證管理 |
| browser-automation | `references/by-category/browser-automation.md` | — | Playwright / headless browser |
| bash-defensive-patterns | `references/by-category/bash-defensive-patterns.md` | **4** | **2026-06-07 從這次對話建立** |
| hermes-backup-strategy | `references/by-category/hermes-backup-strategy.md` | — | **v1 → v4.2 演進** |
| hermes-backup-design-pitfalls | `references/by-category/hermes-backup-design-pitfalls.md` | **15** | **2026-06-07 從 v3 → v4.1 → v4.2 大幅擴充** |
- `hermes-backup-sop` | `references/by-category/hermes-backup-sop.md` | — | 備份執行 SOP |
- `hermes-config-tuning` | `references/by-category/hermes-config-tuning.md` | — | model / provider / wakeAgent gate |
- `execution-sop` | `references/execution-sop.md` | — | **跨分類執行 SOP**（改 jobs.json / .env / config.yaml / **patch 工具防 cascade damage (SOP-5)** / **跨 profile 寫入 soft-guard (SOP-6)** / L3 教訓分流） |

## 用戶偏好（2026-06-07 v4 演進中觀察到，**已寫進對應 Rules**）

- **「不要憑印象答」**：當用戶問「X 可以不備嗎？」「X 是 Y 還是 Z？」時，先跑驗證命令（`git remote -v`、`git log`、`file <X>`、`du -sh`）並把輸出貼出來。**見 Rule 6（✅ 聲稱附驗證）+ Rule 12（rebuild 判斷要先查）**。對應觸發：「真的可以不備嗎？」「驗證一下」。
- **「先建 todo、按優先順序執行」**：v4 演進 + 還原 SOP + Telegram 通知 3 個任務都是先 `todo` 規劃再跑。對應觸發：「按照你的建議先 sync」、「按照建議順序處理任務」。
- **「失誤要直接說、不要假裝沒事」**：v4 跑 Drive purge 砍整個 remote、誠實承認「我犯了個大錯」、不迴避。對應 SKILL 的 hermes-internal「自我審查：自我報告 ≠ 驗證」段。
- **「涉及具體 ID（commit SHA、PR 編號、deployment ID）時，必須驗證而非憑敘事」**（2026-06-07 新增）：我曾回報「commit 4a8b3f3 已 push」但 git reflog 完全沒這個 commit — 浪費了 8 個工具呼叫才發現。對應 hermes-internal 條目「LLM 幻覺出成功 commit SHA」。**任何回報具體 ID 給使用者前，必須先跑 `git log` / `gh pr view` / `curl API` 驗證並貼輸出。**
- **「探勘式問題也要先查」(2026-06-07 新增)**：使用者問「X 系統/技能/機制有沒有在運作？」「X 是什麼？」「X 存不存在？」「X 是誰在評價？」這類**探索狀態**的問題（不是修 bug、不是執行任務），**仍然要先實地查** — 不能靠「我記得是這樣」答。具體方法：
  - 問「有沒有在運作」 → 先 `cron list` / 跑對應命令看輸出 / 查檔案 mtime
  - 問「X 是什麼 / 存不存在」 → 先 `find` / `skill_view` / 搜目錄
  - 問「誰在做 X」 → 先查 DB / 查程式碼邏輯（不要從 narrative 推）
  - 答覆結構必含「我親自查了什麼 + 真實輸出」 — 不能直接給結論
  - 失敗時說「我沒查到」+ 給「我怎麼查了」+ 給「我可以怎麼繼續查」— 不要用模糊敘述填空
- **「決策前要看『推薦清單 + 預期效益』再行動」(2026-06-09 觀察 2 次確認)**：使用者面對「該怎麼處理」類問題時，**連續 2 次都選「先看推薦清單 + 預期效益 + 影響範圍、我再決定」選項**（清理常駐子代理相關技能時選 4，處理不相關技能時選 4）。**不是**「不要動」而是「動之前我要先看到具體要改什麼、有什麼影響、有什麼備案」。**If** 使用者交付「請清理 X」「請修整 Y」「請改 Z」類任務 **Then** 動手前先列出「推薦處理方案 + 預期效益 + 影響範圍 + 備案」給使用者看。**If** 任務有「動 vs 不動」「刪 vs 留」「直接做 vs 分階段」的可選性 **Then** 用 `clarify` 給 3-4 個選項，含「先看清單再決定」選項。**If** 已預期風險低的動作（備份、列清單、跑 grep）**Then** 可以直接動並在事後報告；風險高（刪除、覆蓋、修改 config）的動作一律先報告方案

## 支援檔案（references / templates / scripts）

這個 skill 除了「踩雷條目庫」外還有幾個跨分類的 SOP 與支援檔，按用途分類：

| 用途 | 檔案 | 說明 |
|------|------|------|
| 跨分類執行 SOP | `references/execution-sop.md` | 改 jobs.json / .env / config.yaml / **patch 防 cascade (SOP-5)** / **跨 profile soft-guard (SOP-6)** / L3 分流 |
| 評估 + grep bug | `references/eval-sync-grep-bug.md` | eval-sync 抓 `***` redaction marker 的細節 |
| Git push recovery | `references/git-push-recovery.md` | cron deployment git push rejection recovery |
| v3 skills sync bug | `references/v4-p7-skills-sync-bug.md` | v3 漏掉 skills/ 同步的完整還原 SOP |
| 備份 timeout | `references/hermes-backup-timeout.md` | rclone Drive 速度降到 B/s 的完整 time + flag 設定 |
| 跨檔 reference | `references/cross-refs.md` | 各分類的快速 cross-reference 索引 |
| **新增條目 SOP** | `references/adding-entries-sop.md` | **2026-06-09 新建**：用 trial-and-error 寫新條目的 4 步流程完整版（決策樹、常見錯誤、If→Then 速查）。**`@學習` keyword 觸發後的標準 SOP** |
| **Keyword 觸發 SOP** | `references/sops/keyword-triggers-sop.md` | **2026-06-09 新建**：使用者自訂 `@關鍵字` 觸發機制的完整設計（A/B/C 三模式、表格如何維護、新增 keyword 的 SOP） |
| **Profile 精瘦 SOP** | `references/sops/profile-slimming-sop.md` | **2026-06-09 新建**：常駐代理 skill 精瘦 4 階段 SOP（5 項必跑驗證） |
| **MEMORY 維護 SOP** | `references/sops/memory-maintenance-sop.md` | **2026-06-09 新建**：MEMORY 25 KB 警戒線觸發時的「plan-first-not-just-do」清理流程（5 步、3 件驗證、3 個常見錯誤） |
| 模板 | `templates/entry-template.md` | 寫新 L2 條目時複製這個 skeleton（保證格式一致） |
| 腳本 | `scripts/oauth_device_poll.py` | OAuth Device Code polling 範例（Google TV/limited-input client 用） |

> **注意**：`references/sops/` 子目錄的 SOP 檔**不在 `linked_files.references` 自動掃描範圍**（system 只掃 `references/` 直接子檔），要 `skill_view(name='trial-and-error', file_path='references/sops/<name>.md')` 手動指定路徑。

**If** 寫新 L2 條目 **Then** 先看 `templates/entry-template.md` 確認格式
- **If** 觸發 `@學習` keyword **Then** 跑 `references/adding-entries-sop.md` 的 4 步流程
- **If** 觸發 `@` 開頭的 keyword **Then** 跑 `references/sops/keyword-triggers-sop.md` 的設計
- **If** 寫 MEMORY/AGENTS 的「X 是 Y 裝法 / X 在 Z 路徑 / X 是 N 版本」結論 **Then** **必同步寫一條「怎麼驗證」**（`which X` / `npm ls -g` / `ls -la <path>`）——沒驗證命令的結論可能錯好幾個月直到 CLI 爆才被發現。對應 MEMORY.md「MEMORY 寫『X 是 Y』也要寫『怎麼驗證』」(2026-06-09) + hermes-internal「Hermes CLI 找不到：真因是 user-local 安裝」條目
- **If** 看到「該清 MEMORY / 該刪 X / 該改 Y」任務 **Then** **plan-first-not-just-do**：動手前先列「推薦處理方案 + 預期效益 + 影響範圍 + 備案」給使用者看、可加 `clarify` 給「先看清單再決定」選項（2026-06-09 觀察 2 次確認）。對應 `references/sops/memory-maintenance-sop.md` 完整 5 步流程 + [[#「決策前要看『推薦清單 + 預期效益』再行動」]]
- **If** MEMORY 維護 5 步流程中遇到「不知道這條該 L2 還是 L3」 **Then** 看 `references/adding-entries-sop.md` Step 3「判斷層級」決策樹
</content>