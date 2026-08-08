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

## Umbrella relationship (2026-08 curator pass)

This is the context-isolation subsection of the agent orchestration class. Its durable contract is orchestrator → isolated workers → summarizer → verified handoff; individual research sessions belong in references, not new skills.



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

## ⚠️ Hermes Orchestration Decision Tree（2026-06-17 新增）

> **背景**: 赫米斯有 `delegate_task`、`hermes chat -q`、`profiles`、`cron`、`kanban` 等多套協作原語，但缺乏「什麼情境用哪個」的系統化判斷。這個 decision tree 填補這個缺口。

### Step 0：我需要多個 agent 嗎？

| 判斷 | 結論 |
|------|------|
| 任務可以在一個 context 內完成 | **不用多代理，直接做** |
| 任務需要同時做 N 件不相關的事 | 進 Step 1 |
| 只有「順序依賴」的子任務（如 A→B→C）| 進 Step 1 |

### Step 1：選 Topology（orchestration pattern）

| 情境 | 拓撲 | 赫米斯實作方式 |
|------|------|---------------|
| 需要一個 orchestrator 集中控制所有 sub-agent | **Hub-and-Spoke** | `delegate_task(tasks=[...])` batch 模式 |
| 任務是「研究→整理→結論」流水線 | **Hierarchical** | `orchestrator-worker-architecture` 三層模式 |
| 2 個 agent 來回對話（如「評審 agent」對「實作 agent」給回饋）| **Sequential** | `hermes chat -q` × 2 次觸發 |
| N 個 agent 完全對等、直接溝通 | **Mesh/P2P** | **赫米斯不原生支持**——需用 shared file state 模擬 |

### Step 2：選 Context 隔離層級

| 隔離需求 | 赫米斯實作方式 | 代價 |
|---------|---------------|------|
| **高隔離**（skills/persona/SOUL 統統不要） | `hermes chat -q "..." --cli` 啟動獨立 session | 每個 session 重新 init（~5-10s overhead）|
| **中隔離**（skills 可繼承，但 context 不累積）| `delegate_task`（leaf role） | Session 共享，context 會累積 |
| **低隔離**（完整 context 延續）| 主 session 直接做 | Context 爆掉風險（>80-120K）|

### Step 3：選 State 共享機制

| State 需求 | 赫米斯機制 | 備註 |
|-----------|-----------|------|
| 簡單（只傳結論） | `delegate_task` return value | 限制：return value 大小有限 |
| 中等（檔案交換）| `_plan.md` + `_raw/` + `_summary.md` | Orchestrator-worker-architecture 標準機制 |
| 複雜（結構化共享狀態、跨時間）| `memorial palace`（mcp_mempalace）| 適合長期任務、狀態持久化 |

### Step 4：選 Failure Recovery

| 失敗容忍度 | 赫米斯機制 |
|-----------|-----------|
| **高**（自動化 24/7，失敗自動修）| `hermes cron` watchdog + `anti-panic-protocol` |
| **中**（需要知道失敗了）| `notify_on_complete=true` + 驗證命令（`wc -c`、`ls -la`）|
| **低**（失敗就全部停）| 同步 `delegate_task`，失敗就終止整條鏈 |

### Step 5：Special Cases

| 情境 | 決策 | 原因 |
|------|------|------|
| Cron 驅動的長期自主工作流 | **用 `hermes cron` + `hermes chat -q` + `kanban`**，不用 `delegate_task` | cron 本身就是 orchestrator，繞過 session 初始化 overhead |
| 同一個 long-running 任務內多 agent 共享狀態 | **用 shared file**（`_state.json`），不用 `delegate_task` return value | return value 受 context 限制 |
| 任務只有 2 個 sub-task 且依賴簡單 | **直接 `hermes chat -q` × 2**，不繞 `delegate_task` | 節省 session 初始化 overhead |

### If→Then 快速查詢表

