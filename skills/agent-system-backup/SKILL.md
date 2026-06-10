---
name: agent-system-backup
description: "赫米斯型 AI agent 的全狀態備份 SOP。涵蓋產兩個 tar.gz（public + full）的雙 sink 策略、本地保留 N 份、雲端加密上傳（rclone crypt）、公開 repo push、Drive 資料夾自描述、cron 排程、secret 掃描、in-house 還原 SOP。2026-06-06 赫米斯實際運行驗證通過。"
version: 1.0.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [backup, disaster-recovery, restore, rclone, github, google-drive, cron, hermes-agent]
    triggers: [backup, 備份, restore, 還原, disaster-recovery, 異機還原]
---

# Agent System Backup — 全狀態備份 class-level SOP

適用於任何「想把自己整套設定異機還原」的 agent 系統（不限 Hermes）。
**2026-06-06 赫米斯實戰驗證**：跑出兩個 tar.gz（公開版 244 KB、完整版 134 MB），本地 + Google Drive（rclone 加密）+ GitHub 公開 repo 三 sink，cron 排程每天 03:00，無 token 洩漏。

## 1. 為什麼要雙 tar.gz（公開版 + 完整版）

**核心分層原則**：

| 層 | 內容 | 進哪 |
|---|---|---|
| **公開版** (`*_public.tar.gz`) | 設定、記憶、skills、scripts、kanban.db、INSTALLED_MANIFEST、**不含敏感不含大型** | GitHub 公開 repo |
| **完整版** (`*_full.tar.gz`) | 公開版全部 + .env 真實檔 + GPG token + 源碼 + state.db + 衍生資料 | Google Drive（rclone crypt 加密） |

**為什麼不分開兩個 repo / 兩個 Drive 資料夾**？因為「異機還原時使用者只想要一個入口」。雙 tar.gz 讓 restore script 可以：
- 從 Drive 拉一份 = 拿到全部（含 .env）
- 從 GitHub 拉 = 拿公開版、缺的部分從 Drive 補

## 2. 完整版 INVENTORY（這次實際跑的內容）

```
hermes_backup_<ts>_full.tar.gz  (~134 MB)
├── config/                          # 公開版 + 額外
│   ├── hermes-config.yaml
│   ├── hermes-env-real              # 真實 .env（mode 600、31 個 key）—— 只有完整版有
│   ├── cron-jobs.json
│   └── env-template                 # 公開版的 key *** 化範本
├── memories/                        # 7 個核心 MD
├── skills/                          # 自建 6 個
├── scripts/                         # 含 restore_hermes.sh
├── data/kanban.db
├── docs/RESTORE.md                  # 完整版也帶一份（雙保險）
└── full_backups/                    # 額外這層（**只有完整版**）
    ├── INVENTORY.md                 # Drive 專屬清單，列出所有敏感/大型檔
    ├── state.db                     # 169 MB session store
    ├── hermes-agent/                # 1.1 GB 源碼（rsync 排除 venv/、.git/、__pycache__/）
    ├── sparc-methodology/           # 103 MB 外部 skill
    ├── alt_gh_tokens/               # GPG 加密的備用 PAT
    ├── secrets/                     # GPG 加密的 .env + auth.json + state.db（需 passphrase 解）
    ├── passphrase-recovery/         # v4.5 新增：GPG 加密的 passphrase（需 USER_KEY 解）
    ├── cache/、logs/、lsp/、bin/、sessions/   # 衍生資料
    └── models_dev_cache.json
```

**rsync 排除清單**（hermes-agent 源碼用 rsync 複製時）：

```
--exclude='venv/' --exclude='venv64/' --exclude='.git/' --exclude='__pycache__/'
--exclude='*.pyc' --exclude='node_modules/'
```

省 ~700 MB venv 大小。

## 3. 雙重 Secret 掃描 SOP

**位置 1：打包前**（在 staging 內 redact）

