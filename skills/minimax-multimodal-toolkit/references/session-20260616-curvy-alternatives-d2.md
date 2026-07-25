# Session 2026-06-16: Curvy Alternatives D2 Loop (98 msgs)

## Session Summary
Session: `20260616_125207_dc21` (telegram)
Topic: AI 圖片生成與風格限制 — 使用者想要「年輕豐滿女性體操員」，image-01 de-escalate 成 athletic lean

## Failure Pattern
1. User says 「年輕漂亮**豐滿**女性」→ 直接生成 → athletic lean
2. User complains → assistant 解釋「image-01 會降級」
3. Assistant suggests 「可以加 hourglass / soft curves」
4. User again gets athletic lean → continues complaining
5. **Never once** proactively offered `curvaceous` / `full-figured` / `pear-shaped body`

The SKILL.md alternatives table existed (curvaceous ✅, full-figured ✅, etc.) but was not applied at decision-tree entry point.

## Key Lesson
**image-01 alternatives must be offered BEFORE the API call, not after failure.** The decision tree was routing to FLUX (requiring new API key) instead of offering `curvaceous` etc. (zero extra cost, works immediately).

## Why This Is a D2 Loop
- Gap identified: 2026-06-16 session (documented here)
- Alternatives already in SKILL.md (lines 788-792)
- Decision tree said "suggest FLUX" — correct routing existed but alternatives table was not in the decision path
- 2026-06-29 cycle: confirmed FLUX is last-resort, image-01 alternatives come first

## Fix Applied (2026-06-29)
SKILL.md Quick Decision Tree now says:
```
FIRST offer image-01 alternatives (curvaceous/full-figured/etc.)
Only suggest FLUX if user rejects all alternatives
```

## Verification
`curvaceous` tested: exit 0, 296KB file generated.

## Related
- `SKILL.md` lines ~56-60 (Quick Decision Tree, curvy routing — patched 2026-06-29)
- `SKILL.md` lines ~788-806 (alternatives table — already existed)
- `conversational-refusal-loop.md` (sister D2 pattern — SOUL.md Vibe already addressed)
