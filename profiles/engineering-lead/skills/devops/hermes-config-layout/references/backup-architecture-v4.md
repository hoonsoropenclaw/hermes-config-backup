# Hermes 備份架構 v4：雙雲端分層（2026-06-07 啟動）

> **TL;DR**：GitHub 管文字/小檔（Tier 1）、Drive 加密管 secrets（Tier 2）、本地鏡像管即時還原（Tier 3，選配）。v3 那種 Drive 1 萬+ 小檔 → 必爆 API 配額（840K/分鐘/專案）→ 不要走那條路。

## 為什麼 v1/v2/v3 都不夠

| 版本 | 做法 | 死亡原因 |
|------|------|----------|
| v1 (tar.gz) | 整包加密上 Drive | 異機還原要下整包 694 MB（58 分鐘）|
| v2 | v1 改名 | 同上 |
| v3 (rclone sync 目錄) | 整個 ~/.hermes/ sync 上 Drive | 13,611 個小檔 → 50000+ API 單位 → 幾分鐘內秒殺 840K 配額 → sync 卡 63-68% 然後 throttle（真實事件，見 trial-and-error skill Rule 10）|

## v4 設計：雙雲端分工

| Tier | 雲端 | 備什麼 | 為什麼這層 | 異機還原時間 |
|------|------|--------|------------|-------------|
| **Tier 1** | **GitHub** `hermes-config-backup` | skills / agents / memories / scripts / docs / config.yaml | 文字版控最優、git protocol 無 Drive 配額問題、永久歷史 | 5 分鐘 |
| **Tier 2** | **Google Drive**（crypt 加密）| secrets bundle（.env、auth.json、auth.lock）| Drive 配額寬容（1 個大檔）、加密安全 | 額外 2 分鐘 |
| **Tier 3** | **本地 Y 槽**（選配）| 即時鏡像 | 最快還原、零網路 | 0 分鐘 |

## 關鍵決定：sparc-methodology 怎麼處理

**陷阱**：寫 v4 時第一個假設是「把 sparc 從 staging 拆成自己的 GitHub repo」。**結果發現 sparc 本來就是 `ruvnet/claude-flow` upstream 的 git clone**（HEAD = 844f68d、落後 upstream 2 個 commit、origin 指向 `https://github.com/ruvnet/claude-flow.git`）。

**正確決定**：用 **snapshot 模式**進 staging，不用 submodule。

| 比較 | snapshot（採用）| submodule |
|------|------------------|-----------|
| 還原時網路需求 | `git clone` 一次 | 還要多步 `git submodule update` |
| 上游 API 變動風險 | 無（凍結 844f68d）| 隨時被上游改壞 |
| repo 大小 | 78 MB（sparc 內含）| ~5 MB（不內含）|
| 更新方式 | 手動 `cd ~/.hermes/skills/sparc-methodology && git pull` | `git submodule update --remote` |
| 適合情境 | **備份**（凍結歷史）| **追蹤開發**（跟最新）|

**If** 要判斷 ~/.hermes/ 內某個 skills/ 子資料夾是本地維護還是 upstream clone
**Then** 跑 `cd <path> && git log --oneline -3 && git remote -v`
**Then** 有 `origin` 指向 GitHub = upstream clone、不用自建 repo

**staging 內要排除的東西**（已寫進 staging 根 `.gitignore`）：
- `agentdb.rvf` / `agentdb.rvf.lock`（sparc 內的 vector store）
- `.git/`（避免把整個 .git 歷史塞進 staging，會破 100 MB 限制）
- `venv/`、`__pycache__/`、`*.pyc`
- `state.db`、`*.db-wal`（rebuild 即可）
- `.env`、`auth.json`、`*.gpg`、secrets 目錄（會另外加密上 Drive）
- `*.bak.*`、`*.lock`、`*.clean.*`（備份悖論：備份檔不該被備份）
- `backups/`、`hermes-backup-staging/`（自我引用）

## GH013 防雷：什麼會被擋

GitHub 對 public repo 的 **push protection** 會掃描 commit 內的真實 API key/PAT/secret pattern。如果 commit 內有：
- `sk-[a-zA-Z0-9]{20,}`（OpenAI）
- `sk-ant-[a-zA-Z0-9-]{20,}`（Anthropic）
- `ghp_[a-zA-Z0-9]{20,}`（GitHub PAT）
- `gho_/ghs_/ghr_/ghu_[a-zA-Z0-9]{20,}`（其他 GitHub token 類型）
- `AIza[0-9A-Za-z_-]{35}`（Google）
- `xai-[a-zA-Z0-9]{20,}`（xAI）

