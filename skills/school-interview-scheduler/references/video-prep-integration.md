# Interview Preparation Video Integration (2026-06-23)

**Scope**: Adding video generation to the school-interview-scheduler LR pipeline. When HR wants to send a "訪談準備影片" to candidates alongside the Google Meet invite, this reference covers the i2v workflow.

**Why this reference exists**: The current school-interview-scheduler pipeline ends at "send Google Meet invite." The 2026-06-16 session showed users want a video preparation resource sent to candidates alongside the invite. The skill currently has no video LR step.

---

## Pipeline Gap: Where Video Fits

```
HR says: "幫我約張三面試，並寄準備影片給他"
    ↓
school-interview-scheduler:
  1. create_interview.py → Google Calendar + Meet URL
  2. [NEW] mmx image gen → interview prep image (comic book style)
  3. [NEW] mmx video gen (i2v) → prep video from image
  4. Attach video to email or share link
    ↓
Candidate receives: Calendar invite + Meet link + Preparation video
```

**If the user says**: "寄準備影片" / "面試準備影片" / "發影片給候選人" → trigger this reference.

---

## Image-to-Video Workflow (mmx-cli)

**Applicable models**: `MiniMax-Hailuo-2.3` (default), `MiniMax-Hailuo-02` (first-last-frame), `S2V-01` (face consistency)

### Step 1: Generate a Safe Interview Prep Image

**School safety rule**: Always use `comic book style` / `vector illustration` / `Ghibli` for school scenarios with people. `image-01` bird's-eye + portrait + photoreal = NSFW over-fire risk.

```bash
mmx image generate \
  --prompt "comic book style, professional female teacher in smart casual attire, sitting at desk, welcoming smile, classroom background with books, overhead angle, bold ink outlines, halftone patterns" \
  --aspect-ratio 16:9 \
  --n 2 \
  --out-dir /tmp/interview_prep \
  --out-prefix prep_frame \
  --quiet
# exit 0 → ~600KB JPEG
```

**Style Safety Ranking (image-01)**:
- ✅ S: comic book, vector illustration, Ghibli (4/4 hold)
- ⚠️ C: fashion editorial (needs explicit clothing description)
- ❌ D: minimalist line art, flat colors (washed to photoreal)

### Step 2: Animate with Image-to-Video (i2v)

```bash
mmx video generate \
  --prompt "the professional teacher starts explaining the interview process with welcoming gestures, calm and encouraging tone, dynamic subtle motion, comic book style" \
  --first-frame /tmp/interview_prep/prep_frame_001.jpg \
  --model MiniMax-Hailuo-2.3 \
  --duration 6 \
  --resolution 720P \
  --download /tmp/interview_prep/candidate_prep.mp4 \
  --quiet
# exit 0 → ~1.8MB MP4, ~25s total
```

### Prompt Formula for Interview Prep Video

From `references/video-generation.md` (Hailuo-specific):

```
[Camera Shot + Motion] + [Subject + Description] + [Action] + [Scene + Description] + [Lighting] + [Style/Mood]
```

**Camera movement terms at BEGINNING** (token-weight principle).

**Do NOT**: Stack multiple camera movements in one prompt.

---

## Video Generation Exit Codes

| Exit | Meaning | Action |
|------|---------|--------|
| 0 | Success | MP4 saved |
| 1 | Usage/system error | Check flags, model name |
| 3 | Auth error | Check `--api-key` (see token filter pitfall below) |
| 5 | Timeout | Retry once |

---

## Critical Pitfall: `***` Token Filter Breaks mmx Video Gen

**Symptom**: `mmx video generate` exits with code 3, `stderr: "No credentials found."` — even when `--api-key` is passed.

**Root cause**: The `***` redaction filter in Hermes (which masks `MINIMAX_API_KEY` values) also mangles Python source code that contains the string `***` in certain patterns, OR it causes the key value read from `~/.hermes/.env` to come back empty when the key is stored as `MINIMAX_API_KEY=***` (masked).

**Verified working pattern** — use subprocess with list args, read key via shell:

```bash
# In execute_code, the key reads as empty because *** filter affects the
# value extraction. Workaround: use terminal() for mmx video/image calls
# since shell variable expansion avoids the Python-side filter.

KEY=$(grep MINIMAX_API_KEY ~/.hermes/.env | cut -d= -f2)
npx -y mmx-cli video generate \
  --api-key "$KEY" \
  --prompt "..." \
  --first-frame /tmp/interview_prep/prep_frame_001.jpg \
  --model MiniMax-Hailuo-2.3 \
  --duration 6 \
  --resolution 720P \
  --download /tmp/interview_prep/candidate_prep.mp4 \
  --quiet
```

**When to use terminal() vs execute_code()**: For any `mmx video generate` or `mmx image generate` call that passes `--api-key`, use `terminal()` (shell subprocess) not `execute_code()` (Python subprocess) — the Python subprocess inherits the filter that corrupts the key read.

---

## If→Then Rules

**If** user wants interview prep video for candidate **Then**: comic book image → i2v → send MP4 or share link

**If** `--api-key` causes exit code 3 **Then** switch to `terminal()` for mmx calls (not `execute_code`)

**If** `image-01` bird's-eye + portrait + photoreal style requested **Then** redirect to comic book / vector style first (NSFW over-fire risk)

**If** school scenario with minors **Then** verify Prompt Safety Checklist: no body-shape adjectives, no suggestive poses, fully clothed, safe-for-work context

---

## Integration with Other Skills

| Skill | Integration Point |
|-------|------------------|
| `minimax-multimodal-toolkit` | `references/video-generation.md` for Hailuo prompt formula + camera movement reference |
| `hr-document-workflow` | Document output (offer letter) → calendar invite → video prep: complete HR pipeline |
| `himalaya` | If candidate replies to email with questions, use himalaya to fetch reply |
| `google-workspace` | Google Meet URL from `create_interview.py` → attach video to same calendar event |

---

## Complete LR Sequence for "Interview + Prep Video"

```bash
# 1. Create calendar event + Meet (existing skill)
python3 ~/.hermes/skills/school-interview-scheduler/scripts/create_interview.py \
  --candidate "張三" \
  --email "zhangsan@school.edu.tw" \
  --datetime "2026-06-25 10:00" \
  --position "數學教師" \
  --duration 60

# 2. Generate prep image (comic book style — safe)
mmx image generate \
  --prompt "comic book style, professional teacher at desk, explaining topics, classroom, overhead view, bold ink outlines" \
  --aspect-ratio 16:9 --n 2 --out-dir /tmp/prep --out-prefix frame --quiet

# 3. Animate (i2v)
mmx video generate \
  --prompt "the teacher welcomes the candidate and explains the interview structure, friendly gesture, comic book style" \
  --first-frame /tmp/prep/frame_001.jpg \
  --model MiniMax-Hailuo-2.3 --duration 6 --resolution 720P \
  --download /tmp/prep/interview_prep.mp4 --quiet

# 4. Share video link with candidate (attach to email or calendar description update)
```
