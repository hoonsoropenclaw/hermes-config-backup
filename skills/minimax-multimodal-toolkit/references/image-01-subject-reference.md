# image-01 `subject_reference` — Character Consistency (2026-06-19 verified)

`--subject-ref 'type=character,image=/path/to/ref.jpg'` on `mmx image generate` binds visual identity of a subject across scenes/styles. Verified 2026-06-19: castle photo (64KB) → watercolor re-interpretation (503KB), exit 0, file confirmed on disk.

## Syntax

```bash
mmx image generate \
  --prompt "The same castle, but in a watercolor painting style, soft colors" \
  --subject-ref 'type=character,image=/path/to/reference.jpg' \
  --out-dir /tmp/out \
  --quiet
```

- `type=character` — the only verified type (2026-06-19)
- `image=` accepts local absolute path OR URL
- Multiple `--subject-ref` calls are NOT supported (single subject only)
- Works with `--n 1`; `--n > 1` behavior with subject_ref is untested

## Verified Behaviors

|| Ref type | Prompt style | Result | File size |
||----------|-------------|--------|-----------|
|| Portrait JPG (queen contestant) | Victorian ball gown, comic book style | ✅ Face consistent: green eyes, dark brows, red lips, blonde hair all preserved | 299KB |
|| Portrait JPG (queen contestant) | Cyberpunk outfit, anime cel-shaded | ✅ Face consistent: oval face, green eyes, blonde hair, dark red lips all preserved | 327KB |
|| Castle photo | Watercolor re-interpret | ✅ Success, exit 0 | 503KB |
|| Castle photo | Minimalist line art | ✅ Success, exit 0 | 503KB |

**Face consistency verified (2026-06-19):** Reference `q1_001.jpg` (blonde, green eyes, dark brows, red lips) → two generated images in vastly different styles both preserved: oval face shape, green eye color, dark arched eyebrows, full red lips, honey-blonde hair. Vision description confirms strong face identity preservation across style changes.

The subject's visual identity is preserved (face, distinctive features, architectural style) while style is applied. The model does NOT copy the reference image directly — it extracts visual features and applies them to the new prompt.

## Limitations

- **Pose/scene transfer**: `subject_reference` binds *visual identity* (face, distinctive features, architectural style), NOT pose or exact composition. Use `--first-frame` for pose continuity (video pipeline).
- **Multiple subjects**: Not supported — single `--subject-ref` only.
- **Character type only**: `type=character` is the only documented type. Other types (object, scene) may exist but are unverified.

## When to use vs `--first-frame` (video pipeline)

| Use case | Tool | Flag |
|----------|------|------|
| Same character in different scenes/styles | `mmx image generate` | `--subject-ref 'type=character,image=...'` |
| Same pose/shot in video | `mmx video generate` | `--first-frame /path/to.jpg` |
| Style transfer (landscape/art) | `mmx image generate` | `--subject-ref` (works for any subject) |

## Cross-link

- Main skill: `minimax-multimodal-toolkit/SKILL.md` — `--subject-ref` flag table entry
- Trial-and-error (agent-side integration issues): `~/.hermes/skills/trial-and-error/references/by-category/mmx-cli-image-gen.md`
