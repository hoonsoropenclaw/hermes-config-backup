# Shipping ≠ Adoption — D2 Loop Trap (2026-06-21)

## Core Insight

Establishing a skill (SKILL.md written, scripts deployed, SOPs documented) ≠ the skill is adopted and active. This is the "D2 Loop Trap": the same gap is identified across multiple cycles, recommendations are documented, but no actual behavioral change occurs in the agent's execution.

## Product Management Analogy

| Stage | Feature Adoption | Hermes Skill |
|-------|-----------------|--------------|
| Shipping | Feature code merged | SKILL.md written + scripts deployed |
| Discoverability | Users know feature exists | Skill documented in skills list |
| Activation Energy | User must try it once | Hermes must execute SOP-A once in a real task |
| Adoption | User returns voluntarily | User replies with star rating |

## The D2 Loop Trap Pattern

1. **Cycle 1**: Identifies gap → recommends "create X skill"
2. **Cycle 2**: Creates X skill (SKILL.md + scripts) → system exists, SOP written → recommends "use X in next task"
3. **Cycle 3**: Gap still present → "X skill exists but never triggered" → recommends "ensure X is in task handoff" → **loop back to Cycle 1**

**Root cause**: The act of building (Cycle 2) is mistaken for the act of solving (Cycle 3). No enforcement mechanism forces the agent to actually use the newly-built skill in the next task.

## Detecting the Trap

- Same gap identified in 2+ consecutive cycles
- SKILL.md exists for the gap topic
- But `stat` on target script/SKILL.md shows no new mtime changes across those cycles
- `analyze.py` shows 0 entries despite SOP being "complete"

## The Correct Exit: D3 (Implementation)

When the same gap appears in Cycle 2 with an existing (but inactive) skill:

**Do NOT** research or re-document. **DO**:
1. Take the existing skill's SKILL.md
2. Run its scripts against a real session (even historical)
3. Confirm mtime updated on the skill directory
4. Deliver one real output that proves the skill was executed

## Verification Commands

```bash
# Confirm skill directory mtime changed THIS cycle
stat -c '%y' ~/.hermes/skills/<skill-name>/SKILL.md

# Confirm post_delivery.py ran in this session
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
  --session <session_id>

# Confirm analyze.py sees the new task count
python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py
```

## Related References

- `references/auto-trigger-gap.md` — why Layer 1 (self-reported) tracking fails
- `references/layer2-coverage-gap.md` — why SKILL.md coverage ≠ actual work
- `references/d3-exit-post-delivery-20260621.md` — post_delivery.py D3 exit execution record
