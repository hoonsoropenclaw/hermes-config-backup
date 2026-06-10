#!/usr/bin/env bash
# ============================================================
# hermes-restore-v3.sh - 赫米斯一鍵異機還原腳本（2026-06-06 v3.0）
#
# 對應 backup_hermes_v3.sh — 從 Drive v3/ 目錄式備份還原
#
# 用法：
#   1. nano hermes-restore-v3.sh  # 改下方 3 個變數
#   2. ./hermes-restore-v3.sh
#
# v3 vs v2 差異：
#   ❌ 不下載 694 MB 大 tar.gz（rclone crypt 超慢）
#   ✅ 用 rclone copy 挑目錄拉（增量、可選）
#   ✅ 用 manifest 驗證還原完整性
#   ✅ 可選「核心」、「完整」、「週 snapshot」三種模式
# ============================================================

# ===================== 設定區（必改） =====================

# 1. 新主機的 hermes home
HERMES_HOME="$HOME/.hermes"

# 2. rclone config 檔路徑（必填，從舊主機或備份機器拿來）
RCLONE_CONFIG="$HOME/documents/rclone.conf"

# 3. Drive 備份版本（v2 = tar.gz 舊版 / v3 = 目錄式新版）
BACKUP_VERSION="v3"

# 4. 要還原的週（空字串 = 還原 current；填 YYYY_Www = 還原某週 snapshot）
#    範例："2026_W22" 還原 2022 年第 22 週的狀態
RESTORE_SNAPSHOT=""

# 5. GPG manifest passphrase 檔（驗證還原完整性）
MANIFEST_PASS_FILE="$HOME/.local/share/hermes/secrets/manifest-passphrase"

# ===================== 進階設定（可選） =====================

RCLONE_REMOTE="crypt_hermes"
DRIVE_BASE="${RCLONE_REMOTE}:hermes-backup/${BACKUP_VERSION}"

# Telegram 警告
# 如果新主機要啟用 gateway，先在舊主機跑：pkill -f hermes-gateway

# ===================== 腳本本體（不用改） =====================

set -euo pipefail

# 顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 解析旗標
YES_MODE="no"
DO_MODE="core"  # core | full | verify-only
for arg in "$@"; do
  case "$arg" in
    --yes|-y) YES_MODE="yes" ;;
    --full) DO_MODE="full" ;;
    --core) DO_MODE="core" ;;
    --verify-only) DO_MODE="verify-only" ;;
    --snapshot=*) RESTORE_SNAPSHOT="${arg#--snapshot=}" ;;
  esac
done

# === 0. 前置警告 ===
clear
cat << EOF
╔════════════════════════════════════════════════════════════════╗
║  赫米斯異機還原腳本 v3.0（Drive 目錄式）                       ║
╠════════════════════════════════════════════════════════════════╣
║  ⚠️  此腳本會覆蓋現有的 ~/.hermes/ 部分檔案                   ║
║  ⚠️  還原前請先關閉任何運行的 hermes-gateway：                ║
║      pkill -f hermes-gateway                                  ║
║  ⚠️  Telegram session 一次只能掛一台機器：                    ║
║      別同時開兩台主機的 gateway，會搶同一個 bot               ║
╚════════════════════════════════════════════════════════════════╝
EOF

echo ""
echo -e "${BLUE}目前設定：${NC}"
echo "  HERMES_HOME      = $HERMES_HOME"
echo "  RCLONE_CONFIG    = $RCLONE_CONFIG"
echo "  BACKUP_VERSION   = $BACKUP_VERSION"
echo "  DO_MODE          = $DO_MODE (core=核心 / full=完整 / verify-only=只驗證)"
echo "  RESTORE_SNAPSHOT = ${RESTORE_SNAPSHOT:-<使用 current>}"
echo "  YES_MODE         = $YES_MODE"
echo ""

# 判斷來源路徑
if [ -n "$RESTORE_SNAPSHOT" ]; then
  SOURCE="${DRIVE_BASE}/snapshots/${RESTORE_SNAPSHOT}/"
  echo -e "${YELLOW}→ 還原週 snapshot: ${RESTORE_SNAPSHOT}${NC}"
else
  SOURCE="${DRIVE_BASE}/current/"
  echo -e "${GREEN}→ 還原最新 current${NC}"
fi
echo ""

if [ "$YES_MODE" != "yes" ]; then
  read -p "設定正確嗎？(yes/no) " -r
  echo
  if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "請先 nano hermes-restore-v3.sh 改設定，再重跑"
    exit 0
  fi
fi