```bash
# 萬用 redact：所有 vcp_/ghp_/sk-/hms_/gho_/glpat- 開頭、長度 20+ 的字串
find "$STAGING" -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) -print0 | \
  xargs -0 perl -i -pe 's/(vcp_|ghp_|sk-|hms_|gho_|glpat-)[A-Za-z0-9_-]{20,}/[TOKEN_REDACTED]/g'
```

**位置 2：打包後**（從 tar.gz 抽出再 grep）

```bash
SECRET_REGEX='***=' tar -tzf "$PUBLIC_TARBALL" | xargs -I{} tar -xzOf "$PUBLIC_TARBALL" {} 2>/dev/null | \
  grep -E "$SECRET_REGEX" >/dev/null && abort
```

**位置 3：commit 前**（GitHub 版最後一次）

```bash
cd "$GITHUB_REPO_DIR"
grep -rE "$SECRET_REGEX" . --include="*.md" --include="*.yaml" --include="*.json" --include="*.py" --include="*.sh" | grep -v "INSTALLED_MANIFEST" && abort
```

**位置 4：Drive 上傳後檢查目錄結構**

```bash
# Drive 資料夾內會有 tar.gz（加密亂碼）、RESTORE.md、restore_hermes.sh
rclone lsf crypt_hermes:hermes_backup_<ts>_full/
# 預期看到 3 個檔案，不是 1 個
```

## 4. Drive 資料夾自描述模式（重要設計 pattern）

**每個 Drive 子資料夾內放獨立 RESTORE.md + restore_hermes.sh**：

```bash
RCLONE_TARGET="crypt_hermes:hermes_backup_${TIMESTAMP}_full/"
rclone copy "$FULL_TARBALL" "$RCLONE_TARGET" --config rclone.conf
rclone copy "$HERMES_HOME/docs/RESTORE.md" "$RCLONE_TARGET" --config rclone.conf
rclone copy "$SCRIPT_DIR/restore_hermes.sh" "${RCLONE_TARGET}restore_hermes.sh" --config rclone.conf
```

**為什麼這樣設計**：使用者打開 Drive 資料夾，**不需要先解 tar 就能看到還原 SOP**。也意味著 restore script 不能依賴 Drive 內有 tar.gz（要能獨立運作）。

## 5. cron 排程（no-agent script 模式）

**手動加 jobs.json**（避開 `hermes cron edit --script` 的 bug，這是已知問題）：

```python
# jobs.json schema
{
  "id": "<uuid>",
  "name": "<system>-daily-backup",
  "prompt": "# 說明 script 做什麼（給 log 看）",
  "script": "backup_<system>.sh",  # 純檔名
  "no_agent": True,
  "schedule": {"kind": "cron", "expr": "0 3 * * *", "display": "0 3 * * *"},
  "enabled": True,
  "deliver": "local",
  ...
}
```

**為什麼凌晨 3 點**：
- 避開其他 cron（metacognitive-learner 是 120m 週期）
- 美西時間離峰、上傳雲端速度較快
- **不是 0 點**：避免跨日時的「本機是昨天、雲端是今天」混淆

## 6. restore_hermes.sh 三路徑設計

```bash
# 路徑 A：本地 tar.gz（最快）
bash restore_hermes.sh /path/to/local.tar.gz

# 路徑 B：rclone crypt_hermes（推薦，自動找最新）
bash restore_hermes.sh   # 自動 ls crypt_hermes: 找 hermes_backup_*

# 路徑 C：GitHub clone（最慢但最方便）
git clone https://github.com/<user>/<repo>
bash <repo>/scripts/restore_hermes.sh
```

**警告語必含**：

> ⚠️ 異機還原前，務必先 `pkill -f hermes-gateway` 關掉任何已運行的 gateway。
> Telegram session 一次只能掛一台機器。兩台同時開會搶同一個 bot。

## 7. 異機還原時 Telegram / Gateway 影響（重要 FAQ）

**Q：異機還原會影響 Telegram session 嗎？**
A：分三情境：
- **新主機第一次架設**：不影響舊主機。restore 完後啟動 gateway 會重新跑一次 OAuth、生成新 session 檔。
- **暫時取代舊主機**（先關舊再開新）：會有幾秒到幾分鐘斷線。session 從 `gateway_state.json` 還原、不需重跑 OAuth。
- **兩台同時開 gateway**：**禁止**。Telegram bot 會搶同一個 chat_id 訊息、使用者會看到漏訊或重複回覆。

