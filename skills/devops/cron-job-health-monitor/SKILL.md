---
name: cron-job-health-monitor
description: "赫米斯 24/7 cron jobs 健康監控與失敗自動修復指引。當任何 cron job 顯示 error 狀態、或需要定期掃描 hermes cron list 時喚醒此技能。"
version: 1.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [cron, monitoring, self-healing, operational, autonomous, 24-7]
    triggers: [cron list, last_error, GH013, 401 unauthorized, script exited, jobs.json]
---

# Cron Job 健康監控與自我修復

赫米斯的 cron jobs 是 24/7 自主運作的骨幹（每天自動同步評價、技能統計、scheduler、MEMORY 同步到 Vercel 等）。當任何 cron job 失敗且沒人主動介入，整個 autonomous 迴路就會靜默壞掉。

此技能提供：**自動偵測 → 失敗分類 → 對應 If→Then 修復指引**。

## 何時使用

- 任何 `hermes cron list` 顯示 `status: error` 的 job
- 定期（建議每日）主動掃描 cron health
- `metacognitive-learner` Phase 1.5（每次啟動必跑）
- 用戶問「為什麼 hermes-portal 的評價沒同步進來？」「為什麼 hermes-status-site 沒更新？」

## 標準掃描指令

```bash
# 一次性列出所有 error 狀態的 job
hermes cron list 2>&1 | grep -B 1 -A 12 "status.*error"

# 或 JSON 解析（適合 script 化）
python3 ~/.hermes/skills/cron-job-health-monitor/scripts/check_cron_health.py
```

支援檔案 `scripts/check_cron_health.py` 會輸出結構化報告（job name / 錯誤類型 / 建議修復 / 嚴重度）。

## 失敗分類決策樹

抓到一個失敗 job 後，依 `last_error` 模式分類：

### 類型 A：認證/授權失敗（HTTP 401 / Unauthorized / Token expired）

**症狀**：
```
last_error: ...HTTP Error 401: Unauthorized...
```

**觸發情境**：
- `eval-sync` 從 `.env.local` 讀錯的 `AGENT_API_KEY`（見 portal-401-troubleshoot Step 5.5）
- Vercel build cache 對 `process.env` 處理異常
- 對方 API key 真的過期了

**修復入口**：
1. 先 `curl <endpoint> -H "X-Agent-Key: <test_key>"` 確認 endpoint 活著（401 = auth 問題、503 = endpoint 死）
2. 若是 `.env.local` 多行問題 → `portal-401-troubleshoot` Step 5.5
3. 若是 Vercel build cache → `portal-401-troubleshoot` Step 6（`vercel --prod --yes` 強制 rebuild）
4. 若是 key 真的過期 → 找對應 service 重發新 key

### 類型 B：GitHub Push Protection（GH013 / Repository rule violations）

**症狀**：
```
last_error: ...GH013: Repository rule violations...
       - commit: a4c14...
         path: assets/md-files.json:40
```

**這代表 secrets 正在被推到公開 GitHub**——最高優先級。

**修復入口**：見 `alt-token-secrets-layout/references/cron-secret-leak-scrub.md` 完整 SOP。

**核心動作**：
1. 立即暫停相關 cron (`hermes cron edit <id> --enabled false`)
2. Scrub 公開 repo 內 secrets
3. 用 `bfg-repo-cleaner` 或 `git filter-branch` 清歷史
4. 撤銷被洩漏的 token（Vercel Dashboard / GitHub Settings）
5. 修補 sync 腳本加 pre-commit secret scan
6. 把 secrets 從 MEMORY.md 清掉
7. 重啟 cron 驗證

### 類型 C：hermes cron edit --script Bug

**症狀**：
```
last_error: Script not found: /home/hoonsoropenclaw/.hermes/scripts/#!/bin/bash\n...
```

**觸發條件**：`hermes cron edit <id> --script '...'` 對 `no_agent=True` 的 script-only jobs。

**修復入口**：見 `metacognitive-learner` 技能「hermes cron edit --script 對 no_agent jobs 的 Bug」段落。

**核心動作**：直接編輯 `~/.hermes/cron/jobs.json`，把該 job 的 `prompt` 設為 `null`、`script` 改為純檔名。

### 類型 D：Script 找不到 / Path 錯誤

**症狀**：
```
last_error: Script not found: /home/hoonsoropenclaw/.hermes/scripts/<wrong_path>
```

**修復**：
1. 確認實際檔案位置（`ls ~/.hermes/scripts/<name>.py`）
2. 編輯 jobs.json 修正 `script` 欄位為「相對於 `~/.hermes/scripts/` 的檔名」或絕對路徑
3. 確認 `no_agent: true`

### 類型 E：Timeout / Connection refused（暫時性）

**症狀**：
```
last_error: ConnectionRefusedError: [Errno 111]...
或 urllib.error.URLError: <urlopen error timed out>
```

**處理**：
- 標記為 transient
- 24 小時後重試
- 若連續 3 天同類錯誤 → 升級為「服務真的掛了」，轉 `portal-401-troubleshoot` 或建立新 SOP

### 類型 G：相對路徑導致 `cd` / 檔案引用失敗

**症狀**：
```
cd: hermes-status-site: No such file or directory
ERROR: /home/hoonsoropenclaw/hermes-status-site/tabs/scheduler.html not found
```

**觸發情境**：cron job script 使用 `cd <dir>` 或 `python3 .hermes/scripts/xxx.py`（相對路徑），但 cron 執行時 cwd 不是 `/home/hoonsoropenclaw`

