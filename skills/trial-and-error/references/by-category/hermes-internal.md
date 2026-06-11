---

### hermes-config-backup-daily prompt 殘留 args 導致 script path 錯誤（2026-06-11 修復）

**症狀**：
- `hermes-config-backup-daily` (65f2dc35) last_error：`Script timed out after 3600s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes_v3.sh`
- jobs.json 顯示 `script: 'hermes-backup-v4.sh'` 但 Scheduler 報 `backup_hermes_v3.sh`

**根因**：
- 之前某次 `hermes cron edit --script 65f2dc35 'hermes-backup-v4.sh --tier1'` 把 `prompt` 汙染成 `'hermes-config-backup-daily: hermes-backup-v4.sh --tier1'`
- prompt 欄位殘留 script+args，Scheduler 可能從 prompt 構造 script path（即使 jobs.json script 是對的）
- 另外 `timeout_seconds: 3600` 仍 timeout → 可能同時觸發 Scheduler `_get_script_timeout()` 的預設 600s 上限（需要重啟 gateway 才會生效）

**正確做法**（已落地）：
```python
# 修復 jobs.json
with open('/home/hoonsoropenclaw/.hermes/cron/jobs.json') as f:
    d = json.load(f)
for j in d['jobs']:
    if '65f2dc35' in j['id']:
        j['prompt'] = None          # 清除 args 殘留
        j['script'] = 'hermes-backup-v4.sh'  # 確認 script 是檔名
        j['no_agent'] = True
with open('/home/hoonsoropenclaw/.hermes/cron/jobs.json', 'w') as f:
    json.dump(d, f, indent=2)
```

**驗證命令**：
```bash
# 確認 prompt 已清空
python3 -c "import json; d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json')); [print(j['name'], 'prompt=', repr(j.get('prompt'))) for j in d['jobs'] if '65f2dc35' in j['id']]"
# 預期：prompt= None
```

**If→Then**：
- **If** cron job 的 last_error 顯示執行了「另一個 script」但 jobs.json script 是對的 **Then** 檢查 prompt 是否被汙染、設為 null
- **If** jobs.json timeout_seconds 設 3600 但仍 timeout at 600s **Then** 可能是 Scheduler 預設上限、需要改 config.yaml 或重啟 gateway

---

### coverage check 假 warning：`.skills_prompt_snapshot.json` 是隱藏檔不是根目錄檔（2026-06-11 修復）

**症狀**：
- `hermes-backup-coverage-check.sh` 多次報 ⚠️ `'.skills_prompt_snapshot.json' 本機有但 v4 ROOT_SINGLE_FILES 沒列（建議加）`
- 但 v4.sh ROOT_SINGLE_FILES 早已列了 `.skills_prompt_snapshot.json`

**根因**：
- 檔案實際在 `~/.hermes/.skills_prompt_snapshot.json`（隱藏檔，dot-file）
- coverage check 對根目錄 grep 找到的是 `.skills_prompt_snapshot.json`（dot prefix）
- INVENTORY.md 描述「prompt snapshot（v4.6 新增）」暗示它是根目錄檔，導致誤解
- v4.sh ROOT_SINGLE_FILES 確實有 `.skills_prompt_snapshot.json`（正確）
- coverage check 誤判是因為 INVENTORY.md 描述誤導

**正確做法**（已落地）：
1. 修正 INVENTORY.md 描述：`'.skills_prompt_snapshot.json' | prompt snapshot（存在於 `~/.hermes/.skills_prompt_snapshot.json`，非根目錄）|`
2. coverage check 現在 ✅ PASS（不需要再改 v4.sh）

**驗證命令**：
```bash
# 確認 hidden file 存在
ls -la ~/.hermes/.skills_prompt_snapshot.json
# 確認 coverage check PASS
bash ~/.hermes/scripts/hermes-backup-coverage-check.sh
# 預期：✅ PASS
```

**If→Then**：
- **If** coverage check 報「'.skills_prompt_snapshot.json' 本機有但 v4 ROOT_SINGLE_FILES 沒列」**Then** 先 `ls ~/.hermes/.skills_prompt_snapshot.json` 確認是不是隱藏檔（在 `~/.hermes/` 而非 hermes 根目錄）——如果是，INVENTORY.md 描述需修正但 v4.sh ROOT_SINGLE_FILES 不需要列它
- **If** 新增任何 dot-file 進 v4 同步清單 **Then** INVENTORY.md 必加「存在於 `~/.hermes/.hlen`」說明、避免誤判

