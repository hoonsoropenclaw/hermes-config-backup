---
name: creative-style-memory
description: "Multi-session creative style memory for AI image/video generation. Captures style parameters (lighting, palette, composition, mmx params) after successful generations and re-applies them in future sessions. Prevents 'intention drift' across creative pipeline turns."
version: 1.0.0
author: hermes-agent
platforms: [linux]
metadata:
  hermes:
    tags: [creative, image-generation, style-memory, multi-session, mmx, pipeline]
    category: creative
    cycle_created: 519
    last_cycle_updated: 551
---

## Umbrella relationship (2026-08 curator pass)

Creative style memory is the persistence subsection of creative production. It complements HTML/design, image/video generation, and delivery QA; brand- or session-specific profiles belong in its support data, not standalone skills.



Persistent style memory system for AI creative generation — prevents every session starting from random noise.

## What This Skill Does

AI image/video generation models have no brand memory — every generation starts from random noise guided by the prompt alone (Superside, 2026). This skill implements a 3-layer memory system so Hermes can remember style parameters across sessions and re-apply them automatically.

**Core problem solved**: User says "continue in the same style" days after a previous session, and Hermes has no idea what style was used.

## Trigger Mechanism (CRITICAL — without this, the skill is never invoked)

**The SOP describes WHAT but the skill MUST also define WHEN to invoke itself.**
Per arXiv:2606.06893v1 WSA Framework, the R (Routing Header) is the skill's trigger switch.
Without explicit triggers, a skill that describes "what to do" remains dead code.

### Trigger Hierarchy

**Layer 1 — User Implicit Approval (most common, most missed)**

When the user says ANY of these after a creative generation → trigger Style Memory Capture immediately:

| Signal type | Examples |
|------------|----------|
| Positive feedback | 「很好」「不錯」「滿意」「這張好」「喜歡」|
| Adoption intent | 「就用這張」「這版吧」「可以」「OK」|
| Iteration stop | 「先這樣」「先到此為止」「好了」|
| Specific praise | 「這個風格很好看」「色調很棒」|

→ **Capture BEFORE responding** — extract style params, update profile, *then* reply.

**Layer 2 — User Explicit Style Request**

| Signal type | Examples |
|------------|----------|
| Style reuse | 「跟上張一樣的風格」「延續這個風格」|
| Style adjustment | 「要更亮一些」「改成暖色調」|
| Cross-project | 「這個風格可以用在我的另一個案子」|

→ Execute Style Inheritance first, then run new generation.

**Layer 3 — System Internal Triggers**

| Trigger condition | Action |
|-----------------|--------|
| Creative pipeline delivery gate passes | Auto-execute Layer 1 capture |
| User uploads new reference image | Copy to `references/` + update profile |
| `creative_brand_profiles/` missing | Create dir structure, then write |

### WSA R-Component Rule

Every new creative SOP that describes a workflow MUST define its R (Routing Header):
```
觸發條件：[specific user signals or system events]
適用場景：[when this skill should be called]
不適用：[when NOT to call this]
```
Without an R-component, the SOP = dead code that never gets invoked.

→ Full trigger SOP: `references/creative-style-memory-trigger-20260719.md` (Cycle 521) — detailed trigger signals, Midjourney --sref reverse-engineering, 4 If→Then rules.
Also trigger **after every successful creative generation** to capture style parameters (this is the memory-writing phase, not just the retrieval phase).

## Three-Layer Memory System

| Layer | Scope | Storage | Trigger |
|-------|-------|---------|---------|
| Layer 1: In-conversation | Same session | Session TODO / style_memory dict | Auto after every successful generation |
| Layer 2: Cross-session profiles | All sessions | `~/.hermes/creative_brand_profiles/<name>.json` | "same style" / "continue" triggers |
| Layer 3: Style inheritance keywords | Intent detection | Pattern matching | User uses style inheritance words |

## Key SOPs (References)

| File | Content |
|------|---------|
| `references/creative-style-memory-20260719.md` | Full SOP: 3-layer system, If→Then rules (4 rules), validation commands, gap analysis from Talk2Image arXiv:2508.06916, Superside (2026), getimg.ai Style Elements (2026) |
| `references/creative-style-memory-20260719.md#layer-2` | Brand profile JSON schema + profile location `~/.hermes/creative_brand_profiles/` |
| `references/creative-style-memory-20260719.md#if--then` | 4 If→Then rules covering: style capture after success, style inheritance on new generation, project-specific profiles, graceful fallback when no memory exists |
| `references/design-token-pipeline-20260802.md` | **W3C DTCG v2025.10 brand token pipeline** — Style Dictionary transform, 5-tier JSON schema, CSS/JS/SCSS output, taste-skill bridge (Cycle 551 D3-learn) |