→ push 會被擋下（`remote: error: GH013`）、**整個 push 不會發生**。

**寫 v4-P2 補 staging 完整備份時真的觸發了** — 因為把 `memories/MEMORY.md.bak.*` 一堆備份檔 commit 進去、裡面包了過去的 API key literals。**修法**：
1. `git reset --soft HEAD~1`（保留改動在工作目錄）
2. 刪掉 `.bak.*` / `.lock` / `.clean.*` 實體檔
3. 加強 `.gitignore`
4. 用 regex `sed` 遮罩可疑 pattern（`sk-XXX` → `sk-***REDACTED***`）
5. 重新 commit + push

**未來預防**（任何備份/同步腳本）：
- sync 之前先跑一次 `grep -E 'sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{35}' <files>` 掃描
- `.bak.*`、`.lock`、`.clean.*` 永遠加進 `.gitignore`（備份悖論）
- `MEMORY.md` / `USER.md` 等會被 sync 的檔**不放具體 token 值**、用 `***` 取代（這個 USER 偏好已記在 `alt-token-secrets-layout` skill）

## 3 個核心腳本（已實作在 `~/.hermes/scripts/`）

### hermes-backup-v4.sh
統一備份入口。Modes：
- 預設（不帶參數）= 跑 Tier 1 + Tier 2 加密（不上傳 Drive）
- `--tier1` = 只推 GitHub（增量、每天 cron 用）
- `--tier2` = 只跑 Drive secrets 加密
- `--upload-tier2` = 加密完推到 Drive（Tier 2 完整流程）
- `--dry-run` = 看會做什麼但不做

### hermes-restore-v4.sh
統一還原入口。Modes：
- `tier1` = 從 GitHub clone + rsync 還原（5 分鐘）
- `tier2` = 從 Drive 拉加密檔 + GPG 解密（額外 2 分鐘）
- `tier3` = 本地 Y 槽鏡像（placeholder、需手動設定來源路徑）
- `all` = 跑 tier1 → tier3 → tier2
- `--target DIR` = 還原到指定目錄（**不覆蓋當前 $HERMES_HOME**、用於異機測試）

### hermes-secrets-encrypt.sh
Tier 2 加密腳本（被 backup-v4 呼叫）。Modes：
- 預設 = 加密但不上傳
- `--verify` = 加密後用 decrypt 驗證
- `--upload-drive` = 推 Drive
- `--rotate` = 重新生成 passphrase

## 異機還原 SOP（5 分鐘可跑 hermes）

```bash
# Step 1: 安裝 hermes-agent 本體（不算備份、隨時可裝）
pip install hermes-agent

# Step 2: Tier 1 還原（從 GitHub）
git clone https://github.com/hoonsoropenclaw/hermes-config-backup.git ~/.hermes
bash ~/.hermes/scripts/hermes-restore-v4.sh tier1 --target ~/.hermes

# Step 3: Tier 2 補 secrets（需要 Drive access + passphrase）
# 注意：passphrase 必須**手動從備份位置複製**過來（這是設計、不是 bug）
mkdir -p ~/Documents/hermes-keys
cp /path/to/backup/.hermes_backup_passphrase ~/Documents/hermes-keys/
chmod 600 ~/Documents/hermes-keys/.hermes_backup_passphrase
bash ~/.hermes/scripts/hermes-restore-v4.sh tier2
```

## 還原驗證 SOP

```bash
# 看 secrets 權限
ls -la ~/.hermes/.env ~/.hermes/auth.json
# 預期：-rw------- 1 user user

# diff 主機 vs 還原（如果有第二份還原目錄可比較）
diff -r /home/hoonsoropenclaw/.hermes/ /tmp/hermes-restore-test/

# 抽樣驗證 sparc（最大的 skill）
find ~/.hermes/skills/sparc-methodology/ -type f | wc -l
# 預期 4674
```

## 排除清單（v4 不備什麼 vs 為什麼）

