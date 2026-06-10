---
name: orchestrator-worker-architecture
description: |
  處理 LLM context 累積的「Orchestrator + Worker + summarizer」三層架構。
  **特徵**:主 session context 隔離(只讀摘要)、web-worker 平行抓、summarizer-worker 去重+摘要。
  **使用情境**:任何「需要抓 >5 個 URL 或 >50K chars 資料」的研究/分析任務(consumer-researcher 風格)。
  **觸發關鍵字**:「context 累積」、「抓資料爆掉」、「邊抓邊整」、「平行抓」、「LLM context」、「summarizer」、「_raw/」、「_summary.md」、「@專案 大型研究」
risk: safe
source: hermes-internal
date_added: "2026-06-10"
last_updated: "2026-06-10"
---

# Orchestrator + Worker + Summarizer 三層架構

> **目的**:解決單體 LLM agent「把所有 web 結果直接餵進 context」的 context 累積爆掉問題。
> 從 2026-06-10 `consumer-researcher` v2 架構重構中提煉。

## 為什麼需要這套架構

**問題**:LLM agent 跑 web 搜尋時,每個結果 1.6-30K chars 都直接餵進 conversation history。累積到 80-120K 時,LLM 進入 thinking loop 卡住、主動終止。

**症狀**(2026-06-10 真實案例):
- consumer-researcher 跑了 14 個 URL、137K chars,context 累積 108K → 5 分鐘卡住 → 終止
- 任務失敗,使用者對結果品質不信任

**解法**:把任務**拆分**給多個獨立 web-worker(每個 context 隔離),主 session 只做「決策 + 整合」,讀的是 summarizer 壓縮過的 5-10 KB 摘要。

## 三層架構

```
Layer 1: Orchestrator(consumer-researcher 主 session,context 30-50K)
  ├─ Step 1-2 釐清 + 規劃(5-10K context)
  ├─ Step 3 派遣 web-worker(每個 +5K,但觸發完就釋放)
  │   ├─ Worker 1: 抓 3 個直接標竿 → 寫 _raw/worker-1.md
  │   ├─ Worker 2: 抓 1 個跨領域典範 → 寫 _raw/worker-2.md
  │   └─ Worker 3-N: 抓消費者聲音 / Persona 素材
  ├─ Step 4 等所有 worker 完成(0 context)
  ├─ Step 5 派遣 summarizer-worker → 寫 _summary.md(5-10 KB)
  ├─ Step 6 讀 _summary.md(5-10K context)→ 做 MoSCoW + Persona
  └─ Step 7 整合寫最終報告
```

## 核心設計原則

### 1. Worker 必須 context 隔離

**做法**:用 `hermes chat -q "..." --cli`(不是 `-p <profile>`)啟動**獨立 hermes session**。
- 不繼承任何 persona / SOUL / skill 庫
- 每個 worker 的 LLM context 完全隔離(主 session 不會被污染)
- 完成後**只輸出 "DONE"**,不傳詳細結果給主 session

### 2. Worker 只整理事實、不做分析

- Worker 的 prompt 必須明確寫「**不要分析、不要總結、不要給建議**」
- Worker 只做:抓 → 整理成結構化 markdown → 寫檔
- 分析、洞察、決策是 Orchestrator 的工作

### 3. Summarizer 必讀 _plan.md(保留 Orchestrator 的決策意圖)

Orchestrator 派遣前要寫 `_plan.md`,包含:
- Worker 任務清單
- **使用者原意 Persona(若 default orchestrator 有預填)**(必填,2026-06-10 教訓)
- **必抓清單(若該專案有核心標竿)**(必填,2026-06-10 教訓)
- Persona 順序規則(使用者原意排前面、_raw/ 歸納排後面)

Summarizer 讀 _plan.md 知道要保留哪些資訊,從 _raw/ 擴展具體痛點。

### 4. Summarizer 嚴格大小控制(5-10 KB)

- 太大(> 15 KB):Orchestrator 讀完 context 飆高
- 太小(< 5 KB):丟失關鍵資訊
- 嚴格 5-10 KB,透過 prompt 內的「每段長度限制」控制

### 5. 主動監聽、平行派遣

- 用 `terminal(command="...", background=true, notify_on_complete=true)` 平行派遣 worker
- 用 `process(action='wait', session_id=...)` 監聽
- **不要**包成一個 shell script 一次跑(失敗 debug 困難、且會擋住互動)

## 標準工作流程

### Phase 1:Orchestrator 規劃(主 session,5-10K context)

1. **釐清問題邊界**(反問 3-5 個關鍵問題、若 default 已預填答案直接用)
2. **寫 _plan.md**:
   ```markdown
   # Worker 派遣計劃
   - Worker 1: <任務類型> — <具體 URL/範圍>
   - Worker 2: <任務類型> — <具體 URL/範圍>
   - summarizer: 讀 _plan.md + _raw/ → 寫 _summary.md

   # ★ 使用者原意 Persona(若 default 有預填)
   - Persona 1:[名字]([職業]) — 主流客群
   - Persona 2:[名字]([職業]) — 差異化客群
   - Persona 3:[名字]([職業]) — CSR 亮點

   # 必抓清單(若該專案有核心標竿)
   - SkillSwap.io、Reddit r/SkillSwap 等
   ```
