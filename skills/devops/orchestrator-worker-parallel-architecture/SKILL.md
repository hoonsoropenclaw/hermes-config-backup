---
name: orchestrator-worker-parallel-architecture
description: "Orchestrator + N 個 worker 平行架構的 class-level SOP — 主 session 不跑重型任務、改派 hermes chat -q ... --cli 獨立 hermes session(context 完全隔離)+ summarizer 整合結果。**2026-06-10 consumer-researcher v2 架構實戰驗證**:v1 跑 10 分鐘卡 108K context 失敗、v2 跑 6 分鐘成功。觸發:用戶說「v2 架構」「平行架構」「Orchestrator」「summarizer」「不要在自己 context 跑 web 抓取」「context 爆炸」「子代理 context 隔離」。"
version: 1.0.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [orchestration, parallel, subagent, context-isolation, hermes-chat-cli, web-worker, summarizer]
    triggers: [v2架構, Orchestrator, parallel, parallel-worker, context爆, context隔離, subagent, web抓取]
---

# Orchestrator + Worker 平行架構(class-level)

> **2026-06-10 consumer-researcher v2 架構驗證**。適用於任何「主 session context 不能爆、要跑大量 web 抓取 / 平行任務」的場景。

## 為何需要這個架構

**症狀**:單體 agent(在主 session 內)連續跑 N 個 web search → context 累積到 100K+ → 終止失敗。

**根因**:LLM context window 有上限、且 context 累積會讓「早期 prompt」被稀釋、推理品質下降。

**解法**:把「重型任務」外包到獨立 hermes session——每個 session 有自己的 context window,跑完只回傳結果。

## 三層架構

```
┌────────────────────────────────────────────┐
│ Orchestrator(default profile,主 session)  │
│                                            │
│ 1. 寫 _plan.md(任務 + 必抓清單 + Persona) │
│ 2. 派 N 個 worker 平行跑                  │
│ 3. 收 worker 結果(_raw/)                  │
│ 4. 派 summarizer 整合                      │
│ 5. 撈最終摘要(_summary.md)                 │
│ 6. 交給下游(例 product-planner)            │
└────────────────────────────────────────────┘
         ↓          ↓          ↓
    ┌────────┐ ┌────────┐ ┌────────┐
    │ worker │ │ worker │ │ worker │  ← hermes chat -q ... --cli
    │   1    │ │   2    │ │   3    │  ← 每個獨立 session、context 隔離
    └────────┘ └────────┘ └────────┘
              ↓
    ┌────────────────┐
    │   summarizer   │  ← 整合 + 去重 + 分類 + 摘要
    └────────────────┘
```

## SOP(7 步)

### Step 1:Orchestrator 寫 _plan.md

**為何必要**:sub-agent 是無狀態的,**啟動時看不到「使用者之前提的偏好」**。必抓清單 + Persona 必須在 _plan.md 內預填。

**最小 _plan.md 結構**:
```markdown
# 任務:<slug>

## 使用者原意(必讀,sub-agent 不要重新推導)
- Persona 1:<小美/業務>...
- Persona 2:<佐藤/工程師>...
- Persona 3:<陳媽媽/退休族>...

## 必抓清單(8-15 個具體目標/網站/品牌)
- SkillSwap.io(直接標竿)
- Tandem(直接標竿)
- ...

## 必避免
- 不要把「跨國使用者」「退休族」當 Persona 自動推導
- 不要漏 SkillSwap.io(已驗證 v1 漏)
```

### Step 2:派 N 個 worker 平行跑

**用 `hermes chat -q` 而非 `delegate_task`**:
```bash
# 給 worker 1
~/.local/bin/consumer-researcher chat -q "
你是 consumer-researcher web-worker。
任務:抓 SkillSwap.io、Tandem 功能盤點。
讀 _plan.md:$(cat /path/to/_plan.md)

輸出寫到 _raw/worker-1.md,跑完 exit 0。
" --cli
```

**為何用 `hermes chat` 而非 `delegate_task`**:
- `delegate_task` 是 foreground、會把結果回傳到主 session context
- `hermes chat -q ... --cli` 是獨立 hermes process、context 完全隔離
- 主 session 只看到 exit code 跟輸出檔

### Step 3:收 worker 結果

**用 `ls` 等背景 process 結束,不用 `notify_on_complete`**:

notify_on_complete 延遲 10-14 分鐘是常態,不要當 polling 機制。

**主動監聽**:
```bash
# 每 30 秒看一次
while [ ! -f _raw/worker-1.md ] || [ ! -f _raw/worker-2.md ] || [ ! -f _raw/worker-3.md ]; do
  sleep 30
done
# 或 timeout 10 分鐘放棄
```

### Step 4:派 summarizer 整合

