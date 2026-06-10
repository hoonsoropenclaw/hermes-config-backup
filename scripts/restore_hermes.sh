#!/usr/bin/env bash
# ============================================================
# restore_hermes.sh - 赫米斯異機還原腳本（2026-06-06 建立）
# 來源：本地 tar.gz / rclone crypt_hermes:hermes_backup_*/ / GitHub repo
# 目標：~/.hermes/ 完整還原（不含 .env / 源碼 / 衍生資料）
# ============================================================

set -euo pipefail

# === 設定 ===
HERMES_HOME="$HOME/.hermes"
RESTORE_FROM="${1:-}"   # 選填：tar.gz 路徑；不填就從 GitHub clone

# === 0. 前置警告 ===
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║  赫米斯異機還原腳本 v1.0                                      ║
╠══════════════════════════════════════════════════════════════╣
║  ⚠️  此腳本會覆蓋現有的 ~/.hermes/ 部分檔案                 ║
║  ⚠️  還原前請先關閉任何運行的 hermes-gateway：              ║
║      pkill -f hermes-gateway                                ║
║  ⚠️  Telegram session 一次只能掛一台機器：                   ║
║      別同時開兩台主機的 gateway，會搶同一個 bot              ║
╚══════════════════════════════════════════════════════════════╝
EOF

read -p "確定要繼續嗎？(yes/no) " -r
echo
if [[ ! $REPLY =~ ^yes$ ]]; then
  echo "取消還原"
  exit 0
fi

# === 1. 安裝 hermes-agent 源碼（如果沒有） ===
if [ ! -d "$HERMES_HOME/hermes-agent" ]; then
  echo "[$(date +%T)] 安裝 hermes-agent 源碼..."
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
fi

# === 2. 決定還原來源 ===
STAGING="$HERMES_HOME/restore_staging_$$"

if [ -n "$RESTORE_FROM" ] && [ -f "$RESTORE_FROM" ]; then
  echo "[$(date +%T)] 從本地 tar.gz 還原: $RESTORE_FROM"
  mkdir -p "$STAGING"
  tar -xzf "$RESTORE_FROM" -C "$STAGING" --strip-components=1
elif rclone listremotes --config "$HOME/documents/rclone.conf" 2>/dev/null | grep -q "^crypt_hermes:$"; then
  echo "[$(date +%T)] 從 rclone crypt_hermes 找最新備份（時間戳目錄）..."
  STAGING="$HERMES_HOME/restore_staging_$$"
  rm -rf "$STAGING"
  mkdir -p "$STAGING"

  LATEST=$(rclone lsf crypt_hermes: --dirs-only --config "$HOME/documents/rclone.conf" 2>/dev/null | grep "^hermes_backup_.*_full$" | sort | tail -1 | tr -d '\r')
  if [ -z "$LATEST" ]; then
    echo "❌ 找不到 rclone 備份"
    exit 1
  fi
  echo "  最新備份: $LATEST"
  rclone copy "crypt_hermes:${LATEST}" "$STAGING/" --config "$HOME/documents/rclone.conf" 2>&1 | tail -3
  TARBALL=$(find "$STAGING" -name "hermes_backup_*_full.tar.gz" 2>/dev/null | head -1)
  if [ -z "$TARBALL" ] || [ ! -f "$TARBALL" ]; then
    echo "❌ 找不到 _full.tar.gz 檔案"
    ls -la "$STAGING"
    exit 1
  fi
  rm -rf "$STAGING"
  mkdir -p "$STAGING"
  tar -xzf "$TARBALL" -C "$STAGING" --strip-components=1
else
  echo "[$(date +%T)] 從 GitHub clone..."
  rm -rf "$STAGING"
  git clone https://github.com/hoonsoropenclaw/hermes-config-backup.git "$STAGING"
fi

# === 3. 驗證 staging 內容 ===
echo "[$(date +%T)] 驗證 staging 內容..."
for required in config/hermes-config.yaml memories/USER.md config/cron-jobs.json scripts/backup_hermes.sh; do
  if [ ! -e "$STAGING/$required" ]; then
    echo "❌ staging 缺少必要檔案: $required"
    exit 1
  fi
done
echo "✓ staging 內容完整"

# === 4. 還原檔案 ===
echo "[$(date +%T)] 還原檔案到 $HERMES_HOME ..."

# 配置
cp "$STAGING/config/hermes-config.yaml" "$HERMES_HOME/config.yaml"
mkdir -p "$HERMES_HOME/cron"
cp "$STAGING/config/cron-jobs.json" "$HERMES_HOME/cron/jobs.json"

