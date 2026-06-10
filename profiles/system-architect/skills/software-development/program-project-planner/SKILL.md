---
name: program-project-planner
description: "Use when a user presents a vague idea and requests a rigorous 4-state project planning workflow: benchmark reverse-engineering, requirements convergence, architecture design, and execution handoff. Produces 4 formal documents before any implementation begins."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, architecture, reverse-engineering, requirements, handoff, workflow]
    related_skills: [writing-plans, subagent-driven-development, systematic-debugging, pdd, code-assist, code-task-generator]

**Related skills (strands-agents-sops ecosystem):**
- **`code-assist`** (strands-skills-generated) — 補 TDD 內核。當 implementer subagent 被派遣時，載入此技能：Explore → Plan → TDD 實現 → Commit。每個 micro-task 應遵循此流程。
- **`persistent-subagent`** — 身份配置框架。派遣前自動讀取 `~/.hermes/agents/<role>.yaml` 注入 persona，subagent 輸出中的 `[TO_MEMORY]` 區塊自動回收至記憶系統。
- **`pdd`**, **`code-task-generator`** — 前後銜接：pdd 產生 plan，code-task-generator 將 plan 轉為 `.code-task.md` 檔案。
---

# Program Project Planner (程式專案規劃師)

## Overview

Transform a user's vague idea into an actionable, peer-reviewed system architecture blueprint — without writing any implementation code. This skill enforces a strict 4-state pipeline; each state must complete and receive user confirmation before advancing.

**Core principle:** No speculation, no code, no architecture without evidence. Every claim comes from web research or existing artifacts.

## When to Use

**Trigger conditions (any one):**
- User says "帮我规划" / "请先规划" / "先做需求分析"
- User describes a system they want to build without technical details
- User references an existing product/app/workflow and asks "能不能做一样的"
- User's request is ambiguous, high-level, or spans multiple components
- **THIS USER SPECIFIC OVERRIDE (hoonsor):** Request is ANY new project, feature, or non-trivial task — regardless of clarity level — UNLESS user explicitly writes "直接實作" or "直接做"

**Do NOT use when:**
- User explicitly says "直接實作" or "直接做" (direct implementation explicitly requested)
- Task is a single, simple, well-defined action (e.g., "帮我把这个文件重命名", "帮我查一下天气")
- User demands immediate implementation (skip planning only when explicitly stated)
- Emergency hotfix scenario

**User profile note:** This user (hoonsor) prefers detailed specification documents and confirmation **before** any implementation begins. Always produce all 4 documents and await confirmation. This user's default mode is planning — do not initiate implementation without going through the 4-state pipeline unless explicitly asked to skip it with "直接實作".

## The 4-State Pipeline (強制狀態機)

```
State 1: Benchmark & Deconstruction
  ↓ [01-Benchmark.md produced]
  
State 2: Ontology & PRD
  ├─ Step 2a: 用戶選擇起點（需求澄清 / 研究 / 提供上下文）
  ├─ Step 2b: 互動式需求澄清（一次一題，Q&A 記錄到 idea-honing.md）
  └─ Step 2c: Iteration Checkpoint（可來回 Clarify ↔ Research）
  ↓ [02-PRD.md produced]
  
State 3: Durable Architecture
  └─ 研究階段每個 topic 完成後主動暫停確認方向
  ↓ [03-Architecture.md produced]
  
State 4: Execution Handoff
  ↓ [04-Execution_Plan.md produced + user confirms]
  → THEN: dispatch subagents via subagent-driven-development
         每個 micro-task 可附上 Given-When-Then acceptance criteria
         建議搭配 code-assist 技能的 TDD workflow 執行
```

**The Iron Rule:** No code, no subagent dispatch, and no architecture diagrams until all 4 documents exist and the user has confirmed them.

---

## State 1: Benchmark & Deconstruction (標竿逆向工程)

**Objective:** Research 3 top-tier references in the problem domain. Extract core data structures, high-value features, and architectural patterns.

**Required actions:**

