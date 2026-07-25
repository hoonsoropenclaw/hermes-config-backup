# Hermes v4.5 異機還原 SOP

> **寫於 2026-06-07 v4.1、2026-06-10 升 v4.5**（雙層 GPG 加密 + USER_KEY 自動還原）
> 適用於：新裝機、災難復原、機器移轉、重新安裝 hermes
> 適用對象：**未來的你**、**未來的 AI agent**、**任何接手維護的人**
> **必讀**：本文檔對「不知道 GPG passphrase」的人有完整解法

---

## 0. 讀我之前請先讀

這個文件**是 hermes 備份 v4.5 的官方還原手冊**。如果你不確定備份架構是什麼：
- 簡短版：見 §1 概念模型
- 完整版：見 `trial-and-error/references/by-category/hermes-backup-strategy.md`

如果這份 SOP 跟你看到的實際狀況不一致、**以實際狀況為準**並更新這份文件。

**這份 SOP 對 AI agent 的特殊設計**：
- 每個步驟都有「**預期輸出**」對照區塊
- 每個失敗都有「**AI 該怎麼 debug**」段
- 「GPG passphrase 忘記」**不再是災難**——有完整自動還原鏈

---

## 1. 概念模型（先看這個、再動手）

v4.5 備份架構由**兩層雲端** + **兩層 GPG 加密**組成：

```
┌────────────────────────────────────────────────────────────────┐
│  全新空機器（沒有 ~/.hermes/、什麼都沒有）                        │
└────────────────┬───────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
 ┌─────────────┐   ┌──────────────────────────────────┐
 │ Tier 1      │   │ Tier 2                            │
 │ GitHub       │   │ Google Drive                       │
 │ (公開 repo)  │   │ (私人 Drive)                       │
 │              │   │                                    │
 │ 內容：       │   │ 內容：                             │
 │ - skills/    │   │ ├── secrets/                        │
 │ - profiles/  │   │ │   └── secrets-bundle-*.tar.gpg   │
 │ - memories/  │   │ │        (GPG 加密的 .env + state.db)│
 │ - config    │   │ └── passphrase-recovery/           │
 │ - scripts/   │   │     └── passphrase-recovery-*.gpg│
 │ - docs/      │   │          (GPG 加密的 GPG passphrase)│
 └─────────────┘   │                                    │
                   │ 需要 2 組金鑰：                     │
                   │   - GPG passphrase  （解密 secrets/）│
                   │   - USER_KEY         （解密 recovery/）│
                   └──────────────────────────────────┘
```

**Tier 1（GitHub）** 公開、任何人可 clone、**不含真實 secrets**。
**Tier 2（Drive）** 私人、加密、需要 Drive OAuth + 雙層 GPG 金鑰。

**hermes-agent/ 不備份**：它是 `NousResearch/hermes-agent` 的 clone、可以 `git pull` 重建。

### 關於「**你不需要知道 GPG passphrase**」

v4.5 設計核心：**GPG passphrase 是 64 字元自動產生的亂碼、不該由人記**。

你只需要記一組 **USER_KEY**（建議 = 1Password 主密碼、或獨立存到密碼管理器）。USER_KEY 用來：
1. 解開 Drive `passphrase-recovery/*.gpg` → 拿到 GPG passphrase（機器自動讀）
2. 再用 GPG passphrase 解開 `secrets/*.tar.gpg` → 拿到 .env / auth.json / state.db

**整條還原鏈**：
```
USER_KEY (你記住)
  ↓ 解 passphrase-recovery/*.gpg
GPG passphrase (64字元, 自動產生, 不該人記)
  ↓ 解 secrets/*.tar.gpg
.env + auth.json + state.db (hermes 可用)
```

**AI 看這段的 debug check**：
- 「找不到 USER_KEY」→ 從 1Password 找「hermes-backup USER_KEY」條目
- 「GPG 解密失敗」→ 兩種可能：(a) USER_KEY 錯  (b) 加密時的 passphrase 跟還原時的 passphrase 不一致（不該發生在 v4.5）
- 「rclone 連不到 Drive」→ OAuth 過期、rclone.conf 沒設對

---

## 2. 環境需求檢查清單

新機器必須有：

- [ ] **OS**：Linux（推薦 Ubuntu 24.04、跟原機一致）
- [ ] **網路**：可訪問 github.com + drive.google.com
- [ ] **Python 3.11+**（用 `python3 --version` 驗證）
- [ ] **git**（用 `git --version` 驗證）
- [ ] **rclone**（用 `rclone version` 驗證）
- [ ] **gpg**（用 `gpg --version` 驗證）
- [ ] **Drive OAuth token**：要 `rclone config` 設定
- [ ] **USER_KEY**：從密碼管理器（1Password / Bitwarden）取得，**記在「hermes-backup USER_KEY」條目**

