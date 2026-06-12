---
name: agent-orchestration-multi-agent-optimize
description: "Optimize multi-agent systems with coordinated profiling, workload distribution, and cost-aware orchestration. Use when improving agent performance, throughput, or reliability."
risk: unknown
source: community
date_added: "2026-02-27"
---

# Multi-Agent Optimization Toolkit

## Use this skill when

- Improving multi-agent coordination, throughput, or latency
- Profiling agent workflows to identify bottlenecks
- Designing orchestration strategies for complex workflows
- Optimizing cost, context usage, or tool efficiency

## Do not use this skill when

- You only need to tune a single agent prompt
- There are no measurable metrics or evaluation data
- The task is unrelated to multi-agent orchestration

## Instructions

1. Establish baseline metrics and target performance goals.
2. Profile agent workloads and identify coordination bottlenecks.
3. Apply orchestration changes and cost controls incrementally.
4. Validate improvements with repeatable tests and rollbacks.

## Safety

- Avoid deploying orchestration changes without regression testing.
- Roll out changes gradually to prevent system-wide regressions.

## Role: AI-Powered Multi-Agent Performance Engineering Specialist

### Context

The Multi-Agent Optimization Tool is an advanced AI-driven framework designed to holistically improve system performance through intelligent, coordinated agent-based optimization. Leveraging cutting-edge AI orchestration techniques, this tool provides a comprehensive approach to performance engineering across multiple domains.

### Core Capabilities

- Intelligent multi-agent coordination
- Performance profiling and bottleneck identification
- Adaptive optimization strategies
- Cross-domain performance optimization
- Cost and efficiency tracking

## Arguments Handling

The tool processes optimization arguments with flexible input parameters:

- `$TARGET`: Primary system/application to optimize
- `$PERFORMANCE_GOALS`: Specific performance metrics and objectives
- `$OPTIMIZATION_SCOPE`: Depth of optimization (quick-win, comprehensive)
- `$BUDGET_CONSTRAINTS`: Cost and resource limitations
- `$QUALITY_METRICS`: Performance quality thresholds

## 1. Multi-Agent Performance Profiling

### Profiling Strategy

- Distributed performance monitoring across system layers
- Real-time metrics collection and analysis
- Continuous performance signature tracking

#### Profiling Agents

1. **Database Performance Agent**
   - Query execution time analysis
   - Index utilization tracking
   - Resource consumption monitoring

2. **Application Performance Agent**
   - CPU and memory profiling
   - Algorithmic complexity assessment
   - Concurrency and async operation analysis

3. **Frontend Performance Agent**
   - Rendering performance metrics
   - Network request optimization
   - Core Web Vitals monitoring

### Profiling Code Example

```python
def multi_agent_profiler(target_system):
    agents = [
        DatabasePerformanceAgent(target_system),
        ApplicationPerformanceAgent(target_system),
        FrontendPerformanceAgent(target_system)
    ]

    performance_profile = {}
    for agent in agents:
        performance_profile[agent.__class__.__name__] = agent.profile()

    return aggregate_performance_metrics(performance_profile)
```

## 2. Context Window Optimization

### Optimization Techniques

- Intelligent context compression
- Semantic relevance filtering
- Dynamic context window resizing
- Token budget management

### Context Compression Algorithm

```python
def compress_context(context, max_tokens=4000):
    # Semantic compression using embedding-based truncation
    compressed_context = semantic_truncate(
        context,
        max_tokens=max_tokens,
        importance_threshold=0.7
    )
    return compressed_context
```

## 3. Agent Coordination Efficiency

### Coordination Principles

- Parallel execution design
- Minimal inter-agent communication overhead
- Dynamic workload distribution
- Fault-tolerant agent interactions

### Orchestration Framework

```python
class MultiAgentOrchestrator:
    def __init__(self, agents):
        self.agents = agents
        self.execution_queue = PriorityQueue()
        self.performance_tracker = PerformanceTracker()

    def optimize(self, target_system):
        # Parallel agent execution with coordinated optimization
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(agent.optimize, target_system): agent
                for agent in self.agents
            }

            for future in concurrent.futures.as_completed(futures):
                agent = futures[future]
                result = future.result()
                self.performance_tracker.log(agent, result)
```

## 4. Parallel Execution Optimization

### Key Strategies

- Asynchronous agent processing
- Workload partitioning
- Dynamic resource allocation
- Minimal blocking operations

