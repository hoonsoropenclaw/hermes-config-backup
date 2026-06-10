# Cron Job 失敗案例記錄（2026-06）

## eval-sync 雙重故障（2026-06-07 → 2026-06-08）

**Job**: `eval-sync`（每日 10:00）
**Script**: `/home/hoonsoropenclaw/.hermes/scripts/sync_evaluations.py`

**錯誤訊息（2026-06-07 10:04）**：
```
[2026-06-07 10:04:25] ERROR: AGENT_API_KEY not found in hermes-portal/.env.local
```

**2026-06-08 調查發現：實際有兩個獨立 bug**

### Bug 1：Python startswith() 語法錯誤（LINE 32）

`sync_evaluations.py` 第 32 行：
```python
# 錯誤（❌）— 缺少 ) 關閉第一個 startswith：
if line.startswith("AGENT_API_KEY=*** or line.startswith("export AGENT_API_KEY=*** 正確（✅）：
if line.startswith("AGENT_API_KEY=*** or line.startswith("export AGENT_API_KEY=***")...thon 把「or line.startswith("export...」視為同一個字串參數的延續，因為缺少 `)`。結果：`SyntaxError: unterminated string literal (detected at line 32)`。

### Bug 2：Vercel env pull 把 AGENT_API_KEY mask 成 `***`

`.env.local` 中 `AGENT_API_KEY=*** 字元 placeholder，`***` 是 Vercel 的遮蔽值，不是真實 key。

**這個遮蔽不可逆**：`vercel env pull` 不會保留真實值，之後從 `.env.local` 永遠讀不到真正的 key。

**修復**：
1. 到 Vercel Dashboard → Settings → Environment Variables → 找到 `AGENT_API_KEY` → 刪除
2. 重新 `Add` 一個新值（用 `openssl rand -hex 32` 生成）
3. **不要用 `vercel env pull`**（會再次 mask）
4. 手動更新 `.env.local` 寫入新 key

---

## skill-usage-daily-v3 git push rejection → 自我修復成功（2026-06-08）

**Job**: `skill-usage-daily-v3`（每日 00:00）
**Script**: `/home/hoonsoropenclaw/.hermes/scripts/run_skill_stats.sh`

**錯誤訊息（2026-06-08 00:00）**：
```
stderr:
To github.com:hoonsoropenclaw/raphael-status-site.git
 ! [rejected]        main -> main (fetch first)
error: failed to push some refs
```

**根因**：cron 執行期間，remote（GitHub Actions cache 或其他 worker）已更新 `origin/main`，local 落後。

**修復機制**：`run_skill_stats.sh` 中的 `deploy_with_git_recovery()` 函數：
1. `git fetch origin main`
2. `git rebase origin/main`
3. `git push origin main`（retry）
4. 最多 2 次 retry

**驗證（2026-06-08 05:xx）**：
```bash
cd /home/hoonsoropenclaw/hermes-status-site
git rev-parse HEAD && git rev-parse origin/main
# 兩個 SHA 相同：ec003b78a5dc91bef545e7054813d62cff037f6e
# 表示 local == remote，sync 成功
```

---

## hermes-config-backup-daily timeout after 120s（2026-06-08）

**Job**: `hermes-config-backup-daily`（每日 03:00）
**Script**: `/home/hoonsoropenclaw/.hermes/scripts/backup_hermes.sh`

**錯誤訊息**：
```
last_error: Script timed out after 120s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes.sh
```

**根因**：stale `.backup.lock` 檔案（03:00 建立，05:33 仍存在）。

`backup_hermes.sh` 使用互斥鎖防止同時間跑兩次：
```bash
LOCKFILE="$HERMES_HOME/backups/.backup.lock"
if [ -f "$LOCKFILE" ]; then
  exit 0  # 直接退出，沒有任何輸出
fi
```

若前一次執行被中斷（Ctrl+C、OOM kill、120s timeout 觸發的 SIGKILL），lock 來不及刪除。之後每次執行直接退出（看似「卡住」），hermes cron 等 120s timeout 才放行。

**修復**：
```bash
rm -f /home/hoonsoropenclaw/.hermes/backups/.backup.lock
```

**驗證**：
```bash
ls -la /home/hoonsoropenclaw/.hermes/backups/.backup.lock
# 檔案不存在 = 修復成功
```

**預防**：lock 檔案應有 TTL（age > 1 小時視為過期，自動刪除）

---

## hermes-config-backup-daily timeout → v3 升級（2026-06-08 確認修復）

**Job**: `hermes-config-backup-daily`（每日 03:00）
**Script**: `~/.hermes/scripts/backup_hermes.sh` → 已改為 `backup_hermes_v3.sh`

**2026-06-08 16:48 驗證**：
- jobs.json 中 `script` 已改為 `backup_hermes_v3.sh`
- backup_hermes_v3.sh 使用 rclone sync（而非 tar.gz + rclone copy）
- rclone mkdir bug（Type H）已修復：`rclone mkdir` 每次一個路徑，不可多參
- lock file 機制：TTL > 1 小時自動刪除（已実装）

**驗證命令**：
```bash
grep -A3 '"hermes-config-backup-daily"' ~/.hermes/cron/jobs.json | grep script
# 輸出："script": "backup_hermes_v3.sh" ✅

ls -la /home/hoonsoropenclaw/.hermes/backups/*.tar.gz | head -5
# 2026-06-08 03:02 有備份檔（1.1GB full + 10MB public）✅
```

---

## Camofox watchdog 每 6 分鐘重啟（持續監控中）

**Watchdog**: `/tmp/camofox-watchdog.sh`（每分鐘執行 via crontab）
**Container**: `camofox-browser:135.0.1-x86_64`

**狀態（2026-06-08）**：Watchdog 已部署進 crontab ✅，container 每 6 分鐘重啟是預期行為（非 bug）

**驗證命令**：
```bash
# 看 watchdog 是否在 crontab
crontab -l | grep camofox

# 看 container uptime
docker ps | grep camofox

# 看 watchdog log
tail -5 /tmp/camofox-watchdog.log
```

**觀察**：每 6 分鐘重啟可能是 Camofox 的預期行為（記憶體管理機制），待進一步確認。