| If 條件 | Then 動作 |
|---------|---------|
| 需要 sub-agent 平行處理多個獨立子任務 | `delegate_task(tasks=[...])` batch 模式 |
| 任務是「研究→整理→結論」流水線 | `orchestrator-worker-architecture` |
| 只有 2 個 agent 來回對話 | `hermes chat -q` × 2 |
| Cron 驅動的長期自主工作流 | `hermes cron` + `hermes chat -q` + `kanban` |
| 需要 shared state 的複雜流程 | memorial palace，不靠 delegate_task return |
| 懷疑自己在用「直覺」而不是「系統化判斷」| 停下來對照本決策樹 Step 0-5 |

### 赫爾米斯特有優勢（相較於 LangGraph/CrewAI/AutoGen）

| 維度 | 赫爾米斯 | 其他框架 |
|------|---------|---------|
| 時間軸自主化 | `hermes cron` 原生 support | 需自己實作 scheduler |
| 完全 context 隔離 | `profiles` 隔離 process | 同 process thread 隔離 |
| 視覺化任務板 | `kanban` 原生 support | 需額外整合 |
| 代價 | process/transport 層隔離，代價較高 | 同 process，代價低（~15x token 節省）|

> **研究印證**: Anthropic 內部研究發現，multi-agent 系統 token 消耗是 chat 的 ~15x（主要來自重複的 context）。赫爾米斯的 process 隔離額外代價在於 session init overhead，而非 LLM context 本身。

## 何時使用

**使用情境**:
- 任何「需要抓 >5 個 URL 或 >50K chars 資料」的研究/分析任務
- 任務可拆分成 3-5 個獨立子任務
- 預期主 session context 會超過 60K
- 想要平行執行(節省時間)
- **需要多代理但拿不定用哪個原語**——先走上方 Decision Tree

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

## ⚠️ 結果彙整失敗模式（Fan-Out/Fan-In 特有）

> **2026-06-14 識別缺口**：平行派遣完成後，Orchestrator 怎麼蒐集、怎麼合併衝突、怎麼檢測部分失敗——這些沒有 SOP，是 Fan-Out/Fan-In 的核心失效點。

| 失敗模式 | 發生情境 | 處理 |
| --- | --- | --- |
| **Aggregation hallucination** | LLM summarizer 把衝突共識當成一致意見（如 A agent 說買、B agent 說賣，summarizer 卻說「一致同意觀望」） | 需要明確衝突 resolution 步驟（不是「summarize」，是「列出所有觀點 + 標記衝突」） |
| **Race condition on shared state** | N 個 worker 同時寫同一檔 | 每個 worker 寫獨立檔（如 `_raw/worker-1.md`），不做任何共享寫 |
| **Partial failure 無人察覺** | 3 個 worker 完成、1 個失敗，但 Orchestrator 沒驗證就假設全部成功 | 每次蒐集結果前先 `ls -la _raw/` 確認所有 expected 檔都有 + 檔案大小 > 0 |
| **結果優先順序不明** | 多個 worker 給出不同答案，誰的結論優先？ | 派遣前在 _plan.md 明確指定「結論採用策略」（如：最多票數 / 最新時間戳 / 指定某個 worker 為主） |
| **Worker 假裝成功** | 回 "DONE" 但實際沒抓到、寫空檔或 1 byte 檔 | Orchestrator 用 `wc -c` 驗每檔大小、用 `grep` 驗實質內容存在 |

**If→Then 規則**：
- **If** 任務是「同一問題多視角分析」（非事實類）**Then** 結果彙整不走 LLM synthesis，改走「列點 + 衝突標記 + Orchestrator 裁決」
- **If** 任務是「各自獨立事實蒐集」**Then** 結果彙整可以 LLM synthesis，但必須先驗每檔非空
- **If** `delegate_task(tasks=[...])` 超過 5 個 **Then** 拆成兩批（每批 2-3 個）+ 中間彙整，避免 N(N-1)/2 衝突增長
- **If** Orchestrator 有高連接度 hub 節點 **Then** 在每階段之間加 phase gates，獨立驗證每個 worker 輸出（防範 cascade failure：hub injection 可在 LangGraph 造成 100% 系統失敗）
- **If** 任務在最外層需要「自由協作」**Then** 重新設計為 supervisor 模式：協作封裝為受控 subroutine，2026 年生產驗證確認 free mesh 在外層是 anti-pattern

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

