#!/usr/bin/env bash
# ============================================================
# hermes-restore.sh - 赫米斯一鍵異機還原腳本（2026-06-06 v2.0）
# 設計：使用者改頂部 3 個變數、準備好 rclone.conf、執行
# 自動找 Drive 上最新備份、解密、解 tar、互動式還原
#
# 用法：
#   1. nano hermes-restore.sh  # 改下方 3 個變數
#   2. ./hermes-restore.sh
# ============================================================

# ===================== 設定區（必改） =====================

# 1. 新主機的 hermes home（不存在會自動建）
HERMES_HOME="$HOME/.hermes"

# 2. rclone config 檔路徑（必填，要先從舊主機或備份機器的 ~/documents/rclone.conf 拿過來）
#    路徑可以是絕對路徑
RCLONE_CONFIG="$HOME/documents/rclone.conf"

# 3. GitHub username（hermes-config-backup 公開版備份用）
GITHUB_USERNAME="hoonsoropenclaw"

# ===================== 進階設定（可選） =====================

# Drive 上遠端備份資料夾前綴（rclone crypt remote 名稱）
RCLONE_REMOTE="crypt_hermes"

# 要還原的 hermes-agent 安裝目錄（不設定會從 GitHub 拉原始碼）
HERMES_AGENT_INSTALL_DIR="$HERMES_HOME/hermes-agent"

# Telegram 警告：還原時會檢查 gateway 狀態
# 如果新主機要啟用 gateway，先在舊主機跑：pkill -f hermes-gateway

# ===================== 腳本本體（不用改） =====================

set -euo pipefail

# 顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 解析 --yes / -y 旗標（2026-06-06 加，給非互動式環境用）
YES_MODE="no"
for arg in "$@"; do
  case "$arg" in
    --yes|-y) YES_MODE="yes" ;;
  esac
done

# === 0. 前置警告 ===
clear
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║  赫米斯異機還原腳本 v2.0                                       ║
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
echo "  HERMES_HOME        = $HERMES_HOME"
echo "  RCLONE_CONFIG      = $RCLONE_CONFIG"
echo "  GITHUB_USERNAME    = $GITHUB_USERNAME"
echo "  RCLONE_REMOTE      = $RCLONE_REMOTE"
echo "  YES_MODE           = $YES_MODE"
echo ""
if [ "$YES_MODE" = "yes" ]; then
  echo -e "${YELLOW}--yes 模式：跳過確認、互動問題用預設值（全部還原）${NC}"
else
  read -p "設定正確嗎？(yes/no) " -r
  echo
  if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "請先 nano hermes-restore.sh 改設定，再重跑"
    exit 0
  fi
fi

# === 1. 預檢 ===
echo -e "${BLUE}[1/8] 預檢工具${NC}"
for tool in rclone git python3 tar rsync; do
  if ! command -v "$tool" &>/dev/null; then
    echo -e "${RED}❌ 缺少工具: $tool（apt install $tool 或 brew install $tool）${NC}"
    exit 1
  fi
done
echo -e "${GREEN}✓ 工具齊全${NC}"

if [ ! -f "$RCLONE_CONFIG" ]; then
  echo -e "${RED}❌ 找不到 rclone config: $RCLONE_CONFIG${NC}"
  echo "   從舊主機或備份機器的 ~/documents/rclone.conf 拿過來"
  echo "   確認裡面有 [hoonsorasus] 跟 [crypt_hermes] 兩個 remote"
  exit 1
fi
chmod 600 "$RCLONE_CONFIG"

if ! rclone listremotes --config "$RCLONE_CONFIG" 2>/dev/null | grep -q "^${RCLONE_REMOTE}:$"; then
  echo -e "${RED}❌ rclone remote ${RCLONE_REMOTE}: 不存在於 config${NC}"
  echo "   確認 rclone.conf 裡有 [${RCLONE_REMOTE}] section"
  exit 1
fi
echo -e "${GREEN}✓ rclone config OK${NC}"

# === 2. 找 Drive 上最新備份 ===
echo -e "${BLUE}[2/8] 找 Drive 上最新備份${NC}"
LATEST="hermes_backup_latest.tar.gz"
# 2026-06-06 修（subagent 測試發現）：
# `rclone lsf --dirs-only` 在 crypt remote 上**取不到**目錄（加密後目錄變檔案）
# 修法：改用 lsf 拿所有 entry + grep + sort 過濾
TIMESTAMP_DIR=$(rclone lsf "${RCLONE_REMOTE}:" --config "$RCLONE_CONFIG" 2>/dev/null | grep "^hermes_backup_.*_full$" | sort | tail -1 | tr -d '\r')
if [ -n "$TIMESTAMP_DIR" ]; then
  echo -e "${GREEN}✓ 找到時間戳備份: $TIMESTAMP_DIR（用這個）${NC}"