1. **Web search for top references:**
   ```
   Search: "<domain> best open source projects" OR "<domain> n8n workflow templates" OR "<domain> top SaaS features"
   Limit: 5 results per query
   ```

2. **For each reference, extract:**
   - Core data structures (as JSON Schema)
   - Key API endpoints and their contracts
   - Database schema patterns (if observable)
   - High-value feature list
   - Docker/deployment patterns (if open source)

3. **Document findings in `01-Benchmark.md`:**

````markdown
# Benchmark Report: [Project/Product Name]

## Reference 1: [Name] ([URL])
### Core Data Structures
```json
{
  "entity_name": {
    "type": "object",
    "properties": {
      "field": { "type": "string", "description": "..." }
    }
  }
}
```
### Key API Endpoints
| Method | Endpoint | Payload | Response |
|--------|----------|---------|----------|
| GET | /api/resource | — | { data: [...] } |

### High-Value Features
1. Feature A
2. Feature B

### Docker/Deployment Notes
- Base image: ...
- Environment variables: ...
- Volume mounts: ...

---

## Reference 2: [Name] ([URL])
[Same structure]

## Cross-Cutting Patterns
- All references use X for auth
- All references share Y data model pattern
- Common feature set: [...]
````

**Output:** `01-Benchmark.md` in a new project folder (`~/.hermes/projects/<project-name>/` or user-specified path).

---

## State 2: Ontology & PRD (系統邊界與需求收斂)

**Objective:** Based on State 1 findings, define **our** system boundary, user stories, and explicit out-of-scope items.

**Reference:** This state draws from the PDD (Prompt-Driven Development) SOP's requirements clarification pattern.
**Key principle: ONE question at a time. Record answer immediately. Never batch-ask.**

**Required document:** `02-PRD.md` + `idea-honing.md`（PDD 風格 Q&A 記錄）

**PDD-Style Process (replace the old State 2 template):**

### 2a. Initial Process Planning — 讓用戶選擇起點

Ask the user ONE question before proceeding:

> *「在開始之前，您希望從哪裡著手？」
>  A) 先做需求澄清（預設）— 我會問您一系列問題來收斂需求
>  B) 先做前期研究 — 您有一些特定技術想先研究
>  C) 直接提供上下文 — 您有現成的文件/链接想直接給我參考」*

Adapt subsequent process based on user's choice.

### 2b. Requirements Clarification — 互動式 Q&A（一次一題）

**CRITICAL: One question at a time. Do NOT batch-ask.**

1. Formulate ONE question based on the design read and benchmark findings
2. Append the question to `idea-honing.md` in the project folder
3. Present the question to the user in the conversation
4. Wait for the user's complete response
5. Once received, append the user's answer to `idea-honing.md`
6. THEN formulate the next question

**What to ask about (cycle through these systematically):**
- Core functionality (what must the system do?)
- User roles and access levels
- Edge cases and error handling expectations
- Success criteria and measurable outcomes
- Technical constraints (stack preferences, existing systems)
- Non-functional requirements (performance, security, scale)
- Out-of-scope items (what should this NOT do?)

**Rules:**
- MUST NOT list multiple questions at once
- MUST NOT pre-populate answers without user input
- MAY suggest options when user is unsure
- MUST continue until requirements appear complete
- MUST explicitly ask: *"需求澄清是否完成？還有其他要补充的吗？"*

### 2c. Research Integration

Identify areas where research would benefit the design:
- Technology choices with trade-offs
- Existing solutions analysis
- Alternative approaches considered
- Key constraints discovered

For each research topic, create a note in `{project_dir}/research/` and periodically share preliminary findings with the user for feedback.

### 2d. Iteration Checkpoint

Summarize current state of requirements and research. Ask user:
> *「需求和研究的現狀如下。您想：
>  A) 繼續到詳細設計（Step 3）
>  B) 回到需求澄清繼續補充
>  C) 做更多研究」*

### 2e. Detailed Design Document