**修復**：
1. 確認 script 中所有路徑都是**絕對路徑**
2. 若有 `cd <dir>` → 改為 `cd /home/hoonsoropenclaw/<dir>` 或 `cd "$(dirname "${BASH_SOURCE[0]}")"`（取得 script 自身目錄）再拼相對路徑
3. 若有 `python3 .hermes/...` → 改為 `python3 /home/hoonsoropenclaw/.hermes/...`
4. 驗證：手動從 `/` 執行該 script（模擬 cron 的無 cwd 環境）

**預防**：cron job 的 workdir 不是 `/home/hoonsoropenclaw`，任何相對路徑都會 fail。新建 script 時一律用絕對路徑。

### 類型 H：rclone mkdir 多路徑語法錯誤（backup_hermes_v3.sh 專屬）

**症狀**：
```
Command mkdir needs 1 arguments maximum: you provided 3 non flag arguments: ["crypt_hermes:hermes-backup/v3/current" "crypt_hermes:hermes-backup/v3/manifests" "crypt_hermes:hermes-backup/v3/snapshots"]
```

**觸發情境**：`rclone mkdir` 每次只能接受 **1 個路徑**，不能像 `mkdir -p` 那樣多個路徑一次建立

**受影響的 Jobs**：`hermes-config-backup-daily`（`~/.hermes/scripts/backup_hermes_v3.sh` line 75）

**修復**：
```bash
# 錯誤（❌）：
rclone mkdir "$DRIVE_CURRENT" "$DRIVE_MANIFESTS" "$DRIVE_SNAPSHOTS" --config "$RCLONE_CONF"

# 正確（✅）：
rclone mkdir "$DRIVE_CURRENT" --config "$RCLONE_CONF" || true
rclone mkdir "$DRIVE_MANIFESTS" --config "$RCLONE_CONF" || true
rclone mkdir "$DRIVE_SNAPSHOTS" --config "$RCLONE_CONF" || true
```

**驗證**: `bash -n backup_hermes_v3.sh` → SYNTAX OK

**預防**: 任何 `rclone mkdir` 都要單一路徑，不可多參

### 類型 I：Hardcoded 錯誤路徑（.env.local / hermes-portal 等）

**症狀**：
```
ERROR: AGENT_API_KEY not found in hermes-portal/.env.local
```

**觸發情境**：script 寫死某個路徑，但該路徑已迁移/改名/從未存在

**修復**：
1. 先用 `grep -r "hermes-portal" ~/.hermes/scripts/` 找出所有相關 script
2. 查詢已知存在的 script（如 `portal_upload_check.sh`）找到正確路徑
3. 改用動態偵測（`Path.home() / ".hermes"`）或多路徑備援
4. 驗證：手動執行該 script

**赫米斯已知正確路徑**：
- Portal .env.local：`/home/hoonsoropenclaw/permanent-projects/hermes-portal/.env.local`（非 `/home/hoonsoropenclaw/hermes-portal/`）
- Hermes .env：`/home/hoonsoropenclaw/.hermes/.env`
- 兩者均可含 `AGENT_API_KEY`，優先讀 portal .env.local，失敗則 fall back 到 hermes .env

**預防**：任何 `.env.local` 路徑都應列為「可能需要備援」的敏感路徑，不要寫死單一路徑

### 類型 K：Python grep pattern 把 redaction marker `***` 當成有效 key（eval-sync 專屬）

**症狀**：
```
last_error: ERROR: AGENT_API_KEY not found in hermes-portal .env.local
# 但 .env.local 檔案存在且有 AGENT_API_KEY 行
```

**觸發情境（兩個獨立 bug）**：

**Bug 1：Python grep pattern 把 mask 當 key（2026-06-08 修復）**
```python
# 錯誤（❌）— `***` 是三個星號字元，不是萬用字元：
if line.startswith("AGENT_API_KEY=*** or line.startswith("export AGENT_API_KEY=***    key = line.split("=", 1)[1].strip()
    if key:  # "***" 是 truthy → 返回 "***" 而非 None
        return key  # → 返回 "***"，腳本試圖用 "***" 認證 → 401

# 正確（✅）：
if line.startswith("AGENT_API_KEY="):
    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if key and key != "***":  # Skip redaction markers
        return key
```

Python 把 `***` 視為三個字元字串，非空值通過 `if key:` → 返回 `***` 而非 None → 腳本拿到 `"***"` 當 Bearer token → 401 Unauthorized。

**Bug 2：Vercel env pull 把 AGENT_API_KEY mask 成 `***`**
- `vercel env pull .env.local` 會把所有 environment variables 的**實際值**以 `***` 遮蔽
- 遮蔽後的 `.env.local` 看起來有 `AGENT_API_KEY=***`，但 `***` 是 placeholder 不是真實 key
- 腳本讀到 `***` 後試圖拿它當 Bearer token 認證 → 401 Unauthorized
- **這個遮蔽是不可逆的** — `vercel env pull` 不會保留真實值，之後從 `.env.local` 永遠讀不到真正的 key

**受影響的 Jobs**：`eval-sync`（`~/.hermes/scripts/sync_evaluations.py`）

