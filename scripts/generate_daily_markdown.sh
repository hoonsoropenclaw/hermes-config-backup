#!/bin/bash

# OpenClaw 每日學習計畫Markdown生成腳本
# 自動生成每日計畫並準備上傳到Google Drive

set -e

# 工作目錄
WORKSPACE="/home/hoonsoropenclaw/.hermes"
cd "$WORKSPACE"

# 日期設定
TODAY=$(date +%Y-%m-%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
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

# 生成每日計畫
generate_daily_plan() {
    print_header "📅 生成每日學習計畫 - $TODAY"
    
    # 讀取模板
    TEMPLATE_CONTENT=$(cat daily-plan-template.md)
    
    # 替換變數
    PLAN_CONTENT="${TEMPLATE_CONTENT//\{\{DATE\}\}/$TODAY}"
    PLAN_CONTENT="${PLAN_CONTENT//\{\{GENERATED_TIME\}\}/$TIMESTAMP}"
    
    # 保存到檔案
    PLAN_FILE="daily-plan-$TODAY.md"
    echo "$PLAN_CONTENT" > "$PLAN_FILE"
    
    print_color $GREEN "✅ 每日計畫已生成: $PLAN_FILE"
    print_color $BLUE "📝 檔案大小: $(wc -l < "$PLAN_FILE") 行"
    
    # 同時生成JSON版本（備用）
    generate_json_version "$PLAN_FILE"
}

# 生成JSON版本（兼容原有系統）
generate_json_version() {
    local md_file="$1"
    local json_file="daily_plan.json"
    
    cat > "$json_file" << EOF
{
  "date": "$TODAY",
  "generated_time": "$TIMESTAMP",
  "status": "pending_review",
  "markdown_file": "$md_file",
  "main_tasks": [
    { "id": "T1", "task": "學習新的程式語言或框架", "status": "pending", "type": "technical" },
    { "id": "T2", "task": "研究AI模型優化技巧", "status": "pending", "type": "technical" },
    { "id": "T3", "task": "探索自動化工具整合方法", "status": "pending", "type": "technical" },
    { "id": "T4", "task": "分析系統架構設計模式", "status": "pending", "type": "technical" },
    { "id": "E1", "task": "優化對話token使用效率", "status": "pending", "type": "efficiency" },
    { "id": "E2", "task": "研究快速回應策略", "status": "pending", "type": "efficiency" },
    { "id": "E3", "task": "開發批量處理功能", "status": "pending", "type": "efficiency" },
    { "id": "E4", "task": "測試新的記憶管理方法", "status": "pending", "type": "efficiency" },
    { "id": "S1", "task": "學習新的API整合技術", "status": "pending", "type": "skill" },
    { "id": "S2", "task": "研究資料處理最佳實踐", "status": "pending", "type": "skill" },
    { "id": "S3", "task": "探索使用者體驗設計", "status": "pending", "type": "skill" },
    { "id": "S4", "task": "開發實用工具腳本", "status": "pending", "type": "skill" }
  ],
  "sub_tasks": [
    { "id": "M1", "task": "更新技能庫和文檔", "status": "pending", "type": "maintenance" },
    { "id": "M2", "task": "整理學習筆記和資源", "status": "pending", "type": "maintenance" },
    { "id": "M3", "task": "測試系統穩定性和性能", "status": "pending", "type": "maintenance" },
    { "id": "M4", "task": "備份重要資料和設定", "status": "pending", "type": "maintenance" },
    { "id": "K1", "task": "總結昨日學習成果", "status": "pending", "type": "knowledge" },
    { "id": "K2", "task": "規劃明日學習重點", "status": "pending", "type": "knowledge" },
    { "id": "K3", "task": "整理常見問題解決方案", "status": "pending", "type": "knowledge" },
    { "id": "K4", "task": "更新最佳實踐指南", "status": "pending", "type": "knowledge" },
    { "id": "C1", "task": "構思新的專案想法", "status": "pending", "type": "creative" },
    { "id": "C2", "task": "研究技術趨勢和發展", "status": "pending", "type": "creative" },
    { "id": "C3", "task": "設計使用者互動改進", "status": "pending", "type": "creative" },
    { "id": "C4", "task": "規劃長期學習路徑", "status": "pending", "type": "creative" }
  ]
}
EOF
    
    print_color $GREEN "✅ JSON版本已生成: $json_file"
}

# 創建Google Drive上傳腳本
create_upload_script() {
    print_header "📤 創建Google Drive上傳腳本"
    
    # Windows批次檔
    cat > "upload-to-gdrive.bat" << 'EOF'
@echo off
chcp 65001 > nul
echo ========================================
echo  OpenClaw 每日學習計畫上傳工具
echo ========================================
echo.

REM 檢查rclone是否安裝
where rclone >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 錯誤: 未找到 rclone
    echo 請先安裝 rclone: https://rclone.org/downloads/
    pause
    exit /b 1
)

REM 設定變數
set TODAY=%date:~0,4%-%date:~5,2%-%date:~8,2%
set PLAN_FILE=daily-plan-%TODAY%.md
set REMOTE_NAME=google-drive
set REMOTE_FOLDER="每日學習計畫"

REM 檢查檔案是否存在
if not exist "%PLAN_FILE%" (
    echo ❌ 錯誤: 找不到檔案 %PLAN_FILE%
    echo 請先運行 generate_daily_markdown.sh 生成計畫
    pause
    exit /b 1
)

echo 📅 今日日期: %TODAY%
echo 📄 計畫檔案: %PLAN_FILE%
echo ☁️  遠端位置: %REMOTE_NAME%:%REMOTE_FOLDER%
echo.

REM 上傳檔案
echo ⬆️  正在上傳到 Google Drive...
rclone copy "%PLAN_FILE%" "%REMOTE_NAME%:%REMOTE_FOLDER%" --progress

if %errorlevel% equ 0 (
    echo.
    echo ✅ 上傳成功！
    echo 🌐 檔案位置: Google Drive > 每日學習計畫 > %PLAN_FILE%
    echo.
    echo 🔗 直接連結（需登入Google帳戶）:
    echo https://drive.google.com/drive/folders/[你的資料夾ID]
) else (
    echo.
    echo ❌ 上傳失敗！
    echo 請檢查:
    echo 1. rclone 配置是否正確
    echo 2. Google Drive 連線狀態
    echo 3. 網路連線
)

echo.
echo 按任意鍵結束...
pause >nul
EOF
    
    # Linux/Mac腳本
    cat > "upload-to-gdrive.sh" << 'EOF'
#!/bin/bash

# OpenClaw 每日學習計畫上傳腳本
# 適用於 Linux/Mac

set -e

echo "========================================"
echo " OpenClaw 每日學習計畫上傳工具"
echo "========================================"
echo

# 檢查rclone是否安裝
if ! command -v rclone &> /dev/null; then
    echo "❌ 錯誤: 未找到 rclone"
    echo "請先安裝 rclone: https://rclone.org/downloads/"
    echo "Linux: sudo apt install rclone"
    echo "Mac: brew install rclone"
    exit 1
fi

# 設定變數
TODAY=$(date +%Y-%m-%d)
PLAN_FILE="daily-plan-$TODAY.md"
REMOTE_NAME="google-drive"
REMOTE_FOLDER="每日學習計畫"

# 檢查檔案是否存在
if [ ! -f "$PLAN_FILE" ]; then
    echo "❌ 錯誤: 找不到檔案 $PLAN_FILE"
    echo "請先運行 generate_daily_markdown.sh 生成計畫"
    exit 1
fi

echo "📅 今日日期: $TODAY"
echo "📄 計畫檔案: $PLAN_FILE"
echo "☁️  遠端位置: $REMOTE_NAME:$REMOTE_FOLDER"
echo

# 上傳檔案
echo "⬆️  正在上傳到 Google Drive..."
rclone copy "$PLAN_FILE" "$REMOTE_NAME:$REMOTE_FOLDER" --progress

if [ $? -eq 0 ]; then
    echo
    echo "✅ 上傳成功！"
    echo "🌐 檔案位置: Google Drive > 每日學習計畫 > $PLAN_FILE"
    echo
    echo "🔗 直接連結（需登入Google帳戶）:"
    echo "https://drive.google.com/drive/folders/[你的資料夾ID]"
else
    echo
    echo "❌ 上傳失敗！"
    echo "請檢查:"
    echo "1. rclone 配置是否正確"
    echo "2. Google Drive 連線狀態"
    echo "3. 網路連線"
    exit 1
fi

echo
echo "🎉 完成！"
EOF
    
    chmod +x "upload-to-gdrive.sh"
    
    print_color $GREEN "✅ 上傳腳本已創建:"
    print_color $BLUE "  • upload-to-gdrive.bat (Windows)"
    print_color $BLUE "  • upload-to-gdrive.sh (Linux/Mac)"
}

