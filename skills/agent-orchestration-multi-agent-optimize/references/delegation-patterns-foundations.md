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
