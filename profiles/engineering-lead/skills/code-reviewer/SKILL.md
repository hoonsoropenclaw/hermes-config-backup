---
name: code-reviewer
description: 對完成的 ticket 跑兩階段 review:Spec Review(對照 Given/When/Then 驗收條件)+ Quality Review(code 風格、資安、效能、可維護性)。不跳過任一階段。
version: 1.0.0
author: hoonsor
tags: [review, spec-review, quality-review, pr, merge, given-when-then]
---

# Code Reviewer Skill

對完成的 ticket 跑兩階段 review。**不跳過任一階段**——Spec Review 過才進 Quality Review,兩個都過才 merge PR。

## 觸發情境

- tdd-implementer 完成 ticket + 開 PR 後
- 使用者明確說「review 這個 PR」「驗收條件都過嗎?」
- sprint 結束前的 quality gate

## 兩階段 Review 流程

### 階段 1: Spec Review

**目的**:確認 PR 真的滿足 ticket 的驗收條件,沒做 Out of Scope 的事。

**檢查清單**:

```markdown
## Spec Review 報告

### Ticket 資訊
- ID: S-001
- 標題: add user creation API
- PR: #123
- 作者: engineering-lead

### 驗收條件對照
- [x] Given: 系統已部署 PostgreSQL 15+
  - 證據: docker-compose.yml 有 postgres:15 服務
- [x] When: POST /api/users 帶 email + password
  - 證據: api/users.py:create_user() 函式存在
- [x] Then: 回 201 + 新 user id,密碼 bcrypt 雜湊
  - 證據: test_post_users_creates_user_with_bcrypt_password() 測試通過
- [x] And: 5xx 回 JSON 結構
  - 證據: middleware/error_handler.py:handle_500() 統一格式
- [ ] And: p95 latency < 200ms
  - 證據: **待補** — 此項需要測試代理 E2E 驗證,工程主管不驗證此項

### Out of Scope 檢查
- [x] 沒做 user deletion(Out of Scope 內)
- [x] 沒做 user list with pagination(Out of Scope 內)
- [x] 沒做 OAuth 第三方登入(Out of Scope 內)

### 結論
- Spec Review: **通過** ✅
- 唯一未驗證項(p95 latency)移交給測試代理
```

**Spec Review 結果**:
- ✅ **通過**:進 Quality Review
- ❌ **不通過**:退回 tdd-implementer 重做(列出哪幾項 Given/When/Then 沒滿足)

### 階段 2: Quality Review

**目的**:確認 code 風格、資安、效能、可維護性都達標。

**檢查清單**:

```markdown
## Quality Review 報告

### 1. Code 風格
- [x] 通過 linter (ruff / eslint)
- [x] 通過 formatter (black / prettier)
- [x] 命名一致 (snake_case for Python, camelCase for JS)
- [x] 沒有 dead code (註解掉的程式碼)
- [x] 沒有 print() (改用 logging)

### 2. 資安
- [x] 密碼 bcrypt 雜湊 (cost 12+)
- [x] SQL injection 防護 (用 ORM 或 parameterized query)
- [x] XSS 防護 (前端 escape user input)
- [x] CSRF token 檢查
- [x] 敏感資料不入 log (password, token, PII)

### 3. 效能
- [x] 無 N+1 query (用 eager loading)
- [x] 資料庫索引覆蓋查詢條件
- [x] 無 blocking call 在 event loop (Python async)
- [x] 大 payload 分頁 (limit + offset)

### 4. 可維護性
- [x] 函式單一職責 (SRP)
- [x] 沒有 magic number (用常數)
- [x] 錯誤訊息對開發者友好
- [x] Docstring 公開函式
- [x] Type hints 覆蓋率 >80%

### 5. 測試
- [x] Unit test 覆蓋率 >80%
- [x] 邊界條件有測 (空字串、超長、特殊字元)
- [x] Mock 外部依賴 (API、DB、檔案)

### 結論
- Quality Review: **通過** ✅
- 沒有 Critical / Important issue
- Minor issue (1 個): functions/get_user.py:42 命名 user_id → uid, 但不影響 merge
```

**Quality Review 結果**:
- ✅ **通過 (無 Critical/Important)**:可 merge
- ⚠️ **通過 (有 Minor issue)**:可 merge,Minor 列為下次 sprint 的 refactor ticket
- ❌ **不通過 (有 Critical/Important)**:退回 tdd-implementer

### 兩個 Review 都過:Merge PR

```bash
# 確認 CI 通過
gh pr checks 123

# Merge
gh pr merge 123 --squash --delete-branch
```

更新 `sprint-<N>-progress.md` 標記 merge 完成。

---

## 跟其他 skill 的關係

| Skill | 互動 |
|-------|------|
| `tdd-implementer` | 上游,接收完成的 PR |
| `code-review` (Anthropic plugin) | 平行,Anthropic 通用 code review skill |
| `security-review` | 平行,資安 review 細節 |
| `python-anti-patterns` | 平行,Python 特定 anti-patterns |
| `github` | 工具,gh CLI 驗 PR、merge、刪 branch |

## 必用工具

- `terminal` (gh CLI、pytest、linter)
- `read_file` / `search_files` (讀 PR diff)
- `delegate_task` (可選,把 review 委派給獨立的 reviewer sub-agent 增加視角多元)

## 品質檢核

1. 兩個 review 都有具體證據(不是「看起來不錯」)?
2. Spec Review 每個 Given/When/Then 都有對應證據?
3. Quality Review 5 個類別(code 風格、資安、效能、可維護性、測試)都過?
4. 不在 PR comment 講主觀偏好(「我喜歡這種命名」),講客觀標準(「linter 規定這樣命名」)?

## 常見坑

1. **跳過 Quality Review 直接 merge** — 會讓 tech debt 累積
2. **Spec Review 用「看起來對」當證據** — 必附「這行 code 對應這個 Given」證據
3. **Quality Review 把 Minor 當 Critical 退回** — 過度嚴格會拖慢 sprint
4. **不在 CI 通過時 merge** — CI 是最低品質門檻
5. **merge 後忘記刪 branch** — 用 `--delete-branch` flag

## 詳見

- `references/spec-review-checklist.md`(完整 Spec Review 清單)
- `references/quality-review-checklist.md`(完整 Quality Review 5 類別)
- `references/minor-vs-critical-guide.md`(怎麼判斷 issue 嚴重度)
