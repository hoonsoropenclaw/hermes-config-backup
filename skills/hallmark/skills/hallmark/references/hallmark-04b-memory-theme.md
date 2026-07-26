
Before loading any visual ruleset, **read the slim index at [`references/macrostructures.md`](references/macrostructures.md) and pick one of the twenty-one named macrostructures.** The index is one-line-per-macro; pick a name, then **load ONLY that one per-macro file** from `references/macrostructures/` (e.g. `references/macrostructures/05-workbench.md`). Do not load the whole catalogue — that's ~37 KB of dead weight for a single pick. Each macrostructure is a complete page-shape — heading placement, body composition, divider language, button voice, image treatment, reveal — bundled as a single named choice. Picking one named macrostructure is faster and more varied than choosing six independent axes from scratch.

**Diversification rule (mandatory).** Before you pick:

1. Look in the target codebase for an existing `/* Hallmark · macrostructure: <name> · ... */` stamp at the top of any CSS file. If you find one, your pick must be a *different* macrostructure.
2. If you have produced any other Hallmark output for this user in this session, your pick must be a different macrostructure than the last one.
3. **The Specimen macrostructure (numbered left-margin labels + huge serif + asymmetric spans + typographic CTA) is no longer a default.** Reach for it only when the brief is explicitly editorial, foundry-adjacent, or the user has named it.

**Theme-diversification rule (mandatory).** Picking a different macrostructure isn't enough on its own — two consecutive Hallmark outputs can share a theme even if their structures differ, and the result reads as repetition. Two consecutive themes must differ on **at least one** of three axes:

- **Paper band** — dark (L < 30 %) / mid (30–85 %) / light (> 85 %), per the theme's `--color-paper` lightness
- **Display style** — italic-serif (Specimen, Studio, Atelier) / roman-serif (Newsprint, Salon, Linen) / geometric-sans (Plume, Manifesto) / mono (Terminal) / display-condensed-italic (Sport) / display-heavy (Brutal) / system-native (Quiet) / risograph-bold (Riso)
- **Accent hue** — warm (red / orange / amber: 10–60°) / cool (blue / indigo / cyan: 200–300°) / neutral (no chromatic accent: Quiet) / chromatic-other (green: Studio · sage: Garden · phosphor: Terminal)

If the previous output was Specimen (light · italic-serif · warm), the next can be Studio (light · italic-serif · chromatic-green) — the *accent hue* differs. But the next can't be Salon (light · roman-serif · warm) which only differs on display style and shares both paper band and accent — pick a more distant theme.

The per-theme axis values live as comments at the top of each theme's tokens block in [`site/css/tokens.css`](../../site/css/tokens.css). When in doubt, name your candidate theme out loud and identify its three axis values; if two of three match the previous output, redirect.

**State your pick.** Before writing any code, say "Macrostructure: <name>. Theme: <name>. Differs from the last on: <axes>." in plain text. This is a deliberate accountability step — picking on the page (not in your head) prevents the default-attractor sameness that kept the skill emitting Specimen output.

If the brief is genuinely vague (no theme, no tone), do **not** default. Offer the user three macrostructures from *categorically different* groups (e.g. one grid-led like Bento, one document-led like Long Document, one poster-led like Manifesto). Three concrete choices, not seven abstract tones.

The macrostructure picks five of the six structural axes for you; you only need to pick the reveal yourself. The deeper axis catalogue is still in [`references/structure.md`](references/structure.md) when you need to deviate from the macrostructure's defaults.

**Pick a nav archetype (N1–N10) and a footer archetype (Ft1–Ft8) at this step.** They are not optional chrome; they are part of the page's structural fingerprint. Read the slim index at [`references/component-cookbook.md`](references/component-cookbook.md) and the routing tables at its bottom — the genre's default plus the acceptable alternates. Then **load ONLY the picked archetype files** from `references/components/` (e.g. `components/n5-floating-pill.md` + `components/ft5-statement.md`). A typical build loads 5–7 archetype files total (1 hero + 1 section head + 1–2 features + 1 CTA + 1 footer + 1 nav). Do not load the cookbook end-to-end — that's ~55 KB of archetypes you won't use. State both picks alongside the macrostructure: *"Macrostructure: Marquee Hero. Nav: N5 Floating pill. Footer: Ft5 Statement. Theme: Bloom."*

