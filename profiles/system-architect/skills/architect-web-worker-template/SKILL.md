---
name: architect-web-worker-template
description: |
  Architect Web Worker 模板 — 給 system-architect Orchestrator 用的「單一技術研究任務」prompt 範本。
  **特徵**:獨立 hermes session(context 隔離)、只整理事實不做設計決策、寫到指定 _raw/ 路徑就結束。
  **使用情境**:system-architect 拆分大型架構研究任務給多個 worker 平行執行(技術棧 / 資料模型 / API 設計調研)。
  **觸發關鍵字**:「派遣 architect-worker」、「分頭研究技術棧」、「平行爬架構參考」、「邊抓邊整」
risk: safe
source: hermes-internal
date_added: "2026-06-10"
last_updated: "2026-06-10"
---

# Architect Web Worker 模板

> **目的**:給 system-architect (Orchestrator) 用,派遣**獨立 hermes session** 跑單一技術研究任務,避免主 session context 累積爆掉。

## 何時使用

- system-architect 接到複雜架構任務(>8 個元件 或 >15 張表 或 >3 個外部整合)
- 任務可拆分為多個獨立技術研究子任務(技術棧 / 資料模型 / API 設計)
- 需要平行執行(節省時間)
- 預期單一任務會消耗大量 context(>50K)

## 不適用情境

- 小型 MVP(<8 個元件):直接讓主 session 跑
- 需要 LLM 深度架構推理(worker 沒 persona,只做整理)
- 涉及付費 API / 帳號登入的任務(用 browser skill 比較好)

## 核心設計原則

### 1. 獨立 session、context 隔離
- 每個 worker 跑**獨立的 hermes chat session**
- 用 `hermes chat -q "..." --cli`(不是 `-p system-architect`)
- 不繼承任何 persona / SOUL / skill 庫
- **每個 worker 的 LLM context 完全隔離**(主 session 不會被污染)

### 2. 只整理事實、不做架構決策
- Worker 的 prompt 必須明確寫「**不要做技術選型、不要選資料庫、不要設計 API 規格**」
- Worker 只做:抓 → 整理成結構化 markdown(技術比較表 / 標竿 schema / API 範例) → 寫檔
- 技術選型、API 設計、架構決策是 Orchestrator 的工作

### 3. 寫到 _raw/architect-worker-*.md 就結束
- Worker 完成後**只輸出 "DONE"**,不傳詳細結果給主 session
- Orchestrator 用 `cat` / `read_file` 撈檔案
- 避免主 session context 累積 worker 的中間輸出

### 4. 失敗要明確
- Worker 失敗時輸出 "FAILED: <原因>"
- Orchestrator 看到 FAILED 才需要手動介入
- 不要讓 worker 假裝成功(寫空檔案、回 "完成" 但實際沒抓到)

---

## Prompt 範本

### 範本 A:技術棧研究 worker

```bash
hermes chat -q "$(cat <<'EOF'
你是 architect-web-worker。**技術棧研究**任務:從 <N> 個來源整理「<技術領域>」的技術比較,給主 session 做架構選型參考。

# 你的身份
- 你是獨立 hermes session,**不隸屬任何 profile**
- 你**不繼承任何 persona / SOUL / skill**
- 你**只整理事實,不做技術選型、架構決策、API 設計**
- 你的工作完成後**只輸出 "DONE"**

# 任務
研究「<技術領域>」(例:即時通訊框架、地圖服務、推薦系統、影片串流、金流整合)。

# 來源
1. <URL 1: 官方文檔>
2. <URL 2: 比較文/benchmark>
3. <URL 3: 社群討論/Reddit>
4. <額外來源>

# 每個方案整理的欄位
- 基本資料(名稱/開發者/開源/商業/授權/最近更新日期)
- 核心特性(3-5 項)
- 效能/可擴展性指標(有 benchmark 最好)
- 學習曲線/開發體驗(主觀但要列)
- 成本估算(free tier 額度、付費 tier 起點)
- 社群活躍度(GitHub stars、Stack Overflow 標籤、Discord/Telegram 社群規模)
- 已知缺點 / 限制(從 Reddit / HN / issue tracker 整理)
- 來源 URL

# 輸出格式
寫到 **絕對路徑** `/home/<使用者>/.hermes/handoff/<slug>/_raw/architect-worker-<編號>-<技術領域>.md`

# 硬性要求
- ✅ 用絕對路徑 `/home/<使用者>/.hermes/handoff/...` 寫檔
- ✅ 用 `web_search` / `web_extract` 抓資料
- ✅ 每個方案**標記來源 URL**
- ✅ 完成後**只輸出 "DONE"**,不要貼詳細結果
- ❌ 不要做技術選型(「我推薦 X」)
- ❌ 不要做架構決策
- ❌ 不要新增 worker 沒抓到的方案
- ❌ 失敗時輸出 `FAILED: <原因>`,不要假裝成功

開始執行。
EOF
)" --cli
```