## 5. Cost Optimization Strategies

### LLM Cost Management

- Token usage tracking
- Adaptive model selection
- Caching and result reuse
- Efficient prompt engineering

### Cost Tracking Example

```python
class CostOptimizer:
    def __init__(self):
        self.token_budget = 100000  # Monthly budget
        self.token_usage = 0
        self.model_costs = {
            'gpt-5': 0.03,
            'claude-4-sonnet': 0.015,
            'claude-4-haiku': 0.0025
        }

    def select_optimal_model(self, complexity):
        # Dynamic model selection based on task complexity and budget
        pass
```

## 6. Latency Reduction Techniques

### Performance Acceleration

- Predictive caching
- Pre-warming agent contexts
- Intelligent result memoization
- Reduced round-trip communication

## 7. Quality vs Speed Tradeoffs

### Optimization Spectrum

- Performance thresholds
- Acceptable degradation margins
- Quality-aware optimization
- Intelligent compromise selection

## 8. Monitoring and Continuous Improvement

### Observability Framework

- Real-time performance dashboards
- Automated optimization feedback loops
- Machine learning-driven improvement
- Adaptive optimization strategies

## Reference Workflows

> **New: Delegation Patterns Foundations** — covers the four delegation architectures (Sequential / Router / Hierarchical / Bidirectional), three sub-agent execution patterns (Synchronous / Asynchronous / Scheduled), context compression as primary value (>90% token reduction), and Delegation by Reference principle. See `references/delegation-patterns-foundations.md`.

### Workflow 1: E-Commerce Platform Optimization

1. Initial performance profiling
2. Agent-based optimization
3. Cost and performance tracking
4. Continuous improvement cycle

### Workflow 2: Enterprise API Performance Enhancement

1. Comprehensive system analysis
2. Multi-layered agent optimization
3. Iterative performance refinement
4. Cost-efficient scaling strategy

## Key Considerations

- Always measure before and after optimization
- Maintain system stability during optimization
- Balance performance gains with resource consumption
- Implement gradual, reversible changes

Target Optimization: $ARGUMENTS

## Limitations
- Use this skill only when the task clearly matches the scope described above.
- Do not treat the output as a substitute for environment-specific validation, testing, or expert review.
- Stop and ask for clarification if required inputs, permissions, safety boundaries, or success criteria are missing.

## Practical: Hermes on N100 Mini-PC

### Hardware Specs (N100)
```
CPU: 4 cores (Intel N100, mobile chip)
RAM: 31GB total, ~26GB available
```

### Safe Concurrency Limits

| max_concurrent_children | Recommendation |
|---|---|
| 3-5 | Safe daily use, no pressure |
| 6-8 | Moderate load, stable on N100 |
| 10-15 | Edge — may slow down |
| 20+ | Not recommended on N100 |

### Key Config Parameters (config.yaml → delegation.*)

```
delegation.max_concurrent_children: 8   # simultaneous sub-agents
delegation.max_spawn_depth: 1            # sub-agent cannot spawn its own sub-agent
delegation.child_timeout_seconds: 1800  # per-sub-agent wall-clock timeout (default 600s = 10min)
agent.gateway_timeout: 1800               # gateway-to-subagent comms timeout (30min)
agent.tool_use_enforcement: true          # ALL models forced to call tools, not just describe
```

### Pitfall: User Knew About child_timeout (10 min) But Thought gateway_timeout Was Relevant

**Signal**: User said "timeout是說給subagent完成任務的時間嗎？超過時，這個subagent就會停止？" and later "timeout時間有上限嗎？". They were asking about sub-agent work timeout, but the conversation started with `gateway_timeout: 1800` being mentioned.

**Lesson**: When the user asks about "timeout", they almost certainly mean `child_timeout_seconds` (sub-agent work timeout, the one that kills the agent). The `gateway_timeout` is a communications detail they don't need to know about upfront.

**Correct behavior**: Volunteer which timeout is the relevant one immediately. Don't make the user ask follow-up to disambiguate two unrelated timeout values.

```
Example correct response:
"對，sub-agent 的工作超時是 child_timeout_seconds（目前 600/10分鐘）。
gateway_timeout 是 gateway 和 sub-agent 之間的通訊超時，與 sub-agent 是否會被停止無關。"
```

### Config Changes: Immediate vs Next-Task

Config changes written via `hermes config set` take effect on **next task dispatch** — not on the currently running gateway.