```bash
# 一次性環境檢查
python3 --version   # >= 3.11
git --version        # any
rclone version       # >= 1.60
gpg --version        # >= 2.0
curl --version       # 用來下載 hermes-agent install script
```

---

## 3. 還原流程（Step-by-Step）

### Step 1: 安裝 hermes-agent 本體

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes --version
```

如果失敗改用：
```bash
git clone https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent
pip install -e .
```

**注意**：hermes-agent 安裝完後**不會自動有 `~/.hermes/skills/`、`memories/` 等**。要靠 Tier 1 還原。

**預期輸出**：`hermes-agent v0.16.x installed` 之類的成功訊息

### Step 2: 設定 rclone config

```bash
# 從密碼管理器（1Password）複製舊機器的 rclone.conf
mkdir -p ~/documents
# 假設你從 1Password 下載到 ~/Downloads/rclone.conf
mv ~/Downloads/rclone.conf ~/documents/rclone.conf
chmod 600 ~/documents/rclone.conf

# 驗證 Drive 連線
rclone lsf hoonsorasus: --config ~/documents/rclone.conf
# 預期看到 hermes-backup/ 等目錄
```

**AI debug 點**：
- 沒看到 `hermes-backup/` → Drive 內容全空、可能是 OAuth 過期或 remote name 錯
- `directory not found` → 可能是 rclone 客戶端路徑拼接問題、加 `-v` 看詳細

### Step 3: 跑 Tier 1 還原（從 GitHub）

```bash
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-v4.sh -o /tmp/hermes-restore-v4.sh
bash /tmp/hermes-restore-v4.sh tier1 --target ~/.hermes
```

**預期時間**：4-10 分鐘。
**預期輸出**：`✓ Tier 1 完成、$TARGET_DIR 已含備份內容`

### Step 4: 跑 Tier 2 還原（從 Drive 雙層加密）

```bash
# 互動式：會問 USER_KEY（隱藏輸入）
bash /tmp/hermes-restore-v4.sh tier2 --target ~/.hermes

# 或非互動式（CI / cron 場景）：
HERMES_USER_KEY="<你的 USER_KEY>" bash /tmp/hermes-restore-v4.sh tier2 --target ~/.hermes
```

**內部會做**：
1. 偵測本地是否有 `~/Documents/hermes-keys/.hermes_backup_passphrase`
2. **沒的話** → 自動從 Drive `passphrase-recovery/` 下載最新加密檔
3. 互動式問 USER_KEY（或讀環境變數）
4. GPG 解密 → 放回 `~/Documents/hermes-keys/.hermes_backup_passphrase` (mode 600)
5. 從 Drive `secrets/` 下載最新 `secrets-bundle-*.tar.gpg` (~125 MB)
6. GPG 用 passphrase 解密
7. 解 tar 到 `~/.hermes/`：包含 `.env`、`auth.json`、`state.db`
8. 自動 chmod 600 所有 secrets 檔案

**預期時間**：3-5 分鐘（含 125 MB 下載）
**預期輸出**：
```
[15:14:25] === Tier 2: Drive secrets decrypt ===
[15:14:25] ⚠ 找不到本地 passphrase 檔
[15:14:25] ⚠ 嘗試從 Drive passphrase-recovery/ 還原...
[15:14:29] 找到 Drive passphrase-recovery: passphrase-recovery-20260610_071248Z.gpg
[15:14:33] USER_KEY 從 HERMES_USER_KEY 環境變數讀取（跳過互動 prompt）
[15:14:33] ✓ Passphrase 還原成功 → /home/.../hermes_backup_passphrase
[15:19:03] ✓   所有 secrets 檔案權限 600
[15:19:06] ✓ Tier 2 完成
```

**如果 rclone 報錯**：
- `directory not found` → Drive OAuth 過期（重新跑 rclone config）或路徑錯
- `Not Found` → token 過期
- `gpg: decryption failed` → USER_KEY 錯
- `bad session key` → 加密時的 passphrase 跟 USER_KEY 不對應

**AI debug 點**：
- 如果用戶跑完後說「還原失敗」→ 先看輸出 log 哪個步驟 fail
- 如果用戶說「不知道 USER_KEY」→ 提醒從 1Password「hermes-backup USER_KEY」條目找
- 如果用戶說「GPG 解密失敗」→ 兩種可能：USER_KEY 錯 或 加密時跟 USER_KEY 不一致（v4.5 應該不可能）

### Step 5: 跑週日自動驗證腳本（**最關鍵**）

```bash
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-verify.sh -o /tmp/hermes-restore-verify.sh
bash /tmp/hermes-restore-verify.sh
```

**預期結果**：
```
=== ✓ v4 Tier 1 還原驗證成功 ===
  還原 9226 個檔 / 157 個 skill
  設計約束符合：hermes-agent/ 不在、state.db 不在