**修復**：
1. **Python grep pattern 修復**：加 `key != "***"` 明確跳過 redaction marker
2. **AGENT_API_KEY 再生**：到 Vercel Dashboard → Settings → Environment Variables → 找到 `AGENT_API_KEY` → 刪除 → 重新 `Add` 一個新的 random value（或用 `openssl rand -hex 32` 生成）
3. **手動更新 .env.local**：**不要用 `vercel env pull`**（會再次 mask），直接在 `.env.local` 中寫入新 key
4. 若無法取得真實 key → 整個專案需要重新設定 API key（因为旧 key 已经丢失）

**驗證**：
```bash
python3 ~/.hermes/scripts/sync_evaluations.py
# 預期：exit 0 + "取得 N 筆評價"（不是 "ERROR: AGENT_API_KEY not found"）
# 且 key 长度 > 20（真 key 约 40+ chars，masked 是 3 chars "***"）
```

**預防**：
- **永遠不要對 `AGENT_API_KEY` 使用 `vercel env pull`** — 它會把值 mask 成 `***`，之後無法恢復
- 若需要同步 AGENT_API_KEY → 在 Vercel Dashboard 手動設定，或用 `vercel env add AGENT_API_KEY <value>` 而非 pull
- 腳本驗證時增加長度檢查：`if len(key) < 10: log("WARN: AGENT_API_KEY appears to be masked")`
- **任何 `startswith("***")` 在 Python 中是字面比對，不是 glob/wildcard** — 要明確用 `!= "***"` 比對

### 類型 L：cron 部署腳本 git push rejection（無自我修復機制）

**症狀**：
```
error: failed to push some refs to 'github.com:hoonsoropenclaw/raphael-status-site.git'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

**觸發情境**：
- cron 部署腳本執行期間，其他 worker/cache 更新了 `origin/main`
- local main 落後於 `origin/main` → non-fast-forward rejection
- 下次 cron 執行時落後更多，形成惡性循環

**修復**：在部署腳本中 implement `deploy_with_git_recovery()` 函數（fetch + hash compare + rebase + retry，最多 2 次）。詳見 `metacognitive-learner/references/git-push-recovery.md`。

**受影響的 Jobs**：`skill-usage-daily-v3`（`~/.hermes/scripts/run_skill_stats.sh`）

**驗證**：
```bash
bash ~/.hermes/scripts/run_skill_stats.sh
git rev-parse HEAD && git rev-parse origin/main
# 兩個 SHA 相同 = 同步成功
```

**預防**：任何使用 `git push` 的 cron 部署腳本都應有 git recovery 機制。

---

### 類型 L2：rebase-based git recovery 的設計缺陷（2026-06-08 發現）

**症狀**：
```
last_error: ...rejected...fetch first...
# 且 recovery 後仍失敗，或 `set -euo pipefail` 環境下 script non-zero exit
```

**根因**：`deploy_with_git_recovery()` 使用 `git rebase origin/main` 作為 recovery 手段，在 rebase conflict 時會：
1. 執行 `git reset --hard origin/main`（砍 local commits）
2. Regenerate stats（`python3 skill_usage_stats.py`）
3. Commit + push

若 `set -euo pipefail` 環境下 `return 1`（retry exhausted）或 `git rebase` conflict，會導致 script exit 而非 graceful fallback。

**修復方向**（2026-06-08 更新）：
- **不要用 `git rebase` + `git push --force` 的兩階段 recovery**
- 改用 `git push --force origin main:main` 一步到位（直接用 remote 覆蓋 local，無 conflict 風險）

**If→Then**: **If** cron script 的 git push 被遠端拒絕 **Then** 使用 `git push --force origin main:main` 一步到位，不要用 `git rebase` + `git push --force` 的兩階段 recovery
**If** cron script 使用 `set -euo pipefail` 且函數用 `return N` 表達失敗 **Then** 確保呼叫方不使用 `set -e`，或函數用 `exit N` 而非 `return N`

**驗證**：
```bash
git -C /home/hoonsoropenclaw/hermes-status-site status --short
# 乾淨 = push 成功
git -C /home/hoonsoropenclaw/hermes-status-site log --oneline -3
# 有最近 commit = stats 有更新
```

### 類型 N：Scheduler Hardcoded 120s Timeout（backup_hermes_v3.sh 等長時腳本）

**症狀**：
```
last_error: Script timed out after 120s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes_v3.sh
# jobs.json 中 timeout_seconds 已是 600
```

**根因**：Scheduler 的 `_run_job_script()` 對 no_agent script jobs 有優先順序：
1. `HERMES_CRON_SCRIPT_TIMEOUT` env var（最高優先）
2. `cron.script_timeout_seconds` in config.yaml
3. `_SCRIPT_TIMEOUT` module 常數（寫死 120s）

jobs.json 的 `timeout_seconds` 控制的是 **agent iteration 預算**，不是 script execution timeout。

**受影響 Jobs**：`hermes-config-backup-daily`（rclone sync ~750MB 需要 8-10 分鐘）

**修復**（三層都要設定）：
```bash
# 1. config.yaml（中等優先，gateway 重啟後生效）
cron:
  script_timeout_seconds: 600

# 2. .env（最高優先，gateway 重啟後生效）
HERMES_CRON_SCRIPT_TIMEOUT=600

