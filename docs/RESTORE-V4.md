# Hermes v4.1 異機還原 SOP

> **寫於 2026-06-07**、v4.1 雙雲端架構（GitHub Tier 1 + Google Drive Tier 2）。
> 適用於：新裝機、災難復原、機器移轉、重新安裝 hermes。
> 適用對象：未來的你、其他 AI agent、或任何接手維護的人。

## 0. 讀我之前請先讀

這個文件**是 hermes 備份 v4.1 的官方還原手冊**。如果你不確定備份架構是什麼：
- 簡短版：見 §1 概念模型
- 完整版：見 `trial-and-error/references/by-category/hermes-backup-strategy.md`

如果這份 SOP 跟你看到的實際狀況不一致、**以實際狀況為準**並更新這份文件。

---

## 1. 概念模型（先看這個、再動手）

v4.1 備份架構由**兩層**組成：

```
┌─────────────────────────────────────────────────────────────┐
│  全新空機器（沒有 ~/.hermes/、什麼都沒有）                      │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
 ┌─────────────┐  ┌─────────────────┐
 │ Tier 1      │  │ Tier 2          │
 │ GitHub       │  │ Google Drive     │
 │ (公開 repo)  │  │ (私人 Drive)     │
 │             │  │                  │
 │ 還原這個    │  │ 還原這個         │
 │ 就能跑      │  │ 才能對話歷史      │
 │             │  │                  │
 │ 內容：     │  │ 內容：          │
 │ - skills/  │  │ - .env          │
 │ - agents/  │  │ - auth.json     │
 │ - memories/ │  │ - state.db      │
 │ - config   │  │   (200 MB 對話)  │
 │ - scripts/  │  │ (GPG 加密)      │
 │ - docs/     │  │                  │
 └─────────────┘  └─────────────────┘
```

**Tier 1（GitHub）** 公開、任何人可 clone、**不含真實 secrets**。
**Tier 2（Drive）** 私人、加密、需要你的 Drive OAuth token + GPG passphrase。

**hermes-agent/ 不備份**：它是 `NousResearch/hermes-agent` 的 clone、可以 `git pull` 重建。

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
- [ ] **GPG passphrase**：跟加密時用的完全一致（**這最重要、丟了就完全無法解開 Drive 上 87MB 加密檔**）

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

### Step 2: 設定 rclone config

```bash
rclone config
# 選 n) New remote
# name: hoonsorasus
# Storage: drive
# scope: drive
# 完成後 rclone lsf hoonsorasus: 看得到 Drive 根目錄就成功
```

如果你有舊機器的 `~/documents/rclone.conf`：
```bash
mkdir -p ~/documents
scp old_machine:~/documents/rclone.conf ~/documents/
chmod 600 ~/documents/rclone.conf
rclone lsf hoonsorasus: --config ~/documents/rclone.conf
```

### Step 3: 跑 Tier 1 還原（從 GitHub）

```bash
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-v4.sh -o /tmp/hermes-restore-v4.sh
bash /tmp/hermes-restore-v4.sh tier1 --target ~/.hermes
```

**預期時間**：4-10 分鐘。

### Step 4: 跑 Tier 2 還原（從 Drive 加密檔）

```bash
# passphrase 在哪看你之前怎麼存、預設 ~/Documents/hermes-keys/.hermes_backup_passphrase
bash /tmp/hermes-restore-v4.sh tier2 --target ~/.hermes
```

**這會**：
- 找最新 `secrets-bundle-*.tar.gpg`
- 下載 87 MB
- AES256 解密
- 解 tar 到 `~/.hermes/`：包含 `.env`、`auth.json`、`state.db`
- 自動 chmod 600 所有 secrets 檔案

**預期時間**：1-3 分鐘。

**如果 rclone 報錯**：
- `directory not found` → Drive OAuth 過期或備份沒跑
- `Not Found` → token 過期
- `gpg: decryption failed` → passphrase 錯

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
### 4.2 確認 state.db 有對話歷史
### 4.3 確認 hermes-agent 源碼已安裝
### 4.4 跑一次 backup 確認自動排程會跑
### 4.5 跑一次 Tier 2 確認 Drive 上傳會跑
### 4.6 驗證 hermes 能跑
### 4.7 跑週日驗證腳本

每項具體指令見各小節。

---

## 5. 還原驗證清單（打勾用）

- [ ] `python3 --version` >= 3.11
- [ ] `hermes --version` 有版本
- [ ] `~/.hermes/hermes-agent/run_agent.py` 存在
- [ ] `~/.hermes/config.yaml` 存在、size > 5 KB
- [ ] `~/.hermes/.env` 存在、mode 600、含真實 API key
- [ ] `~/.hermes/auth.json` 存在、mode 600
- [ ] `~/.hermes/state.db` 存在、size > 150 MB
- [ ] `ls ~/.hermes/skills/` 至少有 100+ 個 skill
- [ ] `hermes cron list` 顯示 10+ 個 jobs、含 v4-* 三個
- [ ] `bash ~/.hermes/scripts/hermes-restore-verify.sh` 顯示「✓ 還原驗證成功」
- [ ] `rclone lsf hoonsorasus:hermes-backup/secrets/` 看到 secrets-bundle-*.tar.gpg

---

## 6. 常見問題（FAQ）

### Q1：Drive 上看不到 hermes-backup/ 怎麼辦？
OAuth token 過期、hermes-backup 真的不存在、或 remote 名不對。詳解見 hermes-restore-v4.sh 內建錯誤訊息。

### Q2：GPG passphrase 找不到怎麼辦？
**很慘**、真的無解。預防：把 passphrase 寫進密碼管理器（1Password / Bitwarden）。

### Q3：hermes-agent 是什麼版本？
看 `git log --oneline -5` 在 `~/.hermes/hermes-agent/`。v4.1 不備 hermes-agent 源碼、從 upstream 重建。

### Q4：state.db 比預期小？
1. Drive 上沒抓到最新
2. Tier 2 跑在 Tier 1 之前
3. 真的最近清空

### Q5：rclone crypt 跟明文 Drive 怎麼選？
v4.1 **完全不用 rclone crypt**。所有加密在 client side（gpg AES256）。

### Q6：週日驗證失敗？
看 `/tmp/hermes-restore-verify-*.log`。

### Q7：Vercel token 怎麼申請？
https://vercel.com/account/tokens → Create Token。

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

## 9. 版本紀錄

| 日期 | 版本 | 改動 |
|------|------|------|
| 2026-06-07 | v4.1.0 | 全新撰寫、對應 v4.1 雙雲端架構 |
| 2026-06-06 | v3.0 | 舊版、保留供參考 |

**如果你覺得這份 SOP 有缺漏**：直接編輯補上、commit + push 到 `hermes-config-backup/docs/RESTORE-V4.md`。
