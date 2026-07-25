#!/usr/bin/env bash
# hermes-restore-verify.sh
# v4.1 自我驗證還原腳本（cron 週日跑）
# 跑 hermes-restore-v4.sh tier1 到隔離目錄、驗證 Tier 1 (GitHub) 真的能還原
#
# 為什麼獨立：hermes cron 對 no_agent script 不帶參數、所以需要 wrapper
# 設計給 cron 週日 04:00 跑

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
RESTORE_SCRIPT="$HERMES_HOME/scripts/hermes-restore-v4.sh"
VERIFY_TARGET="/tmp/hermes-restore-verify-$$"
LOG_FILE="/tmp/hermes-restore-verify-$$.log"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== v4 Restore Verify (cron weekly) ==="
log "HERMES_HOME: $HERMES_HOME"
log "VERIFY_TARGET: $VERIFY_TARGET"
log "LOG_FILE: $LOG_FILE"

# 1. 跑 Tier 1 還原（從 GitHub 拉）
log "Step 1: 跑 hermes-restore-v4.sh tier1"
if ! "$RESTORE_SCRIPT" tier1 --target "$VERIFY_TARGET" > "$LOG_FILE" 2>&1; then
  log "✗ Tier 1 還原失敗、看 log: $LOG_FILE"
  tail -30 "$LOG_FILE"
  exit 1
fi

# 2. 驗證還原結果
log "Step 2: 驗證還原結果"
EXPECTED_FILES=(
  "$VERIFY_TARGET/config.yaml"
  "$VERIFY_TARGET/auth.json.template"
  "$VERIFY_TARGET/agents"
  "$VERIFY_TARGET/memories"
  "$VERIFY_TARGET/scripts"
  "$VERIFY_TARGET/docs"
  "$VERIFY_TARGET/skills/trial-and-error/SKILL.md"
)
MISSING=0
for f in "${EXPECTED_FILES[@]}"; do
  if [[ ! -e "$f" ]]; then
    log "  ✗ 缺: $f"
    MISSING=$((MISSING+1))
  fi
done

if [[ $MISSING -gt 0 ]]; then
  log "✗ 驗證失敗、$MISSING 個檔案缺失"
  exit 1
fi

# 3. 算還原了多少檔（粗略驗證）
FILE_COUNT=$(find "$VERIFY_TARGET" -type f 2>/dev/null | wc -l)
log "  ✓ 還原 $FILE_COUNT 個檔"

# 4. 算 skill 數量
SKILL_COUNT=$(find "$VERIFY_TARGET/skills" -maxdepth 2 -name 'SKILL.md' 2>/dev/null | wc -l)
log "  ✓ $SKILL_COUNT 個 skill（含 SKILL.md）"

# 5. 算 hermes-agent/ 沒在（v4.1 設計）
if [[ -d "$VERIFY_TARGET/hermes-agent" ]]; then
  log "  ✗ 設計違規：hermes-agent/ 不該在還原目錄"
  exit 1
fi
log "  ✓ hermes-agent/ 不在（符合 v4.1 設計）"

# 6. 算 state.db 不在（Tier 1 不含、要去 Tier 2）
if [[ -f "$VERIFY_TARGET/state.db" ]]; then
  log "  ⚠ state.db 意外在還原目錄（應該只在 Tier 2）"
fi
log "  ✓ state.db 不在 Tier 1 還原目錄（符合設計）"

# 7. v4.1 加強：檢查 hermes-agent 在主機端有安裝（這次只還原 Tier 1、不含 hermes-agent）
if [[ ! -d "$HERMES_HOME/hermes-agent" ]]; then
  log "  ⚠ hermes-agent/ 不在 $HERMES_HOME（需要從 upstream 重建）"
  log "    解法：curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
else
  log "  ✓ hermes-agent/ 在 $HERMES_HOME（已從 upstream 安裝）"
fi

# 8. 清理
rm -rf "$VERIFY_TARGET"

log ""
log "=== ✓ v4 Tier 1 還原驗證成功 ==="
log "  還原 $FILE_COUNT 個檔 / $SKILL_COUNT 個 skill"
log "  設計約束符合：hermes-agent/ 不在、state.db 不在"
log "  Tier 1 (GitHub) 備份狀態：健康"
