# 赫米斯全狀態備份系統實作記錄（2026-06-06）

## 背景

用戶在 2026-06-06 session 中規劃了「備份赫米斯重要檔案到 GitHub 私有 repo」的方案，由 metacognitive-learner 完成實作。

## 實作成果

| 檔案 | 功能 |
|------|------|
| `~/.hermes/scripts/backup_hermes.sh` | 選擇性備份、secret 掃描、GitHub push |
| `~/.hermes/scripts/restore_hermes.sh` | 6 步驟還原腳本 |
| `hermes-config-backup` 私有 repo | https://github.com/hoonsoropenclaw/hermes-config-backup |
| cron job `65f2dc3583d5` | 每日凌晨 3:00 執行 |

## 備份內容（精確版）

只備份有意義的小檔案，不備份大檔案和生成物：

```
config/hermes-config.yaml     ← 14 KB
config/cron-jobs.json         ← 8 KB
memories/*.md                ← 7 個核心 MD 檔
skills/autonomous-ai-agents/   ← SKILL.md + references/
skills/hermes-tier-router/    ← SKILL.md
skills/trial-and-error/       ← SKILL.md + references/
scripts/*.py                  ← 業務邏輯腳本（不含 hermes-agent 源碼）
data/kanban.db                ← 104 KB（小，有意義）
skills/INSTALLED_MANIFEST.md   ← 所有已裝技能清單
```

**不備份**：.env、state.db、hermes-agent/、sparc-methodology/、venv/、sessions/、cache/

## Secret Scanner 設計（重要）

### 問題
舊版 regex `DEEPSEEK_API_KEY=.*[^ "]` 會匹配檔案中「設定 `DEEPSEEK_API_KEY` 環境變數」這類解釋文字，導致 trial-and-error 文件被誤判為含真實 credential。

### 解決：格式匹配而非 key name 匹配

```bash
SECRET_REGEX="ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20,}|vcp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{40,}|hms_[A-Za-z0-9_]{20,}"
```

只匹配具有實際 credential 格式的字串（prefix + 固定長度），不匹配檔案中的變數名提及。

### `set -e` + `grep` 陷阱

```bash
# 錯誤示範（grep 無 match 時返回 exit 1，觸發 set -e 導致 script abort）
FOUND=$(grep -rE "$SECRET_REGEX" "$REPO_DIR" ...)
# 正確寫法
FOUND=$(grep -rE "$SECRET_REGEX" "$REPO_DIR" ... || true)
```

### 驗證方式

```bash
# 測試 secret scanner 不會誤判檔案中的變數名提及
grep -rE "$SECRET_REGEX" ~/.hermes/hermes-backup-staging/ --include="*.md" --include="*.yaml"
# 預期：無輸出（只有變數名提及，無實際值）
```

## 首次執行結果（已驗證）

```
[2026-06-06 14:47:40] === 備份完成：20260606_144732 ===
29 files changed, 3554 insertions(+)
✓ Secret 掃描通過
✓ 已推送
```

repo 驗證：`gh repo view hoonsoropenclaw/hermes-config-backup --json isPrivate` → `"isPrivate":true`

## If→Then 規則

**If** 要設計一個 secret scanner  **Then** 用 credential format（prefix + 長度）匹配，不要用 key name + value 的泛化 regex

**If** `set -e` script 裡用 `FOUND=$(grep ...)` 抓可能無 match 的結果  **Then** 要加 `|| true` 否則會在 grep 返回 exit 1 時觸發 script abort

**If** 備份腳本執行失敗  **Then** 檢查 log (`~/.hermes/logs/backup_*.log`) 找出哪個步驟失敗，不要假設是哪個環節

**If** 需要建立一個 script-only cron job  **Then** 在 jobs.json 中手動創建，不要用 `hermes cron create --script`（該工具有 bug，對 no_agent jobs 會把 script 值寫入 prompt 欄位）

## restore_hermes.sh 使用方式

```bash
bash ~/.hermes/scripts/restore_hermes.sh
```

還原步驟：
1. 檢查前提（hermes-agent 已安裝、gh CLI）
2. Clone backup repo
3. 還原配置檔 + 記憶檔 + skills + 腳本 + kanban.db
4. 提示用戶重新申請 API keys（.env 不進 repo）
5. 重建 cron jobs
6. 驗證關鍵檔案存在

## 相關檔案

- `~/.hermes/scripts/backup_hermes.sh` — 備份腳本（本機）
- `~/.hermes/scripts/restore_hermes.sh` — 還原腳本（本機）
- `https://github.com/hoonsoropenclaw/hermes-config-backup` — 備份 repo
- `~/.hermes/logs/backup_*.log` — 備份日誌