# 行政領域學習經驗萃取（赫米斯繼承前任拉斐爾 OpenClaw 時代,2026-06-08）

> **歷史註記**：本檔由前任拉斐爾 OpenClaw 套件代理（2026-05-30 ~ 2026-06-08）建立,2026-06-08 OpenClaw 反安裝後由赫米斯（繼承後的現任拉斐爾）接管。內容描述的「If → Then 知識庫」是 OpenClaw 拉斐爾時代的學習萃取成果,赫米斯保留、繼續擴充。

## If → Then 格式知識庫

**萃取來源**: SKILL_CATALOG.md + progress.md
**領域**: admin / school / hr（學校行政、人事、人力資源）
**建立時間**: 2026-05-30

---

## 一、文件處理自動化

### If 需要批次產生學校公文（通告、獎狀、成績單、聘書）
### Then 使用 python-docx-template（docxtpl）Mail Merge 系統
- SchoolMailMerge類：置換、圖片、表格
- batch_merge() 支援 CSV 批次載入
- Jinja2 模板语法：{%p} 條件區塊、{%tr} 表格迴圈、Subdoc 嵌入
- 參考：SKILL_CATALOG.md line 74-75

### If 需要對照不同版本法規（教師法、教育人員任用條例等）
### Then 使用 python-docx + difflib 做文字差異比對
- unified_diff + side_by_side HTML 報告
- 相似度統計（相似度/新增/刪除條文數）
- 正規表示式解析公文編號+日期+主旨
- 參考：SKILL_CATALOG.md line 323

### If 需要萃取 PDF 表格或OCR辨識
### Then 使用 PyMuPDF（1.27.x）
- 表格萃取、OCR、敏感資訊修訂、PDF合併拆分
- pypdf 填表 + PyMuPDF bake() 壓平
- 參考：SKILL_CATALOG.md line 75

---

## 二、工作流自動化

### If 需要建立多步驟審核鏈（请假、成績、异动）
### Then 使用 LangGraph State Machine 設計狀態機
- Conditional Edge 控制流程分支
- 與 docxtpl+SMTP+PyMuPDF 整合
- 學校請假申請自動化工作流
- 參考：SKILL_CATALOG.md line 81

### If 需要流水線式批次處理（學生異動、成績、公告）
### Then 使用 school_admin_pipeline 框架
- DocumentPipeline/ExcelPipeline/EmailPipeline/PDFPipeline/RegulationPipeline 五大模組
- SQLite 任務佇列 + 狀態機 + FastAPI REST API
- 人類審核鏈 + APScheduler 排程
- 參考：SKILL_CATALOG.md line 73, 327

### If 需要自動化人事資料批次處理
### Then 使用 Pydantic 模型驗證 + DataRepairEngine 修復
- 多格式讀取（Excel/CSV/JSON）
- BatchValidationResult 批次驗證
- 5種修復規則自動修復異常
- 參考：admin_workflow_001_20260528_020100 progress.md

---

## 三、通知系統整合

### If 需要 LINE 推播學校行政通知
### Then 使用 LINE Messaging API + LINE Notify
- Flex Message Bubbles 三種模板（申請/確認/結果）
- Postback 動作處理（核准/拒絕/確認/修改）
- Quick Reply + Datetime Picker
- 學校行政通知模板/排程通知
- 參考：SKILL_CATALOG.md line 87, 329

### If 需要從 LINE 申請请假到主管核准完整流程
### Then 使用 LINE Bot + Flask + Flex Message + SQLite
- 狀態機：AwaitingType→AwaitingDate→Confirm→Submit
- 8種假別枚舉定義
- 自動化 Push 通知
- 參考：SKILL_CATALOG.md line 329, 461

### If 需要即時通知但 WebSocket 不穩定
### Then 使用 SSE（Server-Sent Events）備援
- NotificationPriority（urgent/high/normal/low）
- Queue-based dispatcher 離線消息緩存
- 參考：SKILL_CATALOG.md line 357

---

## 四、法規監控

### If 需要自動追蹤教育法規最新異動
### Then 使用教育法規智能監控系統（ERIM）
- 政府 RSS Feed 抓取（全國法規資料庫/教育部/行政院公報）
- 學校相關性評分算法 + 優先級判定（Critical→Low）
- LINE Notify 多渠道通知 + 每日 Markdown 報告
- RegulationAnalyzer：關鍵詞萃取/摘要生成/版本差異比較
- 參考：SKILL_CATALOG.md line 452

