---
name: bug-report-generator
description: "從失敗的 E2E / integration / performance test log 自動生成 .docx bug 報告。test-engineer FAIL sprint 必用。"
version: 1.0.0
author: hoonsor
tags: [test, bug-report, docx, reproduction, severity]
---

# Bug Report Generator Skill

從失敗的測試 log 自動生成結構化 bug 報告（`.docx` 格式、用 `minimax-docx` 模板）。**test-engineer FAIL sprint 時必走**——不是寫「我覺得有 bug」、而是給 engineering-lead 具體可重現的證據。

## 觸發情境

- `e2e-suite-runner` 跑完發現失敗
- `test-driven-development` 跑 unit test 有失敗
- Performance test 發現 regression
- 使用者說「這個 bug 給 engineering-lead」

## 為什麼用 .docx 不是 .md

- engineering-lead 比較習慣看 .docx（工程師常用）
- `.docx` 可以有表格、顏色、截圖內嵌、版面整齊
- `.md` 給程式讀、`.docx` 給人讀
- sprint review meeting 用投影機放 .docx 比 .md 順眼

## 標準流程（5 步）

### Step 1 — 收集失敗資訊

從測試 log 抓：
- **What**：（一句話描述問題）
- **Where**：（PR / endpoint / ticket # / 檔案路徑）
- **Reproduction**：（1/2/3 步驟）
- **Expected**：（應該發生什麼）
- **Actual**：（實際發生什麼）
- **Environment**：
  - commit SHA（`git rev-parse HEAD`）
  - test env 版本（`docker compose ps`）
  - 瀏覽器版本（E2E 才需要）
  - 網路狀態
- **Severity**：critical / major / minor
- **附件**：截圖、log、trace

### Step 2 — 分類 Severity

| Severity | 定義 | 例子 | sprint 影響 |
|----------|------|------|-----------|
| **critical** | 主流程全斷、無 workaround | 登入完全壞掉、付款 500 | sprint 必 FAIL |
| **major** | 主流程部分壞、有 workaround 但 UX 差 | 註冊流程壞、但可用第三方登入 | sprint 建議 FAIL |
| **minor** | 邊角功能壞、不影響主流程 | 個人頭像上傳壞、但顯示預設圖 OK | sprint 可 CONDITIONAL PASS |

### Step 3 — 寫 bug ticket（markdown 格式）

```markdown
# Bug #1（critical）

**What**：登入 API 在 production 回 500
**Where**：PR #234 / `api/auth/login.py` / `POST /api/auth/login`

## Reproduction
1. 開瀏覽器到 https://app.example.com/login
2. 輸入 email `test@example.com` + 密碼 `correct-password`
3. 點「登入」按鈕
4. 看到 500 Internal Server Error

## Expected
- 應該導到 https://app.example.com/dashboard
- 後台 log 應該有 200 記錄

## Actual
- 看到 500 Internal Server Error
- 後台 log：`psycopg2.OperationalError: connection to server at "postgres" (172.18.0.2), port 5432 failed: Connection refused`

## Environment
- commit SHA：`abc123def`
- test env：`docker compose ps` 顯示 postgres healthy
- 瀏覽器：Chrome 120.0

## Severity
critical（主流程全斷、無 workaround）

## Attachment
- `qa-artifacts/sprint-<N>/bug-1-screenshot.png`
- `qa-artifacts/sprint-<N>/bug-1-server-log.txt`
```

### Step 4 — 用 minimax-docx 生成 .docx

寫 Python 腳本、用 minimax-docx 套件：

```python
from minimax_docx import Document
from pathlib import Path

doc = Document()
doc.add_heading(f'Bug #{bug_id} ({severity})', 0)
doc.add_paragraph(f'**What**：{what}')
doc.add_paragraph(f'**Where**：{where}')

doc.add_heading('Reproduction', 1)
for i, step in enumerate(reproduction, 1):
    doc.add_paragraph(f'{i}. {step}')

doc.add_heading('Expected', 1)
doc.add_paragraph(expected)

doc.add_heading('Actual', 1)
doc.add_paragraph(actual)

doc.add_heading('Environment', 1)
for k, v in environment.items():
    doc.add_paragraph(f'{k}: {v}')

doc.add_heading('Severity', 1)
doc.add_paragraph(severity)

# 附件
if screenshot:
    doc.add_picture(screenshot, width=Inches(6))

doc.save(f'bug-report-{bug_id}.docx')
```

**產出**：`bug-report-<N>.docx`（給 engineering-lead 看）

### Step 5 — 寫進 handoff/

```bash
cp bug-report-<N>.docx ~/.hermes/handoff/<project-slug>/
echo "- [$(date)] Bug #${bug_id} (${severity}): ${what}" >> ~/.hermes/handoff/<project-slug>/sprint-<N>-bugs.md
```

**給 engineering-lead 的交付**：
- `bug-report-<N>.docx`（人類讀）
- `sprint-<N>-bugs.md`（彙總清單、預設讀）
- 對應到 `sprint-<N>-qa-signoff.md` 的「Bug 清單」段

## 為什麼 bug 報告要附 reproduction

| 沒附 reproduction 的 bug 報告 | 附 reproduction 的 bug 報告 |
|---------------------------|----------------------|
| engineering-lead 問「怎麼重現？」 | engineering-lead 直接照步驟 1/2/3 重現 |
| 浪費 2-3 小時 debug 時間 | 立刻知道是哪個環節出問題 |
| bug 可能永遠修不好 | bug 可以被追蹤到 fix |

## 給 engineering-lead 的反向回饋

跑 sprint 時如果發現：
- 某個 component **反覆出 bug**（同個檔案、3 個 sprint 都有 bug）→ 寫進 `tech-debt` skill 紀錄
- 某個 PR 的 unit test 覆蓋率 < 70% → 退回、要求補 test
- 某個 Given/When/Then **寫得不夠具體**（缺步驟、缺預期）→ 退回、要求改寫

**不要自己改 engineering-lead 的程式碼**——那是下個 sprint 的事。

## If→Then 規則

- **If** 測試失敗 **Then** 自動跑 bug-report-generator 生成 .docx（不要只回「FAIL」）
- **If** severity = critical **Then** bug 報告加紅色標記 + 立刻 flag 給主 session
- **If** bug 報告超過 5 個 **Then** 自動把 sprint 標為 FAIL（不需要測試每個都過）

_Last updated: 2026-06-11（test-engineer SOP）_
