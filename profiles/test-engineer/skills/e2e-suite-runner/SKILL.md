---
name: e2e-suite-runner
description: "從 sprint-<N>-report.md 的 Given/When/Then ticket 自動生成 Playwright E2E 測試、跑、回報。test-engineer 跑 E2E 時必走。"
version: 1.0.0
author: hoonsor
tags: [test, e2e, playwright, given-when-then, automation]
---

# E2E Suite Runner Skill

從 `sprint-<N>-report.md` 的 Given/When/Then ticket 自動生成 Playwright E2E 測試腳本、跑、回報結果。**test-engineer 跑 E2E 時的核心 skill**——不是手寫每個 E2E、是 Given/When/Then → Playwright code 的轉譯。

## 觸發情境

- test-environment-bootstrap 已建好
- 收到 `sprint-<N>-report.md` 裡有「給 test-engineer 的測試重點」段
- 要重跑上個 sprint 沒通過的 E2E
- 使用者說「跑 E2E」「驗收 user flow」

## 為什麼 E2E 從 Given/When/Then 自動生成

- **節省時間**：手寫 1 個 Playwright test 平均 30-60 分鐘、Given/When/Then → code 只要 5 分鐘
- **一致性**：每個 ticket 的驗收條件都是 G/W/T、code 也照 G/W/T 結構跑、零翻譯失誤
- **可追蹤**：ticket #5 G/W/T → test-005.spec.ts → 跑完 PASS/FAIL 直接對到 ticket
- **重生性**：sprint 結束後、G/W/T 不變、test code 重新跑也能驗證

## 標準流程（5 步）

### Step 1 — 讀 sprint report 抓 G/W/T

```bash
cat ~/.hermes/handoff/<project-slug>/sprint-<N>-report.md
```

**抓**：
- 每個 ticket 的 Given/When/Then 段
- 「給 test-engineer 的測試重點」段的「必跑的 E2E 場景」清單
- 「已知跳過的測試」清單（不要為這些生成 E2E）

**產出**：`e2e-tickets.md`（ticket # → G/W/T 對照表）

### Step 2 — 選 user flow 對應

不是每個 ticket 都要 E2E、有些是純後端邏輯（unit + integration 就夠）。

**E2E 適用的場景**：
- ✅ 涉及 UI 互動（點按鈕、填表單、看結果）
- ✅ 涉及 user flow 串接（登入 → 寫文 → 看到）
- ✅ 涉及多個 component 合作
- ✅ 涉及外部 service 真實呼叫（不要 mock 掉）

**E2E 不適用的場景**：
- ❌ 純 utility function（unit 就夠）
- ❌ 純 DB migration（integration 就夠）
- ❌ 純 API endpoint 邏輯（unit + integration 就夠）

**對照後產出**：`e2e-scope.md`（哪些 ticket 跑 E2E、ticket # → flow name）

### Step 3 — 生成 Playwright 程式碼

每個 flow 一個 spec.ts 檔：

```typescript
// tests/e2e/ticket-001-login.spec.ts
import { test, expect } from '@playwright/test';

test('Ticket #1: User login flow', async ({ page }) => {
  // Given: User is on login page
  await page.goto('http://localhost:3000/login');
  
  // When: User enters credentials and clicks submit
  await page.fill('[data-testid="email-input"]', 'test@example.com');
  await page.fill('[data-testid="password-input"]', 'password123');
  await page.click('[data-testid="submit-button"]');
  
  // Then: User is redirected to dashboard
  await expect(page).toHaveURL('http://localhost:3000/dashboard');
  await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
});
```

**產生位置**：`tests/e2e/sprint-<N>/ticket-<NNN>-<slug>.spec.ts`

**重點**：
- 用 `data-testid` 而不是 CSS class（避免 UI 改了就壞）
- 不用 `waitForTimeout()` 寫死（用 `expect().toBeVisible()` 自動等）
- 每個 ticket 對應 1 個 spec、檔名清楚
- 加上 `test.describe()` 標記 sprint 編號

### Step 4 — 跑 Playwright

```bash
cd <project-root>
npx playwright test tests/e2e/sprint-<N>/
```

**輸出**：
- 終端機結果（passed / failed / skipped 數）
- HTML 報告（`playwright-report/`）
- 截圖 + trace（失敗的 test 才有）
- 影片（CI mode 才有、本機不錄）

**常見失敗**：
- `data-testid` 沒實作 → 跟 engineering-lead 反映、要他加
- race condition（測試跑太快、UI 還沒 ready）→ 加 `expect().toBeVisible()` 等元素
- network timeout → 增加 `timeout` 設定
- 服務掛了 → 回 `test-environment-bootstrap` 重建

### Step 5 — 寫 e2e-test-report.md

```markdown
# E2E Test Report (Sprint <N>)

**測試時間**：YYYY-MM-DD HH:MM
**跑了**：<X> 個 spec
**通過**：<Y> 個
**失敗**：<Z> 個
**跳過**：<W> 個

## 失敗清單

### Ticket #1: User login flow
- **錯誤**：`expect.toBeVisible` timeout 30s
- **截圖**：`test-results/ticket-001-login-failed.png`
- **trace**：`test-results/ticket-001-login-trace.zip`
- **可能原因**：
  - UI 改了 data-testid
  - 登入 API 壞了
  - test env 沒建好

## 通過清單（簡列）
- Ticket #2: ...
- Ticket #3: ...

## 截圖
- `qa-artifacts/sprint-<N>/e2e-screenshots/`（所有截圖）
- `qa-artifacts/sprint-<N>/traces/`（失敗的 trace）
```

## 給其他 skill 的介面

| Skill | 用 e2e-test-report.md 的方式 |
|-------|---------------------------|
| `bug-report-generator` | 讀「失敗清單」、每個失敗生成 1 個 bug ticket |
| `sprint-qa-signoff` | 讀「跑了 / 通過 / 失敗」統計、跟 unit + integration 結果組合成 sprint QA |

## 給 engineering-lead 的回饋

跑完 E2E 發現「data-testid 沒實作」或「UI 改了但 spec 沒改」是常見問題。**不要自己改**、寫進 bug ticket 退回給 engineering-lead。

## If→Then 規則

- **If** E2E test 失敗 **Then** 自動生成 bug ticket（用 `bug-report-generator` skill）
- **If** 失敗是「data-testid 找不到」**Then** 檢查是 engineering-lead 改了 UI（合預期）還是 spec 寫錯（要修）
- **If** 跑完所有 E2E **Then** 自動跑 `sprint-qa-signoff` 收尾

_Last updated: 2026-06-11（test-engineer SOP）_
