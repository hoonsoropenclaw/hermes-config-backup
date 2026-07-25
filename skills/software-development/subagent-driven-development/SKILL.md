---
name: subagent-driven-development
description: "Execute plans via delegate_task subagents (2-stage review)."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, subagent, implementation, workflow, parallel]
    related_skills: [writing-plans, requesting-code-review, test-driven-development, code-assist, persistent-subagent, systematic-debugging]
---

# Subagent-Driven Development

## Overview

Execute implementation plans by dispatching fresh subagents per task with systematic two-stage review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## When to Use

Use this skill when:
- You have an implementation plan (from writing-plans skill or user requirements)
- Tasks are mostly independent
- Quality and spec compliance are important
- You want automated review between tasks

**vs. manual execution:**
- Fresh context per task (no confusion from accumulated state)
- Automated review process catches issues early
- Consistent quality checks across all tasks
- Subagents can ask questions before starting work

## The Process

### 1. Read and Parse Plan

Read the plan file. Extract ALL tasks with their full text and context upfront. Create a todo list:

```python
# Read the plan
read_file("docs/plans/feature-plan.md")

# Create todo list with all tasks
todo([
    {"id": "task-1", "content": "Create User model with email field", "status": "pending"},
    {"id": "task-2", "content": "Add password hashing utility", "status": "pending"},
    {"id": "task-3", "content": "Create login endpoint", "status": "pending"},
])
```

**Key:** Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context.

### 2. Per-Task Workflow

For EACH task in the plan:

#### Step 1: Dispatch Implementer Subagent

Use `delegate_task` with complete context:

```python
delegate_task(
    goal="Implement Task 1: Create User model with email and password_hash fields",
    context="""
    TASK FROM PLAN:
    - Create: src/models/user.py
    - Add User class with email (str) and password_hash (str) fields
    - Use bcrypt for password hashing
    - Include __repr__ for debugging

    FOLLOW TDD:
    1. Write failing test in tests/models/test_user.py
    2. Run: pytest tests/models/test_user.py -v (verify FAIL)
    3. Write minimal implementation
    4. Run: pytest tests/models/test_user.py -v (verify PASS)
    5. Run: pytest tests/ -q (verify no regressions)
    6. Commit: git add -A && git commit -m "feat: add User model with password hashing"

    PROJECT CONTEXT:
    - Python 3.11, Flask app in src/app.py
    - Existing models in src/models/
    - Tests use pytest, run from project root
    - bcrypt already in requirements.txt
    """,
    toolsets=['terminal', 'file']
)
```

#### Step 2: Dispatch Spec Compliance Reviewer

After the implementer completes, verify against the original spec:

```python
delegate_task(
    goal="Review if implementation matches the spec from the plan",
    context="""
    ORIGINAL TASK SPEC:
    - Create src/models/user.py with User class
    - Fields: email (str), password_hash (str)
    - Use bcrypt for password hashing
    - Include __repr__

    CHECK:
    - [ ] All requirements from spec implemented?
    - [ ] File paths match spec?
    - [ ] Function signatures match spec?
    - [ ] Behavior matches expected?
    - [ ] Nothing extra added (no scope creep)?

    OUTPUT: PASS or list of specific spec gaps to fix.
    """,
    toolsets=['file']
)
```

**If spec issues found:** Fix gaps, then re-run spec review. Continue only when spec-compliant.

#### Step 3: Dispatch Code Quality Reviewer

After spec compliance passes:

```python
delegate_task(
    goal="Review code quality for Task 1 implementation",
    context="""
    FILES TO REVIEW:
    - src/models/user.py
    - tests/models/test_user.py

    CHECK:
    - [ ] Follows project conventions and style?
    - [ ] Proper error handling?
    - [ ] Clear variable/function names?
    - [ ] Adequate test coverage?
    - [ ] No obvious bugs or missed edge cases?
    - [ ] No security issues?

    OUTPUT FORMAT:
    - Critical Issues: [must fix before proceeding]
    - Important Issues: [should fix]
    - Minor Issues: [optional]
    - Verdict: APPROVED or REQUEST_CHANGES
    """,
    toolsets=['file']
)
```

