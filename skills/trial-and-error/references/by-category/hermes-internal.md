# Hermes 內部架構 / 工具鏈 / SOP 試誤條目

> 集中收容：cron / gateway / profile / config / AGENTS.md / keyword 觸發 / 備份等內部工具鏈的 L2 試誤條目
> 寫法：問題情境 + 失敗原因 + 正確做法 + 驗證命令

---

## 2026-06-10（最新）

### `hermes -p X chat` 只讀 SOUL.md、不自動載入 persona.md（engineering-lead 建立時的關鍵發現，第二類「看起來建好了但實際沒生效」）

**症狀**：
- 寫了 10KB+ 的 persona.md（4 個核心決策 + 6 步工作流 + 12 個禁止事項）
- sub-agent 啟動新 session 時**只回答赫米斯 SOUL 核心信念**（耗盡配額/有主見/先查再問/用能力換取信任）
- **完全不知道自己的 4 個核心決策**（B/B/C/B）、不知道在 handoff chain 的位置

**根因**：
`hermes -p <name> chat` 啟動 sub-agent 時**只讀 `<profile>/SOUL.md`**，**不會自動讀 `<profile>/persona.md`**。SOUL.md 跟 persona.md 是兩種不同檔案：
- `<profile>/SOUL.md` ✅ sub-agent 啟動時自動載入 → 決定 LLM 的「語氣」跟「核心信念」
- `<profile>/persona.md` ❌ sub-agent **不會**自動載入 → 必須在 SOUL.md 內引用、或在主 session 內手動讀
- `<profile>/skills/<X>/SKILL.md` ✅ sub-agent 載入（按需）→ 跟 persona 獨立

**為什麼 system-architect 跟 engineering-lead 行為不同**：
- system-architect 之所以能直接回答 6 個核心決策，因為它的 SOUL.md 頂部**已經含完整 persona 摘要**（4.9KB SOUL.md 有 persona 段）
- engineering-lead 之所以失敗，因為 SOUL.md 是 default clone 的通用版、**完全沒含 persona 摘要**

**正確做法**：

1. **在 SOUL.md 頂部插入 persona 摘要**（不是抄整份 persona）：
   - 4 個核心決策（每個 1 行）
   - 在 handoff chain 的位置（誰 → 我 → 誰）
   - 與上下游關係（讀什麼檔、寫什麼檔）
   - 禁止事項（3-5 條）

2. **用 `patch` 工具做頂部插入**（避免破壞原 SOUL 內容）：
   - `patch(old_string='# SOUL.md - Who You Are', new_string='# <New Agent> — <Role> Persona\n\n[摘要]\n\n---\n\n# SOUL.md - Who You Are')`

3. **驗證 SOP**（每個常駐 profile 必跑）：
   ```bash
   hermes -p <name> chat -q "用一句話回報: 你的 N 個核心決策是什麼?" --cli
   # 預期: 回答自己的決策
   # ❌ 失敗: 回答 hermes 預設 SOUL 核心信念（耗盡配額/有主見/先查再問/用能力換取信任）
   ```

**反面案例**：
- 看到 sub-agent 回答 default SOUL 內容 → **不要懷疑 persona.md 寫錯** → **修法是加 SOUL.md 頂部摘要**
- 寫了一堆 SOUL.md 改完也沒動 → 別懷疑 hermes 沒載入 → 確認 `grep prompt_builder.py:1414` 載入的是 `<profile>/SOUL.md`

**配套**：
- persona.md 仍可保留完整版（給主 session 手動讀、或未來擴展用）
- SOUL.md 引用 persona 即可：「詳見 `persona.md`」
- 每個常駐 profile 建立時的 **Step 5.7 端到端真實跑驗證** 必含這個 SOP（驗證 sub-agent 真的套用 persona）

**If→Then**：
- **If** 任何常駐 profile 的 SOUL.md 沒含 persona 摘要 **Then** sub-agent 啟動時不知道自己的決策 → **修法：加到 SOUL.md 頂部**
- **If** 寫了 10KB+ persona.md 但 sub-agent 答 default 內容 **Then** SOUL.md 頂部插入 persona 摘要、不是改 persona.md
- **If** 想保留完整 persona 在 persona.md **Then** 在 SOUL.md 加「詳見 `persona.md`」引用即可