# 3. 直接重啟 gateway（讓它重新讀 .env）
kill $(pgrep -f "hermes_cli.main gateway")
# 或 pkill -f "hermes_cli.main gateway"
# gateway 會自動 respawn
```

**驗證**：
```bash
# 檢查是否生效
hermes cron run 65f2dc3583d5  # 手動觸發
# 等 10 分鐘後
hermes cron list 2>&1 | grep -A3 "hermes-config-backup-daily"
# last_status 應為 ok（不是 error）
```

**預防**：任何 script 預期跑超過 2 分鐘的 cron job，都要設定 `HERMES_CRON_SCRIPT_TIMEOUT`。

### 類型 N2：Script 檔案從未部署（jobs.json 指向不存在的檔案）

**症狀**：
```
last_error: Script timed out after 600s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes_v3.sh
# jobs.json 中 script 欄位正確指向 backup_hermes_v3.sh
# 但 ls ~/.hermes/scripts/backup_hermes_v3.sh → No such file
```

**根因**：trial-and-error 條目記錄了「jobs.json 改 script 欄位」，但**從未驗證 script 檔案是否真的存在於 `~/.hermes/scripts/`**。

V3-BACKUP-STATUS.md 記載：v3 實驗因 Google Drive API throttle 未完成、從未接 cron。但 jobs.json 已搶先改為指向 v3，造成「jobs.json 指向不存在的檔案」。

**這不是 timeout 問題，是 Phase 1.5 交叉驗證失效的典型案例**：「文件說了要改，但根本沒改」。

**受影響 Jobs**：`hermes-config-backup-daily`

**修復**（二選一）：
1. **快速方案**：將 jobs.json 改回 `script: backup_hermes.sh`（v2，確認存在）
2. **完整方案**：從 staging 取回 v3 腳本、部署到正確位置

**驗證命令**（每次 Phase 1.5 必跑）：
```bash
ls -la ~/.hermes/scripts/backup_hermes_v3.sh   # 確認存在
ls -la ~/.hermes/scripts/backup_hermes.sh       # fallback 確認
python3 -c "import json; d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json')); print([j['script'] for j in d['jobs'] if j['id']=='65f2dc3583d5'])"  # 確認 jobs.json 值
```

**If→Then**：
**If** cron job error 且 trial-and-error 已有修復記錄 **Then** 必須同步驗證：script 檔案 `mtime` 在 trial-and-error 記錄的「修復日期」之後。**文件改了 ≠ 檔案部署了。**

**預防**：任何「jobs.json 指向某 script」的修復完成後，必須立即執行 `ls -la ~/.hermes/scripts/<script_name>` 確認檔案存在。

---

### 類型 F：其他 Script exited with code 1

**症狀**：
```
last_error: Script exited with code 1
(stdout/stderr 含實際錯誤訊息)
```

**處理**：
1. 讀完整 stdout + stderr（`hermes cron list` 會附上）
2. 找對應的 skill 或腳本文件
3. 若無對應 → 手動執行該 script 看完整 stacktrace

## 自動修復觸發（可選，Layer 2.5）

如果有 `automated-sop-validation` 的合約設定，這些修復可以做成「自動 + 通知人」模式：

```yaml
# contracts/cron-failure-recovery.contract.yaml
triggers:
  - event: "cron.error.detected"
    condition: "last_error contains 'GH013'"
    action: "alert + halt_cron"
    notify: "main_session"
    severity: "critical"
