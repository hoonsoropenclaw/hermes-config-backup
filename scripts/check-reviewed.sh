#!/bin/bash

# 檢查Google Drive是否有審閱完成的檔案

WORKSPACE="/home/hoonsoropenclaw/.hermes"
cd "$WORKSPACE"

TODAY=$(date +%Y-%m-%d)
REVIEWED_FILE="daily-plan-$TODAY-REVIEWED.md"

echo "檢查審閱狀態 - $(date)"
echo "今日: $TODAY"
echo "尋找檔案: $REVIEWED_FILE"
echo

# 檢查本地是否有審閱完成的檔案
if [ -f "$REVIEWED_FILE" ]; then
    echo "✅ 發現本地審閱檔案: $REVIEWED_FILE"
    echo "開始處理..."
    # 這裡可以添加處理邏輯
    exit 0
fi

# 如果有rclone配置，檢查Google Drive
if command -v rclone &> /dev/null && rclone config show google-drive &> /dev/null; then
    echo "檢查Google Drive..."
    if rclone ls google-drive:"每日學習計畫" | grep -q "$REVIEWED_FILE"; then
        echo "✅ 發現Google Drive上的審閱檔案"
        echo "下載檔案..."
        rclone copy "google-drive:每日學習計畫/$REVIEWED_FILE" .
        echo "✅ 檔案已下載，開始處理..."
        # 這裡可以添加處理邏輯
    else
        echo "⏳ 尚未發現審閱完成的檔案"
    fi
else
    echo "⚠️  rclone未配置，無法檢查Google Drive"
fi
