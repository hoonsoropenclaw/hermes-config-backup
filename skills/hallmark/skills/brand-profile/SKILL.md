---
name: brand-profile
description: "Persistent brand profile storage for hallmark — saves/loads brand DNA across sessions. Part of the hallmark creative pipeline."
version: 1.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hallmark:
    verb: brand-profile
    integrates_with: hallmark/study
    profile_dir: ~/.hermes/creative_brand_profiles/
    schema: _schema.md
---

# Brand Profile — Persistent Brand DNA Storage

## Purpose

`brand-profile` gives hallmark a persistent brand memory. Without it, `hallmark study` outputs a diagnosis that lives in the project directory and is never reused. With it, you can:

- Save a brand DNA extracted by `hallmark study` to `~/.hermes/creative_brand_profiles/<slug>.json`
- Load it in future sessions without re-running `study`
- Apply it to new builds with `hallmark build --brand <slug> <brief>`
- List all saved brands with their source and date

## Directory structure

```
~/.hermes/creative_brand_profiles/
  _schema.md          ← shared schema definition
  stripe.json         ← one file per brand
  linear.json
  vercel.json
  ...
```

## Commands

### `hallmark save <brand-slug> [--name "Display Name"] [--source <url|screenshot>]`

Saves the current `hallmark study` diagnosis as a brand profile.

**Prerequisites**: A `hallmark study` diagnosis must have been run in the current session.

**Procedure**:
1. Read the diagnosis from `design.md` or extract the key fields (typography, color, macrostructure, signature) from the session context
2. Prompt user for: display name (default: slug), source URL or "screenshot"
3. Write `~/.hermes/creative_brand_profiles/<slug>.json`
4. Confirm: "Brand profile `stripe` saved with 7 tokens, 3 font families, macrostructure: full-bleed"

### `hallmark list-brands`

Lists all saved brand profiles.

**Output format**:
```
2 brand profiles found:

  stripe    Stripe       studied 2026-07-28   source: https://stripe.com
  linear    Linear       studied 2026-07-27   source: screenshot
  (none)    No brands saved yet — run `hallmark study` first
```

### `hallmark build --brand <slug> <brief>`

Loads a brand profile and applies its DNA to a new build.

**Procedure**:
1. Load `~/.hermes/creative_brand_profiles/<slug>.json`
2. Read the profile's `typography`, `color`, `macrostructure`, `signature` fields
3. Inject these as design-context into the standard `hallmark build` flow
4. Tag the output: "Built with Stripe DNA (studied 2026-07-28)"

### `hallmark delete-brand <slug>`

Deletes a brand profile. Requires confirmation.

## Schema (stored in `_schema.md`)

```json
{
  "name": "Human-readable brand name",
  "slug": "url-safe-kebab-case",
  "studiedAt": "ISO 8601",
  "source": { "type": "url"|"screenshot", "ref": "URL or 'uploaded'" },
  "typography": {
    "display": { "family": "font", "weight": 400|700, "style": "normal|italic" },
    "body": { "family": "font", "weight": 400, "style": "normal|italic" },
    "mono": { "family": "font", "weight": 400, "style": "normal|italic" }
  },
  "color": {
    "brand": { "hex": "#rrggbb", "oklch": "oklch(...)" },
    "accent": { "hex": "#rrggbb", "oklch": "oklch(...)" },
    "cobalt": { "hex": "#rrggbb", "oklch": "oklch(...)" },
    "jade": { "hex": "#rrggbb", "oklch": "oklch(...)" },
    "rose": { "hex": "#rrggbb", "oklch": "oklch(...)" },
    "neutral": { "hex": "#rrggbb", "oklch": "oklch(...)" },
    "paper": { "hex": "#rrggbb", "oklch": "oklch(...)" }
  },
  "macrostructure": { "archetype": "string", "columns": 1|2|3|4 },
  "motion": { "entrance": "string", "duration": "string", "easing": "string" },
  "signature": { "memorable": "string", "technique": "string" },
  "antiPatterns": ["string"],
  "notes": "string"
}
```

## Integration with `hallmark study`

After `hallmark study` completes a diagnosis, offer the user:

> *"Brand profile saved. To reuse this DNA in future sessions, say `hallmark save <brand-slug>`."*

The profile is a superset of what `design.md` stores — it lives at the user level (`~/.hermes/creative_brand_profiles/`) rather than the project level (`design.md`).

## Anti-patterns captured per brand

`antiPatterns` in each profile is the list of design decisions from that brand that should NOT be carried over to new builds. This is extracted from the `study` diagnosis's "do NOT carry over" section.

## Verification commands

```bash
# Verify profiles exist
ls -la ~/.hermes/creative_brand_profiles/

# Count profiles
ls ~/.hermes/creative_brand_profiles/*.json | wc -l

# Validate a profile (must have required fields)
python3 -c "import json,sys; d=json.load(open('$HOME/.hermes/creative_brand_profiles/stripe.json')); print('name:', d['name']); print('tokens:', len(d['color'])); print('schema OK')"
```
