# Hermes v4.5 備份(Google Drive 版本)

> **這是 hoonsoropenclaw 的赫米斯全狀態加密備份所在。**
> **異機還原用**,完整還原需要 hermes-agent 源碼、state.db、.env 等敏感/大型資料。
> **公開版(不含敏感)在 https://github.com/hoonsoropenclaw/hermes-config-backup**

**最後更新**:2026-06-10(v4.5 雙層 GPG 加密)

## 📁 資料夾結構(v4.5)

```
hermes-backup/                                ← 你在這層
├── DRIVE-RESTORE.md                          ← 這份 Drive 端還原說明(給 AI/接手者)
├── secrets/                                  ← GPG 加密的 .env + auth.json + state.db
│   ├── secrets-bundle-20260610_061609Z.tar.gpg    (125 MB)
│   ├── secrets-bundle-20260607_155646Z.tar.gpg
│   └── ... (過去備份)
└── passphrase-recovery/                      ← v4.5 新增:GPG 加密的 GPG passphrase
    └── passphrase-recovery-20260610_071248Z.gpg  (156 bytes)
```

**Tier 1(公開)在 GitHub**:`https://github.com/hoonsoropenclaw/hermes-config-backup`
**Tier 2(私人加密)在這層 Drive**

## 🚨 你需要知道的事(必讀)

### 你不需要知道 GPG passphrase

v4.5 設計讓你**只記一組 USER_KEY**(通常 = 1Password 主密碼)。整條還原鏈:

```
USER_KEY (你記住)
  ↓ 解 passphrase-recovery/*.gpg
GPG passphrase (64字元自動產生、不該人記)
  ↓ 解 secrets/*.tar.gpg
.env + auth.json + state.db (hermes 可用)
```

### USER_KEY 必須能拿到

**3 個地方找**:
1. 1Password「hermes-backup USER_KEY」條目
2. 密碼管理器 (Bitwarden / LastPass 等)
3. **找不到的話** → 真的無解、必須重跑 v4.5 backup 重新生成

### 完整異機還原流程(給 AI 看)

```bash
# 1. 全新主機:裝 hermes-agent
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. 設 rclone config(從密碼管理器複製舊機器的 rclone.conf 到 ~/documents/)
mkdir -p ~/documents && chmod 700 ~/documents
# 從 1Password 複製 rclone.conf 條目到 ~/documents/rclone.conf
chmod 600 ~/documents/rclone.conf
rclone lsf hoonsorasus:hermes-backup/ --config ~/documents/rclone.conf

# 3. 跑 Tier 1 還原(從 GitHub 拉 skills/memories/profiles)
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-v4.sh -o /tmp/r.sh
bash /tmp/r.sh tier1

# 4. 跑 Tier 2 還原(從 Drive 雙層解密 secrets)
HERMES_USER_KEY="<從 1Password 找>" bash /tmp/r.sh tier2
# 自動:
#   a. 從 Drive 下載 passphrase-recovery/*.gpg
#   b. 用 USER_KEY 解 → 拿到 GPG passphrase
#   c. 從 Drive 下載 secrets-bundle-*.tar.gpg
#   d. 用 GPG passphrase 解 → 拿到 .env/auth.json/state.db
#   e. chmod 600

# 5. 跑還原驗證
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-verify.sh -o /tmp/v.sh
bash /tmp/v.sh

# 6. 確認 hermes 能跑
hermes status
```

**預期總時間**:10-20 分鐘(含 125 MB 下載)

## 🆘 失敗時怎麼辦(AI debug 指南)

| 失敗症狀 | 可能原因 | 解法 |
|---|---|---|
| `rclone: command not found` | 新主機沒裝 rclone | `apt install rclone` 或 `brew install rclone` |
| `directory not found` | Drive OAuth 過期 或 路徑錯 | `rclone config` 重新設定;或加 `-v` 看詳細 |
| `Permission denied (publickey)` | rclone.conf 沒 chmod 600 | `chmod 600 ~/documents/rclone.conf` |
| `gpg: decryption failed` | USER_KEY 錯 | 從 1Password 重找 |
| `bad session key` | 加密時跟 USER_KEY 不一致 | v4.5 不該發生;若發生就是備份時 USER_KEY 沒記對 |
| `bad signature` | 加密檔被竄改 | 從舊備份重抓(找 `secrets-bundle-20260607_*.tar.gpg`) |
| `.env 內全是 ***` | .env 是範本不是真實 | 跑 tier2 重新還原 |
| `state.db size < 150 MB` | 抓到舊備份 | 確認 secrets/ 內最新時間戳 |
| `hermes status` 看不到 LLM key | .env 沒真實值 | grep `MINIMAX_API_KEY=sk-` 確認 |

## 🔐 安全注意事項

- **這層 Drive 資料夾是加密的**(GPG AES256, client-side),但 Drive 端是明文
- 本檔(`DRIVE-RESTORE.md`)是**明文**的(讓沒 rclone config 的人也能看到說明)
- 真正的敏感資料(.env、state.db、token)都在 GPG 加密的 tar.gz 內
- **請勿把本資料夾設為公開分享** —— 雖然內容是加密的,但避免不必要風險
- **不要把 passphrase-recovery/ 加密檔跟 USER_KEY 放在同一個地方** —— 兩層加密失去意義

## 📞 還原有問題時

1. 看 hermes-restore-v4.sh 印出的錯誤訊息
2. 看 GitHub 上 `docs/RESTORE-V4.md` 詳細步驟
3. 看 `trial-and-error` skill:`references/by-category/hermes-backup-strategy.md`

## 版本紀錄

| 日期 | 版本 | 改動 |
|------|------|------|
| 2026-06-10 | v4.5.0 | 雙層 GPG 加密 + USER_KEY 自動還原 + DRIVE-RESTORE.md |
| 2026-06-06 | v2.x | 舊版、保留供參考 |

---

**你看到這份檔案、但不知道 USER_KEY 的話**:
- 不要慌張
- 1Password 找「hermes-backup USER_KEY」條目
- 找 hermes-restore-v4.sh 跑 tier1 + tier2
- 完整說明:https://github.com/hoonsoropenclaw/hermes-config-backup/blob/main/docs/RESTORE-V4.md
