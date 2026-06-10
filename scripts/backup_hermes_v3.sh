#!/usr/bin/env bash
# ============================================================
# backup_hermes_v3.sh - 赫米斯全狀態備份（2026-06-06 v3.0）
#
# v2 → v3 重大改變：
#   ❌ 不再產 694 MB 大 tar.gz（rclone crypt 下載超慢）
#   ✅ Drive 上用 rclone sync 保留目錄架構（增量、可差異還原）
#   ✅ 每次備份產 manifest（SHA256 清單）→ Drive v3/manifests/
#   ✅ 每周一份 snapshot（完整目錄鏡像）→ Drive v3/snapshots/YYYY_Www/
#   ✅ Drive v3/current/ 永遠是最新（增量同步）
#   ✅ 異機還原時用 rclone copy 挑目錄拉，不用下整包
#
# Drive 結構（v3）：
#   hermes-backup/v3/                       ← v3 根目錄
#   ├── current/                            ← 永遠最新（rclone sync 增量）
#   ├── manifests/                          ← 每次備份的 SHA256 清單
#   │   └── 2026-06-06T150000Z.manifest.gpg
#   └── snapshots/                          ← 每周一份完整鏡像
#       ├── 2026_W22/
#       ├── 2026_W23/
#       └── ...
#
# GitHub 結構（保持 v2 不變）：
#   hermes-config-backup repo              ← 公開版（redact + 排除大檔）
#
# 觸發：hermes cron 每天 03:00（no-agent script 模式）
# ============================================================

set -euo pipefail

# === 設定 ===
HERMES_HOME="$HOME/.hermes"
SCRIPT_DIR="$HERMES_HOME/scripts"
LOG_DIR="$HERMES_HOME/logs"
RCLONE_CONF="$HOME/documents/rclone.conf"
RCLONE_REMOTE="crypt_hermes"
GITHUB_REPO_DIR="$HERMES_HOME/hermes-backup-staging"
GITHUB_REPO_URL="git@github.com:hoonsoropenclaw/hermes-config-backup.git"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ISO_TIMESTAMP=$(date -u +%Y-%m-%dT%H%M%SZ)
WEEK_TAG=$(date +%Y_W%V)
LOG_FILE="$LOG_DIR/backup_v3_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# === Drive 路徑 ===
DRIVE_V3="${RCLONE_REMOTE}:hermes-backup/v3"
DRIVE_CURRENT="${DRIVE_V3}/current"
DRIVE_MANIFESTS="${DRIVE_V3}/manifests"
DRIVE_SNAPSHOTS="${DRIVE_V3}/snapshots"
DRIVE_SNAPSHOT_TODAY="${DRIVE_SNAPSHOTS}/${WEEK_TAG}"

# === 1. 預檢 ===
echo "[$(date +%T)] === 赫米斯備份開始 v3.0（目錄式 + manifest）===" | tee "$LOG_FILE"

for tool in rclone git python3 tar rsync gh sha256sum gpg; do
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

# === 2. 建立 Drive v3 目錄結構（首次）===
echo "[$(date +%T)] 確認 Drive v3 目錄結構..." | tee -a "$LOG_FILE"
rclone mkdir "$DRIVE_CURRENT" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE" || true
rclone mkdir "$DRIVE_MANIFESTS" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE" || true
rclone mkdir "$DRIVE_SNAPSHOTS" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE" || true

# === 3. 排除規則（不備份到 Drive 的東西）===
# 這些是 v3 排除清單：太大、可重新生成、不重要
RCLONE_EXCLUDES=(
  # 大且可重新生成
  "--exclude=backups/**"              # 本地備份（會無限增長）
  "--exclude=hermes-agent/venv/**"    # Python venv（351 MB、可重建）
  "--exclude=hermes-agent/venv64/**"
  "--exclude=hermes-agent/.venv/**"
  "--exclude=hermes-agent/**/__pycache__/**"
  "--exclude=hermes-agent/**/*.pyc"
  "--exclude=**/node_modules/**"      # Node.js 模組（隨時可 npm install）
  "--exclude=**/.git/**"              # Git metadata（不需備份，可從 remote pull）
  "--exclude=cache/**"                # 1.1 MB 快取
  "--exclude=logs/**"                 # 4.4 MB 日誌（會無限增長）
  "--exclude=lsp/**"                  # 26 MB LSP server
  "--exclude=bin/**"                  # 12 MB binary tools
  "--exclude=sessions/**"             # 8.5 MB 對話 cache
  "--exclude=state.db-wal"            # SQLite WAL（重建）
  "--exclude=models_dev_cache.json"   # 2.2 MB LLM 排行快取
  "--exclude=hermes-backup-staging/**"  # 48 MB / 2222 檔 git 鏡像（GitHub 已有）
  "--exclude=skills/.archive/**"      # 垃圾桶（80 KB 不需備份）
  # 元資料
  "--exclude=.tick.lock"
  "--exclude=**/.DS_Store"
  "--exclude=**/Thumbs.db"
)