```

### Step 6: 設定 cron 排程

```bash
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/cron/jobs.json -o /tmp/jobs.json
cp /tmp/jobs.json ~/.hermes/cron/jobs.json
chmod 600 ~/.hermes/cron/jobs.json

hermes gateway install
hermes gateway start

hermes cron list
# 應該看到 10 個 jobs、含 3 個 v4-*
```

---

## 4. 還原後必做的 7 件事

### 4.1 確認 .env 跟 auth.json 都有真實值

```bash
# 確認 .env 不是範本（內含 *** 就是範本）
head -3 ~/.hermes/.env
# 預期：註解 + 真實 key (不是「Copy this file to .env」)

# 確認 .env 內真有 4 個關鍵 key
grep -E "MINIMAX_API_KEY|DEEPSEEK_API_KEY|TAVILY_API_KEY|TELEGRAM_BOT_TOKEN" ~/.hermes/.env
# 預期：4 行（每行 key=sk-cp-xxx 之類的 30+ 字元）
```

**如果 .env 內全是 `***`** → Tier 2 沒真的還原、檢查 hermes-restore-v4.sh tier2 輸出

### 4.2 確認 state.db 有對話歷史

```bash
ls -lh ~/.hermes/state.db
# 預期：size > 150 MB
```

**如果 state.db 很小** → Drive 上抓到的是舊備份、應該找 `secrets-bundle-<最新時間戳>.tar.gpg`

### 4.3 確認 hermes-agent 源碼已安裝

```bash
ls -la ~/.hermes/hermes-agent/run_agent.py
# 預期：-rw-r--r-- 1 hoonsoropenclaw hoonsoropenclaw
```

### 4.4 跑一次 backup 確認自動排程會跑

```bash
bash ~/.hermes/scripts/hermes-backup-v4.sh --dry-run
# 預期：列出 Tier 1 + Tier 2 步驟（不真的跑）
```

### 4.5 跑一次 Tier 2 確認 Drive 上傳會跑

```bash
bash ~/.hermes/scripts/hermes-secrets-encrypt.sh --upload-drive
# 預期：5-10 分鐘內 Drive 上看到新 secrets-bundle-*.tar.gpg
```

### 4.6 驗證 hermes 能跑

```bash
hermes status
# 預期：4 個 ✓（含 LLM provider + Drive token + 其他整合）
```

### 4.7 跑週日驗證腳本

```bash
bash ~/.hermes/scripts/hermes-restore-verify.sh
# 預期：✓ 還原驗證成功
```

每項具體指令見各小節。

---

## 5. 還原驗證清單（打勾用）

- [ ] `python3 --version` >= 3.11
- [ ] `hermes --version` 有版本
- [ ] `~/.hermes/hermes-agent/run_agent.py` 存在
- [ ] `~/.hermes/config.yaml` 存在、size > 5 KB
- [ ] `~/.hermes/.env` 存在、mode 600、**含真實 API key（4 個關鍵 key）**
- [ ] `~/.hermes/auth.json` 存在、mode 600
- [ ] `~/.hermes/state.db` 存在、size > 150 MB
- [ ] `ls ~/.hermes/skills/` 至少有 100+ 個 skill
- [ ] `ls ~/.hermes/profiles/` 有 consumer-researcher + product-planner（2026-06-10 後）
- [ ] `hermes cron list` 顯示 10+ 個 jobs、含 v4-* 三個
- [ ] `bash ~/.hermes/scripts/hermes-restore-verify.sh` 顯示「✓ 還原驗證成功」
- [ ] `rclone lsf hoonsorasus:hermes-backup/secrets/` 看到 secrets-bundle-*.tar.gpg
- [ ] `rclone lsf hoonsorasus:hermes-backup/passphrase-recovery/` 看到 passphrase-recovery-*.gpg（v4.5 後）

---

## 6. 常見問題（FAQ）

### Q1：Drive 上看不到 hermes-backup/ 怎麼辦？
OAuth token 過期、hermes-backup 真的不存在、或 remote 名不對。詳解見 hermes-restore-v4.sh 內建錯誤訊息。

### Q2：USER_KEY 找不到怎麼辦？（**v4.5 新解**）
從 1Password / Bitwarden 找「hermes-backup USER_KEY」條目。
- **如果找不到** → 真的無解、必須從頭重跑 v4.5 backup 重新生成
- **千萬不要從 1Password 主密碼直接拿**（那組你可能忘記、USER_KEY 必須是你確定記得的）

### Q3：GPG passphrase 找不到怎麼辦？（**v4.5 新解**）
**不再卡住**！v4.5 設計讓你不需要直接記 GPG passphrase：
1. 從 1Password 找 USER_KEY
2. 跑 `HERMES_USER_KEY=... bash hermes-restore-v4.sh tier2`
3. 腳本自動從 Drive 還原 GPG passphrase
4. 再用 GPG passphrase 解開 secrets

### Q4：hermes-agent 是什麼版本？
看 `git log --oneline -5` 在 `~/.hermes/hermes-agent/`。v4.5 不備 hermes-agent 源碼、從 upstream 重建。

### Q5：state.db 比預期小？
1. Drive 上沒抓到最新
2. Tier 2 跑在 Tier 1 之前
3. 真的最近清空

### Q6：rclone crypt 跟明文 Drive 怎麼選？
v4.5 **完全不用 rclone crypt**。所有加密在 client side（gpg AES256）。

### Q7：週日驗證失敗？
看 `/tmp/hermes-restore-verify-*.log`。

### Q8：Vercel token 怎麼申請？
https://vercel.com/account/tokens → Create Token。

### Q9：為什麼 .env 內的 API key 跟我當初設定的不一樣？
可能原因：
1. **備份時間點不同**——你最後一次 v4.5 備份是 2026-06-10 06:16，之後改的 key 不在 Drive 加密檔內
2. **平台 revokes 了 key**——v4.5 只備份「當時」的金鑰，不會自動同步
3. **解法**：重新到平台申請新 key、跑 v4.5 重新備份

### Q10：可以升級 USER_KEY 嗎？
可以。流程：
1. 跟我說「升級 USER_KEY」或「我要改 USER_KEY」
2. 赫米斯跑 `hermes-secrets-encrypt.sh --rotate` 重新生成 GPG passphrase
3. 跑 `hermes-backup-v4.sh` 重新備份（互動式問新 USER_KEY）
4. 1Password「hermes-backup USER_KEY」條目改成新 USER_KEY

---

## 7. 自動化檢查

每次還原後跑：
```bash
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-verify.sh -o /tmp/h.sh
bash /tmp/h.sh
```

---

## 8. 緊急聯絡

1. `~/.hermes/logs/` 內最新 log
2. 本 SOP §6 FAQ
3. `~/.hermes/skills/trial-and-error/references/by-category/hermes-backup-strategy.md`

**不要**亂試 `purge` 或 `deletefile` 跟 rclone 相關的指令（會誤刪）。

---

## 9. v4.5 雙層 GPG 加密設計（給進階使用者）

如果你想理解為什麼要兩層加密、看這段：

```
攻擊模型:
  攻擊者拿到 Drive secrets/*.tar.gpg  → 沒 GPG passphrase 拿不到
  攻擊者拿到 Drive passphrase-recovery/*.gpg  → 沒 USER_KEY 拿不到
  攻擊者同時拿到兩者  → 還需要 USER_KEY 才能解第一層

3 個獨立 failure domain:
  - Drive (可能被駭、可能不小心設公開)
  - 本地 GPG passphrase 檔 (硬碟壞掉)
  - USER_KEY (使用者腦中, 或 1Password)

任一 domain 失效、其他兩個還能擋
```

**USER_KEY 設定建議**：
- 跟 1Password / Bitwarden 主密碼相同（最容易記）
- **不要**跟 GPG passphrase 相同（兩層加密才有意義）
- 記在 1Password 的「hermes-backup USER_KEY」條目
- 每季驗證一次還能用（解密任一 passphrase-recovery-*.gpg 看是否成功）

---

## 10. 版本紀錄

| 日期 | 版本 | 改動 |
|------|------|------|
| 2026-06-10 | v4.5.0 | 雙層 GPG 加密、USER_KEY 自動還原、hermes-restore-v4.sh tier2 支援環境變數 |
| 2026-06-07 | v4.1.0 | 全新撰寫、對應 v4.1 雙雲端架構 |
| 2026-06-06 | v3.0 | 舊版、保留供參考 |

**如果你覺得這份 SOP 有缺漏**：直接編輯補上、commit + push 到 `hermes-config-backup/docs/RESTORE-V4.md`。