## 8. 已驗證成果（2026-06-06 赫米斯實跑）

| 指標 | 數值 |
|---|---|
| 公開版 tar.gz | 244 KB |
| 完整版 tar.gz | 134 MB |
| 完整版檔案數 | 8,588 個 |
| .env 真實 key 數 | 31 個（25,594 bytes） |
| 雲端上傳速度 | ~1.3 MB/s（Google Drive） |
| 總耗時 | ~3 分鐘（含上傳） |
| Secret 掃描結果 | 公開版 0 hit、完整版僅有受保護的 .env（mode 600） |
| GitHub commit | `5552b98` push 成功 |

## 9. 跟其他 skill 的關係

- **trial-and-error → by-category → hermes-config-tuning**：之前的 model routing 失敗案例。**不重複**，本 skill 只 cover 備份這塊 class。
- **hermes-tier-router**：備份 cron 會把這個 skill 也備份。
- **alt-token-secrets-layout**：GPG 加密 token 的 SOP 在那邊，備份時只備「加密檔」不備「明文 passphrase」以外的明文 token。

## 10. 已知陷阱

### 10.1 腳本歧義（2026-06-10 踩坑，新加）

N100 上**同時存在兩份備份腳本**：

| 腳本 | 路徑 | 狀態 | 用途 |
|---|---|---|---|
| **`hermes-backup-v4.sh`** | `~/.hermes/scripts/hermes-backup-v4.sh` | ✅ **當前唯一正確** | v4 流程：Tier 1 GitHub + Tier 2 Drive encrypted + 3 位置 secret 掃描 |
| **`backup-all.sh`** | `~/.local/bin/backup-all.sh` | ❌ **2025-12 環境的舊 v3**，**不要用** | 會把備份寫到 `/media/hoonsoropenclaw/n100/backup-2025-12/` — **這條路徑在當前 N100 不存在**(`/media/` 是空的) |

**If** 使用者說「跑備份」「備份 hermes」「異機還原準備」
**Then** **永遠用 `~/.hermes/scripts/hermes-backup-v4.sh`**，**不要**用 `~/.local/bin/backup-all.sh`
**Then** 跑前先 `head -50 hermes-backup-v4.sh` 確認 `--help` 介面
**Then** `ls ~/.hermes/backups/` 看現有備份時間戳、預期格式 `hermes_backup_<YYYYMMDD_HHMMSS>_{public,full}.tar.gz`

### 10.2 GPG 加密方式：自動讀 passphrase 檔（2026-06-07 設計、2026-06-10 釐清）

- `hermes-secrets-encrypt.sh` 用 `gpg --batch --yes --passphrase-file "$PASSPHRASE_FILE"` 從固定路徑讀,**完全不需要互動 prompt**
- **不用 PTY**、**不用 process write 餵入**、**不用人工記密碼**
- passphrase 自動產生 64 字元、存在 `~/Documents/hermes-keys/.hermes_backup_passphrase` (mode 600)
- **如果有人問「GPG 密碼是什麼」** → 不要在對話打密碼、回他「在 `~/Documents/hermes-keys/.hermes_backup_passphrase`、64 字元自動產生的」
- **驗證命令**：`cat ~/Documents/hermes-keys/.hermes_backup_passphrase | wc -c` 應回 65（含換行）
- **如果未來要互動式**（罕見）才需要 PTY + process write

### 10.2.1 v4.5 雙層 GPG 加密（2026-06-10 新增，必讀）

**問題**：v4.0 ~ v4.4 完全沒備份 passphrase 檔（單靠本地 = 不是備份）。

**v4.5 修法**：Tier 2 跑完後自動加跑 `backup_passphrase_recovery()`：
1. 用 GPG 對稱加密 passphrase（使用者互動輸入 USER_KEY）
2. 上傳 `hoonsorasus:hermes-backup/passphrase-recovery/`