---

### 改 `hermes-agent` 源碼後 gateway 重啟卡 3 分鐘是正常（systemd `Type=simple` 沒 `TimeoutStopSec`）（2026-06-11 觸發 cycle 識別）

**症狀**：
- 改完 `cron/scheduler.py` 跑 `sudo systemctl restart hermes-gateway.service`
- Terminal 卡 60-90 秒 timeout、誤以為 service 卡死
- `pgrep -af "hermes_cli.main gateway"` 還看到舊 PID（2540916 或 2677420）
- `systemctl status` 顯示 `Active: deactivating (stop-sigterm) since X min ago`

**根因**：
- `/etc/systemd/system/hermes-gateway.service` 設 `Type=simple`、**沒設 `TimeoutStopSec`**
- systemd 預設 90s graceful timeout → 過了才送 SIGKILL 強制殺
- 為什麼 graceful shutdown 慢：gateway 跑 async telegram long polling、收到 SIGTERM 後要等 in-flight agent request 跑完（metacognitive 87s）+ telegram API 釋放連線
- **加總**：SIGTERM 後 60-180 秒才真的退、然後 `Restart=always` 立刻起新 PID

**正確做法**（已驗證 3 次重啟都是這模式）：
1. 跑 `sudo systemctl restart hermes-gateway.service`、**不要急著手動 kill**
2. 等 3-5 分鐘（journalctl 看 `Started hermes-gateway.service` 跟 `Main process exited`）
3. `pgrep -af "hermes_cli.main gateway"` 看到新 PID = 重啟成功
4. 驗證新 PID 載了改動：`md5sum <改的檔案>` 跟新 PID 的 `lsof -p <pid> 2>/dev/null | grep <檔案>`（systemd 啟動後會 import 載入）

**If→Then**：
- **If** 跑 `sudo systemctl restart` 後 terminal 60s timeout **Then** 不要慌、看 journalctl 跟 PID 變化、等 3-5 分鐘
- **If** 5 分鐘後新 PID 還沒出來 **Then** 才需手動 `systemctl kill -s SIGKILL hermes-gateway` 強殺
- **If** 收到 `Background process completed` 通知但 service 沒新 PID **Then** 重跑 systemctl status 看 `Restart=` counter、有異常時手動重啟

**預防**（systemd service 改 TimeoutStopSec 加速）：
- 在 `/etc/systemd/system/hermes-gateway.service` 加 `TimeoutStopSec=10s`（10 秒 grace 期間讓 telegram long polling 自己退、然後 SIGKILL）
- 但要先驗證 hermes 收到 SIGTERM 後能正常處理（沒 in-flight agent 還在算東西）

**完整 7 步 SOP**（含 MCP 重連驗證、patch 工具繞道、If→Then 配套）：`references/sops/hermes-source-restart-sop.md`（SOP-7）

---

### `sync_md_files.py` 部署依賴 systemd service 環境變數——cron 子進程拿不到 `VERCEL_API_TOKEN`（2026-06-11 觸發 cycle 識別）

**症狀**：
- `md-files-daily-sync` (67fc8c74e369) cron 跑時 `[FAIL] Deploy failed` 永遠 exit 1
- 從互動式 terminal 跑 `python3 /home/.../sync_md_files.py` 卻 exit 0（deploy 成功）
- `last_status: ok` 一直顯示（stale state、某次偶然成功狀態沒被翻）
- 真正 cron 跑時其實每次都失敗

**根因**：
- `sync_md_files.py` 的 `deploy()` 函式 (line 115) 從 `os.environ.get("VERCEL_TOKEN")` 拿 token
- 互動式 shell 有 `~/.bashrc` 載入 `VERCEL_API_TOKEN` → 拿到 token、deploy 成功
- systemd `hermes-gateway.service` 的 `Environment=` 列表**沒設 `VERCEL_TOKEN` 或 `VERCEL_API_TOKEN`** → cron 子進程 subprocess 拿 None → 立即 return False
- `last_status: ok` 是過去某次從互動式環境跑出來的偽成功（**或 scheduler 寫 status 有 bug**）

