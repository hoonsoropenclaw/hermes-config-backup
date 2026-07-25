#!/usr/bin/env bash
# ============================================================
# verify_backup.sh - 備份驗證腳本 v1.0
# 三層驗證：L1 完整性 → L2 擷取 → L3 內容驗證
#
# 使用方式：
#   bash verify_backup.sh <tar.gz_path>           # L1 + L2
#   bash verify_backup.sh <tar.gz_path> --full    # L1 + L2 + L3
# ============================================================

set -uo pipefail  # Note: removed -e because tar pipe can cause SIGPIPE

BACKUP_FILE="$1"
MODE="${2:-normal}"

# 顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "[$(date +%H:%M:%S)] $*"; }
pass() { log "${GREEN}✓ $*${NC}"; }
fail() { log "${RED}✗ $*${NC}"; }
warn() { log "${YELLOW}⚠ $*${NC}"; }

# === 預檢 ===
if [ ! -f "$BACKUP_FILE" ]; then
  fail "備份檔案不存在: $BACKUP_FILE"
  exit 1
fi

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "開始驗證備份: $(basename "$BACKUP_FILE") (${FILE_SIZE})"

# === L1: 完整性檢查 ===
log "--- L1: 完整性檢查 ---"

# 1a. tar 結構檢查（+ pipefail 保護）
set +e  # temp disable pipefail for tar
TAR_OK=$(tar -tzf "$BACKUP_FILE" 2>&1)
TAR_RC=$?
set -euo pipefail  # re-enable

if [ $TAR_RC -ne 0 ] || echo "$TAR_OK" | grep -q "Cannot open\|Error\|failed"; then
  fail "tar 結構損壞: $TAR_OK"
  exit 1
fi
pass "tar 結構正常（可讀取）"

# 1b. 檢查檔案數量
FILE_COUNT=$(echo "$TAR_OK" | wc -l)
if [ "$FILE_COUNT" -gt 10 ]; then
  pass "檔案數量: ${FILE_COUNT} 個"
else
  warn "檔案數量異常少: ${FILE_COUNT} 個（正常應 > 100）"
fi

# === L2: 擷取測試 ===
log "--- L2: 擷取測試 ---"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_DIR="/tmp/backup_verify_${TIMESTAMP}"
mkdir -p "$TEST_DIR"

if ! tar -xzf "$BACKUP_FILE" -C "$TEST_DIR" 2>&1; then
  fail "擷取失敗"
  rm -rf "$TEST_DIR"
  exit 1
fi
pass "成功擷取到 ${TEST_DIR}"

# === L3: 內容驗證（僅 --full 模式） ===
if [ "$MODE" = "--full" ]; then
  log "--- L3: 內容驗證 ---"

  # 動態抓取 tar 內的根目錄前綴（保護 pipe）
  set +e
  TAR_ROOT=$(echo "$TAR_OK" | head -1 | cut -d'/' -f1)
  set -euo pipefail
  
  if [ -z "$TAR_ROOT" ]; then
    fail "無法判斷 tar 根目錄前綴"
    rm -rf "$TEST_DIR"
    exit 1
  fi
  log "  (tar root: ${TAR_ROOT})"

  CRITICAL_FILES=(
    "config/hermes-config.yaml"
    "config/cron-jobs.json"
    "memories/MEMORY.md"
    "memories/SOUL.md"
    "memories/USER.md"
    "memories/HEARTBEAT.md"
    "memories/IDENTITY.md"
    "memories/AGENTS.md"
  )

  MISSING=0
  for f in "${CRITICAL_FILES[@]}"; do
    if [ -f "$TEST_DIR/${TAR_ROOT}/$f" ]; then
      pass "存在: $f"
    else
      fail "缺少: $f"
      MISSING=$((MISSING + 1))
    fi
  done

  # 額外檢查：JSON 有效性
  if [ -f "$TEST_DIR/${TAR_ROOT}/config/cron-jobs.json" ]; then
    if python3 -c "import json; json.load(open('$TEST_DIR/${TAR_ROOT}/config/cron-jobs.json'))" 2>/dev/null; then
      pass "cron-jobs.json JSON 有效"
    else
      fail "cron-jobs.json JSON 損壞"
      MISSING=$((MISSING + 1))
    fi
  fi

  # 額外檢查：backup_hermes.sh 存在
  if [ -f "$TEST_DIR/${TAR_ROOT}/scripts/backup_hermes.sh" ]; then
    pass "backup_hermes.sh 存在"
  else
    warn "backup_hermes.sh 不存在（還原時需要）"
  fi

  if [ "$MISSING" -gt 0 ]; then
    fail "L3 驗證失敗：缺少 ${MISSING} 個關鍵檔案"
    rm -rf "$TEST_DIR"
    exit 1
  fi
fi

# === 完成 ===
pass "備份驗證完成: $(basename "$BACKUP_FILE")"
log "測試目錄保留在: $TEST_DIR（人工審查後可刪除）"

# 寫入驗證日誌
LOG_FILE="$HOME/.hermes/logs/backup_verify.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] $(basename "$BACKUP_FILE") | ${FILE_SIZE} | ${FILE_COUNT} files | ${MODE}" >> "$LOG_FILE"
echo "  → 測試目錄: $TEST_DIR" >> "$LOG_FILE"
echo "  → TAR_ROOT: $TAR_ROOT" >> "$LOG_FILE"