- **`references/multi-agent-5-patterns-cascade-20260730.md`** — **2026 5 patterns (fan-out/pipeline/supervisor/debate/swarm) + 'From Spark to Fire' cascade failure research**: hub injection → 100% LangGraph / 100% vs 15.9% CrewAI system failure; free mesh survives only as controlled subroutine inside supervisor (not outer architecture); phase gate + hidden selector + final arbiter as defenses; framework comparison table (2026-07-30 新增）
- **`references/multi-agent-cascade-defense-20260730.md`** — **Cascade failure defense implementation patterns** (Phase Gate + Hub Verifier Gating + Source Provenance): arXiv 2603.04474v2 governance layer; Microsoft `langgraph-trust` adapter (`pip install langgraph-trust`); `should_continue` conditional edge pattern; `interrupt()` for human-in-the-loop on high-risk actions; hub vs leaf injection Impact Factor table (LangGraph 10.31×, CrewAI 6.29×); If→Then implementation rules (2026-07-30 新增）

## 相關檔案

- `references/fan-out-fan-in-aggregation.md` — Fan-Out/Fan-In 結果彙整研究（失敗模式 + 專家建議）
- `references/delegate-task-failure-modes.md` — **CAMEL Inception Prompting：4 種 sub-agent delegation 失敗模式（Role-Flipping / Instruction Echoing / Flake Replies / Infinite Loops）+ If→Then 修復規則（2026-06-16 新增）**
- **`references/parallel-architecture-v1.md`** — **舊版平行架構 SOP（2026-06-10 第一版歸納）**。當時用 7 步 + 三層圖描述，主張「用 `hermes chat -q ... --cli` 而非 `delegate_task`」。**本 SKILL.md（v2+）已涵蓋並超越該版的內容**，這個 reference 留作歷史軌跡 + 早期決策依據（`notify_on_complete` 不可靠、必抓清單設計、_plan.md Persona 保留等核心概念最早在這版定型）。
- **`../../../trial-and-error/references/sops/fan-in-aggregation-sop.md`** — **Step-by-step Fan-In 彙整 SOP：Strategy A/B/C 決策樹、Partial Failure 處理（K/N 失敗率閾值）、驗證清單（wc -c + grep 衝突標記）、衝突預防原則（_plan.md 必填結論採用策略 + prompts 要求 confidence 標記）（2026-06-14 新增）**
- 完整架構重構報告:`~/shared-infra/CONSUMER_RESEARCHER_V2_ARCHITECTURE_REPORT.md`

## ⚠️ Phase 6：整合後端到端驗證（2026-06-16 新增）

> **Gap**: Phase 5 整合完成後，**若任務是工程實作**（程式碼產生/架構實作），必須跑實際建置驗證。不可只靠「每個 worker 報告成功 + summarizer 彙整完成」就視為完整交付。
>
> **根因（2026-06-12 Todo App 案例）**: engineering-lead 同時派了 Ticket 1（資料層）、Ticket 2（API 層）、Ticket 3（UI 層）給 3 個 sub-agent，每個都回報「完成」。但整合後是否可建置、模組是否相互兼容——**從未驗證**。各自正確 ≠ 組合正確，是 Fan-Out/Fan-In 的經典失效模式。
>
> **VMAO 框架驗證**: arXiv 2603.11445 的 Verified Multi-Agent Orchestration 指出，orchestration-level verification（發生在 synthesis 後）比無驗證 baseline 提升 +35% 完整性（3.1→4.2，1-5 scale）。

### 何時觸發

**If** 任務同時滿足以下兩個條件，**Then** 必須執行 Phase 6：
1. 用了 `delegate_task(tasks=[...])` 或 `terminal(background=true)` 平行派遣 2+ workers
2. 任務產出是**可執行的程式碼/系統**（非純研究報告或分析文件）

### Phase 6 步驟

**Step 1：識別專案類型和驗證命令**

```
Python 專案（含 test/）      → pytest 或 python -m py_compile
Next.js / Node 專案          → npm run build
Go 專案                      → go build ./...
Rust 專案                    → cargo build
純 Shell 腳本               → bash -n <script>（語法檢查）
```

**Step 2：執行驗證**

```bash
# 範例：Next.js 多層實作
cd /home/hoonsoropenclaw/reverse-engineering/todo-app/round-3b-parallel-m3/todo-app
npm run build 2>&1 | tail -20
echo "Exit code: $?"

# 範例：Python 多層實作
cd /path/to/project
python -m py_compile src/*.py && pytest tests/ -v --tb=short
echo "Exit code: $?"
```

**Step 3：解讀結果**

| 驗證結果 | 代表意義 | 處理 |
| --- | --- | --- |
| Exit code 0 + 無 warning | ✅ 整合成功 | 交付完成 |
| Exit code ≠ 0 | ⚠️ 整合失敗（介面相沖/依賴缺失） | → Step 4 Replan |
| 編譯 warning（non-fatal） | ⚠️ 可運行但有技術債 | 記錄但不 block |
| Timeout | ⚠️ 可能有無限迴圈或 deadlock | → Step 4 Replan |

**Step 4：若失敗 → Replan**

```bash
# 保留失敗 log（供日後審查）
cp /tmp/build.log ~/.hermes/handoff/<slug>/_build_fail_<timestamp>.log

# 診斷常見整合失敗：
# 1. 介面不一致（export/import  mismatch）
grep -r "export\|import" src/ --include="*.ts" --include="*.py" | sort | uniq -c | sort -rn | head -20

# 2. 依賴缺失（module not found）
grep -r "import\|require" src/ | grep -v node_modules | sed 's/.*from //' | sed 's/.*require //' | sort -u > /tmp/deps.txt
pip list 2>/dev/null | grep -f /tmp/deps.txt || npm list 2>/dev/null | grep -f /tmp/deps.txt || echo "deps check N/A"

# 3. 類型衝突（TypeScript / mypy）
npx tsc --noEmit 2>&1 | head -30 || python -m mypy src/ 2>&1 | head -30
```

### If→Then 規則

- **If** 任務是「工程實作類」（有實際程式碼產出）**Then** Phase 6 是**必選**，不是可選
- **If** 任務是「純研究/分析」（無可運行產出）**Then** Phase 6 跳過，只做 Phase 5 品質審查
- **If** 驗證失敗（exit code ≠ 0）**Then** 保留失敗 log 並在回報中明確標注「整合失敗，待手動介入」，不要假装成功
- **If** 發現同一類整合失敗（如同樣的介面不相容）出現 2+ 次 **Then** 記錄到 `trial-and-error/hermes-internal.md`，當作系統性問題而非單次意外

### Phase 6 vs fan-in-aggregation-sop.md 的差異

| 維度 | fan-in-aggregation-sop | Phase 6（新增） |
| --- | --- | --- |
| 驗證時機 | 彙整前（worker 檔案級） | 彙整後（系統級） |
| 驗證目標 | 檔案存在 + 非空 + 無衝突 | **實際可運行/可建置** |
| 適用任務 | 所有 fan-out 任務 | **僅工程實作類** |
| 失敗影響 | 可能重新 synthesis | 需要 **Replan** |

## 驗證 SOP

架構跑完後,必跑:
```bash
# 1. _raw/ 都有檔
ls -la ~/.hermes/handoff/<slug>/_raw/

# 2. _summary.md 大小合規
wc -c ~/.hermes/handoff/<slug>/_summary.md

# 3. 沒有偽裝衝突（grep 衝突標記）
grep -i "conflict\|CONFLICT\|分歧\|不一致" ~/.hermes/handoff/<slug>/_summary.md || echo "⚠️ no conflict markers — possible hallucination"

# 4. 每個 worker 都有對應內容（來源索引對照）
# 若有 worker 被完全忽略，grep 找不到該 worker 結論

# 5. 寫 v1 vs vN 比對報告(給使用者看)
# 用 USER.md 提到的「v1 vs v2 內容比對報告」格式
```

> **完整 Fan-In 彙整驗證程序**：見 `../../../trial-and-error/references/sops/fan-in-aggregation-sop.md` 的「驗證清單」章節（含 Strategy A/B/C 各自適用的驗證項目）

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
