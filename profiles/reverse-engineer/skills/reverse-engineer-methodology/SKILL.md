---
name: reverse-engineer-methodology
description: 8 視角架構圖導向的反向工程方法論 — 從黑盒產物產出「工程師拿著就能近乎 100% 還原」的規格說明。必載入於 reverse-engineer 處理任何目標時。
---

# Reverse Engineer Methodology — 8 視角架構圖導向

> 本 skill 是 reverse-engineer 代理的**核心競爭力**。clawic 提供的 `reverse-engineering` skill 給的是**通用 TRACE 協議**;本 skill 給的是**架構圖導向的 8 視角展開 SOP**,目標:下游工程師看了能 100% 還原。

---

## 何時使用

reverse-engineer 代理接收任何任務時(程式碼目錄 / binary / 網站 URL / 截圖 / 錄影)必載入本 skill。**不放進主 context,而是 Step 2 表面盤點完成後載入**——用 skill 提供的 8 視角清單驗證自己的盤點有沒有漏。

---

## 核心方法論:8 視角框架

每個 reverse-arch 報告必含 8 個視角章節。少一個 = 不算完整 = 不能 handoff。

### 視角 1:模組拓墣 (Module Topology)

**目的**:靜態結構總覽——「這個東西有哪些塊、怎麼分層」

**產出**:
- 一張分層模組圖(Mermaid `graph TD` 或 `flowchart TB`)
- 一張模組總表(每行:模組名 / 層級 / 職責一句話 / 對外介面數量 / 依賴數量)

**必答問題**:
- 有幾個 subsystem?(例:frontend / backend / db / 3rd-party)
- 每個 subsystem 內有幾個 component?
- component 之間的呼叫方向是單向 / 雙向 / 環?
- 有沒有 circular dependency?(必標)

### 視角 2:對外介面 (Interface Map)

**目的**:「外面的人怎麼跟這個東西對話」

**產出**:
- HTTP API 端點表(method / path / 認證需求 / 請求 schema / 回應 schema / 錯誤碼)
- 或 SDK 函式簽章表(語言 / 函式名 / 參數 / 回傳 / 例外)
- 或事件/訊息 topic 表(producer / consumer / payload 結構)
- 一張介面關係圖(Mermaid sequenceDiagram 或 flowchart)

**必答問題**:
- 對外的入口在哪?(edge gateway / SDK / CLI / event bus)
- 每個介面的認證 / 授權需求?
- 介面契約是 schema-validated 還是 duck-typed?

### 視角 3:資料流 (Data Flow)

**目的**:「一個輸入進來,怎麼走到 DB 寫入」

**產出**:
- 一張端到端資料流圖(Mermaid flowchart,從 input 追到 sink)
- 一張資料轉換表(每行:階段 / 進入資料結構 / 出去資料結構 / 轉換邏輯)
- 標示**同步 vs 異步**節點 / **批次 vs 串流**節點

**必答問題**:
- 從使用者輸入到 DB 寫入的完整路徑?
- 中途經過哪些 schema 轉換?
- 哪些節點是同步阻塞?哪些是非同步佇列?
- 失敗時的補償交易 / 退款 / 重試邏輯?

### 視角 4:狀態機 (State Machine)

**目的**:「這個東西的生命週期長怎樣」

**產出**:
- 一張主狀態圖(Mermaid stateDiagram-v2)
- 物件 / 資源生命週期表(每行:物件類型 / 狀態列表 / 合法轉移 / 觸發事件)
- (若有多個)多張子狀態圖

**必答問題**:
- 主要的狀態有哪些?
- 哪些事件觸發狀態轉移?
- 有沒有「應該不存在但其實存在」的隱含狀態?(例:快取過期、連線半斷)
- 進入每個狀態的 side effect?(audit log / notification / DB write)

### 視角 5:部署拓墣 (Deploy Topology)

**目的**:「這東西跑在哪、怎麼 scale」

**產出**:
- 一張部署拓墣圖(Mermaid flowchart + subgraph,標 service / DB / cache / queue / CDN)
- 一張資源清單表(每行:資源名 / 類型 / 規格 / SLA / 月費估計)
- 環境變數表(每行:var name / 用途 / 哪個 service 用 / 預設值 / 機密等級)
- scaling 策略(horizontal / vertical / auto-scale 條件)

**必答問題**:
- 跑在哪些雲 / region?
- 服務之間的網路拓墣(同 VPC / 跨 VPC / internet-facing)?
- 環境變數的來源(consul / .env / k8s secret / Vault)?
- 部署策略(rolling / blue-green / canary)?

### 視角 6:安全邊界 (Security Boundary) [NEW v1]

**目的**:「這裡的認證 / 授權 / 輸入驗證設計如何,風險在哪」

