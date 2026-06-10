#!/usr/bin/env bash
# hermes-backup-coverage-check.sh
# 每日掃 ~/.hermes/ 路徑變動，跟 hermes-backup-v4.sh 同步清單比對，找漏備的路徑
# 2026-06-10 建立 (v4.6 配套)
#
# 觸發：cron 每日凌晨 4 點跑
# 輸出：PASS / WARN / FAIL + 寫 ~/.hermes/logs/backup-coverage.log
#
# 設計：
# - Layer A (建議加)：本機有檔/目錄、v4 沒列 → 建議加進 INVENTORY.md
# - Layer B (警告)：v4 有列、本機不存在 → 可能剛搬走、需評估
# - Layer C (驗證同步)：本機 vs staging 比對，看 staging 落後
#
# 變更對照：改這個 script → 必同步更新 ~/.hermes/docs/INVENTORY.md

set -uo pipefail

# === 設定 ===
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
STAGING="$HERMES_HOME/hermes-backup-staging"
V4_SCRIPT="$HERMES_HOME/scripts/hermes-backup-v4.sh"
INVENTORY="$HERMES_HOME/docs/INVENTORY.md"
LOG="$HERMES_HOME/logs/backup-coverage.log"

mkdir -p "$(dirname "$LOG")" 2>/dev/null

# 排除清單（本來就不該被視為「應該備份」的路徑）
EXCLUDE_DIRS=(
  "hermes-agent"           # upstream clone、git pull 可重建
  "hermes-backup-staging"  # 備份本體
  "backups"                # 備份本體
  "hooks"                  # 空
  "audio_cache"            # 空
  "image_cache"            # 空
  "images"                 # 空
  "pairing"                # 空
  "sandboxes"              # 空
  "test_rclone_speed"      # 測試
  "browser_screenshots"    # 純截圖暫存
  "lsp"                    # LSP 暫存
  "pastes"                 # 剪貼簿暫存
  "rag"                    # 索引 rebuildable
  "sessions"               # request_dump 暫存、有敏感資料風險
  "state-snapshots"        # 200M 太大、pre-update 快照
  "projects"               # 有 .git 的 rebuildable 專案
  "bin"                    # tirith 二進位
  ".git"                   # 不可能
  "node_modules"           # 不可能
)

# cache 子目錄排除清單
EXCLUDE_CACHE_SUBDIRS=(
  "screenshots"            # 純截圖暫存
  "model_catalog.json"     # rebuildable（會在 cache/ 根目錄）
)

# 根目錄單檔排除清單
# Tier 2 加密的不該出現在 Tier 1 (.env / auth.json)
# hermes runtime 鎖定檔 / 快取不該備
# rebuildable 暫存不該備
EXCLUDE_ROOT_FILES=(
  # Tier 2 加密（hermes-secrets-encrypt.sh 管）
  ".env"
  "auth.json"
  "auth.lock"
  # hermes runtime 鎖定 + 狀態
  "state.db"
  "state.db-shm"
  "state.db-wal"
  "gateway.lock"
  "gateway.pid"
  "gateway_state.json"
  "processes.json"
  "kanban.db.init.lock"
  "kanban.db"              # 空殼、可重 init
  # hermes 內建快取（會自動重建）
  "models_dev_cache.json"
  "ollama_cloud_models_cache.json"
  "provider_models_cache.json"
  "channel_directory.json"
  ".update_check"
  # history / 安裝記錄
  ".hermes_history"
  ".install_method"
  # 第三方（YouTube tokens 該加密但目前沒加密、不在這份 warning 出現）
  "youtube_tokens.json"
)

# === 解析 v4 腳本的同步清單（grep 出 if [[ -d/rsync/cp 段） ===

# 1. 根目錄單檔（從 ROOT_SINGLE_FILES array 解析）
parse_root_files() {
  awk '/ROOT_SINGLE_FILES=\(/{flag=1; next} flag && /\)/{flag=0} flag' "$V4_SCRIPT" \
    | sed -E 's/^[[:space:]]+//; s/^"//; s/"$//' \
    | grep -v '^$'
}