```

目前赫米斯尚未啟用此自動修復，預設是**手動介入 + 留下紀錄**。

## 預防設計（給未來新建的 cron jobs）

新建任何 cron job 時**必須檢查**：

- [ ] `no_agent: true`（若是純 script job）→ 確認 `script` 為純檔名、`prompt` 為 `null`
- [ ] 任何 `*.env*` 讀取用 `awk -F= '/^KEY=/{print $2; exit}'` 或 Python `re.search`（**不要用 `grep | cut`**）
- [ ] 任何「推到公開 GitHub repo」的 sync 腳本有 pre-commit secret scan
- [ ] 任何「呼叫外部 API」的腳本有 retry + timeout
- [ ] `hermes cron list` 顯示 `next_run` 排程正確
- [ ] 第一次手動觸發驗證成功後才放手

## 重啟 hermes-gateway 的正確姿勢（2026-06-11 觀察歸納）

**症狀**：`sudo systemctl restart hermes-gateway.service` 之後**卡 3 分鐘才完成重啟**、中間 `systemctl status` 顯示 `deactivating (stop-sigterm)`、讓人以為指令沒生效又重發。

**根因**：
- `/etc/systemd/system/hermes-gateway.service` 設 `Type=simple`、**沒設 `TimeoutStopSec`**
- systemd 預設 90s graceful timeout → 過了才送 SIGKILL 強制殺
- 為什麼 graceful shutdown 慢：gateway 跑 async telegram long polling、收到 SIGTERM 後要等 in-flight agent request 跑完（metacognitive 87s）+ telegram API 釋放連線
- **本機的 `TimeoutStopSec=210`** 是 2026-06-11 之後才加的（之前用預設 90s + systemd 自動 grace period）

**正確 SOP**：
1. **發 restart 後不要慌**、`systemctl status` 會顯示 `deactivating (stop-sigterm)` 是正常的
2. **等 3 分鐘**（不要用 `timeout 30`、不要連發 restart 指令）
3. **看新 PID 出現**才確認成功：
   ```bash
   pgrep -af "hermes_cli.main gateway" | grep -v "bash -c"
   # 新 PID 出現 = 重啟完成
   ```
4. **第二次重啟建議先驗證**（避免連發造成 zombie process）：
   ```bash
   sudo systemctl show hermes-gateway.service -p ActiveEnterTimestamp
   # 看上次進入 active 的時間、決定是否真的需要再重啟
   ```

**預防**：
- 在 `/etc/systemd/system/hermes-gateway.service` 加 `TimeoutStopSec=10s`（10 秒 grace 期間讓 telegram long polling 自己退、然後 SIGKILL）
- 但要先驗證 hermes 收到 SIGTERM 後能正常處理（沒 in-flight agent 還在算東西）
- 或加 `KillSignal=SIGINT`（部分 hermes 版本會更主動收訊號）

**If→Then 規則**：
- **If** `systemctl restart hermes-gateway` 30 秒後 status 仍 `deactivating` **Then** **不要**重發指令、繼續等 2-3 分鐘（這是正常 graceful stop）
- **If** 收到 `Background process completed` 通知但 service 沒新 PID **Then** 重跑 `systemctl status` 看 `Restart=` counter、有異常時手動重啟
- **If** 改完 hermes-agent 源碼要重啟生效 **Then** 預期要等 3 分鐘（不是 30 秒）

### 類型 P：Cron 失敗時 telegram 訊息爆炸（scheduler.py 缺乏 500 字截斷）（2026-06-11 修訂）

**症狀**：
- 任何 cron script 失敗時 cron 失敗訊息是幾十 KB 到幾百 KB（git push 輸出、rsync 進度、traceback 等等）
- telegram 收到 50+ 則訊息（每次 4096 char 切一段）
- 使用者**誤以為每天 cron 都在爆炸**、但其實只有當天失敗才有

**觸發情境（2026-06-11 實例）**：
- 02:00 `v4-backup-tier1-daily` 失敗
- scheduler.py line 2105 把 191,490 bytes stderr 整份塞進 `deliver_content`
- telegram 自動切 47 段
- 使用者收到「50 則左右」的備份訊息 → 誤判為「每天都這樣」

**根因**（`hermes-agent/cron/scheduler.py` line 2105）：
```python
deliver_content = final_response if success else f"⚠️ Cron job '{job.get('name', job['id'])}' failed:\n{error}"
```
- `error` 是 script 失敗時的 `subprocess.Popen` 完整 stderr + stdout
- 沒上限、沒截斷
- Telegram 切段是事後補救、本來不該靠它

**正確做法**（已落地於 2026-06-11）：
1. `scheduler.py` line 2105-2115：失敗時若 `len(error) > 500` 字自動截斷成「`⚠️ job failed (truncated, full N chars saved to log):\n<前 500 字>\n... [truncated, see ~/.hermes/cron/output/]`」
2. 完整 stderr 仍寫進 `~/.hermes/cron/output/<id>/<timestamp>.md`（已存在）
3. Telegram 切段從 47 段 → 1 段

**驗證**：
```bash
# 改完需重啟 hermes-gateway 才會生效
# （Python 程式碼改動要重啟 process、修改只動到記憶體不夠）
sudo systemctl restart hermes-gateway.service
```

**If→Then 規則**：
- **If** 看到 cron 失敗「N 段訊息」爆炸 **Then** 立刻看 `hermes-agent/cron/scheduler.py` 的 `deliver_content = ` 那行、必有沒截斷的 `error` 變數
- **If** 設計任何「失敗時送 telegram 訊息」的功能 **Then** 必加 ≤ 500 字截斷 + 完整版寫 log（不要靠 telegram 4096 char 自動切段補救）
- **If** 任何 hermes-agent 程式碼（scheduler.py / jobs.py / run_agent.py）被改動 **Then** 提醒使用者「需要重啟 hermes-gateway 才會生效」、不要默默假設已生效

**預防**（避免未來再犯）：
- scheduler.py 任何把 `error` 變數塞進 `deliver_content` 的位置都要先截斷
- 新增 cron runner 平台（discord / slack）時也吃這條：≤ 500 字 + 完整版寫 log

## 驗證修復成功

任何失敗修復後，**必須主動驗證**：

```bash
# 看下次排程時間
hermes cron list 2>&1 | grep -A 8 "name: <job_name>"

# 手動觸發（如果支援）
hermes cron run <job_id>

