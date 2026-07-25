# Cron Script Timeout 修復（2026-06-09）

## 問題
`hermes-config-backup-daily` 執行 rclone sync ~750MB，預估 8-10 分鐘，但 Scheduler 預設 120s timeout。

jobs.json 的 `timeout_seconds: 600` 設了沒效。

## 根因：Timeout 優先順序

Scheduler 的 `_run_job_script()` 對 no_agent script jobs 的 timeout 優先順序：

| 優先順序 | 來源 | 預設值 |
|---------|------|--------|
| 1（最高） | `HERMES_CRON_SCRIPT_TIMEOUT` env var | — |
| 2 | `cron.script_timeout_seconds` in config.yaml | 120s |
| 3 | `_SCRIPT_TIMEOUT` module constant | 120s |

**jobs.json 的 `timeout_seconds` 控制的是 agent iteration 預算，不是 script execution timeout。**

## 修復（三層都要設定）

```bash
# 1. config.yaml（中等優先，gateway 重啟後生效）
# ~/.hermes/config.yaml
cron:
  script_timeout_seconds: 600

# 2. .env（最高優先，gateway 重啟後生效）
# ~/.hermes/.env
HERMES_CRON_SCRIPT_TIMEOUT=600

# 3. 重啟 gateway（讓它重新讀 .env）
pkill -f "hermes_cli.main gateway"
```

## 驗證

```bash
# 手動觸發
hermes cron run 65f2dc3583d5

# 等 10 分鐘後檢查
hermes cron list 2>&1 | grep -A5 "hermes-config-backup-daily"
# last_status 應為 ok（不是 error）

# 或檢查 log
ls -la ~/.hermes/logs/backup_v3_20260609_*.log | tail -3
```

## 效能數據（2026-06-09 實測）

- 備份大小：~750 MB（8672 個檔案）
- 速度：1.0-1.3 MiB/s（Google Drive crypt remote）
- 預估時間：8-10 分鐘
- 實際耗時：2026-06-09 05:34 開始，05:44 完成（約 10 分鐘）

## If→Then

**If** cron job `last_error` 顯示 `Script timed out after 120s` 且 jobs.json 的 `timeout_seconds` 已設夠大
**Then** 問題不是 jobs.json，而是 Scheduler 的 module 層級覆寫
**Then** 設定 `HERMES_CRON_SCRIPT_TIMEOUT` env var（最高優先順序）+ `cron.script_timeout_seconds` config + 重啟 gateway

**If** 需要讓 cron script 跑超過 2 分鐘
**Then** 都要設定 `HERMES_CRON_SCRIPT_TIMEOUT`，不要只靠 jobs.json 的 `timeout_seconds`