**異機還原**（`hermes-restore-v4.sh tier2` 自動）：
- 偵測本地無 passphrase → 自動從 Drive `passphrase-recovery/` 還原
- 互動式問 USER_KEY → GPG 解密 → 放回 `~/Documents/hermes-keys/.hermes_backup_passphrase` (mode 600)

**USER_KEY 規則**：
- 必須**跟 GPG passphrase 不同**（兩層加密才有意義）
- 建議 = 1Password / Bitwarden 主密碼
- 記在 1Password 的 `hermes-backup USER_KEY` 條目

**為何需要第二個 layer？** 單一密碼 = 單點失敗。USER_KEY 在使用者腦中、跟 GPG passphrase 在本地檔、跟加密檔在 Drive = 3 個不同 failure domain。

### 10.3 跑完必須 `ls` 真實驗證（2026-06-10 踩坑，新加）

- **pty 跑完顯示「12 個項目成功」不代表真的備份成功**——pty 可能把輸出緩衝在記憶體、tar 寫到不存在的路徑卻沒 error
- **強制驗證**：`ls -la ~/.hermes/backups/hermes_backup_<新時間戳>_*.tar.gz` 確認兩個檔案存在
- **沒看到檔案 = 備份失敗**、**不論 pty 輸出多漂亮**

### 10.4 bash regex 字串要小心縮寫

- display tool 會把長 regex 縮成 `vcp_[A...20,}`，但 `bash -n` 只檢查 syntax 不檢查 regex literal。**實際跑 grep 驗證 regex 是真的**。
- **rclone config 兩份要分清楚**：`~/.config/rclone/rclone.conf`（舊）vs `~/documents/rclone.conf`（新、含 crypt 層）。備份 script 必須明確指 `~/documents/rclone.conf`，否則會用過期 token。
- **GitHub repo 預設 private**：`gh repo create --public` 不一定生效（帳號可能有預設 private）。**建完立刻 `gh repo edit --visibility public`**。
- **hermes-agent 沒 deepseek provider**：這次本想用 deepseek 當 cheap tier，失敗了。**未來不要嘗試 deepseek**（除非 patch source 或架 LiteLLM proxy）。詳見 `hermes-config-tuning` 試誤檔。
- **rclone sync Google Drive timeout → 速度崩潰至 B/s**：Google Drive API 寫入限制 = **3 requests/second sustained，無法提高**。用 `--transfers=2` 時，2 個檔案同時傳輸 = 2 組 API 並發 → 觸發 rate limit → 速度從 MiB/s 指數崩潰至 64 B/s → 600s timeout。**解法**：
  1. cron job `timeout_seconds` 至少設 **3600**（給夠時間在 rate limit 下慢慢跑完）
  2. rclone sync/copy 命令加：`--transfers=1 --checkers=1 --tpslimit 5 --drive-pacer-min-sleep 100ms`
  3. **觸發信號**：log 裡速度從 MiB/s → KiB/s → B/s 指數衰退，就是 rate limit，不是網路問題

### 🆕 10.5 v4 腳本 4 次修補（2026-06-10 14:xx，新加）

`hermes-backup-v4.sh` 在 2026-06-10 14:xx 從 v4.1 升到 **v4.4**，**4 個修補**：

| 版本 | 修補 | 為什麼 |
|---|---|---|
| **v4.2** | 加 `~/.hermes/profiles/` 同步段（18 個 exclude 旗標） | 原本只備 default profile，常駐子代理（consumer-researcher、product-planner）的整個 skill 庫/記憶/persona 都不會被備份 |
| **v4.3** | `skills/` rsync 加 `--max-size=50m` | hermes 自動備份在 `~/.hermes/skills/.curator_backups/<日期>/skills.tar.gz` 是 125MB 單一 blob，**GitHub 拒絕 > 100MB 物件**會讓 push 卡 95% 後 server 端 disconnect |
| **v4.3** | profiles rsync 加同樣 `--max-size=50m` | `~/.hermes/profiles/*/skills/.curator_backups/skills.tar.gz` 也是 125MB，v4.3 profiles 段必須同步加 |
| **v4.4** | `skills/` rsync 加 `--exclude='sparc-methodology/v3/'` 跟 `'sparc-methodology/ruflo/'` | sparc-methodology 整體 78MB（v3 跟 ruflo 內含大量 wasm/gif/mp4）--max-size 排除單檔、但整體 push 量還在容易觸發 GitHub 卡頓 |

