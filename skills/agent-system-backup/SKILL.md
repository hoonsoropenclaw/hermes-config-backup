---
name: agent-system-backup
description: "赫米斯型 AI agent 的全狀態備份 SOP。涵蓋 v4.5 雙層 GPG 加密（Tier 1 GitHub + Tier 2 Google Drive）、USER_KEY 自動還原、4 份還原說明檔、cron 排程、secret 掃描、in-house 還原 SOP、AI 友善的還原說明。2026-06-10 完整驗證通過。**未來 AI 處理任何『備份/還原/異機還原/GPG/passphrase/USER_KEY』任務必先載入本 skill**。"
version: 1.1.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [backup, disaster-recovery, restore, rclone, github, google-drive, cron, hermes-agent, gpg, user-key, v4, v4.5]
    triggers:
      # 主要觸發：使用者說什麼時要載入
      - 備份
      - 跑備份
      - 備份 hermes
      - 異機還原
      - 還原
      - 還原 hermes
      - 還原說明
      - GPG 密碼
      - passphrase
      - USER_KEY
      - 雙層加密
      - 加密還原
      - 備份策略
      - restore
      - backup hermes
      - disaster recovery
      - 異機還原 SOP
      - 跑 hermes-restore
      - 跑 hermes-backup
---

# Agent System Backup — 全狀態備份 class-level SOP

適用於任何「想把自己整套設定異機還原」的 agent 系統(不限 Hermes)。
**2026-06-10 v4.5 驗證**:HERMES N100 迷你電腦實戰跑通,雙層 GPG 加密解密鏈端到端驗證(passphrase md5 完全一致)。

## 🎯 這個 skill 何時該載入(給未來 AI 看)

**If** 收到以下任何訊息/任務 **Then** 載入本 skill:

- 「跑備份」「備份 hermes」「異機還原準備」「幫我還原」
- 「GPG 密碼是什麼」「USER_KEY」「passphrase 找不到」
- 「我的備份設計有沒有漏洞」「加密備份安全嗎」
- 「寫個還原 SOP」「給未來的 AI 看的還原說明」
- 「備份有定時跑嗎」「上次備份什麼時候」
- 「異機還原要怎麼做」「新機器要怎麼裝 hermes」

**If** 你正在設計任何「加密檔推雲端」架構 **Then** 必讀 §10 已知陷阱 + `references/gpg-two-layer-encryption.md`

**If** 你正在改任何 v4 backup 腳本 **Then** 必讀 §14 修改影響對照表(避免改了忘記同步改其他地方)

---

## 1. 為什麼 v4.5 雙層加密(2026-06-10 新版設計)

| 層 | 內容 | 進哪 | 加密 |
|---|---|---|---|
| **Tier 1** (公開) | 設定、記憶、skills、profiles、scripts、config | GitHub 公開 repo | 無(redact secrets) |
| **Tier 2a** (私人) | GPG 加密的 .env + auth.json + state.db (197MB) | Google Drive `secrets/` | GPG (金鑰:64 字元 passphrase) |
| **Tier 2b** (私人) | GPG 加密的 passphrase 檔(156 bytes) | Google Drive `passphrase-recovery/` | GPG (金鑰:USER_KEY 使用者記住) |

**為什麼要雙層 GPG?**

單層 GPG 加密 .env → Drive、passphrase 留本地 → 機器壞掉 = 加密檔無法解開(沒金鑰)。**單靠本地金鑰 = 不是備份**。

v4.5 設計:passphrase 也加密推到 Drive 獨立目錄、金鑰的「金鑰」(USER_KEY)由使用者記憶(1Password)。3 個獨立 failure domain 任一失效、其他擋住。

詳細設計見 `references/gpg-two-layer-encryption.md`。

---

## 2. 完整備份流程 SOP(2026-06-10 補強)

未來任何 AI 想跑備份,**照這 7 步**。