**Default away from N1 and Ft3.** N1 (wordmark + 4–5 inline links + button-right at full width) and Ft3 (4 columns of links + social row + tiny copyright) are the most-recognised AI fingerprints. Reach for N5–N9 and Ft1/Ft2/Ft4/Ft5/Ft6/Ft7/Ft8 by default; reach for N1 only when the page genuinely has 2 destinations and the genre allows it; reach for Ft3 only on a genuine docs root or hub.

**Diversification extends to nav + footer.** Across consecutive Hallmark runs in the same project session (per `.hallmark/log.json`), no two outputs should share the same nav archetype OR the same footer archetype. If the previous run used N5 + Ft5, the next picks N6/N7/N8/N9 + Ft1/Ft2/Ft4/Ft6/Ft7/Ft8 from the routing tables. The nav and footer picks are recorded in the macrostructure stamp at Step 6.

### 2.5. Check project memory

If the project has a `.hallmark/log.json` file (created by previous Hallmark runs), **read it before** picking the macrostructure or theme. The schema is a JSON array, newest entry first:

```json
[
  { "date": "2026-04-30", "macrostructure": "Bento Grid",   "theme": "Linen",   "enrichment": "E1 clipped-edge",  "brief": "Tracejam · SaaS observability" },
  { "date": "2026-04-28", "macrostructure": "Long Document","theme": "Linen",   "enrichment": "E5 hand-built SVG", "brief": "Maple Street Bread · bakery" },
  { "date": "2026-04-25", "macrostructure": "Manifesto",    "theme": "Manifesto","enrichment": "none",            "brief": "Meridian · studio manifesto" }
]
```

Use the **last 3–5 entries** to inform diversification:
- Your macrostructure pick must not match any of the last three.
- Your theme pick must differ from the last on at least one axis (see the theme-diversification rule above).
- Your enrichment pick should not be the same enrichment archetype as the last (`E1 clipped` twice in a row reads as templated, even with different content).

If the file doesn't exist, this is the first Hallmark run for this project — no constraint, but **you'll create the file in Step 6**.

If the project has a CSS stamp but no `log.json`, infer one entry from the stamp and proceed.

**State the rotation in plain text before picking.** This is the user's accountability line for diversification — picking on the page (not in your head) is what keeps the skill from drifting back into Bento-Grid-by-default. The format:

> *"Last 5 builds: Bento Grid (Tracejam) · Bento Grid (Foundry) · Long Document (Maple) · Manifesto (Meridian) · Quote-Led (Tide). Bento Grid used 2 of 5 — picking from {Marquee Hero, Stat-Led, Workbench, Letter} this time. I'll go with Marquee Hero."*

Then the theme rotation, on the next line:

> *"Last 3 themes: Linen · Plain · Salon. Picking from {Newsprint, Atelier, Studio, Garden} — Newsprint differs on display style and accent hue."*

**Three sample shapes** to imitate:

- **First-time** (no `log.json`, fresh project): no rotation block at all — just the macrostructure pick. *"This is the first Hallmark run for this project. Picking Long Document — fits the Coffeebox brief's editorial tone."*
- **Mature project** (5+ entries in `log.json`): the format above — frequency count, exclusion list, pick.
- **User overrode last run** ("use Bento Grid again, I want the same shape"): *"Last build was Bento Grid (you requested it). You've asked for it again — I'll pick different knob values. Knob deltas: tiles=8 (was 6), accent=full-bleed (was corner-only), spans=irregular (was even). Same archetype, different fingerprint."*

