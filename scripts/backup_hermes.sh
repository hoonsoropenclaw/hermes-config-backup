#!/usr/bin/env bash
# ============================================================
# backup_hermes.sh - 赫米斯全狀態備份（2026-06-06 v2.0）
# 設計：產出兩個 tar.gz
#   1. hermes_backup_<ts>_public.tar.gz → GitHub 公開 repo（不含敏感/過大）
#   2. hermes_backup_<ts>_full.tar.gz   → Google Drive 加密（**全部**含 .env/源碼/state.db/GPG token）
#
# 觸發：hermes cron 每天 03:00（no-agent script 模式）
#
# 安全設計：
#   - Drive 版：rclone crypt 加密，裡面有 .env、加密 GPG token、hermes-agent 源碼、state.db
#   - GitHub 版：redact 任何 vcp_/ghp_/sk- 等 token pattern，**不**含 .env、源碼、state.db
#   - Drive 版的 tar 內含 RESTORE.md + restore_hermes.sh，讓 Drive 資料夾可自描述
# ============================================================

set -euo pipefail

# === 互斥鎖：防止同時間跑兩次 ===
LOCKFILE="$HERMES_HOME/backups/.backup.lock"
if [ -f "$LOCKFILE" ]; then
  LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCKFILE" 2>/dev/null || echo 0)))
  if [ "$LOCK_AGE" -lt 300 ]; then
    echo "❌ 備份正在執行中（鎖檔已存在，${LOCK_AGE}s）。退出。" | tee -a "$LOG_FILE"
    exit 0
  else
    echo "⚠️ 鎖檔已存在 ${LOCK_AGE}s（超過 5 分鐘），強制移除後重試" | tee -a "$LOG_FILE"
    rm -f "$LOCKFILE"
  fi
fi
trap 'rm -f "$LOCKFILE"' EXIT
touch "$LOCKFILE"

# === 設定 ===
HERMES_HOME="$HOME/.hermes"
SCRIPT_DIR="$HERMES_HOME/scripts"
BACKUP_BASE="$HERMES_HOME/backups"
LOG_DIR="$HERMES_HOME/logs"
RCLONE_CONF="$HOME/documents/rclone.conf"
RCLONE_REMOTE="crypt_hermes"
GITHUB_REPO_DIR="$HERMES_HOME/hermes-backup-staging"
GITHUB_REPO_URL="git@github.com:hoonsoropenclaw/hermes-config-backup.git"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/backup_${TIMESTAMP}.log"
PUBLIC_TARBALL="$BACKUP_BASE/hermes_backup_${TIMESTAMP}_public.tar.gz"
FULL_TARBALL="$BACKUP_BASE/hermes_backup_${TIMESTAMP}_full.tar.gz"

mkdir -p "$BACKUP_BASE" "$LOG_DIR"

# === 1. 預檢 ===
echo "[$(date +%T)] === 赫米斯備份開始 v2.0 (公開版 + 完整版) ===" | tee "$LOG_FILE"

for tool in rclone git python3 tar rsync gh; do
  if ! command -v "$tool" &>/dev/null; then
    echo "❌ 缺少工具: $tool" | tee -a "$LOG_FILE"
    exit 1
  fi
done

if [ ! -f "$RCLONE_CONF" ]; then
  echo "❌ 找不到 rclone config: $RCLONE_CONF" | tee -a "$LOG_FILE"
  exit 1
fi

if ! rclone listremotes --config "$RCLONE_CONF" 2>/dev/null | grep -q "^${RCLONE_REMOTE}:$"; then
  echo "❌ rclone remote ${RCLONE_REMOTE}: 不存在" | tee -a "$LOG_FILE"
  exit 1
fi

# === 2. 建立 staging 目錄（兩個版本分開） ===
STAGING_PUBLIC="$HERMES_HOME/backups/staging_public_${TIMESTAMP}"
STAGING_FULL="$HERMES_HOME/backups/staging_full_${TIMESTAMP}"
rm -rf "$STAGING_PUBLIC" "$STAGING_FULL"
mkdir -p "$STAGING_PUBLIC"/{config,memories,skills,scripts,data,docs}
mkdir -p "$STAGING_FULL"/{config,memories,skills,scripts,data,docs,full_backups}

