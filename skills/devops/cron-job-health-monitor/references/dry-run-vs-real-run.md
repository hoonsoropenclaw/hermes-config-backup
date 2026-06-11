# Dry-Run vs Real-Run：備份腳本驗證的關鍵區別（2026-06-11）

## 核心發現

`hermes-backup-v4.sh --dry-run` 成功 ≠ `hermes-backup-v4.sh --tier1` 成功。

dry-run 只驗證：
- rsync 指令語法正確
- git add + commit 語法正確
- 邏輯流程無 syntax error

real-run 還驗證：
- GitHub push 是否被 remote 接受（non-fast-forward、GH013 secret scan、branch protection）
- rclone 認證是否有效（Drive API token、crypt 設定）
- 網路穩定性（rsync 8-10 分鐘傳輸不掉線）

## 實際案例（2026-06-11）

```
$ bash hermes-backup-v4.sh --dry-run  → exit 0 ✓（所有步驟 DRY 標記）
$ bash hermes-backup-v4.sh --tier1    → git push 成功（920734e..c10d269）✓
```

dry-run 和 real-run 都成功，但兩者是不同測試維度。**Phase 1.5 驗證時不能只靠 dry-run 結論 real-run 也能過。**

## If→Then 規則

**If** 驗證 backup cron job 是否正常 **Then** 執行 `bash ~/.hermes/scripts/hermes-backup-v4.sh --tier1`（real run，不是 dry-run），並檢查：
1. `git rev-parse HEAD` 對比 `git rev-parse origin/main`（两个 SHA 相同 = push 成功）
2. Telegram 收到「備份完成」通知（scheduler deliver 成功）
3. last_status 在下次 cron tick 時翻成 `ok`

**If** 只跑 `--dry-run` 就斷言「備份腳本正常」 **Then** 忽略了 git push remote rejection 和網路傳輸失敗兩種真實 failure mode

## 預防

任何 cron backup script 的驗證都要包含：
1. dry-run（語法/邏輯檢查）
2. real-run（git push + 網路傳輸檢查）
3. cron scheduler tick 後 last_status 翻 ok（完整閉環）