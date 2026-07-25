# Known Risky Prompt Combinations for image-01

## High-Risk Combinations That Trigger Content Filter

### Category 1: Angle + Artistic Style + Person
**Risk**: Triggers aesthetic/NSFW filter despite no explicit content.
**Example**: `bird's-eye view + looking down + artistic style keywords + person`

**Why it triggers**: Elevated camera angle + artistic style + person reads as "looking down at subject" which has boudoir/suggestive connotations even without explicit content.

**Safe alternative**: Use `front view` or `side view` with artistic style, drop the elevated angle.

---

### Category 2: Body-Shape Adjectives + Fashion Terms
**Risk**: Model de-escalates body description, filter may trigger.
**Example**: `young beautiful curvy woman in dress` or `豐滿女人穿著禮服`

**Why it triggers**: "Curvy/豐滿" signals body shape, combined with fashion = model defaults to safe athletic build and may filter.

**Safe alternative**: Use neutral build descriptors: `young woman, athletic build` or omit build entirely.

---

### Category 3: Off-Shoulder / Revealing + Elevated Camera
**Risk**: Strong visual suggestiveness signal.
**Example**: `off-shoulder dress + camera positioned above` or `禮服滑落 + 俯視`

**Why it triggers**: Off-shoulder clothing with overhead camera produces boudoir aesthetic.

**Safe alternative**: Keep camera at eye level or below for formal fashion shots.

---

### Category 4: Suggestive Pose Keywords
**Risk**: Rejection or sanitization.
**High-risk terms**: `M字腿`, `sitting spread`, `legs crossed`, `provocative pose`, `seductive`

**Safe alternative**: Neutral activity descriptions: `walking`, `standing`, `sitting on chair`, `reading`.

---

### Category 5: Clothing + Pose Collective Signal (2026-06-30)
**Risk**: Multiple individually-neutral clothing descriptors stacked with any pose keyword triggers filter as collective suggestiveness — even though each individual term is safe on its own.

**Example**: `制服短裙 + 高跟鞋 + M字腿` — each term individually unremarkable, but the combination signals suggestive intent to image-01's collective assessment.

**Why it triggers**: image-01 does not evaluate keywords in isolation; it assesses the prompt as a whole. Stacking multiple clothing/footwear descriptors with a pose keyword creates a cumulative signal that exceeds any single-category threshold.

**High-risk stack patterns**:
- Uniform/costume outfit + any pose keyword + body-shape adjective
- Female professional attire (護士服/OL套裝/制服) + short-skirt or fitted clothing + sitting pose
- Footwear descriptor (高跟鞋/細跟/靴) + any above-the-knee clothing + pose

**Safe alternative**: Use a single clothing descriptor + neutral standing/walking activity. Avoid stacking multiple clothing or footwear terms with any pose keyword.

**Session evidence** (2026-06-16): `young beautiful woman, 制服短裙, M字腿` — second request was filtered despite M字腿 already being a known Category 4 term. The addition of "制服短裙" to the existing Category 4 keyword created a Category 2+4 collective trigger.

---

## Filter Trigger Indicators

| Indicator | Meaning |
|-----------|---------|
| `n=4` but only 2 files created | Content filter partially accepted prompt |
| File sizes ~200KB vs expected 350KB+ | Model simplified generation |
| `content filter` in assistant message | Explicit filter activation |
| `⚠️` warning in output | Possible filter triggered |

---

## Session Reference
- `image-01-tradeoffs-20260616.md` — Full session log with actual prompts and outputs