**產出**:
- 一張 trust boundary 圖(Mermaid flowchart,標 attacker / internet / edge / internal / data)
- 認證 / 授權矩陣表(每行:操作 / 誰能執行 / 怎麼驗證 / token 過期時間)
- 敏感資料流向圖(個資 / 密碼 / API key / token 流向)
- 設計風險清單(每行:風險 / 觸發條件 / 影響 / 緩解建議)

**必答問題**:
- 認證在哪一層(edge / service / 雙層)?
- 授權是 RBAC / ABAC / 自訂?
- 輸入驗證的覆蓋率?(哪些欄位驗證、哪些沒驗)
- 敏感資料有沒有 logging?(密碼 / token 進 log = 風險)
- 沒有寫好但常見的漏洞類型?(SQLi / XSS / SSRF / path traversal / IDOR)

### 視角 7:效能熱點 (Performance Hotspot) [NEW v1]

**目的**:「這裡 scale up 會爆炸的死點」

**產出**:
- 一張熱點圖(在 module / data-flow 圖上用紅色標出)
- 熱點清單(每行:位置 / 問題類型 / 證據 / 影響規模 / 優化方向)
- (若可)效能 baseline 數字(p50 / p99 / QPS / 記憶體)

**必答問題**:
- 有沒有 N+1 query 嫌疑?(迴圈內 query DB)
- 有沒有同步阻塞 I/O?(call API 不 await / 讀檔 sync)
- 有沒有缺乏快取?(每次都重算 / 每次都查 DB)
- 有沒有大資料全載記憶體?(無分頁 / 無 streaming)
- 有沒有 hot key / 熱點 partition?

### 視角 8:錯誤處理鏈 (Error Handling Chain) [NEW v1]

**目的**:「一個 error 從拋出到被吞掉或上報,完整鏈路」

**產出**:
- 一張錯誤鏈圖(從 throw / reject / 異常 → catch / handler / log / 上報)
- 錯誤類型表(每行:錯誤類型 / 拋出位置 / 處理位置 / 上報目標 / 對使用者的影響)
- (重點)「被吞掉的錯誤」清單(throw 但沒人 catch = 風險)

**必答問題**:
- 哪些地方 try / catch 但沒做事(silent failure)?
- 哪些錯誤上報到 Sentry / 監控?
- 哪些錯誤回給使用者、哪些是 internal-only?
- retry / circuit breaker / fallback 的策略?

---

## 8 視角的相互關係

```
       ┌─────────────────────────────────────────────┐
       │  1.模組拓墣(靜態結構)                       │
       │     告訴你「有哪些塊」                       │
       └────────────────┬────────────────────────────┘
                        │ 給元件名
       ┌────────────────▼────────────────────────────┐
       │  2.對外介面(契約)                            │
       │     告訴你「怎麼跟它對話」                   │
       └────────────────┬────────────────────────────┘
                        │ 給入口
       ┌────────────────▼────────────────────────────┐
       │  3.資料流(動態路徑)                          │
       │     告訴你「一個請求走完會經過什麼」          │
       └────────────────┬────────────────────────────┘
                        │ 給狀態變化點
       ┌────────────────▼────────────────────────────┐
       │  4.狀態機(生命週期)                          │
       │     告訴你「過程中的狀態轉移」                │
       └────────────────┬────────────────────────────┘
                        │ 給資源與 service
       ┌────────────────▼────────────────────────────┐
       │  5.部署拓墣(執行環境)                        │
       │     告訴你「跑在哪、怎麼 scale」              │
       └────────────────┬────────────────────────────┘
                        │ 給所有節點
   ┌────────┬───────────┼───────────┬────────┐
   ▼        ▼           ▼           ▼        ▼
 6.安全    7.效能      8.錯誤     (上 5 視角的橫切檢查)
 (信任邊界) (熱點)     (異常路徑)
```

**寫作順序**:視角 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8(由靜態到動態,由結構到橫切)

---

## 證據等級標記(Ladder)

每個結論必附證據等級,**所有下游閱讀者都該認得**:

| 標記 | 意義 | 範例 |
|------|------|------|
| `[O:直接觀察]` | 看到原始碼 / 跑過 binary / 抓過 HTML / 截圖確認 | `[O:src/api/users.ts:42]` |
| `[I:推斷 80%+]` | 從多個觀察點交叉推斷、高信心 | `[I:在 v1.2 之前是這樣寫,從 git log + 測試推斷]` |
| `[I:推斷 50-80%]` | 部分觀察、邏輯推斷 | `[I:從 API 回應結構推斷 DB schema]` |
| `[?:黑盒:未分析]` | 沒分析過、純猜 | `[?:不知道為什麼這個 function 是 async]` |
| `[X:矛盾]` | 觀察到矛盾、待釐清 | `[X:文件說 sync、code 是 async]` |

**使用規則**:
- 視角 1-2(靜態結構):絕大多數 `[O]`,沒分析到的標 `[?]`
- 視角 3-4(動態行為):可能 `[I]`,必附推斷依據
- 視角 5(部署):可能 `[I]` 或 `[?]`,需 trace log / 訪問實際環境才能升 `[O]`
- 視角 6-8(橫切):可能 `[I]` 或 `[?]`,必附「為什麼我認為是這樣」