# === 3. 複製到 PUBLIC staging（不含敏感/過大） ===
echo "[$(date +%T)] 複製檔案到 PUBLIC staging..." | tee -a "$LOG_FILE"

# 配置
cp "$HERMES_HOME/config.yaml" "$STAGING_PUBLIC/config/hermes-config.yaml"
cp "$HERMES_HOME/cron/jobs.json" "$STAGING_PUBLIC/config/cron-jobs.json"

# .env 範本（key 全部 *** 化，公開版絕不含真實 key）
if [ -f "$HERMES_HOME/.env" ]; then
  echo "# .env 範本（真實 key 在 Drive 加密版）" > "$STAGING_PUBLIC/config/env-template"
  echo "# 還原時從各平台申請，貼到 ~/.hermes/.env（mode 0600）" >> "$STAGING_PUBLIC/config/env-template"
  echo "" >> "$STAGING_PUBLIC/config/env-template"
  grep -E "^[A-Z_]+_(KEY|TOKEN|SECRET|PASSWORD|BASE_URL|ENDPOINT)=" "$HERMES_HOME/.env" | \
    sed -E 's/=.*$/=<從 Drive 加密版取回或從平台申請>/' >> "$STAGING_PUBLIC/config/env-template"
fi

# 記憶（7 個核心 MD）
for f in USER MEMORY SOUL AGENTS IDENTITY HEARTBEAT TOOLS; do
  [ -f "$HERMES_HOME/memories/${f}.md" ] && cp "$HERMES_HOME/memories/${f}.md" "$STAGING_PUBLIC/memories/"
done

# 核心 skills（自建的 + 重要的，完整備份含 references）
for skill_dir in \
  "$HERMES_HOME/skills/autonomous-ai-agents/metacognitive-learner" \
  "$HERMES_HOME/skills/autonomous-ai-agents/persistent-subagent" \
  "$HERMES_HOME/skills/autonomous-ai-agents/hermes-agent" \
  "$HERMES_HOME/skills/hermes-tier-router" \
  "$HERMES_HOME/skills/trial-and-error" \
  "$HERMES_HOME/skills/alt-token-secrets-layout"; do
  if [ -d "$skill_dir" ]; then
    name=$(basename "$skill_dir")
    mkdir -p "$STAGING_PUBLIC/skills/$name"
    # 完整 rsync 整個 skill 資料夾（保留修改後版本）
    rsync -a --exclude='__pycache__/' --exclude='*.pyc' \
          "$skill_dir/" "$STAGING_PUBLIC/skills/$name/" 2>/dev/null || \
    cp -r "$skill_dir"/* "$STAGING_PUBLIC/skills/$name/" 2>/dev/null || true
  fi
done

# === 外部 skills（完整備份，不管是否修改過） ===
# 理由：使用者可能改過外部 skill 的 SKILL.md / scripts，未來重裝會拿原始版
# 2026-06-06 修正：之前只列名單，重裝會丟失修改
echo "[$(date +%T)] 完整備份所有外部 skills（保留修改）..." | tee -a "$LOG_FILE"

EXTERNAL_COUNT=0
EXTERNAL_TOTAL_SIZE=0
# 排除自建的 6 個 + 排除 sparc-methodology（已在 FULL 版備份 72 MB，PUBLIC 版太大不進）
EXCLUDE_DIRS=(
  "*/autonomous-ai-agents/metacognitive-learner"
  "*/autonomous-ai-agents/persistent-subagent"
  "*/autonomous-ai-agents/hermes-agent"
  "*/hermes-tier-router"
  "*/trial-and-error"
  "*/alt-token-secrets-layout"
  "*/sparc-methodology"  # PUBLIC 版不放（72 MB 太肥）
)

