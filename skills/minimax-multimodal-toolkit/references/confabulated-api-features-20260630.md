# Confabulated API Features — Self-Detection (2026-06-30)

## What happened

Session `20260616_125207` (98 msgs, AI image generation) involved multiple `mmx image generate` calls where the assistant mentioned "similar mode", "variation mode", and `similar variants` to the user as if they were mmx-cli features.

**Verification:**
```bash
$ npx -y mmx-cli image generate --help 2>&1 | grep -iE "similar|variation"
# → 0 matches

$ npx -y mmx-cli image generate --help 2>&1 | grep -iE "seed"
--seed <n>   Random seed for reproducible generation (same seed + prompt = identical output)
```

The only confirmed mmx-cli flags for controlled variation are:
- `--seed N` — reproducible output (same N + same prompt = same image)
- `--n 4` — batch generation with independent seeds

## Why it happens

LLMs trained on Midjourney/DALL-E documentation carry cross-API interference. Midjourney has `/similar` and `V` (variation) buttons; DALL-E has variation modes. The assistant defaults to these familiar terms when the user says "another one like this" without checking if mmx-cli actually implements them.

## How to detect in real time

1. **The assistant says a flag or mode name the user didn't say** — e.g., user says "give me a variant" and the assistant responds with "I'll use `--similar mode`" when the user never mentioned "similar"
2. **The assistant describes a behavior that sounds like an API feature** (not just a technique) — `similar mode`, `variation mode`, `style lock mode`, `seed-based variation`
3. **The user asks "what does --X do?" and the assistant can't produce the exact help output**

## Correct pattern for each use case

| User wants | Correct mmx-cli approach |
|------------|--------------------------|
| "another one like this" | Rerun without `--seed` (random seed), or with `--n 4` for batch |
| "same image again" | Record the `--seed` from the first run's output, rerun with that seed |
| "same subject, different style" | Use `--subject-ref 'type=character,image=/path/to/ref.jpg'` |
| "4 variations at once" | `mmx image generate --prompt "..." --n 4` |

## Self-correction script

Before saying any flag name to the user in an image gen context, run:
```bash
mmx image generate --help 2>&1 | grep -iE "<flag_name>"
```
If zero matches → do NOT say the flag name to the user. Rephrase the explanation using only verified flags.

## Related

- `trial-and-error/references/by-category/mmx-cli-image-gen.md` §11 — the 2026-06-30 finding that triggered this reference
- `minimax-multimodal-toolkit/SKILL.md` — "Confabulated API Features" pitfall added to image generate flags table

---

## `--sref` is confabulated for video subject-consistency (2026-07-26)

**What happened:** Cycle 543 D3-learn test mentioned `--sref` flag for subject-consistency video (S2V-01 model). The flag does not exist in mmx-cli.

**Verification:**
```bash
$ npx -y mmx-cli video generate --help 2>&1 | grep -iE "sref|subject-image|subject-ref"
--subject-ref <params>  Subject reference for face-consistency video (requires S2V-01)
```

**Correct flag:** `--subject-ref` (for S2V-01 face-consistency video). The confabulation likely came from Midjourney's `--sref` (style reference) which has different semantics.

**Self-correction rule:** If you mention `--sref` in any video generation context, stop and run `mmx video generate --help | grep -iE "sref|subject"` to verify. If zero matches for `--sref`, use `--subject-ref` instead.
