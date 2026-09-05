---
name: ascii
description: ASCII art production class covering static terminal art (pyfiglet/cowsay/boxes/toilet, image-to-ASCII conversion, pre-made art search, LLM-generated Unicode) AND animated ASCII media (video-to-ASCII, audio-reactive visualizers, generative animation, hybrid video+audio). One skill for the whole ASCII art spectrum. TRIGGER on "ascii art", "text art", "ascii video", "terminal art", "matrix-style", "music visualizer ascii", "convert video to ascii", "ascii banner", "figlet".
version: 5.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ascii, art, terminal, figlet, cowsay, boxes, visualizer, video, animation, text-art]
    related_skills: [excalidraw, claude-design]
---

## Umbrella relationship (2026-09 curator pass)

ASCII art is a single creative production class with two modes: **static** (banners, borders, character art, image-to-ASCII conversion) and **animated** (video-to-ASCII, audio-reactive visualizers, generative animation). This umbrella subsumes the `ascii-art` and `ascii-video` siblings as labeled sections below; their full original SKILL.md content is preserved in `references/`. Dated recipe variants (new font tables, new effect libraries) belong in `references/recipes.md`; do not split by output format.

---

## Which mode?

| Mode | When to use | Reference |
|------|-------------|-----------|
| **Static** | One-shot terminal output — text banner, character image, decorative frame, QR code, weather art | `references/static-art.md` |
| **Animated** | Any time-based output — video file → ASCII video, audio → music visualizer, generative animation, lyrics overlay, hybrid | `references/video-art.md` + `references/architecture.md` |

Both modes share the **Creative Standard** (see below) — ASCII is visual art, terminal is the medium, cinema is the standard.

---

## Creative Standard (applies to BOTH modes)

This is visual art. ASCII characters are the medium; cinema is the standard.

**Before writing a single line of code**, articulate the creative concept. What is the mood? What visual story does this tell? What makes THIS project different from every other ASCII project? The user's prompt is a starting point — interpret it with creative ambition, not literal transcription.

**First-render excellence is non-negotiable.** The output must be visually striking without requiring revision rounds. If something looks generic, flat, or like "AI-generated ASCII art," it is wrong — rethink the creative concept before shipping.

**Go beyond the reference vocabulary.** The effect catalogs, shader presets, palette libraries in the references are a starting vocabulary. For every project, combine, modify, and invent new patterns. The catalog is a palette of paints — you write the painting.

**Be proactively creative.** Extend the skill's vocabulary when the project calls for it. If the references don't have what the vision demands, build it. Include at least one visual moment the user didn't ask for but will appreciate — a transition, an effect, a color choice that elevates the whole piece.

**Cohesive aesthetic over technical correctness.** All scenes in a video must feel connected by a unifying visual language — shared color temperature, related character palettes, consistent motion vocabulary. A technically correct video where every scene uses a random different effect is an aesthetic failure.

**Dense, layered, considered.** Every frame should reward viewing. Never flat black backgrounds. Always multi-grid composition. Always per-scene variation. Always intentional color.

---

# Part 1: Static ASCII Art (one-shot terminal output)

Full reference: `references/static-art.md`

## Tool map (decision flow)

1. **Text as a banner** → pyfiglet if installed, otherwise asciified API via curl
2. **Wrap a message in fun character art** → cowsay
3. **Add decorative border/frame** → boxes (can combine with pyfiglet/asciified)
4. **Art of a specific thing** (cat, rocket, dragon) → ascii.co.uk via curl + parsing
5. **Convert an image to ASCII** → ascii-image-converter or jp2a
6. **QR code** → qrenco.de via curl
7. **Weather/moon art** → wttr.in via curl
8. **Something custom/creative** → LLM generation with Unicode palette
9. **Any tool not installed** → install it, or fall back to next option

## Common tools quick reference

