# Refusal Pattern D2 Loop: Documented ≠ Practiced

**Session**: metacognitive-learner cycle 2026-06-23

**症狀**: The "3-strike progressive refusal" pattern is well-documented in `minimax-multimodal-toolkit/SKILL.md` (Pre-Execution Request Triage section, 2026-06-22). Yet in actual sessions (e.g., 2026-06-15: 163 messages, 8+ probes, same refusal structure repeated), the behavior didn't change. The documentation exists but the *conversational self-interrupt* didn't happen.

**根因**: SKILL.md tables are passive references — the agent reads them at session start, not dynamically during conversation. There's no mechanism to:
1. Count prior refusals in the current conversation
2. Self-interrupt when the same refusal structure appears for the 3rd time
3. Inject new information before sending the next refusal

**解法**: The real fix requires a behavioral enforcement mechanism (Layer 2.5/3), not just documentation. See `minimax-multimodal-toolkit/references/refusal-anti-loop-20260623.md` for the full analysis.

**預防**: The distinction between "documented SOP" and "enforced SOP in conversation" is fundamental. Layer 1 documentation alone does not change behavior.

**If→Then**: **If** a SOP is documented but user sessions still show the same failure pattern **Then** the SOP alone is insufficient — a behavioral enforcement mechanism is needed, not another documentation update
