# 赫米斯備份 — Drive 端還原指南

> **這個檔案在 Drive `hoonsorasus:hermes-backup/` 根目錄**
> 寫給:**接手的人**、**未來的你**、**未來的 AI agent**
> **不需要任何 hermes 知識就能開始還原**

## 你是誰?看哪一段

- **「我新裝機、要把 hermes 還原回來」** → 看 §A
- **「我拿到 Drive 連結、但不知道 GPG passphrase」** → 看 §B
- **「我是 AI、要幫使用者還原」** → 看 §C

---

## §A. 完整異機還原(10-20 分鐘)

### 前置需求(全新主機要裝的)

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y python3 python3-pip git curl rclone gnupg
```

### 步驟

```bash
# 1. 裝 hermes-agent 本體
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. 從 1Password 複製 rclone.conf 到 ~/documents/
mkdir -p ~/documents
# (從 1Password 拉 rclone.conf 條目內容、貼到 ~/documents/rclone.conf)
chmod 600 ~/documents/rclone.conf

# 3. 驗證 Drive 連線
rclone lsf hoonsorasus:hermes-backup --config ~/documents/rclone.conf
# 預期看到: DRIVE-RESTORE.md  secrets/  passphrase-recovery/

# 4. 從 GitHub 拉還原腳本 + 跑 Tier 1
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-v4.sh -o /tmp/r.sh
bash /tmp/r.sh tier1

# 5. 跑 Tier 2(從 Drive 雙層解密)
#    從 1Password 找「hermes-backup USER_KEY」條目、複製 USER_KEY
HERMES_USER_KEY="<貼上 USER_KEY>" bash /tmp/r.sh tier2
# 或互動式(會問 USER_KEY):
bash /tmp/r.sh tier2

# 6. 跑週日驗證
curl -fsSL https://raw.githubusercontent.com/hoonsoropenclaw/hermes-config-backup/main/scripts/hermes-restore-verify.sh -o /tmp/v.sh
bash /tmp/v.sh

# 7. 確認 hermes 啟動正常
hermes status
```

**完成**!

---

## §B. 不知道 GPG passphrase 的還原(2026-06-10 v4.5 設計)

### 你需要 USER_KEY(從 1Password 找)

USER_KEY 應該記在 1Password 的「**hermes-backup USER_KEY**」條目。

**找不到 USER_KEY 怎麼辦**:
- 找舊電腦看 ~/.bash_history 有沒有 `HERMES_USER_KEY=...` 的記錄
- 找其他密碼管理器有沒有存
- **真的找不到** → 必須重跑 v4.5 備份、重新生成 USER_KEY(聯絡 hoonsoropenclaw)

### 用 USER_KEY 還原

```bash
# 把 USER_KEY 設成環境變數
export HERMES_USER_KEY="<USER_KEY 內容>"

# 跑 Tier 2 還原(自動從 Drive 抓 passphrase-recovery)
bash /tmp/r.sh tier2
```

**腳本內部會做**:
1. 偵測到 `~/Documents/hermes-keys/.hermes_backup_passphrase` 不存在
2. 從 Drive `passphrase-recovery/` 下載最新加密檔
3. 用 USER_KEY 解密 → 拿到 GPG passphrase(64 字元)
4. 把 GPG passphrase 放回本地路徑
5. 從 Drive `secrets/` 下載 `secrets-bundle-*.tar.gpg` (~125 MB)
6. 用 GPG passphrase 解密 → 拿到 .env/auth.json/state.db
7. 修權限 (600)

### USER_KEY 強度建議

- ✅ 12+ 字元
- ✅ 跟 1Password 主密碼相同(最好記)
- ❌ 不要跟 GPG passphrase 相同(兩層加密失去意義)

---

## §C. AI 助手:幫使用者還原的決策樹

```
使用者:「我想在新機器還原 hermes」
↓
問使用者這 3 個問題:
  1. 有 1Password 嗎? (或任何密碼管理器)
     → 沒有 → 教他們安裝 + 複製 USER_KEY
  2. 知道「hermes-backup USER_KEY」條目嗎?
     → 不知道 → 讓他們找密碼管理器或重設 USER_KEY
  3. 有 rclone.conf 嗎?
     → 沒有 → 從舊機器複製或重建
↓
協助執行 §A 的 7 個步驟
↓
驗證 hermes status
↓
告訴使用者完成
```

### AI 跑還原時**預期看到的輸出**(用於判斷成功/失敗)

成功:
```
[15:14:25] === Tier 2: Drive secrets decrypt ===
[15:14:25] ⚠ 找不到本地 passphrase 檔
[15:14:25] ⚠ 嘗試從 Drive passphrase-recovery/ 還原...
[15:14:29] 找到 Drive passphrase-recovery: passphrase-recovery-XXXX.gpg
[15:14:33] USER_KEY 從 HERMES_USER_KEY 環境變數讀取（跳過互動 prompt）
[15:14:33] ✓ Passphrase 還原成功
[15:19:03] ✓   所有 secrets 檔案權限 600
[15:19:06] ✓ Tier 2 完成
```

失敗(USER_KEY 錯):
```
[15:14:33] ✗ USER_KEY 錯誤、解密失敗
gpg: decryption failed
```

失敗(GPG passphrase 跟 USER_KEY 不對應、v4.5 不該發生):
```
gpg: bad session key
```

失敗(Drive 連不到):
```
Failed to copy: directory not found
```

---

## 🔐 安全提醒

- 這層 Drive 資料夾**請勿設為公開分享**(雖然內容加密、但避免不必要風險)
- **不要把 passphrase-recovery/ 加密檔跟 USER_KEY 放在同一個地方**(兩層加密失去意義)
- USER_KEY 跟 GPG passphrase 必須不同

## 版本紀錄

| 日期 | 版本 | 改動 |
|------|------|------|
| 2026-06-10 | v4.5.0 | v4.5 雙層 GPG 加密對應、AI debug 指南、3 個角色入口 |

---

**完整備份設計與策略**:`https://github.com/hoonsoropenclaw/hermes-config-backup/blob/main/docs/RESTORE-V4.md`
**策略文件**:`https://github.com/hoonsoropenclaw/hermes-config-backup/blob/main/skills/trial-and-error/references/by-category/hermes-backup-strategy.md`