Create `{project_dir}/design/detailed-design.md` with:
- Overview
- Consolidated Requirements (from idea-honing.md)
- Architecture Overview
- Components and Interfaces
- Data Models
- Error Handling
- Testing Strategy
- Appendices (Technology Choices, Research Findings, Alternative Approaches)

Use Mermaid diagrams for architecture, data flow, and component relationships.

**Output:** `02-PRD.md` + `idea-honing.md` in the project folder (`~/.hermes/projects/<project-name>/`).

````markdown
# Product Requirements Document: [Project Name]

## 1. Overview
[Brief description of what we're building, derived from user's request]

## 2. User Stories

| ID | As a... | I want to... | So that... | Acceptance Criteria |
|----|---------|--------------|------------|---------------------|
| US-001 | [Role] | [Action] | [Outcome] | [Measurable test condition] |
| US-002 | ... | ... | ... | ... |

## 3. Functional Requirements

### FR-001: [Feature Name]
**Description:** ...
**Input:** ...
**Output:** ...
**Edge Cases:** ...

### FR-002: [Feature Name]
[Same structure]

## 4. Non-Functional Requirements
- Performance: ...
- Reliability: ...
- Scalability: ...

## 5. Out of Scope (必須填寫 — 至少3項)
1. **Not doing:** [Feature/functionality] — reason why
2. **Not doing:** [Feature/functionality] — reason why
3. **Not doing:** [Feature/functionality] — reason why

## 6. Assumptions & Constraints
- Assumes: ...
- Constrained by: ...
- Rate limits observed: [API name] allows X req/min
- Retry strategy: exponential backoff, max Y attempts
````

---

## State 3: Durable Architecture (堅固的系統架構圖)

**Objective:** Define every node, data flow, Docker networking, environment variables, and disaster recovery fallback.

**Required document:** `03-Architecture.md`

**Structure:**

````markdown
# Architecture Document: [Project Name]

## 1. System Overview
[2-3 sentence description of the system architecture]

## 2. Component Diagram

```mermaid
graph TB
    subgraph Docker Network ["Docker Network: project_network"]
        A[API Gateway<br/>Port: 3000] --> B[Service A<br/>Node: app-a]
        A --> C[Service B<br/>Node: app-b]
        B --> D[(Database<br/>PostgreSQL)]
        C --> E[(Cache<br/>Redis)]
    end

    Ext[External APIs] --> A
    B --> Ext
    C --> Ext
```

## 3. Data Flow Schema

```mermaid
graph LR
    User[User Request] --> APIGateway
    APIGateway --> Validator[Input Validation]
    Validator --> Processor[Business Logic]
    Processor --> DB[(Database)]
    Processor --> Cache[(Redis Cache)]
    Cache -.-> Processor
```

## 4. Database Schema (ER Diagram)

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    USER {
        uuid id PK
        string email
        string password_hash
        timestamp created_at
    }
    ORDER {
        uuid id PK
        uuid user_id FK
        decimal total_amount
        string status
        timestamp created_at
    }
```

## 5. API Specification

### Endpoint: POST /api/resource
**Description:** ...
**Auth:** Bearer token
**Rate Limit:** 60 req/min

**Request:**
```json
{
  "field": "string (required, max 255 chars)"
}
```

**Response (200):**
```json
{
  "data": { "id": "uuid", "field": "value" },
  "meta": { "request_id": "string" }
}
```

**Response (400):**
```json
{
  "error": { "code": "VALIDATION_ERROR", "message": "..." }
}
```

**Response (429):**
```json
{
  "error": { "code": "RATE_LIMITED", "retry_after": 60 }
}
```

## 6. Docker Configuration

### docker-compose.yml
```yaml
version: '3.8'
services:
  api:
    build: ./api
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build: ./worker
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

## 7. Environment Variables

| Variable | Description | Example | Source |
|----------|-------------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:***@host:5432/db` | User-provided |
| `REDIS_URL` | Redis connection string | `redis://host:6379` | User-provided |
| `API_KEY_*` | External API keys | `sk-...` | User-provided |

## 8. Disaster Recovery & Fallback