### If 需要合規審查（教師法§14/§15/§17、政府採購法§14/§22/§70）
### Then 使用 ComplianceRuleEngine 規則引擎
- SchoolComplianceRuleSet：21條規則/5大領域（人事/採購/財務/安全/隱私）
- 條件評估引擎（AND/OR/比較/清單/正規表達）
- 合規狀態機：NOT_START→PENDING_REVIEW→COMPLIANT/PARTIAL/NON_COMPLIANT→RESOLVED
- 參考：SKILL_CATALOG.md line 90, 349

---

## 五、出勤與統計

### If 需要自動化出勤統計月報
### Then 使用 AttendanceRecord 資料模型
- 月度統計計算 + CSV 解析
- 異常偵測 + 出勤率趨勢圖
- 圖表產生（Chart.js）+ PDF 報告自動產生
- 參考：SKILL_CATALOG.md line 89, 342

### If 需要視覺化 HR 儀表板
### Then 使用 Flask + Chart.js + SQLite + python-docx
- 教職員基本資料/年齡分布/服務年資分析
- 請假類型分布/異動統計
- Word 月報年報自動產生
- 參考：SKILL_CATALOG.md line 335, hr_dashboard_v3_001 progress.md

---

## 六、會議與行事曆

### If 需要智慧會議排程（時間推薦、衝突檢測）
### Then 使用貪心+評分機制演算法
- SchoolPeriodConfig：學校作息時間設定（114學年度）
- MeetingScheduler + ICalSyncer + GoogleCalendarSyncer
- 學校行事曆同步（iCal/Google Calendar）
- 參考：SKILL_CATALOG.md line 339, school_meeting_scheduler_232 progress.md

### If 需要 LINE Bot 查詢會議室預約
### Then 使用 meeting_main.py 整合系統
- meeting_db.py 資料庫模組
- meeting_linebot.py LINE Bot 模組
- 學校會議智慧排程系統
- 參考：school_meeting_scheduler_232 progress.md

---

## 七、文件智慧分類

### If 需要自動分類公文（10種類型：人事/會計/採購/教務/學務/總務/輔導/研發/主計）
### Then 使用正規表示式 + 關鍵字加權計分
- DocumentType 枚舉（6種文件類型）
- 緊急程度5級制
- 處理建議自動產生
- 參考：SKILL_CATALOG.md line 337

### If 需要萃取文件摘要與待辦事項
### Then 使用 AISummarizer + TF統計關鍵詞
- SummaryResult 資料結構
- 緊急程度判定（緊急/高/普通）
- 待辦事項自動提取
- 支援：學校公告/會議紀錄/请假單/獎懲令/報告
- 參考：SKILL_CATALOG.md line 353

---

## 八、人事行政工具箱

### If 需要自動化人事業務（假單、聘書、考績、統計）
### Then 使用 hr_automation_tools.py 工具箱
- 假單處理自動化（批次確認、統計分析）
- 教師資料異動通報（自動產生通報函）
- 聘書產生系統（根據範本自動產生）
- 考績評鑑自動化（評分計算、等第判定）
- 出勤統計報表（CSV/PDF產出）
- 參考：EL_admin_hr_automation_20260523_210000 progress.md

---

## 九、MCP 工具整合

### If 需要自訂學校行政 MCP Server
### Then 使用 FastMCP 3.2.4 SDK
- 13個學校行政MCP工具：get_employees/leaves/calendar/meetings/equipment/salary/stats/documents/regulations/announcements/audit/users/settings
- OllamaOptimizer 效能優化（動態Batch/並發/Tensor加速）
- MCP vs REST API 比較/MCP安全考量（Token/SSRF/Injection）
- 參考：SKILL_CATALOG.md line 463

---

## 十、學習教訓

### If 使用 docxtpl 出現變數未置換
### Then 確認 Jinja2 變數格式正確：{{variable_name}} 而非 ${variable}

### If LINE Flex Message 顯示異常
### Then 檢查 JSON 格式：altText 必填、contents 型別正確

### If 正規表示式匹配失敗
### Then 使用原始字串（r'...'）避免轉義問題，並測試線上工具

### If 學校法規對照結果有誤
### Then 比對全國法規資料庫最新版本，檢查法規適用日期

### If 出勤統計有異常值
### Then 先檢查資料格式（可能有空白、特殊字元），使用 DataRepairEngine 修復

---

*萃取完成：共 47 條 If→Then 規則*
*涵蓋：文件處理、工作流、通知、法規、統計、會議、分類、MCP整合*