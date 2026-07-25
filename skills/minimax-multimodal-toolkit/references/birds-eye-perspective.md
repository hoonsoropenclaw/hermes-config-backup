# Bird's-Eye Perspective — image-01 Failure & Solution Reference

**Scope**: bird's-eye / overhead / looking-down + portrait combinations on MiniMax `image-01`.
**Status**: KNOWN FAILURE — see If→Then for workarounds.

---

## The Problem

`image-01` does NOT reliably bind `bird's-eye view` / `overhead shot` / `top-down perspective` when combined with:
- Abstract artistic keywords (`line art`, `flat colors`, `minimalist`)
- Natural language camera directions (`looking down`, `from above`, `viewed from above`)

**What happens**: The model ignores the artistic directive and renders photoreal photography instead.

**Why**: Training signal for `bird's-eye + line art / flat colors` combinations is sparse in image-01's dataset. Without sufficient examples, the model defaults to photorealism — its highest-confidence domain.

---

## Reliable Style Bindings

| Style Keyword(s) | bird's-eye + portrait | Verified |
|---|---|---|
| `comic book style, ink outlines, halftone` | ✅ 3/3 tests pass | 2026-06-19 |
| `anime style, cel-shaded` | ✅ | 2026-06-19 |
| `vector illustration with thick black outlines` | ✅ | pipeline suggestion |
| `minimalist line art` | ❌ washes to photoreal | failure cluster |
| `flat colors` alone | ❌ washes to photoreal | failure cluster |
| `looking down` (natural language) | ❌ ignored | failure cluster |

---

## Standard Cinematography Formula

**Natural language is ignored. Use standard cinematography terms at the BEGINNING of the prompt.**

```
bird's eye view, overhead shot, top-down perspective, [subject], [context], [style]
```

**Wrong**:
```
A woman looking down from above...  ← model ignores this
```

**Correct**:
```
bird's eye view, overhead shot, top-down perspective,
A woman sitting at a cafe table, warm lighting,
comic book style, ink outlines, halftone
```

---

## Priority Ordering (2026-06-29 verified)

1. **Primary**: `comic book style + ink outlines + halftone` — only verified solution (3/3 tests, 2026-06-19)
2. **Secondary**: prompt decomposition — verify angle on landscape/object first, then use `--first-frame` to layer subject
3. **Last resort**: FAL.ai FLUX — ⚠️ claim "bird's-eye + portrait works on FLUX" is **unverified** (FAL_KEY currently masked `***`); only recommend if user rejects comic/vector styles and explicitly accepts unverified risk

---

## Body-Shape + bird's-eye: Triple-Constraint Failure

**The specific failure**: When a prompt contains ALL THREE of:
1. Body-shape adjective (`curvy`, `hourglass`, `voluptuous`)
2. bird's-eye view
3. Abstract/artistic style

→ This is a triple-constraint failure. The model's safety filter de-escalates body-shape terms AND ignores artistic style directives simultaneously.

**Solution**: Use **situational vocabulary** instead of anatomical terms:
- `volleyball player athletic build` (not `curvy`)
- `competitive swimmer V-taper` (not `hourglass`)
- `gymnast physique` (not `voluptuous`)

And apply the **standard bird's-eye cinematography formula** at prompt start.

---

## If→Then

**If** user prompt contains `bird's-eye` / `overhead` / `looking down` + `portrait` + `abstract artistic style`
**Then** inform user of the limitation, provide replacement方案 (`comic book style + ink outlines + halftone`), explain the root cause

**If** user rejects the replacement style AND FAL_KEY is available
**Then** offer FLUX.1-dev as last resort, with explicit "unverified" caveat

**If** user rejects replacement AND FAL_KEY is NOT available
**Then** state this is an image-01 architecture limitation that cannot be solved via prompt engineering

**If** prompt has body-shape adjective + bird's-eye + abstract style (triple-constraint)
**Then** switch to situational vocabulary + standard cinematography formula at prompt beginning

---

## Related References

- `style-binding-spectrum.md` — Full spectrum of abstract vs commercial art keywords
- `image-prompting-cookbook.md` — Verified prompt recipes including gymnastics/sports context
- `refusal-anti-loop-20260623.md` — Progressive refusal pattern for boundary requests