### Step 1: 環境檢查
```bash
which hermes          # ~/.local/bin/hermes (使用者層安裝)
which gpg && gpg --version   # >= 2.0
which rclone && rclone version  # >= 1.60
which gh && gh auth status    # GitHub OAuth 認證
```

### Step 2: 看現有備份狀態
```bash
ls -la ~/.hermes/backups/ 2>&1 | head -10
rclone lsf hoonsorasus:hermes-backup --config ~/documents/rclone.conf
ls ~/.hermes/hermes-backup-staging/  # staging 應跟 GitHub 同步
```

### Step 3: dry-run 試跑(不真實 push)
```bash
bash ~/.hermes/scripts/hermes-backup-v4.sh --dry-run
# 預期列出 Tier 1 + Tier 2 + backup_passphrase_recovery + upload_drive_restore_readme
```

### Step 4: 跑 Tier 1(GitHub push)
```bash
bash ~/.hermes/scripts/hermes-backup-v4.sh --tier1
# 預期 5-10 分鐘,git push 完整成功
```

### Step 5: 跑 Tier 2(Drive 加密 + USER_KEY)
```bash
# 互動式:會問 USER_KEY 兩次(確認)
bash ~/.hermes/scripts/hermes-secrets-encrypt.sh --upload-drive

# 或設環境變數(cron 用):
export HERMES_USER_KEY="<USER_KEY>"
bash ~/.hermes/scripts/hermes-secrets-encrypt.sh --upload-drive
```

**互動式 prompt**(第一次跑、還沒設 HERMES_USER_KEY 時出現):
```
════════════════════════════════════════════════════════════
  v4.5 passphrase 備份
  這台 N100 硬碟如果壞掉,需要 USER_KEY 從 Drive 解開 passphrase
  然後才能解開 secrets/*.tar.gpg
  ⚠️  USER_KEY 跟 GPG passphrase 不同、是你自己選的一組密碼
  ⚠️  建議跟你的密碼管理器(1Password)主密碼相同
  ⚠️  千萬不要跟 GPG passphrase 相同
  請輸入 USER_KEY: ********
  請再輸入一次確認: ********
```

### Step 6: 端到端驗證(必做)
```bash
# 自動跑整套解密鏈驗證(PASS/FAIL)
HERMES_USER_KEY="<USER_KEY>" bash ~/.hermes/skills/agent-system-backup/scripts/verify-recovery-chain.sh
```

**預期輸出**:`✓ PASS 鏈通、可以信賴`

### Step 7: 確認 Drive 端內容
```bash
rclone tree hoonsorasus:hermes-backup --level 2
# 預期看到:
#   DRIVE-RESTORE.md
#   passphrase-recovery/passphrase-recovery-<時間戳>.gpg
#   secrets/secrets-bundle-<時間戳>.tar.gpg
```

---

## 3. 完整版 INVENTORY(這次實際跑的內容)

```
hermes_backup_<ts>_full.tar.gz  (~134 MB)
├── config/                          # 公開版 + 額外
│   ├── hermes-config.yaml
│   ├── hermes-env-real              # 真實 .env（mode 600、4 個 key）—— 只有完整版有
│   ├── cron-jobs.json
│   └── env-template                 # 公開版的 key *** 化範本
├── memories/                        # 7 個核心 MD
├── skills/                          # 自建 6 個
├── profiles/                        # v4.2 新增:consumer-researcher + product-planner
├── scripts/                         # 含 hermes-backup-v4.sh + hermes-restore-v4.sh
├── docs/                            # v4.5 新增:4 份還原說明
└── full_backups/                    # 額外這層（**只有完整版**）
    ├── INVENTORY.md
    ├── state.db                     # 271 MB session store
    ├── hermes-agent/                # 1.1 GB 源碼
    ├── sparc-methodology/           # 103 MB 外部 skill
    ├── alt_gh_tokens/
    ├── secrets/                     # ← v4.5 變成指向 Drive 加密檔的 symlink
    └── models_dev_cache.json
```

**rsync 排除清單**:`references/v4-rsync-exclude-recipes.md` 完整版(三層過濾)

