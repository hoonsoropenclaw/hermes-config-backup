# Consumer-Researcher v2 架構設計:Orchestrator + Worker

> **2026-06-10 設計** — 解決 v1 單體架構的 context 累積問題

---

## 1. 問題陳述(為什麼需要改)

### v1 單體架構的失敗案例(2026-06-10 技能/語言交換平台)

```
單體 LLM agent(consumer-researcher)
  ↓ 跑 Step 1-6
  ├─ Step 1 釐清邊界
  ├─ Step 2 標竿盤點
  │  ├─ web_search #1 → +1.6K chars → context 30K
  │  ├─ web_search #2 → +4.6K chars → context 35K
  │  ├─ web_extract #1 → +30K chars → context 65K
  │  ├─ web_extract #2 → +27K chars → context 92K
  │  └─ ... 14 個 URL 後,context 108K → **卡住 5 分鐘**
  ├─ Step 3 消費者聲音
  └─ Step 4-6 → 永遠到不了
```

**核心問題**:每個 web 結果直接餵進 LLM context,沒有「中間摘要」機制。14 個 URL 後 context 108K,LLM 進入 thinking loop 無回應。

---

## 2. v2 架構:Orchestrator + Worker

### 2.1 三層分工

```
┌────────────────────────────────────────────────────┐
│ Layer 1: Orchestrator(consumer-researcher 主 session)│
│  - LLM context 維持 20-30K(只讀摘要)              │
│  - 決策:派哪些 worker、怎麼整合                   │
│  - 接收 worker 結果,做 MoSCoW + Persona + 寫報告 │
└──┬─────────────┬─────────────┬─────────────────────┘
   │             │             │
   ↓             ↓             ↓
┌─────────┐  ┌─────────┐  ┌─────────┐
│Layer 2A:│  │Layer 2A:│  │Layer 2B:│
│web-     │  │web-     │  │summary- │
│worker-1 │  │worker-2 │  │worker   │
│(背景跑) │  │(背景跑) │  │(背景跑) │
│         │  │         │  │         │
│抓 3-5 個│  │抓 3-5 個│  │讀 _raw/│
│URL      │  │URL      │  │去重摘要│
│         │  │         │  │         │
│寫到     │  │寫到     │  │寫到     │
│_raw/1.md│  │_raw/2.md│  │_summary│
└─────────┘  └─────────┘  └─────────┘
   ↑             ↑             ↑
   各自獨立 LLM context(隔離 50K)
```

### 2.2 詳細角色定義

#### Layer 1: Orchestrator(consumer-researcher)

**身份**:仍然是 consumer-researcher profile,但內部行為從「一個人做完」變成「指揮官」

**新 SOP(7 步)**:
1. **Step 1 釐清邊界**(跟 v1 一樣)
2. **Step 2 規劃 worker 任務**:
   - 把「要抓的目標」拆成 N 個獨立任務(例:標竿分析 N1 + 消費者聲音 N2 + 跨領域典範 N3)
   - 寫任務清單到 `~/.hermes/handoff/<slug>/_plan.md`
3. **Step 3 派遣 N 個 web-worker**(平行跑):
   - 每個 worker 獨立 hermes session、獨立 LLM context(50K 上限,但不互相累積)
   - 每個 worker 完成後寫 `~/.hermes/handoff/<slug>/_raw/<n>.md`(只寫檔,不回傳給主 session)
4. **Step 4 等所有 worker 完成**:
   - 用 `process(action='poll')` 監聽 background workers
   - 撈每個 worker 的 _raw/ 檔案
