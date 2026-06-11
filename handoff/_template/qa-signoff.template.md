# Sprint <N> QA Signoff

> **承接自**：`~/.hermes/handoff/<project-slug>/sprint-<N>-report.md`  
> **給主 session 召集**：PASS/FAIL 決策 + bug 報告清單

---

## 1. QA 總覽

| 欄位 | 內容 |
|------|------|
| Sprint 編號 | <N> |
| 測試日期 | YYYY-MM-DD |
| 測試環境 | docker-compose / k8s staging / ... |
| 跑過的 ticket 數 | <X> |
| 通過的 ticket 數 | <X> |
| 失敗的 ticket 數 | <X> |

---

## 2. 三層測試結果

### Unit Test
- 來源：engineering-lead 在 PR 內已跑
- 通過率：<X>%
- 結果：✅ 全部通過 / ⚠️ 部分失敗 / ❌ 大批失敗

### Integration Test
- 環境：docker-compose（postgres + redis + api + frontend）
- 跑了：<X> 個整合場景
- 結果：✅ 全部通過 / ⚠️ <Y> 個失敗 / ❌ 大批失敗
- 失敗的整合場景：...

### E2E Test
- 工具：playwright-skill / agent-browser
- 跑了：<X> 個 user flow
- 結果：✅ 全部通過 / ⚠️ <Y> 個失敗 / ❌ 大批失敗
- 失敗的 user flow：...
- 截圖：見 `qa-artifacts/sprint-<N>/e2e-screenshots/`

### Performance Test
- 工具：k6 / locust
- SLA 對照：

| 指標 | 目標 | 實際 | 結果 |
|------|------|------|------|
| API p95 latency | < 200ms | <X>ms | ✅/❌ |
| API p99 latency | < 500ms | <X>ms | ✅/❌ |
| 併發 1000 RPS | 0 error | <X>% error | ✅/❌ |
| DB query p95 | < 50ms | <X>ms | ✅/❌ |

---

## 3. Bug 清單

### Bug #1（<severity>）
- **What**：（一句話）
- **Where**：（PR / endpoint / ticket）
- **Reproduction**：
  1. ...
  2. ...
  3. ...
- **Expected**：（應該發生什麼）
- **Actual**：（實際發生什麼）
- **Environment**：（commit SHA、test env 版本）
- **Severity**：critical / major / minor
- **Screenshot/Log**：`qa-artifacts/sprint-<N>/bug-1.png`

### Bug #2（<severity>）
...

### Bug 清單彙總
- Critical：<X> 個
- Major：<X> 個
- Minor：<X> 個

---

## 4. PASS / FAIL 決策

### 決策矩陣

| 條件 | 結果 |
|------|------|
| ✅ 全 ticket PASS + 沒 critical bug + 性能在 SLA 內 | **PASS**（可 merge to main） |
| ⚠️ 1-2 個 minor bug + 性能在 SLA 內 | **CONDITIONAL PASS**（merge 但下個 sprint 必修） |
| ❌ 有 critical bug / 性能超 SLA / >30% ticket FAIL | **FAIL**（退回 engineering-lead 修） |

### 本 sprint 決策：`<PASS / CONDITIONAL PASS / FAIL>`

### 理由（明確、可驗證）
- 條件 1：（PASS / FAIL 的具體事實）
- 條件 2：
- 條件 3：

---

## 5. 給主 session 的後續建議

- **若 PASS**：merge to main、進下個 sprint
- **若 CONDITIONAL PASS**：merge 但下個 sprint 必加 bug fix ticket
- **若 FAIL**：sprint 退回 engineering-lead、列「為什麼退回」清單

---

## 6. 給下個 sprint 觀察

- 哪些模組風險高（應該加 regression test）
- 哪些 flaky test 需要修
- 哪些環境問題要解

---

**Last updated**: 2026-06-11（test-engineer 交付）
