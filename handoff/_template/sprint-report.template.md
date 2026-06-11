# Sprint <N> 報告

> **承接自**：`~/.hermes/handoff/<project-slug>/prd.md` + `arch-<slug>.md`  
> **交棒給**：`test-engineer`（跑品質驗收）

---

## 1. Sprint 概述

| 欄位 | 內容 |
|------|------|
| Sprint 編號 | <N> |
| 開始日期 | YYYY-MM-DD |
| 結束日期 | YYYY-MM-DD |
| 主軸 | （這 sprint 主要做什麼）|
| Velocity | <X> story points（從上個 sprint 預估） |

---

## 2. 完成的 Tickets

### Ticket 1：<標題>
- **複雜度**：S / M / L
- **類型**：feature / fix / refactor / infra
- **PR 編號**：[#123](https://github.com/...)
- **Given/When/Then**：
  - **Given**：（前置條件）
  - **When**：（觸發動作）
  - **Then**：（預期結果）
- **單元測試覆蓋率**：<X>%
- **整合測試結果**：PASS / FAIL
- **備註**：（任何需要 test-engineer 知道的）

### Ticket 2：<標題>
...

---

## 3. 未完成的 Tickets

### Ticket X：<標題>（carry to next sprint）
- 為什麼沒做完
- 預估還要多久
- 任何 blocker

---

## 4. 程式碼品質

- **總 commit 數**：<X>
- **總 PR 數**：<X>
- **總 LOC 變更**：+<X> -<Y>
- **新增依賴套件**：（package.json / requirements.txt 變更）
- **移除的依賴套件**：
- **重構的部分**：
- **技術債務累積**：（任何 to-be-fixed-later 項目）

---

## 5. 兩階段 Review

### Spec Review（sprint 開始前）
- 對 arch 與 PRD 的一致性檢查
- 對 Given/When/Then 完整性的檢查
- 結果：✅ 通過 / ⚠️ 部分修正 / ❌ 重做

### Quality Review（sprint 結束前）
- Code review 結果（誰 review、有幾個 comment、是否都解決）
- Security review（OWASP top 10 自我檢查）
- Performance baseline（API latency、DB query time）
- 結果：✅ 通過 / ⚠️ 部分修正 / ❌ 重做

---

## 6. 給 test-engineer 的測試重點

- **必跑的 E2E 場景**：（從 consumer-needs-research Persona 行為抓出）
- **必跑的整合測試**：（從每個 ticket 的整合邊界）
- **必跑的 performance baseline**：（從 NFR 抓）
- **已知跳過的測試**：（為什麼跳）

---

## 7. 給下個 sprint 的建議

- 哪些 ticket 應該優先
- 哪些技術債務該清
- 哪些 spike 該做

---

**Last updated**: 2026-06-11（engineering-lead 交付）
