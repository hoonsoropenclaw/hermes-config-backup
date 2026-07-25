# 赫米斯全狀態備份策略（2026-06-06 完整建立）

赫米斯「完整還原到新主機」這類任務的標準 SOP。涵蓋本地 tar.gz + Google Drive rclone crypt 加密 + GitHub 公開 repo 的三路分流架構。

## 何時用這個檔

**If** 接到任務包含以下任一：
- 「備份赫米斯設定 / 異機還原 / 全狀態備份 / 災難復原」
- 「把所有 hermes 設定推到 GitHub / 雲端 / Drive」
- 「我換新主機了怎麼把赫米斯搬過去」
- 「cron 跑備份失敗 / 還原失敗 / 備份不完整」

**Then** 先讀這份，看「分流決策樹」跟「常見踩雷」再動手。

---

## 三路分流架構（2026-06-06 設計）

| 目標 | 內容策略 | 公開性 | 還原時機 |
|------|---------|-------|---------|
| **GitHub 公開 repo** | 不含敏感/過大；外部 skill **完整版**保留修改 | 任何人可 clone | 平時開發、輕量還原 |
| **Google Drive rclone crypt** | **全部**（含 .env 真實、源碼、state.db、GPG token、cache/logs/...） | 加密、私人 | 災難還原、跨主機遷移 |
| **本地 tar.gz** | 7 天保留 + Drive 資料夾命名 `hermes_backup_<ts>_full/` | 本機 | 中間還原、debug |

**為什麼要兩版（PUBLIC vs FULL）**：
- PUBLIC 版可放 GitHub 公開、隨時 clone、不需要 Drive 權限
- 但公開版不能含真實 .env、state.db（169 MB session store）、hermes-agent 源碼（1.1 GB）
- FULL 版**只**放 Drive（加密），含**所有**敏感 + 大型 + 修改後的外部 skill
- **使用者問「外部 skill 我改過的版本怎麼辦」→ 兩版都要完整 rsync 整個 skill 資料夾，不要只列 INSTALLED_MANIFEST.md 名單**（v1.0 失敗的經驗）

---

## Drive 資料夾結構（一定要這樣命名）

```
hoonsorasus:hermes-backup/    ← rclone remote: hoonsorasus（明文 Google Drive）
└── hermes-backup/             ← 加密層 crypt_hermes 透明解密
    ├── HERMES-BACKUP-README.md    ← 跨備份的說明（明文，第一次看到 Drive 的人能讀）
    ├── hermes-restore.sh          ← 一鍵還原腳本（明文，使用者先下載改 3 個變數就跑）
    └── hermes_backup_20260606_205730_full/   ← 每次備份一個時間戳資料夾
        ├── hermes_backup_20260606_205730_full.tar.gz  ← 加密 tar（含全部）
        ├── RESTORE.md                                  ← 該次備份專屬 SOP
        └── restore_hermes.sh/                          ← 解 tar 後的還原腳本
```

**Why this shape**：
- 加密層外面（`hoonsorasus:hermes-backup/`）放**明文**的 README + 一鍵腳本 —— 沒 Drive 權限的人也知道怎麼還原
- 加密層裡面（每次備份的 `hermes_backup_<ts>_full/`）放加密 tar + 該次備份的 SOP
- 解密時 Drive 顯示亂碼（這是 rclone crypt 透明加密的效果、**正常的**）

---

## rclone 雙目錄加密（2026-06-06 確認）

### 兩個 rclone.conf 在哪

| 路徑 | 狀態 | 用途 |
|------|------|------|
| `~/.config/rclone/rclone.conf` | 5/24 創、token 已過期、remote 叫 `Openclawdrive` | **不要用** |
| `~/documents/rclone.conf` | 6/6 創、token 新、remote 叫 `hoonsorasus` + `crypt_hermes` | **用這個** |

兩個檔都是 `0600` mode、`533` vs `685` bytes 差異。**If** 看到 token expired 報錯，**先確認用的哪份**。

### 驗證 rclone 連線（不要 ping 一句就說接好）

**If** 看到 hermes 跑 ping pong 通過就以為 rclone 接好 **Then** 提醒自己：簡單 ping 連 fallback 都能回。要驗證 rclone 真的接到 Drive：
1. `rclone listremotes --config /path/rclone.conf` 看到 `[hoonsorasus:]` + `[crypt_hermes:]`
2. `rclone lsd crypt_hermes:` 看到實際資料夾（不是空）
3. `rclone ls crypt_hermes:hermes_backup_<ts>_full/` 看到 tar.gz 大小符合

---

## 全狀態備份包含哪些（**v3.0 完整版**）