| 不備 | 為什麼 | 怎麼重建 |
|------|--------|----------|
| `hermes-agent/` (1.1 GB) | Python venv 巨大、可 `pip install` | `pip install hermes-agent` |
| `venv/`、`__pycache__/` | Python bytecode、rebuild 即可 | 自動生成 |
| `state.db` (179 MB) | 對話資料庫、rebuild 即可 | 對話歷史從 session log 重建 |
| `kanban.db` | 看板資料、不重要 | 重建 |
| `sessions/` (8.4 MB) | 對話 session、可從 git 推導 | 看 session DB |
| `logs/` (4.4 MB) | 系統 log、暫時性 | logrotate |
| `lsp/` (27 MB) | LSP server cache | 重啟 hermes 重生 |
| `bin/` (11.5 MB) | 二進位執行檔 | 從原始碼重編 |
| `browser_screenshots/` | 截圖、cache | 自動清 |
| `image_cache/`、`audio_cache/` | 媒體 cache | 自動清 |
| `backups/` (671 MB) | 舊版備份 | 從 Drive 拉 |
| `hermes-backup-staging/` (39 MB) | 就是本 repo | 自己是 source of truth |
| `node_modules/` | Node.js 模組 | `npm install` |
| `.env`、`auth.json` | **secrets**、另外加密上 Drive | v4 Tier 2 流程 |
| `*.gpg` | 加密檔（已加密的東西不該再被加密）| 從原檔加密重生 |
| `agentdb.rvf` (sparc 內) | binary vector store | 從記憶體 rebuild |

## Drive 現況（2026-06-07 v4 啟動時）

- ✅ v1 完整備份（`hermes_backup_20260606_211411_full.tar.gz`、694 MB）**保留**作 fallback
- ✅ v3 半成品（v3/、v3/current/、v3/manifests/、v3/snapshots/）**已清**
- ⏳ Tier 2 加密檔會在 `crypt_hermes:hermes-backup/secrets/`（**尚未推**、等真實 run `--upload-tier2`）

## 相關 skill 引用

- **`alt-token-secrets-layout`** — GPG 加密 SOP、雙目錄分離佈局、GH013 防雷
- **`trial-and-error` skill** — Rule 10（Drive API 配額 840K/分鐘）、Rule 11（v3 限制催生 v4 雙雲端）
- **`hermes-config-layout`**（本 skill）— `~/.hermes/` 整體結構、staging/ 目錄佈局

## 排程建議（未實作、留 cron 設定）

```cron
# 每天 02:00 跑 Tier 1（增量、輕量）
0 2 * * *  /home/hoonsoropenclaw/.hermes/scripts/hermes-backup-v4.sh --tier1 >> /var/log/hermes-backup.log 2>&1

# 每週日 03:00 跑 Tier 2 完整（加密 + 推 Drive）
0 3 * * 0  /home/hoonsoropenclaw/.hermes/scripts/hermes-backup-v4.sh --upload-tier2 >> /var/log/hermes-backup.log 2>&1
```

---

## v4-P7 後續 bug 修復：skills 同步缺失 + 4 個真實事件（2026-06-07）

> 寫完 v4 架構、跑完第一次端到端驗證後、用戶一句「**skill是同步到github不是嗎？**」暴露了 v4 備份腳本的根本性 bug——**skills/ 根本沒在 sync 範圍內**。trial-and-error skill 的新條目完全沒進到 GitHub。修這個 bug 的過程又踩到另外 4 個坑、一一記下。

### P0 教訓：備份腳本要「顯式列舉」要 sync 的目錄、不能用「想到什麼加什麼」

**症狀**（用戶糾正原話）：「skill是同步到github不是嗎？」

**v4-P7 之前的 hermes-backup-v4.sh 漏掉的目錄**：
- `skills/`（最大的目錄、含 trial-and-error 等所有 skill）→ 用戶糾正才發現
- 任何「腳本作者當下沒想到」的目錄都會被遺漏

**正確做法**（這次補完）：
```bash
# 顯式列舉要 sync 的目錄清單（在腳本開頭、方便 review）
SYNC_DIRS=(
  "config.yaml"
  "auth.json.template"
  "agents/"
  "memories/"
  "scripts/"
  "docs/"
  "skills/"              # ★ 重要、最大、最容易漏
  "cron/"
)
for item in "${SYNC_DIRS[@]}"; do
  # 各自帶對應的 --exclude
done
```

**If** 設計/修改備份腳本 **Then** 寫一個「要 sync 哪些目錄」的清單在腳本開頭、用戶 review 一眼就看到**哪些被包含、哪些被排除**
**Then 不要**「想到一個加一個」式擴充 rsync 步驟（會永遠漏）
**Then** 每次加新目錄到 ~/.hermes/ 時、同步更新這個清單

### 修完 v4-P7 後又踩到的 4 個真實事件