**v4.4 profiles 同步段的完整 exclude 清單**（2026-06-10 14:xx 驗證必備）：

```bash
--exclude='*.bak.*' --exclude='*.lock' --exclude='*.clean.*' \
--exclude='.curator_backups/' --exclude='.archive/' --exclude='.hub/' \
--exclude='.usage.json' --exclude='.bundled_manifest' --exclude='.curator_state' \
--exclude='__pycache__/' --exclude='*.pyc' --exclude='venv/' \
--exclude='state.db' --exclude='state.db-shm' --exclude='state.db-wal' \
--exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip' --exclude='*.7z' \
--exclude='models_dev_cache.json' --exclude='home/' --exclude='logs/'
```

**If** 未來 v5 設計備份
**Then** 必加 `--max-size=50m` 到所有 rsync 段（GitHub 物件限制 100MB、保險起見 50MB）
**Then** 必加 `.curator_backups/` 到所有 rsync 排除清單（hermes 自動 backup 元件是遞迴 backup 陷阱）
**Then** 必加 `state.db*` 排除（對話歷史會爆、且含敏感 metadata，該走 Tier 2 加密備份）

### 🆕 10.6 GitHub push 125MB 卡死的根本解法（2026-06-10 14:xx 釐清，新加）

**症狀**：`git push --progress origin main` 跑到 95% (40+ MiB) 後**突然被砍**、server 端 `send-pack: unexpected disconnect while reading sideband packet`、本地 `git rev-list --left-right --count main...origin/main` 顯示 `1 0` 或 `2 0`(本地領先)。

**真凶**（必查 3 個）：
1. `find .git/objects -type f -size +50M` 找 staging 內 > 50MB 的單一 blob
2. `git verify-pack -v .git/objects/pack/*.pack | sort -k3 -rn | head -5` 找 pack 內最大物件
3. `git log --all --pretty=format:"%H %s" --diff-filter=AM -- '**/skills.tar*'` 找哪個 commit 引入的

**修法**（按優先順序）：

1. **先修 v4 腳本排除清單**（見 10.5）
2. **清空 staging**：`rm -rf .git profiles skills memories scripts cron docs config.yaml`
3. **重建 staging**：`git init -b main && git config user.email/name && git remote add origin https://github.com/.../hermes-config-backup.git`
4. **重跑 v4.4**：`bash ~/.hermes/scripts/hermes-backup-v4.sh --tier1`
5. **force push**：`git push --force --progress origin main`（**注意**：新 init 的 .git 沒共同祖先，`--force-with-lease` 會被 reject，要用 `--force`）

**If** 看到 push 進度條停在 95% 不動
**Then** 不要相信 `git push` 沒報錯就是成功 → 必 `git rev-list --left-right --count main...origin/main` 驗證
**Then** `0 0` = 成功、`1 0` 以上 = 有 commit 沒推上去、必查 blob 大小

### 🆕 10.7 .gitconfig 帳號混亂 — `gh auth setup-git` 是正解（2026-06-10 14:xx 釐清，新加）

**症狀**：`git push` 顯示成功但 `git rev-list` 確認沒推上去，或 `Permission to <repo> denied to <備用帳號>`。

**真凶**：`.gitconfig` 設 `credential.helper = store --file ~/.git-credentials-raphael`，裡面存的是**舊 `hoonsor` 備用帳號的 token**。`gh auth switch` **不會**改 git 全域認證（只改 gh CLI 自己的 token）。

**驗證**：
```bash
cat ~/.git-credentials-raphael   # 會看到 hoonsor:ghp_XXX@github.com
gh auth status                  # 主帳號是 hoonsoropenclaw，但 git 不會用
```