| Tool | Use | Install | Notes |
|------|-----|---------|-------|
| `pyfiglet` | Text → ASCII banner (571 fonts) | `pip install pyfiglet` | Most common banner tool |
| `asciified` | Text → ASCII banner (250+ fonts, no install) | None (curl API) | `https://asciified.thelicato.io/api/v2/ascii?text=...` |
| `cowsay` | Text → character with speech bubble | `apt install cowsay` / `brew install cowsay` | 50+ characters |
| `boxes` | Decorative borders around text | `apt install boxes` | 70+ designs |
| `toilet` | Colored text art with filters | `apt install toilet toilet-fonts` | Has color/effects filters |
| `ascii-image-converter` | Image → ASCII | `snap install ascii-image-converter` | Supports color |
| `jp2a` | JPEG → ASCII (lightweight) | `apt install jp2a` | JPEG only |
| `ascii.co.uk` | Pre-made art library | None (curl) | Parse `<pre>` tags from HTML |

## LLM-fallback character palette

When tools don't have what's needed, generate ASCII art directly using these Unicode characters:

**Box Drawing:** `╔ ╗ ╚ ╝ ║ ═ ╠ ╣ ╦ ╩ ╬ ┌ ┐ └ ┘ │ ─ ├ ┤ ┬ ┴ ┼ ╭ ╮ ╰ ╯`

**Block Elements:** `░ ▒ ▓ █ ▄ ▀ ▌ ▐ ▖ ▗ ▘ ▝ ▚ ▞`

**Geometric & Symbols:** `◆ ◇ ◈ ● ○ ◉ ■ □ ▲ △ ▼ ▽ ★ ☆ ✦ ✧ ◀ ▶ ◁ ▷ ⬡ ⬢ ⌂`

**Rules:** max width 60 chars per line (terminal-safe), max height 15 lines for banners / 25 for scenes, monospace only.

For detailed font tables, character lists, and per-tool recipes, see `references/static-art.md`.

---

# Part 2: Animated ASCII (video, audio-reactive, generative)

Full reference: `references/video-art.md`

## Modes

| Mode | Input | Output | Reference |
|------|-------|--------|-----------|
| **Video-to-ASCII** | Video file | ASCII recreation of source footage | `references/inputs.md` § Video Sampling |
| **Audio-reactive** | Audio file | Generative visuals driven by audio features | `references/inputs.md` § Audio Analysis |
| **Generative** | None (or seed params) | Procedural ASCII animation | `references/effects.md` |
| **Hybrid** | Video + audio | ASCII video with audio-reactive overlays | Both input refs |
| **Lyrics/text** | Audio + text/SRT | Timed text with visual effects | `references/inputs.md` § Text/Lyrics |
| **TTS narration** | Text quotes + TTS API | Narrated testimonial/quote video with typed text | `references/inputs.md` § TTS Integration |

## Stack

Single self-contained Python script per project. No GPU required.

| Layer | Tool | Purpose |
|-------|------|---------|
| Core | Python 3.10+, NumPy | Math, array ops, vectorized effects |
| Signal | SciPy | FFT, peak detection (audio modes) |
| Imaging | Pillow (PIL) | Font rasterization, frame decoding, image I/O |
| Video I/O | ffmpeg (CLI) | Decode input, encode output, mux audio |
| Parallel | concurrent.futures | N workers for batch/clip rendering |
| TTS | ElevenLabs API (optional) | Generate narration clips |
| Optional | OpenCV | Video frame sampling, edge detection |

## Pipeline Architecture

Every mode follows the same 6-stage pipeline:

```
INPUT → ANALYZE → SCENE_FN → TONEMAP → SHADE → ENCODE
```

1. **INPUT** — Load/decode source material (video frames, audio samples, images, or nothing)
2. **ANALYZE** — Extract per-frame features (audio bands, video luminance/edges, motion vectors)
3. **SCENE_FN** — Scene function renders to pixel canvas (`uint8 H,W,3`). Composes multiple character grids via `_render_vf()` + pixel blend modes. See `references/composition.md`
4. **TONEMAP** — Percentile-based adaptive brightness normalization. See `references/composition.md` § Adaptive Tonemap
5. **SHADE** — Post-processing via `ShaderChain` + `FeedbackBuffer`. See `references/shaders.md`
6. **ENCODE** — Pipe raw RGB frames to ffmpeg for H.264/GIF encoding

