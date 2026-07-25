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