#### 事件 1：`.curator_backups/` 含 119 MB tar.gz 觸發 GH001

**症狀**：
```
remote: error: GH001: Large files detected.
remote: error: File skills/.curator_backups/2026-06-06T03-54-08Z/skills.tar.gz is 119.44 MB;
        this exceeds GitHub's file size limit of 100.00 MB
```

**根因**：
- hermes 內建 `~/.hermes/skills/.curator_backups/` 是 curator 功能自動備份 skill 用的目錄
- 內含 `skills.tar.gz`（全量 skill 快照）+ `cron-jobs.json` + `manifest.json`
- 119.44 MB > GitHub public repo 100 MB 限制
- **`.gitignore` 沒排除**、rsync 也沒排除

**修法**：
```bash
# staging 根 .gitignore 加
.curator_backups/
*.tar.gz
*.tar
*.zip
*.7z

# hermes-backup-v4.sh rsync --exclude 也加
--exclude='.curator_backups/'
--exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip'
```

**預防規則**：
- **任何目錄含 .tar / .zip / .7z 都要排除**（檔案太大、且備份檔不該被備份）
- 已知 hermes 自動產的「自我備份」目錄：`.curator_backups/`、`.archive/`、`.trash/`

#### 事件 2：`metacognitive-learner/references/` 含真實 `vcp_` token 觸發 GH013

**症狀**：
```
remote: —— Vercel Personal Access Token ——————————————————————
remote:   - commit: c016387a90...
remote:     path: skills/autonomous-ai-agents/metacognitive-learner/references/secrets-in-sync.md:18
```

**根因**：
- `alt-token-secrets-layout` skill 內 references/cron-secret-leak-scrub.md 是 2026-06-05 md-files-daily-sync 事件的修復 SOP
- 教學文件**用真實 `vcp_***REDACTED***` 當範例**（教「怎麼 redact」）
- 這個 skill 透過 v4-P7 完整 skills 同步第一次進到 staging
- push 觸發 GH013

**修法**：
1. 從 staging 工作目錄刪除該 references/ 目錄
2. **加進 staging .gitignore**：`skills/autonomous-ai-agents/metacognitive-learner/references/`
3. `git rm --cached -r` 從索引移除
4. 必要時 `git filter-branch` 從整個歷史移除（但只對「未 push 過的 commit」有效，見事件 4）

**這個 token 已經公開洩漏**——**請去 Vercel 後台 revoke 重新申請**。這是 2026-06-05 md-files-daily-sync 事件後第二次踩同一個 token。

**預防規則**：
- **任何 reference 教學文件、示範用的 token 必須用 `***` 取代**（不能留真實 literal）
- 已寫進 `alt-token-secrets-layout` skill 的「預防」段：MEMORY.md / USER.md 等被 sync 的檔不放具體值
- 同步前必須掃一次 GitHub 完整 secret pattern：`sk-`、`sk-ant-`、`ghp_`/`gho_`/`ghs_`/`ghr_`/`ghu_`、`AIza`、`xai-`、**`vcp_`**

#### 事件 3：push 失敗訊息被 grep 吞掉、`exit code: 0` 假成功

**症狀**：
- hermes-backup-v4.sh 顯示「✓ GitHub push 成功」
- 但 GitHub 上其實沒收到（origin 還是舊 commit）
- 用戶沒察覺、trial-and-error 條目實際沒進 GitHub

**原版 bug**（v4-P7 之前）：
```bash
if git push origin main 2>&1 | grep -qE "(GH013|error:)"; then
  err "push 失敗..."
  return 1
fi
ok "GitHub push 成功"  # ← 即使 push 失敗、也會跑到這
```

**根因**：
- `set -e` 在 `if` 條件內**不會觸發**（bash 設計）
- `git push ... | grep` 的 exit code 是 grep 的（0 = 有 match、1 = 沒 match）、不是 push 的
- 即使 push 失敗、grep 沒 match、判斷為「成功」

**修法**（v4-P7 已修）：
```bash
local push_output
push_output=$(git push origin main 2>&1) || true   # ← 關鍵：|| true 確保後面 echo 不被中斷
echo "$push_output" | tail -10

# 分別檢查 GH013 / GH001 / 其他錯誤
if echo "$push_output" | grep -qE "GH013.*secrets"; then ...; return 1; fi
if echo "$push_output" | grep -qE "GH001.*Large files"; then ...; return 1; fi
if echo "$push_output" | grep -qE "(\[remote rejected\]|error:|fatal:)"; then ...; return 1; fi

ok "GitHub push 成功"
```

