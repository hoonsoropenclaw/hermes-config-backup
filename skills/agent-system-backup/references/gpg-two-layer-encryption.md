# GPG 雙層加密 + 異機還原完整設計

> **2026-06-10 v4.5 新增**。任何「加密檔推雲端」設計必讀。
> 對應 SKILL.md 第 10.2 / 10.2.1 段。

## 核心觀念:Recovery Chain 必須形成迴路

**單靠本地金鑰 = 不是備份**。如果金鑰跟加密檔在同一台機器、同一個 failure domain,機器壞掉就全失。

```
加密檔:雲端(Google Drive)
金鑰:本機(~/Documents/hermes-keys/)
金鑰的金鑰(USER_KEY):使用者腦中
```

3 個不同 failure domain = 任何單一點失敗都不會全失。

## 為何 GPG passphrase 不用手動設定

2026-06-07 v4 自動跑 `--rotate` 產生 64 字元高熵密碼,存在固定路徑 `~/Documents/hermes-keys/.hermes_backup_passphrase` (mode 600)。

**不要在對話打密碼**(就算使用者要求)——這違反安全設計原則,且任何未來 session 看到對話記錄都能拿到。

`hermes-secrets-encrypt.sh` 用 `gpg --batch --passphrase-file "$PASSPHRASE_FILE" --decrypt/encrypt` 從檔讀,完全不需要互動 prompt。

**驗證命令**:`cat ~/Documents/hermes-keys/.hermes_backup_passphrase | wc -c` 應回 65(含換行)。

## v4.5 雙層加密設計

### 加密流程(backup 端)

```
┌─────────────────────────────────────────────────┐
│ Tier 2: hermes-secrets-encrypt.sh               │
│                                                 │
│  收集 .env + auth.json + state.db              │
│         ↓                                       │
│  tar -cf secrets-bundle-<ts>.tar                │
│         ↓                                       │
│  gpg --symmetric --passphrase-file $PASS        │
│         ↓                                       │
│  secrets-bundle-<ts>.tar.gpg → Drive secrets/   │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ v4.5 追加: backup_passphrase_recovery()         │
│                                                 │
│  讀 ~/Documents/hermes-keys/.hermes_backup_     │
│  passphrase                                     │
│         ↓                                       │
│  互動式問 USER_KEY(或讀 $HERMES_USER_KEY 環境) │
│         ↓                                       │
│  gpg --symmetric --passphrase "$USER_KEY"       │
│         ↓                                       │
│  passphrase-recovery-<ts>.gpg → Drive recovery/  │
└─────────────────────────────────────────────────┘
```

### 解密流程(restore 端)

```
hermes-restore-v4.sh tier2
  ↓
本地有 $PASSPHRASE_FILE?
  ├─ YES → 直接解 secrets-bundle-*.tar.gpg
  └─ NO  → recover_passphrase_from_drive()
              ↓
            Drive passphrase-recovery/ 下載最新 .gpg
              ↓
            互動式問 USER_KEY
              ↓
            gpg --passphrase "$USER_KEY" --decrypt
              ↓
            放回 ~/Documents/hermes-keys/.hermes_backup_passphrase (mode 600)
              ↓
            再解 secrets-bundle-*.tar.gpg
```

## USER_KEY 規則

1. **必須跟 GPG passphrase 不同**——兩層加密才有意義
2. **建議 = 1Password / Bitwarden 主密碼**——最容易記
3. **記在 1Password 的 `hermes-backup USER_KEY` 條目**——重要!1Password 壞了 USER_KEY 也沒了
4. **每季驗證一次**:`gpg --batch --pinentry-mode loopback --passphrase "$USER_KEY" --decrypt <任何 passphrase-recovery-*.gpg> > /dev/null` 應該成功

## 異機還原完整 SOP

### 全新主機(從零開始)

```bash
# 1. 安裝 hermes-agent(從 GitHub: NousResearch/hermes-agent)
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. 準備 rclone config
# 從 1Password 條目 'rclone.conf hermes' 拿 → 放 ~/documents/rclone.conf

# 3. 跑 Tier 1(從 GitHub 拉 skills/memories/profiles)
hermes-restore-v4.sh tier1

# 4. 跑 Tier 2(從 Drive 解密 secrets)
hermes-restore-v4.sh tier2
# 自動:
#   - 從 Drive secrets/ 下載 .tar.gpg
#   - 偵測本地無 passphrase → 從 Drive passphrase-recovery/ 還原
#   - 互動式問 USER_KEY
#   - GPG 解密放回 ~/Documents/hermes-keys/.hermes_backup_passphrase
#   - 用 passphrase 解 .tar.gpg → 拿到 .env/auth.json/state.db

# 5. 跑 Tier 3(可選,從本地 Y 槽)
hermes-restore-v4.sh tier3
```