# 或等 next_run 後觀察 last_status
```

⚠️ **自我報告不等於驗證**：寫「✅ 已修復」不可只靠 SOP validator（它只檢查輸出格式）。必須：
1. 重新觸發失敗場景（`python3 sync_evaluations.py`）確認 exit code 0
2. 外部系統狀態檢查（如 Vercel deploy URL 存在、GitHub push 成功）
3. 附上真實命令輸出（不是 ✅ emoji，是 stdout/stderr）

**If** 上次 cycle 說「已修復」但本次 cron 仍 error **Then** 不要相信上次 cycle，從頭重新跑完整 SOP

## If→Then 規則彙總

| If | Then |
|------|------|
| 任何 cron job `last_status: error` | 立即用本技能分類、找對應修復入口 |
| 錯誤含 `401` / `Unauthorized` | `portal-401-troubleshoot` |
| 錯誤含 `GH013` | 立刻暫停 cron + `alt-token-secrets-layout/references/cron-secret-leak-scrub.md` |
| 錯誤含 `#!/bin/bash` | `metacognitive-learner` cron script bug 段落 |
| 錯誤含 `Script not found` | 直接編輯 jobs.json 修 path |
| 錯誤含 `AGENT_API_KEY not found` + key 實際存在但很短（3 chars `***`） | 類型 K Bug 2：Vercel env pull mask → 再生 key，手動寫入 .env.local |
| 錯誤含 `AGENT_API_KEY not found` + SyntaxError at line 32 | 類型 K Bug 1：Python startswith() 缺少 `)` |
| 錯誤含 `git push` rejection + 非 fast-forward | 類型 L：cron 部署腳本無 git recovery | 見 `references/git-push-recovery.md` |
| 錯誤含 `git push` rejection + `set -euo pipefail` + non-zero exit | 類型 L2：rebase-based recovery 設計缺陷 | 改用 `git push --force origin main:main` 一步到位 |
| 錯誤含 `Script timed out after 120s` + backup_hermes.sh | v2 backup 產 694 MB tar.gz + rclone crypt 上傳太慢 | jobs.json 中 backup script 改為 `backup_hermes_v3.sh`；見 `references/hermes-backup-timeout.md` |
| 錯誤含 `Script timed out after 120s` + lock file 存在 | 類型 M：stale lock file → `rm -f ~/.hermes/backups/.backup.lock` |
| jobs.json 指向某 script 但 cron 仍 error + `ls ~/.hermes/scripts/<name>` → No such file | 類型 N2：script 檔案從未部署（jobs.json 指向不存在的檔案）。見上方類型 N2。`ls -la ~/.hermes/scripts/<name>` + `ls -la ~/.hermes/scripts/<fallback>` 確認 |
| jobs.json 指向某 script 但 cron 仍 error + `ls ~/.hermes/scripts/<name>` → No such file | 類型 N2：script 檔案從未部署（jobs.json 指向不存在的檔案）。見上方類型 N2。`ls -la ~/.hermes/scripts/<name>` + `ls -la ~/.hermes/scripts/<fallback>` 確認 |
| 錯誤含 `Script timed out after 120s` + jobs.json timeout_seconds 已設够大 | 類型 N（舊版表現）：Scheduler `_DEFAULT_SCRIPT_TIMEOUT=120s` 寫死在 scheduler.py，jobs.json `timeout_seconds` 控制 agent iteration 預算、不控制 script timeout → 在 `config.yaml cron.script_timeout_seconds` 設更大值 + `.env HERMES_CRON_SCRIPT_TIMEOUT` + 重啟 gateway |
| 錯誤含 `Script exited with code 2` + 手動執行 exit 0 | 類型 O：nullglob + set -e bug | `references/nullglob-set-e-bug.md` + 修補後驗證 |
| 任何 cron 失敗時 telegram 收到 N 段訊息（每段 4096 char）| 類型 P：scheduler.py `deliver_content` 沒截斷 `error` 變數 | 修 `hermes-agent/cron/scheduler.py` line 2105：失敗時 `error` 截斷到 500 字、完整版寫 `~/.hermes/cron/output/<id>/` |
| `sudo systemctl restart hermes-gateway` 30 秒後仍 `deactivating` | 不是失敗、是 graceful stop 正常（systemd 預設 90s + hermes 預設 210s）| 等 3 分鐘看新 PID、**不要**重發指令 |
| git push 被拒 `denied to hoonsor` 但 `gh auth status` 顯示 `hoonsoropenclaw` | 類型 J2：舊 hoonsor token 在 `~/.git-credentials-raphael` 把新的 `hoonsoropenclaw` token 蓋過 | 執行一次 `git push` 觸發 `gh auth git-credential store` 更新 store file；若仍無效則手動編輯 store file 把 `hoonsor` URL 置換成 `hoonsoropenclaw` |
| git push 403 + SSH remote + 手動 push 成功 + credential helper 設定存在 | 類型 J2-SSH：SSH push 被 credential helper 劫持、回傳錯誤帳號 token | 移除 `credential.https://github.com.helper`；見 `references/ssh-push-credential-helper-403.md` |
| git push 403 + 手動 push 成功 + 憑證檔正確 | 類型 J3：間歇性 GitHub rate limit（非 credential bug） | stale state，等待下一個 scheduler tick，不要進緊急修復。見 `references/stale-state-2026-06-11-fixes.md` |
| "Script not found" 含 `--tier2 --upload-tier2` args | 早期 `hermes cron edit --script` bug 殘留（jobs.json prompt 欄位含 args）| 檢查 jobs.json `prompt` 是否為 null；是則 stale state，下個 tick 清除 |
| hermes-backup-coverage-check exit 1 但手動跑 exit 0 | 真實 warnings 已修復，之前是 warnings-only exit 0 政策未生效 | stale state，驗證：手動跑 `bash ~/.hermes/scripts/hermes-backup-coverage-check.sh` 確認 exit 0 |
| 連續 3 天同類錯誤 | 升級為已知問題，建立新 skill 或 patch 既有 skill |

### 類型 M：Stale Lock File 導致 Timeout（backup_hermes.sh 專屬）

**症狀**：
```
last_error: Script timed out after 120s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes.sh
last_status: error
# 但 script 本身正常，手動執行 exit 0
```

**觸發情境**：
- `backup_hermes.sh` 使用互斥鎖防止同時間跑兩次（`LOCKFILE="$HERMES_HOME/backups/.backup.lock"`）
- 若前一次執行被強制中斷（Ctrl+C、OOM kill、120s timeout 觸發的 SIGKILL），`set -euo pipefail` 會讓 script 在收到信號時來不及刪除 lock
- Lock 檔案留下來 → 下次執行時 `if [ -f "$LOCKFILE" ]; then exit 0` → script 直接退出（沒有任何輸出）
- 但 hermes cron scheduler 會等 120s timeout 才放行 → 看起來像「卡住了 120 秒」