**正解**：
```bash
gh auth setup-git   # 自動注入 [credential "https://github.com"] helper = !/usr/bin/gh auth git-credential
```

這會在 `.gitconfig` 加兩段（覆蓋全域設定）：

```ini
[credential "https://github.com"]
    helper =
    helper = !/usr/bin/gh auth git-credential
[credential "https://gist.github.com"]
    helper =
    helper = !/usr/bin/gh auth git-credential
```

**規則**：
- `gh auth switch --user <name>` 切換 gh CLI 帳號（不影響 git）
- `gh auth setup-git` 讓 git 用 gh 當前 active 帳號的 token
- **永遠先 `gh auth status` 看 active account 是誰**再 push

**If** `git push` 失敗 + `Permission denied` + 主帳號是對的
**Then** 跑 `gh auth setup-git` 一次、永久解決

### 🆕 10.8 rclone "directory not found" 誤導錯誤（2026-06-10 14:xx 釐清，新加）

**症狀**：`rclone copy <local-file> <remote>:<bucket>/<subdir>/` 報 `directory not found`，但 `rclone lsd <remote>:<bucket>` **明確看到 subdir 存在**。

**真凶**：
- Drive 端的子目錄**真的存在**（`rclone lsd` 看到）
- rclone client 端的**路徑拼接錯誤**（少一個 `/`、多一個 `:`、特殊字元沒 escape）
- 或 Drive API 回的錯誤被 rclone 包成誤導訊息

**解法**：
- `rclone tree <remote>:<bucket> --max-depth 2` 看完整結構
- `rclone lsf <remote>:<bucket>/<subdir>/` 直接列 subdir 內容
- `rclone copy -v <file> <remote>:<bucket>/<subdir>/` 開 verbose 看哪一步失敗
- **130MB 加密檔 push 預期 5-10 分鐘**（231 KiB/s）—— 不要相信 `directory not found` 立刻放棄，先看 `rclone copy -v` 跑 30 秒有沒有進度

**If** 看到 `directory not found` 但 lsd 確認目錄存在
**Then** 直接 `rclone copy -v` 試一次，**不要相信錯誤訊息**

### 🆕 10.9 備份用錯路徑的終極防呆（2026-06-10 14:xx 釐清，新加）

- **2025-12 環境的備份路徑** `/media/hoonsoropenclaw/n100/backup-2025-12/` **在當前 N100 不存在**(`/media/` 是空的、沒 `hoonsoropenclaw` 子目錄)
- 任何備份腳本要寫到 `/media/...` 路徑 → **必先 `ls /media/` 確認掛載存在**，不存在就 abort
- 替代方案：`~/.hermes/backups/`(當前 v4 用的)或 `~/backups/`(本機磁碟、Drive 加密備份)

**If** 看到備份腳本寫到 `/media/...` 或 `n100/backup-2026...` 開頭
**Then** 先 `ls /media/hoonsoropenclaw/` 確認，**不存在就別跑**

## 11. References 支援檔(class-level 細節)

需要深入特定主題時 view 對應 reference:

- **`references/v4-rsync-exclude-recipes.md`** — v4 rsync 排除清單完整食譜(18+ 個 exclude 的「為何」+ v5 設計 checklist)
- **`references/github-push-recovery.md`** — GitHub push 卡死的 3 種情境 troubleshooting(95% 卡死 / SSH 卡死 / 帳號不一致)
- **`references/gpg-two-layer-encryption.md`** — GPG 雙層加密 + 異機還原完整設計(USER_KEY 規則 + Drive 目錄結構 + 互動式解密流程)

## 12. 改進方向（未實作）

- **真正的異機還原測試**：用 docker 跑完整 restore 流程驗證（未做，本 session 只測了 backup + rclone 連通性）
- **增量備份**：目前每次全量 134 MB 加密上傳，1.3 MB/s 要 100 秒。改 rclone `--backup-dir` 做 incremental 可省頻寬
- **多 profile 增量驗證**：v4.2 profiles 同步的 `.curator_backups/` 排除清單只驗證 default,profile 內是否還有其他隱藏大檔需要實測確認
