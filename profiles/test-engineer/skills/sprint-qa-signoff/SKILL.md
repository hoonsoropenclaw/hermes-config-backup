---
name: sprint-qa-signoff
description: "從三層測試結果（unit + integration + E2E + performance）+ bug 清單生成 sprint-N-qa-signoff.md + PASS/FAIL 決策。test-engineer 唯一對外的交付物、必走。"
version: 1.0.0
author: hoonsor
tags: [test, qa, signoff, sprint-decision, pass-fail]
---

# Sprint QA Signoff Skill

從三層測試結果 + bug 清單生成 `sprint-<N>-qa-signoff.md` + PASS/FAIL 決策。**test-engineer 唯一對外交付物**、**sprint 結束時必走 SOP**——沒有 qa-signoff、sprint 等於沒結束。

## 觸發情境

- `e2e-suite-runner` 跑完 E2E
- `bug-report-generator` 跑完所有 bug 報告
- sprint 結束時
- 使用者說「sprint sign off」「結束 sprint」「sprint PASS/FAIL」

## 為什麼這個 skill 是 test-engineer 核心

test-engineer 在 handoff chain 最後一棒、**不再 handoff 給下個代理**——直接給主 session 決策。決策的依據就是 `sprint-<N>-qa-signoff.md`：

- 主 session 看到 PASS → 進下個 sprint
- 主 session 看到 CONDITIONAL PASS → merge 但下個 sprint 必加 bug fix ticket
- 主 session 看到 FAIL → 退回 engineering-lead、列「為什麼退回」清單

## 標準流程（4 步）

### Step 1 — 收集所有測試結果

從 test-engineer 跑過的測試 + engineering-lead 跑的 unit test：

| 來源 | 路徑 | 內容 |
|------|------|------|
| Unit test | `engineering-lead PR 內 CI log` | engineering-lead 跑的 |
| Integration test | `~/.hermes/handoff/<project-slug>/sprint-<N>-integration-report.md` | test-engineer 跑的 |
| E2E test | `~/.hermes/handoff/<project-slug>/sprint-<N>-e2e-report.md` | test-engineer 跑的 |
| Performance | `~/.hermes/handoff/<project-slug>/sprint-<N>-perf-report.md` | test-engineer 跑的 |
| Bug 清單 | `~/.hermes/handoff/<project-slug>/sprint-<N>-bugs.md` | test-engineer 跑的 |

### Step 2 — 套 PASS/FAIL 決策矩陣

```
┌─────────────────────────────────────────────────────────────────┐
│                      PASS / FAIL 決策矩陣                        │
├─────────────────────────────────────────────────────────────────┤
│ 全 ticket PASS + 沒 critical bug + 性能在 SLA 內  → ✅ PASS     │
│ 1-2 個 minor bug + 性能在 SLA 內                   → ⚠️ CONDITIONAL│
│ 有 critical bug / 性能超 SLA / >30% ticket FAIL  → ❌ FAIL     │
└─────────────────────────────────────────────────────────────────┘
```

**注意**：
- 1 個 critical bug = FAIL（不管其他多完美）
- 1 個 major bug 但無 workaround = FAIL
- 30% ticket FAIL（3 個 ticket 1 個 FAIL）= FAIL
- 性能 p95 差 50% SLA 內但 p99 超 SLA = 看架構怎麼定義（default = FAIL）

### Step 3 — 寫 sprint-N-qa-signoff.md

用 `_template/qa-signoff.template.md` 範本：

```markdown
# Sprint <N> QA Signoff

> **承接自**：sprint-<N>-report.md
> **給主 session 召集**：PASS/FAIL 決策 + bug 清單

## 1. QA 總覽
（從 Step 1 收集的結果填）

## 2. 三層測試結果
### Unit Test
- 通過率：<X>%
- 結果：✅ / ⚠️ / ❌

### Integration Test
- 跑了：<X> 個
- 結果：✅ / ⚠️ / ❌

### E2E Test
- 跑了：<X> 個
- 結果：✅ / ⚠️ / ❌

### Performance Test
- SLA 對照表

## 3. Bug 清單
（從 bug-report-generator 的彙總清單）

## 4. PASS/FAIL 決策

### 決策矩陣
（套 Step 2 的矩陣）

### 本 sprint 決策：`<PASS / CONDITIONAL PASS / FAIL>`

### 理由
- 條件 1：（PASS / FAIL 的具體事實）
- 條件 2：
- 條件 3：

## 5. 給主 session 的後續建議
- 若 PASS：merge to main
- 若 CONDITIONAL PASS：merge 但加 bug fix ticket
- 若 FAIL：sprint 退回 engineering-lead

## 6. 給下個 sprint 觀察
- 哪些模組風險高
- 哪些 flaky test 要修
- 哪些環境問題要解
```

