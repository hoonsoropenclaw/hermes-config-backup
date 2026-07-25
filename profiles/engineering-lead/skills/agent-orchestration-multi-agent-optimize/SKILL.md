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