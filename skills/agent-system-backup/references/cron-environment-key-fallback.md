# cron 環境密鑰 fallback 三級鏈(2026-06-10 v4.5.3)

> **本檔對應 SKILL.md §10.10**。把今天 v4.5 → v4.5.3 最關鍵的修補單獨文件化。

## 問題陳述

**v4.5 雙層 GPG 加密設計**:
- Tier 2 加密需要 `USER_KEY`(使用者記住的密碼)
- 用 `backup_passphrase_recovery()` 函式加密 passphrase → 推到 `passphrase-recovery/`

**But**:HERMES cron 環境(`hermes-gateway` scheduler)有 3 個限制:
1. **沒 TTY**(`[[ -t 0 ]]` 必 false → 互動式 prompt 失敗)
2. **沒設 `HERMES_USER_KEY` 環境變數**(cron daemon 啟動時沒繼承這個變數)
3. **不會有 bash_profile 自動 source**

→ **v4.5 設計的 USER_KEY 互動式 fallback 對 cron 完全失效** = **雙層加密對 cron 自動跑來說不存在** = 雖然函式存在但**根本沒跑成功過**。

**發現時間**:2026-06-10 14:xx,**意外觸發 cron 場景測試時**(跑 `bash -c 'unset HERMES_USER_KEY; bash v4 ...'` 模擬 cron)才發現 `backup_passphrase_recovery` 會**跳過 passphrase 備份**。

## 3 級 fallback 鏈設計

按優先順序嘗試 3 種取得 USER_KEY 的方法:

```
┌────────────────────────────────────────────────────┐
│  1. 環境變數 ${HERMES_USER_KEY}                    │
│     ├─ 存在 → 用、記 log                          │
│     └─ 不存在 → 進 2                                │
├────────────────────────────────────────────────────┤
│  2. 環境變數檔 ~/.hermes/config/.hermes-user-key    │
│     ├─ 存在 → cat 讀第一行、記 log                  │
│     └─ 不存在 → 進 3                                │
├────────────────────────────────────────────────────┤
│  3. 互動式 prompt (僅 [[ -t 0 ]])                   │
│     ├─ 有 TTY → read -r -s 隱藏輸入                │
│     └─ 沒 TTY → 警告、跳過這步                       │
└────────────────────────────────────────────────────┘
```

## 實作代碼(兩個函式對稱設計)

### `backup_passphrase_recovery()`(v4 備份端)

```bash
backup_passphrase_recovery() {
  local passphrase_file="$HOME/Documents/hermes-keys/.hermes_backup_passphrase"
  local user_key_env_file="$HOME/.hermes/config/.hermes-user-key"
  local user_key="${HERMES_USER_KEY:-}"

  # 從環境變數檔讀（cron 場景）
  if [[ -z "$user_key" ]] && [[ -f "$user_key_env_file" ]]; then
    user_key=$(cat "$user_key_env_file" 2>/dev/null | head -1)
    if [[ -n "$user_key" ]]; then
      log "USER_KEY 從 $user_key_env_file 讀取"
    fi
  fi

  if [[ -z "$user_key" ]]; then
    if [[ -t 0 ]]; then
      # 互動式 prompt
      ...
    else
      warn "非互動式模式且 HERMES_USER_KEY 未設、跳過 passphrase 備份"
      return 0
    fi
  fi

  # 用 $user_key 加密
  gpg --batch --yes --pinentry-mode loopback \
    --symmetric --cipher-algo AES256 \
    --passphrase "$user_key" \
    --output "$recovery_gpg" \
    "$passphrase_file"
}
```

### `recover_passphrase_from_drive()`(v4 還原端)

