#!/bin/bash
# hermes-backup-coverage-check.sh — 每日自動驗證備份同步清單完整性
#
# 安裝: ln -sf ~/.hermes/skills/backup-coverage-check/scripts/coverage_check.sh \
#           ~/.hermes/scripts/hermes-backup-coverage-check.sh
# 排程: 每天 04:00(cron job,no_agent=True)
# 通知: PASS 不通知 / WARN 寫 log 累積 / FAIL 立刻 local notify
#
# 設計:從 INVENTORY.md 讀「v4 同步清單」,跟 ~/.hermes/ 根目錄比對,
#       找出「該備但沒列」「有列但本機不存在」「該排除但被當成該備」三類偏差。

set -uo pipefail

HERMES_HOME="$HOME/.hermes"
INVENTORY_FILE="$HERMES_HOME/INVENTORY.md"
LOG_FILE="$HERMES_HOME/logs/backup-coverage-warn.log"
COVERAGE_SCRIPT_VERSION="1.0.0"

# === 三類清單(從 INVENTORY.md 解析) ===
# 設計:備份腳本跟 coverage check 都讀 INVENTORY.md,改清單不用改兩個地方
SHOULD_BACKUP_DIRS=()  # 必備目錄
SHOULD_BACKUP_FILES=() # 必備單檔
SHOULD_EXCLUDE=()      # 明確排除(rebuildable 或自備份)

# === 三層結果 ===
RESULT_LAYER1="PASS"   # 路徑比對
RESULT_LAYER2="PASS"   # staging 同步驗證
WARN_COUNT=0
FAIL_COUNT=0

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG_FILE" >&2; }
warn() { log "WARN: $*"; WARN_COUNT=$((WARN_COUNT + 1)); }
fail() { log "FAIL: $*"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# === Step 1:解析 INVENTORY.md(若檔案不存在 → FAIL) ===
if [[ ! -f "$INVENTORY_FILE" ]]; then
  fail "INVENTORY.md 不存在於 $INVENTORY_FILE,備份腳本沒有維護 single source of truth"
  echo "FAIL: 0 必備目錄/檔案 確認(INVENTORY.md 缺失), $WARN_COUNT WARN, $FAIL_COUNT FAIL"
  exit 1
fi

# 簡化版解析:抓「## v4 同步清單」到「##」之間的「- xxx/」「- xxx.md」行
# 完整實作可用 awk/python,這裡給 bash 版當 template
INVENTORY_SECTION=$(awk '/^## v4 同步清單/,/^## [^v]/' "$INVENTORY_FILE" | head -n -1)

while IFS= read -r line; do
  # 跳過註解/標題/空行
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "$line" ]] && continue
  # 抓「- xxx/」(目錄)跟「- xxx」(檔案,可能帶 .md/.yaml/.json)
  if [[ "$line" =~ ^-[[:space:]]+([a-zA-Z0-9_./-]+)/[[:space:]]*$ ]]; then
    SHOULD_BACKUP_DIRS+=("${BASH_REMATCH[1]}")
  elif [[ "$line" =~ ^-[[:space:]]+([a-zA-Z0-9_./-]+\.[a-z]+)[[:space:]]*$ ]]; then
    SHOULD_BACKUP_FILES+=("${BASH_REMATCH[1]}")
  fi
done <<< "$INVENTORY_SECTION"

log "從 INVENTORY.md 解析: ${#SHOULD_BACKUP_DIRS[@]} 必備目錄, ${#SHOULD_BACKUP_FILES[@]} 必備單檔"

# === Step 2:Layer 1 路徑比對 ===

# 2a. 掃 ~/.hermes/ 根目錄所有子目錄
ACTUAL_DIRS=$(find "$HERMES_HOME" -maxdepth 1 -mindepth 1 -type d -printf "%f\n" 2>/dev/null | sort)
ACTUAL_FILES=$(find "$HERMES_HOME" -maxdepth 1 -maxdepth 1 -type f -printf "%f\n" 2>/dev/null | sort)

# 2b. 檢查「必備目錄清單裡的」是否本機存在
for dir in "${SHOULD_BACKUP_DIRS[@]}"; do
  if [[ ! -d "$HERMES_HOME/$dir" ]]; then
    fail "INVENTORY.md 列為必備但本機不存在: $dir/"
  fi
done

# 2c. 檢查「必備單檔清單裡的」是否本機存在
for file in "${SHOULD_BACKUP_FILES[@]}"; do
  if [[ ! -f "$HERMES_HOME/$file" ]]; then
    fail "INVENTORY.md 列為必備但本機不存在: $file"
  fi
done

