# Hermes Internal 踩坑目錄

## `last_status` 跟 jobs.json 修復狀態完全解耦

**症狀**: jobs.json 已修復（timeout_seconds 600→3600），但 `hermes cron list` 仍顯示 `last_status: error`。

**根因**: `last_status` 由 Scheduler 在 cron tick 時更新，不會因為 jobs.json 改了就自動翻。必須等下一次 cron tick（最多 60 秒後）才更新。兩者完全獨立。

**正確流程**:
1. 修復 jobs.json
2. 手動觸發：`hermes cron run <job_name>` 或 `hermes cron tick`
3. 等待 60 秒
4. `hermes cron list` 看 `last_status` 是否翻轉

**If** 想立即驗證狀態翻轉：
```python
python3 -c "
import json
d = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name') == '<job_name>':
        print('last_status:', j.get('last_status'))
        print('last_run_at:', j.get('last_run_at'))
"
```

---

## 預防 stale state 的三步排除前置檢查

看到 `last_status: error` **不要立刻**進緊急修復模式。三步排除：

1. **手動跑該 script** 確認邏輯 OK（如 `bash ~/.hermes/scripts/<script>.sh`、exit code 0）
2. **交叉驗證 jobs.json**（`script`/`prompt`/`timeout_seconds` 跟 trial-and-error 建議值一致）
3. **看 cron output dir**（`ls -lat ~/.hermes/cron/output/<job_id>/`）跟 **journalctl**（`journalctl -u hermes-gateway -n 30 --no-pager`）

**判定**:
- 三步都過 → **stale state**，**不是新 bug**，不進緊急修復模式
- 三步任一失敗 → 真實 bug，走原 SOP（緊急修復）

---

## GitHub push 403 + SSH 配置問題（2026-06-12）

**症狀**: `git push` 失敗且錯誤為 `remote: Permission to ... denied to hoonsor. The requested URL returned error: 403`，但 `gh auth status` 顯示 `Git operations protocol: ssh`。

**根因**: staging repo 的 `.git/config` 中 `remote.origin.url` 是 `https://github.com/...`（HTTPS），但 gh 已登入 SSH。Credential helper chain 沒正確轉交 HTTPS 認證。

**修復**:
```bash
cd ~/.hermes/hermes-backup-staging
git remote set-url origin git@github.com:hoonsoropenclaw/hermes-config-backup.git
git push origin main  # 驗證：Everything up-to-date
```

**預防**: 備份 script 在 staging 不存在時可能重新 clone，需在 script 中加 `git remote set-url origin git@github.com:...` 在 clone 後。

**相關條目**: [[hermes-backup-strategy.md]] [[hermes-backup-design-pitfalls.md]]

---

## 重啟 gateway 時間成本（2026-06-11 觀察）

`sudo systemctl restart hermes-gateway.service` 觸發 graceful stop、會卡 90~210 秒才完成 PID 切換：
- `Type=simple` 沒設 `TimeoutStopSec`、systemd 預設 90s 後才 SIGKILL
- 為什麼 graceful 慢：gateway 跑 async telegram long polling、收到 SIGTERM 後等 in-flight agent request 跑完（典型 30~90s）+ telegram API 釋放連線

**正確操作序列**:
```bash
# 1. 觸發 restart（不阻塞）
sudo systemctl restart hermes-gateway.service &

# 2. 立刻輪詢
sleep 30
pgrep -af "hermes_cli.main gateway"   # 看 PID 換沒換
systemctl status hermes-gateway | grep -E "Active:|Main PID:"

# 3. PID 還是舊的、等 60 秒再查
sleep 60
pgrep -af "hermes_cli.main gateway"   # 應該看到新 PID
```

**If** user 明確說「重啟 gateway」**Then** 先預告「會斷 telegram 連線 1-3 分鐘」、分多次查狀態

---

## cron jobs 的 skills 陣列不能放 MCP 工具

**問題**: cron job 的 `skills` 陣列中若包含 MCP 工具（如 `session_search`），會導致連續執行失敗但無阻斷。這些失敗被 `skipped` 標記而非錯誤，長期忽略真正問題。

**正確做法**: cron job 的 skills 陣列只放「存在且穩定」的技能。MCP 工具應視為可選依賴而非必要項目。

---

## `hermes cron edit --script` 對 no_agent jobs 的 Bug

**問題**: `hermes cron edit <id> --script '...'` 對 `no_agent=True` 的 script-only jobs 有 bug：
- `--script` 參數值會被寫入 `prompt` 欄位，而非 `script` 欄位
- Scheduler 的 `_run_job_script()` 對 no_agent jobs 讀取 `prompt` 作為 script path
- 導致錯誤：`"Script not found: /home/hoonsoropenclaw/.hermes/scripts/#!/bin/bash\n..."`

**受影響的 Jobs**: scheduler-sync、eval-sync、skill-usage-daily-v3（連續失敗 4-5 天）

**修復方式**: 直接編輯 `~/.hermes/cron/jobs.json`：
1. 將該 job 的 `prompt` 設為 `null` 或移除該鍵
2. 將 `script` 設為「只有檔名」（如 `sync_scheduler.py`，不含路徑）
3. 確保 `no_agent` 為 `true`

**驗證方式**: 執行 `hermes cron list`，若 `last_error` 包含 `#!/bin/bash` 就是這個 bug

**If** 你需要建立一個 script-only cron job
**Then** 在 jobs.json 中手動創建（不要用 `hermes cron create --script`），確保：
- `prompt` 為 `null`
- `script` 為檔名（如 `run_skill_stats.sh`）
- `no_agent` 為 `true`