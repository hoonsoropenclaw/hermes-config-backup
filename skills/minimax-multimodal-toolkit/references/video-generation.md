# Video Generation Runbook

**Scope**: Every `mmx video generate` call from prompt receipt → delivery.
**Why this file exists**: Video gen knowledge was scattered in SKILL.md paragraphs only. This runbook mirrors the image-generation-pipeline structure — decision tree + failure patterns + Hailuo-specific formula in one place.

**Last verified**: 2026-06-24 (t2v + i2v实测, 3 clips生成成功)

---

## Decision Tree

```
User wants a video?
│
├─ school scenario (teacher/student interview, HR presentation)?
│   └─ YES → verify content with Prompt Safety Checklist before anything else
│           (see image-generation-pipeline.md for the checklist — same rules apply)
│
├─ has a still image to animate?
│   └─ YES → Image-to-Video mode (--first-frame) — BEST quality, style binding from image
│
├─ wants first-frame + last-frame continuity?
│   └─ YES → Hailuo-02 model with --first-frame + --last-frame
│
├─ wants face/subject consistency across shots?
│   └─ YES → S2V-01 model with --subject-ref (requires uploaded subject reference)
│
└─ text-to-video only (no reference image)?
    └─ DEFAULT → Hailuo-2.3 (default model, exit 0 ~25s for 6s clip)
```

---

## Prompt Formula (Hailuo-Specific)

From Segmind's verified Hailuo prompting guide:

```
[Camera Shot + Motion] + [Subject + Description] + [Action] + [Scene + Description] + [Lighting] + [Style/Mood]
```

**CRITICAL: Camera movement terms go at the BEGINNING** — same token-weight principle as image-01 camera angle rule.

| Position | Element | Examples |
|----------|---------|----------|
| 1st | Camera Shot + Motion | `tracking shot`, `dolly in`, `slow pan left`, `crane up` |
| 2nd | Subject + Description | `woman in suit`, `student holding book`, `teacher at whiteboard` |
| 3rd | Action | `walking toward camera`, `gesturing`, `reading aloud` |
| 4th | Scene + Description | `modern classroom`, `school corridor`, `office lobby` |
| 5th | Lighting | `golden hour`, `softbox studio`, `natural window light` |
| 6th | Style/Mood | `cinematic`, `documentary`, `warm and inviting` |

**Do NOT**: Stack multiple camera movements in one prompt (e.g. `pan left + dolly in + tilt up`) — confuses the model, reduces quality.

---

## Camera Movement Reference (AI Video)

Based on Eachlabs AI video camera guide + Hailuo-specific best practices:

| Movement | Prompt Phrase | Best For |
|----------|--------------|----------|
| Pan | `slow pan across`, `pan left to right` | Revealing environments, following action |
| Tilt | `camera tilts up to reveal`, `tilts down` | Emphasizing height, dramatic reveals |
| Dolly In | `dolly in toward subject`, `cinematic push-in` | Emotional emphasis, focusing attention |
| Dolly Out | `dolly out`, `camera pulls back` | Establishing context, releasing tension |
| Tracking | `camera tracks behind`, `following shot` | Action scenes, character-driven content |
| Crane | `camera cranes upward`, `crane shot` | Large-scale reveals, cinematic openers |
| Zoom | `subtle zoom in`, `zoom out` | Highlighting details (use sparingly) |
| POV | `first-person view`, `over-the-shoulder` | Immersive, personal perspective |

**Rule**: Use **one primary movement per scene**. More = unstable output.

---

## Verified mmx-cli Video Commands

**IMPORTANT — real-world timing (2026-06-24 verified):**
- t2v (720P/6s): **90–105s wall-clock**, 713KB–1.1MB, exit 0 ✅
- i2v --first-frame (720P/6s): **~150s wall-clock**, 2.1MB, exit 0 ✅
- i2v is slower than t2v; budget 180s timeout for i2v
- `subprocess.TimeoutExpired` from Python does NOT mean the API call failed — always verify by checking output file existence after timeout

### Text-to-Video (blocking)
```bash
KEY=$(grep "MINIMAX_API_KEY=*** ~/.hermes/.env | grep -v "^#" | cut -d= -f2-)
mmx video generate \
  --prompt "tracking shot, woman in professional suit walking through school hallway, carrying folder, natural window light, cinematic" \
  --model MiniMax-Hailuo-2.3 \
  --duration 6 \
  --resolution 720P \
  --api-key "$KEY" \
  --download /tmp/school_walk.mp4 \
  --quiet
# exit 0, ~90–105s, MP4 713KB–1.1MB (2026-06-24 verified)
```

