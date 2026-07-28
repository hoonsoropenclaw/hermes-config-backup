# `hallmark save|list|delete` — Brand Profile Verbs

## Overview

Brand profiles are persistent brand DNA stored in `~/.hermes/creative_brand_profiles/`. Each is a JSON file capturing the extracted design tokens, typography, macrostructure, and anti-patterns from a `hallmark study` run.

**Profile directory**: `~/.hermes/creative_brand_profiles/`
**Schema**: `~/.hermes/creative_brand_profiles/_schema.md`

---

## `hallmark save <brand-slug> [--name "Display Name"] [--source <url|screenshot>]`

### Purpose

Saves the current `hallmark study` diagnosis as a persistent brand profile JSON file. After saving, future sessions can load this brand's DNA without re-running `study`.

### Prerequisites

- A `hallmark study` diagnosis must have been produced in the current session
- The brand's name, source URL, and extracted fields are known

### Input collection

1. **`brand-slug`** (required, positional): URL-safe kebab-case. Default: derived from `--name` or from the studied source URL's domain.

2. **`--name`** (optional): Human-readable display name. Default: the slug, title-cased.

3. **`--source`** (optional): Source type — either a URL (e.g. `https://stripe.com`) or `screenshot`. Default: derived from the `study` diagnosis's provenance block.

### Profile construction

Build the profile JSON from the `study` diagnosis fields:

| Diagnosis field | Profile field |
|-----------------|---------------|
| `## Typography` → font families | `typography.display/body/mono` |
| `## Color` → primary/accent/neutral | `color.brand/accent/neutral/paper` |
| `## Macrostructure` → archetype + columns | `macrostructure.archetype/columns` |
| `## Motion` → entrance pattern | `motion.entrance/duration/easing` |
| Signature element | `signature.memorable/technique` |
| Anti-patterns from diagnosis | `antiPatterns[]` |
| Diagnosis source | `source.type/ref` + `studiedAt` |

If `study` output is not in memory, prompt the user to either:
- Paste the diagnosis text (parse it), or
- Re-run `hallmark study`

### Save procedure

```python
import json, shutil
from pathlib import Path

profile_dir = Path.home() / ".hermes/creative_brand_profiles"
profile_dir.mkdir(exist_ok=True, parents=True)

profile_path = profile_dir / f"{slug}.json"

if profile_path.exists():
    print(f"Brand '{slug}' already exists. Use `hallmark delete-brand {slug}` first, or choose a different slug.")
    return

profile_path.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False))

# Verify
loaded = json.loads(profile_path.read_text())
assert "name" in loaded and "color" in loaded and "typography" in loaded
print(f"Brand profile `{slug}` saved ({len(loaded['color'])} tokens, {len(loaded['typography'])} font families)")
```

### Confirmation message

> *"Brand profile `stripe` saved — 7 color tokens, 3 font families (Camphor + IBM Plex Mono), macrostructure: full-bleed, studied from https://stripe.com. Future sessions: `hallmark build --brand stripe <brief>` to apply this DNA."*

### Error handling

- **Slug conflict**: Ask user to confirm overwrite or pick a different slug.
- **Missing fields**: Prompt user to provide the missing data rather than silently omitting.
- **Permission error**: Report path and permissions issue.

---

## `hallmark list-brands`

### Purpose

Show all saved brand profiles as a scannable list.

### Procedure

```python
import json
from pathlib import Path

profile_dir = Path.home() / ".hermes/creative_brand_profiles"
profiles = sorted(profile_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

if not profiles:
    print("No brand profiles saved yet.")
    print("Run `hallmark study <source>` then `hallmark save <brand-slug>` to create one.")
    return

print(f"{len(profiles)} brand profile(s):\n")
for p in profiles:
    d = json.loads(p.read_text())
    source_tag = d.get("source", {}).get("ref", "unknown")
    print(f"  {d['slug']:<12} {d['name']:<20} studied {d.get('studiedAt', '?')[:10]}   source: {source_tag}")
```

### Output example

```
3 brand profiles:

  stripe    Stripe             studied 2026-07-28   source: https://stripe.com
  linear    Linear             studied 2026-07-27   source: screenshot
  vercel    Vercel             studied 2026-07-26   source: https://vercel.com
```

---

## `hallmark delete-brand <slug>`

### Purpose

Delete a saved brand profile.

### Confirmation required

Before deleting, ask the user:

> *"Delete brand profile `{slug}`? This removes `~/.hermes/creative_brand_profiles/{slug}.json`. Type `yes` to confirm."*

### Procedure

```python
from pathlib import Path

profile_path = Path.home() / ".hermes/creative_brand_profiles" / f"{slug}.json"

if not profile_path.exists():
    print(f"Brand `{slug}` not found.")
    return

profile_path.unlink()
print(f"Brand profile `{slug}` deleted.")
```

---

## Verification

```bash
# List all profiles
ls ~/.hermes/creative_brand_profiles/

# Validate all profiles
python3 -c "
import json
from pathlib import Path
required = ['name','slug','studiedAt','source','typography','color','macrostructure']
profile_dir = Path.home() / '.hermes/creative_brand_profiles'
for p in profile_dir.glob('*.json'):
    d = json.loads(p.read_text())
    missing = [f for f in required if f not in d]
    status = 'OK' if not missing else f'MISSING: {missing}'
    print(f'{p.name}: {status}')
"
```
