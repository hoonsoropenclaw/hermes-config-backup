# D2 Loop Self-Interrupt — Tool-Call Retry Pattern (2026-06-25)

## Context

**Session**: 2026-06-16 `AI 圖片生成與風格限制` (98 messages)

**Problem**: mmx image generation failed with `exit code 3 No credentials found`. The agent attempted the same `execute_code` + `awk` regex pattern 6 times — each time getting the same error — before finally switching to `terminal()` bash subprocess and succeeding.

**Session length cost**: 98 messages for what should have been a 4-step workflow.

---

## The Pattern

```
Attempt N: execute_code → mmx → "No credentials found" → retry
Attempt N+1: execute_code → mmx → "No credentials found" → retry
Attempt N+2: execute_code → mmx → "No credentials found" → retry
... (6 total attempts)
Only THEN: switch to terminal() → success in 1 call
```

**Root cause**: The agent knew the `execute_code` vs `terminal()` distinction existed (documented in the skill), but didn't apply it when it mattered. The documentation existed but wasn't consulted as a decision trigger.

---

## D2 Loop Self-Interrupt Rule

**If the same failure mode occurs 3+ times within a session:**

1. **Name the specific error** — not just "it failed", but `exit code 3`, `awk: unterminated regexp`, `aspect_ratio must be one of...`
2. **Name the current execution context** — `execute_code` vs `terminal()`, Python subprocess vs bash subprocess
3. **State the switch explicitly** — tell the user what you're about to do and why
4. **Execute the switch** — don't continue retrying the same context

**Format for the interrupt statement:**
```
[Diagnosis] I see [error] occurring in [context]. 
The known fix is to switch to [alternative context].
Making that change now.
```

---

## Cross-Skill Link

This is the **tool-call variant** of the conversational refusal loop pattern documented in `references/refusal-anti-loop-20260623.md`. Both share the same underlying principle:

> **A document in the skill library does not equal behavior change during a session.**

The interrupt must be **triggered during the session**, not just referenced after the fact.

---

## If→Then

**If** the same tool-call error repeats 3+ times in a session  
**Then** pause, name the error + context, state the switch, execute the switch — stop retrying the same path

**If** session tool-call count exceeds 15 without a clean image gen exit  
**Then** apply the D2 interrupt before continuing

---

## Related

- `references/refusal-anti-loop-20260623.md` — conversational refusal loop (sister pattern)
- `references/image-generation-pipeline.md` §Step 3.5 — pipeline-integrated self-interrupt step