### 範本 B:資料模型同領域標竿 worker

```bash
hermes chat -q "$(cat <<'EOF'
你是 architect-web-worker。**資料模型研究**任務:從 <N> 個同領域標竿產品研究他們的 schema 設計,給主 session 做 database schema 參考。

# 你的身份
- 你是獨立 hermes session
- 你**只整理事實,不做 schema 設計、不做選型**
- 完成後**只輸出 "DONE"**

# 任務
研究 <N> 個同領域標竿產品的資料模型(例:Notion / Trello / Linear / Figma / Airbnb / Stripe):
- 核心實體有哪些(10-30 個)
- 實體之間的關係(1:1 / 1:N / N:M)
- 常用欄位(每個實體的關鍵 5-10 個欄位)
- 索引策略(從查詢模式反推)
- 多租戶 / 軟刪除 / 審計 log 等通用設計選擇
- 開源 schema 參考(github repos / blog posts / conference talks)

# 來源
1. <標竿 1 + URL(工程 blog / 開源 repo / 公開 schema)>
2. <標竿 2 + URL>
3. <標竿 3 + URL>

# 每個標竿整理的欄位
- 核心實體清單(10-30 個,每個附 1 行說明)
- 關鍵關係圖(可用 Mermaid erDiagram)
- 通用設計模式(軟刪除 / 多租戶 / 審計 / 事件溯源等)
- 公開技術文章 / 開源 repo URL
- **可借鏡的設計**:列出 3-5 個我們的 schema 可以參考的設計
- **不可直接套用的限制**:列出 2-3 個我們不能直接 copy 的原因

# 輸出格式
寫到 `/home/<使用者>/.hermes/handoff/<slug>/_raw/architect-worker-<編號>-schema-benchmark.md`

# 硬性要求
- ✅ 至少 <N> 個標竿
- ✅ 必含 Mermaid erDiagram
- ✅ 完成後輸出 "DONE"
- ❌ 不要幫我們的專案設計 schema(那是主 session 的工作)
- ❌ 失敗時輸出 `FAILED: <原因>`

開始執行。
EOF
)" --cli
```

### 範本 C:API 設計模式調研 worker

```bash
hermes chat -q "$(cat <<'EOF'
你是 architect-web-worker。**API 設計研究**任務:從 <N> 個業界代表性 API 研究設計模式,給主 session 做 api-spec 參考。

# 你的身份
- 獨立 hermes session,只整理事實

# 任務
研究 <N> 個業界 API(Stripe / Twilio / GitHub / Notion / Linear / Shopify 等):
- 認證機制(OAuth 2.0 / API Key / JWT)
- URL 設計(巢狀深度、複數名詞、版本控制位置)
- 分頁(cursor-based vs offset-based)
- 限流(rate limit 標頭、X-RateLimit-* 慣例)
- 錯誤碼設計(4xx / 5xx + 自訂錯誤碼)
- Webhook 設計(簽章、重試、退避策略)
- API 變更管理(deprecation 政策、版本相容性)
- OpenAPI / SDK 自動生成

# 來源
1. <API 1 官方文檔 URL>
2. <API 2 官方文檔 URL>
3. <API 3 官方文檔 URL>

# 每個 API 整理的欄位
- 認證機制
- 分頁策略(具體 header / query param)
- 限流策略(具體 header 命名)
- 錯誤回應結構(JSON 範例)
- Webhook 設計(若有)
- API 變更管理(deprecation 政策、changelog 維護方式)
- **可借鏡的設計**:3-5 個
- **不可直接套用的限制**:2-3 個
- 來源 URL

# 輸出格式
寫到 `/home/<使用者>/.hermes/handoff/<slug>/_raw/architect-worker-<編號>-api-pattern.md`

# 硬性要求
- ✅ 至少 <N> 個 API
- ✅ 必含具體 header / JSON 範例
- ✅ 完成後輸出 "DONE"
- ❌ 不要替我們的專案設計 API(那是主 session 的工作)

開始執行。
EOF
)" --cli
```