```bash
~/.local/bin/consumer-researcher chat -q "
你是 summarizer-worker。
讀 _raw/worker-{1,2,3,4}.md 跟 _plan.md。
整合 → 5 KB _summary.md:
- 8 個標竿(直接 + 間接 + 跨領域)
- 25 個痛點
- 5 個 Persona(包含 _plan.md 的 3 個 + 歸納 2 個)
- 必抓清單全覆蓋
" --cli
```

**為何要讀 _plan.md**:**保留使用者原意 Persona**——sub-agent 不會自己想到、必從 _plan 讀。

### Step 5:撈最終摘要

summarizer 跑完 → 主 session `cat _summary.md` 看結果。

### Step 6-7:交給下游 + 報告

- 寫到 `~/.hermes/handoff/<slug>/<這段產出>.md`
- 派給下段代理(product-planner 等)
- 報告給使用者

## 跟單體架構的差異

| 項目 | 單體(失敗) | v2 平行(成功) |
|---|---|---|
| **主 session context** | 108K 卡住 | 0(完全隔離) |
| **總耗時** | 10+ 分鐘(失敗) | 6 分鐘 |
| **壓縮率**(raw → summary) | N/A | 79%(46 KB → 9.8 KB) |
| **品質** | 漏 SkillSwap.io、Persona 偏離 | 涵蓋 8 標竿、5 Persona |

## 必抓清單設計

**If** 寫 _plan.md 必抓清單段
**Then** 列出 8-15 個具體目標(品牌名 / 網站 / 概念)
**Then 不要**寫「去抓市面上的同類產品」這種模糊指令
**Then 列出**「必避免」清單(sub-agent 常犯的錯)

**範例**:
```markdown
## 必抓清單(從使用者訊息 + v1 驗證補充)
- SkillSwap.io(直接標竿、v1 漏過)
- Tandem(直接標竿)
- HelloTalk(直接標竿)
- ConversationExchange(直接標竿)
- 學生論壇 Reddit r/languagelearning(間接標竿)
- 多鄰國社群(間接標竿)
- 語言學習 app 評論網站(間接標竿)
- 跨領域:Airbnb 雙向評價機制(設計概念借用)
- 跨領域:Tinder 配對演算法(設計概念借用)
- 跨領域:LinkedIn 技能 endorsement(設計概念借用)

## 必避免
- 不要把「跨國使用者」「退休族」當 Persona 自動推導
- 不要漏 SkillSwap.io(2026-06-10 v1 驗證漏過)
- 不要把「家長」當主要客群(使用者原意不是)
```

## 觸發條件

**If** 使用者說以下任一
**Then** 考慮 v2 架構:
- 「v2 架構」「平行架構」「Orchestrator」「summarizer」
- 「不要在自己 context 跑」「context 爆」「context 隔離」
- 「要跑 N 個 web search / API 抓取 / 大量 LLM 任務」
- 「派子代理」「用 hermes chat」「context 不夠」

## 已知陷阱

### Worker 漏關鍵資訊

`v1 失敗 → v2 修正`:v1 沒寫 _plan.md → worker 不知道必抓清單 → 漏 SkillSwap.io。**v2 必寫 _plan.md 給 worker 讀**。

### Summarizer 換掉使用者原意 Persona

`v1 失敗 → v2 修正`:summarizer 自動從 _raw 歸納 Persona → 換成「跨國使用者」「退休族」→ 跟使用者原意偏離。**v2 修正**:summarizer 必讀 _plan.md 保留使用者原意 Persona。

### notify_on_complete 延遲 10-14 分鐘

`常態`:`terminal(background=true, notify_on_complete=true)` 送達延遲 10-14 分鐘、**不是即時**。**用 `ls <output_dir>` 監聽**比等通知更可靠。

### 跑前必先 --dry-run 確認路徑

跟所有 hermes 腳本一樣、跑前先 `--dry-run` 看會做什麼(hermes chat -q 沒有 --dry-run、**改用 echo 任務描述**確認 worker 知道要做啥)。

## 已驗證成果(2026-06-10)

| 指標 | 數值 |
|---|---|
| v2 修正版總耗時 | 6 分 9 秒(4 worker + 1 summarizer) |
| _raw 總量 | 74 KB(4 個 worker 各 ~18 KB) |
| _summary 最終大小 | 12.5 KB |
| 壓縮率 | 83%(74 KB → 12.5 KB) |
| Persona 涵蓋 | 5 個(3 使用者原意 + 2 歸納) |
| 標竿涵蓋 | 8 個(4 直接 + 3 間接 + 1 跨領域) |
| 痛點涵蓋 | 25 個 |
| GitHub repo | `hoonsoropenclaw/hermes-config-backup`(備份整個架構文件) |
| 詳細報告 | `~/shared-infra/CONSUMER_RESEARCHER_V2_ARCHITECTURE_REPORT.md` |
