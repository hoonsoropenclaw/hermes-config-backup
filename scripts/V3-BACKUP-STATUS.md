# Hermes Backup v3（2026-06-06 試作、暫停狀態）

## 為什麼 v3 沒成功取代 v2

v3 用 `rclone sync` 把 `~/.hermes/` 當目錄同步到 Drive `hermes-backup/v3/current/`。
設計目標：增量、可差異還原、避免 694 MB 大 tar.gz。

**實際問題**：
- Google Drive 對單一帳號短時間大量小檔 API 配額太嚴格
- 跑兩次都被 throttle（速度從 1 MiB/s 掉到 3-28 KiB/s）
- v2 大 tar.gz 雖慢 1 小時但只需 1 個 API request、穩定

## 現狀（截至 2026-06-06 23:50）

- ✅ v3 腳本完成：`backup_hermes_v3.sh` + `hermes-restore-v3.sh`
- ✅ Drive `hermes-backup/v3/{current,manifests,snapshots}/` 目錄已建
- ✅ Drive `current/` 內有 ~600 個檔案 / 309 MiB（60% 進度）
- ❌ 沒跑完（被 throttle 兩次）
- ❌ Manifest / snapshot 都沒產（進度到 sync 就卡住）
- ❌ **不接 cron**（v2 繼續用）

## 為什麼保留而不刪

- 309 MB 已上傳的成本已經付出
- 未來 Drive 配額放寬、或換雲端（如 S3）可立即接上
- v3 腳本邏輯完整，未來調整後可用

## 未來重啟 v3 的時機

If 滿足以下任一條件，可重評估 v3：
- Google Drive 放寬 API 配額（罕見）
- 換雲端備份服務（S3 Backblaze B2 — 對小檔較友善）
- `rclone` 改用 chunked upload（避免單檔 1 個 request）
- 或用 `rclone copy --files-from` 分批同步（每天一塊）

## 排除清單（v3 的精華 — 留作參考）

```bash
RCLONE_EXCLUDES=(
  "--exclude=backups/**"                # 本地備份
  "--exclude=hermes-agent/venv/**"      # Python venv
  "--exclude=**/node_modules/**"        # Node 模組
  "--exclude=**/.git/**"                # Git metadata
  "--exclude=cache/**" "--exclude=logs/**"
  "--exclude=lsp/**" "--exclude=bin/**"
  "--exclude=sessions/**"
  "--exclude=state.db-wal"
  "--exclude=models_dev_cache.json"
  "--exclude=hermes-backup-staging/**"  # GitHub 已有
  "--exclude=skills/.archive/**"        # 垃圾桶
)
```

排除後：`13611 個檔案 / 509 MB`（vs 全部 `15804 / 538 MB`）

## 異機還原的兩條路徑

### v2（現行，簡單可靠）
- Drive 上找最新 `hermes_backup_<ts>_full/`
- `rclone copy` 整個資料夾（含 694 MB tar.gz）
- 解 tar、跑 `restore_hermes.sh`
- 耗時：~60 分鐘（rclone crypt 191 KiB/s）

### v3（目錄式，未驗證可用）
- `rclone copy crypt_hermes:hermes-backup/v3/current/config/ ~/.hermes/`
- `rclone copy crypt_hermes:hermes-backup/v3/current/cron/ ~/.hermes/cron/`
- ... 挑需要的目錄拉
- 耗時：核心還原 5-10 分鐘、完整 30-60 分鐘
- ⚠ 但**目前不完整**（只有 60% 進度、沒 manifest）

## L3 教訓（已寫入 trial-and-error skill）

- Rule 8：Drive rate limit 會卡死 rclone sync
- Rule 9：備份策略分層（v3 起）
- Rule 10：Drive 對 rclone sync 小檔目錄會重複 throttle
