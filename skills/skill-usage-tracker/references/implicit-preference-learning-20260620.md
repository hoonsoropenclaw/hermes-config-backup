# Implicit Preference Learning — Research Summary (2026-06-20)

Source: arxiv:2606.05828 + Medium/DPO survey.

## Problem This Solves for Hermes

Hermes has no `on_first_turn_hook`. Even when we build a logging system (`skill-usage-tracker`), it stays at 0 ratings for days because:
1. We forget to invite ratings (Layer 1 failure)
2. Users don't spontaneously give structured feedback

Research shows two complementary paths:

---

## Path A: Structured Implicit Feedback (DPO Lens)

**Key insight** (from Medium/DPO article): Natural language feedback ("that's wrong", "try more concise", "that's exactly right") = binary preference signal. Each user reply is preference data.

**Hermes application**: Instead of waiting for explicit "rate this 1-5", treat the user's next message as implicit feedback:

```
User says "好" / "可以" → combo_rating ≥ 4 (positive)
User says "不行" / "太慢了" → combo_rating ≤ 2 (negative)
User refines request → quality was suboptimal (combo_rating = 3)
User sends correction mid-task → combo_rating = 2, individual_ratings[skill] -= 1
```

**Format** (append to ~/.hermes/skill-usage/<date>.jsonl):
```json
{"ts": "...", "session_id": "...", "task_summary": "...", 
 "actual_skills": [...], "combo_rating": 4, 
 "implicit_signal": "user said '好' after delivery",
 "comment": "from '好' → treated as positive implicit feedback"}
```

**Why this works**: No extra burden on user. Rating invitation is opt-in ("如果你想給我回饋，告訴我幾顆星") not opt-out.

---

## Path B: Bandit-Based Skill Selection (Local Harness)

**Key insight** (from arxiv:2606.05828): Decouple statistical preference learning (local, lightweight) from semantic intent parsing (LLM). The local statistical estimator maintains per-user empirical success-rate for (user, domain, skill) triples.

**Hermes architecture equivalent**:

```
Local Statistical Primitive (Python dict, ~/.hermes/skill-usage/preferences.json):
  {
    "mmx-cli": {"attempts": 6, "successes": 5, "avg_rating": 4.2},
    "school-bulletin-system": {"attempts": 2, "successes": 2, "avg_rating": 4.5}
  }

Remote LLM (Exception Handler):
  - Only used when user names a specific skill explicitly
  - NOT on the critical path for routine skill selection
```

**Three-step decision per task**:
1. Shared Domain Classification: `task → domain` (e.g., "image generation" → `multimodal`)
2. Local Statistical Default: pick skill with highest `avg_rating` for this domain
3. Semantic Override Probe: if user explicitly names a skill, use it

**Current Hermes gap**: Step 2 (Local Statistical) is completely missing. We have no `preferences.json` auto-update mechanism.

---

## Recommended Implementation (Priority Order)

1. **HIGHEST**: Add implicit feedback parsing — no new infrastructure needed, just change how we interpret user messages after task delivery. Patch `session_skill_logger.py` to accept `implicit_signal` field.

2. **MEDIUM**: Create `~/.hermes/skill-usage/preferences.json` and update it when new ratings arrive (auto-update after each `combo_rating` write).

3. **LOWER**: Implement bandit UCB for skill selection (requires ≥ 20 rated entries first).

---

## Related

- `references/auto-trigger-gap.md` — Why Layer 1 fails
- `references/layer2-coverage-gap.md` — Why SKILL.md ≠ actual skill usage
