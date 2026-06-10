#!/usr/bin/env bash
# hermes-restore-v4.sh
# v4 統一還原入口：Tier 1 快速（5 分鐘） + Tier 2 secrets（從 Drive）
#
# 用法：
#   hermes-restore-v4.sh tier1              # 只還原 Tier 1（從 GitHub）
#   hermes-restore-v4.sh tier2              # 只還原 Tier 2（從 Drive 解密 secrets）
#   hermes-restore-v4.sh tier3              # 只還原 Tier 3（從本地 Y 槽、選配）
#   hermes-restore-v4.sh all                # 跑全部（tier1 → tier3 → tier2）
#   hermes-restore-v4.sh all --target DIR   # 還原到指定目錄（不覆蓋當前 $HERMES_HOME）
#   hermes-restore-v4.sh --help
#
# 異機還原 SOP：
#   1. 全新主機、安裝 hermes-agent（pip install）
#   2. 跑 hermes-restore-v4.sh all --target /tmp/hermes-restore-test/
#   3. 驗證還原結果、diff 主機 vs 還原
#   4. 確認後用 rsync 覆蓋到正式位置

set -euo pipefail

HERMES_HOME_SRC="${HERMES_HOME:-$HOME/.hermes}"
TARGET_DIR="$HERMES_HOME_SRC"
STAGING="$HERMES_HOME_SRC/hermes-backup-staging"
GITHUB_REPO="hoonsoropenclaw/hermes-config-backup"

RCLONE_CONF="$HOME/documents/rclone.conf"
RCLONE_REMOTE="hoonsorasus:hermes-backup/secrets"
PASSPHRASE_FILE="$HOME/Documents/hermes-keys/.hermes_backup_passphrase"

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; CYN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GRN}[$(date +%H:%M:%S)] ✓${NC} $*"; }
warn() { echo -e "${YLW}[$(date +%H:%M:%S)] ⚠${NC} $*"; }
err()  { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $*" >&2; }

MODE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    tier1|tier2|tier3|all) MODE="$1"; shift ;;
    --target) TARGET_DIR="$2"; shift 2 ;;
    --staging) STAGING="$2"; shift 2 ;;
    -h|--help)
      head -20 "$0" | tail -18
      exit 0
      ;;
    *) err "Unknown: $1"; exit 1 ;;
  esac
done

[[ -z "$MODE" ]] && { err "需要指定 mode: tier1 / tier2 / tier3 / all"; exit 1; }

# cron 模式：沒給 --target 時用自動隔離目錄（週日自我驗證用）
if [[ -z "${TARGET_DIR_SET:-}" ]] && [[ "$MODE" == "tier1" || "$MODE" == "tier2" || "$MODE" == "all" ]]; then
  if [[ "${CRON_MODE:-}" == "1" ]]; then
    TARGET_DIR="/tmp/hermes-restore-verify-$$"
    log "Cron 模式：自動使用 target=$TARGET_DIR"
  fi
fi

# ===================== Tier 1: GitHub =====================
tier1() {
  log "=== Tier 1: GitHub (hoonsoropenclaw/$GITHUB_REPO) ==="

  if [[ -d "$STAGING" ]]; then
    warn "$STAGING 已存在、用既有 staging（重新 git pull 拉最新）"
    cd "$STAGING"
    git pull origin main 2>&1 | tail -3 || warn "git pull 失敗（可能 offline）"
  else
    log "clone $GITHUB_REPO → $STAGING"
    git clone "https://github.com/$GITHUB_REPO.git" "$STAGING"
  fi

  log "還原到 $TARGET_DIR/"
  mkdir -p "$TARGET_DIR"

  # 還原各目錄（保留目標既有檔案、不刪除）
  for item in config.yaml auth.json.template agents memories scripts docs; do
    src="$STAGING/$item"
    dst="$TARGET_DIR/$item"
    if [[ -e "$src" ]]; then
      if [[ -d "$src" ]]; then
        mkdir -p "$dst"
        rsync -au "$src/" "$dst/"
      else
        cp -f "$src" "$dst"
      fi
      ok "還原 $item"
    else
      warn "staging 內找不到 $item、跳過"
    fi
  done

  # 還原 skills/（sparc 已是 snapshot、不用 submodule update）
  if [[ -d "$STAGING/skills" ]]; then
    mkdir -p "$TARGET_DIR/skills"
    rsync -au --exclude='*.bak' --exclude='*.lock' "$STAGING/skills/" "$TARGET_DIR/skills/"
    ok "還原 skills/（含 sparc-methodology snapshot）"
  fi

  ok "Tier 1 完成、$TARGET_DIR 已含備份內容"
}

