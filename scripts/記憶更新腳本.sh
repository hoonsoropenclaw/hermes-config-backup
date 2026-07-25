#!/bin/bash
# 學習成果記憶更新腳本
# 用於在學習計畫完成後更新相關記憶

echo "========================================"
echo "       學習成果記憶更新系統"
echo "========================================"

# 設定變數
MEMORY_FILE="/home/hoonsoropenclaw/.hermes/MEMORY.md"
DAILY_MEMORY_DIR="/home/hoonsoropenclaw/.hermes/memory"
TODAY=$(date '+%Y-%m-%d')
DAILY_FILE="${DAILY_MEMORY_DIR}/${TODAY}.md"

# 確保記憶目錄存在
mkdir -p "${DAILY_MEMORY_DIR}"

# 顯示選單
show_menu() {
    echo "請選擇操作:"
    echo "1. 📝 記錄今日學習成果"
    echo "2. 🧠 更新長期記憶 (MEMORY.md)"
    echo "3. 📋 查看今日記憶記錄"
    echo "4. 🔍 搜索歷史記憶"
    echo "5. 🏠 返回主選單"
    echo "========================================"
    read -p "請輸入選擇 (1-5): " choice
    echo
}

# 1. 記錄今日學習成果
record_today_learning() {
    echo "📝 記錄今日學習成果"
    echo "日期: ${TODAY}"
    echo
    
    # 檢查今日記憶檔案是否存在
    if [ ! -f "${DAILY_FILE}" ]; then
        echo "📄 創建今日記憶檔案: ${DAILY_FILE}"
        echo "# ${TODAY} 學習記錄" > "${DAILY_FILE}"
        echo "" >> "${DAILY_FILE}"
        echo "## 📅 日期" >> "${DAILY_FILE}"
        echo "- **日期：** ${TODAY}" >> "${DAILY_FILE}"
        echo "- **記錄時間：** $(date '+%H:%M:%S')" >> "${DAILY_FILE}"
        echo "" >> "${DAILY_FILE}"
    fi
    
    echo "請輸入學習成果（按 Ctrl+D 結束輸入）:"
    echo "----------------------------------------"
    
    # 讀取多行輸入
    LEARNING_CONTENT=$(cat)
    
    if [ -n "${LEARNING_CONTENT}" ]; then
        # 添加時間戳記
        TIMESTAMP=$(date '+%H:%M:%S')
        
        echo "" >> "${DAILY_FILE}"
        echo "## 🎯 學習成果記錄 (${TIMESTAMP})" >> "${DAILY_FILE}"
        echo "${LEARNING_CONTENT}" >> "${DAILY_FILE}"
        echo "" >> "${DAILY_FILE}"
        
        echo "✅ 學習成果已記錄到: ${DAILY_FILE}"
        echo ""
        echo "📖 記錄內容預覽:"
        echo "----------------------------------------"
        tail -10 "${DAILY_FILE}"
        echo "----------------------------------------"
    else
        echo "❌ 未輸入內容，取消記錄"
    fi
    echo
}

