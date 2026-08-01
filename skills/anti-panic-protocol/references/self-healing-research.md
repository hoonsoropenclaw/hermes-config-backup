# Self-Healing Agent Patterns — Research Summary

## Key Research Findings

### Market Context
- AI agents with self-healing reached **$7.92B in 2025**, projected $236B by 2034 (45.82% CAGR)
- **67% of AI system failures** stem from improper error handling, not algorithmic issues
- Self-healing implementations achieve **60% reduction in downtime** on average

### Production Patterns (miaoquai.com — 95+ days 24/7)

**4-Layer Error Recovery Stack:**
| Layer | Mechanism | Scope |
|---|---|---|
| L1: Connection | Exponential backoff 1s→60s + 30% jitter | Network/transient |
| L2: Model | Opus→Sonnet→Haiku→Queue fallback | API failures |
| L3: Tool | 30s timeout per tool; isolate failures | Tool calls |
| L4: Escalation | Notify + pause for budget/capability | Irrecoverable |

### Key Insight
> "Error recovery is one of the more underdesigned parts of most agent systems."
> — Anthropic SDK Python Discussion #1341

## Failure Classification Quick Reference

```
transient    → network hiccups, rate limits, 429/500/502/503/504 → exponential backoff + retry
budget       → cost ceiling hit → pause task, notify orchestrator
capability   → missing tool / auth → escalate to parent agent
semantic     → malformed JSON / validation → retry with explicit format correction
```

## 4-Stage Recovery Loop

1. **Validation** — "Did I produce what I was asked to produce?" (not "is it good?")
2. **Detection** — Classify failure type before deciding recovery strategy
3. **Contextual Recovery** — Targeted fix per failure type (never blind retry)
4. **Learning Integration** — Record error_type + fallback_used for next cycle

## Tools Available in This Environment

- `tenacity` — installed and tested (Python 3.11)
- Exponential backoff: `@retry(wait=wait_exponential(multiplier=1, min=1, max=10))`
- Jitter: `wait_exponential_jitter(initial=1, max=30)` for thundering herd prevention
- State-based fallback: chain primary → backup → cached → degraded with error accumulation

## Sources

- [Anthropic SDK Python Discussion #1341](https://github.com/anthropics/anthropic-sdk-python/discussions/1341) — Production 4-layer stack
- [Zylos Research — AI Agent Self-Healing](https://zylos.ai/research/2026-02-17-ai-agent-self-healing-auto-recovery) — Market data + patterns
- [DEV Community — Self-Healing Agent Pattern](https://dev.to/the_bookmaster/the-self-healing-agent-pattern-how-to-build-ai-systems-that-recover-from-failure-automatically-3945) — 4-stage recovery
- [LangGraph Error Handling](https://machinelearningplus.com/gen-ai/langgraph-error-handling-retries-fallback-strategies) — State-based retry patterns
