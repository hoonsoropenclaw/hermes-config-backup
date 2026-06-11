# Hermes 代理 Handoff 共享區

這個目錄是**多代理 handoff chain 的共享介面**。預設鏈條為 5 階段：

```
使用者提出需求
   ↓
consumer-researcher (56) → product-planner (64) → system-architect (102) → engineering-lead (88) → test-engineer (38)
                                                                                            ↑                                  ↓
                                                                                            └────── 測試失敗丟回 engineering-lead ──────┘
                                                                                                                            ↓
                                                                                                                  測試無誤 → 產出成品給使用者
```

> **2026-06-10 更新**:從「市場策略代理 (market-strategist)」重塑為「消費者需求及功能需求代理 (consumer-researcher)」。交付物命名從 `market-research.md` 改為 `consumer-needs-research.md`。
> **2026-06-11 更新**:鏈條圖改為「線性 5 階段 + 迴圈反饋」模型 —— 線性主流程（consumer→product→arch→eng→test），test 發現問題時**迴圈丟回 engineering-lead**重做、直到測試無誤才把產出給使用者。赫米斯（default）是唯一交棒者（透過「@專案」keyword 觸發 handoff pipeline）。

## 目錄慣例

### 5 階段標準鏈的交付物命名

```
~/.hermes/handoff/
└── <project-slug>/                          # kebab-case 專案代號
    ├── _plan.md                              # 鏈條規劃(列出這個 project 用哪幾個代理、按什麼順序)
    ├── consumer-needs-research.md            # 階段 1 交付物(消費者研究)
    ├── sources.json                          # 引用來源索引(可選)
    ├── clarifications.md                     # 階段 1↔2 往返(可選)
    ├── prd.md                                # 階段 2 交付物(PRD)
    ├── architecture.md                       # 階段 3 交付物(技術架構)
    ├── sprint-report.md                      # 階段 4 交付物(sprint 實作報告)
    ├── qa-signoff.md                         # 階段 5 交付物(品質驗收)
    └── _handoff-log.md                       # 各階段代理的觸發時間/狀態/聯絡窗口(debug 用)
```

### 動態鏈條(非 5 階段)

不是每個 project 都要走滿 5 階段。**預設鏈只是起點,實際鏈條由 `_plan.md` 定義**:

- **「純架構評估」**:只跑 system-architect,產出 architecture-review.md

> **注意**:常駐代理的「@學習」= `trial-and-error` skill(試誤學習的觸發標記)、**不是鏈**。Handoff chain 都是「專案」維度、不是「技能學習」維度。

**`_plan.md` 範本**(由 default orchestrator 在 dispatch 第一個代理前寫入):

```markdown
# <project-slug> Handoff Plan

## Chain Definition
- 階段 1: <agent-name> → 交付物:<filename>
- 階段 2: <agent-name> → 交付物:<filename>
- 階段 3: <agent-name> → 交付物:<filename>
(... 視鏈長動態 ...)

## Skip Reason (如適用)
- 為什麼跳過 stage-X
```

## Handoff 流程

### 1. default orchestrator 接任務
- 判斷要走哪條鏈(預設 5 階段 / 動態 N 階段)
- 建立 `~/.hermes/handoff/<project-slug>/` 目錄
- **先寫 `_plan.md`**(給所有下游代理看鏈條)
- 觸發第一階段代理(`<agent-name> chat -q "..." --cli`)

### 2. 每個代理完成後
- 寫自己的交付物到 `<filename>`(結構見各 agent 的 `persona.md`「交付物格式」段)
- append 一行到 `_handoff-log.md`(`<timestamp> | <agent> | <filename> | status: ok/error`)
- **通知 default orchestrator**(目前是手動觸發,未來考慮 cron 監控)

### 3. default orchestrator 收到通知後
- `cat` 撈最新交付物、確認品質
- 觸發下一階段代理(讀 `_plan.md` 決定下一棒是誰)
- 重複直到鏈尾

### 4. 動態鏈條特殊規則
- **跳過階段**:在 `_plan.md` 列「Skip Reason」+ 補交付物佔位檔(如 `architecture-skipped.md: "N/A - 跳過 system-architect"`)
- **插入階段**:直接在 `_plan.md` 加新階段
- **平行階段**(未來):`_plan.md` 加 `[parallel]` 標記,但目前 orchestrator 是 foreground 串接,平行要靠 `delegate_task` 不是 `hermes chat --cli`

`<project-slug>` 用 kebab-case,例:`freelancer-tax-tool`、`ai-tutor-app`、`school-multidept-site`。

## Handoff 流程

### 1. 消費者需求代理完成報告後

- 建立 `~/.hermes/handoff/<project-slug>/` 目錄
- 寫入 `consumer-needs-research.md`(結構見 `persona.md` 的「交付物格式」段)
- 可選:把所有引用 URL 整理到 `sources.json`(便於下游代理追蹤)
- **通知 default orchestrator**,由 default 觸發產品規劃代理(避免 profile 記憶隔離問題)

### 2. 產品規劃代理收到 handoff 後

- 讀 `consumer-needs-research.md`
- 重點吸收:
  - **三大 Persona 與 User Story 草稿**(直接擴寫成驗收標準)
  - **Must have 功能清單**(MVP 範圍)
  - **功能矩陣差異化點**(PRD 核心賣點)
- 反問 5 個釐清問題(寫到 `clarifications.md`)→ 反觸 consumer-researcher 回覆
- 拆解 MVP 範圍,寫入 `prd.md`

### 3. Handoff 完成後

- 兩個代理都可以從自己的 memory 索引該專案代號
- 未來提到「上次那個 freelancer-tax-tool」會自動撈回
- 預期後續的設計、開發代理(未來可能加 `designer` / `engineering-lead` 等)也從這條 handoff 鏈接續

## 為什麼不用 hermes memory 內建 handoff

- 兩個 profile **記憶庫隔離**(各 profile 有自己的 memories/ 目錄)
- handoff 是**結構化交付物**,不該塞進自由對話
- 用檔案系統當 queue:人也能直接 `cat` 看到內容、版本控制能用 git 追蹤
- default orchestrator 是唯一的中繼者(因為 profile 間不互通)

## 怎麼看現有 handoff

```bash
ls -la ~/.hermes/handoff/                          # 看所有進行中/已完成的專案
ls -la ~/.hermes/handoff/<project-slug>/            # 看單一專案的所有階段交付物
cat ~/.hermes/handoff/<project-slug>/consumer-needs-research.md
cat ~/.hermes/handoff/<project-slug>/prd.md
```

## 範本位置

完整報告範本見 `~/.hermes/handoff/_template/consumer-needs-research.template.md`(由 consumer-researcher 自動維護)。

## 歷史

- **2026-06-10**:從「市場策略代理 (market-strategist)」重塑為「消費者需求及功能需求代理 (consumer-researcher)」
- **2026-06-09**:首次建立 handoff 目錄,當時命名為 `market-research.md`
- 重塑前已完成的專案(`school-multidept-site`):保留 `market-research.md` 檔名、加上 `DEPRECATED_` 前綴避免誤用新流程
