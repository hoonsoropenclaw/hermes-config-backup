# Multi-Clip Video Orchestration — Storyboard-First Workflow

**Source**: 2026 AI Video Production Playbook (Data Science Collective, Paolo Perrone) + Hermes metacognitive-learner Cycle 477 research

**Prerequisite**: `mmx image generate` + `mmx video generate` working knowledge (see SKILL.md)

---

## Core Problem

> "You generate a 10-second product clip. The lighting is wrong. You regenerate. The character's outfit drifts. You regenerate. By the fifth attempt the bill is $5 for a clip that should have cost $1.50."

Single-shot generation optimization ≠ cost-per-finished-video optimization. The gap is orchestration.

---

## Three-Layer Production Stack

| Layer | Tool | Optimization Target |
|-------|------|---------------------|
| Layer 1: Storyboard | `mmx image generate` | Lock visual spec (composition, lighting, character appearance) |
| Layer 2: Generation Model | `mmx video generate` | Frame quality, motion accuracy |
| Layer 3: Orchestration | Reference frame management | Continuity across clips, drift correction |

> Treating Layer 2 as the entire stack is the most expensive mistake in AI video production.

---

## Hermes/mmcli-Specific If→Then Rules

**If** user wants a multi-scene video (>15 seconds, multiple clips)
**Then** apply storyboard-first workflow:
1. `mmx image generate` — generate static reference frames first (cheap, fast, iterative)
2. Lock each frame's: composition, lighting, character pose, color palette
3. Use `--first-frame` (I2V mode) to feed locked reference into video generation
4. Video model handles only: motion, camera path, timing

**If** generating a series of clips with character continuity (e.g., same person across scenes)
**Then** use last frame of clip N as input to clip N+1:
```bash
# Clip 1: pure T2V
mmx video generate --prompt "woman, studio lighting, confident pose" --duration 10

# Clip 2: I2V with clip1 last frame
mmx video generate \
  --first-frame /path/to/clip1_last_frame.jpg \
  --prompt "same woman, outdoor setting, walking" \
  --duration 10
```

**If** character appearance drifts across clips (hair, outfit, lighting palette)
**Then** this is a tracked failure mode — generate a corrective frame using `mmx image generate` with exact character reference description, then feed that as `--first-frame` to next clip

**If** user is optimizing for cost-per-finished-clip (not cost-per-generation)
**Then** storyboard-first yields ~80% success rate vs ~40% blind generation:
| Approach | Attempts for 5 clips | Success Rate | Cost per Clip |
|----------|---------------------|--------------|---------------|
| Blind T2V | 10 | ~40% (2/5) | ~$5.00 |
| Storyboard-first | 5 | ~80% (4/5) | ~$1.50 |

**If** user has only one reference image and needs multi-clip continuity
**Then** generate that one reference in highest quality first, then use it as `--first-frame` for ALL clips, supplemented by strong prompt descriptions of what should stay consistent

**If** user is doing single short clip only (<10 seconds)
**Then** storyboard-first overhead may not pay off — use direct `mmx video generate` with detailed prompt

---

## Reference Frame Management for mmx-cli

Current `mmx video generate` supports:
- `--first-frame <path>` — image-to-video (I2V) mode
- `--reference <path>` — style/content reference (model-dependent)

Best practice for character continuity:
1. Store clip N's last frame → `~/mmx-refs/clip_{N}_last.jpg`
2. For clip N+1: `mmx video generate --first-frame ~/mmx-refs/clip_{N}_last.jpg --prompt "..."`
3. Use `mmx image generate` to create explicit correction frames when drift exceeds tolerance

---

## Cost Estimation

- `mmx image generate` (1:1, standard quality): ~$0.01-0.05 per image
- `mmx video generate` (10s, standard): ~$0.10-0.50 per clip
- Storyboard-first: 1-3 extra images per video clip + higher success rate
- Net effect: 2-3x cost reduction per usable finished clip
