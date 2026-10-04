#!/usr/bin/env bash
# hermes-secrets-encrypt.sh (v4 Tier 2 配套)
# 把 ~/.hermes 內的 secrets（.env、auth.json 等）打包加密成 .gpg
# 加密檔推到 Drive Tier 2（crypt_hermes:hermes-backup/secrets/）
# 還原時用 hermes-restore-v4.sh 的 tier2 步驟解開
#
# 設計原則：
#   1. 雙目錄分離（加密檔 + passphrase 不在同一目錄）
#   2. AES256 + S2K mode 3 + s2k-count 65011792（OpenPGP 建議）
#   3. 加密後產出檔 chmod 600（gpg 預設 644 要修）
#   4. 明文 shred -u -z -n 3 刪除
#   5. Drive 上用時間戳命名（每次備份留歷史）
#   6. 預設不解密、不顯示 passphrase 內容
#
# 使用：
#   hermes-secrets-encrypt.sh                    # 加密 ~/.hermes/.env + auth.json
#   hermes-secrets-encrypt.sh --upload-drive     # 加密後推到 Drive
#   hermes-secrets-encrypt.sh --verify           # 加密後用 decrypt 驗證一致性
#   hermes-secrets-encrypt.sh --rotate           # 重新生成 passphrase

set -euo pipefail

# === 設定 ===
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

# 加密 staging 目錄（cache 目錄、語意合理、跟 ~/Documents 隔離）
SECRETS_OUTPUT_DIR="$HOME/.cache/hermes-secrets-staging"

# Passphrase 位置（**嚴格跟加密檔分開**）
PASSPHRASE_DIR="$HOME/Documents/hermes-keys"
PASSPHRASE_FILE="$PASSPHRASE_DIR/.hermes_backup_passphrase"

# Drive 設定（v4.1 Tier 2）
# 改用明文 Drive (`hoonsorasus:`) + client-side GPG 加密
# 不用 rclone crypt layer（對 Drive API 不友善、會拖慢 10x）
# 加密在 client side 做完、Drive 上看到的就是 .gpg 檔案
RCLONE_CONF="$HOME/documents/rclone.conf"
RCLONE_REMOTE="hoonsorasus:hermes-backup/secrets"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%SZ)

# === 顏色 ===
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; CYN='\033[0;36m'; NC='\033[0m'

# === 工具檢查 ===
check_tools() {
  command -v gpg >/dev/null 2>&1 || { echo -e "${RED}ERROR: gpg not found${NC}"; exit 1; }
  command -v rclone >/dev/null 2>&1 || { echo -e "${RED}ERROR: rclone not found${NC}"; exit 1; }
  command -v python3 >/dev/null 2>&1 || { echo -e "${RED}ERROR: python3 not found${NC}"; exit 1; }
  if ! command -v shred >/dev/null 2>&1; then
    echo -e "${YLW}WARN: shred not found (will use rm -P)${NC}"
  fi
}

# === Passphrase 管理 ===
ensure_passphrase() {
  if [[ -f "$PASSPHRASE_FILE" ]]; then
    echo -e "${CYN}OK: Using existing passphrase: ${PASSPHRASE_FILE}${NC}"
  else
    echo -e "${YLW}First run, generating 64-char high-entropy passphrase${NC}"
    mkdir -p "$PASSPHRASE_DIR"
    chmod 700 "$PASSPHRASE_DIR"
    python3 -c "
import secrets, string
alphabet = string.ascii_letters + string.digits + '!@#\$%^&*-_=+'
pp = ''.join(secrets.choice(alphabet) for _ in range(64))
with open('$PASSPHRASE_FILE', 'w') as f:
    f.write(pp + chr(10))
"
    chmod 600 "$PASSPHRASE_FILE"
    echo -e "${GRN}OK: Passphrase stored at ${PASSPHRASE_FILE} (mode 600)${NC}"
    echo -e "${YLW}IMPORTANT: This is the only key to decrypt. Do not lose it.${NC}"
  fi
}

