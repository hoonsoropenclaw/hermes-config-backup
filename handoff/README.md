# Hermes 代理 Handoff 共享區

這個目錄是**消費者需求及功能需求代理 (consumer-researcher)** ↔ **產品規劃代理 (product-planner)** 之間的交付介面。

> **2026-06-10 更新**:從「市場策略代理 (market-strategist)」重塑為「消費者需求及功能需求代理 (consumer-researcher)」。交付物命名從 `market-research.md` 改為 `consumer-needs-research.md`。

## 目錄慣例

```
~/.hermes/handoff/
└── <project-slug>/                          # kebab-case 專案代號
    ├── consumer-needs-research.md           # 消費者需求代理的交付物(主交付)
    ├── sources.json                         # 引用來源索引(可選,便於追蹤)
    ├── clarifications.md                    # 產品規劃代理反問、消費者需求代理回覆(可選)
    └── prd.md                               # 產品規劃代理的交付物
```

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