### Node Failure Handling
| Component | Fallback Strategy |
|-----------|------------------|
| API Gateway | Health check → remove from LB pool |
| Database | Read replica promotion, WAL replay |
| Redis Cache | Graceful degradation → bypass cache |
| External API | Circuit breaker (Polly), fallback to cached response |
| Worker | Job re-queue with exponential backoff |

### Retry Policy
```python
RETRY_CONFIG = {
    "max_attempts": 3,
    "base_delay": 2,      # seconds
    "max_delay": 60,     # seconds
    "exponential_base": 2
}
```

### Data Persistence
- All persistent data mounted as named Docker volumes
- Volume backup: daily cron at 03:00 UTC
- Backup retention: 7 days

---

## State 4: Execution Handoff (實作工單派發)

**Objective:** Break the PRD and architecture into **micro-tasks** that are independently testable. One task = one subagent dispatch unit.

**Required document:** `04-Execution_Plan.md`

**Structure:**

````markdown
# Execution Plan: [Project Name]

> **For Hermes:** Use subagent-driven-development skill to dispatch subagents per task below.

## Project Info
- **Total Tasks:** T-001 to T-00N
- **Execution Mode:** Sequential (tasks are dependent), unless marked PARALLELIZABLE
- **Prerequisite:** All 4 planning documents confirmed by user

---

## Task T-001: [Task Name]

**Module:** [e.g., Infrastructure / API / Worker / Frontend]
**Estimated Time:** 2-5 minutes
**Files:**
- Create: `path/to/file.py`
- Modify: `path/to/existing.py`
- Test: `tests/path/to/test_file.py`

**Verification:**
```bash
pytest tests/path/to/test_file.py::test_feature_x -v
# Expected: PASS
```

**Dependencies:** T-000 (must complete before this starts)

---

## Task T-002: [Task Name]
[Same structure]

## PARALLELIZABLE TASKS
The following tasks have NO interdependencies and MAY be dispatched in parallel:
- T-003, T-004, T-005

## Critical Path (Sequential Order)
T-001 → T-002 → T-003 → ... → T-00N

---

## Handoff Trigger

**After user confirmation of all 4 documents:**

Dispatch to `subagent-driven-development` skill with this plan. Per task workflow:
1. Dispatch implementer subagent (recommend loading `code-assist` skill for TDD workflow)
2. Spec compliance review
3. Code quality review
4. Mark complete

**Recommended micro-task format:** Attach Given-When-Then acceptance criteria to each task:
```
## Task T-001: [Task Name]
Given: [precondition]
When: [action]
Then: [expected outcome]
```

Only after ALL tasks complete and all reviews pass → notify user for final integration review.
````

---

## Output Folder Structure

```
~/.hermes/projects/<project-name>/
├── 01-Benchmark.md           # State 1: 3 reference analyses
├── 02-PRD.md                # State 2: Requirements summary
├── idea-honing.md           # State 2: PDD-style Q&A log (one question at a time)
├── research/                # State 2c: Per-topic research notes
│   ├── existing-solutions.md
│   ├── technology-choices.md
│   └── constraints.md
├── design/
│   └── detailed-design.md   # State 2e: Mermaid architecture diagrams
├── 03-Architecture.md       # State 3: System architecture + Docker config
└── 04-Execution_Plan.md      # State 4: Micro-tasks with Given-When-Then criteria

# PDD SOP directory convention (alternative, supported):
.agents/planning/<project-name>/
  ← same structure, PDD-compatible naming
```

---

## Common Pitfalls

### 1. Skipping States
**Symptom:** User gets a partial plan or direct code.
**Fix:** Always produce all 4 documents in order. Do not skip.

### 2. Writing Code in States 1-3
**Symptom:** Implementation details appear in benchmark, PRD, or architecture docs.
**Fix:** These documents describe WHAT and WHY, not HOW. Implementation = State 4 + subagent phase.

### 3. Missing Out of Scope
**Symptom:** Project scope creep; user expects features not built.
**Fix:** State 2 MUST include at least 3 explicit "Out of Scope" items.