---

## Mermaid 圖的最小規範

所有圖必能在 `mmdc` 渲染,語法必對:

| 圖類型 | 用於哪個視角 | 最小需求 |
|--------|-------------|----------|
| `graph TD` / `flowchart TB` | 1 模組拓墣、5 部署拓墣、6 trust boundary | 節點命名用 `id[顯示文字]`、方向用 `-->` |
| `sequenceDiagram` | 2 對外介面、3 資料流(呼叫序列) | `participant` + `->>` + `-->>` |
| `stateDiagram-v2` | 4 狀態機 | `state` + `[*]` 起始結束 + `:` 轉移標籤 |
| `erDiagram` | 3 資料流(資料模型) | entity 與 relationship |

**節點命名規範**:
- module 用 `M[auth-service]`
- HTTP endpoint 用 `E[POST /api/users]`
- DB table 用 `T[(users)]`
- external party 用 `P[Stripe API]`
- 標熱點用 `H[這裡是熱點]:::hotspot`(定義 class)

---

## restore-checklist 的最小內容

**必含 5 段**:
1. **前置**(環境、工具、API key、第三方帳號)
2. **階段拆分**(每階段預估時數、產出物)
3. **每階段步驟**(有編號、可勾選)
4. **驗收標準**(跑得起來 / smoke test / 跟原系統差異)
5. **已知限制 / 風險**

**風格**:
- 步驟動詞開頭(建立 / 設定 / 跑 / 驗證)
- 有具體指令(`npm install xxx`、`psql -c "..."`)
- 預估時間要寫

---

## 失敗處理

| 失敗模式 | 處理 |
|---------|------|
| 輸入是 binary 但沒有 IDA / Ghidra | 退而用 `strings` / `objdump` / 動態 trace |
| 網站要登入 | 必先問使用者提供測試帳號或截圖 |
| 8 視角某個寫不出來(資料不足) | 寫「[?:資料不足,需 X 才能補]」、不要硬寫 |
| 下游要 Mermaid 圖渲染成 PNG | 用 `mmdc -i input.mmd -o output.png`(`beautiful-mermaid` skill 內有完整流程) |
| 來源程式碼太長 | 先用 `cloc` / 結構分析聚焦到 subsystem,逐個拆 |
| 螢幕截圖解析度不夠 | `vision-analysis` 會標出來,這時該問使用者要更高解析度 |

---

## 不要做的事

- ❌ 不要把 8 視角壓縮成 1 個總圖(下游會讀不懂)
- ❌ 不要用沒渲染的 Mermaid 文字當主報告(必渲染成 PNG/PDF)
- ❌ 不要 `[O]` 跟 `[I]` 混用(必明確標)
- ❌ 不要 restore-checklist 寫得比主報告還長(checklist 是 quick reference)
- ❌ 不要憑印象猜 binary 內部邏輯(必用工具)
- ❌ 不要忽略環境變數(那是部署拓墣的一部份)
- ❌ 不要在沒分析完整個子系統時就推斷「整個系統的狀態」(scope creep)

---

## 跟其他 skill 的關係

- **clawic `reverse-engineering`**(通用 TRACE 協議 + evidence ladder + interface map):本 skill 的方法論祖先。1-4 視角的內容本質就是 TRACE 的「Model」階段具體化。
- **clawic `interface-map.md`**:視角 2 的介面盤點章節,直接套用其模板。
- **clawic `evidence-ladder.md`**:本 skill 的證據等級標記是其簡化版(5 級縮到 5 級但更精準)。
- **`diagram-generator` / `beautiful-mermaid`**:本 skill 所有圖的渲染與美化都走它們。
- **`scrapling` / `agent-browser` / `browser` / `web_search`**:視角 2-3 抓網站時的工具來源。
- **`vision-analysis`**:輸入是截圖 / 錄影時的主力。
- **`software-development` / `code` / `code-reviewer`**:理解原始碼時的方法論支援。
- **`bash-defensive-patterns` / `python-anti-patterns`**:trace 與分析腳本的 defensive 規範。

---

## 自我審查(8 視角完成前必跑)

- [ ] 8 個視角章節都寫了?(缺一個 = 不交付)
- [ ] 每個視角都有一張 Mermaid 圖 + 一張表格?
- [ ] 所有結論都附 `[O]/[I]/[?]` 證據等級?
- [ ] restore-checklist 寫完了、5 段都齊?
- [ ] 主報告 reverse-arch.md 把 8 視角都串起來?
- [ ] 證據索引 + artifacts/ 都有?
- [ ] 沒把 8 視角壓縮成 1 個總圖?
- [ ] 沒忽略環境變數 / 部署設定?

完成以上 8 項 = 該次 reverse-arch 可交付下游。