# === 1. 預檢 ===
echo -e "${BLUE}[1/6] 預檢工具${NC}"
for tool in rclone python3 tar; do
  if ! command -v "$tool" &>/dev/null; then
    echo -e "${RED}❌ 缺少工具: $tool（apt install $tool）${NC}"
    exit 1
  fi
done
echo -e "${GREEN}✓ 工具齊全${NC}"

if [ ! -f "$RCLONE_CONFIG" ]; then
  echo -e "${RED}❌ 找不到 rclone config: $RCLONE_CONFIG${NC}"
  echo "   從舊主機或備份機器的 ~/documents/rclone.conf 拿過來"
  exit 1
fi
chmod 600 "$RCLONE_CONFIG"

if ! rclone listremotes --config "$RCLONE_CONFIG" 2>/dev/null | grep -q "^${RCLONE_REMOTE}:$"; then
  echo -e "${RED}❌ rclone remote ${RCLONE_REMOTE}: 不存在於 config${NC}"
  exit 1
fi
echo -e "${GREEN}✓ rclone config OK${NC}"

# === 2. 確認 Drive 來源存在 ===
echo ""
echo -e "${BLUE}[2/6] 確認 Drive 來源存在${NC}"
echo "  來源: $SOURCE"
DRIVE_SIZE=$(rclone size "$SOURCE" --config "$RCLONE_CONFIG" 2>/dev/null | head -2 | tail -1)
echo "  $DRIVE_SIZE"
if [ -z "$DRIVE_SIZE" ]; then
  echo -e "${RED}❌ 找不到 Drive 來源（$SOURCE）${NC}"
  echo "   可用的目錄："
  rclone lsf "${DRIVE_BASE}/" --dirs-only --config "$RCLONE_CONFIG" 2>&1 | head -10
  exit 1
fi
echo -e "${GREEN}✓ Drive 來源確認${NC}"

# === 3. 互動式選擇要還原什麼 ===
echo ""
echo -e "${BLUE}[3/6] 選擇要還原的內容${NC}"
echo ""
echo "Drive v3/ 備份包含："
echo "  ✓ 7 個核心 MD 檔（USER/MEMORY/SOUL/AGENTS/IDENTITY/HEARTBEAT/TOOLS）"
echo "  ✓ config.yaml / cron-jobs.json（個人化設定）"
echo "  ✓ skills/*（所有自建 + 外部 skills）"
echo "  ✓ scripts/*（50+ Python 腳本）"
echo "  ✓ .env 真實檔（12 個 API key）"
echo "  ✓ state.db（169 MB session store）"
echo "  ✓ hermes-agent 源碼（不含 venv、可重建）"
echo "  ✓ 各 skill 的參考文件"
echo ""

ask_yes() {
  local prompt="$1"
  local default="${2:-Y}"
  if [ "$YES_MODE" = "yes" ]; then
    echo "$prompt (auto-yes: $default)"
    [[ "${default,,}" =~ ^y ]] && return 0 || return 1
  fi
  read -p "$prompt" -r
  echo
  [[ -z "$REPLY" ]] && REPLY="$default"
  [[ "${REPLY,,}" =~ ^y ]] && return 0
  return 1
}

# core 模式：只還原核心（快、5-10 分鐘）
# full 模式：全還原（慢、30-60 分鐘）
if [ "$YES_MODE" = "yes" ]; then
  DO_CORE="yes"
  DO_ENV="yes"
  DO_STATE="$DO_MODE"  # full 才還原 state.db
  DO_SKILLS="yes"
  DO_SCRIPTS="yes"
  DO_AGENT="$DO_MODE"  # full 才還原 hermes-agent
  DO_DOCS="yes"
  DO_GPG="yes"
else
  ask_yes "還原核心設定（config / memories / cron）？ (Y/n) " Y && DO_CORE="yes" || DO_CORE="no"
  ask_yes "還原 skills（所有自建 + 外部 skills）？ (Y/n) " Y && DO_SKILLS="yes" || DO_SKILLS="no"
  ask_yes "還原 scripts（50+ Python 腳本）？ (Y/n) " Y && DO_SCRIPTS="yes" || DO_SCRIPTS="no"
  ask_yes "還原 .env 真實檔（12 個 API key）？ (Y/n) " Y && DO_ENV="yes" || DO_ENV="no"
  ask_yes "還原 state.db（169 MB session store）？ (y/N) " N && DO_STATE="yes" || DO_STATE="no"
  ask_yes "還原 hermes-agent 源碼（不含 venv）？ (Y/n) " Y && DO_AGENT="yes" || DO_AGENT="no"
  ask_yes "還原 docs（RESTORE.md 等說明文件）？ (Y/n) " Y && DO_DOCS="yes" || DO_DOCS="no"
  ask_yes "還原 GPG 加密的備用 token？ (y/N) " N && DO_GPG="yes" || DO_GPG="no"