### Drive FULL tar.gz 內含（v3.0 ~145 MB）

```
config/
├── hermes-config.yaml       ← 全域設定、含 delegation.model、provider、memory 開關
├── cron-jobs.json           ← 所有 cron jobs（hermes-daily-backup 也含在這）
├── env-template             ← 公開版用的 key 範本（key 全部 *** 化）
└── hermes-env-real           ← 真實 .env（mode 600、12 個 API key，**只有 FULL 才有**）

memories/  (7 個核心 MD)
├── USER.md                  ← 個人化設定
├── MEMORY.md                ← 長期記憶
├── SOUL.md、AGENTS.md、IDENTITY.md、HEARTBEAT.md、TOOLS.md

skills/  (PUBLIC 版只放 SKILL.md、references/，完整 rsync 外部 skill 的修改版)
├── autonomous-ai-agents/{metacognitive-learner,hermes-agent}/   # persistent-subagent 已於 2026-06-09 移除
├── hermes-tier-router/
├── trial-and-error/         ← L3 教訓寶庫
├── alt-token-secrets-layout/
└── INSTALLED_MANIFEST.md    ← 所有已裝 skill 清單 + 完整備份大小

scripts/  (全部 Python/Shell)
data/     (kanban.db)
docs/     (RESTORE.md)

full_backups/                ← **只有 FULL 才有這層**
├── INVENTORY.md             ← Drive 專屬清單
├── state.db                 ← 169 MB session store
├── hermes-agent/            ← 1.1 GB 源碼（排除 venv/）
├── sparc-methodology/       ← 103 MB 外部 skill
├── alt_gh_tokens/           ← GPG 加密的備用 GitHub PAT
├── secrets/                 ← GPG **加密的** .env + auth.json + state.db（需 passphrase 才能解）
├── passphrase-recovery/     ← v4.5 新增：GPG **加密的** passphrase 檔（需 USER_KEY 才能解）
├── cache/、logs/、lsp/、bin/、sessions/
└── models_dev_cache.json
```

### v4.5 雙層加密策略（2026-06-10 新增）

**問題**：v4.0 ~ v4.4 設計有致命漏洞——`passphrase 檔（~/Documents/hermes-keys/.hermes_backup_passphrase）` 從未被備份到任何地方。**如果 N100 硬碟壞掉，使用者完全無法異機還原 Drive 上加密的 .env/auth.json/state.db**。

**v4.5 修法**：雙層 GPG 加密 + 雙層 Drive 目錄分離

```
Drive
├── secrets/secrets-bundle-20260610_*.tar.gpg
│   ← 加密的 .env/auth.json/state.db
│   ← 解密金鑰：GPG passphrase (auto-generated 64-char, 在 ~/Documents/hermes-keys/)
│
└── passphrase-recovery/passphrase-recovery-20260610_*.gpg
    ← 加密的 passphrase 檔
    ← 解密金鑰：USER_KEY (使用者記住的單一密碼，建議 = 1Password 主密碼)
```

**異機還原時流程**（hermes-restore-v4.sh tier2 自動處理）：

1. Drive 下載 `secrets-bundle-*.tar.gpg`（需要 Drive 連線）
2. **如果本地沒有 passphrase 檔** → 自動從 `passphrase-recovery/` 還原：
   - 下載 `passphrase-recovery-*.gpg`
   - 互動式問 USER_KEY
   - GPG 解密 → 放到 `~/Documents/hermes-keys/.hermes_backup_passphrase`（mode 600）
3. 用 passphrase 檔解 `secrets-bundle-*.tar.gpg` → 拿到 .env/auth.json/state.db
4. 修權限（600）

**USER_KEY 設定建議**：
- 跟 1Password / Bitwarden 主密碼相同（最容易記）
- **不要**跟 GPG passphrase 相同（兩層加密才有意義）
- 記在 1Password 的 `hermes-backup USER_KEY` 條目

### GitHub PUBLIC tar.gz 內含（v3.0 ~9.4 MB）

**不**含：.env 真實檔、state.db、hermes-agent 源碼、sparc-methodology 完整版

**含**：
- 7 個核心 MD（USER/MEMORY/...）
- config（含 env-template 範本）
- 所有 333 個 skill（**完整 rsync 整個資料夾**，含外部 skill 修改版本）
- 全部 scripts
- RESTORE.md、HERMES-BACKUP-README.md、hermes-restore.sh

---

## 必走的 secret 掃描 + redact 流程

備份**絕不能**把真實 token 推到公開 GitHub。

**If** 看到 STAGING 內有 vcp_/ghp_/sk- 等真實 token **Then** 在打包前用 perl 萬用 regex redact：