3. **規劃 worker 數量**:3-5 個(太少沒省到、太多管理成本反吃)
4. **每個 worker 抓 3-5 個 URL**(避免單一 worker context 也爆)

### Phase 2:派遣 web-workers(主 session,每個觸發 +5K 釋放)

每個 worker 用獨立 script 啟動:
```bash
cat > /tmp/worker-1.sh << 'EOF'
#!/bin/bash
exec hermes chat -q "$(cat <<'INNER'
你是 web-worker #1。<任務類型>任務...

# 你的身份
- 獨立 hermes session,不繼�承任何 profile / persona / SOUL / skill
- 只整理事實,不做分析

# 來源 URL
1. <URL 1>
2. <URL 2>
3. <URL 3>

# 必抓清單(若 Orchestrator 在 _plan.md 內指定)
- <必抓標竿 1>
- <必抓標竿 2>

# 輸出
寫到 /home/<user>/.hermes/handoff/<slug>/_raw/worker-1.md
完成後輸出 "DONE"
INNER
)" --cli
EOF
chmod +x /tmp/worker-1.sh

# 背景啟動
terminal(command="/tmp/worker-1.sh", background=true, notify_on_complete=true)
```

### Phase 3:監聽 + 撈結果(主 session,0 context)

```bash
process(action='wait', session_id=worker-1, timeout=600)
process(action='wait', session_id=worker-2, timeout=600)

# 驗證 _raw/ 都有檔
ls -la ~/.hermes/handoff/<slug>/_raw/
```

### Phase 4:派遣 summarizer(主 session,+5K 觸發)

summarizer 必讀:
1. `_plan.md`(Orchestrator 指定的 Persona 跟必抓清單)
2. `_raw/` 內所有 worker 檔案

```bash
terminal(command="/tmp/summarizer.sh", background=true, notify_on_complete=true)
process(action='wait', session_id=summarizer, timeout=300)

wc -c ~/.hermes/handoff/<slug>/_summary.md
# 應該 5K-15K
```

### Phase 5:讀 _summary.md 整合(主 session,5-10K context)

讀 _summary.md(5-10 KB),做 MoSCoW、Persona 擴展、寫最終報告。

主 session context 預估總計:**30-50 KB**(vs 單體架構 108K 爆掉)。

## Prompt 範本

### Web-Worker Prompt 範本

```bash
hermes chat -q "$(cat <<'EOF'
你是 web-worker。<任務類型>任務:從 <N> 個 URL 抓取內容,整理成結構化 markdown。

# 你的身份
- 獨立 hermes session,**不隸屬任何 profile**
- 不繼承 persona / SOUL / skill
- 只整理事實,不做分析、總結、建議
- 完成後只輸出 "DONE"

# ★ 必抓清單(2026-06-10 教訓)★
- <標竿 1> — 必抓,<原因>
- <標竿 2> — 必抓,<原因>
如果任務指定的 URL 不包含必抓清單,主動用 web_search 補抓。

# 來源 URL
1. <URL 1>
2. <URL 2>

# 每個 URL 整理的欄位
- 基本資料
- 核心功能(已實作/部分實作/未實作)
- 使用者評價(最高頻 3 個好評 + 3 個負評)
- 來源 URL
- **標竿類型標記**:[直接]/[間接]/[跨領域]

# 輸出
寫到 /home/<user>/.hermes/handoff/<slug>/_raw/worker-<編號>.md
完成後只輸出 "DONE"
失敗時輸出 "FAILED: <原因>"
EOF
)" --cli
```

### Summarizer-Worker Prompt 範本

```bash
hermes chat -q "$(cat <<'EOF'
你是 summarizer-worker。任務:讀取 _plan.md + _raw/ 目錄所有檔案,做去重 + 分類 + 摘要。

# 你的身份
- 獨立 hermes session
- 不繼承 persona / SOUL / skill
- 只整理事實,不做分析

# 步驟
1. 讀取 /home/<user>/.hermes/handoff/<slug>/_plan.md
2. ls _raw/ 看檔案數
3. 逐個 read_file
4. 做去重 + 分類 + 摘要
5. 寫到 _summary.md

# 輸出目標
嚴格大小 5-10 KB(不可超過 15 KB)

# 摘要結構(必填)
- § 1. 標竿分析(直接/間接/跨領域三段必填 + 功能矩陣表)
- § 2. 消費者聲音(20-30 則、分高/中/低頻)
- § 3. Persona(使用者原意排前面、_raw/ 歸納排後面)
- § 4. 來源索引

# 硬性
- 標竿分析必填「直接/間接/跨領域」三段(2026-06-10 教訓)
- 功能矩陣表必填
- Persona 必須保留 _plan.md 指定的原意 Persona
- 完成輸出 "DONE: <大小> KB"
- 失敗輸出 "FAILED: <原因>"
EOF
)" --cli
```

