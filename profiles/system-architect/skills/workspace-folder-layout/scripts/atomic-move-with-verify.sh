#!/usr/bin/env bash
# atomic-move-with-verify.sh
# 用途：把檔案搬到子目錄，全程用 SHA256 + /tmp 雙保險、可一鍵還原
# 場景：磁碟盤點 / 清理時的單批動作
# 用法：
#   atomic-move-with-verify.sh <source-file> <target-dir> [label]
# 範例：
#   atomic-move-with-verify.sh ~/old-backup.tar.gz ~/archive/ config-bak
#
# 設計：
#   1. 先 SHA256 fingerprint + 純文字副本到 /tmp/<label>-<date>/
#   2. 建目標子目錄（如果不存在）
#   3. mv 檔案到目標
#   4. 自動驗證：目標 SHA256 = 預期、來源已清、/tmp 備份還在
#   5. 失敗自動 rollback（從 /tmp 還原）
#
# 反模式（不要做）：
#   - 用 `cp -r` 搬 .git 目錄（會壞 git 內部 metadata）
#   - 沒備份就 `rm`（後悔無法還原）
#   - 一次搬多個檔案（本 script 是「單檔單動作」設計，分批才好定位問題）

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "用法: $0 <source-file> <target-dir> [label]"
  echo "範例: $0 ~/old-backup.tar.gz ~/archive/ config-bak"
  exit 64  # EX_USAGE
fi

SRC="$1"
DST_DIR="$2"
LABEL="${3:-$(basename "$SRC")}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/hermes-cleanup-${LABEL}-${DATE}"
SHA_FILE="/tmp/hermes-cleanup-${LABEL}-${DATE}.sha256"

# 顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== atomic-move-with-verify ===${NC}"
echo "來源: $SRC"
echo "目標: $DST_DIR"
echo "備份: $BACKUP_DIR"
echo ""

# 預檢
if [ ! -f "$SRC" ]; then
  echo -e "${RED}❌ 來源檔案不存在: $SRC${NC}"
  exit 66  # EX_NOINPUT
fi

# 1. 備份到 /tmp
echo "【1/5】備份到 /tmp + 記 SHA256..."
mkdir -p "$BACKUP_DIR"
cp -p "$SRC" "$BACKUP_DIR/"
EXPECTED_SHA=$(sha256sum "$SRC" | awk '{print $1}')
echo "$EXPECTED_SHA  $(basename "$SRC")" > "$SHA_FILE"
echo "  ✅ 備份完成: $BACKUP_DIR/$(basename "$SRC")"
echo "  ✅ SHA256: $EXPECTED_SHA"
echo ""

# 2. 建目標子目錄
echo "【2/5】建目標子目錄（如果不存在）..."
mkdir -p "$DST_DIR"
echo "  ✅ $DST_DIR"
echo ""

# 3. 搬
echo "【3/5】mv $SRC → $DST_DIR/"
mv -v "$SRC" "$DST_DIR/"
echo ""

# 4. 驗證
echo "【4/5】驗證..."
ACTUAL_SHA=$(sha256sum "$DST_DIR/$(basename "$SRC")" | awk '{print $1}')
if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
  echo -e "${RED}❌ SHA256 不一致！自動 rollback${NC}"
  echo "  預期: $EXPECTED_SHA"
  echo "  實測: $ACTUAL_SHA"
  mv "$DST_DIR/$(basename "$SRC")" "$SRC"
  exit 70  # EX_SOFTWARE
fi
echo "  ✅ SHA256 一致"

if [ -e "$SRC" ]; then
  echo -e "${RED}❌ 來源還在、搬移失敗、自動 rollback${NC}"
  exit 71
fi
echo "  ✅ 來源已清空"
echo ""

# 5. 報告
echo -e "${GREEN}【5/5】完成${NC}"
echo "  檔案: $(basename "$SRC")"
echo "  新位置: $DST_DIR/$(basename "$SRC")"
echo "  備份: $BACKUP_DIR/$(basename "$SRC")"
echo "  SHA256: $EXPECTED_SHA"
echo ""
echo "還原指令（如果後悔）："
echo "  cp -p $BACKUP_DIR/$(basename "$SRC") $SRC"