echo "[$(date +%T)] 排除清單（v3 不備份這些）：" | tee -a "$LOG_FILE"
printf "  %s\n" "${RCLONE_EXCLUDES[@]}" | tee -a "$LOG_FILE"

# === 4. rclone sync 主目錄到 Drive v3/current/（增量）===
echo "[$(date +%T)] === rclone sync ~/.hermes/ → v3/current/（增量）===" | tee -a "$LOG_FILE"
START=$(date +%s)
rclone sync "$HERMES_HOME/" "$DRIVE_CURRENT/" \
  --config "$RCLONE_CONF" \
  --update \
  --progress \
  --stats-one-line \
  --stats 30s \
  --transfers=1 \
  --checkers=1 \
  --tpslimit 5 \
  --drive-pacer-min-sleep 100ms \
  "${RCLONE_EXCLUDES[@]}" \
  2>&1 | tee -a "$LOG_FILE"
SYNC_ELAPSED=$(($(date +%s) - START))
echo "✓ Drive sync 完成（${SYNC_ELAPSED} 秒）" | tee -a "$LOG_FILE"

# === 5. 產 manifest（SHA256 清單 + metadata）===
echo "[$(date +%T)] === 產生 manifest ===" | tee -a "$LOG_FILE"
MANIFEST_LOCAL="/tmp/hermes_manifest_${TIMESTAMP}.txt"
MANIFEST_ENC="/tmp/hermes_manifest_${TIMESTAMP}.txt.gpg"