fi

STAGING="$(mktemp -d)/hermes-restore"
mkdir -p "$STAGING"

# 優先用時間戳目錄（每次備份建立新目錄，簡單可靠）
if [ -n "$TIMESTAMP_DIR" ]; then
  echo "  下載時間戳備份..."
  # 2026-06-06 修：crypt remote 下 rclone copy 對大檔單檔**不會**自動 list 目錄
  # 改用 copy 整個目錄（會用 Drive 端 list 然後挑 _full.tar.gz）
  rclone copy "${RCLONE_REMOTE}:${TIMESTAMP_DIR}" "$STAGING/" --config "$RCLONE_CONFIG" 2>&1 | tail -3
  TARBALL=$(find "$STAGING" -name "hermes_backup_*_full.tar.gz" 2>/dev/null | head -1)
else
  echo "  下載 hermes_backup_latest.tar.gz（fallback）..."
  rclone copy "${RCLONE_REMOTE}:hermes_backup_latest.tar.gz" "$STAGING/" --config "$RCLONE_CONFIG" 2>&1 | tail -3
  TARBALL="$STAGING/hermes_backup_latest.tar.gz"
fi
if [ -z "$TARBALL" ] || [ ! -f "$TARBALL" ]; then
  echo -e "${RED}❌ 找不到任何 _full.tar.gz 檔案${NC}"
  ls -la "$STAGING"
  exit 1
fi
echo -e "${GREEN}  ✓ 找到: $(basename $TARBALL)${NC}"

mkdir -p "${STAGING}/extracted"
tar -xzf "$TARBALL" -C "${STAGING}/extracted" --strip-components=1
echo -e "${GREEN}✓ 解 tar 完成${NC}"

# 找 staging 內部實際目錄
INNER_DIR="${STAGING}/extracted"

# === 4. 互動式選擇要還原什麼 ===
echo ""
echo -e "${BLUE}[4/8] 選擇要還原的內容${NC}"
echo ""
echo "Drive FULL 版備份包含："
echo "  ✓ 7 個核心 MD 檔（USER/MEMORY/...）"
echo "  ✓ config.yaml / cron-jobs.json（個人化設定）"
echo "  ✓ 6 個自建 skills（metacognitive-learner 等）"
echo "  ✓ 50+ Python 腳本"
echo "  ⚠️  .env 真實檔（12 個 API key）"
echo "  ⚠️  state.db（169 MB session store）"
echo "  ⚠️  hermes-agent 源碼（80+ MB）"
echo "  ⚠️  sparc-methodology（72 MB 外部 skill）"
echo ""

ask_yes() {
  # 2026-06-06 加：--yes 模式用預設值（全部 yes）
  local prompt="$1"
  local default="${2:-Y}"
  if [ "$YES_MODE" = "yes" ]; then
    echo "$prompt (auto-yes: $default)"
    return 0
  fi
  read -p "$prompt" -r
  echo
  [[ -z "$REPLY" ]] && REPLY="$default"
  [[ "${REPLY,,}" =~ ^y ]] && return 0
  return 1
}

read -p "還原核心設定（MD/config/skills/scripts）？ (Y/n) " -r
DO_CORE=${REPLY:-Y}
DO_CORE=${DO_CORE,,}
if [[ "$DO_CORE" == "y" || "$DO_CORE" == "yes" || -z "$DO_CORE" ]]; then
  DO_CORE="yes"
fi

read -p "還原 .env 真實檔（12 個 API key）？ (Y/n) " -r
DO_ENV=${REPLY:-Y}
DO_ENV=${DO_ENV,,}
if [[ "$DO_ENV" == "y" || "$DO_ENV" == "yes" || -z "$DO_ENV" ]]; then
  DO_ENV="yes"
fi

read -p "還原 state.db（169 MB session store）？ (Y/n) " -r
DO_STATE=${REPLY:-Y}
DO_STATE=${DO_STATE,,}
if [[ "$DO_STATE" == "y" || "$DO_STATE" == "yes" || -z "$DO_STATE" ]]; then
  DO_STATE="yes"
fi