# 2. 更新長期記憶
update_long_term_memory() {
    echo "🧠 更新長期記憶 (MEMORY.md)"
    echo
    
    # 檢查 MEMORY.md 是否存在
    if [ ! -f "${MEMORY_FILE}" ]; then
        echo "📄 創建長期記憶檔案: ${MEMORY_FILE}"
        echo "# 🧠 MEMORY.md - 長期記憶" > "${MEMORY_FILE}"
        echo "" >> "${MEMORY_FILE}"
        echo "## 📖 說明" >> "${MEMORY_FILE}"
        echo "這是拉斐爾的長期記憶檔案，記錄重要的學習成果、經驗教訓和系統知識。" >> "${MEMORY_FILE}"
        echo "" >> "${MEMORY_FILE}"
        echo "## 🗓️ 更新記錄" >> "${MEMORY_FILE}"
        echo "" >> "${MEMORY_FILE}"
    fi
    
    echo "請選擇要更新的記憶類型:"
    echo "1. 🎓 技能學習"
    echo "2. 🔧 問題解決"
    echo "3. 📈 經驗累積"
    echo "4. ⚙️ 系統優化"
    echo "5. 📝 自定義類別"
    echo "----------------------------------------"
    read -p "請輸入選擇 (1-5): " memory_type
    
    case "${memory_type}" in
        1)
            CATEGORY="技能學習"
            ;;
        2)
            CATEGORY="問題解決"
            ;;
        3)
            CATEGORY="經驗累積"
            ;;
        4)
            CATEGORY="系統優化"
            ;;
        5)
            read -p "請輸入自定義類別名稱: " CATEGORY
            ;;
        *)
            echo "❌ 錯誤選擇，使用預設類別: 經驗累積"
            CATEGORY="經驗累積"
            ;;
    esac
    
    echo ""
    echo "請輸入 ${CATEGORY} 的記憶內容（按 Ctrl+D 結束輸入）:"
    echo "----------------------------------------"
    
    MEMORY_CONTENT=$(cat)
    
    if [ -n "${MEMORY_CONTENT}" ]; then
        # 添加更新記錄
        UPDATE_DATE=$(date '+%Y-%m-%d %H:%M:%S')
        
        # 檢查是否已有該類別
        if ! grep -q "## ${CATEGORY}" "${MEMORY_FILE}"; then
            echo "" >> "${MEMORY_FILE}"
            echo "## ${CATEGORY}" >> "${MEMORY_FILE}"
            echo "" >> "${MEMORY_FILE}"
        fi
        
        # 添加記憶項目
        echo "### ${UPDATE_DATE}" >> "${MEMORY_FILE}"
        echo "${MEMORY_CONTENT}" >> "${MEMORY_FILE}"
        echo "" >> "${MEMORY_FILE}"
        
        # 更新更新記錄
        if grep -q "## 🗓️ 更新記錄" "${MEMORY_FILE}"; then
            # 在更新記錄部分添加
            sed -i "/## 🗓️ 更新記錄/a\\- ${UPDATE_DATE}: 更新 ${CATEGORY}" "${MEMORY_FILE}"
        fi
        
        echo "✅ 長期記憶已更新到: ${MEMORY_FILE}"
        echo ""
        echo "📖 更新內容預覽:"
        echo "----------------------------------------"
        tail -5 "${MEMORY_FILE}"
        echo "----------------------------------------"
    else
        echo "❌ 未輸入內容，取消更新"
    fi
    echo
}

# 3. 查看今日記憶記錄
view_today_memory() {
    echo "📋 查看今日記憶記錄"
    echo "日期: ${TODAY}"
    echo
    
    if [ -f "${DAILY_FILE}" ]; then
        echo "📄 檔案: ${DAILY_FILE}"
        echo "----------------------------------------"
        cat "${DAILY_FILE}"
        echo "----------------------------------------"
        echo ""
        echo "📊 統計資訊:"
        echo "- 檔案大小: $(wc -c < "${DAILY_FILE}") 位元組"
        echo "- 行數: $(wc -l < "${DAILY_FILE}")"
        echo "- 記錄次數: $(grep -c "學習成果記錄" "${DAILY_FILE}")"
    else
        echo "❌ 今日尚未有任何記憶記錄"
        echo "請使用選單 1 開始記錄"
    fi
    echo
}

# 4. 搜索歷史記憶
search_memory() {
    echo "🔍 搜索歷史記憶"
    echo
    
    read -p "請輸入搜索關鍵字: " search_term
    
    if [ -z "${search_term}" ]; then
        echo "❌ 請輸入搜索關鍵字"
        return 1
    fi
    
    echo ""
    echo "🔎 搜索結果:"
    echo "----------------------------------------"
    
    # 搜索每日記憶檔案
    echo "📅 每日記憶檔案:"
    find "${DAILY_MEMORY_DIR}" -name "*.md" -type f | while read file; do
        if grep -q -i "${search_term}" "${file}"; then
            echo "📄 $(basename "${file}"):"
            grep -i "${search_term}" "${file}" | head -3 | sed 's/^/  • /'
            echo ""
        fi
    done
    
    # 搜索長期記憶
    echo "🧠 長期記憶檔案:"
    if [ -f "${MEMORY_FILE}" ] && grep -q -i "${search_term}" "${MEMORY_FILE}"; then
        grep -i "${search_term}" "${MEMORY_FILE}" | head -5 | sed 's/^/  • /'
    else
        echo "  無相關結果"
    fi
    
    echo "----------------------------------------"
    echo
}

# 主程式
main() {
    while true; do
        show_menu
        
        case "${choice}" in
            1)
                record_today_learning
                ;;
            2)
                update_long_term_memory
                ;;
            3)
                view_today_memory
                ;;
            4)
                search_memory
                ;;
            5)
                echo "返回主選單..."
                break
                ;;
            *)
                echo "❌ 錯誤: 請輸入 1-5 的數字"
                echo
                ;;
        esac
        
        read -p "按 Enter 繼續..." wait
        echo
    done
    
    echo "========================================"
    echo "        記憶更新系統結束"
    echo "========================================"
}

# 執行主程式
main