is_excluded() {
  local d="$1"
  for ex in "${EXCLUDE_DIRS[@]}"; do
    [[ "$d" == $ex ]] && return 0
  done
  return 1
}

# 寫 INSTALLED_MANIFEST.md 開頭
cat > "$STAGING_PUBLIC/skills/INSTALLED_MANIFEST.md" << 'EOF'
# 已安裝 Skills 清單

## 自建（隨 repo 完整還原）
- metacognitive-learner（自建）
- persistent-subagent（自建）
- hermes-agent（自建）
- hermes-tier-router（自建）
- trial-and-error（自建）
- alt-token-secrets-layout（自建）

## 外部安裝（**完整備份**保留任何修改）
> 2026-06-06 修：之前只列名單、改了就丟；現在完整備份 SKILL.md + references + scripts
EOF

# 掃描所有 SKILL.md，找出外部 skill 完整備份
find "$HERMES_HOME/skills" -maxdepth 4 -name "SKILL.md" 2>/dev/null | sort | while read skill_md; do
  skill_dir=$(dirname "$skill_md")

  # 跳過自建
  is_excluded "$skill_dir" && continue

  skill_name=$(basename "$skill_dir")
  # 算 skill 大小
  skill_size=$(du -sb "$skill_dir" 2>/dev/null | cut -f1)
  # 在 PUBLIC staging 建同結構
  rel_path="${skill_dir#$HERMES_HOME/skills/}"
  target_dir="$STAGING_PUBLIC/skills/$rel_path"
  mkdir -p "$target_dir"
  # 完整 rsync（保留修改）
  rsync -a --exclude='__pycache__/' --exclude='*.pyc' --exclude='node_modules/' \
        --exclude='.git/' \
        "$skill_dir/" "$target_dir/" 2>/dev/null || \
  cp -r "$skill_dir"/* "$target_dir/" 2>/dev/null || true

  # 寫入 manifest（含原始 source 資訊給未來參考）
  echo "- \`$rel_path\` → 完整備份 ($(numfmt --to=iec $skill_size 2>/dev/null || echo $skill_size) bytes)" >> "$STAGING_PUBLIC/skills/INSTALLED_MANIFEST.md"
done

EXTERNAL_COUNT=$(find "$STAGING_PUBLIC/skills" -name "SKILL.md" 2>/dev/null | wc -l)
echo "✓ 外部 skills 完整備份完成（共 $EXTERNAL_COUNT 個 skill，含自建 6 個）" | tee -a "$LOG_FILE"

# 腳本
[ -d "$HERMES_HOME/scripts" ] && {
  cp "$HERMES_HOME/scripts/"*.py "$STAGING_PUBLIC/scripts/" 2>/dev/null || true
  cp "$HERMES_HOME/scripts/"*.sh "$STAGING_PUBLIC/scripts/" 2>/dev/null || true
}

# kanban
[ -f "$HERMES_HOME/kanban.db" ] && cp "$HERMES_HOME/kanban.db" "$STAGING_PUBLIC/data/"

# 還原腳本跟 SOP
[ -f "$SCRIPT_DIR/backup_hermes.sh" ] && cp "$SCRIPT_DIR/backup_hermes.sh" "$STAGING_PUBLIC/scripts/"
[ -f "$SCRIPT_DIR/restore_hermes.sh" ] && cp "$SCRIPT_DIR/restore_hermes.sh" "$STAGING_PUBLIC/scripts/"
[ -f "$HERMES_HOME/docs/RESTORE.md" ] && cp "$HERMES_HOME/docs/RESTORE.md" "$STAGING_PUBLIC/docs/"

# === 3.5 PUBLIC 版的 secret 掃描 + redact ===
echo "[$(date +%T)] [PUBLIC] Redact 任何 token pattern..." | tee -a "$LOG_FILE"
find "$STAGING_PUBLIC" -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) -print0 | \
  xargs -0 perl -i -pe 's/(vcp_|ghp_|sk-|hms_|gho_|glpat-)[A-Za-z0-9_-]{20,}/[TOKEN_REDACTED]/g' 2>/dev/null || true

# === 4. 複製到 FULL staging（全部都進來，含敏感/過大） ===
echo "[$(date +%T)] 複製檔案到 FULL staging（含敏感/過大）..." | tee -a "$LOG_FILE"

# 先把 public 版的內容全 copy（-T 避免 dest 已存在的 subdir 內檔案衝突）
cp -r --no-target-directory "$STAGING_PUBLIC/" "$STAGING_FULL/"

# .env 真實檔（**只有 FULL 才有，公開版只有範本**）
if [ -f "$HERMES_HOME/.env" ]; then
  cp "$HERMES_HOME/.env" "$STAGING_FULL/config/hermes-env-real"
  chmod 600 "$STAGING_FULL/config/hermes-env-real"
  echo "  ✓ .env 真實檔（mode 600）" | tee -a "$LOG_FILE"
fi

# GPG 加密的 token 目錄（hoonsor 帳號的備用 PAT）
if [ -d "$HOME/.config/hermes/alt_gh_tokens" ]; then
  mkdir -p "$STAGING_FULL/full_backups/alt_gh_tokens"
  cp -r "$HOME/.config/hermes/alt_gh_tokens"/* "$STAGING_FULL/full_backups/alt_gh_tokens/" 2>/dev/null || true
  echo "  ✓ alt_gh_tokens (GPG 加密 token)" | tee -a "$LOG_FILE"
fi
# passphrase 檔
if [ -d "$HOME/.local/share/hermes/secrets" ]; then
  mkdir -p "$STAGING_FULL/full_backups/secrets"
  cp -r "$HOME/.local/share/hermes/secrets"/* "$STAGING_FULL/full_backups/secrets/" 2>/dev/null || true
  echo "  ✓ secrets (passphrase 檔)" | tee -a "$LOG_FILE"
fi

# hermes-agent 源碼（**含 venv**，災難還原可立即使用）
# 2026-06-06 修正：之前排除 venv 為了省空間，現在改包含
# 理由：災難時 venv 重建要 30-60 分鐘，沒時間；多 351 MB 換立即可用值得
if [ -d "$HERMES_HOME/hermes-agent" ]; then
  mkdir -p "$STAGING_FULL/full_backups/hermes-agent"
  rsync -a --exclude='__pycache__/' --exclude='*.pyc' \
        "$HERMES_HOME/hermes-agent/" "$STAGING_FULL/full_backups/hermes-agent/"
  HA_SIZE=$(du -sh "$STAGING_FULL/full_backups/hermes-agent" 2>/dev/null | cut -f1)
  echo "  ✓ hermes-agent 源碼 + venv（$HA_SIZE）" | tee -a "$LOG_FILE"
fi

# state.db（169 MB session store，**只進 Drive，不進 GitHub**）
if [ -f "$HERMES_HOME/state.db" ]; then
  cp "$HERMES_HOME/state.db" "$STAGING_FULL/full_backups/state.db"
  echo "  ✓ state.db (session store)" | tee -a "$LOG_FILE"
fi

# sparc-methodology（103 MB 外部 skill）
if [ -d "$HERMES_HOME/skills/sparc-methodology" ]; then
  mkdir -p "$STAGING_FULL/full_backups/sparc-methodology"
  rsync -a --exclude='__pycache__/' --exclude='*.pyc' \
        "$HERMES_HOME/skills/sparc-methodology/" \
        "$STAGING_FULL/full_backups/sparc-methodology/"
  echo "  ✓ sparc-methodology (103 MB 外部 skill)" | tee -a "$LOG_FILE"
fi

# venv, cache, logs, lsp, bin, sessions, models_dev_cache.json
# 這些太大且可重新生成，**只**在 FULL 進來
for d in venv venv64 cache logs lsp bin sessions; do
  if [ -d "$HERMES_HOME/$d" ]; then
    mkdir -p "$STAGING_FULL/full_backups/$d"
    rsync -a --exclude='*.pyc' --exclude='__pycache__/' \
          "$HERMES_HOME/$d/" "$STAGING_FULL/full_backups/$d/" 2>/dev/null || true
    echo "  ✓ $d/" | tee -a "$LOG_FILE"
  fi
done
[ -f "$HERMES_HOME/models_dev_cache.json" ] && cp "$HERMES_HOME/models_dev_cache.json" "$STAGING_FULL/full_backups/"

# === 4.5 FULL 版的 INVENTORY ===
cat > "$STAGING_FULL/full_backups/INVENTORY.md" << EOF
# Drive 加密版完整備份清單（2026-06-06 起）

這份清單列出本 tar.gz 內含的所有敏感/大型檔案。**本檔案只在 Drive 加密版出現，不進 GitHub。**

## 敏感資料
- \`config/hermes-env-real\` — 真實的 .env（12 個 API key），**mode 0600**
- \`full_backups/alt_gh_tokens/\` — GPG 加密的備用 GitHub PAT
- \`full_backups/secrets/\` — GPG passphrase 檔

## 源碼與大型檔案
- \`full_backups/hermes-agent/\` — Hermes Agent 源碼（排除 venv/，省 ~700 MB）
- \`full_backups/state.db\` — 169 MB session store（含完整對話紀錄）
- \`full_backups/sparc-methodology/\` — 103 MB 外部 skill 套件
- \`full_backups/{venv,cache,logs,lsp,bin,sessions}/\` — 衍生資料
- \`full_backups/models_dev_cache.json\` — 2.2 MB LLM 排行快取

## 還原用
- \`scripts/backup_hermes.sh\` — 這份備份腳本
- \`scripts/restore_hermes.sh\` — 還原腳本（依賴 rclone config）
- \`docs/RESTORE.md\` — 完整還原 SOP（含 Telegram session 警告）

## 還原流程摘要

1. **解密本 tar.gz**（rclone 已自動處理，rclone crypt_hermes 透明解密）
2. **解 tar**: \`tar -xzf hermes_backup_<ts>_full.tar.gz\`
3. **跑還原腳本**: \`bash restore_hermes.sh\`（會用 rclone 找其他備份）
4. **或手動**：
   - \`cp full_backups/hermes-agent/* ~/.hermes/hermes-agent/\`（跳過 venv）
   - \`cp full_backups/state.db ~/.hermes/\`
   - \`cp config/hermes-env-real ~/.hermes/.env\` + chmod 600
   - \`cp -r full_backups/alt_gh_tokens/ ~/.config/hermes/\`
   - \`cp -r full_backups/secrets/ ~/.local/share/hermes/\`
5. **詳見** \`docs/RESTORE.md\`

時間戳: $TIMESTAMP
EOF

# === 5. 打包 PUBLIC 版 ===
echo "[$(date +%T)] 打包 PUBLIC: $PUBLIC_TARBALL" | tee -a "$LOG_FILE"
cd "$HERMES_HOME/backups"
tar -czf "$PUBLIC_TARBALL" -C "$HERMES_HOME/backups" "staging_public_${TIMESTAMP}"
rm -rf "$STAGING_PUBLIC"
echo "✓ PUBLIC 完成: $(du -h "$PUBLIC_TARBALL" | cut -f1)" | tee -a "$LOG_FILE"

# === 6. 打包 FULL 版 ===
echo "[$(date +%T)] 打包 FULL: $FULL_TARBALL" | tee -a "$LOG_FILE"
tar -czf "$FULL_TARBALL" -C "$HERMES_HOME/backups" "staging_full_${TIMESTAMP}"
rm -rf "$STAGING_FULL"
echo "✓ FULL 完成: $(du -h "$FULL_TARBALL" | cut -f1)" | tee -a "$LOG_FILE"

# === 7. Secret 掃描驗證（兩個都掃，但用 tar -xOf 一次解避免慢） ===
SECRET_REGEX='vcp_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{40,}|hms_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20,}'

echo "[$(date +%T)] 掃描 PUBLIC 版是否還有 token（直接 grep 整個 tar）..." | tee -a "$LOG_FILE"
# 改用 tar -xOf --to-stdout 全檔解 + grep（不 xargs 每檔呼叫一次 tar）
if tar -xzOf "$PUBLIC_TARBALL" 2>/dev/null | grep -E "$SECRET_REGEX" >/dev/null 2>&1; then
  echo "❌ ABORT: PUBLIC 版還有 token！要加 redact" | tee -a "$LOG_FILE"
  exit 1
fi
echo "✓ PUBLIC 乾淨" | tee -a "$LOG_FILE"

# === 8. 清理 7 天前的本地備份（兩種都清） ===
find "$BACKUP_BASE" -maxdepth 1 -name "hermes_backup_*.tar.gz" -mtime +7 -delete 2>/dev/null
LOCAL_COUNT=$(find "$BACKUP_BASE" -maxdepth 1 -name "hermes_backup_*.tar.gz" | wc -l)
echo "✓ 本地保留 $LOCAL_COUNT 份" | tee -a "$LOG_FILE"

# === 9. rclone 加密上傳 FULL 版到 Google Drive ===
echo "[$(date +%T)] rclone 加密上傳 FULL 版..." | tee -a "$LOG_FILE"
DRIVE_FOLDER="hermes_backup_${TIMESTAMP}_full"
RCLONE_TARGET="${RCLONE_REMOTE}:${DRIVE_FOLDER}/"
rclone copy "$FULL_TARBALL" "$RCLONE_TARGET" \
  --config "$RCLONE_CONF" \
  --progress \
  --stats-one-line \
  --stats 30s \
  2>&1 | tee -a "$LOG_FILE"
# 也把 RESTORE.md 跟 restore script 額外複製一份到 Drive（讓 Drive 資料夾可自描述）
[ -f "$HERMES_HOME/docs/RESTORE.md" ] && rclone copy "$HERMES_HOME/docs/RESTORE.md" "$RCLONE_TARGET" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"
[ -f "$SCRIPT_DIR/restore_hermes.sh" ] && rclone copy "$SCRIPT_DIR/restore_hermes.sh" "${RCLONE_TARGET}restore_hermes.sh/" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"

# === 9.5 把 README 跟一鍵還原腳本放到 Drive 根目錄（hermes-backup/） ===
# Drive 結構：
#   hermes-backup/                                    ← 根
#   ├── HERMES-BACKUP-README.md                       ← 跨備份的說明
#   ├── hermes-restore.sh                             ← 一鍵還原腳本
#   └── hermes_backup_<ts>_full/                      ← 每次備份一個資料夾
#       ├── hermes_backup_<ts>_full.tar.gz
#       ├── RESTORE.md
#       └── restore_hermes.sh/
DRIVE_ROOT="${RCLONE_REMOTE}:"
[ -f "$HERMES_HOME/docs/HERMES-BACKUP-README.md" ] && rclone copy "$HERMES_HOME/docs/HERMES-BACKUP-README.md" "$DRIVE_ROOT" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"
[ -f "$SCRIPT_DIR/hermes-restore.sh" ] && rclone copy "$SCRIPT_DIR/hermes-restore.sh" "$DRIVE_ROOT" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"
echo "✓ Drive 根目錄 README + 一鍵還原腳本已同步" | tee -a "$LOG_FILE"
echo "✓ Drive 上傳: $RCLONE_TARGET" | tee -a "$LOG_FILE"

# === 9.6 latest.tar.gz 鏡像策略（2026-06-06 暫停） ===
# 2026-06-06 修：rclone 1.60 對大檔 latest 同步容易卡 + Drive rate limit
# 改回：restore 腳本掃時間戳目錄找最新（簡單可靠）
# 保留這段註解、未來 rclone/Drive 改善可重啟用
# LATEST_LINK="${RCLONE_REMOTE}:hermes_backup_latest.tar.gz"
# rclone copy "$FULL_TARBALL" "$LATEST_LINK" --config "$RCLONE_CONF" --stats-one-line --stats 30s 2>&1 | tee -a "$LOG_FILE"

# === 10. GitHub push PUBLIC 版 ===
echo "[$(date +%T)] GitHub push PUBLIC 版..." | tee -a "$LOG_FILE"

GIT_STAGING="$HERMES_HOME/backups/git_staging_${TIMESTAMP}"
rm -rf "$GIT_STAGING"
mkdir -p "$GIT_STAGING"
tar -xzf "$PUBLIC_TARBALL" -C "$GIT_STAGING" --strip-components=1

if [ -d "$GITHUB_REPO_DIR/.git" ]; then
  cd "$GITHUB_REPO_DIR"
  git pull origin main --rebase 2>&1 | tee -a "$LOG_FILE"
else
  rm -rf "$GITHUB_REPO_DIR"
  if gh repo view hoonsoropenclaw/hermes-config-backup &>/dev/null; then
    git clone "$GITHUB_REPO_URL" "$GITHUB_REPO_DIR" 2>&1 | tee -a "$LOG_FILE"
  else
    gh repo create hoonsoropenclaw/hermes-config-backup --public --description '赫米斯全狀態備份（公開版，敏感/大型在 Drive 加密版）' --source "$GIT_STAGING" --remote origin --push 2>&1 | tee -a "$LOG_FILE" || {
      echo "❌ GitHub repo 自動建立失敗" | tee -a "$LOG_FILE"
      exit 1
    }
  fi
fi

rsync -a --delete --exclude='.git' "$GIT_STAGING"/ "$GITHUB_REPO_DIR"/

cd "$GITHUB_REPO_DIR"
git add -A
if git diff --staged --quiet; then
  echo "✓ GitHub 沒變化" | tee -a "$LOG_FILE"
else
  git commit -m "backup: ${TIMESTAMP} (public)" 2>&1 | tee -a "$LOG_FILE"
  git push origin main 2>&1 | tee -a "$LOG_FILE"
  echo "✓ GitHub push 完成" | tee -a "$LOG_FILE"
fi
rm -rf "$GIT_STAGING"

# === 11. 清理 Drive 14 天前的備份（保留最近 14 份） ===
echo "[$(date +%T)] 清理 Drive 上舊備份..." | tee -a "$LOG_FILE"
REMOTE_BACKUPS=$(rclone lsf "${RCLONE_REMOTE}:" --dirs-only --config "$RCLONE_CONF" 2>/dev/null | grep "^hermes_backup_.*_full$" | sort)
COUNT=$(echo "$REMOTE_BACKUPS" | grep -c .)
if [ "$COUNT" -gt 14 ]; then
  DELETE_LIST=$(echo "$REMOTE_BACKUPS" | head -n $((COUNT - 14)))
  for dir in $DELETE_LIST; do
    dir=$(echo "$dir" | tr -d '\r')
    echo "  刪除: $dir" | tee -a "$LOG_FILE"
    rclone purge "${RCLONE_REMOTE}:${dir}" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"
  done
fi
echo "✓ Drive 保留 $COUNT 份加密備份" | tee -a "$LOG_FILE"

# === 12. 完成 ===
echo "[$(date +%T)] === 赫米斯備份完成 v2.0 ===" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📦 兩個版本產出：" | tee -a "$LOG_FILE"
echo "   PUBLIC: $PUBLIC_TARBALL ($(du -h "$PUBLIC_TARBALL" | cut -f1)) → GitHub" | tee -a "$LOG_FILE"
echo "   FULL:   $FULL_TARBALL ($(du -h "$FULL_TARBALL" | cut -f1)) → Google Drive（加密）" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "🔗 還原入口：" | tee -a "$LOG_FILE"
echo "   GitHub: https://github.com/hoonsoropenclaw/hermes-config-backup" | tee -a "$LOG_FILE"
echo "   Drive:  rclone crypt_hermes:hermes_backup_<ts>_full/" | tee -a "$LOG_FILE"
