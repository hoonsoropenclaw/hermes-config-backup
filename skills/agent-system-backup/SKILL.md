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
    ├── secrets/                     # GPG passphrase
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

### 10.2 GPG 互動式 passphrase 強制 PTY（2026-06-10 踩坑，新加）

- `hermes-backup-v4.sh` 的 GPG 段落（行 168 附近）用 `gpg -c` 對稱加密、**passphrase 從互動式 prompt 輸入**
- **不能用 `terminal` foreground 跑**（會卡在 passphrase prompt、5 分鐘 timeout 拿不到輸入）
- **必須用 `pty=true` 跑**（PTY 模擬互動 TTY、prompt 出現時 agent 餵入 passphrase）
- 餵入方式：`pty=true` 啟動 + 看到 "Enter passphrase" prompt 時用 `process(action='write', data='<passphrase>')` 餵入 + `process(action='write', data='\n')` 確認

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

## 11. 改進方向（未實作）

- **真正的異機還原測試**：用 docker 跑完整 restore 流程驗證（未做，本 session 只測了 backup + rclone 連通性）
- **增量備份**：目前每次全量 134 MB 加密上傳，1.3 MB/s 要 100 秒。改 rclone `--backup-dir` 做 incremental 可省頻寬
- **多 profile 支援**：hermes 支援多 profile，但本備份 script 只備 default。要加 `~/.hermes/profiles/*` 的話需先看 `get_hermes_home()` 怎麼運作