**驗證**：
```bash
# 1. 確認互動式 shell 有 token
echo "shell VERCEL_API_TOKEN: ${VERCEL_API_TOKEN:-(unset)}"

# 2. 確認 systemd 沒設
grep -i vercel /etc/systemd/system/hermes-gateway.service
# 結果: (空)

# 3. 確認 cron 子進程確實拿不到
```

**正確做法**（兩選一，**動 service 必須先取得使用者授權**）：

**選項 A：systemd 注入 .env（推薦，但要 user 同意改 service）**
```bash
# /etc/systemd/system/hermes-gateway.service 加
EnvironmentFile=/home/hoonsoropenclaw/.hermes/.env
# 然後
sudo systemctl daemon-reload
sudo systemctl restart hermes-gateway.service
```
- `.env` 本來就 mode 0600、token 安全性不變
- 但這影響所有 cron 子進程的環境載入方式、未來要重啟 service

**選項 B：sync_md_files.py 加 fallback（不改 service）**
```python
# line 117 改成
if not token:
    print("[SKIP] VERCEL_API_TOKEN not set, skipping deploy (cron env)")
    return True   # 算成功、讓 cron 不要 fail
```
- 改 script 簡單、不動 service
- 但失去「deploy 失敗要通知」的能力

**If→Then**：
- **If** 任何 cron script 從互動式 shell 跑成功但從 cron 跑失敗 **Then** 第一個嫌疑是 systemd service 沒設相關環境變數（`grep <VAR> /etc/systemd/system/hermes-gateway.service`）
- **If** 收到 `last_status: ok` 但實際 cron 跑時 deploy 失敗訊息 **Then** `last_status` 是 stale、要看 journalctl 跟 cron output 確認真實狀態
- **If** 想讓 cron 拿到 secret 環境變數 **Then** `EnvironmentFile=` 注入 .env 是最標準做法、不要塞 `Environment=` inline（會被 systemd 印出來）
- **If** `last_status` 跟實際行為對不起來 **Then** 寫進 trial-and-error 或用 `clarify` 問使用者是否清掉 stale state

---

### `last_status` 跟 jobs.json 修復狀態完全解耦——手動驗證成功不等於翻 last_status（2026-06-11 觀察歸納）

**症狀**：
- 手動 `bash <script>.sh` 跑成功、exit 0
- jobs.json 的 `script`/`prompt`/`timeout_seconds` 欄位都修對
- 但 `hermes cron list` 仍顯示 `last_status: error` 跟舊的 `last_error` 文字
- 讓 Phase 1.5 誤以為「還沒修好」、觸發重複修復循環

**根因**：
- `last_status` / `last_error` / `last_run_at` **只在 `_process_job()` 跑完 scheduler tick 才會被 `mark_job_run()` 寫入**（scheduler.py line 2129）
- 手動 `bash <script>.sh` **不走 scheduler 流程**、**不會**更新 jobs.json
- 「真實跑成功」vs「last_status 翻成 ok」是**兩件事**——前者證明 script OK、後者證明 scheduler 真的跑完

**具體觸發情境**（2026-06-11）：
- 06:53 cycle 修了 v4-backup-tier1-daily / hermes-backup-coverage-check / hermes-config-backup-daily / v4-backup-tier2-daily 的 jobs.json
- 08:16 / 09:11 / 09:35 三次 cycle 都看到 last_status: error
- 手動跑全 12 個 script 過、jobs.json 內容已對
- 但**必須等下次 cron 自動跑完才會翻**（v4-backup-tier1 02:00 / tier2 02:30 / coverage 04:00 / config 03:00）
- 也就是說「修對」跟「last_status 顯示 ok」**中間有 6~24 小時的時間差**

**正確做法**（**已不再誤判的 SOP**）：
1. Phase 1.5 看到 `last_status: error` **不要立刻**觸發緊急修復
2. 第一步：手動跑該 script + `bash -n` syntax check + 看 cron output dir
3. 第二步：交叉驗證 jobs.json（`script`/`prompt`/`timeout_seconds` 跟 trial-and-error 建議值一致）
4. 第三步：以上都過 → **這是 stale state**、不是新 bug
5. 第四步：用 `hermes cron run <id>` 立即觸發、**強迫** scheduler 跑一次更新 last_status