### 4. Skipping Rate Limit / Retry Considerations
**Symptom:** Implementation hits API limits, crashes in production.
**Fix:** Always document rate limits from benchmark research. Include retry policies in architecture.

### 5. Tasks Too Large
**Symptom:** T-001 = "Build entire auth system" (not testable in 5 min).
**Fix:** Split into micro-tasks: model → migration → endpoint → test → commit.

### 6. User Confirmed but Documents Incomplete
**Symptom:** User says "go ahead" but you haven't finished all 4 documents.
**Fix:** List what's missing. Do not proceed until all 4 exist.

### 7. Supabase Key Type Mismatch
**Symptom:** Management API (creating tables via `/v1/projects/{ref}/database/query`) returns 403. The `api.supabase.com/v1/` management endpoints require a **Personal Access Token (PAT)**, NOT a service role key (`sb_secret_...`).
**Fix:** Two paths:
- **Preferred for automation:** Get a PAT from Supabase Dashboard → Account → Access Tokens (format `sbp_xxxxxxxxxxxx`). Use this for all management API calls.
- **Manual fallback:** Ask the user to paste SQL into Supabase Dashboard → SQL Editor. This bypasses the PAT requirement entirely.
- **DO NOT assume `sb_secret_` key works for management API.** Service role keys only work for the REST API (`supabase.co/rest/v1/`), not management API (`api.supabase.com/v1/`).

**Verification after table creation:**
```bash
# Test REST API access (sb_secret_ key works here)
curl "{SUPABASE_URL}/rest/v1/works" \
  -H "apikey: {sb_secret_}" \
  -H "Authorization: Bearer {sb_secret_}"
# Expected: [] (empty, tables exist) not 404

# Test management API (needs PAT)
curl -X POST "https://api.supabase.com/v1/projects/{ref}/database/query" \
  -H "Authorization: Bearer {PAT}" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1"}'
# Expected: {"response": null} not 403
```

### 8. Missing Supabase Project URL
**Symptom:** User provides only the service role key (`sb_secret_...`) without the Project URL.
**Fix:** Ask for Project URL from Supabase Dashboard → Settings → General → "Project URL". URL format is `https://{ref}.supabase.co`. You cannot reconstruct it from the key alone.

### 9. Skipping Database Setup Before Implementation
**Symptom:** Planning documents describe a Supabase schema, but T-001 (database creation) is treated as trivial or skipped.
**Fix:** Database schema setup is non-trivial for Supabase — requires PAT + management API OR user manually running SQL in dashboard. Treat it as a dedicated task with its own verification step. Never assume tables can be created without explicit credential or user action.

### 10. Schema-Doc Drift: Adding Fields to Planning Docs Without Syncing SQL
**Symptom:** During PRD/Architecture update (e.g., adding `skill_used` column), the planning documents are updated but the actual database table doesn't have the new column. User runs the original SQL before the field was added to the planning docs, so the column is missing.
**Fix:** When updating planning docs with a new field:
  1. Update all 3 docs (PRD → Architecture → Execution Plan) in one pass
  2. Immediately provide the `ALTER TABLE` SQL the user must run to add the new column to the existing table
  3. Do NOT proceed to implementation until the column actually exists in the database (verify with INSERT test)
  4. Plan for this: any schema evolution AFTER initial table creation requires a migration step, not just a new SQL block

### 11. Wrong Tool for Management API
**Symptom:** Testing multiple keys (`sb_secret_`, `sb_publishable_`) against `api.supabase.com/v1/` management endpoints — all return 403. Agent keeps trying different keys instead of recognizing the fundamental issue.
**Fix:** The management API (`api.supabase.com`) is account-scope, NOT project-scope. It requires a **Personal Access Token (PAT, format `sbp_...`)** from Account → Access Tokens. Service role keys (`sb_secret_`) only work for project-rest API (`*.supabase.co/rest/v1/`). If PAT also returns 403, the account itself lacks management API permission — stop trying keys, use Supabase Dashboard SQL Editor instead.
**Recognition signal:** If you've tried 2+ keys and all return 403 on the same endpoint, you're in this pitfall. Switch approach immediately.