```bash
find $STAGING -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) -print0 | \
  xargs -0 perl -i -pe 's/(vcp_|ghp_|sk-|hms_|gho_|glpat-)[A-Za-z0-9_-]{20,}/[TOKEN_REDACTED]/g'
```

**不要**維護「已知洩漏 token 名單」—— 用 regex 自動 redact 所有符合 pattern 的字串。歷史教訓：2026-06-05 GH013 事件就是 vcp_ token 在 trial-and-error references 內被當事件記錄留下，沒 redact 直接 push 公開 repo。

---

## 跑備份的 script 結構

**If** 寫 `backup_hermes.sh` 類腳本 **Then** 結構要對：
1. 預檢工具（rclone / git / python3 / tar / rsync / gh）
2. 預檢 rclone config 跟 remote
3. 兩個 staging 目錄分開（PUBLIC vs FULL）
4. 複製檔案到對應 staging
5. 打包前的 secret redact（萬用 regex）
6. 打包兩個 tar.gz
7. 打包後 secret 掃描驗證（用 `tar -xzOf | grep` 一次解，**不要**用 `xargs tar` 每檔呼叫一次會卡住 3 分鐘）
8. rclone copy 加密上傳 FULL 到 Drive
9. rsync 到 GitHub repo staging、commit、push PUBLIC
10. 同步 README + hermes-restore.sh 到 **Drive 根目錄**（讓初次看 Drive 的人有入口）
11. 清理 7 天前的本地、14 天前的 Drive 舊備份

---

## cron 註冊注意事項（**不要用 hermes cron edit**）

**If** 要註冊 no-agent script 跑備份 **Then** **手動編輯** `~/.hermes/cron/jobs.json`，不要用 `hermes cron edit --script` 指令。

**症狀**：`hermes cron edit --id <id> --script '...'` 對 no_agent=True jobs 有 bug，會把 script 內容寫進 `prompt` 欄位而非 `script` 欄位。

**正確做法**：手動加 JSON 進 jobs.json：
```json
{
  "id": "<uuid12>",
  "name": "hermes-daily-backup",
  "prompt": "...",
  "script": "backup_hermes.sh",
  "no_agent": true,
  "schedule": {"kind": "cron", "expr": "0 3 * * *", "display": "0 3 * * *"},
  ...
}
```

2026-06-06 修過：詳見 `hermes-internal.md` 內的 `hermes cron edit --script` bug 條目。

---

## 異機還原的 3 條路徑

| 路徑 | 來源 | 適用情境 |
|------|------|---------|
| **A. 本地 tar** | 直接從 .tar.gz 還原 | 最快、已有本地備份 |
| **B. Drive 加密** | `hermes-restore.sh` 一鍵 | 推薦、自動化、互動式選擇 |
| **C. GitHub 公開** | clone repo + 跑 restore_hermes.sh | 沒 Drive 權限時的 fallback |

**Drive 加密路徑（推薦）的執行步驟**：
1. 從 Drive 下載 `hermes-restore.sh`（明文、就放在 `hoonsorasus:hermes-backup/` 根目錄）
2. 編輯頂部 3 個變數：`HERMES_HOME`、`RCLONE_CONFIG`、`GITHUB_USERNAME`
3. `./hermes-restore.sh`
4. 腳本自動：找最新備份 → rclone crypt 自動解密 → 解 tar → **互動式問要不要還原 6 個區塊**（核心/.env/state.db/源碼/GPG/sparc）→ 顯示驗證清單

---

## Telegram session 警告（重要）

異機還原 Telegram bot 行為：
- 還原檔案本身**不會**動到 Telegram session
- 新主機的 gateway 啟動時會認本地 `gateway_state.json`（從備份還原）
- **不能兩台主機同時開 gateway** → 會搶同一個 bot
- 還原前務必：`pkill -f hermes-gateway` 關掉舊主機
- 完整說明見 `RESTORE.md` 第 2.5 節

---

## 已驗證的失敗案例（避免重蹈）

### 案例 1：DeepSeek provider 假接（2026-06-06）
- 看到 `hermes chat --provider deepseek` 回 pong 就以為接好
- 實際：hermes 內建沒 deepseek provider，靜默 fallback 到 minimax
- **教訓**：簡單 ping 通過 ≠ provider 接好。要看源碼、測真實任務輸出風格

### 案例 2：外部 skill 修改丟失（v1.0 → v3.0 修正）
- v1.0 備份只列 INSTALLED_MANIFEST.md 名單 → 重裝會拿原始版
- v3.0 改完整 rsync 整個 skill 資料夾 → 修改版本保留
- **教訓**：對**任何**可能被使用者改過的 skill，**完整 rsync 整個資料夾**，不要只備 SKILL.md

