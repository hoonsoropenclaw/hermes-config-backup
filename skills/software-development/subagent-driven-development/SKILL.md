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

## Further reading (load when relevant)

When the orchestration involves significant context usage, long review loops, or complex validation checkpoints, load these references for the specific discipline:

- **`references/context-budget-discipline.md`** — Four-tier context degradation model (PEAK / GOOD / DEGRADING / POOR), read-depth rules that scale with context window size, and early warning signs of silent degradation. Load when a run will clearly consume significant context (multi-phase plans, many subagents, large artifacts).
- **`references/gates-taxonomy.md`** — The four canonical gate types (Pre-flight, Revision, Escalation, Abort) with behavior, recovery, and examples. Load when designing or reviewing any workflow that has validation checkpoints — use the vocabulary explicitly so each gate has defined entry, failure behavior, and resumption rules.

Both references adapted from gsd-build/get-shit-done (MIT © 2025 Lex Christopherson).
