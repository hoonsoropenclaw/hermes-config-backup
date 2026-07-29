# brand-design-token-consistency.md
# Skill Gap: Design Token → AI Image Generation Pipeline (brandkit D2 gap, Cycle 558)

## L3 Lesson: Data-Without-Consumption Anti-Pattern

### Problem (Gap)
brandkit skill has `creative_brand_profiles/*.json` (3 W3C DTCG 2025.10 brand profiles)
but SKILL.md generation path never reads/feeds these tokens into the prompt.
Result: brand colors, typography, and style are stored but not consumed = silent inconsistency.

### Root Cause
W3C DTCG 2025.10 tokens use `$value` + `$type` + alias chains (e.g., `{color.brand.$root}`).
Generic JSON parsing cannot understand these; must explicitly traverse and inject.

### If→Then

**If→Then #1: Design Token Consumption in AI Image Prompts**
> **If** a brand profile uses W3C DTCG 2025.10 format with `$value` fields, alias references, and composite tokens (typography with font/size/line-height/color)
> **Then** must explicitly parse and inject: hex colors as `color: #HEX`, typography as `font: fontName weight size/line-height`, and style keywords as natural-language descriptors
> **Why**: raw JSON token structure is not prompt-compatible; needs a translation step
> **Validation**: generate with brand tokens vs without → check hex color accuracy + style consistency

**If→Then #2: W3C DTCG 2025.10 Alias Chain Resolution**
> **If** a token value is an alias reference like `{color.brand.$root}` (not a raw hex)
> **Then** must resolve the alias chain before injecting into prompts: follow reference until explicit `$value` found
> **Why**: alias chains can be 2-3 levels deep; unresolved alias produces garbage in prompts
> **Validation**: `jq '[path(..) as $p | select(getpath($p) | has("$value") or type == "string" and startswith("{"))] | .[]' tokens.json` to find all unresolved references

**If→Then #3: Data-Without-Consumption Self-Audit**
> **If** a skill stores structured data files (JSON/YAML/profiles) but SKILL.md generation path never references them
> **Then** this is a D2 gap (data exists but is not consumed) → must either (a) implement consumption in SKILL.md or (b) remove data files to avoid misleading future agents
> **Why**: stored-but-unused data creates false confidence; future agents see data and assume it's being used
> **Fix**: add `--brand <name>` → `json.load()` → token injection flow to SKILL.md

## External Verification Commands
```bash
# Verify brandkit JSON files exist and are valid DTCG 2025.10
ls ~/.hermes/skills/taste-skill-repo/skills/brandkit/creative_brand_profiles/*.json | wc -l
# → 3 (expected)

# Validate DTCG structure
python3 -c "
import json, sys
from pathlib import Path
p = Path.home() / '.hermes/skills/taste-skill-repo/skills/brandkit/creative_brand_profiles/user_default.json'
d = json.load(open(p))
# Check for DTCG required fields
tokens = [k for k,v in d.items() if isinstance(v, dict) and '$value' in v]
print(f'DTCG tokens: {len(tokens)}')
print(f'Sample: {list(d.items())[0]}')
"

# Check brandkit SKILL.md references the profile files
grep -c "creative_brand_profiles" ~/.hermes/skills/taste-skill-repo/skills/brandkit/SKILL.md
# → 0 (D2 gap confirmed: data not consumed)
```

## References
- W3C DTCG 2025.10: https://www.designtokens.org/TR/2025.10/format
- brandkit SKILL.md line 804-828: data-without-consumption gap documented