**If quality issues found:** Fix issues, re-review. Continue only when approved.

#### Step 4: Mark Complete

```python
todo([{"id": "task-1", "content": "Create User model with email field", "status": "completed"}], merge=True)
```

### 3. Final Review

After ALL tasks are complete, dispatch a final integration reviewer:

```python
delegate_task(
    goal="Review the entire implementation for consistency and integration issues",
    context="""
    All tasks from the plan are complete. Review the full implementation:
    - Do all components work together?
    - Any inconsistencies between tasks?
    - All tests passing?
    - Ready for merge?
    """,
    toolsets=['terminal', 'file']
)
```

### 4. Verify and Commit

```bash
# Run full test suite
pytest tests/ -q

# Review all changes
git diff --stat

# Final commit if needed
git add -A && git commit -m "feat: complete [feature name] implementation"
```

## Task Granularity

**Each task = 2-5 minutes of focused work.**

**Too big:**
- "Implement user authentication system"

**Right size:**
- "Create User model with email and password fields"
- "Add password hashing function"
- "Create login endpoint"
- "Add JWT token generation"
- "Create registration endpoint"

## Red Flags — Never Do These

- Start implementation without a plan
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed critical/important issues
- Dispatch multiple implementation subagents for tasks that touch the same files
- Make subagent read the plan file (provide full text in context instead)
- Skip scene-setting context (subagent needs to understand where the task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues → implementer fixes → review again)
- Let implementer self-review replace actual review (both are needed)
- **Start code quality review before spec compliance is PASS** (wrong order)
- Move to next task while either review has open issues

## Handling Issues

### If Subagent Asks Questions

- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

### If Reviewer Finds Issues

- Implementer subagent (or a new one) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

### If Subagent Fails a Task

- Dispatch a new fix subagent with specific instructions about what went wrong
- Don't try to fix manually in the controller session (context pollution)

## Efficiency Notes

**Why fresh subagent per task:**
- Prevents context pollution from accumulated state
- Each subagent gets clean, focused context
- No confusion from prior tasks' code or reasoning

**Why two-stage review:**
- Spec review catches under/over-building early
- Quality review ensures the implementation is well-built
- Catches issues before they compound across tasks

**Cost trade-off:**
- More subagent invocations (implementer + 2 reviewers per task)
- But catches issues early (cheaper than debugging compounded problems later)

## Integration with Other Skills

### With writing-plans

This skill EXECUTES plans created by the writing-plans skill:
1. User requirements → writing-plans → implementation plan
2. Implementation plan → subagent-driven-development → working code

### With test-driven-development

**Strongly recommended:** Load the `code-assist` skill (from `strands-skills-generated/`) when dispatching implementer subagents. It provides the full Explore → Plan → Code → Commit TDD workflow with interactive mode.

When using code-assist, format acceptance criteria as Given-When-Then:

```python
# In implementer context, replace vague specs with GWT:
#
# BEFORE:
# "Create User model with email field"
#
# AFTER:
"""
## Task T-001: Create User model
Given: The project uses Python 3.11 with an existing src/models/ directory
When: I create the User model class
Then:
  - email field accepts valid email strings
  - password_hash field stores bcrypt hashes (60 chars)
  - __repr__ returns f"<User {email}>"
  - Model is importable from src.models.user
"""
```

Include the GWT format in EVERY implementer dispatch. Subagents using code-assist will use it for TDD test design. Subagents not using code-assist will still have clearer acceptance criteria to verify against.

### With persistent-subagent

**Before dispatching any subagent,** load the `persistent-subagent` skill and follow its identity injection protocol:

1. **Read identity config** — for coding tasks, read `~/.hermes/agents/coder.yaml`:
   ```python
   identity_config = read_file("~/.hermes/agents/coder.yaml")
   # Inject identity_config['persona'] into context
   ```

2. **Build context with identity** — combine persona + task + GWT criteria into one context block

3. **After subagent completes** — parse output for `[TO_MEMORY]` blocks and call memory tool to persist learnings

