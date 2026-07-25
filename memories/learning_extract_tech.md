# 技術領域學習經驗萃取（赫米斯繼承前任拉斐爾 OpenClaw 時代,2026-06-08）

> **歷史註記**：本檔由前任拉斐爾 OpenClaw 套件代理（2026-05-30 ~ 2026-06-08）建立,2026-06-08 OpenClaw 反安裝後由赫米斯（繼承後的現任拉斐爾）接管。內容描述的「技術領域學習萃取」是 OpenClaw 拉斐爾時代的成果,赫米斯保留、繼續擴充。源頭 `SKILL_CATALOG.md` 跟 `progress.md` 路徑在 OpenClaw 反安裝後已失效,本檔內容**仍有效**（是 L3 抽象經驗而非路徑參照）。

萃取自 SKILL_CATALOG.md 和 progress.md  
領域：mcp, system, code, web, browser  
格式：If→Then（條件與行動對）

---

## MCP（Model Context Protocol）

### 基礎與生態

If 需要快速建立 MCP Server，Then 使用 FastMCP 3.2.4 Python SDK，它支援 97M+ SDK 下載和 19,831+ MCP 伺服器。

If 需要整合多個 MCP 工具，Then 使用 MCP 工具編排系統（ToolOrchestrator），它包含 DependencyResolver、ExecutionPlanner、ToolChainBuilder 五大模組，支援拓撲排序分層和循環依賴檢測。

If 擔心 MCP 安全問題，Then 遵循 OWASP MCP Top 10（Confused Deputy/Token Passthrough/SSRF/Injection），並使用 snyk/agent-scan 和 mcps-audit 安全掃描器。

If 需要讓 MCP Server 之間互相溝通，Then 採用 MCP + A2A 雙通訊協定框架，支援跨協議互操作。

### 金融應用

If 需要串接股票數據，Then 使用 yfinance-mcp-server 或 maverick-mcp，它們提供 Quotes+Backtesting+Paper Trading 功能。

If 需要多源金融數據整合，Then 建構四層備援（十二Data→Alpha Vantage→Finnhub→yfinance），並實作 UnifiedDataAggregator 統一聚合器。

### 學校行政應用

If 需要學校行政 MCP Server，Then 實作 13 個工具：get_employees/leaves/calendar/meetings/equipment/salary/stats/documents/regulations/announcements/audit/users/settings。

If MCP Tool 執行失敗，Then 實作自動備援：快取系統（5分鐘 TTL）+ 多源故障轉移（Stooq/SEC/ECB/Binance）。

---

## System（系統與架構）

### Sub-agent 設計

If 設計 Sub-agent 行為，Then 採用 context-blind 設計（隔離上下文）+ Progressive Disclosure（Level 1-3 增量揭示）+ Role-Based Template（角色+行為邊界定義）。

If 需要 Tool Learning，Then 使用三階段：目標導向（Level 1）→ 工具輸出示範（Level 2）→ 實作驗證（Level 3），實測 100% 成功率。

If 需要 Multi-Agent 分工，Then 選擇 Supervisor/Network/Pipeline/Hierarchical/Parallel 五種模式之一，視任務复杂度而定。

### 記憶系統

If 需要長期記憶管理，Then 使用 MemPalace AAAK 壓縮（1.7x-30x 壓縮率）+ 混合檢索（RRF 融合關鍵詞+語意向量搜尋）+ 生命週期（EPHEMERAL→WORKING→IMPORTANT→CRITICAL→PERMANENT）。

If 需要跨 session 記憶持續，Then 使用 SubAgentMemoryManager（關鍵詞萃取+Jaccard相似度+SQLite持久化+TTL過期機制）。

### 自癒系統

If 系統需要自我修復，Then 建構三層機制：自動重試（第一層）→ 優雅降級（第二層）→ 升級告警（第三層）。

If 需要健康監控，Then 實現 HealthProbe + CircuitBreaker（熔斷器）+ Bulkhead（隔離區）+ SelfHealingCoordinator。

### Cron 排程

If 需要優化 Cron 排程，Then 使用 cron_optimizer.sh 分析並產生優化配置，採用時段感知並行調整（凌晨+1/白天-1）和自適應學習加速器。

---

## Code（程式設計）

### API 設計

If 設計 REST API，Then 遵循 OAS 3.1，實作統一的錯誤處理、重試機制、Rate Limiting 和快取層。

If 需要高效 API 客戶端，Then 使用 httpx（非同步支援）或 requests，並包裝統一的 UnifiedDataAggregator。

### 非同步模式

If 使用 Python 3.11+，Then 採用 AsyncPipeline v2：TaskGroup + gather_with_concurrency + Semaphore 並發限制 + asyncio.timeout 超時控制。