**產出**：`sprint-<N>-qa-signoff.md` 寫到 `~/.hermes/handoff/<project-slug>/`

### Step 4 — 給主 session 通知（用 minimax-docx 同時出 .docx）

```python
from minimax_docx import Document

doc = Document()
doc.add_heading(f'Sprint {N} QA Signoff - {decision}', 0)
# ... 內容從 signoff.md 自動轉 ...
doc.save(f'sprint-{N}-qa-signoff.docx')
```

**好處**：sprint review meeting 可以用 .docx 投影。

## 為什麼 PASS/FAIL 不能模糊

| 模糊決策的後果 |
|--------------|
| 主 session 不知道要 merge 還是退回 |
| engineering-lead 不知道下個 sprint 該做什麼 |
| test-engineer 自己也不知道算不算「完成」 |
| sprint review 開會要重新討論決策 → 浪費時間 |

**唯一接受的三個決策**：PASS / CONDITIONAL PASS / FAIL

## 跟主 session 的介面

主 session 看到 sprint-qa-signoff.md 後的決策樹：

```
看到 PASS
  → 通知使用者「sprint N PASS、可 merge」
  → merge to main
  → 觸發下個 sprint planning

看到 CONDITIONAL PASS
  → 通知使用者「sprint N CONDITIONAL PASS、merge 但必加 bug fix」
  → merge to main
  → 觸發下個 sprint planning（加 bug fix ticket）

看到 FAIL
  → 通知使用者「sprint N FAIL、退回 engineering-lead」
  → 退回 engineering-lead
  → 不 merge
  → 觸發 engineering-lead 修 bug ticket、再做新 sprint
```

## If→Then 規則

- **If** 跑完所有測試 **Then** 跑 sprint-qa-signoff 自動產出決策（不要等使用者問）
- **If** 決策是 FAIL **Then** 自動 flag 給主 session、附「為什麼退回」清單
- **If** 決策是 CONDITIONAL PASS **Then** 自動生成下個 sprint 的 bug fix ticket

## 給下個 sprint 的回饋

每次 signoff 後、test-engineer 應該主動記錄：
- 哪些 flaky test（不穩定、可能環境問題）
- 哪些 regression 風險（改了某 component 影響其他）
- 哪些 env 設定要修（test-env-bootstrap 失敗的次數）

**寫進** `~/.hermes/handoff/<project-slug>/qa-history.md` 累積。

## 4 個專屬 skill 的關係圖

```
test-environment-bootstrap  ← 必先跑
        ↓
unit test (engineering-lead) + integration test + e2e-suite-runner + performance test
        ↓
bug-report-generator        ← 失敗時跑
        ↓
sprint-qa-signoff           ← 必最後跑、給主 session 決策
```

## 完整 sprint 結束 checklist

- [ ] `test-environment-bootstrap` 跑完、`test-env-status.md` 寫好
- [ ] `e2e-suite-runner` 跑完、`e2e-test-report.md` 寫好
- [ ] `bug-report-generator` 跑完（如果有失敗）、`bug-report-<N>.docx` 寫好
- [ ] `sprint-qa-signoff` 跑完、`sprint-<N>-qa-signoff.md` 寫好
- [ ] `sprint-<N>-qa-signoff.md` 跟 `bug-report-<N>.docx` 寫進 `~/.hermes/handoff/<project-slug>/`
- [ ] 通知主 session、給出 PASS/FAIL/CONDITIONAL PASS

_Last updated: 2026-06-11（test-engineer SOP）_
