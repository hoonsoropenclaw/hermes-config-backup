# Policy Enforcement & SOP Enforcement for Multi-Agent Systems

Research-backed patterns for enforcing SOPs and policies in agent orchestration.

---

## LangGraph + Guardrails Integration

### NeMo Guardrails (NVIDIA)
- **Docs**: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/langchain/langgraph-integration.html
- **What**: Add policy enforcement to LangGraph agents
- **Pattern**: Install → Configure → Handle policy denials → Runnable examples
- **Installation**: `uv pip install nemo-guardrails[langgraph]`

### Sonnera Harness LangGraph Integration
- **Docs**: https://docs.sondera.ai/integrations/langgraph/
- **What**: Policy enforcement for LangChain/LangGraph agents
- **Covers**: Installation, configuration, handling policy denials

---

## Guardrails vs Human Review (OpenAI Pattern)

From OpenAI API docs:
- **Guardrails**: Automatic checks on input/output/tool behavior
- **Human review**: Pauses run for person/policy approval
- **Together**: Define when run should continue/pause/stop

Implementation:
```
Input validation → Guardrail check → 
  PASS → Continue
  FAIL → Human review or deny
```

---

## CASTER: Cost-Aware Multi-Agent Routing

Paper: arxiv 2601.19793v1

Key insight: Context-aware strategy for task-efficient routing in multi-agent systems.

For Hermes on N100 (4 cores, 31GB RAM):
- Safe concurrency: 6-8 simultaneous sub-agents
- Above 10 may slow down
- Token usage optimization = cost savings

---

## Behavioral Contracts Implementation

Python reference: https://github.com/agentcontract/agentcontract-py

AgentContract specification for formal specification + runtime enforcement.

For Hermes: When implementing agent behavioral constraints:
1. Define behavioral contract (what agent MUST do)
2. Implement runtime checks
3. On violation → enforce consequence (re-execute, log deviation, alert)

---

## Key Pattern: External Validation Loop

```
Agent executes task → 
External validator checks output against SOP →
  Compliant → deliver to user
  Non-compliant → re-execute with deviation note
```

This is Layer 3 enforcement. The validator must NOT be the agent itself (otherwise back to Layer 1).

For Hermes: After sub-agent completes, main agent should check against SOP before delivering.