## If→Then Core Rules

### Style Memory Capture (after every successful creative generation)

**If** Hermes completes a creative generation task (image/video/speech/music) and the user expresses satisfaction
**Then** immediately execute Style Memory Capture:
1. Extract style keywords from the successful prompt (lighting, color palette, mood, composition)
2. Extract mmx params (seed, --aspect, --style-preset)
3. If user provided a reference image, copy to `~/.hermes/creative_brand_profiles/references/`
4. Update `~/.hermes/creative_brand_profiles/user_default.json` — append to `successful_prompts`, update `updated_at`
5. **This step is mandatory** — do not skip even if the user says "looks good" without further requests
6. **Verify**: run `python3 -c "import json; from pathlib import Path; p=Path.home()/.hermes/creative_brand_profiles/user_default.json; print('CAPTURED' if p.exists() and json.loads(p.read_text()).get('dominant_style') else 'CAPTURE_FAILED')"` immediately after capture to confirm it worked

### Style Inheritance (on new creative request with existing memory)

**If** user asks for a new creative generation AND `creative_brand_profiles/user_default.json` exists
**Then** before running the creative pipeline:
1. Read user_default.json
2. Generate style injection prefix: `"[dominant_style], [lighting], [color_preferences], [composition]"`
3. Prepend the style prefix to the user's prompt
4. Tell the user: `"套用風格記憶：[dominant_style]，包含 [lighting] + [color_preferences]"`

### Project-Specific Profiles

**If** user provides a specific project name (e.g., "專案：夏日行銷") for a new creative request
**Then** create a project-specific brand profile:
1. Create `~/.hermes/creative_brand_profiles/<project_name>.json` (copy structure from user_default.json)
2. All subsequent generations for this project update the same profile
3. "continue『夏日行銷』" → read that project profile, not user_default

### Graceful Fallback

**If** user asks for "same style as before" but user_default.json has no `dominant_style` record
**Then** ask the user for clarification — do not guess:
> "檢測到您提到「沿用之前的風格」，但當前沒有記錄到之前的風格參數。請提供：
> 1. 參考圖片（可直接貼上）
> 2. 或者描述您想要的風格關鍵詞（如：色調，光線、構圖，情緒）
> 這樣下次我就能自動記住了。"

**If** user asks for "style memory" operations but multiple profiles exist in `creative_brand_profiles/`
**Then** list all profiles with their `updated_at` timestamps and ask the user to confirm which project:
> "以下是目前記錄的風格檔案：
> - user_default (更新：2026-07-19)
> - 夏日行銷 (更新：2026-07-20)
> 請問您要沿用哪一個？"

### Retroactive Capture from Session History

**If** user asks to reuse a style from a previous session, but `user_default.json` is empty
**Then** search session history (via session_search or state.db) for that session's creative generation prompts and reconstruct the style parameters from there:
1. Query state.db for sessions with creative generation topics near the referenced date
2. Extract successful generation prompts from those sessions
3. Reconstruct dominant_style, color_preferences, lighting from prompt keywords
4. Populate user_default.json before executing the new generation

## Brand Profile Schema

```json
{
  "profile_name": "user_default",
  "created_at": "2026-07-19",
  "updated_at": "2026-07-19",
  "dominant_style": "watercolor illustration",
  "color_preferences": ["#E8D5B7", "#8B7355", "#F5F0E8"],
  "lighting": "soft natural",
  "composition": "centered subject, negative space",
  "avoid": ["harsh shadows", "text overlays", "anime style"],
  "reference_images": [],
  "last_session_id": "20260708_070038",
  "successful_prompts": [
    "A serene mountain lake at dawn, watercolor style, soft light..."
  ],
  "moderation_escape_phrases": ["artistic interpretation", "illustrative portrait"]
}
```

Profile directory: `~/.hermes/creative_brand_profiles/`

## Validation Command

```bash
python3 -c "
import json
from pathlib import Path
profile_path = Path.home() / '.hermes/creative_brand_profiles/user_default.json'
if profile_path.exists():
    p = json.loads(profile_path.read_text())
    required_keys = ['dominant_style', 'color_preferences', 'lighting', 'successful_prompts']
    missing = [k for k in required_keys if k not in p or not p[k]]
    print('MEMORY_COMPLETE' if not missing else f'MEMORY_INCOMPLETE: {missing}')
else:
    print('PROFILE_NOT_FOUND')
"
```