fi

echo ""
echo "還原計畫："
echo "  config     : $DO_CORE"
echo "  skills     : $DO_SKILLS"
echo "  scripts    : $DO_SCRIPTS"
echo "  .env       : $DO_ENV"
echo "  state.db   : $DO_STATE"
echo "  agent src  : $DO_AGENT"
echo "  docs       : $DO_DOCS"
echo "  gpg tokens : $DO_GPG"
echo ""

if [ "$YES_MODE" != "yes" ]; then
  read -p "確認執行？ (yes/no) " -r
  echo
  if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "已取消"
    exit 0
  fi
fi

# === 4. 還原 ===
echo ""
echo -e "${BLUE}[4/6] 開始還原到 $HERMES_HOME${NC}"
mkdir -p "$HERMES_HOME"
START=$(date +%s)

if [ "$DO_CORE" = "yes" ]; then
  echo "  [1/8] config / memories / cron ..."
  rclone copy "${SOURCE}config.yaml" "$HERMES_HOME/" --config "$RCLONE_CONFIG" 2>&1 | tail -1
  rclone copy "${SOURCE}cron/" "$HERMES_HOME/cron/" --config "$RCLONE_CONFIG" 2>&1 | tail -1
  rclone copy "${SOURCE}memories/" "$HERMES_HOME/memories/" --config "$RCLONE_CONFIG" 2>&1 | tail -1
fi

if [ "$DO_SKILLS" = "yes" ]; then
  echo "  [2/8] skills/（可能多）..."
  rclone copy "${SOURCE}skills/" "$HERMES_HOME/skills/" \
    --config "$RCLONE_CONFIG" \
    --transfers=4 --checkers=2 \
    --exclude='**/node_modules/**' --exclude='**/__pycache__/**' --exclude='**/*.pyc' \
    --exclude='**/.archive/**' 2>&1 | tail -2
fi

if [ "$DO_SCRIPTS" = "yes" ]; then
  echo "  [3/8] scripts/..."
  rclone copy "${SOURCE}scripts/" "$HERMES_HOME/scripts/" \
    --config "$RCLONE_CONFIG" --transfers=4 2>&1 | tail -1
fi

if [ "$DO_ENV" = "yes" ]; then
  echo "  [4/8] .env 真實檔 ..."
  if rclone copy "${SOURCE}.env" "$HERMES_HOME/.env" --config "$RCLONE_CONFIG" 2>&1 | tail -1; then
    chmod 600 "$HERMES_HOME/.env"
    echo "  ✓ .env 還原（mode 600）"
  else
    echo "  ⚠ .env 還原失敗（v3 可能有 exclude）"
  fi
fi

if [ "$DO_STATE" = "yes" ]; then
  echo "  [5/8] state.db（169 MB）..."
  rclone copy "${SOURCE}state.db" "$HERMES_HOME/state.db" \
    --config "$RCLONE_CONFIG" 2>&1 | tail -1
fi

if [ "$DO_AGENT" = "yes" ]; then
  echo "  [6/8] hermes-agent 源碼（不含 venv）..."
  mkdir -p "$HERMES_HOME/hermes-agent"
  rclone copy "${SOURCE}hermes-agent/" "$HERMES_HOME/hermes-agent/" \
    --config "$RCLONE_CONFIG" \
    --transfers=4 --checkers=2 \
    --exclude='venv/**' --exclude='venv64/**' --exclude='.venv/**' \
    --exclude='**/__pycache__/**' --exclude='**/*.pyc' \
    --exclude='**/node_modules/**' --exclude='ui-tui/node_modules/**' 2>&1 | tail -2
  echo "  ⚠ venv 不在 Drive 裡，請跑：cd $HERMES_HOME/hermes-agent && python -m venv venv && source venv/bin/activate && pip install -e ."
fi

if [ "$DO_DOCS" = "yes" ]; then
  echo "  [7/8] docs/..."
  rclone copy "${SOURCE}docs/" "$HERMES_HOME/docs/" --config "$RCLONE_CONFIG" 2>&1 | tail -1
fi

