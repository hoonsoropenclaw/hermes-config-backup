---
name: ai-agent-development
description: "AI agent development workflow for building autonomous agents, multi-agent systems, and agent orchestration with CrewAI, LangGraph, and custom agents."
category: granular-workflow-bundle
risk: safe
source: personal
date_added: "2026-02-27"
---

# AI Agent Development Workflow

## Overview

Specialized workflow for building AI agents including single autonomous agents, multi-agent systems, agent orchestration, tool integration, and human-in-the-loop patterns.

## When to Use This Workflow

Use this workflow when:
- Building autonomous AI agents
- Creating multi-agent systems
- Implementing agent orchestration
- Adding tool integration to agents
- Setting up agent memory

## Workflow Phases

### Phase 1: Agent Design

#### Skills to Invoke
- `ai-agents-architect` - Agent architecture
- `autonomous-agents` - Autonomous patterns

#### Actions
1. Define agent purpose
2. Design agent capabilities
3. Plan tool integration
4. Design memory system
5. Define success metrics

#### Copy-Paste Prompts
```
Use @ai-agents-architect to design AI agent architecture
```

### Phase 2: Single Agent Implementation

#### Skills to Invoke
- `autonomous-agent-patterns` - Agent patterns
- `autonomous-agents` - Autonomous agents

#### Actions
1. Choose agent framework
2. Implement agent logic
3. Add tool integration
4. Configure memory
5. Test agent behavior

#### Copy-Paste Prompts
```
Use @autonomous-agent-patterns to implement single agent
```

### Phase 3: Multi-Agent System

#### Skills to Invoke
- `crewai` - CrewAI framework
- `multi-agent-patterns` - Multi-agent patterns

#### Actions
1. Define agent roles
2. Set up agent communication
3. Configure orchestration
4. Implement task delegation
5. Test coordination

#### Copy-Paste Prompts
```
Use @crewai to build multi-agent system with roles
```

### Phase 4: Agent Orchestration

#### Skills to Invoke
- `langgraph` - LangGraph orchestration
- `workflow-orchestration-patterns` - Orchestration

#### Actions
1. Design workflow graph
2. Implement state management
3. Add conditional branches
4. Configure persistence
5. Test workflows

#### Copy-Paste Prompts
```
Use @langgraph to create stateful agent workflows
```

### Phase 5: Tool Integration

#### Skills to Invoke
- `agent-tool-builder` - Tool building
- `tool-design` - Tool design

#### Actions
1. Identify tool needs
2. Design tool interfaces
3. Implement tools
4. Add error handling
5. Test tool usage

#### Copy-Paste Prompts
```
Use @agent-tool-builder to create agent tools
```

### Phase 6: Memory Systems

#### Skills to Invoke
- `agent-memory-systems` - Memory architecture
- `conversation-memory` - Conversation memory

#### Actions
1. Design memory structure
2. Implement short-term memory
3. Set up long-term memory
4. Add entity memory
5. Test memory retrieval

#### Copy-Paste Prompts
```
Use @agent-memory-systems to implement agent memory
```

### Phase 7: Evaluation

#### Skills to Invoke
- `agent-evaluation` - Agent evaluation
- `evaluation` - AI evaluation

#### Actions
1. Define evaluation criteria
2. Create test scenarios
3. Measure agent performance
4. Test edge cases
5. Iterate improvements

#### Copy-Paste Prompts
```
Use @agent-evaluation to evaluate agent performance
```

## Agent Architecture

```
User Input -> Planner -> Agent -> Tools -> Memory -> Response
              |          |        |        |
         Decompose   LLM Core  Actions  Short/Long-term
```

## Agent Self-Improvement Mechanisms (Research-Backed)

When building agents that learn from experience, use these validated approaches:

| Mechanism | Source | Validation Level | Use Case |
|-----------|--------|-----------------|----------|
| SOP-Agent | arXiv 2501.09316 | Layer 2.5 | Strict SOP following via decision graphs |
| CRITIC | ICLR 2024 | Layer 3 | Self-correction requires external tool feedback |
| Reflexion | arXiv 2303.11366 | Layer 3 | Verbal reinforcement for persistent learning |
| Agent Behavioral Contracts | arXiv 2602.22302 | Layer 3 | Formal P/I/G/R specs + runtime enforcement |

**Core Principle**: Without external validation (Layer 3), "improving over time" is decoration only.
LLM cannot reliably self-verify — validation must be external-triggered.

**Reference:** See `metacognitive-learner/references/ai-agent-self-improvement-research.md` for condensed research summary.
**Integration Reference:** See `references/full-stack-coding-agent-integration.md` for wiring coding components into a full-stack autonomous agent.

## Agent SOPs (strands-agents-sops)

For production agent workflows, use the **strands-agents-sops** Python package which provides standardized markdown-based SOPs for AI agents. Install via `pip install strands-agents-sops`.

**Available SOPs:**