---

## 4. 雙重 Secret 掃描 SOP

**位置 1:打包前**(在 staging 內 redact)
```bash
find "$STAGING" -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) -print0 | \
  xargs -0 perl -i -pe 's/(vcp_|ghp_|sk-|hms_|gho_|glpat-)[A-Za-z0-9_-]{20,}/[TOKEN_REDACTED]/g'
```

**位置 2:commit 前**(GitHub 版最後一次)
```bash
cd "$GITHUB_REPO_DIR"
grep -rE "$SECRET_REGEX" . --include="*.md" --include="*.yaml" --include="*.json" --include="*.py" --include="*.sh" && abort
```

---

## 5. Drive 資料夾自描述模式(2026-06-10 v4.5 加強)

**Drive `hoonsorasus:hermes-backup/` 根目錄必須有**:
- `DRIVE-RESTORE.md` — 給未來 AI 看的入口(§A 完整 SOP、§B 不知道 GPG 怎麼辦、§C AI 決策樹)
- `secrets/` — 加密 .env
- `passphrase-recovery/` — v4.5 新增

**自動上傳**:`hermes-backup-v4.sh` 的 `upload_drive_restore_readme()` 函式,每次 Tier 2 完成時自動推 `docs/DRIVE-RESTORE.md` 到 Drive 根目錄。

**`DRIVE-RESTORE.md` 範本在 `~/.hermes/docs/DRIVE-RESTORE.md`**,改完後 `bash hermes-backup-v4.sh --upload-tier2` 會自動同步。

---

## 6. cron 排程(no-agent script 模式)

**手動加 jobs.json**:
```python
{
  "id": "<uuid>",
  "name": "<system>-daily-backup",
  "prompt": "# 說明 script 做什麼（給 log 看）",
  "script": "backup_<system>.sh",
  "no_agent": True,
  "schedule": {"kind": "cron", "expr": "0 3 * * *", "display": "0 3 * * *"},
  "enabled": True,
  "deliver": "local"
}
```

**為什麼凌晨 3 點**:避開其他 cron、上傳雲端速度較快、跨日時「本機是昨天、雲端是今天」混淆。

**為什麼 `no_agent: True`**:cron 跑備份不需要 LLM、節省 token 跟延遲。詳見 `hermes-deploy-verification` skill。

---

## 7. restore_hermes.sh 三路徑設計(2026-06-10 v4.5 升級)

```bash
# 路徑 A:互動式(有 TTY 時自動問 USER_KEY)
bash hermes-restore-v4.sh tier1
bash hermes-restore-v4.sh tier2

# 路徑 B:非互動式(cron / CI)
HERMES_USER_KEY="<key>" bash hermes-restore-v4.sh tier1
HERMES_USER_KEY="<key>" bash hermes-restore-v4.sh tier2

# 路徑 C:all(全跑)
HERMES_USER_KEY="<key>" bash hermes-restore-v4.sh all
```

**警告語必含**:
> ⚠️ 異機還原前,務必先 `pkill -f hermes-gateway` 關掉任何已運行的 gateway。
> Telegram session 一次只能掛一台機器。兩台同時開會搶同一個 bot。

---

## 8. 4 份還原說明檔 SOP(2026-06-10 v4.5 新加,**給未來 AI 看**)

**必須同時維護 4 份**,對應 4 個入口場景:

| 檔案 | 位置 | 入口場景 |
|---|---|---|
| `~/.hermes/docs/RESTORE-V4.md` | GitHub + 本地 | 「我要看完整 SOP」(接手者首選) |
| `~/.hermes/docs/HERMES-BACKUP-README.md` | GitHub + 本地 | Drive 端 README(已重寫 v4.5) |
| `~/.hermes/docs/DRIVE-RESTORE.md` | **Drive 根目錄** + GitHub | Drive 端入口指南(給 AI) |
| `trial-and-error/references/by-category/hermes-backup-strategy.md` | GitHub skill | 設計細節(給進階使用者) |

