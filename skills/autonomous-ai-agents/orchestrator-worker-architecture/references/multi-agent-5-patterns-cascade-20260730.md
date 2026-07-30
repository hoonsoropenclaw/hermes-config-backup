# Multi-Agent Orchestration: 5 Patterns + Cascade Failure (2026-07-30)

> **Research source**: [Digital Applied — Multi-Agent Orchestration: 5 Patterns That Work in 2026](https://www.digitalapplied.com/blog/multi-agent-orchestration-5-patterns-that-work) (May 17, 2026) + [Medium — Multi-Agent in Production in 2026: What Actually Survived](https://medium.com/@Micheal-Lanham/multi-agent-in-production-in-2026-what-actually-survived-f86de8bb1cd1)

## 5 Patterns That Dominate Production (2026)

### 1. Fan-Out (Parallel Handoffs)
Multiple agents receive the same task in parallel, work independently, results merge.
**Best for**: Independent fact-gathering, parallel research.
**Anti-pattern**: Dependent tasks forced into parallel.

### 2. Pipeline (Sequential Handoffs + Tool Loops)
Output of Agent A becomes input of Agent B; each step can loop back for refinement.
**Best for**: Research → Draft → Review → Publish chains.
**Hermes equivalent**: `orchestrator-worker-architecture` Phase 1-5.

### 3. Supervisor (Central Handoffs)
One orchestrator decides which agent to call next based on state.
**Best for**: Complex routing, human-in-the-loop checkpoints.
**Hermes equivalent**: `delegate_task` hub-and-spoke mode.

### 4. Debate (Build-Your-Own)
Two+ agents argue opposing positions, final arbiter decides.
**Best for**: Risk assessment, adversarial analysis.
**Note**: Not native to any framework — must build yourself.

### 5. Swarm (Build-Your-Own)
N agents share a topic, take turns, with a manager picking who speaks next.
**Critical 2026 insight**: "Free mesh survived mostly as a **controlled subroutine inside a supervisor**, not as the outer architecture." — free P2P mesh at outer layer is an anti-pattern.

## Cascade Failure: The "From Spark to Fire" Paper (2026)

**Finding**: Multi-agent collaboration is a dependency graph; **a single atomic falsehood can spread into system-level false consensus**.

| Attack | LangGraph | CrewAI |
|--------|-----------|--------|
| Hub injection | 100% system-wide failure | 100% vs 15.9% |
| Extended cascade (all frameworks) | ~100% final infection | ~100% |

**Defense mechanisms that WORK**:
- Phase gates between agent stages
- Hidden selectors (not all agents see all messages)
- Shared artifacts with explicit provenance
- Final arbiter with verification authority
- **Not**: Full mesh / free collaboration at outer layer

## Hermes Orchestrator-Worker Architecture: Gap Analysis

**Already covered** (from existing SKILL.md):
- ✅ Context isolation (worker context = 0 to main)
- ✅ Fan-Out/Fan-In pattern
- ✅ Phase 6 verification for engineering outputs
- ✅ Failure aggregation with conflict markers
- ✅ Aggregation hallucination detection

**Missing from existing skill** (now added via this reference):
- ✅ Cascade failure / hub injection defense
- ✅ Phase gate between orchestrator and workers
- ✅ Free mesh outer-layer anti-pattern warning

## If→Then Rules

**If** multi-agent system has a central hub or orchestrator node with high connectivity,
**Then** add explicit phase gates and verify each agent's output independently before passing to next stage (cascade failure spreads fastest through hub nodes).

**If** task requires agents to "collaborate" at the outer architecture layer,
**Then** wrap the collaboration in a supervisor/hub with a final arbiter — free mesh at outer layer is an anti-pattern in 2026 production systems.

**If** using `delegate_task(tasks=[...])` with 3+ workers,
**Then** always include a verification step that checks each worker's output for atomic falsehoods before aggregation — LangGraph/CrewAI/AutoGen ALL fail at cascade when one worker produces false consensus.

## Framework Quick Reference

| Framework | Paradigm | State | Best For |
|-----------|----------|-------|----------|
| LangGraph | State Machine (Graphs) | Explicit & persistent | Production-grade (Anthropic, LinkedIn, Uber, Replit) |
| CrewAI | Role-Based (Crews) | Memory-based | Rapid prototyping (2-3 days to working crew) |
| AutoGen | Conversation-Based | Message history | Research, negotiation, coding loops |
| OpenAI Agents SDK | Handoffs | Implicit | OpenAI-first stacks |
| LlamaIndex Workflows | Event-driven | RAG-centric | Document-intensive agents |
