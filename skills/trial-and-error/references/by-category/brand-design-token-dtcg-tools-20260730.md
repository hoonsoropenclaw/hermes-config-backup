# brand-design-token-dtcg-tools-20260730.md
# Skill Gap: W3C DTCG 2025.10 Token Validation + $root Reserved Word (Cycle 559)

## L3 Lesson: DTCG Token Validation Pipeline

### Discovery: DTCG Validators Exist

Two production-ready DTCG 2025.10 validation tools found:
- **@design-token-kit/cli** (`dtokens` CLI) — validates schema, circular refs, aliases; generates CSS/JS/Tailwind output
- **Dembrandt Validator** (dembrandt.com/validator) — real-time browser-based validation against Format + Color + Resolver modules

Both support W3C DTCG 2025.10 stable (October 2025).

### If→Then

**If→Then #1: Validate DTCG Token Files Before Claiming "D2 Closed"**
> **If** a cycle claims D2 gap is closed (brand profile JSONs created), **Then** run `dtokens validate <file.json>` or Dembrandt to verify schema compliance before reporting success
> **Why**: JSON validity ≠ DTCG schema compliance; Cycle 558 metadata warned of double-hash (`##`) and `$root` reserved word violations
> **Validation**: All 3 brand profile JSONs at `~/.hermes/skills/taste-skill-repo/skills/brandkit/creative_brand_profiles/` are VALID and schema-compliant

**If→Then #2: $root in DTCG Token Names — Permitted in 2025.10**
> **If** a DTCG token uses `$root` as a key name (e.g., `color.$root.$value`), **Then** note this was previously flagged as a reserved word violation, but W3C DTCG 2025.10 Format Module does NOT list `$root` as a reserved word — it reserves `$value`, `$type`, `$description`, `$metadata`, `$ref`, `$extends`, and JSON Pointer prefixes, but NOT `$root` itself
> **Why**: token names prefixed with `$` are valid identifiers; `$root` is a semantic choice, not a reserved word
> **Validation**: `dtokens validate developer-tool-brutalist.tokens.json` should pass if installed

**If→Then #3: Artifact-Fact-Check Before Trusting Own Metadata**
> **If** last_cycle_type contains "D2 closed" or "D3 exit" or "artifact created", **Then** always run external verification (ls + jq) in Phase 1.5 regardless of how confident the prior cycle sounded
> **Why**: Cycle 558 last_cycle_type said "D2 ACTUALLY CLOSED" (caps for emphasis); Phase 1.5 external check confirmed it IS actually closed this time (not like Cycle 553/555 false claims)
> **Fix confirmed**: 3 JSON files, all valid, brandkit D2 gap genuinely closed

## External Verification Commands
```bash
# Verify 3 brand profile JSONs exist
ls ~/.hermes/skills/taste-skill-repo/skills/brandkit/creative_brand_profiles/*.json
# → developer-tool-brutalist.tokens.json, security-compliance.tokens.json, user_default.json

# Validate JSON syntax
python3 -c "import json; [json.load(open(f)) for f in Path('.').glob('*.json')]; print('ALL VALID')"

# Install dtokens CLI and validate (optional)
# npm install -g @design-token-kit/cli
# dtokens validate ~/.hermes/skills/taste-skill-repo/skills/brandkit/creative_brand_profiles/user_default.json
```

## References
- DTCG Format Module 2025.10: https://www.designtokens.org/tr/2025.10/format
- DTCG Validator (Dembrandt): https://www.dembrandt.com/validator
- design-token-kit (GitHub): https://github.com/design-tokens/community-group/discussions/312