read -p "還原 hermes-agent 源碼（80 MB，跳過可從 GitHub 重新裝）？ (y/N) " -r
DO_AGENT=${REPLY:-N}
DO_AGENT=${DO_AGENT,,}
if [[ "$DO_AGENT" == "y" || "$DO_AGENT" == "yes" ]]; then
  DO_AGENT="yes"
else
  DO_AGENT="no"
fi

read -p "還原 GPG 加密的備用 token（alt_gh_tokens + secrets）？ (Y/n) " -r
DO_GPG=${REPLY:-Y}
DO_GPG=${DO_GPG,,}
if [[ "$DO_GPG" == "y" || "$DO_GPG" == "yes" || -z "$DO_GPG" ]]; then
  DO_GPG="yes"
fi

read -p "還原 sparc-methodology 外部 skill（72 MB）？ (y/N) " -r
DO_SPARC=${REPLY:-N}
DO_SPARC=${DO_SPARC,,}
if [[ "$DO_SPARC" == "y" || "$DO_SPARC" == "yes" ]]; then
  DO_SPARC="yes"
else
  DO_SPARC="no"
fi

# === 5. 還原檔案 ===
echo ""
echo -e "${BLUE}[5/8] 還原檔案到 $HERMES_HOME ...${NC}"
mkdir -p "$HERMES_HOME"