**CODEASSIST.md pre-discovery** (run before every implementer dispatch):
```
find . -maxdepth 3 -type f \
  \( -path "*/node_modules/*" -o -path "*/build/*" -o -path "*/.venv/*" -o -path "*/venv/*" \
  -o -path "*/__pycache__/*" -o -path "*/.git/*" -o -path "*/dist/*" -o -path "*/target/*" \) -prune -o \
  -name "*.md" -print | grep -iE "(CODEASSIST|DEVELOPMENT|SETUP|BUILD|CONTRIBUTING|ARCHITECTURE|TESTING|DEPLOYMENT|TROUBLESHOOTING|README)" | head -10
```
If CODEASSIST.md is found, inject its constraints into the subagent context.

**Scratchpad artifact structure** (for implementer subagent using code-assist):
```
{documentation_dir}/{task_name}/
├── context.md      # Project structure, requirements, patterns, implementation paths
├── plan.md         # Test scenarios, Given-When-Then acceptance criteria, implementation steps
├── progress.md     # TDD cycle log (RED/GREEN/REFACTOR per cycle), checklist, commit hash
└── logs/           # Build output logs (piped: [cmd] > logs/build.log 2>&1)
```
All documentation stays in scratchpad. All actual code lives in `repo_root`. Never mix them.

### With requesting-code-review

The two-stage review process IS the code review. For final integration review, use the requesting-code-review skill's review dimensions.

### With systematic-debugging

If a subagent encounters bugs during implementation:
1. Follow systematic-debugging process
2. Find root cause before fixing
3. Write regression test
4. Resume implementation

## Example Workflow

```
[Read plan: docs/plans/auth-feature.md]
[Create todo list with 5 tasks]

--- Task 1: Create User model ---
[Dispatch implementer subagent]
  Implementer: "Should email be unique?"
  You: "Yes, email must be unique"
  Implementer: Implemented, 3/3 tests passing, committed.

[Dispatch spec reviewer]
  Spec reviewer: ✅ PASS — all requirements met

[Dispatch quality reviewer]
  Quality reviewer: ✅ APPROVED — clean code, good tests

[Mark Task 1 complete]

--- Task 2: Password hashing ---
[Dispatch implementer subagent]
  Implementer: No questions, implemented, 5/5 tests passing.

[Dispatch spec reviewer]
  Spec reviewer: ❌ Missing: password strength validation (spec says "min 8 chars")

[Implementer fixes]
  Implementer: Added validation, 7/7 tests passing.

[Dispatch spec reviewer again]
  Spec reviewer: ✅ PASS

[Dispatch quality reviewer]
  Quality reviewer: Important: Magic number 8, extract to constant
  Implementer: Extracted MIN_PASSWORD_LENGTH constant
  Quality reviewer: ✅ APPROVED

[Mark Task 2 complete]

... (continue for all tasks)

[After all tasks: dispatch final integration reviewer]
[Run full test suite: all passing]
[Done!]
```

### Configuration Parameters for Subagents

Three key delegation parameters in `config.yaml` under `delegation:`:

| 參數 | 預設值 | 最小 | 最大 | 說明 |
|------|--------|------|------|------|
| `max_concurrent_children` | 3 | 1 | 無硬性上限（>10 有 cost warning） | 同時最多幾個 sub-agent |
| `max_spawn_depth` | 1 | — | — | sub-agent 能否再叫 sub-agent（目前不允許） |
| `child_timeout_seconds` | 600 | 30 | 無上限 | 每個 sub-agent 的超時時間（秒） |

**實際限制建議（N100, 4 cores, 31GB RAM）**：
- `max_concurrent_children`: 5-6 是兼顧穩定和效能的安全值
- 超過 8 可能開始變慢
- 20+ 不建議

**超時後的行為**：
- sub-agent 被標記為「timeout」，主體收到超時結果
- 如果 sub-agent 連第一次 API 呼叫都沒發出去（0 API calls），會產生診斷報告
- 可選擇重試、放棄、或做其他處理

