#!/usr/bin/env bash
# verify-recovery-chain.sh — 端到端驗證 v4.5 雙層 GPG 加密解密鏈
#
# 用途:確認從「Drive 加密 passphrase-recovery」→「本地 passphrase」→「secrets-bundle 解密」
#       整條鏈通,並用 md5 對比保證內容完全一致。
#
# 觸發時機:
#   - 設計/修改 v4 / v4-restore 腳本後
#   - 異機還原實際操作後
#   - 每季健康檢查(預防 USER_KEY 變了忘記更新)
#
# 用法:
#   HERMES_USER_KEY="<your_key>" bash verify-recovery-chain.sh
#
# 輸出:
#   - PASS 鏈通、可以信賴
#   - FAIL 哪一層斷了、需要修
#
# 設計:2026-06-10 14:14 D 方案驗證全鏈通後寫成 script

set -euo pipefail

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; CYN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GRN}[$(date +%H:%M:%S)] ✓${NC} $*"; }
warn() { echo -e "${YLW}[$(date +%H:%M:%S)] ⚠${NC} $*"; }
err()  { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $*" >&2; }

# 設定
PASSPHRASE_FILE="$HOME/Documents/hermes-keys/.hermes_backup_passphrase"
TMP_DIR=$(mktemp -d /tmp/verify-recovery-XXXXXX)
trap "rm -rf $TMP_DIR" EXIT

DRIVE_REMOTE="hoonsorasus:hermes-backup"
PASSPHRASE_RECOVERY_DIR="passphrase-recovery"
SECRETS_DIR="secrets"

FAILED=0

# 0. 前置檢查
log "=== 前置檢查 ==="
if [[ -z "${HERMES_USER_KEY:-}" ]]; then
  err "請設定 HERMES_USER_KEY 環境變數"
  err "  export HERMES_USER_KEY=\"<你的 USER_KEY>\""
  exit 1
fi
ok "HERMES_USER_KEY 已設定 (長度: ${#HERMES_USER_KEY} 字元)"

# 警告:USER_KEY 強度檢查
if [[ ${#HERMES_USER_KEY} -lt 16 ]]; then
  warn "USER_KEY 短於 16 字元,對抗字典攻擊弱,建議升級到 1Password 主密碼強度"
fi

# 1. 備份原版 passphrase md5(如果存在)
log "=== 步驟 1: 備份原版 passphrase md5 ==="
if [[ -f "$PASSPHRASE_FILE" ]]; then
  ORIGINAL_MD5=$(md5sum "$PASSPHRASE_FILE" | awk '{print $1}')
  ok "原版 passphrase md5: $ORIGINAL_MD5"
else
  warn "本地無 passphrase 檔(模擬全新主機情況)"
  ORIGINAL_MD5=""
fi

# 2. 從 Drive passphrase-recovery/ 下載最新加密檔
log "=== 步驟 2: 從 Drive 下載 passphrase-recovery ==="
LATEST=$(rclone lsf "$DRIVE_REMOTE/$PASSPHRASE_RECOVERY_DIR/" --files-only 2>/dev/null \
  | grep 'passphrase-recovery-.*\.gpg' | sort -r | head -1)
if [[ -z "$LATEST" ]]; then
  err "Drive $DRIVE_REMOTE/$PASSPHRASE_RECOVERY_DIR 上找不到 passphrase-recovery-*.gpg"
  err "  請先跑 hermes-backup-v4.sh 觸發 backup_passphrase_recovery()"
  exit 1
fi
ok "找到 Drive passphrase-recovery: $LATEST"

rclone copy "$DRIVE_REMOTE/$PASSPHRASE_RECOVERY_DIR/$LATEST" "$TMP_DIR/" 2>&1 | tail -2
if [[ ! -f "$TMP_DIR/$LATEST" ]]; then
  err "下載失敗"
  exit 1
fi
mv "$TMP_DIR/$LATEST" "$TMP_DIR/recovery.gpg"
chmod 600 "$TMP_DIR/recovery.gpg"

# 3. 用 USER_KEY 解開 → 放暫存(測試、不覆蓋本地)
log "=== 步驟 3: USER_KEY 解開 passphrase-recovery ==="
RECOVERED_PASSPHRASE="$TMP_DIR/recovered-passphrase"
if ! gpg --batch --yes --pinentry-mode loopback \
    --passphrase "$HERMES_USER_KEY" \
    --decrypt "$TMP_DIR/recovery.gpg" > "$RECOVERED_PASSPHRASE" 2>/tmp/gpg-err.log; then
  err "USER_KEY 錯誤、解密失敗"
  cat /tmp/gpg-err.log | head -3
  exit 1
fi
chmod 600 "$RECOVERED_PASSPHRASE"
RECOVERED_MD5=$(md5sum "$RECOVERED_PASSPHRASE" | awk '{print $1}')
ok "解出 passphrase md5: $RECOVERED_MD5"

# 4. 對比 md5
log "=== 步驟 4: 對比 md5 ==="
if [[ -n "$ORIGINAL_MD5" ]]; then
  if [[ "$ORIGINAL_MD5" == "$RECOVERED_MD5" ]]; then
    ok "md5 一致: 鏈通 ✓"
  else
    err "md5 不一致!"
    err "  原版:   $ORIGINAL_MD5"
    err "  還原版: $RECOVERED_MD5"
    FAILED=1
  fi
else
  warn "跳過 md5 對比(本地無原版 passphrase)"
  warn "手動驗證: cat $RECOVERED_PASSPHRASE 應回 64 字元高熵密碼"
fi

# 5. 從 Drive secrets/ 下載最新 secrets-bundle
log "=== 步驟 5: 從 Drive 下載 secrets-bundle ==="
LATEST_SECRETS=$(rclone lsf "$DRIVE_REMOTE/$SECRETS_DIR/" --files-only 2>/dev/null \
  | grep 'secrets-bundle-.*\.tar\.gpg' | sort -r | head -1)
if [[ -z "$LATEST_SECRETS" ]]; then
  err "Drive $DRIVE_REMOTE/$SECRETS_DIR 上找不到 secrets-bundle-*.tar.gpg"
  exit 1
fi
ok "找到 Drive secrets-bundle: $LATEST_SECRETS"

rclone copy "$DRIVE_REMOTE/$SECRETS_DIR/$LATEST_SECRETS" "$TMP_DIR/" 2>&1 | tail -2
mv "$TMP_DIR/$LATEST_SECRETS" "$TMP_DIR/secrets.tar.gpg"
chmod 600 "$TMP_DIR/secrets.tar.gpg"

# 6. 用 recovered passphrase 解 secrets-bundle
log "=== 步驟 6: 解 secrets-bundle ==="
if ! gpg --batch --yes --pinentry-mode loopback \
    --passphrase-file "$RECOVERED_PASSPHRASE" \
    --decrypt "$TMP_DIR/secrets.tar.gpg" > "$TMP_DIR/secrets.tar" 2>/tmp/gpg-err.log; then
  err "recovered passphrase 錯誤、解密失敗"
  cat /tmp/gpg-err.log | head -3
  exit 1
fi
chmod 600 "$TMP_DIR/secrets.tar"

# 7. 確認 tar 內容有 .env / auth.json / state.db
log "=== 步驟 7: 確認 tar 內容 ==="
tar -tf "$TMP_DIR/secrets.tar" 2>/dev/null | head -10

if tar -tf "$TMP_DIR/secrets.tar" | grep -qE '^\.env$'; then
  ok "secrets-bundle 包含 .env"
else
  err "secrets-bundle 缺少 .env"
  FAILED=1
fi
if tar -tf "$TMP_DIR/secrets.tar" | grep -qE '^auth\.json$'; then
  ok "secrets-bundle 包含 auth.json"
else
  err "secrets-bundle 缺少 auth.json"
  FAILED=1
fi
if tar -tf "$TMP_DIR/secrets.tar" | grep -qE '^state\.db$'; then
  ok "secrets-bundle 包含 state.db"
else
  err "secrets-bundle 缺少 state.db"
  FAILED=1
fi

# 8. 結尾
echo ""
echo "========================================"
if [[ $FAILED -eq 0 ]]; then
  ok "全鏈驗證 PASS ✓"
  echo ""
  echo "  Drive passphrase-recovery → USER_KEY → 本地 passphrase → secrets-bundle"
  echo "  整條鏈通、可信賴"
  exit 0
else
  err "全鏈驗證 FAIL ✗"
  echo ""
  echo "  請檢查上述 FAILED 步驟、不要在失敗狀態下進行異機還原"
  exit 1
fi
