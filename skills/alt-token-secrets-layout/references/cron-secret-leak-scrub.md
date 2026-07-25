# Cron Job 同步 Secrets 到公開 GitHub — 緊急 Scrub SOP

> 建立日期：2026-06-05
> 觸發情境：`md-files-daily-sync` 或 `sync_md_files.py` 把 hermes-portal 的 `AGENT_API_KEY` / `vcp_` token 同步到 `assets/md-files.json`，推到 `raphael-status-site`（**公開 GitHub repo**），被 GitHub push protection (GH013) 擋下，導致 `skill-usage-daily-v3` cron 連續失敗。

## 觸發症狀

```bash
hermes cron list 2>&1 | grep -B 1 -A 8 "skill-usage-daily-v3"
# 顯示:
# Last run: ...  error: Script exited with code 1
# stderr:
# remote: error: GH013: Repository rule violations found for refs/heads/main.
# remote: - GITHUB PUSH PROTECTION
# remote:   — Vercel Personal Access Token —
# remote:      locations:
# remote:        - commit: a4c14...
# remote:          path: assets/md-files.json:40
```

**這是真實發生過的事件**（2026-06-05 skill-usage-daily-v3 失敗原因）。

## 為什麼會發生

`md-files-daily-sync` 是設計來把 `~/.hermes/memories/*.md`（含 `MEMORY.md`、`USER.md`）同步到 hermes-status-site 的 `tabs/md-files.html` 與 `assets/md-files.json`。同步時如果 `MEMORY.md` 內含任何 token 字面值（`ghp_xxx` / `vcp_xxx`），就會原封不動進到公開 GitHub repo。

更糟的情境：本次是 `hermes-portal/.env.local` 的 `AGENT_API_KEY`（值是 `***`）因為某個除錯記錄貼進了 MEMORY.md，被同步到 `assets/md-files.json` 然後 commit。

## 緊急修復步驟（按下順序執行）

### 1. 立即阻斷 cron

```bash
# 暫停 md-files-daily-sync
hermes cron edit <job_id> --enabled false
# 或直接改 jobs.json 設 enabled=false
```

### 2. Scrub 公開 repo 內的 secrets

```bash
cd /home/hoonsoropenclaw/hermes-status-site
# 從最新 commit 撤回（最常見情境：token 在 HEAD）
git rm --cached assets/md-files.json
sed -i 's/ghp_[A-Za-z0-9]\{36\}/***REDACTED***/g; s/vcp_[A-Za-z0-9]\{40,\}/***REDACTED***/g' assets/md-files.json
git add assets/md-files.json
git commit --amend --no-edit
# 注意：用 --amend 改最後一個 commit，token 仍在歷史
```

### 3. 清掉 Git 歷史中的 token（嚴重情境）

如果 token 已在多個 commit 中（必須做這步，否則 push 仍會被擋）：

```bash
# 用 bfg-repo-cleaner（推薦，比 git filter-branch 快）
# 安裝：brew install bfg（mac）或 scoop install bfg（windows）
# Linux：
wget -O /tmp/bfg.jar https://repo1.maven.org/maven2/com/madgp/bfg/1.14.0/bfg-1.14.0.jar
java -jar /tmp/bfg.jar --replace-text <(echo '***REDACTED***') assets/md-files.json

# 或用 git filter-branch（更慢但內建）
git filter-branch --force --index-filter \
  "git ls-files | grep md-files.json | xargs sed -i 's|vcp_[A-Za-z0-9]\{40,\}|***REDACTED***|g'" \
  --prune-empty --tag-name-filter cat -- --all

# 強制 push（會改寫遠端歷史，警告：若有人 pull 過會 conflict）
git push origin --force --all
```

### 4. 立刻撤銷被洩漏的 token

無論 GitHub 是否有自動撤銷——**自己動手**到 Vercel Dashboard → Settings → Tokens 撤銷那個 `vcp_` token，重新生成。

### 5. 修補同步腳本（防止再犯）

`md-files-daily-sync` 必須加 pre-commit hook：

```bash
# 在 sync_md_files.py 內，git add 前先 scrub
import re
files_to_check = ["assets/md-files.json", "tabs/md-files.html", "tabs/mdfiles.html"]
SECRET_PATTERNS = [
    (r"ghp_[A-Za-z0-9]{36}", "GitHub PAT"),
    (r"vcp_[A-Za-z0-9]{40,}", "Vercel Token"),
    (r"***", "Hermes Portal API Key"),
]
for f in files_to_check:
    p = Path(f)
    if not p.exists():
        continue
    content = p.read_text()
    for pattern, name in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            raise RuntimeError(f"SECRET LEAK DETECTED: {name} in {f} ({len(matches)} occurrences). Aborting sync.")
```

### 6. 把 secrets 從 MEMORY.md 永久清掉

```bash
# 找含 token 字面值的行
grep -nE "ghp_[A-Za-z0-9]{36}|vcp_[A-Za-z0-9]{40,}|***" \
  /home/hoonsoropenclaw/.hermes/memories/*.md
# 改成用 *** 取代 + 加註記
```

### 7. 重啟 cron 驗證

```bash
hermes cron edit <job_id> --enabled true
# 觀察下次執行是否還 GH013
```

## 預防設計（給 sync_*.py 系列腳本通用）

**所有「把本地檔同步到公開 GitHub repo」的腳本必須內建**：

1. **Pre-commit secret scan** — `git diff --cached` 前跑 `detect-secrets` 或上面的 regex 列表
2. **Output 是「渲染後的 HTML/JSON」而非「原始 .md 拷貝」** — `assets/md-files.json` 應該是 preprocessed 過的，token 一律 `***` 化
3. **`.gitignore` 內加 `*.env.local`、`*.gpg`**（雖然不直接相關，但保險）
4. **每次 commit 觸發 GitHub Action** `gitleaks` 或 `trufflehog` 雙重把關

## 教訓

> **絕對禁止把本地 secrets 同步到公開 GitHub repo。** 即使加密過的（`*.gpg`）也不行——金鑰可能在其他地方洩漏過，公開檔案結構本身已是資訊洩漏。

> **MEMORY.md 等「會被同步的檔案」**只能放「抽象教訓」「規律」「行為指引」，**不放具體 token、不放具體值、不放路徑下的具體檔名**——這些一旦同步出去就是 credential leak。

## 相關 SKILL

- `alt-token-secrets-layout` — 正確的 GPG 加密 + 雙目錄分離儲存
- `portal-401-troubleshoot` — Step 5.5 多行 `.env.local` 陷阱（同步腳本讀錯 token 也會引發 401）
- `cron-job-health-monitor` — 自動偵測 GH013 等 secret leak