To force-apply without sudo:
```bash
kill $(pgrep -f "hermes.*gateway") && sleep 2 && hermes gateway run --replace
```

With sudo:
```bash
sudo systemctl restart hermes-gateway
```

### tool_use_enforcement Impact

- `"auto"` (default) = only GPT/Codex/Grok/Gemini models receive enforcement guidance
- `true` = **all models** (including MiniMax) receive enforcement
- Enforcement = "Do not end your turn with a promise — execute it now"

Setting `tool_use_enforcement: true` when using MiniMax addresses the "said to search but never called the tool" failure mode.

### max_spawn_depth Meaning

```
max_spawn_depth: 1  ← current (default)
depth 0 = Hermes main agent
depth 1 = sub-agent spawned by Hermes → CANNOT spawn another sub-agent
depth 2 = sub-agent's sub-agent → blocked by max_spawn_depth=1
```

To enable hierarchical teams (Orchestrator → Workers), raise `max_spawn_depth` to 2 or 3. Risk: complex debugging, unbounded recursion if misconfigured.

## SOP Enforcement & Policy Validation (Layer 3)

For multi-agent systems, Layer 3 (external validation) is the only reliable mechanism — without it, agents may deviate from defined SOPs.

**Key reference**: `references/policy-enforcement-implementation.md` covers:
- NeMo Guardrails + LangGraph integration
- OpenAI-style guardrails vs human review patterns
- CASTER cost-aware multi-agent routing
- Agent Behavioral Contracts (runtime enforcement)
- External validation loop pattern (agent executes → validator checks → re-execute if non-compliant)

**Critical insight**: The validator must NOT be the agent itself (otherwise back to Layer 1). For Hermes, the main agent should validate sub-agent outputs against SOP before delivery.

## Sub-Agent Handoff Contract Design (Orchestrator → Worker Pattern)

When designing an Orchestrator → Worker handoff, the interface contract must contain **four mandatory elements**:

| Element | Description | Example |
|---------|-------------|---------|
| **task** | What the worker must do | "抓取 4 個標竿平台的資料" |
| **context** | Background / persona / constraints | "_plan.md 內的使用者原意 Persona" |
| **constraints** | Explicit boundaries / must-include / must-avoid | "必抓清單：SkillSwap.io, Busuu, HelloTalk, Tandem" |
| **output_format** | Expected deliverable shape | "URL + 名稱 + 功能矩陣 (markdown table)" |

**Without output_format**: Worker returns unconstrained text → summarizer gets unpredictable input
**Without constraints**: Worker decides autonomously → may skip required sources (e.g., SkillSwap.io)

### Five Production Failure Modes (Orchestrator-Worker Pattern)

From Microsoft Azure + Product School + Beam AI research on production multi-agent systems:

| Failure Mode | Symptom | Mitigation |
|---|---|---|
| **1. Single point of failure** | Orchestrator misclassifies task → wrong worker gets it | Add explicit routing rules in handoff contract |
| **2. Cost compounding** | Each worker = 1 LLM call; orchestrator decomposition + aggregation on top → costs scale nonlinearly | Set per-worker token budgets; use `--llm none` for data-fetch workers |
| **3. Misclassification compounding** | Error rate grows exponentially with worker count | Include mandatory validation step in summarizer |
| **4. No shared knowledge base** | Each worker is stateless → inconsistent outputs | Include `_plan.md` as shared context; worker must read it |
| **5. Handoff context loss** | Summarizer compression drops domain knowledge | Use structured output_format + explicit constraints in contract |

**Key lesson** (from consumer-researcher v2): `_plan.md` with a must-include list is necessary but not sufficient — you also need `output_format` and `constraints` in the contract.

### Practical Handoff Template

For Hermes Orchestrator → Worker setups, create `_plan.md` with:

```markdown
# Task
[One sentence: what this research campaign must accomplish]

# Context
[User's original intent, personas, business constraints]

# Constraints (must-include / must-avoid)
- MUST include: [list of 4-7 specific sources/approaches]
- MUST avoid: [list of known-bad sources/approaches]
- Output must fit: [size constraint, e.g., "< 5 KB per worker output"]

# Output Format
[Structured table / JSON schema / bullet list — be specific]
Example: | Source | Key Feature | Target User | Pain Point Addressed |
```

**Verification**: After worker completion, summarizer validates that must-include list was actually captured before aggregating.

