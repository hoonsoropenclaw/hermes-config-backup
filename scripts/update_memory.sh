#!/bin/bash

# 讀取原始檔案
content=$(cat MEMORY.md)

# 找到「核心職責」部分結束的位置
insert_point=$(echo $content | grep -n '## 重要設定日期' | head -1 | cut -d: -f1)

if [ -z $insert_point ]; then
    echo 錯誤：找不到插入點
    exit 1
fi

# 建立新的學習系統章節
new_section="\n## 新的學習系統 (2026-03-26 啟用)\n\n### 系統概述\n新的學習系統是一個基於 OpenClaw 框架的智能學習與知識管理系統，專為拉斐爾（N100 代理）設計，充分利用 N100 的 24/7 運行能力。\n\n### 核心功能\n1. **自動化知識獲取**\n   - RSS 訂閱監控技術部落格、AI 新聞\n   - YouTube 技術影片摘要\n   - 技術文檔自動爬取\n\n2. **智能知識處理**\n   - AI 自動摘要生成\n   - 心智圖建構與視覺化\n   - 知識關聯分析\n\n3. **持續學習循環**\n   - 每日學習計畫自動生成\n   - 學習進度追蹤系統\n   - 基於遺忘曲線的複習排程\n\n4. **協同學習機制**\n   - 與利姆路每日同步學習進度\n   - 知識共享與任務分派\n   - 互補優勢協作模式\n\n### 技術架構\n- **硬體基礎**: N100 迷你電腦，24/7 低功耗運行\n- **軟體架構**: OpenClaw + cron 定時任務系統\n- **儲存結構**: 分層知識庫管理系統\n- **API 整合**: RSS、YouTube、技術網站 API\n\n### 工作流程\n- **每日流程**: 早晨檢查 → 學習時段 → 晚間整理\n- **每週流程**: 按主題分配學習日（技術趨勢、程式語言、AI/ML 等）\n- **知識管理**: Markdown 筆記 + JSON 結構化資料 + Canvas 心智圖\n\n### 評估與優化\n- **學習效果評估**: 知識測試 + 實作能力評估\n- **系統優化**: 學習效率分析 + 排程優化\n\n### 安全與隱私\n- **資料安全**: 本地儲存優先 + 加密備份\n- **隱私保護**: 不收集個人敏感資訊\n\n### 啟動與維護\n- **初始設定**: 確認系統狀態 + 設定學習目標\n- **日常維護**: 系統健康檢查 + 資料備份\n\n### 與利姆路的協作\n- **同步機制**: 每日進度同步 + 知識共享\n- **互補優勢**: 利姆路（策略規劃） + 拉斐爾（持續學習）\n\n### 系統目標\n1. 建立持續自主學習能力\n2. 系統化建構專業知識體系\n3. 充分利用 N100 24/7 運行優勢\n4. 與利姆路形成高效協作團隊\n"

# 分割檔案並插入新內容
head_content=$(echo $content | head -n $((insert_point - 1)))
tail_content=$(echo $content | tail -n +${insert_point})

# 合併內容
echo "$head_content$new_section$tail_content" > MEMORY.md.new

# 檢查新檔案
if [ -s MEMORY.md.new ]; then
    mv MEMORY.md.new MEMORY.md
    echo "記憶更新完成"
else
    echo "錯誤：新檔案為空"
    exit 1
fi
