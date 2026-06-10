# Hermes 內部架構 / 工具鏈 / SOP 試誤條目

> 集中收容：cron / gateway / profile / config / AGENTS.md / keyword 觸發 / 備份等內部工具鏈的 L2 試誤條目
> 寫法：問題情境 + 失敗原因 + 正確做法 + 驗證命令

---

## 2026-06-10（最新）

### v2 Orchestrator sub-agent 不會自動繼承「使用者原意」— 必抓清單是必要設計
- **情境**：consumer-researcher v2 架構跑 skill-language-exchange-platform 任務,Orchestrator 知道使用者原意 Persona(小美/佐藤/陳媽媽),但 sub-agent 派出去後**完全無視這些 Persona**、自己去抓 Reddit/HN 推導
- **失敗原因**：sub-agent 啟動時**只看到任務指令**、看不到「使用者之前提的偏好」——agent 是無狀態的(每次新 session、沒有跨 call 記憶)
- **正確做法**：
  1. Orchestrator 寫 `_plan.md` 到 handoff 目錄,內含**使用者原意 Persona** + **必抓清單** (SkillSwap.io、Busuu、HelloTalk、Tandem 4 個直接標竿 + Conversation Exchange 3 個間接標竿) + **要避開的標竿**
  2. summarizer-worker template SKILL.md 加「必讀 _plan.md」步驟
  3. web-worker template SKILL.md 加「必抓清單」段(明確 list 4-7 個不能漏的標竿)
  4. consumer-researcher persona.md Step 2 加「保留 v1 Persona」段(就算 _raw/ 沒驗證到、也要保留使用者原意)
- **驗證**：v2 修正版三方比對報告(`_V2_FIXED_COMPARISON.md`)確認 SkillSwap.io + 3 個使用者原意 Persona 全有出現
- **推廣**:**任何「Orchestrator + 平行 worker」架構,Orchestrator 跟 worker 的介面契約 = `_plan.md` 必抓清單**

### notify_on_complete 是「最終確認」不是「即時 polling」(2026-06-10)
- **情境**:`terminal(background=true, notify_on_complete=true)` 啟動 4 個 worker,觀察從 worker 寫完到通知送達**延遲 10-14 分鐘**(v1 觀察曾達 1 小時)
- **失敗原因**:把 `notify_on_complete` 當 polling 機制 = 永遠等不到即時狀態
- **正確做法**:
  1. `notify_on_complete` = **最終確認**用,不是「worker 跑完就通知」
  2. **要主動撈狀態**:`ls <output_dir>` 看檔案是否生成(檔案存在 = worker 跑完)
  3. **常態延遲 10-14 分鐘**:不要 timeout 設太短(預設 180s 會誤判失敗)
  4. 觀察「worker 真的卡住 vs 已跑完等通知」的差異:`process(action='list')` 看 process 是否還活著 + `ls` 看 output 是否生成
- **驗證**:v2 修正版 4 worker 寫完 11:51、通知 12:00~12:01 才送達(觀察 4 個 worker 全部 ~10 分鐘延遲)

### PTY 模式跑備份後,pty 緩衝輸出 ≠ 真的備份成功(2026-06-10 踩坑)
- **情境**:pty=true 跑 `backup-all.sh`(2025-12 環境的 v3 舊版),pty 緩衝輸出顯示「12 個備份項目成功」,但**實際**備份目錄 `/media/hoonsoropenclaw/n100/backup-2025-12/` **不存在**(`/media/` 是空的)
- **失敗原因**:
  1. **path completion 跟腳本 lint 是兩回事**:`bash -n` 通過不代表跑起來會成功——v3 腳本語法正確、但 BACKUP_DIR 寫死到已不存在的路徑
  2. **pty 緩衝的「成功」訊息是假象**:tar 寫到不存在路徑時默默失敗、pty 把 stderr 緩衝在記憶體、看起來像成功
  3. **沒用 `ls` 真實驗證**:我看到 pty 輸出就當成功、沒用 `ls -la` 確認檔案存在