**設定方式**：
```bash
hermes config set delegation.max_concurrent_children 8
hermes config set delegation.max_spawn_depth 1  # 維持不變
hermes config set delegation.child_timeout_seconds 600
```

---

## Remember

```
Fresh subagent per task
Two-stage review every time
Spec compliance FIRST
Code quality SECOND
Never skip reviews
Catch issues early
```

**Quality is not an accident. It's the result of systematic process.**

## Subagent Output Finality

**Important:** In Hermes, subagent output IS the final deliverable. The main agent does NOT re-reason, re-summarize, or re-format it. This means:

- If you want formatting or structure, the subagent must do it
- Don't write prompts that say "the main agent will process this" — the subagent's output is what gets delivered
- The ONE exception: `[TO_MEMORY]` blocks at the top of subagent output get parsed by the main agent and written to memory
- See `metacognitive-learner/references/subagent-communication.md` for the full communication protocol

## Model Selection: M3 vs M2.7 Sub-Agents (2026-06-12 實驗結論)

**Critical finding:** `delegate_task` 派出的 sub-agent **預設 model = M2.7**(不是 M3,即便常駐 profile 是 M3)。M2.7 跟 M3 在「派遣寫 code」任務上的表現**有顯著差異**,改變了「該不該派遣」的策略。

### 4 個關鍵差異(實驗驗證,Todo App 5 round 對比)

| 維度 | M2.7 sub-agent | M3 sub-agent |
|------|---------------|--------------|
| 讀 reverse-arch 後推測 export 形式 | named function 跟 default 物件**隨機選** | **準確推測物件形式** |
| 推測 import 形式 | 跟其他 ticket 寫的 export 形式**容易不一致** | **跟其他 ticket 對齊** |
| 推測函式簽名 | 容易漏參數 / 加多餘參數 / 忘 `\| null` | **比較準** |
| 整合修正次數(粗糙 ticket) | **2 個大問題**(export 形式不一致) | **1 個小問題**(1 個 catch lint) |
| 整合修正次數(改進 ticket + 6 條 coding 規範) | 2 個小問題(函式簽名) | **0 個問題** |
| 派遣總時間 vs 單獨寫 | 派遣 180-200s 跟單獨寫 161s 差不多、但要修 30-90s 整合 | **派遣 180s 跟單獨寫 161s 差不多、零整合** |

### 怎麼把 sub-agent 升級成 M3(2026-06-12 workaround)

**問題**: `delegate_task` 工具 schema 沒有 `model` 參數,傳進去會被忽略。

**解法**: 不要用 `delegate_task`,改用 `terminal(background=true)` 直接跑 `hermes chat -m MiniMax-M3`:

```bash
# 1. 寫 prompt 到永久位置(/tmp 不可靠,會被系統清)
mkdir -p /path/to/exp/prompts
cat > /path/to/exp/prompts/t1.txt << 'EOF'
你是 sub-agent,負責 X 任務
(reverse-arch 規格、coding 規範、驗證步驟)
EOF

# 2. 平行 background 啟動
terminal(background=true, command="hermes chat -m MiniMax-M3 -q \"$(cat /path/to/exp/prompts/t1.txt)\" --cli --quiet --yolo --accept-hooks", timeout=600, notify_on_complete=true)
terminal(background=true, command="hermes chat -m MiniMax-M3 -q \"$(cat /path/to/exp/prompts/t2.txt)\" --cli --quiet --yolo --accept-hooks", timeout=600, notify_on_complete=true)
terminal(background=true, command="hermes chat -m MiniMax-M3 -q \"$(cat /path/to/exp/prompts/t3.txt)\" --cli --quiet --yolo --accept-hooks", timeout=600, notify_on_complete=true)

# 3. 主動 ls 監聽(不依賴 notify,延遲 10-18 分鐘常態)
# 4. 整合驗證:build + typecheck + lint
```

**為什麼需要 `--yolo --accept-hooks`**:M3 sub-agent 第一次跑會卡在「dangerous command approval prompt」(headless 沒 TTY),這兩個 flag 跳過。