**驗證**（2026-06-10 engineering-lead 真實案例）：
- 修前：`hermes -p engineering-lead chat -q "回報 4 個核心決策" --cli` → 回答「耗盡配額/有主見/先查再問/用能力換取信任」（default SOUL）
- 修後（patch SOUL.md 頂部插入 50 行 persona 摘要）：`hermes -p engineering-lead chat -q "回報 4 個核心決策" --cli` → 回答「(1) B 規劃+平行寫 code (2) B gh CLI+git+GitHub (3) C 雙維度交叉 (4) B 只管當下 sprint」（自己的決策）

**相關條目**：
- [[hermes-config-layout#SOUL.md 永遠在 HERMES_HOME 根目錄、不在 memories/]]（第一類「看起來建好但沒生效」）
- [[hermes-config-layout#persistent-profile-sop]]（Step 2.5 寫 SOUL.md、Step 5.7 端到端驗證、SOUL.md vs persona.md 載入機制）

---

### 跨 profile 寫入有 soft-guard,需 `cross_profile=true` bypass（2026-06-10 從 engineering-lead 建立踩到、第 3 次撞到）

**症狀**：
從 `default` profile 寫進新 profile 的 `skills/<X>/SKILL.md` 被擋：
```
Cross-profile write blocked by soft guard:
  <file> belongs to Hermes profile '<other>', but the agent is running under profile 'default'.
  To bypass this guard after explicit user direction, retry with cross_profile=True.
```

**根因**：
- `write_file` / `patch` 預設只寫當前 active profile（通常 default）
- 跨 profile 寫入有 soft guard（不是硬阻擋、會提示 retry with cross_profile）
- 觸發條件：當前 active profile ≠ 目標 profile 的目錄

**正確做法**：

1. **明確加 `cross_profile=True` 參數 bypass**：
   ```python
   write_file(path="/home/hoonsoropenclaw/.hermes/profiles/<target>/skills/<X>/SKILL.md", content=..., cross_profile=True)
   patch(path=..., old_string=..., new_string=..., cross_profile=True)
   ```

2. **前提**：使用者已明確指示「動工」或「建好」— 這就是 explicit user direction
3. **警告**：**不要**為了省事預設 `cross_profile=True` 開著 — 會繞過所有 profile 邊界、可能誤寫到其他 profile
4. **驗證**：寫完用 `hermes -p <target> skills list` 看是否 enabled（不同 profile 看到的 `skills/` 不一樣）

**常見踩坑情境**：
- 從 default profile 用 `write_file` 寫 `~/.hermes/profiles/consumer-researcher/skills/...` ❌
- 從 default profile 用 `write_file` 寫 `~/.hermes/profiles/system-architect/skills/...` ❌
- 從 default profile 用 `write_file` 寫 `~/.hermes/profiles/engineering-lead/skills/...` ❌
- **修法**: 全部加 `cross_profile=True`（確認使用者已明確指示）

**配套**：
- 一次寫多個檔案要每個都加 `cross_profile=True`（不能只加第一個）
- 寫完 cross-profile 後必 `hermes -p <target> skills list` 確認 enabled
- 偶爾需要切換到目標 profile (`hermes -p <target> chat`) 確認 sub-agent 看得見

**If→Then**：
- **If** 跨 profile 寫入被擋 **Then** 加 `cross_profile=True`、不繞路 debug「為什麼寫不進去」
- **If** 不知道要 `cross_profile` 還是 `default` **Then** 看目標路徑在 `~/.hermes/profiles/<X>/` 還是 `~/.hermes/` 根目錄
- **If** 預設 `cross_profile=True` 開著 **Then** 危險 — 會繞過 profile 邊界

**驗證**（2026-06-10 真實案例）：
- 修前：4 個 `write_file` 呼叫 engineering-lead profile skill 全部失敗（`write_file has failed 4 times`）
- 修後：4 個 `write_file(path=..., cross_profile=True)` 全部成功、4 個 skill 都 enabled

**相關條目**：
- [[hermes-config-layout#persistent-profile-sop]]（Step 3 提到這個 guard）
- [[orchestrator-worker-parallel-architecture]]（worker 跨 profile 寫入也會觸發）

---

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

### v4-backup-tier2-daily 加密 OK ≠ Drive 有新檔(2026-06-10 從這次對話歸納)
- **情境**:`v4-backup-tier2-daily`(02:30)原本 script 寫 `hermes-secrets-encrypt.sh`(沒加 `--upload-drive` flag),**本地加密成功**、daily-summary 看 log 報「OK」、但 Drive 上完全沒新檔 — 連續 3 天加密檔都留在 `~/.cache/hermes-secrets-staging/` 沒推到 Drive
- **症狀**:`hermes-secrets-encrypt.sh` 預設行為是「加密到本地 + 不上傳」(需手動加 `--upload-drive`),`v4.5` 完整化時 v4 主腳本 `hermes-backup-v4.sh --tier2` 跑 `tier2_drive()` 才會觸發 `backup_passphrase_recovery` + `upload_drive_restore_readme` + 自動傳 `--upload-drive` 給 encrypt
- **失敗原因**:cron 設 script 寫錯 — 應該用 `hermes-backup-v4.sh --tier2 --upload-tier2` 當入口,不是直接呼叫底層 `hermes-secrets-encrypt.sh`(會繞過 v4 完整流程)
- **正確做法**:
  1. v4-* cron 的 script 一律用 `hermes-backup-v4.sh` 當入口(`--tier1` / `--tier2` / `--upload-tier2` / `--dry-run`)
  2. 底層 `hermes-secrets-encrypt.sh` 留給 v4 主腳本內部呼叫、不直接掛 cron
  3. **驗證 cron 跑了什麼**=`grep -E 'name|script' ~/.hermes/cron/jobs.json | grep -B1 'hermes-secrets' | head -5` 應該找不到(找到 = cron 繞過 v4)
- **驗證**:
  - 修前:2026-06-08/09/10 三天 02:30 log 寫「OK: Encrypted 114M」+「Skipping Drive upload」= 加密成功但 Drive 沒新檔
  - 修後:2026-06-10 16:22Z 手動觸發 `v4 --tier2 --upload-tier2` → Drive `secrets/` 有 130M 082230Z 新檔、`passphrase-recovery/` 也有 082239Z 新檔
- **推廣**:**任何「看起來跑完 = 備份成功」的 cron 場景,都要 grep 外部儲存(GitHub/Drive/S3)實際看有沒有新物件**,不能只信本地 log 的「OK」。每日驗證 SOP 見 `agent-system-backup` skill 的 verify-recovery-chain.sh
- **相關條目**:[[hermes-internal#N100 同時存在 v3 / v4 兩份備份腳本,腳本歧義會誤導(2026-06-10 踩坑)]]

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


---

### 平行架構 v3_4_workers 實測 Token 預估(2026-06-10 system-architect 真實驗證)

**情境**:system-architect 跑技能/語言交換平台 Step 3-6,4 個 web-worker 完全平行(context 隔離)
**時間**:8.1 分鐘(v1 預估 60-90 分鐘 → **89% 加速**)
**Token 消耗**:627K(4 個 worker 各 45K-312K)

**症狀**:之前在 SKILL.md 寫 v3 模式「Token 200-320K、跟 v1 差不多」這種**沒實測過的預估**。實測 v3 比 v1 多 **214%**(627K vs 200K),預估**嚴重低估**。

**根因**:
- 4 個 worker 各自讀取 Step 1-2 報告(30KB) + 各自寫出 5-10K 對話 + 各自思考推論
- 主 session 還要做對齊整合(+20K)
- **每個 worker 都要付「讀上游 + 思考 + 寫出」的成本**,不是只算最後寫出來的檔案大小

**教訓**:
- 寫「v3 跟 v1 差不多」這種**沒實測過**的預估是危險的——會讓使用者誤判成本、選錯模式
- 真實情境下平行模式 token 是單線的 **2-3 倍**(不是 1.3-1.5 倍)
- **價值在「省時間」不是「省 token」**,要把這個 trade-off 寫進 SOP

**解法 — 真實 Token 預估公式**:
```
v1_single ≈ 任務複雜度 × 1.0x
v2_3_workers ≈ 任務複雜度 × 1.5-2.0x
v3_4_workers ≈ 任務複雜度 × 2.5-3.5x
mixed ≈ 任務複雜度 × 1.5-2.0x
```
- 任務複雜度:L 等級約 200K、 M 約 80K、S 約 30K(主 session 單線估算)
- 每個 worker 平均消耗 50K-300K 視複雜度而定

**複雜度對 Token 影響(實測分布)**:
| Worker 任務 | 複雜度 | 實際 Token |
|------------|--------|-----------|
| B (元件圖 7 元件) | 低 | 45K |
| A (容器圖 14 整合) | 中 | 120K |
| C (DB 8 表 + ER) | 中高 | 149K |
| D (API 25+ 端點) | 高 | 312K |

**預防**:
- 寫任何「平行/序列成本預估」SOP 前必先**實測一次**,不要用「差不多」這種模糊詞
- 在 persona/SKILL.md 開個「**真實數據(2026-06-10 實測)**」段,定期更新
- 對使用者解釋 v3 時,主動說「Token 會多 2-3 倍、但時間省 80%+」不要藏 trade-off

**If** 設計任何 Orchestrator + N 個子代理的架構 **Then** 先實測 1 次拿真實 Token 數據、再寫進 SOP 預估
**If** 使用者問「v3 會不會比 v1 貴」 **Then** 直接給「2-3 倍」數字、不要給「差不多」這種模糊答案
**If** 任務是「趕時間、預算不重要」 **Then** v3_4_workers 適合
**If** 任務是「預算重要、可以等」 **Then** v1_single 適合
**If** 中間值 **Then** v2_3_workers

**驗證**:2026-06-10 技能/語言交換平台架構 Step 3-6
- v3 平行: 8.1 分鐘, 627K tokens
- v1 對照(預估): 60-90 分鐘, 200K tokens
- **時間節省 67 分鐘(89%)、Token 多 428K(+214%)**


---

### 多 sub-agent 平行產出的對齊契約 SOP(2026-06-10 system-architect v3 模式實戰)

**情境**:Orchestrator 派 N 個 web-worker 平行產出 1 份完整文件(架構/資料庫/API 等),N 個 worker 完成後**主 session 要整合成 1 份**。**對齊失敗 = 整合時間 + 返工**,可能比單線跑還慢。

**症狀(沒對齊契約會怎樣)**:
- 4 個 worker 各自命名「UserService」「UserController」「users 表」「/users」——但**有些叫 user 複數、有些叫 user 單數**
- 容器 A 選 PostgreSQL、worker B 假設是 MySQL → 整合時欄位型別對不上
- worker C 的欄位命名是 snake_case(`created_at`)、worker D 的 JSON 用 camelCase(`createdAt`)→ API 回應對不上 schema

**根因**:LLM sub-agent **沒看過其他 worker 的產出**——只看 prompt 內的 spec 寫什麼就寫什麼,容易出現命名/欄位/型別不一致。

**解法 — 3 段對齊契約 SOP**:

#### 階段 1:_plan.md 寫對齊契約(派遣前)

在 `_plan.md` 內明確定義跨 worker 的「契約」:

```markdown
## 對齊契約(3 個 worker 之間要對得起來)

| 契約 | 來源 | 必須對齊 |
|------|------|---------|
| 容器命名 | Worker A | Worker B 的元件必須住在 A 定義的容器內 |
| 服務命名 | Worker B | Worker D 的 API 路徑必須對得起 B 定義的 Service |
| 資料表命名 | Worker C | Worker D 的 API 回應欄位必須對得起 C 的 schema |
| 命名風格 | 全員 | snake_case(Python/PostgreSQL)/ camelCase(JSON API) |
| 容器技術棧 | Worker A | B/C/D 必須假設 A 選的技術,不能另選 |
```

**5 個常見契約**:容器名、服務名、資料表名、命名風格、技術棧假設。

#### 階段 2:主 session 整合前先做對齊檢查(整合時)

不要直接合併 4 份檔案。先**讀 4 份 + 比對命名**:

```bash
# 1. 列出每個 worker 用的「服務名」/「表名」/「端點前綴」
for f in _raw/architect/worker-*.md; do
  echo "=== $f ==="
  grep -E "^(\s*)?(UserService|MatchingService|users|matchings)\b" "$f" | head -5
done

# 2. 比對是否有不一致(grep 找一個名字只在某些 worker 出現)
grep -l "UserService" _raw/architect/worker-*.md
grep -l "UserService" _raw/architect/worker-B-components.md
# 兩個都找不到 = 該 worker 用別的名字(不一致)
```

#### 階段 3:整合後加 §對齊檢查段(交付物)

每份整合後的交付物第一節加「**對齊檢查**」表格,標明:
- 容器名 ↔ 元件名 ↔ 表名 ↔ API 端點,**全部對齊**(✓/✗)
- 哪個 worker 跟其他人命名不一致
- 5 個架構盲點的對應(全部 3+ worker 都有提到)

```markdown
## §3 對齊檢查(主 session 整合時做的)

| 契約 | 來源 | 對齊狀態 |
|------|------|---------|
| 容器命名 | A 定義「API Server (Node.js 20 Fastify)」 | ✓ B 的 *Controller/*Service 都在 A 定義的 API Server 內 |
| 服務命名 | B 定義 7 個 Service | ✓ D 的 API 端點前綴(/users /matchings /orders)跟 B 對應 |
| 技術棧一致性 | A 選 Node.js 20 + Fastify + tRPC + Drizzle + Supabase PG | ⚠️ 跟上游預設 Python 不同,但 A 選的也是合理主流 |
| 5 個盲點對應 | §1.5 預設建議 | ✓ A/B/C/D 全部採用預設(無 [架構決策待釐清] 提出) |
```

**實戰數據(2026-06-10 system-architect v3 模式)**:
- 4 個 worker 平行 8 分鐘完成
- 主 session 整合 + 對齊檢查花 5 分鐘(讀 4 份 + 寫整合 + 加對齊段)
- 整合後 3 份文件 116KB、對齊 0 錯誤
- **沒有對齊契約的話**:整合可能 30+ 分鐘、且可能留隱藏 bug(API 端點對不上資料表)

**預防**:
- 派 N 個 worker 平行產出「**會被主 session 整合**」的文件時,**_plan.md 必含對齊契約段**
- 對齊契約 5 個:**容器名 / 服務名 / 表名 / 命名風格 / 技術棧**
- 主 session 整合前先做對齊檢查(grep + 命名比對)
- 整合後的交付物第一節必含「對齊檢查」表格

**If→Then**:
- **If** 派 ≥ 2 個 worker 平行產出文件 **Then** _plan.md 必含「對齊契約」段
- **If** 主 session 整合時發現命名不一致 **Then** 改主 session 的整合文件,不要回去叫 worker 重跑(重跑成本高)
- **If** worker 寫出的命名跟對齊契約不一致 **Then** 在整合時標 ⚠️ + 列出不一致點(誠實,不裝懂)
- **If** 看到 worker 用了「未在契約內」的技術/命名 **Then** 視情況:(a) 接受(若合理)、(b) 改契約叫其他 worker 對齊(成本高)、(c) 標 [待釐清] 不裝懂


---

### SOUL.md 永遠在 HERMES_HOME 根目錄、不在 memories/（2026-06-10 從 SOUL.md 沒生效 bug 歸納）

**症狀**：使用者寫的完整 persona（8957B Super Learner 宣言）沒生效、AGENTS.md「啟動程序」寫「讀取 SOUL.md」沒明指路徑

**根因**：`agent/prompt_builder.py:1414` `load_soul_md()` 走 `get_hermes_home() / "SOUL.md"` 讀根目錄、不是 `memories/SOUL.md`。AGENTS.md 寫「讀取 SOUL.md」沒指路徑會誤導（事實上曾經被誤導過、寫錯位置），使用者寫了 8K+ 內容但完全沒生效。

**解法**：
1. 任何時候編輯/新增「重要檔」、先 grep hermes 程式碼（`prompt_builder.py` / `system_prompt.py`）確認讀哪裡
2. 跟 AGENTS.md 7 個重要檔實際路徑速查表對照
3. 改完用 `cp <新位置> <最終位置>` 同步到 hermes 會讀的位置
4. 修 AGENTS.md「啟動程序」段、加 ⚠️ 標記寫「SOUL.md 在 `~/.hermes/SOUL.md`、不是 `memories/SOUL.md`」

**預防**：
- AGENTS.md 啟動程序段必明寫每個重要檔的**實際路徑**
- 加「讀哪/編輯時改哪」速查表（防止未來再寫錯位置）
- SOUL.md / AGENTS.md / IDENTITY.md 等「人格系統檔」編輯後必跑 `hermes --version` + `hermes status` 確認 hermes 仍能正常啟動

**If→Then**：
- **If** 任何時候編輯/新增「重要檔」 **Then** 必先 grep hermes 程式碼確認讀哪裡、不靠 AGENTS.md 文字推測
- **If** SOUL.md 寫錯位置（persona 沒生效） **Then** `cp memories/SOUL.md SOUL.md` 同步到根目錄
- **If** 重要檔路徑不明 **Then** AGENTS.md 啟動程序段必明寫路徑、不能只寫檔名

**相關條目**：
- [[hermes-config-tuning#SOUL.md 跟其他重要檔交叉比對 6 個衝突修正]]
- [[workspace-folder-layout#根目錄檔案盤點三類法]]

---

### AGENTS.md 7 個重要檔必建「實際路徑速查表」(讀哪/改哪/備份哪)（2026-06-10 從修 SOUL.md bug 歸納）

**症狀**：使用者（或 agent）寫 persona / 重要設定時、不確定該寫到根目錄還是 `memories/`、寫錯位置 persona 沒生效；多個重要檔分散在不同目錄、沒有統一速查

**根因**：AGENTS.md「啟動程序」段原本只寫「讀取 SOUL.md」沒指路徑；7 個重要檔的路徑散落在 3 個目錄（根目錄、memories/、AGENTS.md 內含清單），沒有視覺化速查表。

**解法**：
1. AGENTS.md 啟動程序段必含 7 個重要檔速查表（**3 欄**：hermes 啟動時讀哪 / 編輯時改哪 / 備份時備到哪）
2. 必含「歷史教訓」段（為什麼當初這樣設計、避免重複犯同樣錯）
3. 「SOUL.md 在根目錄、不在 memories/」之類容易誤會的路徑必加 ⚠️ 標記
4. 7 個重要檔分組：
   - **hermes 啟動時主動讀**：`SOUL.md`（根目錄）、`USER.md`（memories/）、`MEMORY.md`（memories/）
   - **hermes 不主動讀**（給 agent 查閱用）：`AGENTS.md`（memories/）、`HEARTBEAT.md`（memories/）、`IDENTITY.md`（memories/）、`TOOLS.md`（memories/）

**預防**：
- 7 個重要檔是「人格系統」、路徑速查表比檔名清單更有用
- 修完速查表必跑 `hermes --version` 確認 hermes 仍能正常啟動
- 改完必同步更新 hermes-backup-coverage-check.sh 的「v4 同步清單」對照

**If→Then**：
- **If** 重要檔職責不明 **Then** AGENTS.md 必建路徑速查表(讀哪/改哪/備份哪三欄)
- **If** 修完路徑速查表 **Then** 必跑 hermes 啟動測試 + coverage check 雙驗證
- **If** 新增重要檔 **Then** 必同步更新 AGENTS.md 速查表 + INVENTORY.md 同步清單

**相關條目**：
- [[hermes-internal#SOUL.md 永遠在 HERMES_HOME 根目錄、不在 memories/]]
- [[hermes-backup-design-pitfalls#v4 備份腳本只列 7 個目錄+1 個檔,但 ~/.hermes/ 根目錄有 20+ 個路徑]]