**修復**：
```bash
rm -f /home/hoonsoropenclaw/.hermes/backups/.backup.lock
```

**驗證**：
```bash
ls -la /home/hoonsoropenclaw/.hermes/backups/.backup.lock
# 檔案不存在 = 修復成功
```

**預防**：
- lock 檔案應有 TTL（如 lock age > 1 小時視為過期，自動刪除）
- 或在 script 開頭加 `if [ -f "$LOCKFILE" ]; then age=$(stat -c '%Y' "$LOCKFILE" 2>/dev/null || echo 0); now=$(date +%s); if [ $((now - age)) -lt 3600 ]; then exit 0; fi; rm -f "$LOCKFILE"; fi`

**受影響的 Jobs**：`hermes-config-backup-daily`（`~/.hermes/scripts/backup_hermes.sh`）

---

### 類型 O：nullglob + set -e Bug（glob 匹配 0 檔導致 script 中斷）

**症狀**：
```
last_status: error
last_error: Script exited with code 2
# 但手動執行: bash script.sh → EXIT 0（成功）
```

**觸發情境**：
- `set -euo pipefail` + glob pattern + `ls -t *.md` + `head -1` 組合
- 當 glob 匹配 0 個檔案時，`ls *.md` 擴展成無參數的 `ls` → exit 1
- `head -1` 收到 empty stdin → exit 1
- Pipeline exit code = 1 → `set -e` + `pipefail` 導致 script 中斷
- 非週日執行 `v4-daily-summary` 時，`v4-restore-verify-weekly` 的 log 為空 → 觸發

**受影響的 Jobs**：`v4-daily-summary`（`hermes-backup-daily-summary.sh`）

**修復**：
```bash
# 在 glob 前加 nullglob，事後還原
shopt -s nullglob
today_log="$CRON_OUTPUT/$job_id/${TODAY}_"*".md"
latest=$(ls -t $today_log 2>/dev/null | head -1 || true)
shopt -u nullglob
```

**驗證**：
```bash
bash ~/.hermes/scripts/hermes-backup-daily-summary.sh
# 修復後：EXIT 0
```

**預防**：任何 cron script 有 `set -euo pipefail` + glob，都必須加 `shopt -s nullglob`

**支援檔案**：`references/nullglob-set-e-bug.md`

---

### 類型 J：Stale last_error 排除 SOP（2026-06-11 修訂）

**症狀**：
```
last_status: error
last_error:  Script exited with code 1
# 但 jobs.json 的 script 欄位修對了、script 手動跑也 exit 0
# 連續 3 個 cycle 都看到同樣 error、但根本沒有新 bug
```

**根因（比 2026-06-09 觀察的更細）**：
- `last_status` / `last_error` / `last_run_at` **只在 `_process_job()` 跑完 scheduler tick 才會被 `mark_job_run()` 寫入**（scheduler.py line 2129）
- 手動 `bash <script>.sh` **不走 scheduler 流程**、**不會**更新 jobs.json
- jobs.json 被手動修對 ≠ last_status 翻成 ok
- 「修對」跟「last_status 顯示 ok」**中間有 6~24 小時的時間差**（看 cron 排程）
- 這是 metacognitive-learner Phase 1.5 最常誤判的陷阱——以為「還沒修好」、反覆進緊急修復循環

**完整排除流程（4 步）**：
1. **手動跑 script**（從 `/` 或空 cwd 模擬 cron 環境）：
   ```bash
   cd / && python3 /home/hoonsoropenclaw/.hermes/scripts/<script_name>.py
   # 或
   cd / && bash /home/hoonsoropenclaw/.hermes/scripts/<script_name>.sh
   ```
2. **交叉驗證 jobs.json**（jobs.json 跟 trial-and-error 建議值一致）：
   ```bash
   python3 -c "
   import json
   d = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
   for j in d['jobs']:
       if j.get('name') == '<job_name>':
           print('script:', j.get('script'))
           print('prompt:', j.get('prompt'))
           print('timeout_seconds:', j.get('timeout_seconds'))
           print('no_agent:', j.get('no_agent'))
   "
   ```
3. **以上都過 → 這是 stale state**、不是新 bug。**不要**進 Phase 1-3 緊急修復模式
4. **用 `hermes cron run` + `hermes cron tick` 強迫翻 last_status**（不要等 cron 自然排程）：
   ```bash
   hermes cron run <job_name>      # schedule 到下一個 tick
   sleep 30                         # 等 scheduler tick
   # 驗證
   python3 -c "
   import json
   d = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
   for j in d['jobs']:
       if j.get('name') == '<job_name>':
           print('last_status:', j.get('last_status'))
           print('last_run_at:', j.get('last_run_at'))
           print('last_error:', j.get('last_error'))
   "
   # 看 cron output dir
   ls -lat /home/hoonsoropenclaw/.hermes/cron/output/<job_id>/
   ```

**驗證方式**：
- cron list 的 `last_error` 只代表「上次觸發時」的狀態，不代表當下
- **自我報告不等於驗證**：「上次 cycle 說已修復」不可信，必須重新執行一次
- `last_status: pending` 跟 `last_status: error` 不同：pending = 從未跑過（如 `v4recovery2026` 等週日 23:00）；error = 跑過但失敗、且未再跑翻

#### 類型 J2：Git 憑證過期導致 Stale Push Error（2026-06-11 新增）

