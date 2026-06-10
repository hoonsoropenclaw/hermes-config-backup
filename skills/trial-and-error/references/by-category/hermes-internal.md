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