if [[ "$DO_CORE" == "yes" ]]; then
  echo "  ✓ 核心設定還原中..."
  cp "$INNER_DIR/config/hermes-config.yaml" "$HERMES_HOME/config.yaml"
  mkdir -p "$HERMES_HOME/cron"
  cp "$INNER_DIR/config/cron-jobs.json" "$HERMES_HOME/cron/jobs.json"

  mkdir -p "$HERMES_HOME/memories"
  cp "$INNER_DIR/memories/"*.md "$HERMES_HOME/memories/"

  mkdir -p "$HERMES_HOME/skills"
  for skill_dir in "$INNER_DIR/skills"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    if [ "$skill_name" = "INSTALLED_MANIFEST.md" ]; then continue; fi
    if [ "$skill_name" = "autonomous-ai-agents" ]; then
      for sub in "$skill_dir"/*/; do
        [ -d "$sub" ] || continue
        sub_name=$(basename "$sub")
        mkdir -p "$HERMES_HOME/skills/autonomous-ai-agents/$sub_name"
        cp -r "$sub"/* "$HERMES_HOME/skills/autonomous-ai-agents/$sub_name/"
      done
    else
      mkdir -p "$HERMES_HOME/skills/$skill_name"
      cp -r "$skill_dir"/* "$HERMES_HOME/skills/$skill_name/"
    fi
  done

  mkdir -p "$HERMES_HOME/scripts"
  cp "$INNER_DIR/scripts/"*.py "$HERMES_HOME/scripts/" 2>/dev/null || true
  cp "$INNER_DIR/scripts/"*.sh "$HERMES_HOME/scripts/" 2>/dev/null || true
  chmod +x "$HERMES_HOME/scripts/"*.sh 2>/dev/null || true

  [ -f "$INNER_DIR/data/kanban.db" ] && cp "$INNER_DIR/data/kanban.db" "$HERMES_HOME/kanban.db"

  [ -f "$INNER_DIR/docs/RESTORE.md" ] && cp "$INNER_DIR/docs/RESTORE.md" "$HERMES_HOME/docs/"
  echo -e "${GREEN}  ✓ 核心設定完成${NC}"
fi

if [[ "$DO_ENV" == "yes" ]] && [ -f "$INNER_DIR/config/hermes-env-real" ]; then
  echo "  ✓ .env 還原中..."
  cp "$INNER_DIR/config/hermes-env-real" "$HERMES_HOME/.env"
  chmod 600 "$HERMES_HOME/.env"
  echo -e "${GREEN}  ✓ .env 完成（mode 600）${NC}"
fi

if [[ "$DO_STATE" == "yes" ]] && [ -f "$INNER_DIR/full_backups/state.db" ]; then
  echo "  ✓ state.db 還原中..."
  cp "$INNER_DIR/full_backups/state.db" "$HERMES_HOME/state.db"
  echo -e "${GREEN}  ✓ state.db 完成${NC}"
fi

if [[ "$DO_AGENT" == "yes" ]] && [ -d "$INNER_DIR/full_backups/hermes-agent" ]; then
  echo "  ✓ hermes-agent 源碼還原中（含 venv，立即可用）..."
  mkdir -p "$HERMES_AGENT_INSTALL_DIR"
  rsync -a --exclude='__pycache__/' --exclude='*.pyc' \
        "$INNER_DIR/full_backups/hermes-agent/" "$HERMES_AGENT_INSTALL_DIR/"
  echo -e "${GREEN}  ✓ hermes-agent 源碼 + venv 完成（災難還原可立即使用）${NC}"
elif [[ "$DO_AGENT" == "no" ]]; then
  echo "  ⚠️  跳過 hermes-agent 源碼（將從 GitHub 重新安裝）"
  if [ ! -d "$HERMES_AGENT_INSTALL_DIR" ]; then
    echo "  → 安裝 hermes-agent 中..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
  fi
fi

if [[ "$DO_GPG" == "yes" ]] && [ -d "$INNER_DIR/full_backups/alt_gh_tokens" ]; then
  echo "  ✓ GPG 加密 token 還原中..."
  mkdir -p "$HOME/.config/hermes/alt_gh_tokens"
  cp -r "$INNER_DIR/full_backups/alt_gh_tokens"/* "$HOME/.config/hermes/alt_gh_tokens/" 2>/dev/null || true
  chmod 700 "$HOME/.config/hermes/alt_gh_tokens"
  chmod 600 "$HOME/.config/hermes/alt_gh_tokens"/*

  if [ -d "$INNER_DIR/full_backups/secrets" ]; then
    mkdir -p "$HOME/.local/share/hermes/secrets"
    cp -r "$INNER_DIR/full_backups/secrets"/* "$HOME/.local/share/hermes/secrets/" 2>/dev/null || true
    chmod 700 "$HOME/.local/share/hermes/secrets"
    chmod 600 "$HOME/.local/share/hermes/secrets"/*
  fi
  echo -e "${GREEN}  ✓ GPG token 完成（測試解密：gpg --list-secret-keys）${NC}"
fi

if [[ "$DO_SPARC" == "yes" ]] && [ -d "$INNER_DIR/full_backups/sparc-methodology" ]; then
  echo "  ✓ sparc-methodology 還原中..."
  mkdir -p "$HERMES_HOME/skills/sparc-methodology"
  cp -r "$INNER_DIR/full_backups/sparc-methodology"/* "$HERMES_HOME/skills/sparc-methodology/"
  echo -e "${GREEN}  ✓ sparc-methodology 完成${NC}"
fi

# === 6. 清理 staging ===
echo ""
echo -e "${BLUE}[6/8] 清理 staging...${NC}"
rm -rf "$STAGING"
echo -e "${GREEN}✓ 清理完成${NC}"

# === 7. 顯示還原清單 ===
echo ""
echo -e "${BLUE}[7/8] 還原驗證清單${NC}"
echo ""
echo "  跑這些指令驗證："
echo ""
echo "  1. 設定檢查："
echo "     \$ cat $HERMES_HOME/config.yaml | head -20"
echo ""
echo "  2. 記憶檢查："
echo "     \$ ls $HERMES_HOME/memories/  # 應該 7 個 MD"
echo ""
echo "  3. cron jobs 檢查："
echo "     \$ hermes cron list  # 應該 7 個 jobs（6 個舊 + hermes-daily-backup）"
echo ""
echo "  4. 自建 skills 檢查："
echo "     \$ ls $HERMES_HOME/skills/trial-and-error/references/by-category/  # 8 個分類"
echo ""
echo "  5. .env 檢查（如果有還原）："
echo "     \$ ls -la $HERMES_HOME/.env  # 應該 mode 600"
echo ""
echo "  6. 啟動 gateway："
echo "     ⚠️  確保沒有其他主機在跑 hermes-gateway"
echo "     \$ hermes gateway run"
echo ""
echo "  7. Telegram 測試："
echo "     從 Telegram 給 bot 發訊息，看有沒有回應"

# === 8. 完成 ===
echo ""
echo "============================================================"
echo -e "${GREEN}✓ 還原完成！${NC}"
echo "============================================================"
echo ""
echo "🚨 不要忘記的事項："
echo "  1. .env 裡的 key 全部要重新申請（除非有還原 .env）"
echo "  2. hermes-agent venv 沒備份（首次啟動會自動重建）"
echo "  3. 外部 skills 沒自動還原的（sparc-methodology 除外）請看："
echo "     $HERMES_HOME/skills/INSTALLED_MANIFEST.md"
echo "  4. Telegram 一次只能一台機器掛 gateway"
echo ""
echo "📖 完整 SOP 見：$HERMES_HOME/docs/RESTORE.md"