The rotation block keeps the user inside the discipline without making them read the rules. Skip it and the user starts thinking the diversification is theatre.

### 2.6. Theme route — studied-DNA, catalog, or custom

By the time you reach this step, one of four things is true:

0. **A `study` diagnosis was emitted earlier in this conversation and the user is asking to build from it** (phrases: *"build it"*, *"make it"*, *"use this DNA"*, *"build with this"* — immediately following the diagnosis) → theme route is **studied-DNA**. **Skip catalog/custom dispatch entirely.** The studied paper OKLCH, accent OKLCH, type roles (with named candidates), macrostructure, and nav/footer archetypes from the diagnosis become the locked system for this build. Diversification is suspended — you're following an external DNA, not rotating the catalog. The Step 6 stamp records `theme: studied-DNA (source: <URL or image>)` plus the actual OKLCH/font values inline. **If the user later pivots with phrases like *"use Linen instead"* / *"ignore the DNA"* / *"rotate to a different theme"*,** route back to the normal dispatch below and resume diversification. Continue to Step 3.
1. **The user named custom** (because they said so, or because Step 1's signal detection fired and they confirmed) → load [`references/custom-theme.md`](references/custom-theme.md), ask the **one** follow-up (vibe in 4–8 words + optional anchor colour), construct the OKLCH palette + free-font pairing, compute the three axis values (paper-band / display-style / accent-hue), then continue to Step 3.
2. **The user named catalog** (or implicitly accepted it by not naming custom) → pick one of the 22 named themes per the diversification rule above. Existing flow — continue to Step 3.
3. **Neither was discussed** (Step 1's signals didn't fire — vanilla brief) → default to **catalog**. Do not pause. Do not ask. Continue to Step 3.

**Custom is a quiet branch, not a default question.** Most briefs route to catalog and the user never sees the words "catalog" or "custom." The 22 named themes plus the rotation rule already deliver structural variety; the fork is reserved for when the brief specifically asks for a tuned look the catalog can't carry.

A custom theme is a **complete** OKLCH palette + font pairing tuned to the brief — not a one-off colour swap, not an excuse to bypass the rules. Every constraint in [`color.md`](references/color.md), [`typography.md`](references/typography.md), and [`anti-patterns.md`](references/anti-patterns.md) still applies. The 65 slop-test gates fire unchanged. The Step 5 preview block surfaces the palette + pairing in plain text **before** any code is emitted, so the user can redirect.

The diversification rule is theme-route-blind: a custom run that follows another custom (or a catalog) must differ on at least one of the three axes from the previous entry, same as catalog-vs-catalog. Custom entries record their three axes explicitly into `.hallmark/log.json` (see [`custom-theme.md`](references/custom-theme.md) § F).

### 3. Load the visual ruleset

The non-negotiables live in [`references/`](references/). **Be precise about what to load when. Discipline matters — over-eager loading is the largest avoidable cost of running Hallmark.**

**Always-load (eager — 1 file):**
- The genre file picked in Step 1 — [`genres/editorial.md`](references/genres/editorial.md), [`genres/modern-minimal.md`](references/genres/modern-minimal.md), [`genres/atmospheric.md`](references/genres/atmospheric.md), or [`genres/playful.md`](references/genres/playful.md). Scopes everything downstream.

**Index-then-pick (read the slim index, then load only the picks):**
- [`macrostructures.md`](references/macrostructures.md) — slim index of the 21 macros. Pick one name from the index, then load ONLY `references/macrostructures/<NN-slug>.md` for that pick. **Never load the whole index plus more than one per-macro file in a single build.** ~30 lines per per-macro file vs. 660 lines for the old monolith.
- [`component-cookbook.md`](references/component-cookbook.md) — slim index of 46 component archetypes (9 heroes, 5 section heads, 6 features, 4 CTAs, 4 testimonials, 8 footers, 10 navs) + the nav + footer routing tables at the bottom. Pick your archetype codes (H#, S#, F#, C#, T#, Ft#, N#) from the index, then load ONLY the matching `references/components/<code>-<slug>.md` files. A typical build loads 5–7 archetype files. **Loading the cookbook end-to-end or pre-loading more than one archetype per category is the single biggest token waste in the skill — don't.**

**Load-per-build (universal rules — load every build):**
- [`typography.md`](references/typography.md) — fonts, scale, pairing, weights, measure, hero headline sizing
- [`color.md`](references/color.md) — OKLCH, palette construction, accent discipline
- [`layout-and-space.md`](references/layout-and-space.md) — 4 pt scale, grid-breaks, asymmetry, depth
- [`motion.md`](references/motion.md) — durations, easings, what to animate, reduced-motion
- [`copy.md`](references/copy.md) — verbs, labels, error structure, link text
- [`anti-patterns.md`](references/anti-patterns.md) — the named tells you must not emit

**Load-conditionally (only when the page actually needs it — be honest, do not pre-load "for safety"):**
- [`microinteractions.md`](references/microinteractions.md) — load whenever the output has *any* interactive element (buttons, inputs, modals, tabs, dropdowns, toasts, drag handles, copy buttons). That is most pages.
- [`interaction-and-states.md`](references/interaction-and-states.md) — load when the page has stateful UI (forms, command palettes, optimistic updates).
- [`responsive.md`](references/responsive.md) — load when mobile is in scope.
- [`structure.md`](references/structure.md) — load only when deviating from a named macrostructure.
- [`hero-enrichment.md`](references/hero-enrichment.md) — **do NOT load at Step 4 unless the image-need check in the next paragraph returns YES.** Most builds are typography-only and never touch this file. The decision is one quick read of the brief, not a defensive auto-load.
- [`custom-craft.md`](references/custom-craft.md) — load only when an enrichment archetype requires construction (CSS art, SVG, declarative animation, etc.).
- [`assets.md`](references/assets.md) — load only when an enrichment archetype needs an external asset (icons, illustration, photography, Lottie).
- [`custom-theme.md`](references/custom-theme.md) — load only when Step 2.6 routes to custom. The full custom branch (palette construction, font pairing, axis computation) lives there; SKILL.md only carries the dispatch.
- [`design-md.md`](references/design-md.md) — load only when the user explicitly asks Hallmark to lock the system into a portable file (phrases: *"lock the system"*, *"give me a design.md"*, *"make this portable"*, etc.). Opt-in; never fires on a vanilla build.
- [`preview-examples.md`](references/preview-examples.md) — load only if you need a worked example of the Step 5 preview block format. The bullet list in Step 5 itself is normally enough; reach for the file only when picking unusual macrostructures / custom themes.

**Load-at-the-end (Step 7 only):**
- [`slop-test.md`](references/slop-test.md) — **strictly Step 7, after Build.** The 66 gates are a post-emit check, not a pre-emit reference. Pre-loading slop-test.md costs ~7K tokens for nothing — the gates inform fixes, not generation. If a gate fails at Step 7, fix and re-test; do not consult the file earlier "to know what to avoid" — that's what `anti-patterns.md` is for.
- [`contract.md`](references/contract.md) — load at handoff time for output-contract + scope rules.
- [`export-formats.md`](references/export-formats.md) — load at Step 6 only when the project warrants multi-format exports (i.e. has a `design.md`). Single-page builds emit `tokens.css` from the in-memory token state and don't need this file.

**Verb-specific:**
- [`verbs/audit.md`](references/verbs/audit.md), [`verbs/redesign.md`](references/verbs/redesign.md) — load only when that verb runs.
- [`study.md`](references/study.md) — load only when `hallmark study` runs.

**Human-only (do NOT auto-load):**
- [`../../docs/recipes.md`](../../docs/recipes.md) — eight worked briefs for human readers.
- [`../../docs/study-examples.md`](../../docs/study-examples.md) — three worked DNA-extractions for human readers.

### 4. Decide on hero enrichment
