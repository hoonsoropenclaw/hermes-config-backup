# cron git push rejection recovery

## 發現時間
2026-06-08

## 問題描述
skill-usage-daily-v3 的 `run_skill_stats.sh` 在 cron 環境執行時，git push 到 GitHub 因 remote 有新 commit（另一来源的 push）而被拒絕，導致整個 script exit with code 1，skills.html 更新無法部署到 Vercel。

## 修復
`run_skill_stats.sh` 已內建 `deploy_with_git_recovery()` 函數，邏輯：
1. `git fetch origin main` 獲取 remote 狀態
2. 若 local == remote hash → 已同步，忽略
3. 若低於 max_retries → `git rebase origin/main`  onto remote
4. rebase 衝突 → `git rebase --abort` + `git reset --hard origin/main` + 重新產生 stats + commit + push

## 驗證
```bash
cd /home/hoonsoropenclaw/hermes-status-site && git rev-parse HEAD
# ec003b78a5dc91bef545e7054813d62cff037f6e

cd /home/hoonsoropenclaw && bash .hermes/scripts/run_skill_stats.sh
# [deploy] ✓ git push succeeded
# Vercel deploy: Production: https://hermes-status-site.vercel.app
```

## 預防
所有 cron 部署腳本（含 `sync_md_files.py`、`backup_hermes*.sh`）若會執行 `git push`，都應內建此 recovery 機制，不可假設 git push 第一次就成功。