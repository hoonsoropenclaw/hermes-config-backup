#!/bin/bash

# 每日學習計畫生成腳本
# 每天上午8點自動執行

set -e

# 工作目錄
WORKSPACE="/home/hoonsoropenclaw/.hermes"
cd "$WORKSPACE"

# 日期
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo
    print_color $BLUE "=" * 60
    print_color $GREEN "$1"
    print_color $BLUE "=" * 60
}

# 主函數
main() {
    print_header "📅 OpenClaw 每日學習計畫生成 - $TODAY"
    
    # 檢查記憶文件
    if [ -f "memory/$YESTERDAY.md" ]; then
        print_color $BLUE "📖 讀取昨日記憶..."
        YESTERDAY_SUMMARY=$(grep -A5 "## 完成任務" "memory/$YESTERDAY.md" 2>/dev/null || echo "無昨日記錄")
    else
        YESTERDAY_SUMMARY="無昨日記錄"
    fi
    
    # 生成今日學習計畫
    print_color $BLUE "📝 生成今日學習計畫..."
    
    cat > daily_plan.json << EOF
{
  "date": "$TODAY",
  "main_tasks": [
    { "id": "m1", "task": "複習昨日學習內容並總結", "status": "pending" },
    { "id": "m2", "task": "優化OpenClaw對話效率策略", "status": "pending" },
    { "id": "m3", "task": "學習新的自動化工具整合", "status": "pending" },
    { "id": "m4", "task": "研究Token使用優化技巧", "status": "pending" },
    { "id": "m5", "task": "開發新的實用技能模組", "status": "pending" }
  ],
  "sub_tasks": [
    { "id": "s1", "task": "整理學習筆記和文檔", "status": "pending" },
    { "id": "s2", "task": "測試系統穩定性和性能", "status": "pending" },
    { "id": "s3", "task": "更新技能庫和工具列表", "status": "pending" },
    { "id": "s4", "task": "規劃明日學習重點", "status": "pending" }
  ]
}
EOF
    
    print_color $GREEN "✅ 今日學習計畫已生成: daily_plan.json"
    
    # 啟動網頁伺服器（如果未運行）
    print_color $BLUE "🌐 檢查網頁伺服器狀態..."
    
    if ! lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_color $YELLOW "🔄 啟動網頁伺服器..."
        cd daily-plan-ui
        nohup python3 server.py > server.log 2>&1 &
        SERVER_PID=$!
        sleep 2
        
        if kill -0 $SERVER_PID 2>/dev/null; then
            print_color $GREEN "✅ 網頁伺服器已啟動 (PID: $SERVER_PID)"
            echo $SERVER_PID > server.pid
        else
            print_color $RED "❌ 網頁伺服器啟動失敗"
        fi
        cd ..
    else
        print_color $GREEN "✅ 網頁伺服器已在運行"
    fi
    
    # 生成訪問連結
    print_header "🔗 系統訪問資訊"
    print_color $GREEN "🌐 網頁界面: http://localhost:8080"
    print_color $BLUE "📅 今日日期: $TODAY"
    print_color $BLUE "📋 主任務: 5個"
    print_color $BLUE "📝 次要任務: 4個"
    print_color $BLUE "📁 計畫文件: daily_plan.json"
    
    # 記錄到記憶
    print_color $BLUE "💾 記錄到今日記憶..."
    
    cat >> "memory/$TODAY.md" << EOF

## 每日學習計畫生成 - $TODAY
- 生成時間: $(date '+%Y-%m-%d %H:%M:%S')
- 主任務數量: 5
- 次要任務數量: 4
- 網頁伺服器狀態: 運行中
- 訪問連結: http://localhost:8080

### 今日重點任務
1. 複習昨日學習內容並總結
2. 優化OpenClaw對話效率策略  
3. 學習新的自動化工具整合
4. 研究Token使用優化技巧
5. 開發新的實用技能模組

### 系統狀態
- 網頁界面已準備就緒
- 學習計畫已更新
- 等待使用者選擇和提交
EOF
    
    print_color $GREEN "✅ 系統準備完成！"
    print_color $YELLOW "🚀 請訪問: http://localhost:8080"
}

# 錯誤處理
trap 'print_color $RED "腳本執行錯誤"; exit 1' ERR

# 執行主函數
main "$@"