- **正確做法**:
  1. 跑完任何備份**必須** `ls -la <預期目錄>/<預期檔名>` 真實驗證
  2. **沒看到檔案 = 失敗**,不論 pty 輸出多漂亮
  3. 跑前先 `test -d <BACKUP_DIR> && echo "OK" || echo "MISSING"` 確認目錄存在
- **驗證**:2026-06-10 pty 跑 v3 備份後,`ls /media/hoonsoropenclaw/n100/backup-2025-12/Hermes-Backup-2026-06-10/` = **No such file or directory**(備份完全沒寫)
- **推廣**:**任何長時間 + 路徑依賴的腳本,跑完必 ls 驗證,不要信 pty 輸出**

### N100 同時存在 v3 / v4 兩份備份腳本,腳本歧義會誤導(2026-06-10 踩坑)
- **情境**:`~/.local/bin/backup-all.sh`(2025-12 環境的 v3)跟 `~/.hermes/scripts/hermes-backup-v4.sh`(2026-06-06 驗證的 v4)**同時存在 N100**——v3 在 PATH、v4 在 scripts/
- **失敗原因**:我看到 `backup-all.sh` 在 `~/.local/bin/` 就當它是當前備份腳本、跑下去才發現 v3 BACKUP_DIR 寫死到不存在的路徑
- **正確做法**:
  1. **永遠用 v4**:`~/.hermes/scripts/hermes-backup-v4.sh`(`--tier1` / `--tier2` / `--upload-tier2` / `--dry-run`)
  2. **不要用 v3**:`~/.local/bin/backup-all.sh` 是 2025-12 環境的舊版
  3. v4 支援 `--dry-run` 可看會做什麼
  4. v4 互動式 GPG passphrase 必用 `pty=true`(行 168 附近)
- **驗證**:`ls ~/.hermes/backups/hermes_backup_*.tar.gz` 看時間戳(2026-06-08 03:00 最後 cron 跑的就是 v4)
- **推廣**:**任何腳本名稱相似的工具,跑前先 `head -50 <腳本>` 確認是當前版本,不要看 `which X` 就當權威**

### Profile 改造的 Orchestrator 必須寫 _plan.md 才能傳承使用者原意(2026-06-10)
- **情境**:consumer-researcher 從 v1 單體升 v2 架構(Orchestrator + 4 worker + 1 summarizer),v1 跑 10 分鐘卡住 → 失敗;v2 跑 6 分鐘成功
- **失敗原因**:v1 是單體 agent 在自己 context 內跑 4 個 web 搜尋、context 累積到 108K 卡住;v2 是 Orchestrator 派 4 個 worker 平行跑、context 隔離到 sandbox
- **正確做法**:
  1. 升級到 v2:Orchestrator 寫 `_plan.md` → 4 worker 平行抓資料 → summarizer-worker 壓縮去重 → `_summary.md`
  2. web-worker-template skill:啟動時讀 `_plan.md` 拿必抓清單
  3. summarizer-worker-template skill:讀 `_plan.md` 拿「使用者原意 Persona」+「間接標竿分類」
  4. consumer-researcher persona.md Step 2 加「保留 v1 Persona」段
- **驗證**:三方比對報告 `_V2_FIXED_COMPARISON.md` 顯示 v2 修正版涵蓋 SkillSwap.io + 3 個使用者原意 Persona
- **推廣**:**任何 LLM agent 跑 4+ 次 web 搜尋、context 會爆的任務,改用 Orchestrator + 平行 worker 架構**

### 跨 profile 寫入有軟防護,需 cross_profile=true bypass(2026-06-10)
- **情境**:用 `write_file` / `patch` 改 `~/.hermes/profiles/consumer-researcher/skills/web-worker-template/SKILL.md` 被擋
- **失敗原因**:`write_file` 預設只寫當前 active profile(default),跨 profile 有 soft guard
- **正確做法**:明確加 `cross_profile=true` 參數 bypass
- **驗證**:`write_file(path, content, cross_profile=true)` 成功寫入 consumer-researcher profile
- **推廣**:**任何跨 profile 寫入(共享 skill / 共享 SOP)必加 cross_profile=true,別傻傻 debug「為什麼寫不進去」**

