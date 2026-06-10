#!/usr/bin/env bash
# hermes-backup-v4.sh
# v4 統一備份入口：Tier 1 (GitHub) + Tier 2 (Drive encrypted)
#
# 用法：
#   hermes-backup-v4.sh                  # 跑完整流程（GitHub + secrets encrypt）
#   hermes-backup-v4.sh --tier1          # 只推 GitHub（增量）
#   hermes-backup-v4.sh --tier2          # 只跑 Drive secrets 加密
#   hermes-backup-v4.sh --upload-tier2   # 加密完推到 Drive
#   hermes-backup-v4.sh --dry-run        # 看會做什麼但不做
#
# 排程建議（cron）：
#   每天 02:00 跑 tier1（增量 git push）
#   每週日 03:00 跑 tier2（加密 tar.gz → Drive）

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
STAGING="$HERMES_HOME/hermes-backup-staging"
GITHUB_REPO="hermes-config-backup"

# 顏色
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; CYN='\033[0;36m'; NC='\033[0m'

DRY_RUN=false
DO_TIER1=true
DO_TIER2=true
DO_UPLOAD_T2=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --tier1) DO_TIER2=false; shift ;;
    --tier2) DO_TIER1=false; shift ;;
    --upload-tier2) DO_UPLOAD_T2=true; shift ;;
    -h|--help) head -16 "$0" | tail -14; exit 0 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