# 創建rclone配置指南
create_rclone_guide() {
    print_header "🔧 創建rclone配置指南"
    
    cat > "rclone-setup-guide.md" << 'EOF'
# rclone + Google Drive 配置指南

## 步驟1：安裝 rclone

### Windows
1. 下載 rclone: https://rclone.org/downloads/
2. 解壓縮到 `C:\rclone\`
3. 將 `C:\rclone\` 加入系統 PATH

### Linux
```bash
sudo apt update
sudo apt install rclone
```

### Mac
```bash
brew install rclone
```

## 步驟2：配置 Google Drive

1. **打開終端機/命令提示字元**
2. **運行配置命令**:
   ```bash
   rclone config
   ```
3. **按照提示操作**:
   ```
   n) New remote
   名字: google-drive
   類型: 18 (Google Drive)
   client_id: 直接按Enter（使用預設）
   client_secret: 直接按Enter（使用預設）
   scope: 1 (full access)
   root_folder_id: 直接按Enter
   service_account_file: 直接按Enter
   編輯高級配置: n
   自動配置: y
   ```

4. **瀏覽器會打開**，登入你的Google帳戶:
   - 帳戶: `hoonsoropenclaw@gmail.com`
   - 授權 rclone 訪問 Google Drive

5. **完成配置**，會顯示配置成功訊息

## 步驟3：測試連線

```bash
# 列出Google Drive根目錄
rclone lsd google-drive:

# 創建「每日學習計畫」資料夾
rclone mkdir google-drive:"每日學習計畫"

# 列出資料夾內容
rclone ls google-drive:"每日學習計畫"
```

## 步驟4：使用上傳腳本

### Windows
1. 雙擊 `upload-to-gdrive.bat`
2. 自動上傳今日學習計畫

### Linux/Mac
```bash
./upload-to-gdrive.sh
```

## 疑難排解

### 問題：授權失敗
```
解決：刪除舊配置重新設定
rclone config delete google-drive
rclone config
```

### 問題：找不到命令
```
解決：確認rclone已加入PATH
Windows: 系統環境變數
Linux/Mac: which rclone
```

### 問題：上傳速度慢
```
解決：使用 --drive-chunk-size 參數
rclone copy file.md google-drive:folder --drive-chunk-size 64M
```

## 常用命令

```bash
# 上傳檔案
rclone copy 檔案名 google-drive:"資料夾"

# 下載檔案
rclone copy google-drive:"資料夾/檔案名" .

# 同步資料夾
rclone sync 本地資料夾 google-drive:"遠端資料夾"

# 列出檔案
rclone ls google-drive:"資料夾"

# 刪除檔案
rclone delete google-drive:"資料夾/檔案名"
```

## 自動化設定

### Windows 工作排程器
1. 開啟「工作排程器」
2. 建立基本工作
3. 設定每天執行 `upload-to-gdrive.bat`

### Linux/Mac cron
```bash
# 每天上午8點自動上傳
0 8 * * * cd /path/to/workspace && ./upload-to-gdrive.sh
```

## 安全注意
- 配置檔案位置: `~/.config/rclone/rclone.conf`
- 不要分享配置檔案
- 定期備份重要資料
EOF
    
    print_color $GREEN "✅ rclone配置指南已創建: rclone-setup-guide.md"
}

# 創建審閱流程說明
create_review_guide() {
    print_header "📖 創建審閱流程說明"
    
    cat > "review-process-guide.md" << EOF
# 每日學習計畫審閱流程

## 流程圖
```
OpenClaw生成計畫 → 上傳Google Drive → 審閱者下載編輯 → 重新上傳 → OpenClaw讀取執行
```

## 步驟詳解

### 步驟1：計畫生成（OpenClaw自動執行）
- 時間：每天上午8:00 (UTC)
- 動作：自動生成 `daily-plan-YYYY-MM-DD.md`
- 內容：包含20個任務的勾選清單
- 狀態：🟡 等待審閱

### 步驟2：上傳到Google Drive
```bash
# 自動執行（設定定時任務）
./upload-to-gdrive.sh

