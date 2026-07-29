# W3C DTCG 2025.10 Brand Token Spec Research (Cycle 558)

## Spec Status
- **Version**: W3C Design Tokens Format Module 2025.10 (stable)
- **Published**: 2025-10-28 by Design Tokens Community Group
- **URL**: https://www.designtokens.org/TR/2025.10/format
- **Endorsed by**: Figma, Penpot, Sketch, Tokens Studio, Style Dictionary, Terrazzo

## Core Terminology

| Term | Definition |
|------|------------|
| Token | `{ "tokenName": { "$value": ..., "$type": ... } }` — name/value pair with metadata |
| Alias | Token reference: `"{color.brand.root}"` — resolves via alias chain |
| Composite | Token with multiple named child values (e.g., typography with font/size/lh/color) |

## Token Properties (required vs optional)

| Property | Required | Notes |
|----------|----------|-------|
| `$value` | **Yes** | The token's actual value |
| `$type` | No | Color, Size, Duration, etc. Inherited from group if omitted |
| `$description` | No | For IDE tooltips, style guide docs |
| `$extensions` | No | Vendor-specific (reverse-domain recommended) |
| `$deprecated` | No | `true`, `false`, or string explanation |

## Token Name Rules (§4)

- **MUST NOT** begin with `$` — `$` is reserved for DTCG property names
- Case-sensitive
- MUST NOT contain `{`, `}`, `.`

## Hex Value Format

```json
// CORRECT
{ "$value": { "hex": "#0066CC", "colorSpace": "srgb" } }

// INCORRECT (double hash — the brandkit JSON bug)
{ "$value": { "hex": "##0066CC" } }
```

## Alias/Reference Syntax

```json
"semantic.link": { "$value": "{color.brand.primary}" }
// resolves to same value as color.brand.primary
```

Tools MUST follow alias chains until explicit `$value` found.

## File Format

- MIME type: `application/design-tokens+json` (preferred) or `application/json`
- Extension: `.tokens` (preferred) or `.tokens.json`
- All JSON files are valid design token files

## Brand Token Extraction for AI Image Prompts

Given a DTCG JSON, extract these fields for brand image generation:

```
color.$root → primary background/canvas
color.surface → card/panel background
color.border → divider/rule color
color.accent.primary → brand signal accent
color.accent.secondary → secondary accent
color.text.primary → main text
typography.heading → heading font family
typography.body → body font family
mood.keywords → style descriptors
generation_prompt_seed.composition → layout guidance
```

## Relevant Sessions

- Cycle 558: DTCG spec research + `##` hex bug + `$root` reserved word discovery