### background process 通知延遲 10-14 分鐘是 hermes scheduler 常態(2026-06-10 觀察)
- **情境**:v2 修正版 4 個 worker 啟動,寫完時間 11:51,通知送達時間 12:00~12:01
- **正確做法**:
  1. **不要用 `notify_on_complete` 當 polling 機制**
  2. **要主動撈**:`process(action='list')` 看 process 是否還活著 + `ls <output_dir>` 看檔案是否生成
  3. 觀察「卡住 vs 跑完等通知」:process 還在 = 卡住、process 不在 + 檔案在 = 跑完
- **驗證**:4 個 worker 全部 ~10 分鐘延遲送達通知(常態值)
- **推廣**:**任何 hermes background process,通知延遲 10-14 分鐘是正常,不是 bug**

### GPG passphrase 不用手動設定,64 字元自動產生存在固定路徑(2026-06-10 14:xx 釐清)
- **情境**:使用者問「GPG 密碼在哪、是不是抓 rclone.conf 密碼」、還主動打了 12 字元密碼到對話
- **失敗原因**:我之前以為 GPG passphrase 要使用者手動設定、不知道已經自動產生了
- **真相**:
  1. **2026-06-07 v4 自動跑 `--rotate`** 產生 **64 字元高熵密碼**
  2. 存在 `~/Documents/hermes-keys/.hermes_backup_passphrase`（mode 600）
  3. `hermes-secrets-encrypt.sh` 用 `gpg --passphrase-file "$PASSPHRASE_FILE"` 從檔讀、**完全不需要互動輸入**
  4. 使用者打的「xm3fm065ji6」**不符合 rclone.conf 內的 crypt password 也不符合 GPG passphrase**——可能是密碼管理員主密碼
- **正確做法**:
  1. **不要在對話打 GPG 密碼**(就算使用者主動給,也不接)
  2. 回答「在 ~/Documents/hermes-keys/.hermes_backup_passphrase、64 字元自動產生的、Tier 2 用 --passphrase-file 從檔讀」
  3. 驗證命令:`cat ~/Documents/hermes-keys/.hermes_backup_passphrase | wc -c` 應回 65
- **驗證**:2026-06-10 14:xx 跑 `bash ~/.hermes/scripts/hermes-secrets-encrypt.sh`,GPG 自動從檔讀、零互動完成加密
- **推廣**:**任何「備份 / 加密」任務,Tier 2 用 `--passphrase-file` 自動讀、不要互動輸入**

### .gitconfig 帳號混亂 — `gh auth setup-git` 是正解(2026-06-10 14:xx 釐清)
- **情境**:`git push` 顯示進度跑到 95% 但 `git rev-list --left-right --count main...origin/main` 顯示 `1 0`(本地領先),或 `Permission to <repo> denied to <備用帳號>`
- **失敗原因**:`~/.gitconfig` 設 `credential.helper = store --file ~/.git-credentials-raphael`,裡面存的是**舊 `hoonsor` 備用帳號的 token**(前任拉斐爾 OpenClaw 套件時代留下)。`gh auth switch` **不會**改 git 全域認證
- **正確做法**:
  1. **跑 `gh auth setup-git` 一次**:自動注入 `[credential "https://github.com"] helper = !/usr/bin/gh auth git-credential` 到 `.gitconfig`
  2. 推 push 前**永遠先 `gh auth status` 看 active account 是誰**
  3. **`gh auth switch` 切換 gh CLI 帳號**;`gh auth setup-git` 讓 git 用 gh token
- **驗證**:
  - `cat ~/.git-credentials-raphael` 看到 `hoonsor:ghp_XXX@github.com` = 確認中
  - `gh auth status` 主帳號是 `hoonsoropenclaw`(對的)
  - **但 git push 仍用 hoonsor token** ← 這就是 bug
  - 跑 `gh auth setup-git` 後:.gitconfig 多出 `[credential "https://github.com"]` section、push 成功
