# [專案名稱] PRD（產品需求文件）

> **版本**：v0.1（初稿）  
> **承接自**：`~/.hermes/handoff/<project-slug>/consumer-needs-research.md`  
> **交棒給**：`engineering-lead`（拆 sprint ticket）

---

## 1. 目標 & 成功指標

**產品目標**：（一句話描述這個產品要解決什麼問題、為誰解決）

**關鍵成功指標（KPI）**：
| 指標 | 目標值 | 量測方式 |
|------|--------|---------|
| （例：月活躍用戶）| （例：1000 MAU）| （例：後台 analytics）|
| （例：轉換率）| （例：5%）| （例：Stripe webhook）|
| （例：使用者滿意度）| （例：4.5/5）| （例：NPS 問卷）|

---

## 2. Persona 摘要

從 `consumer-needs-research.md` 抓 3 個核心 Persona 的精華：

### Persona A：（名字 + 一句話）
- **背景**：（職業、年齡、痛點）
- **目標**：（想達成什麼）
- **痛點**：（現有解法的不足）

### Persona B：（...）
### Persona C：（...）

---

## 3. 範圍（v1 / v2 / Backlog）

### v1（Must have，3 個月內必上）
- [ ] 功能 1
- [ ] 功能 2
- [ ] 功能 3

### v2（Should have，6 個月後）
- [ ] 功能 A
- [ ] 功能 B

### Backlog（Could have，未來）
- [ ] 功能 X
- [ ] 功能 Y

---

## 4. User Stories

**每個 User Story 遵循「As a [persona], I want to [action], so that [benefit]」格式**：

### Story 1：<標題>
- **As a** Persona A
- **I want to** 做某事
- **So that** 達到某個目的
- **Acceptance criteria**：
  - [ ] Given（前置條件）...
  - [ ] When（觸發動作）...
  - [ ] Then（預期結果）...

### Story 2：<標題>
...

---

## 5. 功能需求

### 5.1 模組 A：<名稱>

**功能 A.1**：<一句話描述>
- 詳細規格：...
- 對應 User Story：Story 1
- 優先級：P0 / P1 / P2

### 5.2 模組 B：<名稱>
...

---

## 6. 非功能需求

| 類別 | 需求 | 量測指標 |
|------|------|---------|
| 效能 | API response time < 200ms (p95) | k6 load test |
| 可用性 | 99.9% uptime | uptime monitoring |
| 資安 | TLS 1.3 + OWASP top 10 防護 | penetration test |
| 法遵 | GDPR / 各國個資法 | legal review |
| 可擴展 | 支援 10x 使用者成長而無需重構 | load test |
| 可維護 | 新人 1 週內能上手 codebase | onboarding time |

---

## 7. 風險與待辦實驗

| 風險 | 影響 | 機率 | 緩解策略 |
|------|------|------|---------|
| （例：第三方 API 限制）| 高 | 中 | 多重備援 + rate limit monitor |
| （例：新技術棧不熟）| 中 | 中 | spike 1 週 + 找資深 mentor |

### [待釐清] 列表（從 consumer-researcher 來的問題）
- [ ] 問題 1（PR 來源、量測方式、優先級）
- [ ] 問題 2
- [ ] 問題 3

### [待驗證] 列表（需要做實驗/原型才能決定）
- [ ] 假設 1（如何驗證）
- [ ] 假設 2

---

## 8. 時程建議

| 階段 | 週數 | 產出 | 備註 |
|------|------|------|------|
| Sprint 0 | 1 週 | spike + 架構確認 | 解決 [待釐清] + [待驗證] |
| Sprint 1 | 2 週 | MVP 核心功能 | Must have |
| Sprint 2 | 2 週 | 次要功能 + E2E | Should have |
| ... | | | |

---

## 9. 給 engineering-lead 的 1 小時上手 checklist

- [ ] 讀完整份 PRD（30 分鐘）
- [ ] 確認所有 [待釐清]、[待驗證] 項目（10 分鐘）
- [ ] 跟 product-planner sync 一輪（10 分鐘）
- [ ] 規劃 Sprint 0 的 spike 項目（10 分鐘）
- [ ] 確認下游代理（test-engineer）已知此專案

---

**Last updated**: 2026-06-11（product-planner 交付）
