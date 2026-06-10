# Hermès Cron Scheduler Script Timeout (2026-06-09)

## 問題
`hermes-config-backup-daily` cron job timeout，錯誤訊息：
```
Script timed out after 600s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes_v3.sh
```

jobs.json 中 `timeout_seconds` 已設為 600，但仍 timeout。

## 根因

Scheduler 的 `_run_job_script()` 對 no_agent script jobs 的 timeout 優先順序：
1. `HERMES_CRON_SCRIPT_TIMEOUT` env var（最高）
2. `cron.script_timeout_seconds` in config.yaml
3. `_SCRIPT_TIMEOUT` module constant（寫死 120s，預設值）

**jobs.json 的 `timeout_seconds` 控制的是 agent iteration 預算，不是 script execution timeout**。

backup_hermes_v3.sh 執行 rclone sync ~750MB，速度 1.0-1.3 MiB/s，需要 8-10 分鐘才能完成，遠超預設 120s。

## 2026-06-09 Session 新發現

jobs.json 的 `timeout_seconds` 在 v3 表現中**已被 Scheduler 讀取**（不再只是 120s 硬編碼），但 600s 上限仍不夠：

```
hermes-config-backup-daily [65f2dc3583d5]
  Last run: 2026-06-09T05:44:11  error: Script timed out after 600s
```

rclone sync ~750MB @ ~1 MiB/s 需要 8-10 分鐘，600s（10 分鐘）剛好卡在邊界，無任何 buffer。

**劑量**：`timeout_seconds: 600` 在 Scheduler 層級就是「最多等 600 秒」，不是「目標值」。

## 修復（三層都要設定）

```bash
# 1. .env（最高優先，重啟 gateway 後生效）
echo "HERMES_CRON_SCRIPT_TIMEOUT=1800" >> ~/.hermes/.env

# 2. config.yaml
cron:
  script_timeout_seconds: 1800

# 3. jobs.json 中的 timeout_seconds 也提高（防止 jobs.json 層級蓋過）
hermes cron edit 65f2dc3583d5 --timeout 1800

# 4. 重啟 gateway（讓它重新讀 .env）
pkill -f "hermes_cli.main gateway" || true
# gateway 會自動 respawn

# 5. 手動驗證
hermes cron run 65f2dc3583d5
# 等 15 分鐘後
hermes cron list 2>&1 | grep -A5 "hermes-config-backup-daily"
# last_status 應為 ok
```

## 備份效能數據

- 備份大小：~750 MB（8672 個檔案）
- 速度：1.0-1.3 MiB/s（Google Drive crypt）
- 預估時間：8-10 分鐘
- 實際耗時：2026-06-09 05:34 開始，05:44 完成（約 10 分鐘）

## If→Then

**If** `Script timed out after 600s` 且 script 是 backup_hermes_v3.sh **Then** 提高到 1800s（30 分鐘）並重啟 gateway

**If** 提高到 1800s 後仍 timeout **Then** 問題不是 timeout 設定，是 rclone sync 本身太慢（考慮減少傳輸量：排除 logs/、sessions/ 等非必要目錄）