**If** 寫任何 `command 2>&1 | grep` 模式做錯誤檢查 **Then** 改成 `output=$(command 2>&1) || true; echo "$output" | grep`
**Then 不要** 用 pipe 進 `if`（exit code 會是 grep 的、不是原命令的）
**Then** push / curl / docker push 等外部命令**永遠存完整 output 到變數**、不要只 grep

#### 事件 4：`git filter-branch` 改寫後 SHA 不變、commit 內的大檔還在

**症狀**：
- 跑 `git filter-branch --index-filter 'git rm -rf --cached --ignore-unmatch <path>' --prune-empty --all`
- 看到 "Ref 'refs/heads/main' was rewritten" 以為成功
- 但 `git log --oneline -3` 顯示 SHA **完全沒變**
- 再 push 還是被擋（commit tree 物件還引用舊的 blob）

**根因**：
- `filter-branch` 改寫 commit tree、但 blob 物件本身（`.git/objects/<hash>`）**不會被刪除**
- 如果 commit **整個 tree** 沒變（只是刪了某個檔案）、filter-branch 會用**相同 tree 物件**、所以 SHA 不變
- 即使 SHA 變了、push 還是會擋、因為**已經被推過的 commit** GitHub 仍記得它含的 blob hash

**修法**（從已 push 過的歷史移除大檔、需要 3 步）：
```bash
# 1. filter-branch 改寫 tree
git filter-branch -f --index-filter \
  'git rm -rf --cached --ignore-unmatch <path>' \
  --prune-empty --tag-name-filter cat -- --all

# 2. 確認 SHA 真的變了
git log --oneline -3    # 應該跟 origin/main 不同 SHA

# 3. 如果 SHA 沒變、那這個 commit 必須用 git reset 砍掉重建
git reset --hard <known_clean_commit_sha>

# 4. pack + gc 清掉 dangling blob（**用 git 指令、不要手刪 .git/objects/**）
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. force push
git push --force-with-lease origin main
```

**但**：`--force-with-lease` 在 push protection 觸發時仍會被擋（GitHub 仍記得舊 commit 含 secrets）。**唯一完全乾淨的修法是聯絡 GitHub Support unblock** 或接受「公開 repo 永遠留有歷史」這個事實。

**If** 看到 filter-branch 跑完但 SHA 沒變 **Then** 別指望它清乾淨、直接 `git reset --hard <known_clean_commit_sha>` 砍掉重建
**Then 不要** 手動 `rm -f .git/objects/pack/pack-*.pack`——會把整個 staging 搞壞（HEAD 報 "bad object"）、要從 GitHub 重新 clone 救回

**災難恢復 SOP**（手賤刪了 pack 檔的後果）：
```bash
rm -rf ~/.hermes/hermes-backup-staging
git clone https://github.com/hoonsoropenclaw/hermes-config-backup.git \
  ~/.hermes/hermes-backup-staging
# 然後從 /tmp 備份覆蓋 trial-and-error 改動
```

---

## 已知 GH013 危險清單（v4 啟動前就洩漏的、需 unblock 或 revoke）

| 檔案 / 位置 | 含什麼 secret | 狀態 | 處理 |
|------------|--------------|------|------|
| `skills/autonomous-ai-agents/metacognitive-learner/references/cron-secret-leak-case.md:10` | `vcp_***REDACTED***` | 已被 GH013 擋下 2 次（2026-06-05、2026-06-07）| **去 Vercel revoke**、加進 .gitignore 永久排除整個 references/ |
| `skills/autonomous-ai-agents/metacognitive-learner/references/secrets-in-sync.md:18` | 同上 vcp_ token | 同上 | 同上 |
| Drive `hermes_backup_20260606_211411_full.tar.gz` | 內含 .env、auth.json（**加密中**、不直接可見、但 Drive 是私人、可控）| Drive crypt 加密 | 保留即可（私人不需 revoke）|

**If** 看到 v4 啟動後的 commit 仍觸發 GH013 提到 metacognitive-learner/references **Then** 表示 .gitignore 沒生效、檢查 staging 根 `.gitignore` 是否有 `skills/autonomous-ai-agents/metacognitive-learner/references/` 這行
**Then** 確認 staging 工作目錄內那個目錄**已刪除**（不是只在 git 索引移除）
**Then** 真實的清乾淨方式是 unblock 那個 secret（聯絡 GitHub Support）或接受歷史留有痕跡