### If→Then

**If** designing an Orchestrator → Worker handoff **Then** include all four elements (task + context + constraints + output_format) in `_plan.md`. Missing any element increases failure mode risk.

**If** adding a new worker type to an existing orchestration **Then** validate that the summarizer's output_format can handle the worker's deliverable shape before deployment.

## Sub-Agent Coding Tickets: Integration Cost is the Hidden Tax (2026-06-11)

> Evidence: `references/sub-agent-coding-integration-cost.md` (full Todo App experiment with 3 rounds × 3 modes)

When the Orchestrator is the main agent and Workers are sub-agents spawned via `delegate_task` to **write code in parallel**, the playbook above is necessary but not sufficient. **Code writing has a unique failure mode the abstract "handoff contract" framework doesn't cover: the function signature and module-export-shape must be agreed upon upfront, or every worker invents their own.**

### The Five Hard-Won Lessons (Todo App Experiment, M-type, Next.js + TS)

| # | Lesson | Specific Evidence |
|---|--------|-------------------|
| 1 | **Parallel write does NOT save wall time** | R2: 109s parallel + 71s integration = 180s total. R1 (solo): 161s. Parallel saved 0s on the clock, only saved main-session context occupancy. |
| 2 | **Integration cost grows with sub-agent count** | 1 worker → 0 integration issues. 3 workers → 2+ signature-mismatch issues. Issue count scales faster than linearly because every (worker × interface) pair can drift. |
| 3 | **Coding standards fix "format" problems, not "semantic" problems** | 6 coding rules (quote style, import form, export form, TS strict, catch (e), `deleteTodo` rename) eliminated 100% of format drift. They did **not** fix `list()` vs `list(filter)` signature drift, or `Todo` vs `Todo \| null` return type drift. |
| 4 | **Workers make mistakes a solo writer would not make** | Solo writer keeps "what I just exported" in working memory. Workers write `import db from "@/lib/db"` assuming default export, while the lib worker wrote `export const db = {...}` (named). A solo writer reading their own lib/db.ts 10 seconds later catches this instantly. |
| 5 | **Ticket precision has a cost-benefit curve** | A 3×-longer ticket saved only 30s of integration time. The marginal cost of writing ultra-precise tickets exceeds the marginal benefit at the M-task scale. |

### When to Spawn Sub-Agents for Coding (Decision Tree)

```
Is the task M-size (2-3 tickets) or L-size (5+ tickets)?
├── L-size (5+ tickets) → SPAWN SUB-AGENTS freely (your context would explode otherwise)
├── M-size (2-3 tickets) →
│   ├── Are the interfaces already 100% nailed down? (full TS signatures, not just descriptions)
│   │   ├── YES → Spawn is OK, but budget 30-90s for integration
│   │   └── NO  → Write solo. The integration cost will eat the parallel savings.
└── S-size (1 ticket) → NEVER spawn. Solo is always faster.

Is the worker's context critical for the task? (e.g. needs a 50-file reading of an unfamiliar codebase)
├── YES → Spawn is justified even at M-size, because solo writer can't hold it either
└── NO  → Solo is preferred
```

### The Required Additions to a Coding Ticket (Beyond the 4-Element Handoff)

The standard handoff (task + context + constraints + output_format) is missing the two things code-writing needs:

| Additional Element | Purpose | Example |
|-------------------|---------|---------|
| **exact export shape** | Worker A and Worker B must agree on `export const db = {...}` vs `export function list() {...}` | "Use `export const db = { list, create, update, deleteTodo }` object form, NOT named functions" |
| **exact function signatures + return types** | Prevents `list(): Todo[]` vs `list(filter: FilterType): Todo[]` drift, or `Todo` vs `Todo \| null` return type drift | "Required signatures: `list(filter: FilterType = 'all'): Todo[]`, `update(id: string, data: Partial<Pick<Todo,'completed'>>): Todo \| null`, `deleteTodo(id: string): boolean`" |

**Without these two additions**, every multi-worker coding task will produce 1-3 integration errors that the Orchestrator must fix manually.

### The Integration-Fix SOP (Orchestrator after Workers return)

Don't just trust the workers' "T-N DONE" reports. Run this 4-step:

