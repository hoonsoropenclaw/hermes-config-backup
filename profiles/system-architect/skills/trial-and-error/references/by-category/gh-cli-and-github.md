# gh CLI / GitHub API 相關踩雷

> 觸發:涉及 gh CLI 指令、GitHub API 呼叫、token 操作、雙帳號切換、**GH013 push protection、GH001 大檔限制、filter-branch 從歷史移除陷阱、backup script 漏掉 skills/ 同步導致 GH013 觸發源沒進 .gitignore**
> 建立時間: 2026-06-05
> 最後更新: 2026-06-07（v4 演進時新增 GH013 完整 SOP + GH001 + filter-branch 壞 repo 修復）
> 條目數: 6（含主條目 2 + 2026-06-06 額外條目 2 + 2026-06-07 新增 2）

---

### gh CLI 對缺 read:org scope 的 token 會拒絕 auth login --with-token
**發現時間**: 2026-06-05
**觸發情境**: 想把 `hoonsor` 帳號的 PAT 加進 gh,跑 `gh auth login --with-token`
**症狀**: 
```
error validating token: missing required scope 'read:org'
```
**根因**: gh CLI 預設對所有新 token 都要 `read:org` scope(用來列 org repo),即使你只用個人 repo 也需要
**解法**: 不要用 gh auth login,改用手寫 `~/.config/gh/hosts.yml`:
```yaml
github.com:
    users:
        hoonsoropenclaw:
            oauth_token: ghp_xxx
        hoonsor:                    # ← 新增
            oauth_token: ghp_yyy
    git_protocol: ssh
    user: hoonsoropenclaw
    oauth_token: ghp_xxx
```
寫完用 `gh auth switch --user hoonsor` 切換。gh auth status 會標 X(因為少 scope),但 `GH_TOKEN=*** gh api user/repos` 走 API 照樣能跑
**預防**: 產生 GitHub PAT 時預先勾 read:org,或接受手寫 hosts.yml 的方式
**相關條目**: [[secrets-and-env#GitHub PAT 加密儲存]]

---

### gh auth status 顯示 Failed 但 GH_TOKEN 環境變數仍可走 API
**發現時間**: 2026-06-05
**觸發情境**: 手寫 hosts.yml 後跑 `gh auth status`
**症狀**: 顯示 `X Failed to log in ... is invalid` + `✓ Logged in to ... account hoonsor` (active 標記在不同帳號)
**根因**: gh CLI 對「自己寫進 yml 但缺 scope」會在 status 標 X,但實際上 token 本身仍有效,可以透過 `GH_TOKEN=*** gh api ...` 直接走 API
**解法**:
- 看到 status 標 X 不要慌張,先實際打一次 API 確認
- 用 `GH_TOKEN=*** python3 -c "import urllib.request; ..."` 完全繞過 gh CLI,直接打 GitHub API,最穩
**預防**: 把「GH_TOKEN 環境變數走 API」當成 fallback,不要完全依賴 gh CLI 的 status 判斷
**相關條目**: [[secrets-and-env#替代 token 加密佈局]]

---

## 跨分類關聯

- gpg 加密 GitHub PAT → [[gpg-encryption#gpg 預設產出檔案 mode 是 0644,加密後必 chmod 0600]] + [[secrets-and-env#替代 token 加密佈局]]
- Python sandbox 寫 gh API 程式 → [[python-sandbox#Python sandbox 把 token 遮罩成 *** 導致字串截斷]]
- GH013 push protection → 見下方 2026-06-07 新增 SOP
- GH001 大檔限制 → 見下方 2026-06-07 新增 SOP
- bash push 假成功 → [[bash-defensive-patterns#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]]


## 額外條目（2026-06-06 從 MEMORY.md 移入）

### gh CLI 對缺 `read:org` scope 的 token 會拒絕 `auth login --with-token`
**症狀**: `gh auth login --with-token < token` 報 Bad credentials 或拒絕
**根因**: 該 token 沒有 `read:org` scope,gh CLI 認為認證不完整
**解法**: 跳過 gh CLI,手寫 `~/.config/gh/hosts.yml` 的 `users:` 區塊;gh auth status 會標 X 但 `GH_TOKEN` 環境變數照樣能走 API
**預防**: 對非主帳號 PAT 不要硬走 gh CLI,直接寫 hosts.yml + 用 GH_TOKEN 環境變數

### `gh repo create --source=. --push` 要求目錄已是 git repo + 至少一次 commit
**發現時間**: 2026-06-06
**觸發情境**: 想把本地新專案（還沒 `git init`）推到 GitHub
**症狀**:
```
$ gh repo create <org>/<name> --source=. --push
current directory is not a git repository. Run `git init` to initialize it
```
**根因**: `--source` 參數預期目錄**已經是** git repo,只幫你加 remote + push。**它不會**幫你做 `git init` / `git add` / `git commit`。
**解法**（完整 SOP,從零開始）:
```bash
cd <project-dir>
git init -b main
# 確認 .gitignore 排除 node_modules、dist、.env 等
git add .
git diff --cached --name-only | wc -l   # 確認檔案數
git config user.email "hermes-agent@users.noreply.github.com"
git config user.name "Hermes Agent"
git commit -m "Initial commit: ..."
# 然後才 gh repo create
gh repo create <org>/<name> --public --source=. --remote=origin --push
```
**預防**:
- 看到 `current directory is not a git repository` 就照上面 6 步走
- `gh repo create` **永遠不會**自己 `git init`,不要期待

**If→Then**:
- **If** 想用 `gh repo create` 推新專案 **Then** 先 `git init` + `git add .` + `git commit`,然後才 `gh repo create --source=. --push`
- **If** 看到 gh 報「current directory is not a git repository」**Then** 走上面的 6 步驟,不要去查 gh 選項（沒有 `--init` 參數）

---

### `vercel whoami` 跟 `gh auth status` 顯示的帳號可能不同 — 兩者不互通
**發現時間**: 2026-06-06
**觸發情境**: 同時用 `VERCEL_API_TOKEN`（team 級 token,綁在 `hoonsors-projects` team）跟 gh CLI（綁在 `hoonsoropenclaw` 個人帳號）
**症狀**:
```
$ vercel whoami
hoonsor              ← Vercel team 級帳號

$ gh auth status
Logged in to github.com account hoonsoropenclaw   ← GitHub 個人帳號
```
**根因**: 
- Vercel API token 是 **team-level**,scope 綁在 `hoonsors-projects` 這個 Vercel team,token 持有者 email 是 `hoonsor@hotmail.com`
- gh CLI 是 **per-user**,綁在 GitHub 個人帳號
- 兩個系統的「當前身份」是**獨立維護**,不會自動同步
- 結果:用 `gh repo create` 把 repo 建在 `hoonsoropenclaw/<name>`（GitHub 主帳號下）,但 Vercel 部署後看到 `hoonsors-projects/<name>`（Vercel team 下）— 看起來是兩個不同的 owner,實際上 Vercel 端是綁 Vercel team 顯示名
**解法**:
- **不要假設兩者身份一致**,部署/推送前分別 `vercel whoami` + `gh auth status` 確認
- 若 repo 應該在「主帳號」(`hoonsoropenclaw`)下,gh auth 切到主帳號再建 repo
- 若 Vercel 部署,確認 `VERCEL_API_TOKEN` 的 scope 跟要部署的專案 team 一致

**預防**:
- 任何「跨平台身份」的操作（gh + vercel + npm + ...）**都先列帳號**,再開始
- 不要因為 gh 是主帳號就假設 Vercel 也是 — Vercel token 是 team 級

**If→Then**:
- **If** `vercel whoami` 跟 `gh auth status` 顯示不同帳號 **Then** 不要假設會自動同步,部署前明確指定「repo 屬於 X、vercel project 屬於 Y」
- **If** 用 `VERCEL_API_TOKEN` 部署 + 用 gh 建 repo **Then** 兩者要分開驗證歸屬,Vercel 顯示 `hoonsors-projects/<name>` 跟 GitHub 顯示 `hoonsoropenclaw/<name>` 都可能是對的（取決於哪邊看）

---

### GH013 push protection 觸發時的完整修復 SOP（2026-06-07 第二次踩到）

**發現時間**: 2026-06-07（2026-06-05 md-files-daily-sync 事件後的第二次踩雷）

**觸發情境**: 把備份（含 `memories/MEMORY.md.bak.*` 4x = 至少 2 個完整 MEMORY 副本）推到公開 GitHub repo

**症狀**:
```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - GITHUB PUSH PROTECTION
remote:   — Push cannot contain secrets
```

**根因**:
- GitHub 公開 repo 啟用 secret scanning,任何 push commit 含 `sk-`、`ghp_`、`AIza` 等真實 API key pattern 就會擋
- 危險來源:備份檔**沒被 .gitignore 排除**、或 `.gitignore` 寫在子目錄（**不會繼承到上層 git add**）
- 這次新坑:`MEMORY.md.bak.1780752174` 這種帶 timestamp 的備份檔,**不在 `*.bak` 模式範圍內**（預設 `*.bak` 不含 `.bak.1234567890`）
- 危險覆蓋:sparc-methodology 內 `agentdb.rvf` 系列、skill 內的 `example.env`、各種 `.lock` 檔

**完整修復 SOP**:

**Step 1**: 砍掉有問題的 commit、保留工作目錄改動
```bash
git reset --soft HEAD~1
# 改動回到 staged、可以重新整理
```

**Step 2**: 從 git 索引 + 實體檔案徹底移除
```bash
# 刪實體檔（避免被 re-add 進來）
rm -f memories/*.bak.* memories/*.lock memories/*.clean.*

# 從 git 索引移除（如果已經 staged）
git reset HEAD memories/

# 加強 .gitignore（**寫在 repo 根目錄**才有效）
cat >> .gitignore <<'EOF'
*.bak.*
*.lock
*.clean.*
*~
EOF
```

**Step 3**: 用 regex 掃描即將 add 的內容、遮罩真實 secrets
```bash
# Python regex 過濾（建議用 python、bash regex 太雷）
python3 -c "
import re, glob
patterns = [
    (r'sk-[a-zA-Z0-9]{20,}', 'sk-***REDACTED***'),
    (r'sk-ant-[a-zA-Z0-9-]{20,}', 'sk-ant-***REDACTED***'),
    (r'ghp_[a-zA-Z0-9]{20,}', 'ghp_***REDACTED***'),
    (r'(MINIMAX|OPENAI|ANTHROPIC|DEEPSEEK)_API_KEY=*** r'\\1_API_KEY=***RED...),
    (r'(api[_-]?key:).+', r'\\1 ***REDACTED***'),
    (r'(apiKey:).+', r'\\1 ***REDACTED***'),
]
for f in glob.glob('*/*') + glob.glob('*'):
    if not os.path.isfile(f): continue
    with open(f) as fh: content = fh.read()
    new = content
    for pat, repl in patterns:
        new = re.sub(pat, repl, new)
    if new != content:
        with open(f, 'w') as fh: fh.write(new)
        print(f'遮罩 {f}')
"
```

**Step 4**: 重新 stage + commit
```bash
git add -A
# 確認 .bak/.lock 沒被加進來
git diff --cached --name-only | grep -E '\.bak\.|\.lock' | head -3
# 應該空
git commit -m "fix: 過濾 .bak/.lock + 遮罩 secrets"
```

**Step 5**: push 前**用 GitHub 真實 pattern 再掃一次**（不要相信自己的 regex）
```bash
# 嚴格 regex（GitHub secret scanning 真實用這些）
git show HEAD | grep -E '(sk-[a-zA-Z0-9]{20,}|sk-ant-[a-zA-Z0-9-]{20,}|ghp_[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{35})' | head -5
# 應該空
```

**Step 6**: 真的 push
```bash
git push origin main
# 如果再擋 → 看完整 GH013 訊息、用 `gh secret scan` 找具體位置
```

**預防**:
- **`.gitignore` 一定要寫在 repo 根目錄**（子目錄 .gitignore 對 `git add` 從根加檔無效）
- 任何 `*.bak`、`*.lock` 模式要包含帶 timestamp 的變體（`*.bak.*`）
- 推送前**永遠跑一次 Step 5 的嚴格 regex**（不要相信自己的遮罩邏輯）
- 已知危險 pattern 至少要擋: `sk-`、`sk-ant-`、`ghp_`/`gho_`/`ghs_`/`ghr_`/`ghu_`、`AIza`、`xai-`
- 如果曾經推過含 secrets 的 commit 進 history、即使後來修正也要用 `git-filter-repo` 改寫歷史

**If→Then**:
- **If** 看到 `GH013: Push cannot contain secrets` **Then** 走 Step 1-6 完整修復、**不要**改用 private repo 逃避（private repo 仍可能擋、未來改 public 又炸）
- **If** commit 內含 `MEMORY.md.bak.*` **Then** 這次踩過、`*.bak` 不夠、要寫 `*.bak.*`
- **If** `.gitignore` 寫在子目錄（sparc/ 內、skill/ 內）**Then** 不會對根目錄的 `git add` 生效、要寫在 repo 根

**相關條目**: [[hermes-backup-design-pitfalls#Rule 9：備份檔不該被備份（備份悖論）]] + [[bash-defensive-patterns#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]]

---

### GH001 Large files > 100MB + filter-branch 從歷史移除的陷阱（2026-06-07 踩到）

**發現時間**: 2026-06-07

**觸發情境**: v4 備份腳本把 `~/.hermes/skills/.curator_backups/` 內的 119 MB tar.gz 同步進 staging、推 GitHub 觸發 GH001；用 `git filter-branch` 想從歷史移除、卻把整個 repo 搞壞

**症狀 1（GH001 觸發）**:
```
remote: error: File skills/.curator_backups/2026-06-06T03-54-08Z/skills.tar.gz is 119.44 MB; 
        this exceeds GitHub's file size limit of 100.00 MB
remote: error: GH001: Large files detected. You may want to try Git Large File Storage
```

**症狀 2（filter-branch 沒改 SHA）**:
- 跑 `git filter-branch --index-filter 'git rm -rf --cached --ignore-unmatch skills/.curator_backups/' -- --all`
- 沒看到「Rewrite 13/13」這種訊息 → 知道 SHA 沒改
- 結果：commit SHA 跟之前一樣、GitHub 還是擋
- 推測原因：filter-branch 只在 commit **內容真的改變**時才產生新 SHA、移除單一檔案如果 commit tree 還有大檔（因為歷史 pack 還在）就視為「沒改」

**症狀 3（rm pack 把 repo 搞壞、**最慘的踩雷**）**:
- 想「既然 filter-branch 沒用、那手動清 pack 吧」
- 跑 `rm -f .git/objects/pack/pack-*.pack .git/objects/pack/pack-*.idx`
- 然後 `git gc --aggressive --prune=now`
- → **`fatal: bad object HEAD`**
- → **`fatal: bad object origin/main`**
- → 整個 repo 壞掉、git log / git status / git push 全部失敗
- commit graph 在 .git/objects 內、pack 是 commit 物件的**唯一儲存位置**、刪掉就再也找不回來

**完整修復 SOP**（**先預防**、出事了再還原）:

**預防（v4 備份腳本必加）**:
```bash
# 1. rsync 排除大檔陷阱
rsync -au --delete \
  --exclude='.curator_backups/' \
  --exclude='.archive/' \
  --exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip' --exclude='*.7z' \
  "$HERMES_HOME/skills/" "$STAGING/skills/"

# 2. .gitignore 加這些規則
cat >> .gitignore <<'EOF'
# === 大檔陷阱（GitHub 100MB 上限） ===
.curator_backups/
*.tar.gz
*.tar
*.zip
*.7z
EOF
```

**真實觸發 GH001 時的處理（不要 filter-branch 也不要 rm pack）**:
```bash
# 1. 從 staging 工作目錄 + 索引移除（這個會成功）
git rm -rf --cached skills/.curator_backups/
rm -rf skills/.curator_backups/

# 2. 直接 git reset --hard 到「壞 commit 之前」的最後一個好 commit
git reset --hard <last_good_commit_sha>

# 3. 重新覆蓋本地改動（trial-and-error 等剛改的東西）
#    從 /tmp 備份還原

# 4. 重新 commit + push
git add -A
git commit -m "fix: 移除大檔陷阱"
git push origin main
```

**為什麼 reset --hard 比 filter-branch 好**:
- filter-branch 對「已經 add 過但還沒 push」的 commit **無效**（因為沒改 SHA、也沒人 fetch 過這些 commit）
- 真正的危險是：**已 push 過的歷史 commit 內有大檔**、這時才需要 filter-branch
- 但這條路徑要先安裝 `git-filter-repo`（更安全、官方推薦）或 `bfg`、filter-branch 已棄用
- 沒裝工具的話、**接受這次 push 失敗、用 reset --hard 砍掉新 commit 重來**

**真的需要 filter-branch 從歷史移除時**:
```bash
# 1. 先安裝 git-filter-repo（filter-branch 已棄用）
pip install git-filter-repo
# 或 brew install git-filter-repo / apt install git-filter-repo

# 2. 用 filter-repo 改寫歷史（比 filter-branch 安全、快、有驗證）
git filter-repo --path skills/.curator_backups/ --invert-paths

# 3. 重新 pack + push
git remote add origin git@github.com:USER/REPO.git
git push origin main --force-with-lease
```

**If repo 已經被我搞壞（rm pack 那一類）、只能還原**:
```bash
# 方法 1: 從 GitHub 重新 clone（最簡單、會丟本地未 push 的 commit）
cd ..
rm -rf broken-staging
git clone https://github.com/USER/REPO.git fresh-staging
# 再把本地的 trial-and-error 等改動從 /tmp 備份覆蓋回去

# 方法 2: 從 reflog 救（reflog 還在的話）
cd broken-staging
git reflog | head -20          # 找最後一個好 commit
git reset --hard <sha>         # 救回

# 方法 3: 放棄、重新 init
rm -rf .git
git init
git remote add origin ...
git pull
```

**預防**:
- **絕對不要 `rm -f .git/objects/pack/*`** — 這是 commit 物件的家、刪掉就死
- 看到 GH001 **不要**先 filter-branch、先 `git rm --cached` + `reset --hard` 重來
- filter-branch / filter-repo 是**已 push 過**的歷史才需要、不是本地新 commit
- 寫 `git push` 之前**永遠**先看 GitHub 倉庫大小（`gh api repos/.../... --jq .size`）+ `git ls-files | xargs -I{} wc -c {} | sort -n | tail -20` 找大檔

**If→Then**:
- **If** 看到 `GH001: Large files detected` **Then** 先 `git rm --cached` + `git reset --hard <last_good>` 重來、**不要**直接 filter-branch
- **If** 看到 `.git/objects/pack/` 想手動清 **Then** 用 `git gc --prune=now --aggressive` 自動清、**絕對不要** `rm -f pack/*`
- **If** 看到 `fatal: bad object HEAD` **Then** repo 已壞、`rm -rf staging` + 重新 clone 是最快路徑
- **If** 還是想用 filter-branch 改已 push 過的歷史 **Then** 裝 `git-filter-repo`、**不要**用 `git filter-branch`（官方棄用、行為飄移）

**相關條目**: [[hermes-backup-design-pitfalls#Rule 9：備份檔不該被備份（備份悖論）]] + [[bash-defensive-patterns#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]]


---

### `git reflog` 看不到 force push 砍掉的早期 commit、本地 reset --hard 後更看不到(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 想從 raphael-status-site 本地 git reflog 找回 css 還在的早期 commit(96f0055 之前)
**症狀**:
- 跑 `git reflog` 只看到最近 5-6 條 HEAD 移動:`commit: v2` / `reset: moving to origin/main` / `pull --rebase` / `reset: moving to HEAD~1` 等
- **完全看不到 96f0055 之前 css 還在的版本**
- 想用 `git reset --hard 96f0055` 撈舊 css 失敗 — 因為本地根本沒有那個 commit

**根因**:
- `git reflog` 是**本地 HEAD 的 ref log**,只追蹤本地操作
- 某次 force push 把遠端 history 砍掉後:
  - 遠端:96f0055 之前的 commit 不見了
  - 本地:本來有那些 commit(因為本地還沒 pull),但**經過 reset --hard origin/main + pull --rebase 後**,本地 reflog 也被覆蓋
  - `git reset --hard` 會把 HEAD 移到新位置,reflog 會記錄「移動」,但**移到的地方是「現在的 origin/main」**,而不是「之前的 force push 砍掉的」那個 commit
- 真要找舊 commit 要看 **GitHub 網頁的 reflog** 或其他 clone

**修法**:
1. **真要找舊 commit**:
   - 看 GitHub 網頁 → repo → Insights → Network 或 commits
   - 看 `git fsck --lost-found` 找 dangling commit(本地還在,但沒被任何 ref 指到)
   - 看 `git stash list`
   - 從其他 clone(別的開發者、Tailscale sync 別處、備份)

2. **如果只有要撈舊版特定檔**:
   - 從 GitHub raw URL 撈:`curl raw.githubusercontent.com/<owner>/<repo>/<old-commit-sha>/<path>`
   - 這比救回 commit 物件快很多

3. **預防**:
   - 重要 commit 打 tag:`git tag v1.0-css-ok 96f0055`(tag 不會被 force push 砍掉 — 預設 push tag 不會被 force push 影響)
   - 用 GitHub Releases 而非 git tag 備份
   - 多個 clone 散在不同機器

**If** → **Then** 規則:
- **If** `git reflog` 找不到早期 commit **Then** 看 GitHub 網頁 reflog 或其他 clone
- **If** 本地 `git reset --hard` 多次了 **Then** `git fsck --no-reflogs` 找 dangling commit
- **If** 只是要撈舊版檔案(不是 commit) **Then** 用 `curl raw.githubusercontent.com/...` 比救回 commit 快
- **If** 預防未來 force push 砍重要 commit **Then** 重要節點打 git tag
- **If** force push 真的把重要 commit 砍了 **Then** `git reflog --all` 跨所有 ref 看、有可能救回

**已驗證**:
- 2026-06-07 `git reflog` 看不到 css 還在的早期 commit
- 改用 `curl https://raw.githubusercontent.com/hoonsoropenclaw/raphael-status-site/96f0055/css/styles.css` 撈回 14.6KB css
- 不試圖救回 commit 物件、直接撈檔案就好(快 10 倍以上)

---

### sync_evaluations.py grep pattern 為 `***` 是字面字元而非 wildcard（2026-06-08）
**症狀**: `eval-sync` cron job 失敗，錯誤 `ERROR: AGENT_API_KEY not found in hermes-portal/.env.local`。實際 `.env.local` 有 `AGENT_API_KEY=***` (masked in output, real value=0770415)。
**根因**: script 第 32 行 `grep "^AGENT_API_KEY=***"` — `***` 在 grep pattern 中是**三個星號字面字元**，不是 wildcard。grep 找不到 `AGENT_API_KEY=***` 這個 literal string，所以 returncode != 0，`get_api_key()` 返回 None。
**解法**: 替換整個 `subprocess.run(["grep", ...])` 為直接讀檔案迴圈：
```python
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("AGENT_API_KEY=") or line.startswith("export AGENT_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
```
**預防**: 
- `grep` pattern 用 `***` 作為「任意長度任意字元」是**錯誤**（`*` 是 quantifier，`.*` 才等於 wildcard）
- subprocess + grep 處理簡單文字搜尋過度複雜，直接讀檔更好除錯
- 任何 job 的 skills 陣列不能放 MCP 工具（會 skip 不阻斷），但 skill 的**外部依賴**（Python script 讀 .env）要確保路徑正確
**If→Then**: **If** Python script 用 `subprocess.run(["grep", pattern, path])` 失敗 **Then** 改用 `with open(path) as f: for line in f:` 直接讀檔遍歷
**相關條目**: [[bash-defensive-patterns#cron 部署腳本 git push rejection 自我修復]]