# 2. v4 同步的目錄（從 "$HERMES_HOME/<dir>/" 模式解析）
parse_v4_dirs() {
  grep -oE '"\$HERMES_HOME/[a-z_]+/"' "$V4_SCRIPT" \
    | sed -E 's/"\$HERMES_HOME\///; s|/"$||' \
    | sort -u
}

# 3. v4 同步的 cache 子目錄（從 "$HERMES_HOME/cache/<sub>/" 模式）
parse_v4_cache_subdirs() {
  grep -oE '"\$HERMES_HOME/cache/[a-z_]+/"' "$V4_SCRIPT" \
    | sed -E 's|"\$HERMES_HOME/cache/||; s|/"$||' \
    | sort -u
}

ROOT_FILES_EXPECTED=($(parse_root_files))
DIRS_EXPECTED=($(parse_v4_dirs))
CACHE_SUBDIRS_EXPECTED=($(parse_v4_cache_subdirs))

# === 掃本機現況 ===
ACTUAL_ROOT_FILES=($(find "$HERMES_HOME" -maxdepth 1 -type f -printf "%f\n" | sort))
ACTUAL_DIRS=($(find "$HERMES_HOME" -maxdepth 1 -mindepth 1 -type d -printf "%f\n" | sort))
ACTUAL_CACHE_SUBDIRS=($(find "$HERMES_HOME/cache" -maxdepth 1 -mindepth 1 -type d -printf "%f\n" 2>/dev/null | sort))

# === 比對函式 ===
contains() {
  local needle="$1"
  shift
  for hay in "$@"; do
    [[ "$hay" == "$needle" ]] && return 0
  done
  return 1
}

# === 結果統計 ===
WARNINGS=()
ERRORS=()
NOTES=()

# --- Layer A: 本機有、v4 沒列（建議加） ---
for d in "${ACTUAL_DIRS[@]}"; do
  if contains "$d" "${EXCLUDE_DIRS[@]}"; then
    continue
  fi
  # 檢查是否是 cache 子目錄
  if [[ "$d" == "cache" ]]; then
    continue  # cache/ 本身、會被 cache_subdirs 處理
  fi
  if ! contains "$d" "${DIRS_EXPECTED[@]}"; then
    WARNINGS+=("📂 本機有目錄 '$d/' 但 v4 同步清單沒列（建議加）")
  fi
done

# cache 子目錄比對
for d in "${ACTUAL_CACHE_SUBDIRS[@]}"; do
  if contains "$d" "${EXCLUDE_CACHE_SUBDIRS[@]}"; then
    continue
  fi
  if ! contains "$d" "${CACHE_SUBDIRS_EXPECTED[@]}"; then
    WARNINGS+=("📂 cache/$d/ 本機有但 v4 沒列（建議加）")
  fi
done

# 根目錄單檔比對
for f in "${ACTUAL_ROOT_FILES[@]}"; do
  if contains "$f" "${EXCLUDE_ROOT_FILES[@]}"; then
    continue
  fi
  if ! contains "$f" "${ROOT_FILES_EXPECTED[@]}"; then
    WARNINGS+=("📄 根目錄有 '$f' 但 v4 ROOT_SINGLE_FILES 沒列（建議加）")
  fi
done

# --- Layer B: v4 有列、本機不存在（警告、可能剛搬走） ---
for d in "${DIRS_EXPECTED[@]}"; do
  if [[ ! -d "$HERMES_HOME/$d" ]] && [[ "$d" != "agents" ]]; then
    # agents/ 是 v4.5 之前的、目前可能不存在（被 profiles/ 取代）
    NOTES+=("ℹ️  v4 預期要備 '$d/' 但本機不存在（可能已搬走或不需要）")
  fi
done

for d in "${CACHE_SUBDIRS_EXPECTED[@]}"; do
  if [[ ! -d "$HERMES_HOME/cache/$d" ]]; then
    NOTES+=("ℹ️  v4 預期要備 'cache/$d/' 但本機不存在")
  fi
done

