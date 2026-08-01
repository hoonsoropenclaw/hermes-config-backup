---
name: anti-panic-protocol
description: Handle tool failures under pressure with bounded retries, clean user communication, and safe escalation. Use when commands/tools fail, when repeated retries risk spam or rate limits, or when you need a strict error-response workflow (translate raw errors, attempt safe fixes, then escalate clearly).
---

# Anti-Panic Protocol

- Research: see `references/self-healing-research.md` (production stacks, 4-stage loop, failure taxonomy)
Fail without collateral damage.

## Workflow (strict)
1. Identify the failure in one sentence.
2. Attempt fix #1 (direct, safe, minimal).
3. Attempt fix #2 (bounded alternative).
4. Stop retrying.
5. Escalate in plain language with next action.

Never exceed 2 fix attempts unless user explicitly asks.

## User-facing communication format
Always send:
- What failed
- What you tried
- What happens next

Never send:
- Raw stack traces
- Raw CLI dumps
- Internal tool payloads

## Retry safety
- No retry loops
- Respect cooldowns/rate limits
- One outward message per outcome (no duplicates)
- If rate-limited: wait for next allowed slot

## Verification before done
Before saying “done”, verify outcome:
- Message actually sent
- Event actually created
- Post actually published
- File actually written

If not verified, report as pending/failed, not done.

## Escalation template
Gebruik dit patroon:

"Dit faalde: <korte oorzaak>. Ik heb <poging 1> en <poging 2> geprobeerd. Volgende stap: <concrete actie of vraag>."

## Escalation examples
- "Dit faalde: publish werd afgewezen door rate-limit. Ik heb 1) direct retry en 2) delayed retry geprobeerd. Volgende stap: posten op eerstvolgende toegestane slot, zonder extra spam." 
- "Dit faalde: agenda-event create gaf validation error op datumveld. Ik heb 1) ISO-format gefixt en 2) timezone expliciet gezet. Volgende stap: jij bevestigt datum/tijd, dan maak ik het event direct aan." 
- "Dit faalde: loginflow timed out. Ik heb 1) token-login geprobeerd en 2) browserflow herstart. Volgende stap: ik wacht op jouw OAuth-bevestiging en rond dan automatisch af." 

## Hard stops
Escalate immediately (skip retries) if:
- Risk of destructive action
- Risk of duplicate external sends
- Authentication/security boundary issue
- User says stop/pause

---

## Agent Self-Healing Patterns

When a tool call fails or output validation fails, apply the **4-Stage Recovery Loop**:

### Stage 1 — Validation (before retrying)
Before retrying, check: **Did I produce what I was asked to produce?**
- Success criteria must be *verifiable*, not subjective ("answer good?")
- If validation fails → classify failure type before deciding recovery

### Stage 2 — Failure Classification
| Failure Type | Recovery Action |
|---|---|
| Transient (network, rate limit, timeout) | Exponential backoff + retry |
| Capability (missing tool/auth) | Escalate to parent/parent agent |
| Semantic (malformed output) | Retry with explicit format correction |
| Context overflow | Truncate history, retry with abbreviated context |

### Stage 3 — Contextual Recovery
After classification, apply targeted fix:
- **Transient**: `@retry` with exponential backoff (1s→2s→4s, max 3 attempts)
- **Tool fallback**: Primary API fails → try cached data → try live web search
- **Output corruption**: Retry with different parameters / simplified prompt
- **State corruption**: Roll back to last known good state

### Stage 4 — Learning Integration
After recovery, record:
- `error_type` in state/diagnostics
- Whether fallback succeeded or degraded
- Pattern for next cycle: "if API X fails, use fallback Y"

---

## State-Based Fallback Chain (Tenacity + Fallback)

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

ERROR_TYPES = (ConnectionError, TimeoutError)

@retry(
    retry=retry_if_exception_type(ERROR_TYPES),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
def call_primary():
    """Try primary API."""
    raise ConnectionError("Primary API down")

def call_backup():
    """Try cached data or backup service."""
    return "Fallback: returning cached data"

def call_tertiary():
    """Last resort: live web search or degraded output."""
    return "Fallback: live web search result"

def execute_with_fallback():
    errors = []
    for attempt in range(3):
        try:
            return call_primary()
        except ConnectionError as e:
            errors.append(str(e))
    # Fall through to backup
    try:
        return call_backup()
    except Exception:
        return call_tertiary()
```

---

## Anti-Panic + Self-Healing Combined Protocol

When any tool fails:
1. **Classify** the error (transient / capability / semantic / overflow)
2. **Retry** transient errors with exponential backoff (max 3×)
3. **Fallback** to degraded mode (cached data → static fallback → notify-only)
4. **Escalate** capability/auth errors immediately (do not retry)
5. **Log** error_type + fallback_used for learning

Never retry permanently (bad auth, validation errors). Never silently swallow errors — degraded mode must still produce output AND notify.
