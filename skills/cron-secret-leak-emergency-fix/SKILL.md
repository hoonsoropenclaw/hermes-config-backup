---
name: cron-secret-leak-emergency-fix
description: "緊急修復 cron sync 腳本把 secrets 推到公開 GitHub 觸發 GH013 的完整流程（2026-06-06 實戰）。從識別 → MEMORY scrub → 腳本修補 → git filter-repo 重寫歷史 → force push。當 cron last_error 含 GH013/Vercel Token/GitHub PAT 時自動喚醒。"
version: 1.1.0
author: Hermes Agent (auto-saved)
platforms: [linux]
metadata:
  hermes:
    tags: [cron, gh013, secret-leak, git-filter-repo, emergency, security, public-github]
    triggers: [GH013, push protection, secret scanning, vcp_ token leak, cron error GH013]
---

# Cron Sync 腳本 Secret Leak 緊急修復 SOP

> 觸發情境：cron sync 腳本（`sync_md_files.py` / `run_skill_stats.sh` 等）把本地 secrets 推到公開 GitHub repo，GitHub push protection (GH013) 擋下，cron 連續失敗 4+ 天。
> 建立日期：2026-06-06（從 skill-usage-daily-v3 真實事件歸納）

## 何時使用

- `hermes cron list` 顯示 `last_error` 含 `GH013` / `Repository rule violations` / `Vercel Personal Access Token` / `GitHub PAT`
- 任何 cron 觸發 git push 到公開 GitHub repo 並被擋
- 發現 MEMORY.md / USER.md / 其他 sync 檔內含 `vcp_*` / `ghp_*` / `sk-*` 字面值

## 修復步驟（按下順序執行）

### 1. 識別 root cause（不要只修症狀）

```bash
# 找出哪個檔案 / 哪個 commit 有 secret
cd /home/hoonsoropenclaw/<被推的 repo>
git log --all --oneline | head -10
git grep -nE "vcp_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}" $(git log --all --pretty=format:%H) 2>&1 | head
```

常見位置：
- `assets/md-files.json`（sync MEMORY.md 進來）
- `assets/md-files.html`（同上）
- `tabs/*.html`（SPA 內嵌）
- cron script 本身（fallback default 值）

### 2. Scrub MEMORY.md / USER.md 等源頭

```python
# /home/hoonsoropenclaw/.hermes/memories/MEMORY.md
# 找出所有 token 字面值
grep -nE "vcp_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}" ~/.hermes/memories/*.md
# 改成 *** + 註記「已撤銷」
```

### 3. 修補 sync 腳本（防止再犯）

加 **pre-write secret scan**：

```python
import re
SECRET_PATTERNS=***    (re.compile(r"vcp_[A-Za-z0-9]{20,}"), "Vercel Token"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"sk-[A-Za-z0-9]{40,}"), "OpenAI/Anthropic API Key"),
    (re.compile(r"hms_[A-Za-z0-9_]{20,}"), "Hermes Portal API Key"),
]

def scan_for_secrets(text: str, source: str) -> list[str]:
    return [name for pat, name in SECRET_PATTERNS if pat.search(text)]

def scrub_secrets(text: str) -> str:
    for pat, name in SECRET_PATTERNS:
        text = pat.sub(f"[{name} REDACTED]", text)
    return text

# 在寫入檔案前
content = read_md(memory_file)
hits = scan_for_secrets(content, memory_file.name)
if hits:
    print(f"[SECRET-LEAK] {memory_file.name}: {hits}")
    content = scrub_secrets(content)
# 然後才寫入
```

**Also remove hardcoded token fallbacks**（常見 bug）：
```python
# ❌ 原本（有 leak 風險）
token = os.environ.get("VERCEL_TOKEN", "vcp_0QidbfQdpml...")

# ✅ 修正
token = os.environ.get("VERCEL_TOKEN") or os.environ.get("VERCEL_API_TOKEN")
if not token:
    print("[DEPLOY] ERROR: VERCEL_TOKEN/VERCEL_API_TOKEN not set")
    return False
```

### 4. 用 git-filter-repo 重寫歷史

`git filter-branch` 對「相同內容不同 SHA」沒效，必須用 `filter-repo`：

