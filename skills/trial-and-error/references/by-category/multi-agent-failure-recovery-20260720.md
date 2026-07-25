# Multi-Agent Failure Recovery Patterns
**Source**: MAST Taxonomy (NeurIPS 2025, 1,600+ execution traces) + Taskade AI Error Recovery (2026)
**Created**: Cycle 529 (2026-07-20)

---

## Background

Multi-agent LLM systems fail at **41-86.7%** in production (MAST study, NeurIPS 2025). Root cause distribution:
- **Specification Problems**: 41.77% — role ambiguity, unclear task definitions
- **Coordination Failures**: 36.94% — communication breakdowns, state sync issues
- **Verification Gaps**: 21.30% — inadequate testing, missing output quality checks

Hermes's delegate_task is L0-isolated (no shared memory). MemPalace MCP is the only L3 relay. This means coordination failures are structural, not just implementation bugs.

---

## If→Then Patterns

**If→Then #1: Error Classification Ladder (Transient / Permanent / Critical)**

> **If** [Any tool call or agent subprocess fails]
> **Then** [Classify the error class before choosing a recovery strategy:]
> - **Transient** (timeout, 429, 5xx, network blip) → Retry with exponential backoff + jitter
> - **Permanent** (400, 404, 422, auth rejected) → Skip retry → Fallback (simpler/cached/default)
> - **Critical** (budget exceeded, destructive side effect, safety violation) → Save state + alert + emergency stop
> **Why**: HTTP status codes directly map to error class. Misclassification leads to dangerous retries (retrying permanent failures wastes tokens; retrying critical failures can cause data loss)

**If→Then #2: Multi-Agent Coordination Failure Detection**

> **If** [delegate_task subagent returns without expected output OR produces inconsistent results across runs]
> **Then** [Check coordination failure patterns in this order:]
> 1. **State sync**: Did MemPalace relay deliver the write? (verify with `mempalace__mempalace_get_drawer`)
> 2. **Role ambiguity**: Do multiple agents think they own the same resource? (introduce clear ownership)
> 3. **Spec drift**: Did task spec change mid-execution? (checkpoint before each agent invocation)
> 4. **Cascade failure**: Is failure in agent A causing failure in agent B? (isolate + circuit break)
> **Why**: MAST taxonomy shows 36.94% of failures are coordination failures, not capability failures. Capability is fine; coordination is broken.

**If→Then #3: Idempotent Retry Design**

> **If** [Need to retry a failed agent action]
> **Then** [Design for idempotency before retrying:]
> - Generate unique idempotency key per operation (e.g., `f"{task_id}_{attempt}_{timestamp}"`)
> - Check if key was already processed before re-executing
> - Use "create if not exists" semantics, not blind "create"
> **Why**: Non-idempotent retries compound failures — a 99% reliable tool in a 7-step chain drops to ~93% reliability without idempotency

**If→Then #4: Circuit Breaker for Multi-Agent Chains**

> **If** [A sub-agent or tool consistently fails after 3 retries with exponential backoff]
> **Then** [Trip the circuit breaker:]
> 1. **Open**: Fail fast on all calls to the failing component (no more retries)
> 2. **Half-open**: After 30s, allow one probe call to test recovery
> 3. **Closed**: If probe succeeds, resume normal operation
> **Why**: Without circuit breakers, retry storms cascade — one dead service drags down the entire agent chain and burns tokens

**If→Then #5: Spec-Driven Agent Task Definition**

> **If** [Defining a task for delegate_task subagent]
> **Then** [Use JSON schema spec format with explicit fields:]
> ```json
> {
>   "agent_id": "unique_id",
>   "role": "specific role description (≥10 chars)",
>   "capabilities": ["list of specific capabilities"],
>   "constraints": {"max_iterations": N, "timeout_seconds": N},
>   "success_criteria": ["list of verifiable outcomes"]
> }
> ```
> **Why**: MAST study shows 41.77% of failures stem from specification ambiguity. Agents cannot "read between lines" — every ambiguity becomes a suboptimal decision point.

---

## Key Research Findings

| Source | Key Finding |
|--------|-------------|
| MAST (NeurIPS 2025) | 14 failure modes, 3 root categories, 1,600+ traces |
| Augment Code (2026) | MCP (Model Context Protocol) addresses coordination through schema-enforced JSON-RPC 2.0 communication |
| Taskade (2026) | 99% reliable × 7 steps = 93% chain reliability; recovery is the differentiator |
| arXiv:2603.06847v1 | Faults frequently traverse architectural boundaries (token mgmt → auth, datetime → scheduling, state → memory) |

---

## Hermes-Specific Context

- **delegate_task**: L0 isolated (no shared memory). Each subagent is an island.
- **MemPalace MCP**: Only L3 relay for cross-agent memory. If MemPalace write succeeds but read fails, that's a coordination failure (not a capability failure).
- **Hermes cron**: 14/14 jobs all `ok` — infrastructure is healthy.
- **Creative pipeline SOPs**: 7 SOPs exist (intent classification, pipeline DAG, moderation, output quality, style memory, webhook verification, execution state). Execution state: empty (never triggered).

---

## Related Entries

- [[hermes-internal#delegate_task L0 isolation]] — subagent isolation confirmed
- [[agent-memory-systems#MemPalace MCP L3 relay]] — cross-agent memory relay only path
