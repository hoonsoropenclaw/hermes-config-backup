#!/bin/bash
# OpenClaw Backup Script to GitHub Repository (Raphael - N100)
# 保留原始路徑結構，方便日後還原對應
# 對應利姆路的 backup_rimuru.sh，路徑改為 raphael 的 hoonsoropenclaw

# 不啟用 set -e，讓 cp 空目錄等非致命錯誤不中斷流程

REPO_URL="https://github.com/hoonsor/Rimuru_and_Raphael.git"
BACKUP_DIR="/tmp/raphael_backup"
SOURCE_BASE="/home/hoonsoropenclaw/.openclaw"
GIT_REMOTE_USERNAME="hoonsor"

echo "🚀 開始執行拉斐爾 (Raphael) 備份腳本..."
echo "📅 備份時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📂 來源: ${SOURCE_BASE}"
echo ""

# 設定 Git credential helper（無痛推送用）
if ! git config --global credential.helper >/dev/null 2>&1; then
  echo "🔑 設定 Git credential helper..."
  git config --global credential.helper "store --file ~/.git-credentials-raphael"
fi

# 1. 準備本地備份目錄
rm -rf "$BACKUP_DIR"
echo "📦 Clone 遠端倉庫..."
git clone --depth 1 "$REPO_URL" "$BACKUP_DIR" 2>/dev/null || {
  echo "⚠️ 無法 Clone 倉庫，將在本地初始化..."
  mkdir -p "$BACKUP_DIR"
  cd "$BACKUP_DIR"
  git init
  git branch -M main
  git remote add origin "$REPO_URL"
}

cd "$BACKUP_DIR"

# 確保 remote URL 格式正確
current_url=$(git remote get-url origin 2>/dev/null || echo "")
if echo "$current_url" | grep -q "@github.com"; then
  :
elif [ "$current_url" != "$REPO_URL" ]; then
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REPO_URL"
fi

# 2. 建立對應原始路徑的目錄結構
# 來源: /home/hoonsoropenclaw/.openclaw/...
# 備份: hoonsoropenclaw/.openclaw/...
DEST_PREFIX="hoonsoropenclaw/.openclaw"

echo "📂 建立路徑對應目錄..."
mkdir -p "$DEST_PREFIX/workspace/memory"
mkdir -p "$DEST_PREFIX/workspace/Notes"
mkdir -p "$DEST_PREFIX/workspace/src"

# 3. 複製 openclaw.json (在 /home/hoonsoropenclaw/.openclaw/ 下)
if [ -f "$SOURCE_BASE/openclaw.json" ]; then
  cp "$SOURCE_BASE/openclaw.json" "$DEST_PREFIX/openclaw.json"
  echo "  ✅ $DEST_PREFIX/openclaw.json"
fi

# 使用 Python 處理 openclaw.json 敏感資訊（可靠處理多行 JSON）
if [ -f "$DEST_PREFIX/openclaw.json" ]; then
  echo "  🔒 移除 openclaw.json 中的敏感資訊..."
  python3 -c "
import json, re, sys

with open('$DEST_PREFIX/openclaw.json', 'r') as f:
    data = json.load(f)

def sanitize(obj, path=''):
    if isinstance(obj, dict):
        result = {}
        for key, val in obj.items():
            key_lower = key.lower()
            new_path = f'{path}.{key}' if path else key
            
            # 清除敏感欄位的值
            if any(kw in key_lower for kw in ['api_key', 'apikey', 'token', 'secret', 'password', 'bot_token']):
                if isinstance(val, str):
                    result[key] = '***REMOVED***'
                    continue
            
            # 清除 allowedOrigins 中的 IP（非 localhost）
            if key_lower == 'allowedorigins' and isinstance(val, list):
                result[key] = ['***REMOVED***']
                continue
            
            # 遞迴處理 dict 和 list
            result[key] = sanitize(val, new_path)
        return result
    elif isinstance(obj, list):
        return [sanitize(item, path) for item in obj]
    else:
        return obj

sanitized = sanitize(data)
with open('$DEST_PREFIX/openclaw.json', 'w') as f:
    json.dump(sanitized, f, indent=2, ensure_ascii=False)
    f.write('\n')

print('  ✅ 敏感資訊與 IP 位址已移除')
"
fi

# 4. 複製 .env (在 /home/hoonsoropenclaw/.openclaw/ 下)
if [ -f "$SOURCE_BASE/.env" ]; then
  echo "🔒 處理環境變數 (.env)..."
  sed -E 's/^([^=]+)=(.*)$/\1=***REMOVED***/g' "$SOURCE_BASE/.env" > "$DEST_PREFIX/.env"
  echo "  ✅ $DEST_PREFIX/.env"
else
  echo "  ⚠️ .env 不存在，跳過"
fi