**症狀**：
```
last_error: remote: Permission to hoonsoropenclaw/hermes-config-backup.git denied to hoonsor.
fatal: unable to access 'https://github.com/hoonsoropenclaw/hermes-config-backup.git/': The requested URL returned error: 403
```
但 `gh auth status` 顯示 `hoonsoropenclaw` 已登入。

**根因**：
- `~/.git-credentials-raphael` 內含舊 `hoonsor` 帳號 token（`ghp_akP3...`）
- 當前 gh 登入 `hoonsoropenclaw`（`ghp_SFvS...`）
- `gh auth git-credential` 的 `store` helper 仍使用 store file 的舊 token（gh 的 `get` 會先查 store file）
- Scheduler 的 git push 走 credential.helper → 拿到舊 hoonsor token → 403

**觸發情境**：
- `hermes-config-backup-daily` 或 `v4-backup-tier1-daily` 的 git push 突然失敗
- 使用者說「gh auth status 顯示正確」但 push 仍被拒

**修復**：
```bash
# 1. 強迫 gh auth git-credential 更新 store file
cd /home/hoonsoropenclaw/.hermes/hermes-backup-staging
git push origin main 2>&1
# 觸發 'gh auth git-credential store' 把正確 token 寫入 ~/.git-credentials-raphael

# 2. 驗證
cat ~/.git-credentials-raphael | grep -o 'ghp_[a-zA-Z0-9]*' | head -1
# 應該是 ghp_SFvS...（hoonsoropenclaw），不是 ghp_akP3...（hoonsor）

# 3. 確認 staging 的 credential.helper 只用 gh auth git-credential
cd /home/hoonsoropenclaw/.hermes/hermes-backup-staging
git config --unset credential.helper
git config credential.https://github.com.helper '!/usr/bin/gh auth git-credential'

# 4. 測試
git push origin main  # 應成功
```

**If→Then 規則**：
- **If** git push 被拒 `denied to hoonsor` 但 `gh auth status` 顯示 `hoonsoropenclaw` **Then** 檢查 `~/.git-credentials-raphael` 是否仍有舊 hoonsor token，執行一次 `git push` 觸發 `gh auth git-credential store` 更新
- **If** 憑證檔案已更新但仍有 `hoonsor` URL **Then** 手動編輯 `~/.git-credentials-raphael`，把 `https://hoonsor:ghp_xxx@github.com` 改成 `https://hoonsoropenclaw:ghp_yyy@github.com`

**預防**：
- 任一 gh 帳號 logout/login 都應更新 `~/.git-credentials-raphael`
- 備份 script 的 staging 應只用 `gh auth git-credential`（不用 store file），避免跨帳號污染

**觀察記錄（2026-06-11）**：
- `~/.git-credentials-raphael` 內容：`https://hoonsor:ghp_akP3...SXQO@github.com`
- `gh auth status`：`Logged in to github.com account hoonsoropenclaw`
- 手動 `git push` 觸發 `gh auth git-credential store` 後，憑證檔更新為 `https://hoonsoropenclaw:ghp_SF...g2ex@github.com`，push 成功

## 支援檔案

- `scripts/check_cron_health.py` — 自動掃描 + 分類 + 輸出結構化報告
- `references/hermes-backup-timeout.md` — 類型 N：backup timeout 修復與 Scheduler timeout 分離
- `references/camofox-watchdog-deployment.md` — camofox-watchdog.sh 從未進 crontab 的修復（skill dir 0700 問題 + 部署步驟）
- `references/stale-state-recovery.md` — 2026-06-11：`last_status` 跟 jobs.json 解耦的 4 步排除 SOP（含 `hermes cron run` 強迫翻轉指令）
- `references/git-credential-stale-housor-housoropenclaw.md` — 類型 J2：Git HTTPS push 在 cron 環境因 `~/.git-credentials-raphael` 含舊 `hoonsor` token 導致 403，修復（SSH remote 或 gh auth store 更新）+ 預防方案
- `references/failure-cases-2026-06.md` — 已知失敗案例 + 修復記錄（2026-06 eval-sync 401 key mask、skill-usage-daily-v3 git recovery、camofox watchdog 每 6 分鐘重啟、backup_hermes.sh v2 timeout → v3 修復）
- `references/ssh-push-credential-helper-403.md` — 類型 J2-SSH：SSH push 被 `credential.https://github.com.helper` 劫持導致 403（2026-06-12）
- `references/nullglob-set-e-bug.md` — 類型 O：glob 匹配 0 檔 + set -e + exit code 2 bug（2026-06-10）
- `references/dry-run-vs-real-run.md` — 2026-06-11：dry-run 成功不等於 real-run 成功，backup cron job 驗證必須包含 real-run（git push 實際成功檢查）
- `references/stale-state-2026-06-11-fixes.md` — 2026-06-11 新增：4 個 cron error 均為 stale state 的交叉驗證報告，含 Type J3（間歇性 GitHub rate limit 403 vs credential bug）、coverage check exit code 解析、v4-backup-tier2-daily "Script not found" 謎題根本原因（早期 `hermes cron edit --script` bug 殘留）+ 驗證命令清單

## 相關 SKILL

- `metacognitive-learner` — Phase 1.5 必跑此監控
- `portal-401-troubleshoot` — 類型 A 修復
- `alt-token-secrets-layout` — 類型 B 修復（GH013 secret leak）
- `hermes-self-improvement` — 失敗分類 → 經驗固化