| SOP | Purpose | Key Feature |
|-----|---------|-------------|
| `code-assist` | TDD-based implementation | Explore → Plan → Code → Commit, with Given-When-Then acceptance criteria |
| `code-task-generator` | Task breakdown from plans | Processes PDD implementation plans one step at a time |
| `codebase-summary` | Codebase analysis + docs | Generates AGENTS.md, architecture.md, component docs |
| `pdd` | Prompt-Driven Development | Iterative Clarify ↔ Research → Design → Plan workflow |

**Integration with this skill:**
- Phase 2 (Single Agent Implementation) → use `code-assist` for TDD workflow
- Phase 3 (Multi-Agent System) → use `pdd` for role definition and task delegation
- Phase 5 (Tool Integration) → use `code-task-generator` for breaking down tool-building into micro-tasks
Generated skills available at: `~/.hermes/skills/strands-skills-generated/`

### Autonomous Execution: Combining Skills into a Full-Stack Coding Agent

This skill's Phase 1-7 workflow and the generated strands-skills are building blocks. The actual gap is the **integration layer** — no single skill chains them into a continuous "receive task → plan → execute → verify → deliver" pipeline. To build a full-stack coding agent:

**Skill components already available:**
| Component | Skill | Role |
|-----------|-------|------|
| TDD implementation | `strands-skills-generated/code-assist` | Explore → Plan → Code → Commit, supports `mode: auto` (no user interruption) |
| Orchestrator-Worker contract | `agent-orchestration-multi-agent-optimize` | Handoff format: task + context + constraints + output_format |
| Quality gates | `ai-agent-development` Phase 7 | Evaluation checkpoints across the workflow |
| Task breakdown | `strands-skills-generated/code-task-generator` | Break PDD plans into micro-tasks |

**Integration pattern (If→Then):**
- **If** you need a single agent to autonomously handle a coding task from rough idea to delivered code
- **Then** use `code-assist` with `mode: auto` as the execution engine, use `agent-orchestration-multi-agent-optimize` Orchestrator-Worker contract if spawning sub-agents, and gate each phase with the ai-agent-development Phase 7 quality checklist
- **Trigger conditions** for this integration: task has acceptance criteria, no user present or user approved autonomous mode, task fits in one session

**Pitfall (2026-06-11):** Each component skill works in isolation. Without an explicit integration skill, the agent must manually wire them together every time. Creating a wrapper skill that sequences these is the correct fix — not modifying each component.
Generated skills available at: `~/.hermes/skills/strands-skills-generated/`

## Quality Gates

- [ ] Agent logic working
- [ ] Tools integrated
- [ ] Memory functional
- [ ] Orchestration tested
- [ ] Evaluation passing

## Related Workflow Bundles

- `ai-ml` - AI/ML development
- `rag-implementation` - RAG systems
- `workflow-automation` - Workflow patterns

---

## Layer 3 Enforcement: Agent Behavioral Contracts (ABC)

**Source:** arXiv 2602.22302 — "Agent Behavioral Contracts: Formal Specification and Runtime Enforcement for Reliable Autonomous AI Agents"

**What it adds over Layer 2.5 (Hermes automated-sop-validation):**
- Static YAML contracts (P/I/G) = Layer 2.5 (Hermes current state)
- ABC adds: Runtime enforcement + Probabilistic satisfaction + Recovery mechanism
- ABC defines (p,δ,k)-satisfaction: accounts for LLM non-determinism
- **Drift Bounds Theorem**: if recovery rate γ > α (natural drift rate), behavioral drift is bounded to D* = α/γ
- **Results**: 1980 sessions, 5.2–6.8 soft violations/session detected, 88–100% hard constraint compliance, D* < 0.27 drift, <10ms overhead/action

**ABC Contract Structure:**
| Component | Purpose |
|-----------|---------|
| Precondition (P) | What must be true before action |
| Invariant (I) | What must remain true during execution |
| Postcondition (G) | What must be true after action |
| Recovery (R) | Action when P/I/G violated + recovery rate γ |

**For Hermes (2026-06-12 state):**
- `automated-sop-validation/contracts/*.yaml` = Static P/I/G specs (Layer 2.5)
- Missing: `recovery:` field + runtime ABC enforcement

**If→Then:**
- **If** a contract has `recovery.gamma > alpha` AND output violates postcondition
- **Then** invoke recovery action instead of silent pass

**Minimal ABC YAML extension:**
```yaml
postcondition:
  description: "output must contain X"
  assertion: "X in output"
  recovery:
    action: "retry_once_then_escalate"
    gamma: 0.8   # recovery rate (must exceed alpha for drift bound)
    max_retries: 1
```

## Limitations
- Use this skill only when the task clearly matches the scope described above.
- Do not treat the output as a substitute for environment-specific validation, testing, or expert review.
- Stop and ask for clarification if required inputs, permissions, safety boundaries, or success criteria are missing.