log()  { echo -e "${CYN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GRN}[$(date +%H:%M:%S)] ✓${NC} $*"; }
warn() { echo -e "${YLW}[$(date +%H:%M:%S)] ⚠${NC} $*"; }
err()  { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $*" >&2; }

run_or_dry() {
  if $DRY_RUN; then
    echo -e "${YLW}[DRY]${NC} $*"
  else
    eval "$@"
  fi
}

# ===================== Tier 1: GitHub =====================
tier1_github() {
  log "=== Tier 1: GitHub (staging → hoonsoropenclaw/$GITHUB_REPO) ==="

  if [[ ! -d "$STAGING/.git" ]]; then
    err "staging 不是 git repo: $STAGING"
    return 1
  fi

  cd "$STAGING"

  # 1. 同步本地 ~/.hermes/ 變動到 staging（增量）
  log "Step 1: 同步 ~/.hermes/ 變動到 staging..."

  # 同步 config.yaml（單檔）
  if [[ -f "$HERMES_HOME/config.yaml" ]]; then
    run_or_dry cp -f "$HERMES_HOME/config.yaml" "$STAGING/config.yaml"
  fi

  # 同步 agents/
  if [[ -d "$HERMES_HOME/agents" ]]; then
    run_or_dry rsync -au --delete \
      --exclude='__DEPRECATED__*' \
      "$HERMES_HOME/agents/" "$STAGING/agents/"
  fi

  # 同步 memories/（排除 .bak / .lock / .clean / __DEPRECATED__）
  if [[ -d "$HERMES_HOME/memories" ]]; then
    run_or_dry rsync -au --delete \
      --exclude='*.bak.*' --exclude='*.lock' --exclude='*.clean.*' \
      --exclude='__DEPRECATED__*' \
      "$HERMES_HOME/memories/" "$STAGING/memories/"
  fi

  # 同步 scripts/
  if [[ -d "$HERMES_HOME/scripts" ]]; then
    run_or_dry rsync -au --delete \
      --exclude='*.bak' --exclude='*.pyc' \
      --exclude='__DEPRECATED__*' \
      "$HERMES_HOME/scripts/" "$STAGING/scripts/"
  fi

  # 同步 cron/（v4.1：jobs.json 很重要、是排程配置）
  if [[ -d "$HERMES_HOME/cron" ]]; then
    run_or_dry rsync -au --delete \
      --exclude='*.bak' --exclude='*.bak.*' \
      --exclude='output/' \
      --exclude='__DEPRECATED__*' \
      "$HERMES_HOME/cron/" "$STAGING/cron/"
  fi

  # 同步 docs/
  if [[ -d "$HERMES_HOME/docs" ]]; then
    run_or_dry rsync -au --delete \
      --exclude='__DEPRECATED__*' \
      "$HERMES_HOME/docs/" "$STAGING/docs/"
  fi

  # 同步 profiles/（v4.2：常駐子代理的整套配置 — persona/SOUL/ARCHITECTURE/skill庫/記憶）
  if [[ -d "$HERMES_HOME/profiles" ]]; then
    run_or_dry rsync -au --delete \
      --exclude='*.bak.*' --exclude='*.lock' --exclude='*.clean.*' \
      --exclude='.curator_backups/' --exclude='.archive/' --exclude='.hub/' \
      --exclude='.usage.json' --exclude='.bundled_manifest' --exclude='.curator_state' \
      --exclude='__pycache__/' --exclude='*.pyc' --exclude='venv/' \
      --exclude='state.db' --exclude='state.db-shm' --exclude='state.db-wal' \
      --exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip' --exclude='*.7z' \
      --exclude='models_dev_cache.json' --exclude='home/' --exclude='logs/' \
      --exclude='__DEPRECATED__*' \
      "$HERMES_HOME/profiles/" "$STAGING/profiles/"
  fi

  # 同步 skills/（v4.1：明確排除 hermes-agent 上游 clone、venv、cache、大檔）
  # 注意：
  #   - hermes-agent/ 不在 $HERMES_HOME/skills/ 內、它直接是 $HERMES_HOME/hermes-agent/
  #   - 所以這個 rsync 只同步 skills/、不會把 hermes-agent 抓進來
  #   - 但 .gitignore 仍寫 hermes-agent/ 排除、防止萬一（多層防禦）
  #   - sparc-methodology 是 $HERMES_HOME/skills/sparc-methodology/、會被同步
  #     （snapshot 模式、已排除 .git/ 跟 agentdb.rvf）
  # v4.3：加 --max-size 50m（GitHub 拒絕 > 100MB 物件,保險起見 50m 上限）
  # v4.4：加 v3/ 排除 + ruflo/ 排除（sparc-methodology 整體 78MB,內含大量 wasm/gif,屬可 rebuild）
  if [[ -d "$HERMES_HOME/skills" ]]; then
    run_or_dry rsync -au --delete --max-size=50m \
      --exclude='.git/' \
      --exclude='__pycache__/' \
      --exclude='.archive/' \
      --exclude='.curator_backups/' \
      --exclude='.bundled_manifest' \
      --exclude='.curator_state' \
      --exclude='.hub/' \
      --exclude='.usage.json' \
      --exclude='.claude-plugin/' \
      --exclude='_meta/' \
      --exclude='*.pyc' \
      --exclude='agentdb.rvf' --exclude='agentdb.rvf.lock' \
      --exclude='venv/' \
      --exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip' --exclude='*.7z' \
      --exclude='package-lock.json' --exclude='yarn.lock' --exclude='pnpm-lock.yaml' \
      --exclude='sparc-methodology/v3/' \
      --exclude='sparc-methodology/ruflo/' \
      "$HERMES_HOME/skills/" "$STAGING/skills/"
  fi

  # v4.1 顯式說明：hermes-agent/ 整個不備份（雖然不在 skills 同步範圍、但加註解）
  # 因為 hermes-agent 是 NousResearch upstream clone、git pull 可重建
  # 詳細見 trial-and-error/hermes-backup-strategy.md 的 v4.1 修正段

  # 2. git add + commit
  log "Step 2: git add + commit"
  run_or_dry git add -A

  if git diff --cached --quiet 2>/dev/null && ! $DRY_RUN; then
    ok "沒有變動、跳過 commit"
  else
    local msg="backup: $(date -u +%Y%m%d_%H%M%SZ) (v4 tier1 auto)"
    run_or_dry git commit -m "\"$msg\""
  fi

  # 3. git push
  log "Step 3: git push origin main"
  if $DRY_RUN; then
    echo "[DRY] git push origin main"
  else
    # 看完整 push 輸出、檢查 GH001/GH013/其他錯誤
    local push_output
    push_output=$(git push origin main 2>&1) || true
    echo "$push_output" | tail -10

    # GH013: secrets（已知需處理）
    if echo "$push_output" | grep -qE "GH013.*secrets"; then
      err "push 失敗（觸發 GH013 secrets leak）"
      err "請人工檢查：git status + git log"
      return 1
    fi

    # GH001: 大檔 > 100MB（已知需 .gitignore 排除）
    if echo "$push_output" | grep -qE "GH001.*Large files"; then
      err "push 失敗（檔案 > 100MB 超過 GitHub 限制）"
      err "請加進 .gitignore（看 hermes-backup-design-pitfalls#Rule 9）"
      return 1
    fi

    # 其他錯誤（pre-receive hook declined、non-fast-forward 等）
    if echo "$push_output" | grep -qE "(\[remote rejected\]|error:|fatal:)"; then
      err "push 失敗、看上面錯誤訊息"
      return 1
    fi

    ok "GitHub push 成功"
  fi
}

# ===================== Tier 2: Drive encrypted =====================
tier2_drive() {
  log "=== Tier 2: Drive (encrypted secrets) ==="

  # 直接呼叫 hermes-secrets-encrypt.sh
  local encrypt_script="$HERMES_HOME/scripts/hermes-secrets-encrypt.sh"

  if [[ ! -x "$encrypt_script" ]]; then
    err "找不到 $encrypt_script"
    return 1
  fi

  local args=()
  $DO_UPLOAD_T2 && args+=("--upload-drive")

  log "呼叫 hermes-secrets-encrypt.sh ${args[*]}"
  if $DRY_RUN; then
    echo "[DRY] $encrypt_script ${args[*]}"
  else
    "$encrypt_script" "${args[@]}"
  fi

  # v4.5：Tier 2 完成後，把 passphrase 檔也用 GPG 對稱加密備份到 Drive 獨立目錄
  # 解決「passphrase 沒備份、災難時無法異機還原」的致命漏洞
  # 雙目錄分離保留：secrets/ 還是被 GPG 加密的 .env 等、passphrase-recovery/ 是加密的 passphrase
  # 解 passphrase-recovery 需 USER_KEY(使用者記住的單一密碼,跟 GPG passphrase 不同)
  if ! $DRY_RUN; then
    backup_passphrase_recovery
    upload_drive_restore_readme
  fi
}

# v4.5.1：每次 Tier 2 完成時把 DRIVE-RESTORE.md 推到 Drive 根目錄
# 讓未來的 AI / 接手者 / 使用者打開 Drive 就能看到還原說明
upload_drive_restore_readme() {
  local restore_doc="$HERMES_HOME/docs/DRIVE-RESTORE.md"
  local drive_root="hoonsorasus:hermes-backup"

  if [[ ! -f "$restore_doc" ]]; then
    warn "找不到 $restore_doc、跳過 Drive 端還原說明上傳"
    return 0
  fi

  if ! $DO_UPLOAD_T2; then
    log "DRIVE-RESTORE.md 上傳跳過（需加 --upload-drive）"
    return 0
  fi

  log "上傳 DRIVE-RESTORE.md 到 Drive 根目錄..."
  rclone copy "$restore_doc" "$drive_root/" --transfers=1 --checkers=1 --tpslimit 5 2>&1 | tail -3
  ok "Drive 端還原說明已更新"
}

# v4.5：把 GPG passphrase 加密備份到 Drive 獨立目錄
# USER_KEY 取得順序（防止 cron 場景失敗）：
#   1. ${HERMES_USER_KEY} 環境變數
#   2. ~/.hermes/config/.hermes-user-key 環境變數檔(chmod 600)
#   3. 互動式 prompt(僅 -t 0)
# 若都沒有、跳過這步並警告
backup_passphrase_recovery() {
  local passphrase_file="$HOME/Documents/hermes-keys/.hermes_backup_passphrase"
  local recovery_dir="$HOME/.cache/hermes-passphrase-recovery"
  local recovery_gpg="$recovery_dir/passphrase-recovery-$(date -u +%Y%m%d_%H%M%SZ).gpg"
  local drive_remote="hoonsorasus:hermes-backup/passphrase-recovery"
  local user_key_env_file="$HOME/.hermes/config/.hermes-user-key"
  local user_key="${HERMES_USER_KEY:-}"

  # 從環境變數檔讀（cron 場景）
  if [[ -z "$user_key" ]] && [[ -f "$user_key_env_file" ]]; then
    user_key=$(cat "$user_key_env_file" 2>/dev/null | head -1)
    if [[ -n "$user_key" ]]; then
      log "USER_KEY 從 $user_key_env_file 讀取"
    fi
  fi

  if [[ ! -f "$passphrase_file" ]]; then
    warn "找不到 passphrase 檔 $passphrase_file、跳過 passphrase 備份"
    return 0
  fi

  # 互動式取得 USER_KEY（如果環境變數沒設）
  if [[ -z "$user_key" ]]; then
    if [[ -t 0 ]]; then
      echo ""
      echo "════════════════════════════════════════════════════════════"
      echo "  v4.5 passphrase 備份"
      echo ""
      echo "  這台 N100 硬碟如果壞掉,需要 USER_KEY 從 Drive 解開 passphrase"
      echo "  然後才能解開 secrets/*.tar.gpg"
      echo ""
      echo "  ⚠️  USER_KEY 跟 GPG passphrase 不同、是你自己選的一組密碼"
      echo "  ⚠️  建議跟你的密碼管理器(1Password)主密碼相同"
      echo "  ⚠️  千萬不要跟 GPG passphrase 相同"
      echo ""
      read -r -s -p "  請輸入 USER_KEY: " user_key
      echo ""
      read -r -s -p "  請再輸入一次確認: " user_key2
      echo ""
      if [[ "$user_key" != "$user_key2" ]]; then
        err "兩次 USER_KEY 不一致、跳過 passphrase 備份"
        return 1
      fi
    else
      warn "非互動式模式且 HERMES_USER_KEY 未設、跳過 passphrase 備份"
      warn "（手動跑 v4 backup 時會用互動式 prompt）"
      return 0
    fi
  fi

  mkdir -p "$recovery_dir"
  log "加密 passphrase → $recovery_gpg"
  gpg --batch --yes --pinentry-mode loopback \
    --symmetric --cipher-algo AES256 \
    --s2k-mode 3 --s2k-count 65011792 \
    --compress-algo none \
    --passphrase "$user_key" \
    --output "$recovery_gpg" \
    "$passphrase_file" 2>&1 | head -3

  if [[ ! -f "$recovery_gpg" ]]; then
    err "passphrase 加密失敗"
    return 1
  fi
  chmod 600 "$recovery_gpg"

  # Drive 上傳
  if $DO_UPLOAD_T2; then
    log "上傳 passphrase-recovery 到 Drive ..."
    rclone copy "$recovery_gpg" "$drive_remote/" --transfers=1 --checkers=1 --tpslimit 5 2>&1 | tail -3
    # 保留本地副本 3 份(新→舊)
    ls -1t "$recovery_dir"/passphrase-recovery-*.gpg 2>/dev/null | tail -n +4 | xargs -r rm -f
  else
    ok "passphrase-recovery 加密完成 (本地 $recovery_gpg)"
    echo "  上傳到 Drive 請加 --upload-drive flag"
  fi
}

# ===================== 主流程 =====================
main() {
  echo -e "${GRN}========================================${NC}"
  echo -e "${GRN}  Hermes Backup v4 (Tier 1 + Tier 2)  ${NC}"
  echo -e "${GRN}========================================${NC}"
  echo ""
  echo "Tier 1 (GitHub):   $DO_TIER1"
  echo "Tier 2 (Drive):    $DO_TIER2"
  echo "Upload Tier 2:     $DO_UPLOAD_T2"
  echo "Dry run:           $DRY_RUN"
  echo ""

  local exit_code=0

  if $DO_TIER1; then
    tier1_github || exit_code=1
    echo ""
  fi

  if $DO_TIER2; then
    tier2_drive || exit_code=1
    echo ""
  fi

  echo ""
  if [[ $exit_code -eq 0 ]]; then
    ok "備份完成"
  else
    err "備份有錯誤、請看上面訊息"
  fi

  return $exit_code
}

main "$@"
