---
name: tdd-implementer
description: 對單一 ticket 執行 TDD(RED → GREEN → REFACTOR)實作,完成後 commit + 推 PR。支援 gh CLI 推 code、本地 git 版本控制、平行 sub-agent 多 ticket 同時跑。
version: 1.0.0
author: hoonsor
tags: [tdd, red-green-refactor, gh, git, pr, implement, code]
---

# TDD Implementer Skill

對單一 ticket(或一組平行 ticket)執行完整 TDD 流程。輸入是 sprint-planner 產出的 ticket 含 Given/When/Then 驗收條件,輸出是 feature branch + commit + PR。

## 觸發情境

- sprint-planner 完成後,啟動此 skill 開始實作
- 使用者明確說「實作這個 ticket」「跑 TDD」「寫 code」
- 收到新的 ticket handoff(從 fix 從測試代理回報的 bug)

## 標準流程(7 步)

### 1. 讀 ticket + 確認環境

- 讀 `~/.hermes/handoff/<project-slug>/sprint-<N>-tickets.md`
- 確認當下要實作的 ticket ID、Given/When/Then、依賴
- 確認前置條件(其他依賴 ticket 是否已 merge、測試環境是否就緒)

### 2. 切換到 feature branch

```bash
cd <repo>
git checkout main
git pull origin main
git checkout -b feat/<ticket-id>-<short-title>
gh repo set-default <github-user>/<repo>  # 第一次需要
```

### 3. RED 階段(寫失敗的測試)

針對 ticket 的每個 Given/When/Then,寫對應的 test case:

```python
# tests/test_users_api.py

def test_post_users_creates_user_with_bcrypt_password():
    """S-001 Given-When-Then: POST /api/users creates user with hashed password"""
    response = client.post("/api/users", json={
        "email": "test@example.com",
        "password": "plain_password_123"
    })
    assert response.status_code == 201
    user_id = response.json()["id"]
    # 從資料庫撈出來檢查 password 是雜湊過的
    user = db.query(User).filter_by(id=user_id).first()
    assert user.password_hash != "plain_password_123"  # 不可明文
    assert user.password_hash.startswith("$2b$")  # bcrypt 標記
```

**跑測試確認失敗**:
```bash
pytest tests/test_users_api.py::test_post_users_creates_user_with_bcrypt_password -v
# Expected: FAILED (因為實作還沒寫)
```

### 4. GREEN 階段(寫最小實作)

```python
# api/users.py

@app.post("/api/users", status_code=201)
def create_user(payload: UserCreate):
    password_hash = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt(rounds=12))
    user = User(
        email=payload.email,
        password_hash=password_hash.decode()
    )
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email}
```

**跑測試確認通過**:
```bash
pytest tests/test_users_api.py -v
# Expected: PASS
```

### 5. REFACTOR 階段(改善結構)

- 抽重複邏輯
- 加 type hints
- 改用更好的 naming
- 補 docstring

**持續跑測試確認重構後還是綠的**:
```bash
pytest tests/ -v
# Expected: ALL PASS
```

### 6. Commit + 推 PR

```bash
# Commit(訊息含 ticket ID + 類型 + 為什麼)
git add .
git commit -m "feat(S-001): add POST /api/users with bcrypt password hashing

為什麼選 bcrypt 而非 argon2:
- bcrypt 在 N100 環境成本 12 約 250ms,可接受
- argon2 需要額外 native 依賴,cross-platform build 較複雜
- 公司其他服務已用 bcrypt,降低 audit 成本

驗收條件對照:
- Given: 系統已部署 PostgreSQL 15+ ✅
- When: POST /api/users 帶 email + password ✅
- Then: 回 201 + 新 user id,密碼 bcrypt 雜湊 ✅
- And: 5xx 回 JSON 結構 ✅ (ErrorHandler middleware)
- And: p95 latency < 200ms (待測試代理 E2E 驗證)

Ref: sprint-<N>-tickets.md#S-001"

# 推到 feature branch
git push -u origin feat/S-001-add-user-creation

# 開 PR
gh pr create \
  --title "feat(S-001): add user creation API" \
  --body "## Ticket
S-001

## 類型 + 複雜度
feature / S

## 驗收條件
- [x] Given: 系統已部署 PostgreSQL 15+
- [x] When: POST /api/users 帶 email + password
- [x] Then: 回 201 + 新 user id,密碼 bcrypt 雜湊
- [x] And: 5xx 回 JSON 結構
- [ ] And: p95 latency < 200ms (待測試代理 E2E 驗證)

## 為什麼
[commit message 內的說明]

## 測試
- 8 unit tests pass
- Coverage: 92% for users_api.py"
```

### 7. 標記 ticket 完成 + 進度追蹤

更新 `~/.hermes/handoff/<project-slug>/sprint-<N>-progress.md`:

```markdown
## S-001: add user creation API

- [x] RED: 測試寫完,確認失敗
- [x] GREEN: 實作完成,測試通過
- [x] REFACTOR: 結構改善,持續綠
- [x] Commit + PR: #123 已開
- [ ] 兩階段 Review: 待 code-reviewer skill 跑
- [ ] Merge: 待 review 過
```

---

## 平行實作(多個 Parallelizable ticket 同時跑)

當 sprint-planner 標記 ticket 為 Parallelizable 且互不依賴,用 `delegate_task` 同時派遣:

```python
delegate_task(
  goal="實作 S-001 ticket (add user creation API)",
  context="[完整 ticket 內容 + Given/When/Then + 此 skill 的 7 步流程]",
  toolsets=["terminal", "file"]
)
# 同時跑 S-003、S-005...
```

每個 sub-agent 在自己的 worktree 跑,完成後各自推 PR。

---

## 必用工具

- `read_file` / `write_file` / `patch`
- `terminal` (git, gh, pytest, npm/pip)
- `delegate_task` (平行 ticket)
- `tdd-workflow` skill(更深入的 TDD 細節)
- `github` skill(gh CLI 高階用法)
- `python-anti-patterns` skill(避免常見 Python 陷阱)
- `security-review` skill(資安 checklist)

## 品質檢核(自我審查清單)

每個 ticket 完成後自問:
1. RED 階段真的有跑失敗的測試?(不是寫了但沒跑)
2. GREEN 階段是「最小可通過實作」?(不是 over-engineering)
3. REFACTOR 階段持續綠?(沒有破壞既有測試)
4. Commit message 含「為什麼」?(不只是「改了什麼」)
5. PR 描述對照 Given/When/Then 逐項打勾?
6. 沒有跳過 security-review?(密碼、明文個資、SQL injection 都過了)

任一為否,回去補。

## 常見坑

1. **忘記跑測試就 commit** — 永遠跑 `pytest` 確認綠的才 commit
2. **commit message 寫「update」「fix」** — 必含 ticket ID + 類型 + 為什麼
3. **直接 push 到 main** — 只推 feature branch + PR
4. **RED 階段跳過** — 「我先寫 code 再補測試」會讓 sprint 失控
5. **over-engineering** — YAGNI,只實作 ticket 範圍,不做額外功能
6. **忘記更新 progress.md** — 後續 ticket 會不知道哪些是已完成的

## 詳見

- `references/red-green-refactor-examples.md`(具體範例)
- `references/commit-message-template.md`(完整 commit 格式)
- `references/pr-template.md`(PR 描述範本)