# 5. 複製 Workspace 核心文件 (在 /home/hoonsoropenclaw/.hermes/ 下)
echo "📂 複製 Workspace 檔案..."
for doc in SOUL.md IDENTITY.md USER.md MEMORY.md AGENTS.md TOOLS.md HEARTBEAT.md; do
  if cp "$SOURCE_BASE/workspace/$doc" "$DEST_PREFIX/workspace/$doc" 2>/dev/null; then
    echo "  ✅ $DEST_PREFIX/workspace/$doc"
  else
    echo "  ⚠️ $DEST_PREFIX/workspace/$doc 不存在，跳過"
  fi
done

# 6. 複製 shell 腳本
echo "📂 複製 Shell 腳本..."
cp "$SOURCE_BASE/workspace/"*.sh "$DEST_PREFIX/workspace/" 2>/dev/null
SCRIPT_COUNT=$(ls -1 "$DEST_PREFIX/workspace/"*.sh 2>/dev/null | wc -l)
if [ "$SCRIPT_COUNT" -gt 0 ]; then
  echo "  ✅ $DEST_PREFIX/workspace/ (${SCRIPT_COUNT} 個腳本)"
fi

# 7. 複製子目錄
shopt -s nullglob dotglob
echo "📂 複製子目錄..."

if [ -d "$SOURCE_BASE/workspace/memory" ]; then
  cp -r "$SOURCE_BASE/workspace/memory/"* "$DEST_PREFIX/workspace/memory/" 2>/dev/null
  MEM_COUNT=$(ls -1 "$DEST_PREFIX/workspace/memory/"*.md 2>/dev/null | wc -l)
  echo "  ✅ $DEST_PREFIX/workspace/memory/ (${MEM_COUNT} 個檔案)"
fi

if [ -d "$SOURCE_BASE/workspace/Notes" ]; then
  mkdir -p "$DEST_PREFIX/workspace/Notes"
  find "$SOURCE_BASE/workspace/Notes" -type f \( -name "*.md" -o -name "*.canvas" -o -name "*.json" \) 2>/dev/null | while read f; do
    rel="${f#$SOURCE_BASE/workspace/}"
    mkdir -p "$(dirname "$DEST_PREFIX/workspace/$rel")"
    cp "$f" "$DEST_PREFIX/workspace/$rel" 2>/dev/null
  done
  echo "  ✅ $DEST_PREFIX/workspace/Notes/ (部分複製)"
fi

if [ -d "$SOURCE_BASE/workspace/src" ]; then
  mkdir -p "$DEST_PREFIX/workspace/src"
  cp -r "$SOURCE_BASE/workspace/src/"* "$DEST_PREFIX/workspace/src/" 2>/dev/null
  SRC_COUNT=$(ls -1 "$DEST_PREFIX/workspace/src/"* 2>/dev/null | wc -l)
  echo "  ✅ $DEST_PREFIX/workspace/src/ (${SRC_COUNT} 個檔案)"
fi

shopt -u nullglob dotglob

# 8. 複製這支腳本本身到備份中
cp "$SOURCE_BASE/workspace/scripts/backup_raphael.sh" "$DEST_PREFIX/workspace/backup_raphael.sh" 2>/dev/null

# 9. Git 提交與推送
echo ""
echo "📦 準備 Git 提交..."
git add -A

if git diff --cached --quiet; then
  echo "✅ 沒有新的變更需要提交，備份完成。"
else
  FILE_COUNT=$(git diff --cached --name-only | wc -l)
  git commit -m "chore(backup): 拉斐爾自動備份 OpenClaw 配置與 Workspace ($FILE_COUNT 個檔案變更)"
  echo "🚀 推送至 GitHub..."
  if git push origin main 2>&1; then
    echo "  ✅ 推送成功"
  else
    echo "⚠️ 推送失敗，嘗試使用 credential 重新推送..."
    git push origin main 2>&1 || echo "⚠️ 推送仍失敗，請設定 token: echo 'https://${GIT_REMOTE_USERNAME}:YOUR_TOKEN@github.com' > ~/.git-credentials-raphael"
  fi
fi

echo ""
echo "📊 備份摘要:"
echo "  來源: $SOURCE_BASE"
echo "  保留結構: $DEST_PREFIX/..."
echo "  目標倉庫: $REPO_URL"
echo "  檔案數量: $(find "$DEST_PREFIX" -type f 2>/dev/null | wc -l) 個檔案"
echo ""
echo "📋 還原時的路徑對應表:"
echo "  備份路徑                               →  原始路徑"
echo "  hoonsoropenclaw/.openclaw/openclaw.json →  $SOURCE_BASE/openclaw.json"
echo "  hoonsoropenclaw/.hermes/*.md → $SOURCE_BASE/workspace/*.md"
echo "  hoonsoropenclaw/.hermes/*.sh → $SOURCE_BASE/workspace/*.sh"
echo "  hoonsoropenclaw/.hermes/memory → $SOURCE_BASE/workspace/memory/"
echo ""
echo "  本機暫存目錄: $BACKUP_DIR"
echo "  若需再次推送: cd $BACKUP_DIR && git push origin main"