```bash
# 下載（如果未安裝）
curl -sL -o /tmp/git-filter-repo.tar.xz \
  "https://github.com/newren/git-filter-repo/releases/download/v2.47.0/git-filter-repo-2.47.0.tar.xz"
tar -xJf /tmp/git-filter-repo.tar.xz -C /tmp/
export PATH=/tmp/git-filter-repo-2.47.0:$PATH

# 備份
cp -r .git /tmp/<repo>-git-backup

# 重寫歷史
cd /path/to/repo
git filter-repo --force --replace-text <(echo 'LEAKED_TOKEN==>***REDACTED***')

# 重新加 remote（filter-repo 會移除 origin）
git remote add origin git@github.com:USER/REPO.git

# Force push
git push origin --force --all
```

**驗證歷史已清乾淨**：
```bash
git grep -l "LEAKED_TOKEN"  # 應無輸出
```

### 4.5 強制驗證清單（任何 GH013 修復完成前必跑）— 2026-06-06 新增

⚠️ **2026-06-06 教訓**：sub-agent 修復 GH013 時，scrub 源頭 + filter-repo + force-push 看起來都做了，**但下次 cron cycle 仍 GH013 error**。Root cause：本地確實有 scrub commit，但 force-push 因某環節失敗/被跳過，導致 `origin/main` 仍含舊有 token commit。Sub-agent 的 self-report 寫「git push 從 GH013 blocked 變 success」但**沒人親自驗證** `HEAD == origin/main`。

修復完成後，**任何一步不通過就不算修好**：

```bash
# (1) 確認有 scrub commit
git log --all --oneline | grep -iE "scrub|secret|GH013"   # 應有匹配

# (2) 確認所有歷史 commit 無 token（不只 HEAD）
git grep -nE "vcp_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}" $(git log --all --pretty=format:%H) 2>&1 | head
# 應無輸出

# (3) **關鍵**：確認本地 HEAD 與遠端 origin/main SHA 完全對齊
git rev-list --left-right --count HEAD...origin/main
# 必須輸出 "0\t0"（HEAD 沒有 origin 沒有的 commit，origin 沒有 HEAD 沒有的 commit）
# 若輸出非 0\t0 → 還沒 force-push 成功，回到 Step 4

# (4) 手動跑一次 cron script，看 exit code 0 + push 輸出
bash ~/.hermes/scripts/<the-failing-script>.sh
echo "Exit: $?"
# 預期：最後幾行包含 "main -> main" 與 Vercel deploy URL

# (5) 若有 deploy step，確認 deploy URL 200 OK
curl -sI <deploy-url> | head -1
```

**If** Step 4.5 任一步失敗
**Then** 回到 Step 4 重新執行；不要相信 sub-agent 寫的「✅ 已修復」self-report

### 5. 撤銷被洩漏的 token

無論 GitHub 是否有自動撤銷，**自己動手**到對應 service 撤銷：
- Vercel → Settings → Tokens → 撤銷 `vcp_*`
- GitHub → Settings → Developer settings → Personal access tokens → 撤銷 `ghp_*`
- OpenAI / Anthropic → Dashboard → API keys → 撤銷

**注意**：cron 用的 token 若跟被洩漏的同一個，撤銷後 cron 會立刻壞掉。撤銷前**先確認已有新 token 替換**。

### 6. 觀察 cron next run 是否成功

```bash
hermes cron list 2>&1 | grep -B 1 -A 6 "name: <cron_name>"
# 觀察 next_run 後 last_status 是否變 ok
```

⚠️ **不要只看 `hermes cron list` 狀態**——`last_run_at` 只在下次排程執行後才更新。要立即驗證就跑 `bash $script_path` 看 exit code 0。

## If→Then 規則

| If | Then |
|------|------|
| cron `last_error` 含 `GH013` | 立刻跑本 SOP，**不要只記錄** |
| 任何 `sync_*.py` 寫入公開 GitHub repo | 必須有 pre-write secret scan |
| `assets/md-files.json` / `*.html` 出現 `vcp_*` / `ghp_*` | 源頭是 `MEMORY.md` 等被 sync 的檔案，scrub 源頭 + JSON |
| 發現 sync 腳本有 hardcoded token fallback | 立刻移除，改用 `os.environ.get(...) or sys.exit()` |
| push 被擋但已用 `git filter-repo` 清歷史 | `git remote add origin ... && git push --force --all` |
| token 已在多個 commit 中 | `filter-branch` 不夠，必須 `filter-repo` 重寫 SHA |
| **scrub + filter-repo 已做完但 cron 仍 GH013**（**2026-06-06 新增，最常見陷阱**）| **本地有修但遠端沒 force-push**。執行 `git push origin main --force-with-lease` 後用 `git rev-list --left-right --count HEAD...origin/main` 確認為 `0\t0`。完成前不可信 sub-agent 的「已修復」self-report |
| sub-agent 報告「已修復 GH013」但無驗證輸出 | **不要相信**。重跑 Step 4.5 強制驗證清單，缺一步就不算修好 |
| 修復類任務（任何 cron 失敗、deploy 失敗）| 在最終輸出附上 3 個命令的真實輸出（git rev-list、bash script exit code、deploy URL），不能只寫 "✅" |

