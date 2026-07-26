# Hallmark — Disciplines that hold across every verb

## Disciplines that hold across every verb

These four disciplines are **not** verb-specific. They apply to default Design, `audit`, `redesign`, `study`, and component-scope alike. They sit alongside the slop test, not inside one branch of it.

1. **Pre-emit self-critique.** Before handing back any output, score it 1–5 on six axes — Philosophy, Hierarchy, Execution, Specificity, Restraint, Variety. Anything **< 3** triggers a revision pass. Stamp the six scores at the top of the artifact (`/* Hallmark · pre-emit critique: P5 H4 E5 S4 R5 V5 */`). See [`references/slop-test.md`](references/slop-test.md) § Pre-emit self-critique.

2. **Honest copy — no fabricated content.** If the user did not supply a metric, do not invent one. Stat-led layouts, comparison rows, and proof bars must use real numbers, a placeholder (`—` plus a labelled grey block, "metric to confirm"), or a different macrostructure. *"+47 % conversion"*, *"trusted by 50,000+ teams"*, and *"10× faster"* are slop the moment they're invented. Same rule for testimonials, logos, and case-study counts. See [`references/anti-patterns.md` § Invented metrics](references/anti-patterns.md) and slop-test gate **56**.

3. **Locked tokens — no mid-render improvisation.** Once a theme is selected at Step 2.6, every colour and every `font-family` declaration in the artifact must reference a named token (`var(--color-accent)`, `font-family: var(--font-display)`). Inline OKLCH / hex / `rgb()` values, or a `font-family: "Some Font"` declaration that bypasses the token block, are not allowed. If a value is needed that doesn't exist as a token, lift it into the token block as a new named variable, then reference it. See [`references/anti-patterns.md` § Mid-render token improvisation](references/anti-patterns.md) and slop-test gate **58**.

4. **Re-drawn chrome forbidden.** Hallmark must not hand-build fake browser bars (URL pill + traffic-light dots), fake phone frames, fake code-block windows (mock title bar + dots wrapping a `<pre>`), or fake IDE chrome — the user's environment already supplies real chrome. Use real screenshots wrapped in a `<figure>` (with at most a hairline border), or omit the chrome and let the content stand on its own. See [`references/anti-patterns.md` § Re-drawn UI chrome](references/anti-patterns.md) and slop-test gate **57**.

5. **Mobile responsiveness — every emit verified at 320 / 375 / 414 / 768 px.** Hallmark's output must render flawlessly at all four widths. The non-negotiables: no horizontal scroll (gate 36), no two-line clickable text — buttons, primary nav links, footer links, breadcrumbs, CTAs (gate 59); image-bearing grid tracks use `minmax(0, 1fr)`, never bare `1fr` (gate 61); root has `overflow-x: clip` on both `html` and `body` — never `hidden` (gate 62); display headers wrap inside long words via `overflow-wrap: anywhere; min-width: 0` (gate 63); section heads collapse to one column on mobile across every theme variant (gate 64); radio-tab patterns don't scroll-jump (gate 65). See [`references/responsive.md` § Mobile — non-negotiable](references/responsive.md). This is a hard floor, not a wish list.

---