**驗證**：
```bash
# 1. 跑 hermes cron run 強迫 scheduler 跑
hermes cron run <job_name>     # schedule 到下一個 tick
hermes cron tick                 # 跑一次所有 due job

# 2. 看 last_status 是否翻成 ok
python3 -c "
import json
d = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name') == '<job_name>':
        print('last_status:', j.get('last_status'))
        print('last_error:', j.get('last_error'))
        print('last_run_at:', j.get('last_run_at'))
"

# 3. 看 cron output dir
ls -lat /home/hoonsoropenclaw/.hermes/cron/output/<job_id>/
```

**If→Then**：
- **If** Phase 1.5 看到 cron `last_status: error` **Then** **先**手動跑 script 驗證邏輯 + 比對 jobs.json 跟 trial-and-error 建議值、**再決定**是否緊急修復（不要直接進 Phase 1-3 緊急修復模式）
- **If** jobs.json 已修、script 手動跑成功、但 `last_status: error` **Then** 用 `hermes cron run` + `hermes cron tick` 立即觸發、**不要等 cron 自然排程**（可以省 6~24 小時）
- **If** 連續 3 個 cycle 看到同樣 `last_status: error` 但手動跑都過、jobs.json 修對 **Then** 確認 scheduler 的 `mark_job_run()` 是否真的有跑、`hermes-gateway` 是否在 active
- **If** `last_status: pending` 跟 `last_status: error` 都需要區分 **Then** pending = 從未跑過（如 `v4recovery2026` 等週日 23:00）；error = 跑過但失敗、且未再跑翻

**預防**（給未來 cycle）：
- 寫進 metacognitive-learner SKILL.md Phase 1.5 段的開頭加「stale state 排除 SOP」
- 或者設計 `hermes cron heal-stale` 指令：把 jobs.json 內 `last_status: error` 但 `last_error` 跟當前 jobs.json script 對不起來的 job 自動觸發

