# Delegation Patterns & Sub-Agent Architecture Foundations

**Source**: Fast.io (AI Agent Delegation Patterns, 2026) + Epsilla Blog (3 Essential Sub-Agent Patterns, March 2026)
**Date**: June 12, 2026
**Why**: Closes the gap between the skill's existing "handoff contract" and "coding tickets" content and the foundational patterns those build on.

---

## The Four Core Delegation Architectures

| Pattern | Behavior | Best For |
|---------|----------|----------|
| **Sequential Handoff** | A → B → C, straight line | Linear pipelines (棒1→棒2→棒3) |
| **Router** | Central dispatcher analyzes intent, routes to specialist | Triage / intent classification |
| **Hierarchical** | Manager breaks down goals, assigns to workers, validates output | Complex problem-solving (赫米斯 default 模式) |
| **Bidirectional** | Agents share state, pass tasks back and forth | Joint collaboration / brainstorming |

**Source**: Microsoft Research on AutoGen — multi-agent systems with clear delegation protocols handle more complex tasks than single-agent implementations.

---

## The Three Sub-Agent Execution Patterns

### 1. Synchronous — "Wait and See"
- Parent blocks, waits for sub-agent to finish
- Sub-agent result returns as summarized output
- Mental model: "a complex function call — invoke, wait, get return value"
- Best for: data queries, analytical steps, code generation where output dictates next step
- **Token compression**: sub-agent executes 15 tool calls → parent receives ~750 token summary (90%+ reduction)

### 2. Asynchronous — "Fire and Forget"
- Delegate task, move immediately to next priority
- Multiple sub-agents operate in parallel
- Mental model: "treat as a colleague — delegate and move on"
- Best for: independent tasks where user experience should not be blocked
- **Key insight**: Legacy software is synchronous/predictable; AI agents require asynchronicity and non-determinism

### 3. Scheduled — "Future Execution"
- Instruct sub-agent to execute at a specific future time
- Sub-agent rehydrates context by querying central state at execution time
- Best for: intelligent follow-ups, periodic checks, dynamic reminders
- **Implementation tip**: Use two distinct tools instead of one tool with a mode parameter — models are better at selection than parameter optimization

---

## Core Principle: Context Compression > Parallelism

**The primary value of sub-agents is context management, not parallel execution.**

From Epsilla's production testing:
> "A sub-agent reads 8 files and executes 15 tool calls → the parent agent receives only a concise, 750-token summary of the outcome."
> "Implementing sub-agents reduced the number of tokens added to the parent agent's context by over 90%."

**Implication for Hermes**: When using `delegate_task`, the sub-agent's summarized reply is the product — not the individual tool calls it made. If a sub-agent returns "interrupted" or non-zero exit, that's a failure signal. If it returns a summary, that's success regardless of how many tools it called internally.

---

## Delegation by Reference (Not Context Stuffing)

**Problem**: Passing base64-encoded files or large text blocks through context windows is slow, expensive, and error-prone. LLMs forget instructions when context fills with file data.

**Solution**: Delegate by reference through shared workspace files.

```bash
# WRONG — stuffing files in context:
"Here is the content of data.csv..."  ❌ Expensive, error-prone

# CORRECT — delegate via shared workspace:
/shared/data/input.csv   ✓ Efficient, clean
/shared/data/output.csv
```

**Hermes pattern**: Use `~/.hermes/workspace/` or `/tmp/handoff_<project>.md` as the shared brain. Sub-agents write to these paths; parent reads summaries. Workers access files directly without context stuffing.

---

## When to Specialize: Clear Triggers

Start with a **generalist approach**; specialize only when driven by measured necessity.

| Trigger | Rationale |
|---------|-----------|
| Divergent model requirements | One task needs vision, another needs rapid classification |
| Security boundaries | Agent A handles sensitive data; Agent B handles public info only |
| Regulatory compliance | Finance/healthcare require auditable, independent processing |
| Empirical evidence | Validated evaluations consistently show specialized agent outperforms |

**Principle**: "Specialization must be driven by measured necessity, not architectural aesthetics."

---

## Relevance to Hermes

Hermes's `delegate_task` + `cron` + `subagent` architecture implements the **Hierarchical (Manager-Worker) pattern** — the gold standard for agentic workflows:
- Main agent = Supervisor (holds system prompt, validates output)
- Sub-agents = Workers (stateless, scoped tasks, file-based handoffs)