- **推廣**:**任何 git push 失敗 + 主帳號是對的 + 顯示 Permission denied to <備用帳號> → 必跑 gh auth setup-git**

### v4 備份腳本 4 次修補的必要性(2026-06-10 14:xx 觀察)
- **情境**:`hermes-backup-v4.sh` 在 2026-06-10 14:xx 從 v4.1 升到 v4.4,**4 個修補**才解決 push 卡死
- **4 個修補**:
  1. **v4.2**:加 `~/.hermes/profiles/` 同步段(18 個 exclude)→ 原本只備 default,常駐子代理不被備份
  2. **v4.3**:`skills/` rsync 加 `--max-size=50m` → hermes 自動 backup 在 `.curator_backups/skills.tar.gz` 是 125MB 單一 blob、GitHub 拒絕
  3. **v4.3**:profiles rsync 同步加 `--max-size=50m`(profiles/*/skills/.curator_backups/ 也有 125MB)
  4. **v4.4**:`--exclude='sparc-methodology/v3/'` 跟 `'sparc-methodology/ruflo/'` → 整體 78MB、--max-size 只擋單檔
- **失敗原因**:
  1. **staging 內累積 125MB blob** → 已經 commit 進 git history,`--force-with-lease` 還會被 reject(沒共同祖先)
  2. **必須 rm -rf .git 重 init** + `git push --force` 重建 history
  3. **`.curator_backups/` 是 hermes 自動 backup 元件** → 備份的備份 = 遞迴爆炸陷阱
- **正確做法**(v5 設計必加):
  1. 必加 `--max-size=50m` 到所有 rsync 段(GitHub 物件限制 100MB、保險 50MB)
  2. 必加 `.curator_backups/` 到所有排除清單
  3. 必加 `state.db*` 排除(對話歷史爆、含敏感 metadata,該走 Tier 2)
  4. v4 profiles 段完整 exclude 清單(18 個)見 `agent-system-backup` 10.5 段
- **驗證**:v4.4 跑完 → `git rev-list --left-right --count main...origin/main` 回 `0 0` = 完全同步
- **推廣**:**任何「備份整個 hermes_home」腳本,必加 .curator_backups/ + state.db* + --max-size 50m 三層過濾**

### rclone "directory not found" 是誤導錯誤(2026-06-10 14:xx 釐清)
- **情境**:`rclone copy <file> hoonsorasus:hermes-backup/secrets/` 報 `directory not found`,但 `rclone lsd hoonsorasus:hermes-backup` 明確看到 `secrets/` 存在(裡面還有 3 個 2026-06-07 的備份)
- **失敗原因**:
  1. Drive 端目錄**真的存在**(`rclone lsd` 證實)
  2. rclone client 端的**路徑拼接錯誤**(少一個 `/`、多一個 `:`、特殊字元沒 escape)
  3. **rclone 的錯誤訊息是誤導**——其實是別的問題但被包成 "directory not found"
- **正確做法**:
  1. `rclone tree <remote>:<bucket> --max-depth 2` 看完整結構
  2. `rclone lsf <remote>:<bucket>/<subdir>/` 直接列 subdir 內容
  3. `rclone copy -v <file> <remote>:<bucket>/<subdir>/` 開 verbose 看哪一步失敗
  4. **130MB 加密檔 push 預期 5-10 分鐘**(231 KiB/s)——看到錯誤別立刻放棄,先看 30 秒有沒有進度
- **驗證**:背景跑 `rclone copy -v --transfers=1 --checkers=1 --tpslimit 5 ...` 確實有進度(231 KiB/s)
- **推廣**:**任何 rclone 報錯,先用 verbose + 直接 lsd 確認,不要相信錯誤訊息字面**

### v4.5 雙層 GPG 加密修補 passphrase 沒備份的致命漏洞(2026-06-10 14:xx 釐清)
- **情境**:`hermes-secrets-encrypt.sh` 把 .env/auth.json/state.db 用 GPG 加密成 `secrets-bundle-*.tar.gpg` 推到 Drive,解密金鑰是 `~/Documents/hermes-keys/.hermes_backup_passphrase`(64 字元 auto-gen)。但**v4.0 ~ v4.4 完全沒備份這個 passphrase 檔**——如果 N100 硬碟壞掉,**使用者完全無法異機還原 Drive 上 130MB 加密檔**
- **失敗原因**:v4 設計的「雙目錄分離原則」(加密檔 vs passphrase 嚴格分開)只考慮到「本地兩處分開放」,**沒考慮「passphrase 也需要離線備份」**
- **正確做法**(v4.5 新增):
  1. Tier 2 跑完後**自動**加跑 `backup_passphrase_recovery()`:
     - 用 GPG 對稱加密 passphrase 檔(使用者互動輸入 USER_KEY)
     - 上傳到 `hoonsorasus:hermes-backup/passphrase-recovery/`
  2. `hermes-restore-v4.sh tier2` 偵測本地無 passphrase 檔時:
     - 自動從 Drive `passphrase-recovery/` 下載最新加密檔
     - 互動式問 USER_KEY
     - GPG 解密 → 放到 `~/Documents/hermes-keys/.hermes_backup_passphrase` (mode 600)
     - 然後才解 `secrets/*.tar.gpg`
  3. **USER_KEY 跟 GPG passphrase 必須不同**(兩層加密才有意義)
  4. **USER_KEY 必須使用者記住**(建議 = 1Password 主密碼)
- **驗證**:`rclone lsf hoonsorasus:hermes-backup/passphrase-recovery/` 看到新檔案
- **推廣**:**任何「GPG 對稱加密 + 加密檔推到雲端」設計,金鑰檔也必須有離線副本——單靠本地金鑰不算「備份」**

### Market-strategist → consumer-researcher 身份重塑:連帶 handoff 命名都要改(2026-06-10 釐清)
- **情境**:2026-06-10 把 `market-strategist` profile 整個**重塑**為 `consumer-researcher`(身份語意完全反轉),但**忘記同步更新**:
  1. AGENTS.md `@專案` keyword 表格還寫「`market-strategist`、`product-planner`」(AGENTS 是工作區規範唯一持久化位置)
  2. `references/sops/keyword-triggers-sop.md` 的 `@專案` SOP 段可能也殘留舊名
  3. handoff 命名從 `market-research-<slug>.md` 改為 `consumer-needs-research-<slug>.md`
- **失敗原因**:身份重塑時**只想到「profile 設定」**,沒想到**所有指向這個身份的外部引用都要同步掃**:
  - 跨 profile 寫入(skills、handoff 範本、SOUL.md)
  - 工作區文件(AGENTS.md、IDENTITY.md、USER.md、TOOLS.md、HEARTBEAT.md、keyword SOPs)
  - 下游代理的 persona.md(persona 引用舊 handoff 命名)
- **正確做法**(2026-06-10 重塑時已跑):
  1. **profile 設定**:新 profile clone 過來 + 改 persona.md/SOUL.md
  2. **跨 profile skills**:web-worker-template/summarizer-worker-template 加 `cross_profile=true` 寫入
  3. **AGENTS.md 表格**:`@專案` 觸發段同步更新代理清單
  4. **keyword SOPs**:`keyword-triggers-sop.md` 的 `@專案` 範例從「市場調研」改「消費者調研」
  5. **下游 product-planner persona**:讀 handoff 路徑、MoSCoW 來源、版本標頭都從 `market-research` 改 `consumer-needs-research`
  6. **刪除舊 profile**:`hermes profile delete market-strategist`(用 stdin 餵確認字串繞過 PTY)
- **驗證**:`hermes profile list` 看不到 `market-strategist`、`grep -r "market-strategist" ~/.hermes/{skills,memories,profiles}` 應該 0 個 false-positive
- **推廣**:**任何「身份重塑」(不是「身份繼承」!)要全工作區 grep 同步掃 6 個位置(profile + skills + AGENTS + keyword SOPs + 下游 persona + 範本檔)——不是只改 profile 設定就以為完成**


### GitHub push 95% 卡死是「單一大物件被 server 拒絕」的副作用(2026-06-10 14:xx 釐清)
- **情境**:`git push --progress origin main` 跑到 95% (40+ MiB) 後**突然被砍**,server 端 `send-pack: unexpected disconnect while reading sideband packet`,本地 `git rev-list` 顯示 `1 0` 或 `2 0`
- **失敗原因**:
  1. **GitHub 對單一 push 內的大物件有限制**(~100MB)、push 進度條看起來 95% 是本地 send 完 95% 的物件,但 server 端**中途 disconnect**
  2. **不要相信 `git push` 沒報錯就是成功** → 必 `git rev-list --left-right --count main...origin/main` 驗證
- **正確做法**:
  1. `find .git/objects -type f -size +50M` 找 staging 內 > 50MB 的單一 blob
  2. `git verify-pack -v .git/objects/pack/*.pack | sort -k3 -rn | head -5` 找 pack 內最大物件
  3. `git log --all --pretty=format:"%H %s" --diff-filter=AM -- '**/skills.tar*'` 找哪個 commit 引入
  4. 找到就 `git filter-repo` / `git filter-branch` 移除,**或** `rm -rf .git` 重 init + force push 重建 history
- **驗證**:`0 0` = 成功、`1 0` 以上 = 有 commit 沒推上去、必查 blob 大小
- **推廣**:**任何 git push,跑完必 `git rev-list` 驗證;95% 卡死 = 單一大物件被 server 拒絕**

### 舊備份路徑 2025-12 在當前 N100 不存在,backup-all.sh 寫死會無聲失敗(2026-06-10 14:xx 釐清)
- **情境**:`backup-all.sh` 寫死 `BACKUP_DIR="/media/hoonsoropenclaw/n100/backup-2025-12/"`,pty 跑完顯示「12 個項目成功」但實際目錄不存在
- **失敗原因**:
  1. **2025-12 環境的掛載點 `/media/hoonsoropenclaw/n100/`** 在當前 N100 **不存在**(`/media/` 是空的)
  2. 任何備份腳本要寫到 `/media/...` 路徑 → **必先 `ls /media/` 確認掛載存在**,不存在就 abort
- **正確做法**:
  1. 跑前 `test -d <BACKUP_DIR> && echo OK || echo MISSING`
  2. 不存在就用替代方案:`~/.hermes/backups/`(v4 用的)或 `~/backups/`
  3. **跑完必 ls 驗證**(`ls -la <BACKUP_DIR>`)——別只信 pty 輸出
- **驗證**:`ls /media/hoonsoropenclaw/` 報 `No such file or directory` = 確認 v3 backup-all.sh 不能用
- **推廣**:**任何備份腳本寫到 `/media/...` 或 `n100/backup-2026...` 開頭,先 ls 確認,不存在就別跑**

---

## 2026-06-08 之前

### hermes-agent skill 自我改進 SOP(2026-06-09)
- **情境**:使用者要求赫米斯「越用越聰明」,需要自我改進機制
- **正確做法**:
  1. 技能更新:踩坑後**主動 patch skill**(不只寫 memory)
  2. 記憶管理:遵循「3 層試誤 L1/L2/L3」原則(L1 = state.db、L2 = 具體解法指向、L3 = 抽象教訓入 MEMORY)
  3. SOP 服從性:任務完成對照 SOP 自我檢查
  4. 外部驗收循環:Layer 2.5 用 headless browser / curl 驗證外部系統狀態
- **驗證**:trial-and-error 持續累積條目 + MEMORY.md 定期清理

### 跨 profile handoff pipeline(2026-06-09 確立)
- **情境**:使用者問「能不能把任務轉交給 A→B 自動串?」
- **結論**:default 赫米斯當 orchestrator、依任務動態決定代理鏈、跑每段代理、撈報告寫到 handoff/
- **不是全自動**——會看到 N 次工具呼叫(N=鏈上代理數)
- **常駐代理** = `hermes profile + tmux`,不是舊 agents/ 身份檔方案

### profile 精瘦 keep-list 行尾註解會讓 comm match 0 個(2026-06-09)
- **情境**:`hermes skills opt-out --keep` 的 keep 清單寫 `name # 註解`,結果 regex 沒 match、全部 opt-out
- **失敗原因**:`comm` 比對時把行尾註解算進去、name 比對失敗
- **正確做法**:keep 清單**只寫 name、一行一個、純文字**,註解放外部註解檔或 markdown 表格

### hermes profile delete 需要互動式確認(2026-06-09)
- **情境**:`hermes profile delete <name>` 跳出 `[y/N]` prompt 確認、terminal 模式不能輸入
- **正確做法**:用 `pty=true` 跑 + 看到 prompt 時 `process(action='write', data='y\n')` 餵入;或 stdin 餵 `yes y` / `<<< "y"` 透過 pipe

### hermes curator 會自動把刪掉的 skill 補回來(2026-06-09)
- **情境**:用 `hermes skills opt-out --remove` 砍 skill,跑完發現被砍的 skill 又跑回來
- **失敗原因**:`bundled_manifest` 機制 + curator 自動 sync
- **正確做法**:
  1. **bundled 65 個 skill**:`opt-out --remove` 確實會刪,但下次 `hermes curator` 跑時會自動補回
  2. **user-edited/hub/local skill**:用 Python 白名單法精準刪(`os.remove` + 不要 reload)
  3. 精瘦完跑 `ls ~/.hermes/profiles/<p>/skills/ | wc -l` 看磁碟實際數字(不是 `hermes skills list`)
- **驗證**:consumer-researcher 精瘦 194 → 41(後被 curator 補 13 個、最終 36 個有效)

### 「常駐子代理」= profile + tmux,不是舊 agents/ 方案(2026-06-09)
- **舊方案**:`~/.hermes/agents/*.yaml` 身份檔 + `persistent-subagent` skill 派遣
- **新方案**:`hermes profile create <name> --clone` 建獨立 profile + 專屬 skill + tmux 持久化
- **If** 卸載舊方案 **Then** 驗證 3 件事:(1) 新方案可運作、(2) 沒其他 skill 引用、(3) trial-and-error 同步更新

### 卸載前用 ps -o ppid= 查「真正 owner」可顛覆整個方案(2026-06-08)
- **情境**:卸載前任拉斐爾 OpenClaw 套件前,猶豫 mempalace MCP 是誰啟動的
- **正確做法**:`ps -o pid,ppid,cmd` 查 PPID 鏈,不要從 config 檔讀「誰提到 X」就推論
- **驗證**:mempalace PPID 是 hermes 主進程 → 卸載 OpenClaw 不影響 mempalace

### 卸載任何東西前必先 --dry-run 或 list target(2026-06-08)
- **情境**:`openclaw uninstall --all --dry-run` 會列印將刪除的東西
- **正確做法**:**永遠先 --dry-run** 確認會動什麼
- **沒 --dry-run**:`which X` + `readlink -f $(which X)` + `dpkg -L X | head` 知道會被動到哪些檔
- **套件卸載 bug**:看到 systemd `not-found inactive dead` 但 unit 檔還在 = **手動清**(`rm -f unit 檔` + `daemon-reload` + `reset-failed`)

### keyword 觸發是 agent-level 行為,不是 hermes 內建功能(2026-06-09)
- **情境**:使用者問「能不能設定『@學習』自動觸發學習流程?」
- **失敗原因**:HERMES 沒有內建 user-defined macro
- **正確做法**:keyword 觸發是 **agent-level 行為**——每次收到訊息時 agent 掃、命中就跑 SOP
- **AGENTS.md 表格**是工作區規範唯一持久化位置
- **SOP 集中檔**:`~/.hermes/skills/trial-and-error/references/sops/keyword-triggers-sop.md`(2026-06-10 補建)

### 身份重塑 ≠ 身份繼承,採整個 profile 重建(2026-06-09 確立)
- **情境**:market-strategist 改成 consumer-researcher(整個身份反轉)
- **正確做法**:
  1. **整個 profile 重建** = B 方案(不沿用舊 skill 庫,從 default clone 重來)
  2. **歷史脈絡保留**:舊 profile 不直接刪,**先備份**到 `~/shared-infra/<name>-backup-<date>/`
  3. **wrapper 同步更新**:`~/.local/bin/<name>`
  4. **handoff 命名更新**:`market-research-<slug>.md` → `consumer-needs-research-<slug>.md`
  5. **下游代理同步**:`product-planner` persona.md 5 處改讀新路徑、新 MoSCoW 來源
  6. **刪除舊 profile**:用 `hermes profile delete` + `pty=true` 餵確認

### 備份架構觀念:rebuild 優先、可重建的不備(2026-06-06)
- **核心**:設計備份架構時先問「每個資料類型有沒有辦法 rebuild」
- **Tier 1(GitHub)**:公開版設定、記憶、skills、scripts、kanban.db
- **Tier 2(Drive + rclone crypt)**:完整版 + .env 真實檔 + GPG token + 源碼
- **驗證**:Drive sync timeout ≥ 3600s(Google Drive API 寫入 3 req/s sustained 限制)

### Google Drive API 配額(2026-06-06 確認)
- **配額上限** = 840,000 單位/分鐘/專案
- rclone sync 每個小檔 ≈ 3-5 個 API 單位
- 10000+ 小檔 = 50000+ API 單位 → **幾分鐘內秒殺配額**
- **解法**:`--tpslimit 5 --transfers 1 --checkers 1` 或改 tar.gz
- **觸發信號**:log 裡速度從 MiB/s → KiB/s → B/s 指數衰退 = rate limit(不是網路問題)

### MEMORY 寫「X 是 Y」也要寫「怎麼驗證」(2026-06-09)
- **情境**:MEMORY 寫「N100 的 hermes 是 npm -g 裝」結果是 user-local、錯到 2026-06-09 才修正
- **正確做法**:**結論型事實必同步寫驗證命令**(`which X` / `npm ls -g` / `ls -la <path>`)
- **沒有驗證命令的 MEMORY 紀錄可能錯好幾個月**

### rclone config 兩份要分清楚(2026-06-06 試誤)
- `~/.config/rclone/rclone.conf`(舊、過期 token)
- `~/documents/rclone.conf`(新、含 crypt 層)
- 備份 script 必須明確指新路徑

### v4.5 restore 缺 HERMES_USER_KEY 環境變數 fallback(2026-06-10 14:14 踩坑)
- **情境**:v4.5 `backup_passphrase_recovery()` 支援 `HERMES_USER_KEY` 環境變數(給 cron 用),但 `recover_passphrase_from_drive()` **只支援 `[[ -t 0 ]]` 互動式 prompt**——cron 跑會 fail
- **失敗原因**:v4.5 兩個函式**同步設計時沒對齊**——backup 支援非互動式、restore 沒支援
- **正確做法**:`recover_passphrase_from_drive()` 也加 `${HERMES_USER_KEY:-}` 環境變數 fallback
  ```bash
  if [[ -n "${HERMES_USER_KEY:-}" ]]; then
    user_key="$HERMES_USER_KEY"
  elif [[ -t 0 ]]; then
    read -r -s -p "USER_KEY: " user_key
  else
    err "非互動式、需 HERMES_USER_KEY"
    return 1
  fi
  ```
- **驗證**:`HERMES_USER_KEY=x bash hermes-restore-v4.sh tier2` 成功(2026-06-10 14:14)
- **推廣**:**任何「互動式設計」,準備做 cron 化前必加 `${ENV_VAR:-}` fallback——互動式 prompt 在 cron 必 fail**