**4 份檔案對 AI 的設計**:
- ✅ 每個步驟都有「預期輸出」對照
- ✅ 失敗症狀對照表(9+ 種)
- ✅ 3 個角色入口(新手/不知道 GPG/AI 助手)
- ✅ 「你不需要知道 GPG passphrase」明確標示
- ✅ 決策樹(給 AI 看)
- ✅ 「不要慌張」安全提醒

**任何備份架構改動都必同步更新這 4 份** — 見 §14 改檔對照表。

---

## 9. 異機還原時 Telegram / Gateway 影響(重要 FAQ)

**Q:異機還原會影響 Telegram session 嗎?**
A:分三情境:
- **新主機第一次架設**:不影響舊主機。restore 完後啟動 gateway 會重新跑 OAuth、生成新 session 檔。
- **暫時取代舊主機**:會有幾秒到幾分鐘斷線。session 從 `gateway_state.json` 還原、不需重跑 OAuth。
- **兩台同時開 gateway**:**禁止**。Telegram bot 會搶同一個 chat_id 訊息。

---

## 10. 已知陷阱(持續累積)

### 10.1 腳本歧義(2026-06-10 踩坑)
- `~/.local/bin/backup-all.sh` (舊 v3, 2025-12 環境) **不要用**
- `~/.hermes/scripts/hermes-backup-v4.sh` (當前 v4.5) **唯一正確**
- 用 `ls ~/.hermes/backups/hermes_backup_*.tar.gz` 確認 v4 有跑

### 10.2 GPG 加密方式:**自動讀 passphrase 檔**(2026-06-10 釐清)
- `hermes-secrets-encrypt.sh` 用 `gpg --batch --passphrase-file "$PASSPHRASE_FILE"` 從固定路徑讀
- **完全不需要互動 prompt、PTY、process write 餵入**
- passphrase 在 `~/Documents/hermes-keys/.hermes_backup_passphrase` (mode 600、64 字元)
- **如果有人問「GPG 密碼是什麼」** → 不要在對話打密碼、回他「在固定路徑、64 字元自動產生的」

### 10.2.1 v4.5 雙層 GPG 加密(**必讀**)
**問題**:v4.0 ~ v4.4 沒備份 passphrase 檔 → 機器壞掉 = 無法還原

**v4.5 修法**:
- `backup_passphrase_recovery()`:用 USER_KEY 加密 passphrase 推到 `passphrase-recovery/`
- `recover_passphrase_from_drive()`:本地無 passphrase 自動從 Drive 還原

**USER_KEY 規則**:
- 跟 GPG passphrase **必須不同**
- 建議 = 1Password / Bitwarden 主密碼
- 記在 1Password 的「hermes-backup USER_KEY」條目

**驗證**:`HERMES_USER_KEY=x bash hermes-restore-v4.sh tier2` 成功(2026-06-10 14:14)

### 10.3 跑完必須 `ls` 真實驗證
- pty 跑完顯示「12 個項目成功」不代表真的備份成功
- **強制驗證**:`ls -la ~/.hermes/backups/hermes_backup_<新時間戳>_*.tar.gz`
- **沒看到檔案 = 備份失敗**、不論 pty 輸出多漂亮

### 10.4 bash regex 字串要小心縮寫
- display tool 會把長 regex 縮成 `vcp_[A...20,}`
- `bash -n` 只檢查 syntax 不檢查 regex literal
- **實際跑 grep 驗證 regex 是真的**

### 🆕 10.5 v4 腳本 4 次修補(2026-06-10 14:xx)
| 版本 | 修補 |
|---|---|
| v4.1 | 原始版、只備 default skills/ |
| v4.2 | 加 `profiles/` 同步段(18 exclude)、常駐子代理才會被備份 |
| v4.3 | `skills/` rsync 加 `--max-size=50m`、防止 125MB curator backup 漏進去 |
| v4.4 | 加 `sparc-methodology/v3/` 跟 `ruflo/` 排除(78MB、可 rebuild) |