## 何時使用

**使用情境**:
- 任何「需要抓 >5 個 URL 或 >50K chars 資料」的研究/分析任務
- 任務可拆分成 3-5 個獨立子任務
- 預期主 session context 會超過 60K
- 想要平行執行(節省時間)

**不適用**:
- 簡單查詢(1-2 個 URL)
- 純內部資料分析(不需要 web)
- 快速驗證想法(可用單體快速跑)

## 預期效益

| 指標 | 單體架構 | Orchestrator + Worker |
| --- | --- | --- |
| 主 session context | 80-120K(易爆) | 30-50K(可控) |
| 單一 worker context | N/A(全塞主) | 5-30K(隔離) |
| 總執行時間 | 10 分鐘(失敗) | 6-11 分鐘(成功) |
| 平行度 | 序列 | 3-5 worker 同時 |
| 失敗容錯 | 整個失敗 | 單一 worker 失敗可重試 |
| 可重用性 | 一次一任務 | worker 範本可重用 |

## 失敗處理

| 失敗模式 | 處理 |
| --- | --- |
| Worker 派遣失敗 | fallback:用 `tmux` 背景跑;或 `terminal(command=..., background=true)` |
| Worker 寫到 sandbox 隔離目錄 | prompt 內明確要求絕對路徑;Orchestrator 端用 `find` 撈 |
| Summarizer 摘要太大(> 15 KB) | 重跑 + prompt 加「精簡到 5 KB」 |
| Summarizer 摘要丟失關鍵資訊 | 重跑 + prompt 強調「保留具體數字、URL」 |
| Summarizer 卡住 | Orchestrator 自己讀 _raw/ 整理(放棄 summarizer,但 context 會飆高) |
| Worker 假裝成功(寫空檔、回 "完成" 但實際沒抓到) | Orchestrator 端用 `ls -la` 驗檔大小、檔案時間 |

## 跟 v1 單體架構的差異

| 維度 | v1 單體 | v2 Orchestrator |
| --- | --- | --- |
| LLM agent 數 | 1 個(主 session) | 1 主 + 3-5 worker + 1 summarizer |
| Context 累積 | 主 session 線性成長 | 隔離 + 中段壓縮 |
| Persona 來源 | 從使用者原意推測 | 保留使用者原意 + _raw/ 歸納 |
| 標竿涵蓋 | 依賴 prompt 給的 URL | 必抓清單 + 自動補抓 |
| 失敗恢復 | 整個失敗 | 單一 worker 可重試 |
| 複雜度 | 簡單 | 中等(要寫 3 種 prompt + 監聽) |

## 跟現有 skill 的關係

- `consumer-researcher` profile — 第一個採用此架構的常駐子代理
- `web-worker-template` — 此架構的 web-worker 範本 skill
- `summarizer-worker-template` — 此架構的 summarizer 範本 skill
- `user-collaboration-style` Rule 16 — 架構改完必做 v1 vs vN 內容比對

## 驗證 SOP

架構跑完後,必跑:
```bash
# 1. _raw/ 都有檔
ls -la ~/.hermes/handoff/<slug>/_raw/

# 2. _summary.md 大小合規
wc -c ~/.hermes/handoff/<slug>/_summary.md

# 3. 寫 v1 vs vN 比對報告(給使用者看)
# 用 USER.md 提到的「v1 vs v2 內容比對報告」格式
```

## 真實案例(2026-06-10)

- `~/.hermes/handoff/skill-language-exchange-platform/`
  - `_plan.md`(2.8 KB)— Orchestrator 規劃 + 使用者原意 Persona + 必抓清單
  - `_raw/worker-{1,2,3,4}.md`(74 KB 總計)
  - `_summary.md`(12.5 KB)— summarizer 整合
  - `_V1_VS_V2_COMPARISON.md`(14 KB)— v1 vs v2 原始版比對
  - `_V2_FIXED_COMPARISON.md`(9.7 KB)— v1 vs v2 原始 vs v2 修正版三方比對

- 完整架構重構報告:`~/shared-infra/CONSUMER_RESEARCHER_V2_ARCHITECTURE_REPORT.md`

## 注意事項

- 跨 profile 寫入會被軟防護擋,**加 `cross_profile=true`**(見 trial-and-error L2 條目)
- 背景 process 通知延遲約 1 小時,**用 `ls _raw/` 驗檔**,不依賴 `notify_on_complete`
- hermes curator 會自動把刪掉的 skill 補回來(若精瘦 skill 庫,需用 `hermes skills opt-out`)
- 前台 timeout 預設 60s,背景 task 用 `background=true` + `notify_on_complete=true`