# 記憶
mkdir -p "$HERMES_HOME/memories"
cp "$STAGING/memories/"*.md "$HERMES_HOME/memories/"

# Skills
mkdir -p "$HERMES_HOME/skills"
for skill_dir in "$STAGING/skills"/*/; do
  if [ -d "$skill_dir" ]; then
    skill_name=$(basename "$skill_dir")
    case "$skill_name" in
      autonomous-ai-agents)
        # 巢狀結構
        for sub in "$skill_dir"/*/; do
          sub_name=$(basename "$sub")
          mkdir -p "$HERMES_HOME/skills/autonomous-ai-agents/$sub_name"
          cp -r "$sub"/* "$HERMES_HOME/skills/autonomous-ai-agents/$sub_name/"
        done
        ;;
      INSTALLED_MANIFEST.md) ;;  # 跳過
      *)
        mkdir -p "$HERMES_HOME/skills/$skill_name"
        cp -r "$skill_dir"/* "$HERMES_HOME/skills/$skill_name/"
        ;;
    esac
  fi
done

# 腳本
mkdir -p "$HERMES_HOME/scripts"
cp "$STAGING/scripts/"*.py "$HERMES_HOME/scripts/" 2>/dev/null || true
cp "$STAGING/scripts/"*.sh "$HERMES_HOME/scripts/" 2>/dev/null || true
chmod +x "$HERMES_HOME/scripts/"*.sh 2>/dev/null || true

# kanban
[ -f "$STAGING/data/kanban.db" ] && cp "$STAGING/data/kanban.db" "$HERMES_HOME/kanban.db"

# === 5. 處理 .env ===
echo "[$(date +%T)] .env 處理..."
if [ -f "$HERMES_HOME/.env" ]; then
  echo "  .env 已存在，保留現有（避免覆蓋你的真實 key）"
  echo "  如果想重新申請請刪除 $HERMES_HOME/.env 後跑 hermes setup"
else
  if [ -f "$STAGING/config/env-template" ]; then
    cp "$STAGING/config/env-template" "$HERMES_HOME/.env"
    chmod 600 "$HERMES_HOME/.env"
    echo "  ✓ .env 範本已建（你需要從各平台申請 key 填入）"
    echo "  ⚠️  必填清單："
    grep -E "^[A-Z_]+_(KEY|TOKEN)" "$STAGING/config/env-template" | head -20
  fi
fi

# === 6. 顯示 INSTALLED_MANIFEST.md（提醒重裝外部 skills） ===
if [ -f "$STAGING/skills/INSTALLED_MANIFEST.md" ]; then
  echo ""
  echo "============================================================"
  echo "📋 已安裝 skills 清單（看是不是要重裝外部的）："
  echo "============================================================"
  cat "$STAGING/skills/INSTALLED_MANIFEST.md"
  echo ""
  echo "提示：用 hermes skills install <source> 重裝外部 skills"
fi

# === 7. 清理 staging ===
rm -rf "$STAGING"

# === 8. 驗證還原 ===
echo ""
echo "============================================================"
echo "✓ 還原完成！"
echo "============================================================"
echo ""
echo "📋 還原驗證清單："
echo ""
echo "1. 配置檢查："
echo "   $ diff <(cat $HERMES_HOME/config.yaml) <(cat $HERMES_HOME/config.yaml)"
echo "   （應該沒變化，剛還原的）"
echo ""
echo "2. cron jobs 檢查："
echo "   $ hermes cron list"
echo "   （看 jobs 數量對不對、model 欄位對不對）"
echo ""
echo "3. 記憶檢查："
echo "   $ ls $HERMES_HOME/memories/"
echo "   （應該有 7 個 MD）"
echo ""
echo "4. 啟動 gateway："
echo "   ⚠️  確保沒有其他主機在跑 hermes-gateway"
echo "   $ hermes gateway run"
echo ""
echo "5. Telegram 測試："
echo "   從 Telegram 給 bot 發一則訊息，看有沒有回應"
echo ""
echo "6. 跑一個 cron job 確認整體健康："
echo "   $ hermes cron run <job_id>"
echo "   推薦先跑 metacognitive-learner-24h"
echo ""
echo "============================================================"
echo "🚨 不要忘記的事項："
echo "============================================================"
echo "1. .env 裡的 key 全部要重新申請（除非你用其他方式還原）"
echo "2. GPG 加密的備用 GitHub PAT 沒備份，要重新加密設定"
echo "3. sparc-methodology 103 MB 外部 skill 沒在 backup 範圍，要重裝"
echo "4. hermes-agent 1.1 GB 源碼沒備份（會自動從 GitHub 拉）"
echo "5. 第一次啟動可能要等 1-2 分鐘讓 hermes 初始化"