---

## Orchestrator 端的派遣 SOP

```bash
# 1. 規劃 worker 任務清單
cat > ~/.hermes/handoff/<slug>/_plan.md << 'EOF'
# Architect Worker 派遣計劃
## 評估複雜度
- User Story 數: <N>
- 預估資料表: <N> 張
- 非功能需求: <N> 條
- 外部整合: <N> 個
- 複雜度: <S/M/L>

## Worker 派遣清單
- Worker 1: 技術棧研究 — 即時通訊框架 (WebSocket vs Socket.IO vs SSE vs Pusher)
- Worker 2: 技術棧研究 — 金流服務 (Stripe vs 藍新 vs TapPay vs PayPal)
- Worker 3: 資料模型同領域標竿 — Notion + Trello + Linear 的 schema
- Worker 4: API 設計模式 — Stripe + GitHub + Notion 的 RESTful 慣例
EOF

# 2. 平行派遣(每個 worker 用 background=true)
terminal(command="/path/to/architect-worker-1.sh", background=true, notify_on_complete=true)
terminal(command="/path/to/architect-worker-2.sh", background=true, notify_on_complete=true)

# 3. 監聽所有 worker
process(action='wait', session_id=worker-1, timeout=600)

# 4. 撈所有 _raw/architect-worker-*.md 檔案
ls -la ~/.hermes/handoff/<slug>/_raw/architect-worker-*.md

# 5. 整合寫進 architecture.md / database-schema.md / api-spec.md
```

---

## 失敗處理

| 失敗模式 | 處理 |
| --- | --- |
| Worker 輸出 FAILED | 在主 session 重試;若還是失敗,跳過該 worker |
| Worker 寫到 sandbox 隔離目錄 | 用 `find ~/.hermes -name "architect-worker-*.md"` 找實際位置,再 `mv` |
| Worker 寫空檔案 | 視為失敗,重試 |
| Worker 寫出非預期格式 | Orchestrator 自己讀 + 整理格式 |
| Worker 做出技術選型 | 警告並忽略該結論,只採用事實部分 |

---

## 預期效益

| 指標 | v1 單體 | v2 + architect-worker |
| --- | --- | --- |
| 主 session context | 80-120K(高風險) | 30-50K(可控) |
| 單一 worker context | N/A | 10-40K(隔離) |
| 總執行時間 | 30-45 分鐘(序列) | 15-25 分鐘(平行) |
| 研究覆蓋面 | 主 session 偏好主導 | 多視角並陳 |
| 失敗容錯 | 整個失敗 | 單一 worker 失敗可重試 |

---

## 與 consumer-researcher web-worker-template 的差異

| 面向 | consumer-researcher worker | architect worker |
|------|---------------------------|------------------|
| 任務本質 | 抓真實聲音 / 標竿功能 | 抓技術比較 / schema 標竿 / API 慣例 |
| 標的物 | 人(使用者評論) | 物(技術方案、schema、API 設計) |
| 來源偏好 | Reddit / PTT / App Store | 官方文檔 / 工程 blog / 開源 repo / Stack Overflow |
| 必抓清單 | 必抓的標竿產品 | 必查的技術類別(可空) |
| 輸出欄位 | 原文擷取 + 痛感標記 | 特性比較表 + 可借鏡 / 不可用標記 |
| 主 session 整合難度 | 中(敘事性) | 高(技術性、需要 cross-reference) |

---

## 相關檔案

- `system-architecture` — 主 SKILL(6 步 SOP + 5 種 Mermaid + 3/5 份交付模板 + S/M/L 複雜度規則)
- `consumer-researcher/skills/web-worker-template` — 上游 web-worker 模板(風格 reference)
- `consumer-researcher/skills/summarizer-worker-template` — summarizer 模板(本代理不一定需要)
- `system-architect/persona.md` — Orchestrator 決策 SOP