for f in "${ROOT_FILES_EXPECTED[@]}"; do
  if [[ ! -f "$HERMES_HOME/$f" ]]; then
    NOTES+=("ℹ️  v4 預期要備根目錄 '$f' 但本機不存在")
  fi
done

# --- Layer C: staging vs 本機（驗證同步狀態） ---
if [[ -d "$STAGING" ]]; then
  # staging 必須有 .git
  if [[ ! -d "$STAGING/.git" ]]; then
    ERRORS+=("❌ staging 不是 git repo: $STAGING")
  fi

  # staging 內的 archive/、config/、SOUL.md 應該跟本機 SHA256 一致
  check_file_match() {
    local rel="$1"
    if [[ -f "$HERMES_HOME/$rel" ]] && [[ -f "$STAGING/$rel" ]]; then
      local s1 s2
      s1=$(sha256sum "$HERMES_HOME/$rel" | cut -d' ' -f1)
      s2=$(sha256sum "$STAGING/$rel" | cut -d' ' -f1)
      if [[ "$s1" != "$s2" ]]; then
        WARNINGS+=("⚠️  '$rel' 本機跟 staging SHA256 不一致（staging 落後）")
      fi
    fi
  }
  check_file_match "config.yaml"
  check_file_match "SOUL.md"

  # staging 內 archive/、config/、handoff/、reports/ 應該存在
  for d in archive config handoff reports; do
    if [[ -d "$HERMES_HOME/$d" ]] && [[ ! -d "$STAGING/$d" ]]; then
      WARNINGS+=("⚠️  '$d/' 本機有但 staging 沒有（v4 同步沒跑、或剛加）")
    fi
  done
else
  ERRORS+=("❌ staging 目錄不存在: $STAGING")
fi

# === 輸出 ===

# 寫 log
{
  echo ""
  echo "=== Backup Coverage Check $(date -Iseconds) ==="
  echo "本機掃了: ${#ACTUAL_DIRS[@]} 個根目錄目錄, ${#ACTUAL_ROOT_FILES[@]} 個根目錄檔案"
  echo "v4 預期:   ${#DIRS_EXPECTED[@]} 個目錄 + ${#CACHE_SUBDIRS_EXPECTED[@]} 個 cache 子目錄 + ${#ROOT_FILES_EXPECTED[@]} 個根目錄單檔"
  echo ""

  if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    echo "--- WARNINGS (${#WARNINGS[@]}) ---"
    for w in "${WARNINGS[@]}"; do echo "  $w"; done
  fi

  if [[ ${#NOTES[@]} -gt 0 ]]; then
    echo "--- NOTES (${#NOTES[@]}) ---"
    for n in "${NOTES[@]}"; do echo "  $n"; done
  fi

  if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo "--- ERRORS (${#ERRORS[@]}) ---"
    for e in "${ERRORS[@]}"; do echo "  $e"; done
  fi
} >> "$LOG" 2>&1

# 終端輸出（給 cron 看到）
if [[ ${#ERRORS[@]} -gt 0 ]]; then
  echo "❌ FAIL  備份完整性檢查失敗（${#ERRORS[@]} 個 error, ${#WARNINGS[@]} 個 warning）"
  echo "詳細: $LOG"
  exit 2

elif [[ ${#WARNINGS[@]} -gt 0 ]]; then
  echo "⚠️  WARN  備份覆蓋率不完整（${#WARNINGS[@]} 個 warning）"
  echo "建議修法："
  echo "  1. 看哪些本機新路徑 v4 沒列"
  echo "  2. 編輯 ~/.hermes/docs/INVENTORY.md 加進『v4 同步清單』"
  echo "  3. 編輯 ~/.hermes/scripts/hermes-backup-v4.sh 加 rsync 段"
  echo "詳細: $LOG"
  exit 1

else
  echo "✅ PASS  備份覆蓋率完整（${#ACTUAL_DIRS[@]} 個目錄 + ${#ACTUAL_ROOT_FILES[@]} 個根目錄檔案都有覆蓋）"
  exit 0
fi