{
  echo "# Hermes Backup Manifest v3.0"
  echo "# Generated: ${ISO_TIMESTAMP}"
  echo "# Hostname: $(hostname)"
  echo "# User: $(whoami)"
  echo "# Hermeshome: $HERMES_HOME"
  echo "# IsoWeek: $WEEK_TAG"
  echo "# Format: SHA256  <size>  <path>"
  echo "#"
  echo "# === Summary ==="
  echo "TotalFiles: $(find "$HERMES_HOME" -type f "${RCLONE_EXCLUDES[@]/#/! -path}" 2>/dev/null | wc -l)"
  echo "TotalSize: $(du -sb "$HERMES_HOME" 2>/dev/null | cut -f1) bytes"
  echo ""
  echo "# === File Hashes (sorted by path) ==="

  # 計算所有要備份檔案的 SHA256（套用同樣排除規則）
  find "$HERMES_HOME" -type f \
    -not -path "*/backups/*" \
    -not -path "*/hermes-agent/venv/*" \
    -not -path "*/hermes-agent/venv64/*" \
    -not -path "*/hermes-agent/.venv/*" \
    -not -path "*/__pycache__/*" \
    -not -name "*.pyc" \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/cache/*" \
    -not -path "*/logs/*" \
    -not -path "*/lsp/*" \
    -not -path "*/bin/*" \
    -not -path "*/sessions/*" \
    -not -name "state.db-wal" \
    -not -name "models_dev_cache.json" \
    -not -path "*/hermes-backup-staging/*" \
    -not -path "*/skills/.archive/*" \
    -not -name ".tick.lock" \
    -print0 2>/dev/null | sort -z | \
    xargs -0 sha256sum 2>/dev/null | \
    awk '{size=0; cmd="stat -c%s \""$2"\""; cmd | getline size; close(cmd); printf "%s  %d  %s\n", $1, size, $2}'
} > "$MANIFEST_LOCAL"

MANIFEST_SIZE=$(stat -c%s "$MANIFEST_LOCAL")
MANIFEST_FILES=$(grep -c "^[a-f0-9]\{64\}" "$MANIFEST_LOCAL" || echo 0)
echo "✓ Manifest 產出：${MANIFEST_LOCAL}" | tee -a "$LOG_FILE"
echo "  Size: $MANIFEST_SIZE bytes" | tee -a "$LOG_FILE"
echo "  Files: $MANIFEST_FILES" | tee -a "$LOG_FILE"

# === 6. GPG 加密 manifest（用 --passphrase-file 避免 env 洩漏）===
MANIFEST_PASS_FILE="$HOME/.local/share/hermes/secrets/manifest-passphrase"
echo "[$(date +%T)] 加密 manifest..." | tee -a "$LOG_FILE"
if [ ! -f "$MANIFEST_PASS_FILE" ]; then
  echo "❌ 找不到 GPG passphrase 檔：$MANIFEST_PASS_FILE" | tee -a "$LOG_FILE"
  echo "   建立方式：openssl rand -base64 32 | tr -d '\\n=' > $MANIFEST_PASS_FILE && chmod 600 $MANIFEST_PASS_FILE" | tee -a "$LOG_FILE"
  exit 1
fi

gpg --batch --yes --pinentry-mode loopback \
  --passphrase-file "$MANIFEST_PASS_FILE" \
  --symmetric --cipher-algo AES256 \
  --output "$MANIFEST_ENC" \
  "$MANIFEST_LOCAL" 2>&1 | tee -a "$LOG_FILE"
chmod 600 "$MANIFEST_ENC"
echo "✓ Manifest 加密完成：${MANIFEST_ENC}" | tee -a "$LOG_FILE"

# === 7. 上傳 manifest 到 Drive ===
echo "[$(date +%T)] 上傳 manifest 到 Drive..." | tee -a "$LOG_FILE"
rclone copy "$MANIFEST_ENC" "$DRIVE_MANIFESTS/" \
  --config "$RCLONE_CONF" \
  --progress 2>&1 | tee -a "$LOG_FILE"
echo "✓ Manifest 上傳完成" | tee -a "$LOG_FILE"

# === 8. 每周一份 snapshot（鏡像 current/）===
# 邏輯：檢查這個 week tag 是否已存在 snapshot
#  - 不存在 → 從 current/ 複製整個到 snapshots/<week_tag>/
#  - 已存在 → 跳過（覆蓋會破壞週歷史）
# 用 rclone copy 一次寫入（不是 sync，避免意外刪除）
NEED_SNAPSHOT=$(rclone lsf "$DRIVE_SNAPSHOTS/" --dirs-only --config "$RCLONE_CONF" 2>/dev/null | grep -c "^${WEEK_TAG}/$" || echo 0)

if [ "$NEED_SNAPSHOT" = "0" ]; then
  echo "[$(date +%T)] === 建立本週 snapshot：${WEEK_TAG} ===" | tee -a "$LOG_FILE"
  # 先建空目錄（rclone copy 不會建空 source → dest）
  rclone mkdir "$DRIVE_SNAPSHOT_TODAY" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"

  START=$(date +%s)
  # 用 rclone copy 從 local 一次寫入（不刪除遠端）
  rclone copy "$HERMES_HOME/" "$DRIVE_SNAPSHOT_TODAY/" \
    --config "$RCLONE_CONF" \
    --transfers=1 \
    --checkers=1 \
    --tpslimit 5 \
    --drive-pacer-min-sleep 100ms \
    --stats-one-line \
    --stats 30s \
    "${RCLONE_EXCLUDES[@]}" \
    2>&1 | tee -a "$LOG_FILE"
  SNAP_ELAPSED=$(($(date +%s) - START))
  echo "✓ Snapshot 建立完成（${SNAP_ELAPSED} 秒）" | tee -a "$LOG_FILE"
else
  echo "[$(date +%T)] 本週 snapshot（${WEEK_TAG}）已存在，跳過" | tee -a "$LOG_FILE"
fi

# === 9. 驗證 Drive 內容（rclone check 本機 vs current）===
echo "[$(date +%T)] === 驗證 Drive current/ vs 本機 ===" | tee -a "$LOG_FILE"
# 只驗證大小（不驗證 hash，crypt remote 已經加密沒法比對原始 hash）
rclone check "$HERMES_HOME/" "$DRIVE_CURRENT/" \
  --config "$RCLONE_CONF" \
  --one-way \
  "${RCLONE_EXCLUDES[@]}" \
  2>&1 | tee -a "$LOG_FILE" || {
  echo "⚠ Drive check 發現差異（見上方），可能是新檔尚未同步或 Drive 端問題" | tee -a "$LOG_FILE"
}

# === 10. 清理 Drive 舊 snapshot（保留最近 14 份 = 約 14 週 = 約 3 個月） ===
echo "[$(date +%T)] 清理 Drive 舊 snapshots（保留 14 份）..." | tee -a "$LOG_FILE"
REMOTE_SNAPS=$(rclone lsf "$DRIVE_SNAPSHOTS/" --dirs-only --config "$RCLONE_CONF" 2>/dev/null | sort)
SNAP_COUNT=$(echo "$REMOTE_SNAPS" | grep -c .)
if [ "$SNAP_COUNT" -gt 14 ]; then
  DELETE_LIST=$(echo "$REMOTE_SNAPS" | head -n $((SNAP_COUNT - 14)))
  for snap in $DELETE_LIST; do
    snap=$(echo "$snap" | tr -d '\r')
    echo "  刪除舊 snapshot: $snap" | tee -a "$LOG_FILE"
    rclone purge "${DRIVE_SNAPSHOTS}/${snap}" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"
  done
fi
echo "✓ Drive 保留 $(echo "$REMOTE_SNAPS" | tail -14 | wc -l) 份 snapshots" | tee -a "$LOG_FILE"

# === 11. 清理 Drive 舊 manifest（保留最近 30 份 = 30 天） ===
echo "[$(date +%T)] 清理 Drive 舊 manifests（保留 30 份）..." | tee -a "$LOG_FILE"
REMOTE_MANIFESTS=$(rclone lsf "$DRIVE_MANIFESTS/" --files-only --config "$RCLONE_CONF" 2>/dev/null | sort)
M_COUNT=$(echo "$REMOTE_MANIFESTS" | grep -c .)
if [ "$M_COUNT" -gt 30 ]; then
  DELETE_LIST=$(echo "$REMOTE_MANIFESTS" | head -n $((M_COUNT - 30)))
  for m in $DELETE_LIST; do
    m=$(echo "$m" | tr -d '\r')
    rclone deletefile "${DRIVE_MANIFESTS}/${m}" --config "$RCLONE_CONF" 2>&1 | tee -a "$LOG_FILE"
  done
fi
echo "✓ Drive 保留最近 $(echo "$REMOTE_MANIFESTS" | tail -30 | wc -l) 份 manifests" | tee -a "$LOG_FILE"

# === 12. GitHub push PUBLIC 版（保持 v2 邏輯不變）===
echo "[$(date +%T)] === GitHub push PUBLIC 版 ===" | tee -a "$LOG_FILE"

# 重用 v2 的邏輯（在背景跑，不阻擋 Drive 進度）
PUBLIC_TARBALL="/tmp/hermes_public_${TIMESTAMP}.tar.gz"
GIT_STAGING="/tmp/hermes_git_staging_${TIMESTAMP}"
rm -rf "$GIT_STAGING"
mkdir -p "$GIT_STAGING"

# 簡化版 PUBLIC 版內容（小、redact 後可上 GitHub）
mkdir -p "$GIT_STAGING"/{config,memories,skills,scripts,data,docs}
[ -f "$HERMES_HOME/config.yaml" ] && cp "$HERMES_HOME/config.yaml" "$GIT_STAGING/config/hermes-config.yaml"
[ -f "$HERMES_HOME/cron/jobs.json" ] && cp "$HERMES_HOME/cron/jobs.json" "$GIT_STAGING/config/cron-jobs.json"

# .env 範本
if [ -f "$HERMES_HOME/.env" ]; then
  echo "# .env 範本（真實 key 在 Drive v3/current/config/）" > "$GIT_STAGING/config/env-template"
  echo "# 還原時從 Drive 加密版取回" >> "$GIT_STAGING/config/env-template"
  echo "" >> "$GIT_STAGING/config/env-template"
  grep -E "^[A-Z_]+_(KEY|TOKEN|SECRET|PASSWORD|BASE_URL|ENDPOINT)=" "$HERMES_HOME/.env" | \
    sed -E 's/=.*$/=<從 Drive v3 取回>/' >> "$GIT_STAGING/config/env-template"
fi

# 核心 memories
for f in USER MEMORY SOUL AGENTS IDENTITY HEARTBEAT TOOLS; do
  [ -f "$HERMES_HOME/memories/${f}.md" ] && cp "$HERMES_HOME/memories/${f}.md" "$GIT_STAGING/memories/"
done

# 核心 skills（自建 + 小型外部）
for skill_dir in \
  "$HERMES_HOME/skills/autonomous-ai-agents/metacognitive-learner" \
  "$HERMES_HOME/skills/autonomous-ai-agents/persistent-subagent" \
  "$HERMES_HOME/skills/autonomous-ai-agents/hermes-agent" \
  "$HERMES_HOME/skills/hermes-tier-router" \
  "$HERMES_HOME/skills/trial-and-error" \
  "$HERMES_HOME/skills/alt-token-secrets-layout" \
  "$HERMES_HOME/skills/general-workflow" \
  "$HERMES_HOME/skills/connection-resilience" \
  "$HERMES_HOME/skills/anti-panic-protocol"; do
  if [ -d "$skill_dir" ]; then
    name=$(basename "$skill_dir")
    mkdir -p "$GIT_STAGING/skills/$name"
    rsync -a --exclude='__pycache__/' --exclude='*.pyc' \
          "$skill_dir/" "$GIT_STAGING/skills/$name/" 2>/dev/null || true
  fi
done

# 腳本
[ -d "$HERMES_HOME/scripts" ] && {
  cp "$HERMES_HOME/scripts/"*.py "$GIT_STAGING/scripts/" 2>/dev/null || true
  cp "$HERMES_HOME/scripts/"*.sh "$GIT_STAGING/scripts/" 2>/dev/null || true
}

# 還原用文件
[ -f "$SCRIPT_DIR/hermes-restore.sh" ] && cp "$SCRIPT_DIR/hermes-restore.sh" "$GIT_STAGING/scripts/"
[ -f "$SCRIPT_DIR/restore_hermes.sh" ] && cp "$SCRIPT_DIR/restore_hermes.sh" "$GIT_STAGING/scripts/"
[ -f "$SCRIPT_DIR/backup_hermes_v3.sh" ] && cp "$SCRIPT_DIR/backup_hermes_v3.sh" "$GIT_STAGING/scripts/"
[ -f "$HERMES_HOME/docs/RESTORE.md" ] && cp "$HERMES_HOME/docs/RESTORE.md" "$GIT_STAGING/docs/"

# 寫 v3 README
cat > "$GIT_STAGING/docs/V3-BACKUP-README.md" << 'EOF'
# Hermes Backup v3.0（2026-06-06 起）

## 架構改變（vs v2）
- ❌ **不再產 694 MB 大 tar.gz** — rclone crypt 下載超慢（191 KiB/s、需 58 分鐘）
- ✅ **Drive 上用 rclone sync 保留目錄架構** — 增量、可差異還原
- ✅ **每次備份產 manifest（SHA256 清單）** — 加密後上 Drive
- ✅ **每周一份 snapshot** — 完整目錄鏡像，保留 14 份
- ✅ **異機還原時用 rclone copy 挑目錄拉** — 不用下整包

## Drive v3 結構
```
hermes-backup/v3/
├── current/                    ← 永遠最新（rclone sync 增量）
├── manifests/                  ← 每次備份的 SHA256 清單（加密 .gpg）
│   └── 2026-06-06T150000Z.txt.gpg
└── snapshots/                  ← 每周一份完整鏡像
    ├── 2026_W22/
    ├── 2026_W23/
    └── ...
```

## 異機還原範例
```bash
# 1. 只還原核心設定（5-10 分鐘）
rclone copy crypt_hermes:hermes-backup/v3/current/config/ ~/.hermes/config/
rclone copy crypt_hermes:hermes-backup/v3/current/cron/ ~/.hermes/cron/
rclone copy crypt_hermes:hermes-backup/v3/current/scripts/ ~/.hermes/scripts/

# 2. 還原 skills（依需求挑）
rclone copy crypt_hermes:hermes-backup/v3/current/skills/metacognitive-learner/ \
  ~/.hermes/skills/metacognitive-learner/

# 3. 完整還原某週 snapshot
rclone copy crypt_hermes:hermes-backup/v3/snapshots/2026_W23/ ~/.hermes/

# 4. 驗證還原
bash ~/.hermes/scripts/hermes-restore.sh --verify-only
```

## 排除清單（v3 不備份）
- `backups/`, `cache/`, `logs/`, `lsp/`, `bin/`, `sessions/`
- `hermes-agent/venv/`, `hermes-agent/venv64/`, `hermes-agent/.venv/`
- `state.db-wal`, `models_dev_cache.json`
- `__pycache__/`, `*.pyc`
EOF

# Secret 掃描 + redact
echo "[$(date +%T)] [PUBLIC] Redact token pattern..." | tee -a "$LOG_FILE"
find "$GIT_STAGING" -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) -print0 | \
  xargs -0 perl -i -pe 's/(vcp_|ghp_|sk-|hms_|gho_|glpat-)[A-Za-z0-9_-]{20,}/[TOKEN_REDACTED]/g' 2>/dev/null || true

# 打包
echo "[$(date +%T)] 打包 PUBLIC 版..." | tee -a "$LOG_FILE"
tar -czf "$PUBLIC_TARBALL" -C "$(dirname "$GIT_STAGING")" "$(basename "$GIT_STAGING")"
PUB_SIZE=$(du -h "$PUBLIC_TARBALL" | cut -f1)
echo "✓ PUBLIC 完成: $PUB_SIZE" | tee -a "$LOG_FILE"

# 掃描驗證
SECRET_REGEX='vcp_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{40,}|hms_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20,}'
if tar -xzOf "$PUBLIC_TARBALL" 2>/dev/null | grep -E "$SECRET_REGEX" >/dev/null 2>&1; then
  echo "❌ ABORT: PUBLIC 版還有 token！" | tee -a "$LOG_FILE"
  exit 1
fi
echo "✓ PUBLIC 乾淨（無 token）" | tee -a "$LOG_FILE"

# Git push
if [ -d "$GITHUB_REPO_DIR/.git" ]; then
  cd "$GITHUB_REPO_DIR"
  git pull origin main --rebase 2>&1 | tee -a "$LOG_FILE"
else
  rm -rf "$GITHUB_REPO_DIR"
  if gh repo view hoonsoropenclaw/hermes-config-backup &>/dev/null; then
    git clone "$GITHUB_REPO_URL" "$GITHUB_REPO_DIR" 2>&1 | tee -a "$LOG_FILE"
  else
    gh repo create hoonsoropenclaw/hermes-config-backup --public \
      --description '赫米斯全狀態備份（公開版，敏感/大型在 Drive v3/）' \
      --source "$GIT_STAGING" --remote origin --push 2>&1 | tee -a "$LOG_FILE" || {
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
  git commit -m "backup: ${TIMESTAMP} (v3.0 public)" 2>&1 | tee -a "$LOG_FILE"
  git push origin main 2>&1 | tee -a "$LOG_FILE"
  echo "✓ GitHub push 完成" | tee -a "$LOG_FILE"
fi

# 清理本地暫存
rm -rf "$GIT_STAGING" "$PUBLIC_TARBALL" "$MANIFEST_LOCAL" "$MANIFEST_ENC"

# === 13. 完成 ===
echo "" | tee -a "$LOG_FILE"
echo "[$(date +%T)] === 赫米斯備份完成 v3.0 ===" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📦 這次備份的產出：" | tee -a "$LOG_FILE"
echo "   Drive v3/current/        ← 永遠最新（增量同步）" | tee -a "$LOG_FILE"
echo "   Drive v3/manifests/      ← 加密 SHA256 清單" | tee -a "$LOG_FILE"
echo "   Drive v3/snapshots/${WEEK_TAG}/  ← 本週 snapshot" | tee -a "$LOG_FILE"
echo "   GitHub hermes-config-backup     ← 公開版" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "🔗 還原入口：" | tee -a "$LOG_FILE"
echo "   GitHub: https://github.com/hoonsoropenclaw/hermes-config-backup" | tee -a "$LOG_FILE"
echo "   Drive:  rclone crypt_hermes:hermes-backup/v3/" | tee -a "$LOG_FILE"
echo "   Log:    $LOG_FILE" | tee -a "$LOG_FILE"