**The existing "Sub-Agent Handoff Contract Design" section** in SKILL.md builds on this foundation — those four elements (task + context + constraints + output_format) are specifically what you need when operating in Hierarchical mode.

---

## If→Then

**If** spawning a sub-agent for a task that touches ≤2 files total  
**Then** solo is always faster — spawn overhead exceeds gain  

**If** sub-agent executes 10+ tool calls but returns a clean summary  
**Then** this is normal context compression, not a failure — only "interrupted" or non-zero exit signals actual failure  

**If** designing a multi-step pipeline (棒1→棒2→棒3)  
**Then** use Sequential Handoff pattern with `/tmp/handoff_<project>.md` passing state between stages, not base64 context stuffing  

**If** a task needs "later" execution with current data  
**Then** use Scheduled pattern with sub-agent rehydrating from shared workspace, not polling with stale context  

**If** the user's workflow matches "independent tasks, user shouldn't wait"  
**Then** use Asynchronous (fire-and-forget) pattern — this is the default for cron-triggered sub-agents

---

## Hermes-Specific Orchestration Patterns (2026-06-23 Synthesis)

### Context: What Hermes Already Has
- **Hierarchical (Manager-Worker)**: Hermes default — `delegate_task` + `cron` + `subagent` = supervisor + workers
- **4 reference files** exist but not unified into Hermes-specific decision tree
- **Gap**: Generic orchestration theory is well-covered; Hermes-specific If→Then rules are missing

### Hermes Multi-Agent Decision Tree

```
Task type → Which pattern?
│
├─ Single agent, ≤2 files, < 10 tool calls
│   └→ Solo (no delegation). Handoff overhead > gain.
│
├─ Independent parallel tasks (A∥B∥C, user waits)
│   └→ Asynchronous delegate_task (parallel=true)
│   └→ If tasks are truly independent (no shared state)
│
├─ Sequential pipeline (A→B→C, output of A is input of B)
│   └→ Sequential Handoff via /tmp/handoff_<name>.md
│   └→ **Never** pass state via base64 or long context strings
│
├─ Single task, 10+ tool calls, complex context
│   └→ Synchronous delegate_task (single goal)
│   └→ Parent blocks, receives 750-token summary (90%+ compression)
│
├─ Task that needs future execution with fresh context
│   └→ Scheduled (cron + delegate_task)
│   └→ Sub-agent rehydrates from workspace files at execution time
│
└─ Triage/intent classification
    └→ Router pattern
    └→ Central dispatcher routes to appropriate specialist
```

### If→Then: Common Hermes Scenarios

**If** task involves coding in 1 file **Then** use solo execution — delegation overhead exceeds benefit

**If** 2+ coding tasks share the same repo and interface **Then** spawn 1 sub-agent for all tasks (not 1 per file) to minimize integration drift

**If** sub-agent writes code that other code will import **Then** specify export form explicitly in ticket (named vs default, function signatures, return types)

**If** cron job needs to run a sub-agent **Then** use Asynchronous pattern (fire-and-forget) — don't block cron tick waiting for result

**If** a sub-agent returns "interrupted" **Then** this is failure signal, not success — propagate failure to parent immediately

**If** user says "帮我建立 X 代理" (build me an X agent) **Then** use the 13-step long-running-sub-agent-recipe from references/long-running-sub-agent-recipe.md

**If** creating a new sub-agent profile **Then** use `hermes profile create <name> --clone` (not --clone-all) to avoid polluting with sessions/logs/cron history

**If** sub-agent needs to read/write files for parent **Then** use ~/.hermes/workspace/ or /tmp/handoff_<project>.md as shared brain, not context stuffing

**If** 2+ sub-agents write to same file or shared interface **Then** this is integration risk — specify exact API contract in each ticket before spawning

### The Hidden Tax: Integration Cost

Research from 2026-06-11 experiment:
- Solo write (M-task, 4 files): 161s wall time
- 3 sub-agents parallel: 180s wall time (+12% slower!) + 71s integration time
- **Why slower**: Workers don't share context, so they drift on: export forms, function signatures, return types, error conventions

**If** using sub-agents for coding **Then** write detailed tickets with exact export/signature conventions — this is the integration cost that determines whether parallelism helps or hurts

### Layer 3缺，口：赫米斯的multi-agent觀測

Current: No production observability for multi-agent runs (token counts per sub-agent, failure rates, context compression ratios).

**If** this gap is addressed **Then** it becomes a Layer 3 (external verification) capability — pass rate + cost tracking per agent type