# ===================== Tier 2: Drive secrets =====================
tier2() {
  log "=== Tier 2: Drive secrets decrypt ==="

  if [[ ! -f "$PASSPHRASE_FILE" ]]; then
    err "找不到 passphrase: $PASSPHRASE_FILE"
    err "（這是 Drive 加密 secrets 的解密金鑰、第一次跑要先從備份位置複製）"
    err ""
    err "找不到 passphrase 常見原因："
    err "  1. 全新主機、從來沒複製過 passphrase 過來"
    err "     解法：從舊機器或密碼管理器（1Password / Bitwarden）取得"
    err "     預設位置：$HOME/Documents/hermes-keys/.hermes_backup_passphrase"
    err "  2. Passphrase 檔存在但權限錯（不是 600）"
    err "     解法：chmod 600 $HOME/Documents/hermes-keys/.hermes_backup_passphrase"
    err "  3. 加密時的 passphrase 跟還原時不一樣"
    err "     症狀：gpg 會報 'decryption failed'"
    err "     解法：找出原始 passphrase（從備份密碼管理器）"
    return 1
  fi

  # 驗證 passphrase 檔權限
  if [[ "$(stat -c %a "$PASSPHRASE_FILE" 2>/dev/null)" != "600" ]]; then
    warn "Passphrase 檔權限不是 600、自動修"
    chmod 600 "$PASSPHRASE_FILE"
  fi

  # 驗證 Drive 連線（提早 fail、不等到下載才發現）
  log "驗證 Drive 連線..."
  if ! rclone lsd "${RCLONE_REMOTE%/*}" --config "$RCLONE_CONF" 2>&1 | head -1 >/dev/null; then
    err "無法連線到 Drive、可能 OAuth token 過期"
    err "解法：rclone config 重新設定 hoonsorasus remote"
    return 1
  fi

  # 列出 Drive 上有哪些 secrets bundle
  log "列出 Drive 上的 secrets bundle..."
  rclone lsf "$RCLONE_REMOTE/" --config "$RCLONE_CONF" 2>&1 | head -10

  # 找最新的
  local latest=$(rclone lsf "$RCLONE_REMOTE/" --config "$RCLONE_CONF" --files-only 2>/dev/null \
    | grep 'secrets-bundle-.*\.tar\.gpg' | sort -r | head -1)

  if [[ -z "$latest" ]]; then
    err "Drive 上找不到 secrets-bundle-*.tar.gpg"
    return 1
  fi

  log "下載最新: $latest"
  local tmp_gpg="/tmp/hermes-restore-$$-secrets.tar.gpg"
  rclone copy "${RCLONE_REMOTE}/$latest" /tmp/ --config "$RCLONE_CONF" 2>&1 | tail -3
  mv "/tmp/$latest" "$tmp_gpg"
  chmod 600 "$tmp_gpg"

  # 解密
  log "解密..."
  local tmp_tar="/tmp/hermes-restore-$$-secrets.tar"
  gpg --batch --yes --pinentry-mode loopback \
    --passphrase-file "$PASSPHRASE_FILE" \
    --decrypt "$tmp_gpg" > "$tmp_tar"
  chmod 600 "$tmp_tar"

  # 解 tar 到 target
  log "解開到 $TARGET_DIR/..."
  (cd "$TARGET_DIR" && tar -xf "$tmp_tar")

  # 修權限（secrets 必須 600）
  for f in .env auth.json auth.lock; do
    if [[ -f "$TARGET_DIR/$f" ]]; then
      chmod 600 "$TARGET_DIR/$f"
    fi
  done
  # state.db 系列：確保不是 world-readable
  for f in state.db state.db-wal state.db-shm; do
    if [[ -f "$TARGET_DIR/$f" ]]; then
      chmod 600 "$TARGET_DIR/$f"
    fi
  done
  # 驗證權限（如果跑錯了、警告使用者）
  log "驗證權限..."
  PERM_OK=true
  for f in .env auth.json state.db; do
    if [[ -f "$TARGET_DIR/$f" ]]; then
      actual=$(stat -c %a "$TARGET_DIR/$f" 2>/dev/null)
      if [[ "$actual" != "600" ]]; then
        warn "  $f 權限是 $actual、不是 600（安全風險）"
        chmod 600 "$TARGET_DIR/$f"
        PERM_OK=false
      fi
    fi
  done
  $PERM_OK && ok "  所有 secrets 檔案權限 600"

  # 清暫存
  shred -u -z -n 3 "$tmp_tar" 2>/dev/null || rm -P "$tmp_tar"
  shred -u -z -n 3 "$tmp_gpg" 2>/dev/null || rm -P "$tmp_gpg"

  ok "Tier 2 完成、$TARGET_DIR/ 已含 secrets"
}

# ===================== Tier 3: 本地 Y 槽鏡像（選配）=====================
tier3() {
  log "=== Tier 3: 本地 Y 槽鏡像（選配、需手動設定來源）==="
  warn "Tier 3 是 placeholder、需要根據你的 Y 槽路徑調整"
  warn "預期 source = /mnt/y/hermes-snapshot/ 或 /Volumes/Y/hermes-snapshot/"
  warn "請手動跑："
  warn "  rsync -au /mnt/y/hermes-snapshot/ $TARGET_DIR/"
}

# ===================== 主流程 =====================
main() {
  echo -e "${GRN}========================================${NC}"
  echo -e "${GRN}  Hermes Restore v4                      ${NC}"
  echo -e "${GRN}========================================${NC}"
  echo ""
  echo "Mode:  $MODE"
  echo "Target: $TARGET_DIR"
  echo "Staging: $STAGING"
  echo ""

  case "$MODE" in
    tier1) tier1 ;;
    tier2) tier2 ;;
    tier3) tier3 ;;
    all)
      tier1 || { err "Tier 1 失敗、停止"; exit 1; }
      echo ""
      tier3 || warn "Tier 3 失敗、繼續"
      echo ""
      tier2 || warn "Tier 2 失敗、繼續"
      ;;
  esac

  echo ""
  ok "Restore 完成"
  echo ""
  echo "驗證指令："
  echo "  ls -la $TARGET_DIR/    # 看 .env 權限 600"
  echo "  diff -r $HERMES_HOME_SRC/ $TARGET_DIR/ 2>&1 | head -20"
}

main