### Image-to-Video (first frame)
```bash
# Step 1: generate image
KEY=$(grep "MINIMAX_API_KEY=*** ~/.hermes/.env | grep -v "^#" | cut -d= -f2-)
mmx image generate --prompt "comic book portrait of a young woman in professional blazer, bold ink outlines, halftone patterns" \
  --aspect-ratio 16:9 --out-dir /tmp --out-prefix char_test \
  --api-key "$KEY" --quiet
# Step 2: use as first frame (i2v ~150s, budget 180s timeout in Python subprocess)
mmx video generate \
  --prompt "the character starts walking toward camera, then pauses and smiles, comic book style animation" \
  --first-frame /tmp/char_test_001.jpg \
  --model MiniMax-Hailuo-2.3 \
  --duration 6 \
  --resolution 720P \
  --api-key "$KEY" \
  --download /tmp/test_i2v.mp4 \
  --quiet
# exit 0, ~150s, MP4 2.1MB (2026-06-24 verified)
```

### First-Last Frame (continuity mode, Hailuo-02)
```bash
mmx video generate \
  --prompt "the scene transitions smoothly" \
  --first-frame /tmp/first.jpg \
  --last-frame /tmp/last.jpg \
  --model MiniMax-Hailuo-02 \
  --duration 6 \
  --resolution 1080P \
  --download /tmp/transition.mp4 \
  --quiet
```

### Subject Reference Video (S2V-01, face consistency)
```bash
mmx video generate \
  --prompt "subject walks through neon city at night" \
  --subject-ref "type=character,image=/tmp/portrait.jpg" \
  --model S2V-01 \
  --duration 6 \
  --resolution 1080P \
  --download /tmp/consistent.mp4 \
  --quiet
```

### Async (get task ID immediately)
```bash
TASK=$(mmx video generate \
  --prompt "ocean waves at sunset" \
  --model MiniMax-Hailuo-2.3 \
  --async --quiet)
echo "Task ID: $TASK"

# Poll status
mmx video task get --task-id "$TASK" --output json

# Download when ready
mmx video download --file-id <from-task-status> --out /tmp/waves.mp4
```

---

## Resolution & Duration (Verified 2026-06-19)

| Flag | Accepted Values | Notes |
|------|----------------|-------|
| `--resolution` | `720P`, `1080P` | Default: 1080P |
| `--duration` | `5`, `6` | Default: 6 seconds |
| `--model` | `MiniMax-Hailuo-2.3`, `MiniMax-Hailuo-2.3-Fast`, `MiniMax-Hailuo-02`, `S2V-01` | Default: Hailuo-2.3 |

---

## Key Distinction: Image-01 Rules DO NOT Transfer to Video

From 2026-06-19 testing:

| image-01 Behavior | Video (Hailuo) Status |
|-------------------|----------------------|
| `minimalist line art` → washed to photoreal | May differ — test independently |
| `bird's-eye` + portrait fails | May work — do not assume |
| `curvy/hourglass` → de-escalated | May differ — test independently |
| Style words strongly bound | Video style binding generally weaker |

**If a prompt works on image-01 but user wants video**: test the video prompt directly. Do not apply image-01 workaround logic (e.g., "switch to comic because line art fails") to video.

---

## Failure Patterns

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | MP4 saved to `--download` path or `/tmp/mmx-video/` |
| 1 | Usage/system error | Check flags, model name, file path |
| 3 | Auth error | Verify `--api-key` is valid MiniMax Platform key |
| 5 | Timeout | Retry once — network波动 |
| Python TimeoutExpired | **NOT an API failure** | Check output file — Hailuo may still be generating in background; file existence is ground truth |
| async task fails | Polling returns error | Check task status, retry if transient |

**Async timeout**: If `--async` task never completes, poll every 10s up to 5 minutes.

**Python subprocess timeout (execute_code)**: When calling mmx video from Python `subprocess.run()` with a hard timeout, a `TimeoutExpired` exception does NOT mean the API call failed. Hailuo generates asynchronously — the subprocess times out but generation continues. **Always verify by checking `Path('/tmp/output.mp4').exists()` after catching `TimeoutExpired`.**

---

## School HR Use Cases

| Use Case | Recommended Approach |
|----------|---------------------|
| Interview preparation video | Image-to-Video: generate still image (comic book style for safety), animate with Hailuo |
| School event highlight reel | Text-to-Video with tracking shots, school campus scenes |
| Teacher training presentation | Image-to-Video with professional headshot + subtle motion |
| Student orientation clip | First-Last frame continuity for scene transitions |

**Safety note**: Same prompt safety checklist as image generation applies. School scenarios with minors: verify clothing, pose, and context before generating.

---

## See Also

- `SKILL.md` — Core mmx-cli reference (image, text, speech, music commands)
- `references/image-generation-pipeline.md` — Image gen runbook (same structure as this file)
- `references/image-prompting-cookbook.md` — Worked prompt examples
- `references/fal-ai-flux.md` — FLUX fallback when image-01 constraints are problematic
- `references/ai-image-safety-school-20260620.md` — School HR image safety guardrails
