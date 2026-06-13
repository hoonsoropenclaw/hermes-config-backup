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

---

### `gh auth git-credential` 在 cron 環境導致 SSH push 403

**症狀**: cron job `v4-backup-tier1-daily` 失敗，error 為：
```
remote: Permission to hoonsoropenclaw/hermes-config-backup.git denied to hoonsor.
fatal: unable to access 'https://github.com/hoonsoropenclaw/hermes-config-backup.git/': The requested URL returned error: 403
```
但 staging repo 是 SSH URL（`git@github.com:hoonsoropenclaw/hermes-config-backup.git`）。

**根因**: `git config --global` 設定了 `credential.https://github.com.helper = !/usr/bin/gh auth git-credential`。SSH 推送時，git 的 credential helper 被錯誤觸發並回傳錯誤帳號（`hoonsor` 而非 `hoonsoropenclaw`）的 token，導致 HTTPS 403。cron 環境下 gh 可能回傳預設活躍帳號而非正確的 `hoonsoropenclaw`。

**解法**: 移除 credential helper（SSH 推送不需要它）：
```bash
git config --global --remove-section credential.https://github.com
git config --global --remove-section credential.https://gist.github.com
```

**驗證命令**:
```bash
# 確認 credential helpers 已移除
git config --global --list | grep credential  # 應無輸出

# 確認 staging SSH URL 不變
cd ~/.hermes/hermes-backup-staging && git remote -v  # 應顯示 git@github.com:...

# 驗證 push 成功
git add -A && git commit -m "test" --allow-empty && git push origin main  # 應成功
```

**預防**: SSH 推送不需要 credential helper。若 GitHub 推送使用 SSH，應移除所有 `credential.https://*.helper` 設定，避免 cron 環境下 credential helper 被錯誤呼叫。

**If→Then**: **If** cron job 的 SSH push 出現 403 且 error 顯示 `denied to hoonsor`（錯誤帳號）**Then** 檢查並移除 `git config --global` 中的 `credential.https://github.com.helper`

---

## Credential 拓撲地圖（2026-06-13 新增）

**症狀**: 用戶抱怨「token 錯誤一直出現」、「哪個 token 對應哪個帳號不知道」。根本原因是赫米斯沒有統一的 credential 拓撲圖，導致同一個 token 被多個腳本以不同方式讀取。

**根因**: 赫米斯的 credential 散布在：
- `~/.hermes/.env`（Source of Truth）
- `~/.hermes/permanent-projects/hermes-portal/.env.local`（Secondary，內含 Vercel mask 值 `***`）
- 某些腳本內 hardcode path

**解法**: 建立 credential_topology_map.py 並持續維護：

```bash
# 查詢任何 token 的完整消費鏈
python3 ~/.hermes/scripts/credential_topology_map.py

# 核心原則
# 1. 所有 credential 只從 ~/.hermes/.env 讀取
# 2. 禁止同時讀多個路徑（sync_evaluations.py 的雙路徑是壞味道）
# 3. cron job 從不應直接持有 token，透過 HERMES_ENV passthrough
```

**token → 消費者對照表**（2026-06-13 現況）：

| Token | Source | 消費者 |
|-------|--------|--------|
| `AGENT_API_KEY` | `~/.hermes/.env` (真實) | eval-sync, sync_evaluations.py |
| `VERCEL_API_TOKEN` | `~/.hermes/.env` | sync_md_files.py, sync_scheduler.py, run_skill_stats.sh |
| `TELEGRAM_BOT_TOKEN` | `~/.hermes/.env` | hermes-gateway, api_quota_monitor.sh, watchdog.sh |
| `GITHUB_TOKEN` | `~/.hermes/.env` (masked) | v4-backup-tier1/2, hermes-backup-v4.sh |
| `MINIMAX_API_KEY` | `~/.hermes/.env` (masked) | hermes-gateway (主要 LLM) |
| `DEEPSEEK_API_KEY` | `~/.hermes/.env` | hermes-gateway (備援) |
| `OLLAMA_WEB_SEARCH_API_KEY` | `~/.hermes/.env` | Web search 主軌 |
| `TAVILY_API_KEY` | `~/.hermes/.env` | Web search 備軌 |

**已知問題**：`sync_evaluations.py` 同時讀 `hermes-portal/.env.local` 和 `~/.hermes/.env`，但 `.env.local` 中的 `AGENT_API_KEY` 是 Vercel env pull 的 mask 值 `***`，導致 eval-sync 出 401。**永遠只從 `~/.hermes/.env` 讀取**。

**If→Then**: **If** cron job 出現 401 Unauthorized 且涉及 `AGENT_API_KEY` **Then** 檢查該 script 是否從 `.env.local` 讀取（應只從 `~/.hermes/.env`）
**If→Then**: **If** 不確定某個 token 在哪些腳本被使用 **Then** 執行 `grep -r "TOKEN_NAME" ~/.hermes/scripts/`
**If→Then**: **If** 要新增一個 API token **Then** 必須同時更新 `~/.hermes/.env` 和 `credential_topology_map.py`