5. **Step 5 派遣 summarizer-worker**:
   - 讀所有 _raw/*.md
   - 去重(同來源重複、相似內容)
   - 分類(標竿 / 消費者聲音 / Persona 素材)
   - 摘要(目標:5-10 KB 的結構化 markdown)
   - 寫到 `~/.hermes/handoff/<slug>/_summary.md`
6. **Step 6 讀 summary.md**(已壓縮到 5-10 KB):
   - 做 MoSCoW(從 28 個功能需求 → Must/Should/Could/Won't)
   - 寫 3 大 Persona + User Story
   - **這個階段 context 只累積 summary 內容,約 20-30K**
7. **Step 7 整合寫最終報告**:`~/.hermes/handoff/<slug>/consumer-needs-research.md`

**context 預估**:
- Step 1-2: 5-10K(只有使用者 prompt + 計劃)
- Step 3 派遣:每個 worker 觸發 +5K(累積 10-30K)
- Step 4 撈:每個 _raw/ 讀一次 +2K(累積 30-40K)
- Step 5 派遣 summarizer: +5K
- Step 6 讀 summary: 5-10K
- Step 7 寫報告: 10-15K(LLM 寫的內容)
- **總計**:30-50K(遠低於 v1 的 108K)

#### Layer 2A: web-worker(新類型,獨立 hermes session)

**身份**:**獨立的 hermes chat session**(不隸屬任何 profile),用極簡 prompt 跑單一任務

**特性**:
- **單一 LLM session**,context 隔離(最多 50K,但**不互相累積**)
- **極簡 prompt**:只給「任務說明 + 預期輸出格式」
- **不用 persona.md / SOUL.md**(不需要人格、只要工具)
- **寫到 _raw/ 目錄就結束**

**範例 prompt**:
```bash
hermes chat -q "$(cat <<'EOF'
你是 web-worker #1。任務:抓 3 個技能交換平台的功能評論。

# 任務
從以下 3 個 URL 抓取內容,每個 URL 整理出:
- 平台名稱
- 核心功能(已實作 / 部分實作 / 未實作)
- 使用者最高頻 3 個好評
- 使用者最高頻 3 個負評
- 來源 URL

# URL
1. https://actualfluency.com/tandem
2. https://www.fluentu.com/blog/reviews/hellotalk
3. https://www.518.com.tw/article/2253

# 輸出格式
寫到 ~/.hermes/handoff/skill-language-exchange-platform/_raw/worker-1.md
格式:每個 URL 一個 H2 標題,結構如上。
不要做總結、不要分析,只整理事實。

# 重要
- 只用 web_search / web_extract 工具
- 抓到內容後直接 write_file,不要再分析
- 完成後輸出 "DONE" 即可
EOF
)" --cli
```

**context 預估**:5-30K(每個 worker 獨立)

#### Layer 2B: summarizer-worker(獨立 hermes session)

**身份**:另一個獨立 hermes chat session

**任務**:
- 讀 `_raw/*.md`(所有 worker 的輸出)
- 做去重(相似內容合併)
- 分類(每段屬於「標竿」「消費者聲音」「Persona 素材」)
- 摘要(目標:5-10 KB 結構化 markdown)
- 寫到 `_summary.md`

**範例 prompt**:
```bash
hermes chat -q "$(cat <<EOF
你是 summarizer-worker。任務:讀取所有 _raw/ 檔案,做去重 + 分類 + 摘要。

# 輸入
讀取以下目錄所有 .md 檔:
$(ls ~/.hermes/handoff/skill-language-exchange-platform/_raw/)

# 輸出格式
寫到 ~/.hermes/handoff/skill-language-exchange-platform/_summary.md
結構:
## 1. 標竿分析摘要(目標 3-5 個標竿 × 5 個欄位)
## 2. 消費者聲音摘要(目標 20-30 則,分高/中/低頻)
## 3. Persona 素材摘要(3 個 persona,每個含人口統計+痛點+替代方案)
## 4. 來源索引(所有 URL + 摘要對應編號)

# 重要
- 同樣的內容如果多個 worker 都抓到,只留最詳細的
- 不要新增資訊,只整理 + 摘要
- 摘要後的 _summary.md 應該在 5-10 KB 之間
- 完成後輸出 "DONE"
EOF
)" --cli
```

**context 預估**:20-50K(讀所有 _raw/ 累積,但只跑一次)

---

## 3. 跟 v1 的對比

| 維度 | v1(單體) | v2(Orchestrator + Worker) |
| --- | --- | --- |
| **context 累積** | 線性成長,108K 爆 | 隔離 + 摘要,主 session 30-50K |
| **執行時間** | 序列(慢) | 平行 web-worker(快 2-3 倍) |
| **失敗影響** | 卡住就整個失敗 | 單一 worker 失敗不影響整體 |
| **可重用性** | 一次只能跑一個任務 | worker 可重用於多個任務 |
| **複雜度** | 簡單(一個 prompt) | 中等(要寫 3 種 prompt + 監聽) |
| **可調適性** | 改 SOP 要改 prompt | 改 SOP 只改 Orchestrator,worker 可重用 |
| **debug 難度** | 卡住不知道卡哪 | 知道是哪個 worker 失敗 |

---

## 4. 工具 / Skill 需求

### 4.1 新 skill 1:`web-worker-template`

**路徑**:`~/.hermes/profiles/consumer-researcher/skills/web-worker-template/`

**功能**:
- 提供 web-worker 的 prompt 範本(可變數化:URL 數、輸出路徑、任務類型)
- 包含「不要分析,只整理事實」的硬性 prompt
- 包含失敗重試邏輯(若 worker 失敗,可重新派遣)

### 4.2 新 skill 2:`summarizer-worker-template`

**路徑**:`~/.hermes/profiles/consumer-researcher/skills/summarizer-worker-template/`

**功能**:
- 提供 summarizer 的 prompt 範本
- 包含「去重 + 分類 + 摘要」SOP
- 包含「目標 5-10 KB」的大小控制

### 4.3 改寫:`consumer-researcher/persona.md`

- 從「6 步單體 SOP」改為「7 步 Orchestrator SOP」
- 加入「派遣 worker」的決策邏輯
- 加入「監聽 worker 結果」的 process 操作

### 4.4 改寫:`consumer-researcher/SOUL.md`

- 語氣從「田野調查員」改為「**研究計畫主持人**」(指揮 worker,不自己跑)

---

## 5. 實作順序

1. **Step 1**:備份 v1(✅ 已完成,2026-06-10 11:07)
2. **Step 2**:設計 v2 架構(✅ 本文檔)
3. **Step 3**:建 `web-worker-template` skill
4. **Step 4**:建 `summarizer-worker-template` skill
5. **Step 5**:改寫 `consumer-researcher/persona.md` 為 Orchestrator SOP
6. **Step 6**:改寫 `consumer-researcher/SOUL.md` 為「研究計畫主持人」語氣
7. **Step 7**:**用 skill-language-exchange-platform 重跑測試**(驗證 v2 context 控制有效)
8. **Step 8**:寫架構重構報告

---

## 6. 風險與緩解

| 風險 | 緩解 |
| --- | --- |
| **worker 派遣失敗**(hermes delegate_task 不支援背景爬) | fallback 用 `terminal(background=true)` 跑 worker script |
| **worker 結果寫到 sandbox 隔離目錄** | 在 prompt 內明確要求「用絕對路徑 `/home/<user>/.hermes/handoff/...`」+ Orchestrator 端用 `find` 二次驗證 |
| **summarizer 摘要太短、丟失關鍵資訊** | prompt 內要求「保留所有具體數字、URL、人名」+ 「寧可冗長不要遺漏」 |
| **Orchestrator context 還是會累積** | 限制每個 worker 觸發指令只 +5K、_raw/ 讀只 +2K,加監控 |
| **平行 worker 互相搶資源** | 限制同時最多 3 個 worker 平行(不超過 4 核 CPU 瓶頸) |

---

## 7. 不在 v2 範圍

- ❌ 分散式 worker pool(需要 k8s,太重)
- ❌ 增量 checkpoint(可在 v3 再加)
- ❌ 自動重試 worker 失敗(本次手動重試就夠)
- ❌ worker 結果的版本控制(本次只用 _raw/ + _summary.md 兩層)