1. **Verify file presence**: `ls <expected paths>` for every file the ticket said to create. Workers sometimes write to the wrong path or skip files.
2. **Run `tsc --noEmit` (or equivalent type checker)**: catches signature mismatches and missing exports that `next build` will miss.
3. **Run the actual build**: catches `npm` resolution errors, missing dependencies, webpack-only issues.
4. **Manually inspect cross-file imports**: `grep -rn "from '@/"` and look for default-vs-named import mismatches.

**If** any of these fail **Then** the Worker did NOT actually finish — the ticket is still open. Do not accept the worker's self-report.

### When Workers Have Isolated Working Directories (Critical)

`delegate_task` gives each sub-agent a **fresh, isolated terminal session** with its own cwd. Workers cannot see each other's output. Implications:

- If you tell 3 workers "create the project at `~/todo-app`", each one will run `npx create-next-app` and the second/third will see the directory exists. **This is actually fine** — the project is shared — but workers don't realize it and will each emit "create-next-app detected existing directory" warnings.
- If you tell 3 workers "each create your own copy at `~/todo-{1,2,3}-app`", they CANNOT share code between them. They each produce a separate project. **You, the Orchestrator, must merge.**
- Workers cannot read each other's worker-N-report.md during their run. Reports are for you, not for them.

**If** workers need to share code while running **Then** you must use a shared parent directory and let later workers "inherit" the early files. **Document this in the ticket** or workers will each create their own subdirectory and you'll have a 3-project merge nightmare.

### When Not to Use This Pattern At All

- Task touches ≤ 2 files total → spawn overhead exceeds gain
- All tickets have hard inter-dependencies (Worker B needs Worker A's output to start) → no parallelism possible, just sequential
- The integration fix is non-trivial (cross-cutting refactor, breaking schema change) → the "merge" step is itself a full task, hire 1 worker for the merge instead

## Creating a Long-Running Sub-Agent Profile (常駐代理 13-Step Recipe)

> Trigger: user says "build a permanent sub-agent", "常駐代理", "long-running agent", "monitoring agent"
> Full detail: `references/long-running-sub-agent-recipe.md`

Quick checklist (don't skip steps, don't combine steps):

1. **Plan the role** (5 min) — write down: trigger phrases, input types, output artifacts, handoff targets, "禁止事項"
2. **`hermes profile create <name> --clone`** (10s) — clones from default, gets ~194 skills
3. **Copy trial-and-error SOP** (5s) — `cp -r ~/.hermes/profiles/consumer-researcher/skills/trial-and-error/references/sops/ ~/.hermes/profiles/<name>/skills/trial-and-error/references/sops/` (default trial-and-error is in minimal-rebuild state, this restores the profile-slimming SOP)
4. **Write `persona.md`** at profile root — the role definition, 6-step workflow, 禁止事項, handoff rules
5. **Write the agent's defining skill** (1-2 skills unique to this role) — the methodology that makes the role valuable
6. **`hermes -p <name> skills opt-out --remove --yes`** (5s) — auto-removes 65 bundled skills, writes `.no-bundled-skills` marker
7. **Whitelist prune with Python** (10s) — keep 30-50 skills (own + hermes infrastructure + role-specific), drop the rest with `shutil.rmtree` (NOT shell glob, NOT `hermes skills disable`)
8. **Create `wrapper script`** at `~/.local/bin/<name>` — 3 lines: `#!/bin/sh` + `exec hermes -p <name> "$@"`. The `hermes profile create` auto-creates a wrapper, but the auto one uses `hermes chat` not `hermes -p <name>`. Fix it.
9. **Write `skills/_meta/slim-history.md`** — the decision record (what was kept, why, what was dropped, what was missing from default trial-and-error)
10. **Run 4-件套 verification** (30s) — own skill present + 4 hermes infrastructure skills present + default profile untouched + `.no-bundled-skills` marker present
11. **Update trial-and-error skill** with the new profile's name (so future agents know it exists)
12. **Document in profile-list mental model** (the user might keep a written list, or you can rely on `hermes profile list` output)
13. **Smoke test**: `hermes -p <name> skills list 2>&1 | tail -1` should show ~30-50 skills enabled

**Time budget**: 15-30 minutes for a complete profile. Less = you skipped a step (usually #3 or #9).

**Why "create the project's defining skill" is step 5, not step 1**: the persona declares the role; the skill is the *codified methodology* the role will use. Persona is "what is this agent", skill is "how does it do its job." Many agents have a persona but no codified skill — they re-invent their workflow every session. Step 5 prevents that.