**下次 v4.5.1 還有微調(HERMES_USER_KEY 環境變數 + DRIVE-RESTORE 自動推)**。

**If** 改 v4 腳本 **Then** 必加:
1. `--max-size=50m` 到所有 rsync 段
2. `.curator_backups/` 到所有排除清單
3. v4 profiles 段完整 exclude 清單見 `references/v4-rsync-exclude-recipes.md`

### 🆕 10.6 GitHub push 125MB 卡死的根本解法(2026-06-10)
**症狀**:`Writing objects: 95%` 然後 `send-pack: unexpected disconnect`

**根因**:GitHub 拒絕 > 100MB 單一物件。`.curator_backups/skills.tar.gz` 是 125MB。

**修法**:`--max-size=50m` 排除 + 確認 staging 內沒有 `.curator_backups/`。

**完整修法**見 `references/github-push-recovery.md`。

### 🆕 10.7 .gitconfig 帳號混亂 — `gh auth setup-git` 是正解(2026-06-10)
**症狀**:`git push` 顯示進度跑到 95% 但 `rev-list` 顯示 `1 0`,或 `Permission to <repo> denied to <備用帳號>`

**根因**:`~/.gitconfig` 設 `credential.helper = store --file ~/.git-credentials-raphael`(舊帳號 token),不會自動用 gh 帳號 token

**修法**:
```bash
gh auth setup-git  # 注入 !gh auth git-credential 到 .gitconfig
gh auth status     # 看 active account
gh auth switch --user hoonsoropenclaw  # 必要時切換
```

### 🆕 10.8 rclone "directory not found" 誤導錯誤(2026-06-10)
**症狀**:`rclone copy <file> hoonsorasus:hermes-backup/secrets/` 報 `directory not found`,但 `rclone lsd` 看到目錄存在

**根因**:rclone 錯誤訊息是誤導、可能是 OAuth 過期或路徑拼接

**修法**:
1. `rclone tree <remote>:<bucket> --max-depth 2` 看完整結構
2. `rclone lsf <remote>:<bucket>/<subdir>/` 直接列 subdir
3. `rclone copy -v <file> <remote>:<bucket>/<subdir>/` 開 verbose
4. 130MB 加密檔 push 預期 5-10 分鐘(231 KiB/s)、看到錯誤別立刻放棄

### 🆕 10.9 備份用錯路徑的終極防呆(2026-06-10)
**症狀**:用 `~/.local/bin/backup-all.sh` (舊 v3) 寫到不存在的 `/media/.../backup-2025-12/`、pty 卻顯示「成功」

**根因**:舊 v3 腳本硬編 `/media/hoonsoropenclaw/n100/backup-2025-12/` 路徑、此機器根本沒這路徑

**修法**:
- **永遠用 `~/.hermes/scripts/hermes-backup-v4.sh`**
- 跑前 `head -50 hermes-backup-v4.sh` 確認 `--help` 介面
- 跑後 `ls ~/.hermes/backups/hermes_backup_<新時間戳>_*.tar.gz` 真實驗證
- 詳見 §10.3

---

## 11. 跟其他 skill 的關係

- `trial-and-error` → `by-category` → `hermes-backup-strategy.md` — 設計文件
- `hermes-deploy-verification` — 部署前驗證 SOP(備份屬於其中一環)
- `hermes-tier-router` — 備份 cron 會把這個 skill 也備份
- `alt-token-secrets-layout` — GPG 加密 token 的 SOP

---

## 12. 一鍵驗證腳本(2026-06-10 14:14 新增)

- **`scripts/verify-recovery-chain.sh`** — 端到端驗證 v4.5 雙層 GPG 加密解密鏈
  ```bash
  HERMES_USER_KEY="<你的 USER_KEY>" bash scripts/verify-recovery-chain.sh
  ```
  自動跑:備份原版 md5 → Drive 下載 passphrase-recovery → USER_KEY 解密 → 對比 md5 → 下載 secrets-bundle → recovered passphrase 解 → 確認 tar 內容有 .env / auth.json / state.db。輸出 PASS / FAIL。**每季跑一次、跟備份同樣重要**。