### 案例 3：secret scan 卡住 3 分鐘（v2.0 → v3.0 修正）
- v2.0 用 `tar -tzf | xargs tar -xzOf` 對 10000+ 檔案跑 scan → 30 秒還沒好
- v3.0 改用 `tar -xzOf | grep` 一次解 → 秒過
- **教訓**：對大 tar 跑內容 grep，**永遠用 `tar -xzOf`** 一次解，不要用 `xargs tar` 每檔呼叫

### 案例 4：trial-and-error references 內含真實 token（2026-06-05）
- vcp_ token 當事件教訓字串留在文件內
- 沒 redact 直接 push 公開 GitHub → 觸發 GH013 push protection
- **教訓**：所有備份打包前用萬用 regex redact 一次；教訓檔的「真實洩漏字串」要嘛化名要嘛明示「已 redact」

### 案例 5：rclone.conf 用了舊的（2026-06-06）
- `~/.config/rclone/rclone.conf` 是 5/24 舊版、token 過期
- 應該用 `~/documents/rclone.conf` 6/6 新版
- **教訓**：rclone config 雙目錄時先看 token 跟 remote 名，**不要假設自動連到對的**

---


## v4 雙雲端演進：2026-06-07 從 v3.0 半成品到 v4 雙雲端

v3.0 設計上線後**在 Drive 跑了 2 次都卡 63-68%**（rclone sync 13,611 小檔撞 Drive API 840K 配額牆），**正式放棄 v3 純 Drive 架構**、改用 v4 雙雲端分工。

### 為什麼 v3 失敗（一句話總結）

> Google Drive API 配額 = 840,000 單位/分鐘/專案。rclone sync 每小檔 ≈ 3-5 單位。13,611 小檔 = 50,000+ 單位、**幾分鐘內必秒殺**。
> 即使加 `--tpslimit 5 --transfers 1 --checkers 1` 限速到 1-2 小時、還是會在跑到一半 throttle。