# === 收集要加密的 secrets ===
collect_secrets() {
  # 所有 echo 都去 stderr、避免汙染函式回傳值
  mkdir -p "$SECRETS_OUTPUT_DIR" >&2
  chmod 700 "$SECRETS_OUTPUT_DIR" >&2

  local file_names=()
  # 標準 secrets（敏感文字檔）
  for f in .env auth.json auth.lock .env.local .env.production; do
    if [[ -f "$HERMES_HOME/$f" ]]; then
      file_names+=("$f")
      echo -e "  ${CYN}found${NC} $f" >&2
    fi
  done

  # v4.1 新增：state.db（對話歷史、SQLite、FTS5 索引 — 不可重建）
  if [[ -f "$HERMES_HOME/state.db" ]]; then
    file_names+=("state.db")
    echo -e "  ${CYN}found${NC} state.db (197MB 對話歷史、SQLite)" >&2
  fi
  # 配套的 WAL / SHM（SQLite 寫入時的暫存檔、可能跟 .db 一起加密比較安全）
  for f in state.db-wal state.db-shm; do
    if [[ -f "$HERMES_HOME/$f" ]]; then
      file_names+=("$f")
      echo -e "  ${CYN}found${NC} $f" >&2
    fi
  done

  # 啟用 nullglob 避免 glob 沒匹配時報錯
  shopt -s nullglob
  for f in "$HERMES_HOME"/*.token "$HERMES_HOME"/*.gpg "$HERMES_HOME"/*.key "$HERMES_HOME"/*.credentials; do
    if [[ -f "$f" ]]; then
      local bn
      bn=$(basename "$f")
      case " ${file_names[*]} " in
        *" $bn "*) ;;
        *)
          file_names+=("$bn")
          echo -e "  ${CYN}found${NC} $bn" >&2
          ;;
      esac
    fi
  done
  shopt -u nullglob

  if [[ ${#file_names[@]} -eq 0 ]]; then
    echo -e "${YLW}WARN: No secrets found to encrypt${NC}" >&2
    return 1
  fi

  local tar_path="$SECRETS_OUTPUT_DIR/secrets-bundle-$TIMESTAMP.tar"
  echo -e "${CYN}Packing secrets -> ${tar_path}${NC}" >&2
  (cd "$HERMES_HOME" && tar -cf "$tar_path" "${file_names[@]}") >&2
  chmod 600 "$tar_path" >&2

  echo -e "${GRN}OK: Packed $(du -sh "$tar_path" | cut -f1) / ${#file_names[@]} files${NC}" >&2
  # 只有 tar_path 走 stdout（函式回傳值）
  echo "$tar_path"
}

# === 加密 ===
encrypt_tar() {
  local tar_path="$1"
  local gpg_path="${tar_path}.gpg"

  echo -e "${CYN}Encrypting -> ${gpg_path}${NC}"
  gpg --batch --yes --pinentry-mode loopback \
      --passphrase-file "$PASSPHRASE_FILE" \
      --symmetric \
      --cipher-algo AES256 \
      --s2k-mode 3 \
      --s2k-count 65011792 \
      --output "$gpg_path" \
      "$tar_path"

  chmod 600 "$gpg_path"

  if command -v shred >/dev/null 2>&1; then
    shred -u -z -n 3 "$tar_path"
  else
    rm -P "$tar_path"
  fi

  echo -e "${GRN}OK: Encrypted ${gpg_path} ($(du -sh "$gpg_path" | cut -f1))${NC}"
  echo "$gpg_path"
}

# === 上傳 Drive ===
upload_drive() {
  local gpg_path="$1"
  echo -e "${CYN}Uploading to Drive: ${RCLONE_REMOTE}/${NC}"

  # 用 rclone copy（會自動建立目標子目錄、行為跟 cp -r 類似）
  rclone copy "$gpg_path" "${RCLONE_REMOTE}/" \
      --config "$RCLONE_CONF" \
      --progress 2>&1 | tail -3

  rm -f "$gpg_path"

  echo -e "${GRN}OK: Drive location: ${RCLONE_REMOTE}/$(basename "$gpg_path")${NC}"
}

# === 驗證 ===
verify() {
  local latest=$(ls -t "$SECRETS_OUTPUT_DIR"/secrets-bundle-*.tar.gpg 2>/dev/null | head -1)
  if [[ -z "$latest" ]]; then
    echo -e "${YLW}WARN: No encrypted file to verify${NC}"
    return 1
  fi
  echo -e "${CYN}Verifying decrypt: ${latest}${NC}"
  echo "Decrypted file list:"
  gpg --batch --yes --pinentry-mode loopback \
      --passphrase-file "$PASSPHRASE_FILE" \
      --decrypt "$latest" 2>/dev/null | tar -tf - | head -20
  echo -e "${GRN}OK: Decryption successful${NC}"
}

# === 主流程 ===
main() {
  local do_upload=false
  local do_verify=false
  local do_rotate=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --upload-drive) do_upload=true; shift ;;
      --verify) do_verify=true; shift ;;
      --rotate) do_rotate=true; shift ;;
      -h|--help)
        head -22 "$0" | tail -20
        exit 0
        ;;
      *) echo "Unknown arg: $1"; exit 1 ;;
    esac
  done

  echo -e "${GRN}========================================${NC}"
  echo -e "${GRN}  Hermes Secrets Encrypt (v4 Tier 2)   ${NC}"
  echo -e "${GRN}========================================${NC}"
  echo ""

  check_tools

  if $do_rotate; then
    echo -e "${YLW}Rotate passphrase mode${NC}"
    echo "Existing passphrase will be deleted. Old .gpg files cannot be decrypted without re-encryption."
    read -p "Confirm rotate? (y/N) " confirm
    if [[ "$confirm" != "y" ]]; then
      echo "Cancelled"
      exit 0
    fi
    rm -f "$PASSPHRASE_FILE"
  fi

  ensure_passphrase

  echo ""
  echo "=== Step 1: Collect secrets ==="
  local tar_path
  tar_path=$(collect_secrets) || exit 1
  echo ""

  echo "=== Step 2: Encrypt ==="
  local gpg_path
  gpg_path=$(encrypt_tar "$tar_path")
  echo ""

  if $do_verify; then
    echo "=== Step 3: Verify ==="
    verify
    echo ""
  fi

  if $do_upload; then
    echo "=== Step 3: Upload Drive ==="
    upload_drive "$gpg_path"
    echo ""
  else
    echo -e "${YLW}Skipping Drive upload (use --upload-drive to enable)${NC}"
    echo "Local encrypted file: ${gpg_path}"
  fi

  echo ""
  echo -e "${GRN}DONE${NC}"
  echo "To restore: hermes-restore-v4.sh tier2 (auto-download from Drive + decrypt)"
}

main "$@"
