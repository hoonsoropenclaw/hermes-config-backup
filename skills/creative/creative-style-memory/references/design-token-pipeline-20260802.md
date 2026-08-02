# Design Token Pipeline — W3C DTCG v2025.10 (Cycle 551)

**Status**: EXECUTED (D2→D3 exit) — `creative_brand_profiles/` directory created 2026-08-02 after 25+ cycles as D2 gap.

## W3C DTCG v2025.10 — Key Facts

- **Stable release**: October 28, 2025 (W3C Design Tokens Community Group)
- **84% team adoption** (2026 survey of ~300 professionals)
- **Backers**: Adobe, Google, Meta, Figma, Tokens Studio, Style Dictionary, Terrazzo
- **Media type**: `application/design+json` (official)
- **Spec**: [W3C DTCG Design Tokens Specification](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version)

## 5-Tier Token Architecture

```
$metadata     — version, format version, source, lastModified
$themes       — VARIANCE/MOTION/DENSITY dial variants (taste-skill 3-dial mapping)
$core         — primitive values (hex, rem, cubic-bezier) — NEVER reference upward
$semantic     — purpose-based references {core.X} (action-primary, text-secondary)
$component    — component-scoped references {semantic.X} (button.bg, card.shadow)
```

**Reference syntax**: `{layer.property}` — e.g., `{color.palette.accent.blue-primary}`

## Brand Token JSON Schema (W3C DTCG v2025.10)

Location: `~/.hermes/skills/taste-skill-repo/skills/creative_brand_profiles/brand_tokens.json`

```json
{
  "$metadata": {
    "version": "1.0.0",
    "tokenFormatVersion": "2025.10",
    "source": "hermes-agent creative_brand_profiles",
    "lastModified": "2026-08-02"
  },
  "$themes": {
    "hermes_default": { "VARIANCE": 6, "MOTION": 4, "DENSITY": 4 },
    "taste_dial_high": { "VARIANCE": 8, "MOTION": 6, "DENSITY": 4 },
    "taste_dial_low":  { "VARIANCE": 4, "MOTION": 4, "DENSITY": 6 }
  },
  "$core": {
    "color": {
      "palette": {
        "monochrome": { "white": { "$value": "#FFFFFF", "$type": "color" }, ... },
        "accent": { "blue-primary": { "$value": "#3B82F6", "$type": "color" }, ... }
      }
    },
    "typography": { "fontFamily": { "sans": { "$value": "Inter, ...", "$type": "fontFamily" } }, ... },
    "spacing": { "0": { "$value": "0", "$type": "dimension" }, "4": { "$value": "1rem", "$type": "dimension" }, ... },
    "motion": {
      "ease": { "ease-out": { "$value": "cubic-bezier(0, 0, 0.2, 1)", "$type": "cubicBezier" }, ... },
      "duration": { "fast": { "$value": "150ms", "$type": "duration" }, ... }
    },
    "borderRadius": { "md": { "$value": "0.375rem", "$type": "dimension" }, ... },
    "shadow": { "sm": { "$value": "0 1px 2px 0 rgba(0,0,0,0.05)", "$type": "boxShadow" }, ... }
  },
  "$semantic": {
    "color": {
      "action-primary": { "$value": "{color.palette.accent.blue-primary}", "$description": "Primary CTA" },
      "text-secondary":  { "$value": "{color.palette.monochrome.gray-500}", "$description": "Muted text" }
    },
    "motion": {
      "duration": { "hover": { "$value": "{motion.duration.fast}" }, ... },
      "ease": { "interactive": { "$value": "{motion.ease.ease-out}" }, ... }
    }
  },
  "$component": {
    "button": {
      "background":     { "$value": "{semantic.color.action-primary}" },
      "radius":         { "$value": "{borderRadius.md}" },
      "padding-x":      { "$value": "{spacing.4}" }
    }
  }
}
```

## Style Dictionary Transform

Script: `~/.hermes/skills/taste-skill-repo/skills/creative_brand_profiles/brand_tokens_transform.py`

```bash
python3 brand_tokens_transform.py
# Output: dist/tokens.css (67 lines) + dist/tokens.mjs (67 lines) + dist/_tokens.scss (99 lines)
# Total: 99 resolved tokens
```

**CSS output example**:
```css
:root {
  --color.palette.accent.blue-primary: #3B82F6;
  --motion.ease.ease-out: cubic-bezier(0, 0, 0.2, 1);
  --motion.duration.fast: 150ms;
}
```

**GSAP integration** (use CSS var, not string literal):
```javascript
gsap.to(el, {
  duration: 0.25,
  ease: 'power2.out'  // ← WRONG: string literal
  // ✅ CORRECT: CSS custom property resolved by brand_tokens.json
  ease: 'cubic-bezier(0, 0, 0.2, 1)'
})
```

## If→Then — Design Token Usage

**If** generating a landing page, article illustration, or UI component
**Then** read `brand_tokens.json` and inject color/typography tokens into the prompt:
```
Prompt: "A clean professional landing page for Hermes Portal,
background: {color.palette.monochrome.gray-50},
heading: {typography.fontFamily.sans}, size: {typography.scale.2xl},
CTA button: {color.palette.accent.blue-primary}"
```

**If** building a GSAP animation
**Then** use `--motion.duration.fast` (150ms) and `--motion.ease.ease-out` CSS values from the token system, not string literals like `"power2.out"` — this ensures animation parameters stay in sync with brand tokens.

**If** user asks to "continue in the same style" weeks later
**Then** read `creative_brand_profiles/brand_tokens.json` and inject tokens (not just color hexes) into the generation prompt — the 5-tier reference system ensures semantic consistency even if surface values change.

## taste-skill Bridge

The taste-skill 3-dial system (VARIANCE / MOTION / DENSITY) maps directly to `$themes`:

| taste-skill dial | Theme key | VARIANCE | MOTION | DENSITY |
|-----------------|-----------|----------|--------|---------|
| High (premium) | `taste_dial_high` | 8 | 6 | 4 |
| Default | `hermes_default` | 6 | 4 | 4 |
| Low (functional) | `taste_dial_low` | 4 | 4 | 6 |

## Verification

```bash
# Check creative_brand_profiles/ exists
ls ~/.hermes/skills/taste-skill-repo/skills/creative_brand_profiles/
# Expected: brand_tokens.json  brand_tokens_transform.py  dist/

# Validate JSON format
python3 -c "import json; t=json.load(open('brand_tokens.json')); print('✅ 5-tier:', list(t.keys()))"
# Expected: ['\$metadata', '\$themes', '\$core', '\$semantic', '\$component']

# Run transform
cd ~/.hermes/skills/taste-skill-repo/skills/creative_brand_profiles/
python3 brand_tokens_transform.py
# Expected: tokens.css (67 lines) + tokens.mjs (67 lines) + _tokens.scss (99 lines)
```

## External Sources

- [W3C DTCG Stable Release Announcement](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version) — October 28, 2025
- [Design Systems in 2026: Scale UI Without the Chaos](https://www.digitalapplied.com/blog/design-systems-2026-scale-ui-without-chaos-methodology) — 84% adoption rate, June 2026
- [Figma Schema: DTCG and Multi-Brand](https://www.youtube.com/watch?v=XI8cjfw8rt8) — October 2025 announcement