## External Sources

- **Talk2Image** (arXiv:2508.06916): Intention Drift is the #1 challenge in multi-turn image generation. Dialogue State Memory `Hₜ = {(u₁,r₁), ..., (uₜ₋₁,rₜ₋₁)}` prevents drift.
- **Superside** (June 2026): "AI doesn't know your brand. Most tools rely on generic data. Once an image is generated, your brand is forgotten, wiped clean."
- **getimg.ai Style Elements** (2026): Style Element = saved reference set (palette, lighting, finish, mood), called with `@StyleName` in any prompt. 8-15 diverse reference images produce reliably consistent conditioning.

## Relationship to Other Creative Skills

| Skill | Covers | Gap This Solves |
|-------|--------|----------------|
| `creative-intent-classification` | Request classification + 6-type routing | What to generate |
| `creative-pipeline-dag` | Multi-step pipeline orchestration | How to chain generation steps |
| `creative-pipeline-execution-state` | Checkpoint/retry for pipelines | How to recover from failures |
| `creative-output-quality-verification` | Post-generation quality checks | Is the output any good? |
| `image-moderation-reframing` | Content moderation handling | How to escape moderation |
| **`creative-style-memory`** | **Cross-session style memory** | **What style to use across sessions** |
| `comfyui` | ComfyUI workflow execution | Technical pipeline execution |
| `baoyu-article-illustrator` | Article illustration workflow | Article-specific image pipeline |

## ⚠️ D2 Execution Gap — CLOSED (Cycle 551, 2026-08-02)

**Discovery**: `creative-style-memory` SOP was created at Cycle 519 with complete 3-layer system, 4 If→Then rules, and brand profile schema — but `user_default.json` was **empty** as of Cycle 550. The `creative_brand_profiles/` directory was confirmed MISSING for 25+ cycles.

**Action taken (Cycle 551)**:
- Created `~/.hermes/skills/taste-skill-repo/skills/creative_brand_profiles/brand_tokens.json` — W3C DTCG v2025.10 compliant, 5-tier structure
- Created `brand_tokens_transform.py` — Style Dictionary pipeline, outputs CSS + JS + SCSS
- Generated `dist/tokens.css` (67 lines), `dist/tokens.mjs` (67 lines), `dist/_tokens.scss` (99 lines) — 99 resolved tokens
- `$themes` maps taste-skill 3-dial values: hermes_default (6/4/4), taste_dial_high (8/6/4), taste_dial_low (4/4/6)
- **Gap status**: CLOSED (D2→D3 exit)

**The SOP is not the deliverable. Executed memory is the deliverable.**

**Every creative generation success must trigger mandatory capture, no exceptions.**

---

## Pitfalls

1. **Capture is mandatory** — don't skip Style Memory Capture after a successful generation because "the user didn't ask for another one". The next session depends on it.
2. **Don't guess on fallback** — if no style memory exists and user asks for "same style", ask for clarification rather than generating something random.
3. **Reference images need to be copied locally** — if user provides a reference image URL, download it to `~/.hermes/creative_brand_profiles/references/` before updating the profile.
4. **Layer 2 profiles persist** — unlike session memory (Layer 1), Layer 2 profiles survive session boundaries. Keep them updated after every successful generation.
5. **SOP existence ≠ SOP execution** — if `user_default.json` is empty after any creative generation, the capture step was skipped. Verify with: `python3 -c "import json; from pathlib import Path; p=Path.home()/.hermes/creative_brand_profiles/user_default.json; print('EXISTS' if p.exists() and json.loads(p.read_text()).get('dominant_style') else 'EMPTY_OR_MISSING')"`
6. **Style Inheritance must happen BEFORE pipeline, not after** — mmx generate must read the profile first, then inject style prefix into prompt. If generation runs before reading profile, the memory system is bypassed entirely.
7. **Style reference via W3C DTCG tokens (Cycle 551)** — mmx has no `--sref` equivalent, but `brand_tokens.json` provides a partial workaround: store hex values + typography + motion tokens in the 5-tier JSON, then inject token references into generation prompts. GSAP uses `--motion.ease.ease-out` (cubic-bezier) from `dist/tokens.css` instead of string literals. Full pipeline: `brand_tokens_transform.py` → CSS/JS/SCSS → prompt injection.
8. **Temporal durable execution applies** — checkpoint directory `creative_pipeline_checkpoints/` exists but is empty. The D2 gap is "checkpoint write never called", not "checkpoint mechanism missing". After every successful creative pipeline completion, write a checkpoint even if the workflow succeeded — this is how the pipeline becomes resumable.
