---
name: prd-drafting
description: PRD 撰寫方法論：把市場調研轉成可執行產品需求文件，含 MoSCoW、User Story、功能/非功能需求、驗收條件。
version: 1.0.0
author: hoonsor
tags: [product, prd, planning, user-story]
---

# PRD Drafting Skill

給產品規劃代理使用。載入後代理會自動套用結構化 PRD 流程。

## 觸發情境

- 收到 `consumer-needs-research-*.md` handoff
- 使用者明確要求寫 PRD
- 進入工程階段前需要把模糊需求結構化

## 流程（見 persona）

1. 讀 handoff 並反問 5 個釐清問題
2. MoSCoW 拆 MVP 範圍
3. 三大 Persona 各寫 3-5 個 User Story
4. 功能 / 非功能需求
5. 成功指標 + 實驗
6. 交付 prd-<project-slug>.md

## User Story 範本

US-001：身為 [Persona 名字]，
我想要 [動作]，
以便 [價值]。

驗收條件（Given/When/Then）：

Given [前提]
When [動作]
Then [預期結果]
And [其他結果]

## MoSCoW 分類規則

- **Must**：v1 沒有就上線失敗的功能
- **Should**：v1 有最好、沒有也能上線
- **Could**：v2 之後再說
- **Won't**：這次不做（明確切割，避免 scope creep）

## 必用工具

- `read_file` / `write_file` / `patch`：管理 PRD 檔案
- `kanban_create`：把 User Story 拆成 ticket 推上 kanban
- `web_search`：查技術現有方案、API 比較
- `notion` / `airtable`（如可用）：同步給團隊

## 自我審查

- 三大 Persona 都有對應 User Story 嗎？
- 每個 User Story 都有 Given/When/Then 嗎？
- v1 範圍真的可以 6 週內做完嗎？
- 風險有對應的緩解行動嗎？