If 需要生產者-消費者模式，Then 使用 AsyncQueue + Queue-based dispatcher，可提升 5x 效能。

### 架構模式

If 需要微服務架構，Then 採用 API Gateway + Service Mesh + 分庫分表模式。

If 需要狀態機設計，Then 使用 LangGraph State Machine（Conditional Edge + 多步驟審核）處理行政工作流。

---

## Web（網頁與爬蟲）

### 前端框架

If 選擇前端框架，Then 考慮 Next.js/Vue/Svelte 其中之一；Web Components 2026 成熟度：Lit（~5KB gzipped）vs React（~40KB）。

### 爬蟲框架選擇

If 需要一般爬蟲，Then 使用 Scrapling（自適應解析+隱形抓取+Cloudflare繞過）或 Crawlee Python SDK（三種模式+請求佇列+自動重試）。

If 需要 LLM 友善爬蟲，Then 使用 Crawl4AI（Markdown 生成+結構化萃取+51k+⭐）或 ScrapeGraphAI（自然語言驅動+6種Pipeline）。

If 需要高速 HTTP 請求，Then 使用 hrequests（TLS指紋偽裝+selectolax解析+gevent並發）。

### 反偵測

If 網站有反機器人防護，Then 按等級選擇：中等防護用 Camoufox（Firefox反偵測），高防護用 Patchright（drop-in Playwright替代+CDP leak修補）或 DrissionPage（瀏覽器+HTTP混合模式）。

### 即時通訊

If 需要 WebSocket 即時功能，Then 使用 WebSocketNotificationServer + SSENotificationServer 備援，實作 NotificationPriority 和 NotificationChannel 機制。

### 即時協作

If 需要協作編輯功能，Then 採用 CRDT（Yjs YATA 演算法）+ WebSocket Provider，可解決 OT vs CRDT 的衝突問題。

---

## Browser（瀏覽器自動化）

### 框架選擇

If 需要跨平台瀏覽器自動化，Then 使用 Playwright（14,582 ⭐），支援 Windows/Linux/macOS， 並用 Playwright Stealth 反偵測。

If 需要 AI 驅動的瀏覽器自動化，Then 使用 Skyvern（Vision LLMs 驅動+四大 AI 命令：act/extract/validate/prompt）或 Browser Use（79k+ ⭐）。

If 需要 CDP WebDriver-Free，Then 使用 Pydoll（CDP over WebSocket + Pydantic 萃取 + Shadow DOM 支援）。

### 指紋偽裝

If 需要瀏覽器指紋偽造，Then 实现四個級別：WebDriver 標誌（基礎）→ Canvas/WebGL（中等）→ Font/Audio（高等）→ Timezone/Hardware（專業）。

If 需要專業級反偵測，Then 使用 Kameleo（C++引擎+雙瀏覽器引擎）或 Undetectable（10+指紋維度欺騙）。

### 學校行政應用

If 需要自動化校務系統登入，Then 建構 BrowserAutomation 類，處理政府表單自動化（CDC 通報/教育統計），注意 CAPTCHA 需要額外處理。

If 需要多瀏覽器引擎整合，Then 使用 BrowseForge（Camoufox+CloakBrowser雙引擎+REST API+MCP Server+Playwright）。

---

## 跨領域整合經驗

### LINE 整合

If 需要 LINE 通知整合，Then 使用 LINE Messaging API + Flex Message + Postback（核准/拒絕/確認/修改），並加入 Rich Menu + Quick Reply 支援。

### 文件處理

If 需要 Word 文件自動化，Then 使用 docxtpl（Jinja2+python-docx）+ CSV 批次載入，支援通告+獎狀+證明書+成績單+公函。

If 需要 PDF 處理，Then 使用 PyMuPDF（表格萃取+OCR+敏感資訊修訂+PDF合併拆分）。

### 數據存儲

If 需要快速數據處理，Then 使用 pandas + openpyxl（公式+圖表+條件格式化），與 docxtpl+SMTP 整合。

If 需要持久化存儲，Then 使用 SQLite（任務佇列+狀態機+日誌稽核）+ FastAPI REST API。

---

## 驗證與測試經驗

If 驗證 Sub-agent 工具學習，Then 採用 sessions_spawn 測試 Progressive Disclosure + Tool Learning Level 3，測試成功標準：9/9 實體 100% 提取準確率。

If 測試 MCP 安全，Then 使用 OWASPMCPScanner 類（SecurityThreat 枚舉 MCP01-10）+ CWE 弱點關聯 + 正規表達式模式匹配。

If 驗證批次處理，Then 使用 DataRepairEngine（Pydantic 驗證框架），實測成功處理 50 筆資料，耗時 0.12 秒。

---

*萃取時間：2026-05-30*
*來源：SKILL_CATALOG.md + progress.md*