---

## 13. 改進方向(未實作)

- **真正的異機還原測試**:用 docker 跑完整 restore 流程驗證(本 session 只測了 backup + rclone 連通性 + 端到端 md5 驗證)
- **增量備份**:目前每次全量 134 MB 加密上傳、1.3 MB/s 要 100 秒。改 rclone `--backup-dir` 做 incremental 可省頻寬
- **多 profile 增量驗證**:v4.2 profiles 同步的 `.curator_backups/` 排除清單只驗證 default,profile 內是否還有其他隱藏大檔需要實測確認
- **加密備份的時間鎖**:USER_KEY 改變時,先 `--rotate` 再備份,避免新舊 passphrase 衝突

---

## 14. 📋 修改影響對照表(2026-06-10 補強,**給未來 AI 必看**)

> **這是本 skill 最關鍵的章節**。
> 改任何備份/還原相關東西,**必同步掃下表所有要連動的檔**。
> 漏一個就會出問題(這次踩過的坑)。

### 14.1 改 `hermes-backup-v4.sh`(備份腳本)時

**必同步修改**:

| 檔案 | 為什麼必改 |
|---|---|
| `~/.hermes/docs/RESTORE-V4.md` | SOP 要跟備份腳本對得上 |
| `~/.hermes/docs/DRIVE-RESTORE.md` | Drive 端入口要反映新設計 |
| `~/.hermes/docs/HERMES-BACKUP-README.md` | Drive 端 README |
| `~/.hermes/scripts/hermes-restore-v4.sh` | 還原腳本要對應(例如新加 --upload-drive 就要 restore 加對應處理) |
| `~/.hermes/skills/agent-system-backup/SKILL.md` | **本檔** §10 已知陷阱 + §2 SOP 要更新 |
| `~/.hermes/skills/agent-system-backup/references/v4-rsync-exclude-recipes.md` | rsync 排除清單變了要更新 |
| `trial-and-error/references/by-category/hermes-backup-strategy.md` | 設計文件 |
| `trial-and-error/references/by-category/hermes-internal.md` | L2 試誤條目(踩過的坑) |
| `~/.hermes/memories/MEMORY.md` | L3 抽象教訓 |
| `~/.hermes/memories/AGENTS.md` | 如果有提到備份架構 |

**驗證**:
```bash
# 改完跑這些確認
bash ~/.hermes/scripts/hermes-backup-v4.sh --dry-run  # 語法 + 邏輯
ls ~/.hermes/hermes-backup-staging/                    # staging 仍可同步
gh auth setup-git && timeout 60 git -C ~/.hermes/hermes-backup-staging push  # push 通
```

### 14.2 改 `hermes-restore-v4.sh`(還原腳本)時

**必同步修改**:跟 §14.1 一樣,外加:
- `~/.hermes/skills/agent-system-backup/scripts/verify-recovery-chain.sh` — 驗證腳本要對應新設計

### 14.3 改 GPG / passphrase / USER_KEY 設計時

**必同步修改**:
- `hermes-backup-v4.sh` (Tier 2 段)
- `hermes-restore-v4.sh` (`recover_passphrase_from_drive` 段)
- `hermes-secrets-encrypt.sh` (加密段)
- `~/.hermes/docs/RESTORE-V4.md` §6 Q2/Q3
- `~/.hermes/docs/DRIVE-RESTORE.md` §B
- `~/.hermes/skills/agent-system-backup/SKILL.md` §1 / §10.2.1
- `references/gpg-two-layer-encryption.md` — 完整設計文件
- `trial-and-error/references/by-category/gpg-encryption.md` — L2 試誤

**驗證**:`HERMES_USER_KEY=x bash scripts/verify-recovery-chain.sh` 必跑 PASS

### 14.4 加新的還原說明檔時