完整根因 + 症狀證據見 [[hermes-backup-design-pitfalls#Rule 8：Drive API 配額 840K/分鐘/專案、13,611 小檔必爆（從 stderr 拿到 Google 官方配額數字）]]

### v4 架構（已實作在 `~/.hermes/scripts/`）

| Tier | 雲端 | 備什麼 | 為什麼這層 | 還原時間 |
|------|------|--------|------------|----------|
| **Tier 1** | **GitHub** `hoonsoropenclaw/hermes-config-backup` | skills/agents/memories/scripts/docs/config.yaml | 文字版控、git protocol 無 Drive 配額問題、永久歷史 | **5 分鐘** |
| **Tier 2** | **Google Drive**（crypt 加密） | secrets bundle（.env、auth.json、auth.lock）| 大檔 + 加密 + Drive 配額寬容 | 額外 2 分鐘 |
| **Tier 3** | **本地 Y 槽**（選配） | 即時鏡像 | 最快還原、零網路 | 0 分鐘 |

**腳本**（已建立並通過端到端測試）：
- `hermes-backup-v4.sh` — 統一備份入口
  - `--tier1`：只推 GitHub（增量）
  - `--tier2`：只跑 Drive secrets 加密
  - `--upload-tier2`：加密後推到 Drive
  - `--dry-run`：看會做什麼但不做
- `hermes-restore-v4.sh` — 統一還原入口
  - `tier1` / `tier2` / `tier3` / `all`
  - `--target DIR`：還原到隔離目錄（不覆蓋當前 hermes）
- `hermes-secrets-encrypt.sh` — Tier 2 加密腳本
  - AES256 + S2K mode 3 + s2k-count 65011792
  - 雙目錄分離：加密檔在 `~/.cache/hermes-secrets-staging/`、passphrase 在 `~/Documents/hermes-keys/`
  - 加密後產出 chmod 600、明文 shred 刪除

### v4.1 修正（2026-06-07）：state.db 跟 hermes-agent 分類重新檢視

**問題發現**：v4 設計時把 `state.db` 跟 `hermes-agent/` 都歸類為「rebuild 即可、不備份」— **這兩個判斷都錯了**。

#### state.db 真的要備

**症狀**：
- `state.db` 197 MB、`SessionDB` 類別（hermes_state.py 內）
- AGENTS.md 明確寫：「**SQLite session store (FTS5 search)**」
- 包含所有對話歷史、FTS5 索引、session metadata
- **壞了 = 所有對話歷史全沒、不能用 pip install 重建**

**錯誤判斷**：
- 我之前說「rebuild 即可」是**憑印象**、沒實際看 `hermes_state.py` 跟 `state.db` 內容
- 用戶當場質問「state.db 不是對話紀錄嗎、不是應該要備嗎？」才讓我去查現況

**修正**：
- state.db → **Drive Tier 2 加密**（197 MB、單一大檔、Drive 友善）
- 跟 `.env`、`auth.json` 一起打包成 secrets bundle、用同一套 GPG 加密
- Drive 對單一大檔 197 MB = 1 個 API request 解決、配額完全不是問題

#### hermes-agent/ 真的可以不備（這次有驗證）

**驗證步驟**（這次我有做）：
```bash
cd ~/.hermes/hermes-agent
git remote -v
# → origin  = git@github.com:NousResearch/hermes-agent.git

git rev-list --count HEAD..origin/main
# → 786（落後 upstream 786 個 commit）

git status -sb
# → ## main...origin/main [behind 786]
# → （沒有未推的本地 patch）
```

**結論**：
- ✅ `hermes-agent/` 是 `NousResearch/hermes-agent` 的 clone、**不是用戶本地維護的**
- ✅ 沒有未推的本地 patch（所以用戶沒改過源碼）
- ✅ `git pull` 隨時可重建、**真的不需要備份 1.1 GB 的源碼**
- ❌ 之前 v4 說「venv 排除省 351 MB」是對的、但**整個 hermes-agent/ 也是可以排除的**

#### venv 維持不備

- 純 site-packages 351 MB
- `pip install hermes-agent` 可重建
- 用戶沒問 venv 細節、維持原判斷

### v4.1 最終資料分配表

| 資料 | 大小 | 去哪 | 為什麼 |
|------|------|------|--------|
| `skills/`（用戶自建） | ~340 MB | **GitHub** | 文字、版控友善 |
| `agents/`、`memories/`、`scripts/`、`docs/`、`config.yaml` | ~10 MB | **GitHub** | 純文字 |
| `state.db`（對話歷史、FTS5） | 197 MB | **Drive 加密** | 不可重建、單一大檔 Drive 友善 |
| `.env`、`auth.json`（secrets） | ~30 KB | **Drive 加密** | 敏感 |
| `hermes-agent/`（1.1 GB upstream clone） | 1.1 GB | **不備** | `git pull` 重建 |
| `venv/`（351 MB site-packages） | 351 MB | **不備** | `pip install` 重建 |
| `~/.cache/`、`logs/`、`sessions/`、截圖 | ~50 MB | **不備** | 可重建 |

**修正後 Drive Tier 2 預估總量**：~200 MB（state.db + secrets + auth.lock）
**Drive 對這個量 = 1 個檔就行、配額完全不是問題**

### v4.1 重裝清單（完整版）

```bash
# === Step 1: 系統依賴 ===
apt install -y python3 python3-pip python3-venv git curl gpg rclone

# === Step 2: 安裝 hermes-agent 本體（從 upstream GitHub） ===
git clone https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent
pip install -e .                                    # 開發模式安裝
# 或：pip install -r requirements.txt                 # 純用戶模式

# === Step 3: 從 v4 Tier 1（GitHub）拉用戶資料 ===
git clone https://github.com/hoonsoropenclaw/hermes-config-backup.git /tmp/hermes-restore
rsync -au /tmp/hermes-restore/skills/ ~/.hermes/skills/
rsync -au /tmp/hermes-restore/memories/ ~/.hermes/memories/
cp /tmp/hermes-restore/config.yaml ~/.hermes/
# agents/、docs/、scripts/ 同上

# === Step 4: 從 v4 Tier 2（Drive 加密）拉 secrets + state.db ===
hermes-restore-v4.sh tier2
# 自動：rclone pull → gpg decrypt → 寫回 ~/.hermes/.env, auth.json, state.db

# === Step 5: 驗證 ===
hermes status
hermes chat -q "ping"
```

**總時間預估**：15-20 分鐘（Tier 1 拉 + Tier 2 拉 + 安裝 hermes-agent）

### v4.1 帶來的腳本改動

1. `hermes-secrets-encrypt.sh` — 加密清單加 `state.db`
2. `hermes-backup-v4.sh` 的 rsync 排除 — 明確排除 `hermes-agent/`（不是依賴子檔案排除）
3. `hermes-restore-v4.sh tier2` — 解密後把 state.db 寫回 `~/.hermes/`

### If→Then（v4.1 自我審查）

- **If** 用戶問「X 真的可以不備嗎」**Then** 永遠去查：是不是 upstream clone？有沒有本地 patch？能不能 rebuild？
- **Then 不要**憑印象答「rebuild 即可」、**要附驗證命令的真實輸出**（`git remote -v`、`git rev-list` 比較）
- **If** 發現「X 是對話歷史、不能重建」**Then** 立刻歸類到 Drive Tier 2（單一大檔、Drive API 友善）

### 相關條目

- [[hermes-internal#自我審查：自我報告 ≠ 驗證（2026-06-06 確立）]] — 為什麼這次一開始判斷錯
- [[gh-cli-and-github#GH013 push protection 觸發時的完整修復 SOP]] — state.db 含什麼敏感資訊（如果進 GitHub 會怎樣）
- [[bash-defensive-patterns#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]] — 為什麼備份腳本的錯誤檢查要重寫

---

### sparc-methodology 的處理決策

**重要**：`~/.hermes/skills/sparc-methodology/` **不是赫米斯本地維護的 skill**、是 `https://github.com/ruvnet/claude-flow.git` 的 clone（commit 844f68d、落後 upstream 2 個 commit）。

**最終決策**（2026-06-07 採納）：
- ❌ 不用 Git submodule（over-engineering、v4 雙雲端不需要）
- ❌ 不用自建 `hermes-sparc-skills` repo（白工、浪費時間）
- ✅ 用 **snapshot 模式**：把 `sparc-methodology/` 內容複製進 `hermes-config-backup/skills/`
- ✅ 用 root `.gitignore` 排除 `agentdb.rvf` 系列、`.git/`、venv、cache
- ✅ 排除規則在 staging repo 根目錄 `.gitignore`（不是 sparc 內子目錄）
- ✅ 更新方式：手動 `cd ~/.hermes/skills/sparc-methodology && git pull` 後再跑 v4 備份

完整決策過程見 [[hermes-backup-design-pitfalls#Rule 10：「先查上游、不要假設本地是 source of truth」— sparc-methodology 是 upstream clone 不是本地維護]]

### v4 驗證結果（2026-06-07 實測）

| 驗證項 | 結果 |
|--------|------|
| 跑 `hermes-backup-v4.sh --tier1` | ✓ GitHub push 成功（commit 1eab220） |
| 跑 `hermes-secrets-encrypt.sh --verify` | ✓ 加密 + 解密驗證成功（3 個 secrets、9.2 KB） |
| 跑 `hermes-restore-v4.sh tier1 --target /tmp/test/` | ✓ 4 秒完成、6760 個檔還原 |
| `diff -r ~/.hermes/agents/ /tmp/test/agents/` | ✓ 完全一致（2026-06-09 已刪 agents/，此列為歷史紀錄） |
| sparc-methodology 還原檔案數 | 4640 / 4674（差 34 個是 .gitignore 排除） |
| 第二次跑 `hermes-backup-v4.sh --tier1` | ✓ 「沒有變動、跳過 commit」（增量運作正確） |

### v4 不解決的問題（誠實聲明）

| 限制 | 影響 | 替代方案 |
|------|------|----------|
| GitHub 5 GB 總量限制 | 現在 151 MB、可用 12,000 倍空間 | 真爆了花 $7/月升級 |
| GitHub 公開 repo | 你的 skills 內容會被看光 | 看你是否要改 private（$4/月） |
| Drive 84 萬配額 | 加密 tar.gz 是 1 個檔、**OK** | v3 那種 1 萬小檔繼續不支援 |
| 異機還原需要網路 | 沒網路時只能用 Tier 3 | 已涵蓋 |

### If 接到 v4 設計相關任務的決策樹

- **If** 想把更多資料備份進 GitHub **Then** 先確認不含 secrets、不是 cache、不是備份檔
- **If** 拿到 sparc / claude-flow / 任何 upstream clone **Then** 不用 submodule、用 snapshot
- **If** 看到 Drive 上半成品備份資料夾 **Then** 先清掉（v3 那種 13,611 小檔半成品）再談新方案
- **If** 異機還原要 5 分鐘內拿到可運行的 hermes **Then** 用 `hermes-restore-v4.sh tier1`、**不要**載 694 MB v2 tar.gz

---

## v4.2 修整（2026-06-07）：廢掉 rclone crypt，改明文 Drive + client-side GPG

### 觸發情境

v4.1 設計完後嘗試把 88 MB state.db + secrets 的加密 bundle 推到 Drive Tier 2，結果：
- `rclone copy` 用 rclone crypt 跑 **18+ 分鐘**還沒完成（speed 56-100 KiB/s、過程中還會重傳 chunk、變成 174 MB 的「虛擬傳輸」）
- 部分 run 卡 12 分鐘沒進度、kill 重來 3 次都沒成功
- 同步跑 `rclone copy` 改用明文 Drive（`hoonsorasus:`）→ **1 分 46 秒**完成 87 MB（1.1 MiB/s）

**速度差 10x**（crypt: 56 KiB/s vs 明文: 1.1 MiB/s），加上 rclone crypt 對大檔有「streaming 加密」效能問題、結論：**rclone crypt 對 >50 MB 大檔加密不實用**。

### 架構決策（2026-06-07 確認）

**廢掉 rclone crypt layer**。改用：
- **Drive 端**：明文 `hoonsorasus:`（rclone.conf 已有、token 新）
- **client 端**：本地用 `gpg --symmetric` 加密成 .gpg 檔（aes256 + s2k-mode 3 + s2k-count 65011792）
- **Drive 上看到**的就是 `.gpg` 副檔名的加密檔（**沒有雙重加密 overhead**）

**Drive 結構**（v4.2）：
```
hoonsorasus:hermes-backup/    ← 明文 Drive（rclone crypt 不再用）
├── HERMES-BACKUP-README.md    ← 明文 README（跨備份說明）
├── hermes-restore.sh          ← 一鍵還原腳本（明文）
└── secrets/                    ← 加密 .gpg 檔（client-side GPG）
    └── secrets-bundle-20260607_032356Z.tar.gpg  ← 89 MB（含 state.db + .env + auth.json）
```

**好處**:
- 加密在 client side 做完、Drive 上傳只看到「加密 blob」
- Drive 對單一大檔 1 個 API request 解決、配額完全不是問題
- 還原時 client 端 GPG 解密、跟原本 hermes-secrets-encrypt.sh 流程一致
- 速度從 18 分鐘變 1 分 46 秒

**Passphrase 分離**（不變、原本就是對的）：
- 加密 staging：`~/.cache/hermes-secrets-staging/`（cache 目錄、跟 ~/Documents 隔離）
- Passphrase：`~/Documents/hermes-keys/.hermes_backup_passphrase`（**嚴格跟加密檔分開**）

### 腳本改動

`hermes-secrets-encrypt.sh`：
- `RCLONE_REMOTE="hoonsorasus:hermes-backup/secrets"`（改用明文 Drive、不用 crypt）
- `upload_drive` 函式用 `rclone copy`（不用 `copyto`、不用 `mkdir` 偽成功）

`hermes-restore-v4.sh`：
- `RCLONE_REMOTE="hoonsorasus:hermes-backup/secrets"`（同上）
- tier2 函式不變、解密流程跟 v4.1 一致

### 閉環驗證（2026-06-07 實測）

| 步驟 | 結果 |
|------|------|
| 1. 跑 `hermes-secrets-encrypt.sh --upload-drive` | ✓ **1m46s** 完成 89 MB（speed 1.1 MiB/s） |
| 2. `rclone ls hoonsorasus:hermes-backup/secrets/` | ✓ 89 MB 加密檔在 Drive 上 |
| 3. 跑 `hermes-restore-v4.sh tier2 --target /tmp/test-restore-tier2/` | ✓ 解密成功（`AES256.CFB`） |
| 4. `ls /tmp/test-restore-tier2/` | ✓ 6 個檔全還原：.env (25 KB), auth.json (1.2 KB), state.db (**200 MB**), state.db-wal, state.db-shm, auth.lock |
| 5. 權限檢查 | ✓ .env mode 600 ✓ |

**結論**: v4.2 流程**可實際運作**、state.db 對話歷史有備份、secrets 加密安全、Drive 速度 1.1 MiB/s 友善。

### 用戶偏好的明確信號

> 用戶：*「請使用你自己的加密方式去加密然後再直接備份到google drive上（一樣路徑）好了」*

**這條要求背後的意思**：
- 接受「client-side 加密 + 明文 Drive」這個架構（這是業界標準模式）
- 拒絕 rclone crypt 的 double encryption overhead
- 未來備份任務**預設走「明文 Drive + 客戶端 GPG」**，除非明確說要改

### If→Then（v4.2 自我審查）

- **If** rclone crypt 對 >50 MB 大檔跑超過 10 分鐘還沒完成 **Then** 立刻 kill、廢掉 crypt、改用明文 Drive + client-side GPG
- **If** 寫備份腳本用 `rclone` 系列指令 **Then 不要**用 `2>/dev/null || true` 偽成功、讓錯誤冒出來
- **If** 寫 Drive 還原腳本用 `rclone lsf` 找最新檔 **Then** 一定要加 `--files-only`（Drive .gpg 偽目錄陷阱）
- **If** 接到「rclone purge」這類高風險指令 **Then** 先 `--dry-run` 確認範圍、不要對 `remote:` 不帶 path 跑
- **Then** 任何 Drive 操作完成後都用 `rclone ls` 驗證檔案真的在（不要只信 exit code）

### 相關條目

- [[hermes-backup-design-pitfalls#Rule 14：`rclone purge <remote>:` = 砍整個 remote 內容到垃圾桶（不是清垃圾桶）]] — 為什麼 v4.2 廢掉 crypt
- [[hermes-backup-design-pitfalls#Rule 15：`rclone mkdir ... 2>/dev/null || true` 偽成功 + Drive 上 .gpg 顯示成「偽目錄」陷阱]] — 還原腳本要避開的坑
- [[hermes-backup-design-pitfalls#Rule 13：rclone crypt 對大檔（>50 MB）加密是反模式]] — 速度差 10x 的數據
- [[bash-defensive-patterns#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]] — 為什麼不能用 `|| true`

---

## 跟其他分類的關聯

- 編輯 jobs.json 的具體步驟 → [[hermes-internal#hermes cron edit --script 對 no_agent jobs 的 bug]]
- Provider 真的接上 ≠ 設了 API key → [[hermes-config-tuning#Provider 真的接上 ≠ 設了 API key]]
- 完整 L3 教訓：Tier routing 設定→驗證→失敗循環 → [[hermes-config-tuning#完整 L3 教訓：Tier routing 設定→驗證→失敗循環（2026-06-06）]]
- 自我報告不等於驗證 → [[hermes-internal#自我審查：自我報告 ≠ 驗證（2026-06-06 確立）]]

---

### hermes-backup-coverage-check.sh 設計:3 層檢查 + EXCLUDE 清單明確（2026-06-10）

**症狀**：備份覆蓋率檢查如果只比對「v4 有列 vs 本機有」會被「故意不備的檔」（如 .env 走 Tier 2、state.db 走加密、hermes runtime 鎖定檔）誤判為「漏備」、刷出幾十個假 warning；信號/噪音比太低、最後變成「看到 WARN 就跳過」

**根因**：第一版實作只判斷「v4 沒列 = 漏備」、沒分「故意不備」（EXCLUDE 清單）跟「真的漏備」（建議加），導致 25 個 warning、其中 21 個是假警報。

**解法**（3 層檢查）：
- **Layer A（本機有 v4 沒列 → 建議加）**：解析 v4 腳本 `ROOT_SINGLE_FILES` array + 13 個 `if [[ -d $HERMES_HOME/<dir>/ ]]` 段
- **Layer B（v4 有列本機沒 → 可能搬走）**：notes 段、不算 error
- **Layer C（staging vs 本機 SHA256 同步驗證）**：檢查 staging 落後、不是純「該備沒備」

**EXCLUDE 清單要明確標出「故意不備的」**（3 類）：
1. **Tier 2 加密的**（hermes-secrets-encrypt.sh 管）：`.env`、`.env.lock`、`auth.json`
2. **hermes runtime 鎖定 + 狀態**：`state.db` 系列、gateway 系列鎖、`processes.json`、`kanban.db.init.lock`、`kanban.db`（空殼）
3. **rebuildable 暫存**：4 個 cache.json、`.update_check`、`.hermes_history`、`.install_method`、`youtube_tokens.json`（待加密但暫不）

**Exit code 三級**：
- 0 = PASS（完整、沒漏）
- 1 = WARN（有建議加的、不影響備份）
- 2 = FAIL（嚴重問題、立即處理）

**預防**：
- 覆蓋率檢查不是「grep 找漏」、是「比對 expected vs actual + 標出故意排除」
- 寫 log 到 `~/.hermes/logs/<script-name>.log`、**不靠 stdout 通知**（notify_on_complete 延遲 10-14 分鐘是常態）
- cron 排程要避開主備份時段（v4 是 03:00、coverage check 04:00、避開 30 分鐘內重疊）

**If→Then**：
- **If** 設計任何 config-driven 系統的覆蓋率檢查 **Then** EXCLUDE 清單必明確標出「故意不備的」、避免誤判
- **If** coverage check 第一次跑就出現 > 10 個 WARN **Then** 必檢查 EXCLUDE 清單是否完整（v0 = 25 WARN、v1 = 4 WARN 才是合理）
- **If** cron job 用 no_agent + script 模式 **Then** stdout 空 = SILENT（不要把訊息寫 stdout、寫 log 檔）

**相關條目**：
- [[hermes-backup-design-pitfalls#v4 備份腳本只列 7 個目錄+1 個檔,但 ~/.hermes/ 根目錄有 20+ 個路徑]]
- [[hermes-backup-sop#改任何備份腳本必同步改 INVENTORY.md + SKILL.md §14.1 改檔對照表]]
- [[hermes-internal#notify_on_complete 是「最終確認」不是「即時 polling」]]