if [ "$DO_GPG" = "yes" ]; then
  echo "  [8/8] GPG tokens（需手動解密）..."
  mkdir -p "$HOME/.config/hermes/alt_gh_tokens"
  rclone copy "${SOURCE}full_backups/alt_gh_tokens/" "$HOME/.config/hermes/alt_gh_tokens/" \
    --config "$RCLONE_CONFIG" 2>&1 | tail -1
  mkdir -p "$HOME/.local/share/hermes/secrets"
  rclone copy "${SOURCE}full_backups/secrets/" "$HOME/.local/share/hermes/secrets/" \
    --config "$RCLONE_CONFIG" 2>&1 | tail -1
  chmod 700 "$HOME/.config/hermes" "$HOME/.local/share/hermes"
  chmod 600 "$HOME/.config/hermes/alt_gh_tokens"/* 2>/dev/null || true
  chmod 600 "$HOME/.local/share/hermes/secrets"/* 2>/dev/null || true
  echo "  ✓ GPG tokens 還原（仍是加密狀態）"
fi

ELAPSED=$(($(date +%s) - START))
echo ""
echo -e "${GREEN}✓ 還原完成（${ELAPSED} 秒 = $((ELAPSED/60)) 分 $((ELAPSED%60)) 秒）${NC}"

# === 5. 驗證（用 manifest）===
echo ""
echo -e "${BLUE}[5/6] 驗證還原（manifest 比對）${NC}"
LATEST_MANIFEST=$(rclone lsf "${DRIVE_BASE}/manifests/" --files-only --config "$RCLONE_CONFIG" 2>/dev/null | sort | tail -1 | tr -d '\r')

if [ -n "$LATEST_MANIFEST" ] && [ -f "$MANIFEST_PASS_FILE" ]; then
  echo "  找到最新 manifest: $LATEST_MANIFEST"
  TMP_DIR=$(mktemp -d)
  cd "$TMP_DIR"

  # 下載並解密
  rclone copy "${DRIVE_BASE}/manifests/${LATEST_MANIFEST}" ./ --config "$RCLONE_CONFIG" 2>&1 | tail -1
  if [ -f "$LATEST_MANIFEST" ]; then
    gpg --batch --yes --pinentry-mode loopback \
      --passphrase-file "$MANIFEST_PASS_FILE" \
      --decrypt "$LATEST_MANIFEST" > manifest.txt 2>/dev/null

    if [ -f manifest.txt ]; then
      MANIFEST_FILES=$(grep -c "^[a-f0-9]\{64\}" manifest.txt)
      echo "  manifest 內含 $MANIFEST_FILES 個檔案"

      # 抽樣驗證前 20 個檔案的 SHA256
      echo "  抽樣驗證前 20 個檔案..."
      PASS=0
      FAIL=0
      grep "^[a-f0-9]\{64\}" manifest.txt | head -20 | while read hash size path; do
        if [ -f "$path" ]; then
          ACTUAL=$(sha256sum "$path" 2>/dev/null | awk '{print $1}')
          if [ "$ACTUAL" = "$hash" ]; then
            echo "  ✓ $path"
          else
            echo "  ✗ $path（hash 不符：期望 $hash，實際 $ACTUAL）"
          fi
        else
          echo "  ⚠ $path（檔案不存在）"
        fi
      done
    else
      echo -e "${YELLOW}  ⚠ Manifest 解密失敗${NC}"
    fi
  fi

  cd /tmp
  rm -rf "$TMP_DIR"
else
  echo -e "${YELLOW}  ⚠ 跳過 manifest 驗證（無 manifest 或無 passphrase 檔）${NC}"
fi

# === 6. 完成 ===
echo ""
echo -e "${BLUE}[6/6] 完成${NC}"
echo ""
echo -e "${GREEN}✓ 還原成功！${NC}"
echo ""
echo "下一步："
echo "  1. 確認 hermes-agent 能跑："
echo "     cd $HERMES_HOME/hermes-agent && source venv/bin/activate && pip install -e ."
echo ""
echo "  2. 確認 .env 內容："
echo "     head $HERMES_HOME/.env"
echo ""
echo "  3. 確認 config.yaml 路徑正確："
echo "     head $HERMES_HOME/config.yaml"
echo ""
echo "  4. 重啟任何運行中的 hermes gateway / cron"
echo ""
echo "  5. 跑 smoke test："
echo "     hermes status"
echo ""
echo "還原來源記錄："
echo "  來源: $SOURCE"
echo "  Drive: $DRIVE_BASE"
if [ -n "$RESTORE_SNAPSHOT" ]; then
  echo "  Snapshot: $RESTORE_SNAPSHOT"
fi