**必同步修改**:
- 對應的 SOP 入口
- 本 SKILL.md §8 4 份說明檔表
- 把新檔推到對應的雲端位置(Drive 用 `rclone copy`、GitHub 用 `git add`)

### 14.5 改身份 / profile / 命名空間時

(例如 v4.2 加 profiles/、v4.5 加 passphrase-recovery/)

**必同步修改**:
- 所有 `market-strategist` / `consumer-researcher` / `product-planner` 引用
- 跨 profile 的 SKILL 引用
- 任何「已知 profile 清單」文件
- `AGENTS.md` `@專案` 表格
- `trial-and-error` 索引(grep 驗證)

---

## 15. 撰寫還原說明檔 SOP(**給未來給異機還原的 AI 看**,2026-06-10 補強)

> 這次經驗:使用者反覆問「AI 能不能理解」、「要不要寫進說明檔」、「怎樣才不漏」。
> **結論:寫進說明檔,並且對 AI 友善**。

### 15.1 還原說明檔要包含的 7 個元素

撰寫任何給「未來 AI / 接手者」看的還原說明檔,**必含**:

1. **概念模型**(架構圖 + 失敗域分析)
2. **環境需求檢查清單**(可貼上貼下的命令)
3. **Step-by-Step 流程**(每步都有「預期輸出」對照)
4. **還原後必做的事**(可驗證清單)
5. **常見 FAQ**(至少 5 個 Q&A)
6. **失敗症狀對照表**(症狀 → 真凶 → 解法)
7. **自動化驗證方法**(一鍵 script 跑 PASS/FAIL)

### 15.2 「對 AI 友善」的 5 個設計原則

1. **「不要慌張」** — 在文件開頭放,降低未來 AI 看到陌生錯誤的恐懼
2. **決策樹** — 給 AI 看的「如果 X 走 A、Y 走 B、Z 走 C」明確指引
3. **預期輸出對照** — 每個步驟寫「跑完應該看到什麼」,AI 可對照判斷
4. **不要術語** — 或術語後立刻解釋
5. **「為什麼這樣設計」** — 讓 AI 理解架構而不是死記 SOP

### 15.3 還原說明檔 4 入口場景

(同 §8 表格,但這邊講**為什麼要有 4 份**)

| 入口 | 為什麼要這個入口 |
|---|---|
| RESTORE-V4.md | GitHub README 入口、搜尋引擎找得到 |
| HERMES-BACKUP-README.md | Drive 端基本 README |
| DRIVE-RESTORE.md | Drive 根目錄入口、給「打開 Drive 就想還原」的人 |
| 設計策略檔 | 給進階使用者(為什麼這樣設計、未來怎麼改) |

### 15.4 改任何還原說明檔時必跑的驗證

```bash
# 1. 文件還在(沒被誤刪)
ls -la ~/.hermes/docs/{RESTORE-V4.md,HERMES-BACKUP-README.md,DRIVE-RESTORE.md}

# 2. 文件提到 USER_KEY
grep -l "USER_KEY" ~/.hermes/docs/*.md

# 3. Drive 上的 DRIVE-RESTORE.md 跟本地同步
rclone cat hoonsorasus:hermes-backup/DRIVE-RESTORE.md | diff - <(cat ~/.hermes/docs/DRIVE-RESTORE.md)

# 4. 還原鏈仍通
HERMES_USER_KEY="<key>" bash ~/.hermes/skills/agent-system-backup/scripts/verify-recovery-chain.sh
```

---

## 16. References 支援檔(class-level 細節)

- `references/gpg-two-layer-encryption.md` — 雙層 GPG 加密完整設計(2026-06-10)
- `references/v4-rsync-exclude-recipes.md` — v4 rsync 排除清單完整食譜(2026-06-10)
- `references/github-push-recovery.md` — GitHub push 卡死 troubleshooting 完整流程(2026-06-10)

## 17. Scripts 支援檔

- `scripts/verify-recovery-chain.sh` — 端到端解密鏈驗證(2026-06-10 D 方案驗證後寫成)