## Aesthetic dimensions (animated mode)

| Dimension | Options | Reference |
|-----------|---------|-----------|
| Character palette | Density ramps, block elements, symbols, scripts (katakana, Greek, runes, braille), project-specific | `architecture.md` § Palettes |
| Color strategy | HSV, OKLAB/OKLCH, discrete RGB palettes, auto-generated harmony, monochrome, temperature | `architecture.md` § Color System |
| Background texture | Sine fields, fBM noise, domain warp, voronoi, reaction-diffusion, cellular automata, video | `effects.md` |
| Primary effects | Rings, spirals, tunnel, vortex, waves, interference, aurora, fire, SDFs, strange attractors | `effects.md` |
| Particles | Sparks, snow, rain, bubbles, runes, orbits, flocking boids, flow-field followers, trails | `effects.md` § Particles |
| Shader mood | Retro CRT, clean modern, glitch art, cinematic, dreamy, industrial, psychedelic | `shaders.md` |
| Grid density | xs(8px) through xxl(40px), mixed per layer | `architecture.md` § Grid System |
| Coordinate space | Cartesian, polar, tiled, rotated, fisheye, Möbius, domain-warped | `effects.md` § Transforms |
| Feedback | Zoom tunnel, rainbow trails, ghostly echo, rotating mandala, color evolution | `composition.md` § Feedback |
| Masking | Circle, ring, gradient, text stencil, animated iris/wipe/dissolve | `composition.md` § Masking |
| Transitions | Crossfade, wipe, dissolve, glitch cut, iris, mask-based reveal | `shaders.md` § Transitions |

## Workflow (animated mode)

### Step 1: Creative Vision

Before any code, articulate the creative concept:

- **Mood/atmosphere**: What should the viewer feel? Energetic, meditative, chaotic, elegant, ominous?
- **Visual story**: What happens over the duration? Build tension? Transform? Dissolve?
- **Color world**: Warm/cool? Monochrome? Neon? Earth tones? What's the dominant hue?
- **Character texture**: Dense data? Sparse stars? Organic dots? Geometric blocks?
- **What makes THIS different**: What's the one thing that makes this project unique?
- **Emotional arc**: How do scenes progress? Open with energy, build to climax, resolve?

Map the user's prompt to aesthetic choices. A "chill lo-fi visualizer" demands different everything from a "glitch cyberpunk data stream."

### Step 2: Pipeline skeleton

Build the 6-stage pipeline first. Reference scripts and skeleton code: `references/video-art.md` + `references/architecture.md`.

### Step 3: Per-scene variation

Never use the same config for the entire video. For each section/scene:

- Different background effect (or compose 2-3)
- Different character palette (match the mood)
- Different color strategy (or at minimum a different hue)
- Vary shader intensity (more bloom during peaks, more grain during quiet)
- Different particle types if particles are active

### Step 4: Project-specific invention

For every project, invent at least one of:

- A custom character palette matching the theme
- A custom background effect (combine/modify existing building blocks)
- A custom color palette (discrete RGB set matching the brand/mood)
- A custom particle character set
- A novel scene transition or visual moment

Don't just pick from the catalog. The catalog is vocabulary — you write the poem.

---

## Support files

- `references/static-art.md` — full original `ascii-art` SKILL.md content (preserved)
- `references/video-art.md` — full original `ascii-video` SKILL.md content (preserved)
- `references/architecture.md` — character palettes, color systems, grid system (from `ascii-video`)
- `references/composition.md` — scene composition, tonemap, feedback, masking (from `ascii-video`)
- `references/effects.md` — background effects, particles, transforms (from `ascii-video`)
- `references/shaders.md` — shader chains, transitions, post-processing (from `ascii-video`)
- `references/inputs.md` — video/audio/text/TTS input handling (from `ascii-video`)
- `references/scenes.md` — scene composition patterns (from `ascii-video`)
- `references/optimization.md` — performance tuning (from `ascii-video`)
- `references/troubleshooting.md` — common failures + fixes (from `ascii-video`)