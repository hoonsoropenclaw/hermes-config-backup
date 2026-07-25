# 路徑修正參考（2026-06-03）

## 三大專案路徑對照表

| 專案 | 本機路徑 | GitHub | Vercel Project |
|------|----------|--------|----------------|
| hermes-status-site（自身狀態網站） | `/home/hoonsoropenclaw/hermes-status-site/` | hoonsoropenclaw/raphael-status-site | prj_6FcNdvnHwPoXdkjr5csknUVJ5bUX |
| hermes-portal（評價網站） | `/home/hoonsoropenclaw/hermes-portal/` | hoonsoropenclaw/hermes-portal | prj_uUsJw3x4NZCofkO1KKFT7viCNvLD |
| 舊狀態頁（OpenClaw） | `~/.openclaw/workspace/status_dashboard/` | — | — |

## 腳本路徑（已修正）

| 腳本 | 正確路徑 |
|------|----------|
| skill_usage_stats.py | `/home/hoonsoropenclaw/.hermes/scripts/skill_usage_stats.py` |
| sync_scheduler.py | `/home/hoonsoropenclaw/.hermes/scripts/sync_scheduler.py` |
| sync_evaluations.py | `/home/hoonsoropenclaw/.hermes/scripts/sync_evaluations.py` |
| run_skill_stats.sh | `/home/hoonsoropenclaw/.hermes/scripts/run_skill_stats.sh` |
| portal_upload_check.sh | `/home/hoonsoropenclaw/scripts/portal_upload_check.sh` |

## 錯誤軌跡（供日後調適）

1. 將 `hermes-portal` 的 `AGENT_API_KEY`（`hms_hermes...y_2026`，33字）用於 hermes-status-site 的部署腳本 → 錯誤
2. 將 `hoonsor/Rimuru_and_Raphael`（備份倉庫）當成 status site repo → 錯誤
3. 將 `~/.openclaw/workspace/status_dashboard/` 當成 hermes-status-site 的本機路徑 → 錯誤
4. cron job `skill-usage-daily-v3` 的 script path 原本指向 `~/.hermes/skills/productivity/hermes-status-site/scripts/` → 錯誤（已修正）

## 預防原則

每次執行「部署/同步/更新」前，必須先確認：
1. 目標是哪個專案（status site 或 portal）？
2. 使用的 API key 是哪一個？
3. git remote 是否正確？

**驗證指令**：
```bash
# 確認 hermes-status-site 的 git remote
cd /home/hoonsoropenclaw/hermes-status-site && git remote -v

# 確認 hermes-portal 的 git remote
cd /home/hoonsoropenclaw/hermes-portal && git remote -v

# 確認 hermes-status-site 的 Vercel project
cd /home/hoonsoropenclaw/hermes-status-site && vercel projects ls --token $VERCEL_API_TOKEN | grep raphael
```