# 2d. 掃根目錄子目錄,對照「該備清單」+「該排除清單」,找出「該備但漏列」
# 注意:這個檢查需要 SHOULD_EXCLUDE 清單,若 INVENTORY.md 沒維護 → 跳過
# (避免「該備但其實是空目錄或 rebuildable」的誤判)
for dir in $ACTUAL_DIRS; do
  # 跳過已知系統/重建/備份本體
  case "$dir" in
    hermes-agent|hermes-backup-staging|backups|backups-*) continue ;;  # 備份本體/upstream clone
  esac
  # 檢查是否在「必備清單」
  if [[ ! " ${SHOULD_BACKUP_DIRS[@]} " =~ " ${dir} " ]]; then
    # 不在必備清單 → 可能是 rebuildable(已知排除)或真的漏備
    # 只警告、不 fail(避免噪音、留給人判斷)
    # 但如果目錄有實際內容(>1KB)且不是空目錄,值得關注
    size=$(du -sk "$HERMES_HOME/$dir" 2>/dev/null | cut -f1)
    if [[ "$size" -gt 1 ]]; then
      warn "根目錄有目錄不在 INVENTORY.md 必備清單: $dir/ (大小: ${size}KB) — 可能漏備、可能是刻意跳過"
    fi
  fi
done

# 2e. 掃根目錄單檔,警告「不在必備清單」的(可能漏備)
for file in $ACTUAL_FILES; do
  # 跳過系統檔
  case "$file" in
    *.lock|*.pid|state.db*|channel_directory.json|*.cache.json|.*.cache.json|.update_check) continue ;;  # hermes runtime
  esac
  # 跳過已知清單
  if [[ ! " ${SHOULD_BACKUP_FILES[@]} " =~ " ${file} " ]]; then
    size=$(stat -c '%s' "$HERMES_HOME/$file" 2>/dev/null || echo 0)
    if [[ "$size" -gt 0 ]]; then
      warn "根目錄有單檔不在 INVENTORY.md 必備清單: $file (大小: ${size}B) — 可能漏備"
    fi
  fi
done

# === Step 3:Layer 2 staging 同步驗證(若 staging 存在) ===
STAGING_DIR="$HERMES_HOME/hermes-backup-staging"
if [[ -d "$STAGING_DIR" ]]; then
  if [[ ! -d "$STAGING_DIR/.git" ]]; then
    fail "staging 不是 git repo: $STAGING_DIR"
    RESULT_LAYER2="FAIL"
  else
    # 抓 staging 內最舊跟最新 commit 的 mtime
    latest_commit_time=$(git -C "$STAGING_DIR" log -1 --format=%ct 2>/dev/null || echo 0)
    now=$(date +%s)
    age_hours=$(( (now - latest_commit_time) / 3600 ))
    if [[ "$age_hours" -gt 48 ]]; then
      warn "staging 最新 commit 是 ${age_hours} 小時前(>48h) — 備份 cron 可能卡住"
      RESULT_LAYER2="WARN"
    else
      log "Layer 2: staging 最新 commit ${age_hours} 小時前,正常"
    fi
  fi
else
  warn "staging 目錄不存在: $STAGING_DIR — 備份 cron 從未跑過或被刪除"
  RESULT_LAYER2="WARN"
fi

# === Step 4:輸出結果 ===
OVERALL="PASS"
[[ "$WARN_COUNT" -gt 0 ]] && OVERALL="WARN"
[[ "$FAIL_COUNT" -gt 0 ]] && OVERALL="FAIL"

echo "=========================================="
echo "備份同步清單完整性檢查 (v$COVERAGE_SCRIPT_VERSION)"
echo "時間: $(date -Iseconds)"
echo "=========================================="
echo "Layer 1 (路徑比對):     $RESULT_LAYER1"
echo "Layer 2 (staging 同步): $RESULT_LAYER2"
echo ""
echo "INVENTORY.md 解析: ${#SHOULD_BACKUP_DIRS[@]} 必備目錄, ${#SHOULD_BACKUP_FILES[@]} 必備單檔"
echo "本次掃描發現: $WARN_COUNT WARN, $FAIL_COUNT FAIL"
echo ""
echo "整體結果: $OVERALL"
echo ""
echo "詳細 log: $LOG_FILE"
echo "=========================================="

# 通知策略:PASS 不通知 / WARN 累積(不立刻)/ FAIL 立刻 local notify
if [[ "$OVERALL" == "FAIL" ]]; then
  echo "ACTION REQUIRED: 上述 FAIL 項目需立即手動介入" >&2
  exit 1
elif [[ "$OVERALL" == "WARN" ]]; then
  echo "WARN 已寫入 log,下次 cron 會累積" >&2
  exit 0
else
  exit 0
fi
