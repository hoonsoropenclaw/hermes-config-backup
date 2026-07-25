# Refusal Pattern Anti-Progressive Loop (2026-06-23)

**Scope**: Why the "3-strike progressive refusal" pattern, despite being well-documented in SKILL.md, still fails in actual sessions — and the fix.

**Observation (2026-06-23)**: The 3-strike progressive refusal pattern was identified as a D2 loop gap in the 2026-06-16 session (163 messages). SKILL.md was updated with the pattern. But the 2026-06-23 cycle found that in actual conversations, the refusal structure is still being repeated identically — the documentation exists but the *conversational behavior* hasn't changed.

**Root cause**: The pattern is documented as a table, but that's a passive reference. It doesn't trigger the agent to interrupt itself mid-conversation when it notices the 3rd identical refusal. The agent only reads the SKILL.md at session start, not dynamically during conversation.

---

## The Anti-Pattern in Practice

From session 2026-06-15 (163 messages, 8+ probes):

```
[User]: [boundary request]
[Assistant]: Brief refusal, no redirect
[User]: [rephrase]
[Assistant]: Same refusal structure, different words, no new info
[User]: [rephrase again]
[Assistant]: Same refusal structure again
... repeated 5+ times
```

The agent kept refusing the same way without:
- Explaining *why* the category is off-limits
- Offering a specific alternative domain
- Signaling "I'm not going to change my answer on this"

---

## The Fix: Interrupt-Then-Redirect (2026-06-23)

**Rule**: If the same refusal structure has been used 2+ times in a conversation, the next refusal MUST include ALL of:

1. **Why this category is off-limits** — specific reason, not generic
2. **A concrete alternative domain** — specific to what the user asked
3. **A "hard line" signal** — explicitly state this is not a capability issue

**Example of what the 3rd refusal must contain**:

```
[Still about the boundary topic]
"I can't help with this request. Here's why [specific category reason].
I want to be direct: this isn't something I'll do under any packaging.
What I CAN do instead: [specific alternative]. 
Interested in that direction?"
```

**NOT**: "I can't generate this type of content. I'm sorry, I can't help with that." (identical to strike 1)

---

## Detection Trigger

**If** during a conversation, the same refusal structure (same pattern, same domain) appears for the 3rd time
**Then** the agent MUST self-interrupt and add the three elements above before the refusal is sent

**This is not natural conversation flow** — it requires actively counting prior refusals and interrupting the normal response generation. The SKILL.md table alone doesn't drive this behavior.

---

## If→Then

**If** user probes the same boundary request 2+ times **Then** on the next refusal, explicitly state: (1) why, (2) a concrete alternative, (3) a hard line signal

**If** the refusal is identical in structure to the previous 2 **Then** this is a pattern failure — add new information before sending
