---
name: sprint-reporter
description: Sprint 結束時產出 burndown 圖 + velocity 報告,更新 sprint-history.md。可選週報、月中進度報告。
version: 1.0.0
author: hoonsor
tags: [sprint, report, burndown, velocity, metrics, retro]
---

# Sprint Reporter Skill

Sprint 結束時產出報告(burndown 圖 + velocity 報告 + 自我回顧),更新 `sprint-history.md`。也支援週報跟月中進度報告。

## 觸發情境

- Sprint 結束時(每 2 週)
- 使用者明確說「產出 sprint 報告」「跑 retro」「看 velocity」
- 月中進度報告(可選)

## 報告類型

### 1. Sprint 結案報告(Sprint Closing Report)

**產出**:`~/.hermes/handoff/<project-slug>/sprint-<N>-report.md`

**內容結構**:

```markdown
# Sprint N 結案報告

**Sprint 週期**: 2026-06-10 ~ 2026-06-23 (2 週)
**參與角色**: engineering-lead + 測試代理 + system-architect
**目標**: [從 sprint plan 抄]

---

## Burndown 圖

```
Day:  1  2  3  4  5  6  7  8  9  10
理想:  9  8  7  6  5  4  3  2  1   0
實際:  9  9  8  7  6  5  4  3  2   0
       ↑ 第 6 天卡在 S-002 兩天
```

---

## Velocity

| 指標 | 數值 |
|------|------|
| 計畫 ticket 數 | 7 |
| 完成 ticket 數 | 6 |
| 完成率 | 86% |
| 計畫 story points | 12 |
| 實際 story points | 10 |
| Velocity (SP/週) | 5.0 |
| 跟上個 sprint 比較 | +1.2 SP/週 |

---

## 完成的 Tickets

| ID | 標題 | 類型 | 複雜度 | 實際耗時 | PR |
|----|------|------|--------|----------|-----|
| S-001 | add user creation API | feature | S | 0.5 天 | #123 |
| S-002 | add user login API | feature | S | 1.5 天(超 1 天) | #124 |
| M-001 | add email validation | feature | M | 2 天 | #125 |
| ... | ... | ... | ... | ... | ... |

---

## 沒完成的 Tickets

| ID | 標題 | 為什麼沒完成 | 下個 sprint 處理? |
|----|------|------------|------------------|
| M-002 | add password reset | 依賴測試代理 E2E 框架尚未就緒 | 是,等測試代理 |
| L-001 | add OAuth 第三方登入 | 使用者變更 scope(改為 v2) | 否,改進 backlog |

---

## 從測試代理回收的 Bug

| Bug ID | 標題 | 嚴重度 | 已開 ticket? |
|--------|------|--------|--------------|
| BUG-001 | 登入失敗時回 500 而非 401 | Critical | 是,M-003 |
| BUG-002 | email 欄位未驗證格式 | Important | 是,M-004 |

---

## 自我回顧(Retro)

### 做得好的
- 平行 ticket 用 delegate_task 同時跑,省 1.5 天
- commit message 都有寫「為什麼」,review 變快
- 跟測試代理的 Given/When/Then 交接很順

### 要改進的
- M-002 因為等測試代理卡 2 天,下個 sprint 提早 1 週對齊
- S-002 估時 0.5 天實際 1.5 天,下次同類 ticket 估 M
- L-001 使用者中途改 scope,下個 sprint 開始前先用 clarify 確認 scope

### 下個 sprint 行動項
- [ ] 提早 1 週跟測試代理對齊依賴
- [ ] 估時偏低時自動升級複雜度(S → M)
- [ ] sprint 開始前跑一次 scope 確認
```

### 2. 週報(Mid-Sprint Status)

**產出**:訊息直接送到主 session,簡短格式

```markdown
## Sprint N 週報 (Day 5/10)

**進度**: 50% 完成(3/6 tickets)
**風險**: S-002 卡 2 天、可能延遲到下週
**協助需求**: 無
**下週預期**: 完成 2 tickets,可能加 1 個 bug 修復
```

### 3. 月中進度報告(Monthly)

**產出**:`~/.hermes/handoff/<project-slug>/monthly-2026-06.md`

```markdown
# 2026-06 月報

## 完成的 Sprints
- Sprint 1: 6/6 tickets (velocity 4.2 SP/週)
- Sprint 2: 6/7 tickets (velocity 5.0 SP/週, +19%)

## 累計交付
- API endpoints: 12 個
- 資料表: 5 個
- 整合測試: 0 (待測試代理)

## 累積 tech debt
- 3 個 refactor tickets 從 Quality Review 累積
- 1 個 infra ticket (PostgreSQL 連線池調校)

## 給長期 roadmap (system-architect)
- OAuth 整合是熱門需求,下季評估
- 行動 app API 還沒規劃,需架構決策
```

---

## 更新 sprint-history.md

每次 sprint 結束,在 `sprint-history.md` 加一行:

```markdown
| Sprint | 週期 | 完成率 | Velocity | 給測試代理的 ticket 數 | 回收 bug 數 |
|--------|------|--------|----------|--------------------|------------|
| 1 | 06-01~06-13 | 100% | 4.2 | 6 | 1 |
| 2 | 06-10~06-23 | 86% | 5.0 | 6 | 2 |
```

---

## 必用工具

- `read_file` / `write_file`(讀 sprint progress、寫報告)
- `execute_code` 或 `python`(算 velocity、畫 burndown)
- `delegate_task`(可選,把 burndown 圖交給 designer sub-agent 美化)

## 品質檢核

1. Burndown 圖是實際數據(不是猜的)?
2. Velocity 有跟上個 sprint 比較?
3. 沒完成的 ticket 都有說明「為什麼」+「下個 sprint 處理?」?
4. 從測試代理回收的 bug 都有追蹤?
5. Retro 段有「做得好的、要改進的、行動項」三段?

## 詳見

- `references/burndown-chart-format.md`(Mermaid 圖語法)
- `references/velocity-calculation.md`(story points 怎麼算)
- `references/retro-template.md`(完整 retro 範本)