## 已知陷阱

1. **`git filter-branch` 對「相同內容」不重寫 SHA**——commit blob hash 一樣就不算修改。必須用 `filter-repo`。
2. **`git filter-repo --force` 會移除 `origin` remote**——記得在 push 前 `git remote add origin ...` 加回。
3. **`gh secret-scanning/alerts` 對 push-time 觸發的 GH013 沒有 open alert**——查 alerts 列表會顯示 0，但 push 仍被擋，因為 push protection 是另外的機制。
4. **GitHub 給的 unblock URL（如 `/security/secret-scanning/unblock-secret/XXX`）需要 user web 登入**——agent 用 API token 訪問會返回 404。
5. **Python sandbox 把 `ghp_*` / `vcp_*` 遮罩成 `***`**（`alt-token-secrets-layout` 已有記載）——debug 寫 token 字面值時會踩坑。
6. **scrub 後 push 仍失敗**通常是「commit 內仍含 token」而不是「工作目錄內含 token」——需要 `git log --all` 找歷史。
7. **🚨 Sub-agent self-report 不可信（2026-06-06 教訓）**：上次 cycle 報告「✅ git push 從 GH013 blocked 變 success」、「SOP validator 6/6 passed」，但**實際上 force-push 沒成功執行**，下次 cycle 仍 error。**強制規範**：修復完成後必須親自跑 Step 4.5 驗證清單，**不可只信 sub-agent 的文字輸出**。若上個 cycle 說「已修好」但 cron 仍 error，第一個懷疑對象就是 sub-agent 沒做 force-push（本地有 scrub commit 但 origin/main 仍舊）。
8. **本地 history 已 rewrite 但 cron 仍 GH013**——99% 是「本地有修，遠端沒 force-push」。用 `git push origin main --force-with-lease`（用 `--force-with-lease` 而非 `--force`，避免覆蓋他人 commit），然後跑 `git rev-list --left-right --count HEAD...origin/main` 必須為 `0\t0`。

## 驗證清單

完成後**必須親自驗證**（不可只信 sub-agent self-report）：

- [ ] `git log --all --oneline | grep -iE "scrub|secret"` 有 scrub commit
- [ ] `git grep -nE "vcp_|ghp_" $(git log --all --pretty=%H)` 在所有歷史 commit 中無 token
- [ ] `git rev-list --left-right --count HEAD...origin/main` 為 `0\t0`（本地與遠端 SHA 完全對齊）— **🚨 這是 2026-06-06 新增的關鍵驗證，本地有修不等於遠端有修**
- [ ] 手動 `bash ~/.hermes/scripts/<script>.sh` 看 exit code 0 + grep 輸出「main -> main」+ Vercel deploy URL
- [ ] `git push origin main --force-with-lease` 不再被 GH013 擋
- [ ] cron `last_status: ok`（下次排程後更新）
- [ ] `MEMORY.md` 等源頭檔已用 `***` 取代具體值
- [ ] sync 腳本有 pre-write secret scan
- [ ] sync 腳本無 hardcoded token fallback
- [ ] 被洩漏的 token 已在 service 撤銷 + 新 token 部署

## 相關 SKILL

- `alt-token-secrets-layout` — 正確的 GPG 加密 + 雙目錄分離儲存 + Python sandbox 遮罩問題
- `portal-401-troubleshoot` — 401 問題排查（eval-sync 的另一條失敗鏈）
- `cron-job-health-monitor` — cron 失敗自動分類 + 修復入口
- `metacognitive-learner` — Phase 1.5 cron 健康掃描（每次啟動必跑）

## 參考文件

- `references/2026-06-06-case-self-report-failure.md` — 04:00 sub-agent self-report「已修復」但實際只完成 80% 的完整 case study（必讀）