### 你需要從 1Password 帶過去的東西

| 項目 | 1Password 條目 | 備註 |
|---|---|---|
| **USER_KEY** | `hermes-backup USER_KEY` | 必帶、互動式輸入 |
| **rclone.conf** | `rclone.conf hermes` | 必帶、放 ~/documents/rclone.conf |
| Telegram bot token | 自動含在 secrets/ 內 | 由 Tier 2 自動還原 |
| 各種 API key | 自動含在 secrets/ 內 | 由 Tier 2 自動還原 |

### 完全忘記 USER_KEY 的災難情境

- **Drive 上 130MB 加密 secrets 永遠解不開**
- **唯一解法**:
  1. 重跑 `hermes-secrets-encrypt.sh --rotate` 產新 GPG passphrase
  2. **重新設定所有 .env 的 API key**(31 個 key 都要重抓)
  3. 重新跑 v4 backup
- **預防**:
  1. USER_KEY 記在 1Password
  2. 額外複製一份加密的 passphrase-recovery 到實體離線 USB(3rd layer 防護)

## 修改腳本時的注意事項

### 加新 secret 類型時

`hermes-secrets-encrypt.sh` 第 30-50 行收集 secrets。要加新類型:

1. 加到 collect 函式的 file glob
2. **確認新檔案**:
   - 權限 600
   - 不在 staging 公開版(GitHub 公開 repo)內
   - 不會讓 tar 爆到 200MB+(Drive API 限制)

### 加新 Drive 目錄時

如果未來要加 `passphrase-recovery-2/`(例如分多個機器)或 `encrypted-volumes/`:

1. 改 `RCLONE_REMOTE` 變數
2. 改 `hermes-restore-v4.sh tier2` 的 recovery 邏輯
3. 同步更新本文件

### 改 USER_KEY prompt 邏輯時

`recover_passphrase_from_drive()` 函式第 4 段是 USER_KEY 取得邏輯(2026-06-10 v4.5.1 確認支援三種)。

**支援三種取得方式**(2026-06-10 v4.5.1 確認):
1. **環境變數** `$HERMES_USER_KEY`(給 cron / CI 模式用)
2. **互動式 prompt**(`[[ -t 0 ]]` 判斷,給人手跑用)
3. **失敗**:完全非互動式且無環境變數 → 報錯退出

**支援環境變數的代價**:
- log 可能暴露 USER_KEY(若 echo 整個環境)
- **緩解**:`$HERMES_USER_KEY` 從 cron 環境變數讀、**不**從 command line argument 讀(command line 在 `ps` 看到)
- 驗證:2026-06-10 14:14 跑 `HERMES_USER_KEY=xm3fm065ji6 bash hermes-restore-v4.sh tier2` 成功、整條鏈從 Drive 加密 passphrase → 還原本地 → 解 secrets-bundle 都通、md5 對比一致

**USER_KEY 強度建議**(2026-06-10 14:14 驗證):
- 12 字元純英文數字(`xm3fm065ji6`)約 2^72 熵,對抗暴力破解 OK
- 但**對抗字典攻擊極弱**——常見密碼前 1000 個就有
- **強烈建議** = 1Password 主密碼強度(20+ 字元、含特殊字元)
- 至少要 16+ 字元、不能是常見密碼

### 異機還原全鏈 md5 驗證 SOP(2026-06-10 14:14 驗證)

**端到端驗證(確認整條恢復鏈通)**:
```bash
# 1. 備份原版 passphrase
md5sum /tmp/passphrase.backup
#  預期: c0c6ead9a96d2a1230c3335b629a948f

# 2. 跑 hermes-restore-v4.sh tier2(會自動還原 passphrase + 解 secrets)
HERMES_USER_KEY="<your_key>" bash hermes-restore-v4.sh tier2

# 3. 比對新還原的 passphrase md5 跟原版
md5sum ~/Documents/hermes-keys/.hermes_backup_passphrase
#  預期: c0c6ead9a96d2a1230c3335b629a948f(完全一致)

# 4. 確認 secrets 檔案權限 600
ls -la ~/.hermes/{.env,auth.json,state.db}
#  預期: -rw------- root root(或 hoonsoropenclaw)
```

**如果 md5 不一致**:
- 環境變數拼錯大小寫
- GPG passphrase 跟 USER_KEY 寫反
- `.gpg` 檔損壞(重新跑 backup)
- Drive 端檔案被覆蓋(檢查 Drive 上的 mtime)

**If** 異機還原後 md5 不一致
**Then** **不要**繼續解 secrets-bundle——先確認是哪一層錯的、避免解出錯誤的 .env