**為什麼要 redirect `2>&1 >` 而不是 `| tee`**:`tee` 接管 stdin,會跟 `hermes chat -q` 的 prompt 衝突 → 「Input is not a terminal」→ Goodbye。**用 redirect 寫檔、不用 tee**:
```bash
# ✅ 安全
hermes chat -m MiniMax-M3 -q "$PROMPT" --cli --quiet --yolo --accept-hooks 2>&1 > worker.log

# ❌ 危險
hermes chat -m MiniMax-M3 -q "$PROMPT" --cli --quiet --yolo --accept-hooks 2>&1 | tee worker.log
# → tee 搶 stdin → hermes chat 收不到 prompt → Goodbye
```

### 何時該派遣、何時該單獨寫(決策表)

| 任務規模 | Model | 推薦 | 理由 |
|---------|-------|------|------|
| **S 型**(1 ticket, 1 個檔) | 任何 | **單獨寫** | 派遣 overhead 反而比任務本身大 |
| **M 型**(2-3 ticket) | **M3** | **派遣 sub-agent** | 平行 180s 跟單獨寫 161s 差不多、零整合、省主 session context |
| **M 型** | **M2.7** | **單獨寫** | 派遣要 60-90s 整合、反而更慢 |
| **L 型**(5+ ticket) | 任何 | **派遣 sub-agent** | 自己寫 context 會爆(108K 實證過) |
| **不確定** | 任何 | **M3 + 派遣 + 改進 ticket** | 最保險 |

**M3 時代改變了一切**:
- 舊結論(M2.7 時代):「派遣整合成本太高、不推薦」
- 新結論(M3 時代):「派遣跟單獨寫一樣快、但省主 session context、推薦」

### Ticket 黃金內容(5 項,派遣必含)

不管用 M2.7 還是 M3,寫 ticket 必含這 5 項才能避免整合災難:

1. **reverse-arch 完整規格**(全文路徑 + 對應視角章節)
2. **具體 export 形式**(`export const db = {...}` 物件 vs `export function list()` named)
3. **具體 import 形式**(`import { db } from "@/lib/db"` named vs `import db from` default)
4. **具體函式簽名**(`list(filter: FilterType = "all"): Todo[]`)
5. **風格約束**(雙引號 / catch (e) / TypeScript 嚴格 / 命名)

**If** ticket 只寫「請寫 lib/db.ts」沒具體 export 形式 **Then** M2.7 一定會猜錯、M3 也可能猜錯
**If** 派遣後整合時間 > 30 秒 **Then** ticket 寫得不夠具體、改進後重派

## Further reading (load when relevant)

When the orchestration involves significant context usage, long review loops, or complex validation checkpoints, load these references for the specific discipline:

- **`references/context-budget-discipline.md`** — Four-tier context degradation model (PEAK / GOOD / DEGRADING / POOR), read-depth rules that scale with context window size, and early warning signs of silent degradation. Load when a run will clearly consume significant context (multi-phase plans, many subagents, large artifacts).
- **`references/gates-taxonomy.md`** — The four canonical gate types (Pre-flight, Revision, Escalation, Abort) with behavior, recovery, and examples. Load when designing or reviewing any workflow that has validation checkpoints — use the vocabulary explicitly so each gate has defined entry, failure behavior, and resumption rules.
- **`references/todo-app-quality-experiment.md`** — 2026-06-11~12 跑的 Todo App 5-Round 對比實驗完整資料(單獨寫 vs 派遣 M2.7 vs 派遣 M3,含 5 個環境陷阱 / 5 個關鍵發現 / 派遣決策表)。**Load when deciding 「這個任務該單獨寫還是派遣 sub-agent?」** 必看,涵蓋 SKILL.md「Model Selection」段的完整數據 + 實驗中踩到的 5 個環境陷阱(`/tmp` 不可靠、`tee` 跟 `hermes chat` 衝突、`terminal(background=true)` silent fail、`execute_code` 5min timeout、redirect 順序)。

Both references adapted from gsd-build/get-shit-done (MIT © 2025 Lex Christopherson).