**相關條目**：
- [[hermes-internal#sync_md_files.py 部署依賴 systemd service 環境變數——cron 子進程拿不到 VERCEL_API_TOKEN]] — stale state 也曾出現在這個 job
- [[hermes-internal#改 hermes-agent 源碼後 gateway 重啟卡 3 分鐘是正常]] — 跟 stale state 不同、但都是「時間差導致誤判」類問題

---

### Profile 補 skill 用 `cp -r` vs `symlink` 的差別——`.user-modified` marker 防未來 sync 覆蓋（2026-06-11 觸發 cycle 識別）

**症狀**：
- 給 `engineering-lead` 補 4 個 coding skill（debug / systematic-debugging / writing-plans / tech-debt）
- 用 `cp -r ~/.hermes/skills/<category>/<name>/ ~/.hermes/profiles/<profile>/skills/`
- 未來 `hermes update` 重新 seed 預設 skill 時、會跟手動 opt-in 的這些**不同步**
- 真正危險的情境：未來 hand-edit 這 4 個 SKILL.md（例如加 L3 教訓段落）、下次 hermes update 重新 seed 時**會被原始版覆蓋**

**正確做法**（**已 opt-in 完的 skill 必走**）：
1. opt-in 用 `cp -r` 後、**立即**在 skill 目錄下加 `.user-modified` 標記檔（內容隨意、純粹 marker）：
   ```bash
   touch ~/.hermes/profiles/<profile>/skills/<skill>/.user-modified
   ```
2. 或在 `_meta/` 加 `user-modified-skills.md` 記錄哪些 skill 改過：
   ```bash
   echo "- <skill-name> (modified YYYY-MM-DD: 加了 X L3 教訓)" >> ~/.hermes/profiles/<profile>/skills/_meta/user-modified-skills.md
   ```
3. **未來手動改 SKILL.md 之前**：先確認 `.user-modified` 還在（沒被 sync 覆蓋）
4. **未來手動改完之後**：在 `_meta/user-modified-skills.md` 記錄改了什麼、何時改的
5. **若要真的 sync 回 default bundle**（極少見、只在你確認 default 那邊也該改）：手動把 default 那邊也改、然後下次 `hermes update` 才會同步

**為什麼用 `cp -r` 而不是 `symlink`**：
- **symlink**：`hermes update` 改 default 那邊、會自動同步、但「改 profile 內 SKILL.md」會破壞 symlink
- **cp -r**：手動 opt-in、改 SKILL.md 不影響 default、但**有 sync 衝突風險**（需要 .user-modified 提醒）
- **混合方案**：對**絕對不會改**的 skill 用 symlink（如 general-workflow）、對**會改**的用 cp -r + marker

**驗證**：
```bash
# 1. 確認 opt-in 結果
ls ~/.hermes/profiles/<profile>/skills/ | wc -l
# 應該 +N（N = 補的 skill 數）

# 2. 確認 marker 已加
ls ~/.hermes/profiles/<profile>/skills/<skill>/.user-modified

# 3. 確認 SKILL.md 內容跟 default 一致（剛 opt-in 時）
diff ~/.hermes/profiles/<profile>/skills/<skill>/SKILL.md ~/.hermes/skills/<category>/<skill>/SKILL.md
# 應該沒輸出（完全相同）

# 4. 確認 hermes list 看到 skill 已 enabled
hermes skills list | grep <skill>
```

**If→Then**：
- **If** 給某 profile opt-in 新 skill 用 `cp -r` **Then** 立即加 `.user-modified` marker（touch 或 `_meta/user-modified-skills.md` 記錄）
- **If** 看到某 profile 的 skill 跟 default skill 內容不一致、且沒 `.user-modified` marker **Then** 那是某次 sync 衝突、需手動決定保留哪邊
- **If** 改某 profile 的 SKILL.md **Then** 先確認 `.user-modified` 存在、不存在就 touch、然後才改
- **If** 從其他 profile 看到一樣的 SKILL.md 內容重複 **Then** 表示 `cp -r` 沒去重、可以接受（佔空間但功能沒問題）、或刪重保留 default

**預防**（建議未來改進）：
- 寫進 metacognitive-learner SKILL.md Phase 4 SOP：「改任何 SKILL.md 前必先 touch .user-modified」
- 或在 hermes_agent source code 加 hermes skills install 時自動加 marker（標準化流程）
- 寫進 `~/.hermes/docs/INVENTORY.md` 的「修改影響對照表」段

**相關條目**：
- [[hermes-internal#jobs.json 欄位污染：no_agent cron job 的 `prompt` 欄位被錯誤寫入 script+args]] — 跟 profile skills 維護一樣、都涉及 jobs.json 跟 skills 同步
- [[hermes-backup-sop#改任何備份腳本必同步改 INVENTORY.md + SKILL.md §14.1 改檔對照表]] — 同樣的「改一動要記下」精神

---

**相關條目**：
- [[hermes-internal#jobs.json 欄位污染：no_agent cron job 的 `prompt` 欄位被錯誤寫入 script+args]] — 另一個 cron job 改動的坑
- [[hermes-internal#MCP server `command: python3` 跟 hermes venv PATH 衝突]] — 同樣是 service 環境配置沒考慮到子進程

---

### 代理重塑後 SOP 範例沒跟著同步——典型系統遺留缺陷（2026-06-11 親身修）

**症狀**：
- `consumer-researcher` 在 2026-06-10 從 `market-strategist` 重塑過來（profile + persona + skill 庫全改）
- 但 `references/sops/keyword-triggers-sop.md` 「`@專案` SOP 段」的範例、命令、`SESSION_DIR` 路徑**全部還在用舊名稱**（`market-strategist` / `market-research.md`）
- 已上線 1 天沒人發現（keyword 沒觸發、沒人實際走 SOP）
- 同樣情況：`AGENTS.md` 表格的「現有常駐代理」列還是 2 段、**沒包含後來加的** `system-architect` / `engineering-lead` / `test-engineer`

**根因**（典型的「重塑不同步」）：
- 身份重塑（agent-identity-management 的 Role Pivot）只動了 profile + skill 庫 + persona
- **沒動** 引用舊名的下游檔案（keyword 觸發 SOP 段、handoff README、AGENTS.md 表格、HEARTBEAT.md、INVENTORY.md）
- 「重塑」跟「下游同步」**是兩個動作**、沒人連起來

**正確做法**（**「代理重塑 SOP」必含的下游同步清單**）：

1. **重塑時立刻 grep 整套工作區**找出所有引用舊名的地方：
   ```bash
   grep -rln 'market-strategist' ~/.hermes/ 2>/dev/null
   grep -rln '@專案' ~/.hermes/ 2>/dev/null
   ```
2. **下游同步清單**（5 個固定位置）：
   - `~/.hermes/memories/AGENTS.md` —— 表格內的「現有常駐代理」列
   - `~/.hermes/memories/HEARTBEAT.md` —— 「現況」描述
   - `~/.hermes/memories/references/sops/keyword-triggers-sop.md` —— 觸發 SOP 段（**最容易漏**、因為藏在 references/）
   - `~/.hermes/handoff/_chains/README.md` + `SCHEMA.md` —— 鏈名範例
   - `~/.hermes/handoff/README.md` —— 鏈條圖
3. **每個引用要修對、不只是「換名稱」**：
   - 代理名稱改了
   - 交付物命名可能也改了（`market-research.md` → `consumer-needs-research.md`）
   - 階段數可能增加（從 2 段變 5 段）
   - 範例命令要實際跑得通（`SESSION_DIR` 路徑）
4. **驗證命令**（**改完必跑**）：
   ```bash
   grep -rn 'market-strategist' ~/.hermes/ 2>/dev/null | grep -v '\.bak\.' || echo "✅ 全部清除"
   grep -rn 'consumer-researcher' ~/.hermes/ | wc -l   # 確認新名稱都到位
   ls ~/.local/bin/consumer-researcher                   # 確認 wrapper 存在
   ```
5. **記下「重塑日期 + 下游同步日期」**讓未來 cycle 容易驗證：
   ```markdown
   ## 變更記錄
   - 2026-06-10: 身份重塑（market-strategist → consumer-researcher）
   - 2026-06-11: 下游同步（keyword-triggers-sop.md / AGENTS.md / handoff README）
   - **延遲 1 天才修、原因：keyword 沒實際觸發、沒人發現**
   ```

**If→Then**：
- **If** 接到「重塑 X 代理 / 重新定位 / 換個角色」類任務 **Then** 跑「下游同步清單」（5 個固定位置）、不是只改 profile 跟 skill
- **If** grep 找到引用舊名稱（不只檔名、還有 `SESSION_DIR`、交付物命名、範例命令）**Then** 全部要改、不只是「替換字串」、要確認「改完後實際跑得通」
- **If** SOP 段是 references/sops/ 內的檔案 **Then** 優先順序最高（system 不會自動掃描、容易漏）、動完 profile 必查這個目錄
- **If** 看到「@keyword 觸發 SOP 段還在用舊名」**Then** 這是已上線 1 天的 bug 沒人發現、趕快修、不能等下次觸發才發現
- **If** agent-identity-management 的 Role Pivot SOP 沒列「下游同步清單」**Then** 補上、這是 SOP 缺漏

**預防**（改進 agent-identity-management）：
- 在 `agent-identity-management/references/role-pivot-sop.md` 加「**Step 6: 下游同步（5 個位置必查）**」
- 用 `grep -rln '<old-name>' ~/.hermes/` 模板化
- 同步日期寫進 MEMORY.md「更新記錄」段

**真實案例**（2026-06-11 修）：
- 改了 6 個檔（AGENTS.md / HEARTBEAT.md / keyword-triggers-sop.md / handoff/_chains/README.md / handoff/_chains/SCHEMA.md / handoff/README.md）
- 順帶修了 1 個**重大系統遺留缺陷**：SOP 段範例從 `market-strategist` 改成 `consumer-researcher` + 5 階段標準鏈 + 迴圈反饋 + 未來 keyword 從 `@` 改成 `^`（設計決策見下條）
- grep 驗證 `market-strategist` 全清除（只保留 `_EXECUTION_REPORT.md` 歷史紀錄）

---

### keyword 符號選擇：`^` 給 handoff、`@` 給 skill，明確分工（2026-06-11 設計決策）

**問題**：
- 原本 `@專案` 觸發 handoff pipeline、`@學習` 觸發 `trial-and-error` skill —— **兩個 `@` keyword 共用前綴**
- 視覺容易混淆（人腦看到 `@` 第一反應是 skill）、shell 沒風險、但長期會誤觸發

**評估過的候選**（2026-06-11 session 跑完）：

| 符號 | 鍵盤 | shell 風險 | 評分 | 結論 |
|------|------|----------|------|------|
| `@`（現有） | `Shift+2` | 0 | ⭐⭐⭐ | 視覺混淆 |
| **`^`** | `Shift+6` | 0 | ⭐⭐⭐⭐⭐ | **採用** |
| `§` | 輸入法 | 0 | ⭐⭐⭐ | 輸入摩擦 |
| `&` | `Shift+7` | ❌ background | ❌ | 不用 |
| `*` | `Shift+8` | ❌ glob | ❌ | 不用 |
| `?` | `Shift+/` | ❌ glob | ❌ | 不用 |
| `#` | `Shift+3` | ⚠️ 註解 | ⭐ | 容易吃字 |
| `>` | `Shift+.` | ❌ redirect | ❌ | 不用 |
| `»` | 輸入法 | 0 | ⭐⭐⭐ | Unicode 麻煩 |

**採 `^` 的 3 個理由**：
1. **鍵盤原生**：`Shift+6` 跟 `&` 一樣順、零輸入摩擦
2. **shell 0 風險**：`^foo` 不會被 bash 解析
3. **視覺分工明確**：`^` 給 handoff（隱喻「啟動 / 進入」）、`@` 給 skill（保留現有設計）

**設計**（已落地 2026-06-11）：

| 用途 | 符號 | 範例 |
|------|------|------|
| handoff pipeline | **`^`** | `^專案 我想做技能交換平台` |
| skill 觸發 | **`@`** | `@學習 rclone 配額` |
| 一般對話 | （無前綴）| `今天天氣如何` |

**改動清單**（6 個檔）：
- `~/.hermes/memories/AGENTS.md` —— `@專案` row → `^專案` row、If 規則改「`^` 或 `@`」
- `~/.hermes/memories/HEARTBEAT.md` —— 現況說明 + 改動紀錄
- `~/.hermes/memories/references/sops/keyword-triggers-sop.md` —— SOP 段標題 + 整段現代化
- `~/.hermes/handoff/README.md` —— 鏈條圖說明
- `~/.hermes/handoff/_chains/README.md` + `SCHEMA.md` —— 範例改 `^專案`
- （保留歷史）`_EXECUTION_REPORT.md` 跟 `MEMORY.md.bak.*` 不改

**驗證**：
```bash
grep -rn '\^專案' ~/.hermes/memories/ ~/.hermes/handoff/ 2>/dev/null | wc -l   # 期望 14+ 處
grep -rn '@專案' ~/.hermes/memories/ ~/.hermes/handoff/ 2>/dev/null | grep -v '.bak\.' | grep -v '_EXECUTION_REPORT'
echo '^專案 我想做技能交換平台'   # ^ 不會被 shell 解析
```

**If→Then**：
- **If** 未來想新增 keyword 觸發 `^X` / `@X` **Then** 先在這表格選符號（handoff 用 `^`、skill 用 `@`）、不要混用
- **If** 看到 SOP / 表格 / 鏈名用 `@專案` **Then** 是過時用法、要改成 `^專案`
- **If** 想選其他符號（`§` / `»` / 自訂）**Then** 先跑這表格的 6 個評估維度（鍵盤 / shell / 視覺 / 衝突 / 輸入摩擦 / 未來維護）
- **If** keyword 改符號 **Then** 必走 5 個檔的同步清單（AGENTS.md / HEARTBEAT.md / keyword-triggers-sop.md / handoff README / _chains/）

**預防**（給未來 cycle）：
- 寫進 `references/sops/keyword-triggers-sop.md` 的「未來可能新增 keyword」段、預設用 `^` 開頭
- AGENTS.md 表格加「符號分工說明」永久條目（避免新 cycle 又把 `^` 改成 `@`）

---

### keyword 觸發時「主動延伸 user 語意」是 Rule 12 違規（2026-06-11 親身踩）

**症狀**：
- 使用者說「目前這些常駐代理，之後可能會因為不同工作流程而有不同任務交棒流向順序跟組合，譬如目前建立的是「At符號 學習」這個流程」
- 這句話是**「未來規劃」討論**、不是「建 @符號學習 鏈」執行命令
- 我**主動延伸語意**：「@符號學習 流程 = consumer→product→eng→test 跳過 arch」+ 寫進 handoff README + 寫進 SCHEMA.md
- 還寫了「反編譯/反組譯」鏈的範例（同樣是延伸）
- 使用者當下立刻糾正：「更正 應該是「@專案」才是唯一的鍊」「沒有「@符號學習」這個鍊，我從來沒說過，是你延伸的」

**根因**（典型 Rule 12 違規）：
- 觸發情境是「純討論 / 探勘式問題」、不是「執行任務」（user-collaboration-style Rule 12）
- 我**沒先反問確認**、就**主動延伸 user 語意建具體內容**（Rule 19 已預防但**沒載入**）
- 我**憑印象**把「At 符號 學習」聯想到「@符號學習 鏈」+「反編譯鏈」+ 寫進 SOP

**正確做法**（**討論模式下絕不延伸**）：

1. **收到 keyword 相關訊息時**、**先**載入 `user-collaboration-style` Rule 19 + `AGENTS.md` 表格 + `keyword-triggers-sop.md`
2. **確認「這是執行命令還是討論」**（user-collaboration-style Rule 12）：
   - 使用者說「建 X 鏈」「這個用 ^專案 跑」= 執行
   - 使用者說「可能會」「之後」「譬如」= 純討論
3. **純討論時**、**只**回答使用者問的東西、**不**主動建具體內容
4. **如果 user 語意模糊**、**先反問**（Rule 19）：
   ```
   你說的「At符號 學習」是：
   - 觸發 keyword（@學習 / @專案）？
   - 一個新的 handoff 鏈（取名 @學習鏈）？
   - trial-and-error skill 載入流程？
   - 其他？
   ```
5. **絕不**主動延伸 user 沒明確說的東西（避免「我覺得他意思應該是 X」的 hallucination）

**驗證**（**判斷自己是否在主動延伸**）：
```bash
# 寫 SOP / 改檔前、問自己：
# 1. 使用者訊息裡有沒有「明確說」要建這個？
# 2. 如果只寫 60% 的內容、剩下的 40% 是從哪來的？
# 3. 40% 是 user 講的還是我延伸的？
# 
# 如果 40% 是我延伸的 → 停下來、反問、不要寫
```

**If→Then**：
- **If** 收到含「可能 / 譬如 / 之後 / 之類 / 大概」的 user 訊息 **Then** 純討論模式、不主動延伸建具體內容
- **If** 想主動延伸 user 語意（建具體鏈 / 範例 / 範本）**Then** 先反問確認、不要直接寫
- **If** 已經延伸寫了、user 糾正 **Then** 立即 revert 延伸部分、只保留 user 明確要的 + **記進這個條目**（避免下次再犯）
- **If** 看到自己的回應含「我覺得他意思應該是」「可能他想」「延伸一下」**Then** 立即刪掉、回到 user 明確說的
- **If** 在 SOP / README 寫了 user 沒明確說的「未來鏈 / 範例鏈」**Then** 這是「架構優先於用戶原意」的錯誤延伸、該段必須移除

**真實案例**（2026-06-11）：
- 寫了「@符號學習 鏈」「反編譯/反組譯 鏈」進 handoff README
- 還寫了「鏈型態 A/B/C」進 SCHEMA.md（含 B 重構鏈、沒人要的）
- 第一次 user 糾正：「更正 應該是「@專案」才是唯一的鍊」 → 改 @符號學習 → @專案
- 第二次 user 糾正：「先停止，不要錯誤理解  「＠學習」是我原本設定呼叫試誤學習的技能」「沒有「＠符號學習」這個鍊」→ 理解 @學習 ≠ 鏈
- **教訓**：「未來可能」類訊息 = **純討論**、不是「建範例」綠燈

**預防**（給未來 cycle）：
- 寫進 `user-collaboration-style` Rule 19 加註：「收到 keyword 相關訊息時、**先判斷這是執行還是討論**、**討論模式下不延伸建具體內容**」
- metacognitive-learner Phase 2 加：「回應含『可能 / 譬如 / 之後』時、檢查有沒有不小心延伸」
- 寫進 `references/sops/keyword-triggers-sop.md` 「A/B/C 模式選擇」段加：「B 模式仍需 user 確認具體行為、不能延伸」

**相關條目**：
- [[hermes-internal#身份重塑 ≠ 身份繼承（2026-06-10 L3 抽象教訓）]] — 同樣的「下游同步沒做」風險
- [[user-collaboration-style#Rule 19 @keyword 觸發反問確認:使用者會打錯、不一定知道是 @專案 還是 @學習(2026-06-10 增補)]]
- [[user-collaboration-style#Rule 12 「先中斷 + 我有疑問」= 純討論模式,不是執行模式（2026-06-06 session 確立,2026-06-07 第二次踩）]]