# 或手動執行
./upload-to-gdrive.bat  # Windows
./upload-to-gdrive.sh   # Linux/Mac
```

### 步驟3：審閱者操作（學校/外部電腦）
1. **訪問Google Drive**
   - 網址: https://drive.google.com
   - 帳戶: hoonsoropenclaw@gmail.com
   - 資料夾: 每日學習計畫

2. **下載今日計畫**
   - 檔案: `daily-plan-YYYY-MM-DD.md`
   - 下載到本地電腦

3. **編輯計畫**
   - 使用支援Markdown的編輯器（VS Code、Obsidian等）
   - 勾選要執行的任務: `- [x] 任務描述`
   - 填寫「審閱者備註」欄位
   - 更新「審閱時間」

4. **重新上傳**
   - 將編輯後的檔案上傳回Google Drive
   - 覆蓋原有檔案或使用新檔名

### 步驟4：通知OpenClaw
- 方式1：發送訊息「已完成批閱」
- 方式2：在檔案名稱加入標記 `daily-plan-YYYY-MM-DD-REVIEWED.md`
- 方式3：在「審閱者備註」加入特定關鍵字

### 步驟5：OpenClaw讀取並執行
1. 檢查Google Drive是否有審閱完成的檔案
2. 下載並解析勾選的任務
3. 開始執行選取的任務
4. 記錄執行結果

## 檔案命名規則
- 原始檔案: `daily-plan-YYYY-MM-DD.md`
- 審閱完成: `daily-plan-YYYY-MM-DD-REVIEWED.md`
- 執行中: `daily-plan-YYYY-MM-DD-INPROGRESS.md`
- 已完成: `daily-plan-YYYY-MM-DD-COMPLETED.md`

## 審閱者工具建議

### 編輯器推薦
1. **VS Code** (免費，功能完整)
   - 安裝「Markdown All in One」擴展
   - 支援checkbox切換快捷鍵

2. **Obsidian** (免費，筆記專用)
   - 內建checkbox支援
   - 雙向連結功能

3. **Typora** (付費，所見即所得)
   - 直覺的編輯界面
   - 即時預覽

### 快速編輯技巧
```markdown
# 切換checkbox狀態
- [ ] 未選取 → 按空格或點擊切換
- [x] 已選取

# 快速選取多個任務
使用編輯器的多游標功能：
- Alt+點擊 (VS Code)
- Cmd+點擊 (Mac)
```

## 離線工作流程
1. **下載檔案**到本地
2. **離線編輯**（無網路時）
3. **重新連線後上傳**
4. **通知OpenClaw**

## 緊急情況處理

### 無法訪問Google Drive
1. 使用電子郵件傳送檔案
2. 使用其他雲端服務（Dropbox、OneDrive）
3. 直接傳送檔案內容

### 編輯器問題
1. 使用純文字編輯器編輯
2. 確保格式正確：`- [ ]` 或 `- [x]`
3. 保存為UTF-8編碼

## 品質檢查清單
- [ ] 所有要執行的任務都已勾選
- [ ] 審閱者姓名和時間已填寫
- [ ] 特別指示已清楚說明
- [ ] 檔案名稱正確
- [ ] 格式未損壞

## 聯絡方式
如有問題，請透過OpenClaw系統聯繫。
EOF
    
    print_color $GREEN "✅ 審閱流程指南已創建: review-process-guide.md"
}

# 主函數
main() {
    print_color $BLUE "╔══════════════════════════════════════════════════════════╗"
    print_color $GREEN "║      OpenClaw Google Drive 同步系統設定               ║"
    print_color $BLUE "╚══════════════════════════════════════════════════════════╝"
    
    # 生成每日計畫
    generate_daily_plan
    
    # 創建上傳腳本
    create_upload_script
    
    # 創建rclone配置指南
    create_rclone_guide
    
    # 創建審閱流程說明
    create_review_guide
    
    # 顯示完成訊息
    print_header "🎉 系統設定完成"
    
    print_color $GREEN "✅ 所有檔案已創建完成！"
    echo
    print_color $YELLOW "📁 生成的檔案:"
    print_color $BLUE "  • daily-plan-$TODAY.md        (今日學習計畫)"
    print_color $BLUE "  • daily_plan.json            (JSON版本)"
    print_color $BLUE "  • upload-to-gdrive.bat       (Windows上傳腳本)"
    print_color $BLUE "  • upload-to-gdrive.sh        (Linux/Mac上傳腳本)"
    print_color $BLUE "  • rclone-setup-guide.md      (rclone配置指南)"
    print_color $BLUE "  • review-process-guide.md    (審閱流程說明)"
    echo
    print_color $YELLOW "🚀 下一步行動:"
    print_color $BLUE "  1. 安裝並配置 rclone (參考 rclone-setup-guide.md)"
    print_color $BLUE "  2. 測試上傳: ./upload-to-gdrive.sh"
    print_color $BLUE "  3. 在Google Drive創建「每日學習計畫」資料夾"
    print_color $BLUE "  4. 設定每日自動化任務"
    echo
    print_color $GREEN "📅 今日計畫已準備好，等待上傳到Google Drive！"
}

# 錯誤處理
trap 'print_color $RED "腳本執行錯誤"; exit 1' ERR

# 執行主函數
main "$@"