```bash
recover_passphrase_from_drive() {
  # ... 1. 驗證 Drive 連線、2. 找最新 recovery、3. 下載 ...
  local user_key=""

  # 1. 環境變數
  if [[ -n "${HERMES_USER_KEY:-}" ]]; then
    user_key="$HERMES_USER_KEY"
    log "USER_KEY 從 HERMES_USER_KEY 環境變數讀取"
  # 2. 環境變數檔
  elif [[ -f "$HOME/.hermes/config/.hermes-user-key" ]]; then
    user_key=$(cat "$HOME/.hermes/config/.hermes-user-key" 2>/dev/null | head -1)
    if [[ -n "$user_key" ]]; then
      log "USER_KEY 從 ~/.hermes/config/.hermes-user-key 讀取"
    fi
  # 3. 互動式
  elif [[ -t 0 ]]; then
    read -r -s -p "USER_KEY: " user_key
    echo ""
  else
    err "非互動式、需 HERMES_USER_KEY 或 ~/.hermes/config/.hermes-user-key"
    return 1
  fi

  # 用 $user_key 解密
  gpg --batch --yes --pinentry-mode loopback \
    --passphrase "$user_key" \
    --decrypt "$tmp_gpg" > "$PASSPHRASE_FILE"
}
```

## 建立環境變數檔 SOP

```bash
# 建立(只跑一次)
echo "your_user_key_here" > ~/.hermes/config/.hermes-user-key
chmod 600 ~/.hermes/config/.hermes-user-key

# 驗證
ls -la ~/.hermes/config/.hermes-user-key
# 預期: -rw------- 1 ... 12 bytes
```

**為什麼用 `~/.hermes/config/` 而不是 `~/.hermes/secrets/`**:
- `~/.hermes/config/` 是 hermes 標準配置目錄
- `config/.hermes-user-key` chmod 600 仍受 `HERMES_HOME` 包圍,只有同使用者可讀
- 不放 `/etc/` 避免 root 讀取風險

**為什麼不用 `pass`(GPG-based password manager):
- `pass` 需要 GPG keyring,N100 headless 環境維護成本高
- USER_KEY 只需一組、不像 pass 設計給多帳號管理
- 簡單 `chmod 600` 文字檔對單一密碼夠安全

## cron 環境驗證(2026-06-10 跑過)

```bash
# 模擬 cron(無 env var、無 TTY)
unset HERMES_USER_KEY
bash -c '
HERMES_HOME="$HOME/.hermes"
user_key="${HERMES_USER_KEY:-}"
if [[ -z "$user_key" ]] && [[ -f "$HOME/.hermes/config/.hermes-user-key" ]]; then
  user_key=$(cat "$HOME/.hermes/config/.hermes-user-key" 2>/dev/null | head -1)
  echo "USER_KEY 從環境變數檔讀取、長度=${#user_key}"
fi
'
# 預期輸出: USER_KEY 從環境變數檔讀取、長度=11
```

## 推廣

**If** 設計任何「**在 cron 環境下需要密鑰的腳本**」 **Then** 必加這 3 級 fallback:

1. 環境變數(最常見、最簡單)
2. 環境變數檔(`chmod 600` 文字檔、給 cron 用)
3. 互動式 prompt(僅 `[[ -t 0 ]]` 才顯示、避免 cron 卡住)

**千萬不要**只設計「互動式 prompt」就以為完成 —— 在 cron 環境必 fail。
**千萬不要**假設 cron 會繼承 `.bashrc` 的 env 設定 —— cron daemon 啟動時通常沒讀 .bashrc。
**千萬不要**把密碼明文放在 script 內 —— 用變數 + 環境變數檔。

## 修補時間軸

- **2026-06-10 14:00** — v4.5 設計完成、但只想到互動式 prompt
- **2026-06-10 14:14** — 修 v4-restore 加 `HERMES_USER_KEY` 環境變數 fallback(L2 試誤)
- **2026-06-10 16:20** — 發現 cron 場景**仍**會 fail(v4.5.2 → v4.5.3 修補本檔案)
- **2026-06-10 16:22** — 意外觸發真實 cron 環境測試、驗證 fallback 通