### 12. Iterative Schema Evolution Mid-Planning
**Symptom:** User adds new fields to PRD during planning (e.g., `skill_used` to works, `score_design/score_practical` to evaluations). Planning docs get updated but database schema doesn't match — user must run ALTER TABLE separately.
**Fix:** When updating planning docs with a new field:
  1. Update all docs in one pass (PRD → Architecture → Execution Plan → Benchmark)
  2. Provide the `ALTER TABLE` SQL immediately — user runs it in SQL Editor
  3. Verify the column exists BEFORE treating the schema as complete (INSERT test with new field)
  4. Clean up test records after verification

### 13. User Acts as Database Admin for Schema Changes
**Symptom:** User executes SQL in Supabase Dashboard SQL Editor himself. Agent waits for confirmation then continues. This is the expected pattern for this user — he is comfortable running DDL himself.
**Fix:** When planning involves schema changes AFTER initial table creation:
  1. Provide the exact SQL to run
  2. Wait for user confirmation ("done")
  3. Verify with INSERT + SELECT test
  4. Clean up test records
  5. Continue planning/implementation
  Do NOT attempt to create tables via Management API when user can run SQL directly.

### 14. User Specifies Detailed Requirements Mid-Planning
**Symptom:** User provides specific details during planning that override or extend the default structure (e.g., "評分改為1~10", "評分面向改成設計感/實用性"). This is direct requirement input, not a vague idea.
**Fix:** This is NOT a violation of the planning-first rule — it's a refinement phase. User is actively participating in shaping the PRD/Architecture. Accept these as State 2 refinements, update all affected docs, and continue. Do not treat it as scope creep or ask "are you sure." The user knows what he wants.

### 15. Two-Score Evaluation System (設計感 + 實用性)
**Symptom:** User requests a multi-dimensional scoring system (e.g., design and practicality, each 1-10) rather than a single score. The evaluation table schema and all related API specs need to reflect both dimensions.
**Fix:** When evaluation scoring expands to multiple dimensions:
  1. Update `evaluations` table schema in all docs (Benchmark, Architecture)
  2. Update API request/response schemas (POST evaluation, GET sync)
  3. Provide ALTER TABLE for existing DB (drop old single score column, add two new columns)
  4. Verify both columns work with INSERT test
  5. Document dimension metadata in PRD (dimension key, label, min, max)
  6. Plan for future dimension expansion — store dimension definitions in config/code, not hardcoded

---

## Verification Checklist

Before triggering subagent dispatch, confirm:

- [ ] `01-Benchmark.md` exists — 3 references researched, data structures extracted
- [ ] `02-PRD.md` exists — user stories with acceptance criteria, ≥3 out-of-scope items
- [ ] `03-Architecture.md` exists — Mermaid diagrams, API specs, Docker config, fallback strategy
- [ ] `04-Execution_Plan.md` exists — micro-tasks T-001 to T-00N, each ≤5 min work
- [ ] User has explicitly confirmed all 4 documents
- [ ] Project folder created at `~/.hermes/projects/<project-name>/`
- [ ] Related skills (`writing-plans`, `subagent-driven-development`) are loaded

---

## Interaction with Writing Plans

This skill is **upstream** of `writing-plans`. The 4-state pipeline produces a full project blueprint. The `writing-plans` skill then converts individual features/tasks from the blueprint into implementable, TDD-driven task specs.

**Pipeline:**
```
program-project-planner (blueprint)
    ↓ produces 4 documents
writing-plans (per-feature specs)
    ↓ produces feature plan
subagent-driven-development (implementation)
```

**This skill does NOT produce TDD-driven implementation plans.** That is the job of `writing-plans` and `subagent-driven-development`.

---

## Remember

```
No research → no architecture
No architecture → no plan
No plan → no code
No out-of-scope → no scope control
No user confirmation → no dispatch
```

**Strict sequential enforcement is not optional.**