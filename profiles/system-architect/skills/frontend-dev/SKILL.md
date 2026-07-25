---
name: frontend-dev
description: |
  Full-stack frontend development combining premium UI design, cinematic animations,
  AI-generated media assets, persuasive copywriting, and visual art. Builds complete,
  visually striking web pages with real media, advanced motion, and compelling copy.
  Use when: building landing pages, marketing sites, product pages, dashboards,
  generating media assets (image/video/audio/music), writing conversion copy,
  creating generative art, or implementing cinematic scroll animations.
license: MIT
metadata:
  version: "1.0.0"
  category: frontend
  sources:
    - taste-skill by Leonxlnx (https://github.com/Leonxlnx/taste-skill) — Design engineering framework
    - canvas-design by Anthropic (https://github.com/anthropics/skills/tree/main/skills/canvas-design) — Static visual art workflow
    - algorithmic-art by Anthropic (https://github.com/anthropics/skills/tree/main/skills/algorithmic-art) — Generative art workflow
    - Framer Motion documentation
    - GSAP / GreenSock documentation
    - Three.js documentation
    - Tailwind CSS documentation
    - React / Next.js documentation
    - AIDA Framework (Elmo Lewis)
    - p5.js documentation
---

# Frontend Studio

Build complete, production-ready frontend pages by orchestrating 5 specialized capabilities: design engineering, motion systems, AI-generated assets, persuasive copy, and generative art.

## Invocation

```
/frontend-dev <request>
```

The user provides their request as natural language (e.g. "build a landing page for a music streaming app").

## Pre-requisite: Planning Gate

**Before any implementation work, check if program-project-planner should be triggered.**

- For **ANY new project, feature, or non-trivial task** — regardless of how clear the request seems — trigger `program-project-planner` FIRST unless the user explicitly says "直接實作" (direct implementation).
- Only proceed directly to implementation (skip planning) when:
  1. User explicitly writes "直接實作" or "直接做"
  2. Task is a single, simple, well-defined action (e.g., "rename this file", "check the weather")
  3. Emergency hotfix scenario

**This is a hard rule.** Skipping planning when it should have been triggered is the primary failure mode for this skill. When in doubt, trigger planning — the cost of a planning pass is far less than the cost of building the wrong thing.

```

```
frontend-dev/
├── SKILL.md                      # Core skill (this file)
├── scripts/                      # Asset generation scripts
│   ├── minimax_tts.py            # Text-to-speech
│   ├── minimax_music.py          # Music generation
│   ├── minimax_video.py          # Video generation (async)
│   └── minimax_image.py          # Image generation
├── references/                   # Detailed guides (read as needed)
│   ├── minimax-cli-reference.md  # CLI flags quick reference
│   ├── asset-prompt-guide.md     # Asset prompt engineering rules
│   ├── minimax-tts-guide.md      # TTS usage & voices
│   ├── minimax-music-guide.md    # Music prompts & lyrics format
│   ├── minimax-video-guide.md    # Camera commands & models
│   ├── minimax-image-guide.md    # Ratios & batch generation
│   ├── minimax-voice-catalog.md  # All voice IDs
│   ├── motion-recipes.md         # Animation code snippets
│   ├── env-setup.md              # Environment setup
│   └── troubleshooting.md        # Common issues
├── templates/                    # Visual art templates
│   ├── viewer.html               # p5.js interactive art base
│   └── generator_template.js     # p5.js code reference
└── canvas-fonts/                 # Static art fonts (TTF + licenses)
```

## Project Structure

### Assets (Universal)

All frameworks use the same asset organization:

```
assets/
├── images/
│   ├── hero-landing-1710xxx.webp
│   ├── icon-feature-01.webp
│   └── bg-pattern.svg
├── videos/
│   ├── hero-bg-1710xxx.mp4
│   └── demo-preview.mp4
└── audio/
    ├── bgm-ambient-1710xxx.mp3
    └── tts-intro-1710xxx.mp3
```

**Asset naming:** `{type}-{descriptor}-{timestamp}.{ext}`

### By Framework

| Framework | Asset Location | Component Location |
|-----------|---------------|-------------------|
| **Pure HTML** | `./assets/` | N/A (inline or `./js/`) |
| **React/Next.js** | `public/assets/` | `src/components/` |
| **Vue/Nuxt** | `public/assets/` | `src/components/` |
| **Svelte/SvelteKit** | `static/assets/` | `src/lib/components/` |
| **Astro** | `public/assets/` | `src/components/` |

### Pure HTML

```
project/
├── index.html
├── assets/
│   ├── images/
│   ├── videos/
│   └── audio/
├── css/
│   └── styles.css
└── js/
    └── main.js           # Animations (GSAP/vanilla)
```

### React / Next.js

```
project/
├── public/assets/        # Static assets
├── src/
│   ├── components/
│   │   ├── ui/           # Button, Card, Input
│   │   ├── sections/     # Hero, Features, CTA
│   │   └── motion/       # RevealSection, StaggerGrid
│   ├── lib/
│   ├── styles/
│   └── app/              # Pages
└── package.json
```

### Vue / Nuxt

```
project/
├── public/assets/
├── src/                  # or root for Nuxt
│   ├── components/
│   │   ├── ui/
│   │   ├── sections/
│   │   └── motion/
│   ├── composables/      # Shared logic
│   ├── pages/
│   └── assets/           # Processed assets (optional)
└── package.json
```

### Astro

```
project/
├── public/assets/
├── src/
│   ├── components/       # .astro, .tsx, .vue, .svelte
│   ├── layouts/
│   ├── pages/
│   └── styles/
└── package.json
```

**Component naming:** PascalCase (`HeroSection.tsx`, `HeroSection.vue`, `HeroSection.astro`)

---

## Compliance

**All rules in this skill are mandatory. Violating any rule is a blocking error — fix before proceeding or delivering.**

---

## Workflow
### Phase 1: Design Architecture
1. Analyze the request — determine page type and context
2. Set design dials based on page type
3. Plan layout sections and identify asset needs

### Phase 2: Motion Architecture
1. Select animation tools per section (see Tool Selection Matrix)
2. Plan motion sequences following performance guardrails

### Phase 3: Asset Generation
Generate all image/video/audio assets using `scripts/`. NEVER use placeholder URLs (unsplash, picsum, placeholder.com, via.placeholder, placehold.co, etc.) or external URLs.

1. Parse asset requirements (type, style, spec, usage)
2. Craft optimized prompts, show to user, confirm before generating
3. Execute via scripts, save to project — do NOT proceed to Phase 5 until all assets are saved locally

### Phase 4: Copywriting & Content
Follow copywriting frameworks (AIDA, PAS, FAB) to craft all text content. Do NOT use "Lorem ipsum" — write real copy.

### Phase 5: Build UI
Scaffold the project and build each section following Design and Motion rules. Integrate generated assets and copy. All `<img>`, `<video>`, `<source>`, and CSS `background-image` MUST reference local assets from Phase 3.

### Phase 6: Quality Gates
Run final checklist (see Quality Gates section).

---

# 1. Design Engineering

## 1.1 Baseline Configuration

| Dial | Default | Range |
|------|---------|-------|
| DESIGN_VARIANCE | 8 | 1=Symmetry, 10=Asymmetric |
| MOTION_INTENSITY | 6 | 1=Static, 10=Cinematic |
| VISUAL_DENSITY | 4 | 1=Airy, 10=Packed |

Adapt dynamically based on user requests.

## 1.2 Architecture Conventions
- **DEPENDENCY VERIFICATION:** Check `package.json` before importing any library. Output install command if missing.
- **Framework:** React/Next.js. Default to Server Components. Interactive components must be isolated `"use client"` leaf components.
- **Styling:** Tailwind CSS. Check version in `package.json` — NEVER mix v3/v4 syntax.
- **ANTI-EMOJI POLICY:** NEVER use emojis anywhere. Use Phosphor or Radix icons only.
- **Viewport:** Use `min-h-[100dvh]` not `h-screen`. Use CSS Grid not flex percentage math.
- **Layout:** `max-w-[1400px] mx-auto` or `max-w-7xl`.

## 1.3 Design Rules
| Rule | Directive |
|------|-----------|
| Typography | Headlines: `text-4xl md:text-6xl tracking-tighter`. Body: `text-base leading-relaxed max-w-[65ch]`. **NEVER** use Inter — use Geist/Outfit/Satoshi. **NEVER** use Serif on dashboards. |
| Color | Max 1 accent, saturation < 80%. **NEVER** use AI purple/blue. Stick to one palette. |
| Layout | **NEVER** use centered heroes when VARIANCE > 4. Force split-screen or asymmetric layouts. |
| Cards | **NEVER** use generic cards when DENSITY > 7. Use `border-t`, `divide-y`, or spacing. |
| States | **ALWAYS** implement: Loading (skeleton), Empty, Error, Tactile feedback (`scale-[0.98]`). |
| Forms | Label above input. Error below. `gap-2` for input blocks. |

## 1.4 Anti-Slop Techniques

- **Liquid Glass:** `backdrop-blur` + `border-white/10` + `shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`
- **Magnetic Buttons:** Use `useMotionValue`/`useTransform` — never `useState` for continuous animations
- **Perpetual Motion:** When INTENSITY > 5, add infinite micro-animations (Pulse, Float, Shimmer)
- **Layout Transitions:** Use Framer `layout` and `layoutId` props
- **Stagger:** Use `staggerChildren` or CSS `animation-delay: calc(var(--index) * 100ms)`

## 1.5 Forbidden Patterns
| Category | Banned |
|----------|--------|
| Visual | Neon glows, pure black (#000), oversaturated accents, gradient text on headers, custom cursors |
| Typography | Inter font, oversized H1s, Serif on dashboards |
| Layout | 3-column equal card rows, floating elements with awkward gaps |
| Components | Default shadcn/ui without customization |

## 1.6 Creative Arsenal

| Category | Patterns |
|----------|----------|
| Navigation | Dock magnification, Magnetic button, Gooey menu, Dynamic island, Radial menu, Speed dial, Mega menu |
| Layout | Bento grid, Masonry, Chroma grid, Split-screen scroll, Curtain reveal |
| Cards | Parallax tilt, Spotlight border, Glassmorphism, Holographic foil, Swipe stack, Morphing modal |
| Scroll | Sticky stack, Horizontal hijack, Locomotive sequence, Zoom parallax, Progress path, Liquid swipe |
| Gallery | Dome gallery, Coverflow, Drag-to-pan, Accordion slider, Hover trail, Glitch effect |
| Text | Kinetic marquee, Text mask reveal, Scramble effect, Circular path, Gradient stroke, Kinetic grid |
| Micro | Particle explosion, Pull-to-refresh, Skeleton shimmer, Directional hover, Ripple click, SVG draw, Mesh gradient, Lens blur |

## 1.7 Bento Paradigm

- **Palette:** Background `#f9fafb`, cards pure white with `border-slate-200/50`
- **Surfaces:** `rounded-[2.5rem]`, diffusion shadow
- **Typography:** Geist/Satoshi, `tracking-tight` headers
- **Labels:** Outside and below cards
- **Animation:** Spring physics (`stiffness: 100, damping: 20`), infinite loops, `React.memo` isolation

**5-Card Archetypes:**
1. Intelligent List — auto-sorting with `layoutId`
2. Command Input — typewriter + blinking cursor
3. Live Status — breathing indicators
4. Wide Data Stream — infinite horizontal carousel
5. Contextual UI — staggered highlight + float-in toolbar

## 1.8 Brand Override

When brand styling is active:
- Dark: `#141413`, Light: `#faf9f5`, Mid: `#b0aea5`, Subtle: `#e8e6dc`
- Accents: Orange `#d97757`, Blue `#6a9bcc`, Green `#788c5d`
- Fonts: Poppins (headings), Lora (body)

---

# 2. Motion Engine

## 2.1 Tool Selection Matrix

| Need | Tool |
|------|------|
| UI enter/exit/layout | **Framer Motion** — `AnimatePresence`, `layoutId`, springs |
| Scroll storytelling (pin, scrub) | **GSAP + ScrollTrigger** — frame-accurate control |
| Looping icons | **Lottie** — lazy-load (~50KB) |
| 3D/WebGL | **Three.js / R3F** — isolated `<Canvas>`, own `"use client"` boundary |
| Hover/focus states | **CSS only** — zero JS cost |
| Native scroll-driven | **CSS** — `animation-timeline: scroll()` |

**Conflict Rules [MANDATORY]:**
- NEVER mix GSAP + Framer Motion in same component
- R3F MUST live in isolated Canvas wrapper
- ALWAYS lazy-load Lottie, GSAP, Three.js

## 2.2 Intensity Scale

| Level | Techniques |
|-------|------------|
| 1-2 Subtle | CSS transitions only, 150-300ms |
| 3-4 Smooth | CSS keyframes + Framer animate, stagger ≤3 items |
| 5-6 Fluid | `whileInView`, magnetic hover, parallax tilt |
| 7-8 Cinematic | GSAP ScrollTrigger, pinned sections, horizontal hijack |
| 9-10 Immersive | Full scroll sequences, Three.js particles, WebGL shaders |

## 2.3 Animation Recipes

See `references/motion-recipes.md` for full code. Summary:

| Recipe | Tool | Use For |
|--------|------|---------|
| Scroll Reveal | Framer | Fade+slide on viewport entry |
| Stagger Grid | Framer | Sequential list animations |
| Pinned Timeline | GSAP | Horizontal scroll with pinning |
| Tilt Card | Framer | Mouse-tracking 3D perspective |
| Magnetic Button | Framer | Cursor-attracted buttons |
| Text Scramble | Vanilla | Matrix-style decode effect |
| SVG Path Draw | CSS | Scroll-linked path animation |
| Horizontal Scroll | GSAP | Vertical-to-horizontal hijack |
| Particle Background | R3F | Decorative WebGL particles |
| Layout Morph | Framer | Card-to-modal expansion |

## 2.4 Performance Rules
**GPU-only properties (ONLY animate these):** `transform`, `opacity`, `filter`, `clip-path`

**NEVER animate:** `width`, `height`, `top`, `left`, `margin`, `padding`, `font-size` — if you need these effects, use `transform: scale()` or `clip-path` instead.

**Isolation:**
- Perpetual animations MUST be in `React.memo` leaf components
- `will-change: transform` ONLY during animation
- `contain: layout style paint` on heavy containers

**Mobile:**
- ALWAYS respect `prefers-reduced-motion`
- ALWAYS disable parallax/3D on `pointer: coarse`
- Cap particles: desktop 800, tablet 300, mobile 100
- Disable GSAP pin on mobile < 768px

**Cleanup:** Every `useEffect` with GSAP/observers MUST `return () => ctx.revert()`

## 2.5 Springs & Easings

| Feel | Framer Config |
|------|---------------|
| Snappy | `stiffness: 300, damping: 30` |
| Smooth | `stiffness: 150, damping: 20` |
| Bouncy | `stiffness: 100, damping: 10` |
| Heavy | `stiffness: 60, damping: 20` |

| CSS Easing | Value |
|------------|-------|
| Smooth decel | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Smooth accel | `cubic-bezier(0.7, 0, 0.84, 0)` |
| Elastic | `cubic-bezier(0.34, 1.56, 0.64, 1)` |

## 2.6 Accessibility
- ALWAYS wrap motion in `prefers-reduced-motion` check
- NEVER flash content > 3 times/second (seizure risk)
- ALWAYS provide visible focus rings (use `outline` not `box-shadow`)
- ALWAYS add `aria-live="polite"` for dynamically revealed content
- ALWAYS include pause button for auto-playing animations

## 2.7 Dependencies

```bash
npm install framer-motion           # UI (keep at top level)
npm install gsap                    # Scroll (lazy-load)
npm install lottie-react            # Icons (lazy-load)
npm install three @react-three/fiber @react-three/drei  # 3D (lazy-load)
```

---

# 3. Vercel Deployment (Update Existing Project)

### When to Use This Path
When updating a Vercel project that **already exists** and is connected to a GitHub repo:

| Situation | Method |
|-----------|--------|
| GitHub repo auto-deploy configured | Push to GitHub → Vercel auto-deploys |
| Need immediate deploy / GitHub not triggering | Vercel API with base64 file upload |

### Path A: GitHub Push (Auto-deploy)
```bash
gh auth status  # verify SSH auth (HTTPS tokens don't work from CI/automated envs)
git remote set-url origin git@github.com:{owner}/{repo}.git
git push -u origin main --force
```

### Path B: Vercel API (Direct Upload — Most Reliable)
```python
import urllib.request, json, base64, os

BASE = '/path/to/project'
# Read token from .env
with open('/home/{user}/.hermes/.env') as f:
    token = next(l for l in f if 'VERCEL_API_TOKEN' in l).split('=', 1)[1].strip()

# Collect all project files (walk dirs, skip .git)
files = []
for root, dirs, filenames in os.walk(BASE):
    dirs[:] = [d for d in dirs if d != '.git']
    for fname in filenames:
        fpath = os.path.join(root, fname)
        with open(fpath, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        files.append({"file": os.path.relpath(fpath, BASE), "data": data, "encoding": "base64"})

payload = {
    "name": "{project-name}",
    "files": files,
    "projectSettings": {"framework": None, "buildCommand": None,
                        "outputDirectory": None, "installCommand": None},
    "target": "production"
}

req = urllib.request.Request(
    "https://api.vercel.com/v13/deployments",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read())
    print(result["id"], result["url"], result["readyState"])

# Poll until READY
import time
deploy_id = result["id"]
for _ in range(12):
    req2 = urllib.request.Request(f"https://api.vercel.com/v13/deployments/{deploy_id}",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req2, timeout=30) as r:
        st = json.loads(r.read())["readyState"]
    print("Status:", st)
    if st == "READY":
        print("Deployed:", f"https://{result['url']}")
        break
    time.sleep(5)
```

**Token format:** `vcp_...`. Read from `~/.hermes/.env`, not `~/.vercel/`.
**Static HTML:** set `framework: None`. Alias (`*.vercel.app`) assigned separately from deployment URL.

**⚠️ Pitfall: `vercel` CLI ignores `~/.hermes/.env`**
The CLI stores tokens in `~/.vercel/config.json` and does NOT read `~/.hermes/.env`. If `vercel --yes` fails with "token is not valid", the token is NOT expired — the CLI just can't find it. **Always use Path B (REST API) directly.** The CLI path is unreliable from automated environments.

### Post-Deploy End-to-End Verification (MANDATORY)

**The most common false-positive:** Running `curl https://your-app.vercel.app` from the deploy machine and seeing `HTTP 200`, then reporting "deployment successful" to the user — only for the user to report `ERR_NAME_NOT_RESOLVED` from their browser 5 minutes later.

**Why this happens:**
- Vercel assigns a new random alias URL per deployment (e.g., `dashboard-abc12345-hoonsors-projects.vercel.app`)
- New alias URLs take 5-30 minutes to propagate globally via DNS
- Your deployment machine may resolve via cached DNS, but the user's ISP/browser doesn't have the new record yet
- The `cff3cpte4` style random aliases are the slow ones; the `hoonsors-projects` fixed aliases are faster but still need propagation

**Mandatory 4-layer verification after every Vercel deploy:**

```bash
# Layer 1: HTTP from deployment machine
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  https://<project>-vercel.app  # use the FIXED/main domain, not the random alias

# Layer 2: Multi-DNS resolution
for dns in 1.1.1.1 8.8.8.8 9.9.9.9; do
  dig +short @$dns <project>.vercel.app A
done
# All three should return IPs

# Layer 3: Vercel API deployment state
vercel ls --token "$VERCEL_API_TOKEN" 2>&1 | grep "<project>"
# Should show "● Ready    Production"

# Layer 4: END-TO-END via headless browser
# CRITICAL: navigate to the INDEX page (e.g., /), not the inner file directly.
# Click through the same flow the user would.
# If the page uses innerHTML to load content, test THAT path.
browser_navigate(url="https://<project>.vercel.app/")  # not /tabs/xxx.html
```

**User instructions to include in deployment report:**
```
建議先按 Ctrl+Shift+R (強制 reload) 清 cache
或用 Chrome 無痕模式 Ctrl+Shift+N 開新視窗
或暫時改 DNS 為 1.1.1.1 (繞過 ISP cache)
```

**The single fixed domain** (`<project>.vercel.app`) is what users should bookmark. Random aliases are for your verification only.

**Self-audit checklist before reporting "deployment successful":**
1. ✅ Fixed domain returns 200 (not just the random alias)
2. ✅ Multi-DNS resolves to IPs (not just your local DNS)
3. ✅ Vercel API shows Ready state
4. ✅ Headless browser navigated the REAL user flow (clicking through tabs, not just curling files)
5. ✅ User-facing URL provided with cache-bypass instructions

**The bar:** "It works on the deployment machine" is NOT enough. The bar is "it works for the user, on their device, on their network, in their browser."

### SPA Tab + XHR Race Pitfall

When building a tab-based SPA (index.html + tabs/*.html), a common pattern is:
1. `loadTab()` fetches tab HTML, injects via `innerHTML`
2. Calls `window.tabInit()` to trigger a data fetch (XHR) that populates the injected DOM

**The bug:** `contentDiv.innerHTML = html` (synchronous DOM write) does NOT guarantee the browser has painted the new elements before the next line runs. The XHR fires, but `document.getElementById('target')` returns null — because the old DOM is still painted.

**Symptoms:** Works in console after `setTimeout(..., 2000)`, but not immediately after `loadTab()` returns. Function exists (`typeof tabInit === 'function'`), target element returns null.

**Fix options (pick one):**
```javascript
// Option A: requestAnimationFrame deferral (recommended)
contentDiv.innerHTML = html;
requestAnimationFrame(function() {
    if (window.mdFilesInit) window.mdFilesInit();
});

// Option B: MutationObserver on the content container
var observer = new MutationObserver(function() {
    observer.disconnect();
    if (window.mdFilesInit) window.mdFilesInit();
});
observer.observe(contentDiv, { childList: true });

// Option C: Explicit post-injection init call in loadTab()
contentDiv.innerHTML = contentEl.innerHTML;
if (tabName === 'mdfiles' && window.mdFilesInit) {
    window.mdFilesInit();
}
```

**Pattern:** Any time you inject HTML and immediately call a function that queries the DOM, you have a race. Always defer DOM access to the next animation frame, or call init AFTER the DOM mutation is guaranteed.

### `innerHTML` Does NOT Execute `<script>` (More Fundamental)

**This is more fundamental than the race condition above.** When you inject HTML via `innerHTML`, the browser does NOT execute `<script>` tags inside the injected content — per HTML5 spec. This includes scripts that dynamically build DOM (radar charts, charts, widgets).

**Symptoms (deceptive):**
- Opening `tabs/overview.html` directly in a browser works fine — script runs, SVG renders
- But when `loadTab()` injects the same file via `innerHTML`, the script silently fails to run
- The container `<div>` is rendered, but is empty inside
- `console.log` from the script doesn't appear
- Headless browser tests can also mislead you if you only test the standalone file

**Fix options (pick one):**

```javascript
// Option A: Inline the generated DOM directly in the HTML
// (best for static/parameterized content like radar charts, no need for runtime JS)
// Pre-compute SVG coordinates in Python, paste directly into HTML
<svg viewBox="0 0 320 320">
  <polygon points="160,132.5 188,143.5 ..." />
  <text>...</text>
</svg>

// Option B: Extract and eval scripts from injected content
async function loadTab(tabName) {
    const response = await fetch(`tabs/${tabName}.html`);
    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    // Get the content
    const contentEl = doc.querySelector('#tab-content') || doc.body;
    contentDiv.innerHTML = contentEl.innerHTML;

    // Extract and execute any scripts
    const scripts = contentEl.querySelectorAll('script');
    scripts.forEach(oldScript => {
        const newScript = document.createElement('script');
        Array.from(oldScript.attributes).forEach(attr => {
            newScript.setAttribute(attr.name, attr.value);
        });
        newScript.textContent = oldScript.textContent;
        oldScript.parentNode.replaceChild(newScript, oldScript);
    });
}

// Option C: Move JS to index.html, initialized after innerHTML write
// Define init functions in index.html, called after each loadTab()
```

**Pattern:** For dynamic content (charts, animations, anything that needs runtime JS), either:
1. Pre-compute and inline (simplest, no runtime cost)
2. Extract-and-eval scripts in loadTab() (more complex, preserves JS)
3. Move all init logic to index.html, call after injection

**Verification pitfall:** Always test the PRODUCTION flow — navigate to the page, click the tab, observe. Don't only test the standalone HTML file in a browser; the test passes but the bug hides in innerHTML.

---

### Three-Layer Separation (Mandatory for SPA Frontend)

All SPA frontend work MUST follow this structure — never collapse multiple concerns into one file:

```
project/
  tabs/
    page.html         ← Pure HTML + data-* attributes (NO inline script, NO inline CSS)
  css/
    page.css          ← Styles (separate file)
  js/
    page.js           ← Logic (separate file)
  assets/
    page-data.json    ← Data (separate file, written by sync scripts)

index.html             ← Shell only: layout, loadTab(), CSS/JS references
```

| Layer | Responsibility | What it MUST NOT have |
|-------|---------------|----------------------|
| structure (HTML) | DOM structure, data-* attributes for JS to read | inline `<script>`, inline `<style>` |
| style (CSS) | All visual rules | JS logic |
| logic (JS) | All behavior, XHR, rendering | Data content (use JSON instead) |
| data (JSON) | Pure data, written by sync scripts | Formatting, HTML |

**Why:** When a bug occurs, you know exactly which layer to look at. A logic bug → `page.js`. A style bug → `page.css`. A data bug → `page-data.json`. Never "everything is in one file so I don't know where to start."

**Sync script rule:** The sync script (e.g., `sync_md_files.py`) writes ONLY to the JSON data file. It does NOT inject HTML or touch the JS file. This keeps the sync script simple and the HTML/JS stable.

---

# 4. Asset Generation

## 4.1 Scripts

| Type | Script | Pattern |
|------|--------|---------|
| TTS | `scripts/minimax_tts.py` | Sync |
| Music | `scripts/minimax_music.py` | Sync |
| Video | `scripts/minimax_video.py` | Async (create → poll → download) |
| Image | `scripts/minimax_image.py` | Sync |

Env: `MINIMAX_API_KEY` (required).

## 4.2 Workflow
1. **Parse:** type, quantity, style, spec, usage
2. **Craft prompt:** Be specific (composition, lighting, style). **NEVER** include text in image prompts.
3. **Execute:** Show prompt to user, **MUST confirm before generating**, then run script
4. **Save:** `<project>/public/assets/{images,videos,audio}/` as `{type}-{descriptor}-{timestamp}.{ext}` — **MUST save locally**
5. **Post-process:** Images → WebP, Videos → ffmpeg compress, Audio → normalize
6. **Deliver:** File path + code snippet + CSS suggestion

## 4.3 Preset Shortcuts

| Shortcut | Spec |
|----------|------|
| `hero` | 16:9, cinematic, text-safe |
| `thumb` | 1:1, centered subject |
| `icon` | 1:1, flat, clean background |
| `avatar` | 1:1, portrait, circular crop ready |
| `banner` | 21:9, OG/social |
| `bg-video` | 768P, 6s, `[Static shot]` |
| `video-hd` | 1080P, 6s |
| `bgm` | 30s, no vocals, loopable |
| `tts` | MiniMax HD, MP3 |

## 4.4 Reference

- `references/minimax-cli-reference.md` — CLI flags
- `references/asset-prompt-guide.md` — Prompt rules
- `references/minimax-voice-catalog.md` — Voice IDs
- `references/minimax-tts-guide.md` — TTS usage
- `references/minimax-music-guide.md` — Music generation (prompts, lyrics, structure tags)
- `references/minimax-video-guide.md` — Camera commands
- `references/minimax-image-guide.md` — Ratios, batch

---

# 5. Copywriting

## 5.1 Core Job

1. Grab attention → 2. Create desire → 3. Remove friction → 4. Prompt action

## 5.2 Frameworks

**AIDA** (landing pages, emails):
```
ATTENTION:  Bold headline (promise or pain)
INTEREST:   Elaborate problem ("yes, that's me")
DESIRE:     Show transformation
ACTION:     Clear CTA
```

**PAS** (pain-driven products):
```
PROBLEM:    State clearly
AGITATE:    Make urgent
SOLUTION:   Your product
```

**FAB** (product differentiation):
```
FEATURE:    What it does
ADVANTAGE:  Why it matters
BENEFIT:    What customer gains
```

## 5.3 Headlines

| Formula | Example |
|---------|---------|
| Promise | "Double open rates in 30 days" |
| Question | "Still wasting 10 hours/week?" |
| How-To | "How to automate your pipeline" |
| Number | "7 mistakes killing conversions" |
| Negative | "Stop losing leads" |
| Curiosity | "The one change that tripled bookings" |
| Transformation | "From 50 to 500 leads" |

Be specific. Lead with outcome, not method.

## 5.4 CTAs

**Bad:** Submit, Click here, Learn more

**Good:** "Start my free trial", "Get the template now", "Book my strategy call"

**Formula:** [Action Verb] + [What They Get] + [Urgency/Ease]

Place: above fold, after value, multiple on long pages.

## 5.5 Emotional Triggers

| Trigger | Example |
|---------|---------|
| FOMO | "Only 3 spots left" |
| Fear of loss | "Every day without this, you're losing $X" |
| Status | "Join 10,000+ top agencies" |
| Ease | "Set it up once. Forget forever." |
| Frustration | "Tired of tools that deliver nothing?" |
| Hope | "Yes, you CAN hit $10K MRR" |

## 5.6 Objection Handling

| Objection | Response |
|-----------|----------|
| Too expensive | Show ROI: "Pays for itself in 2 weeks" |
| Won't work for me | Social proof from similar customer |
| No time | "Setup takes 10 minutes" |
| What if it fails | "30-day money-back guarantee" |
| Need to think | Urgency/scarcity |

Place in FAQ, testimonials, near CTA.

## 5.7 Proof Types

Testimonials (with name/title), Case studies, Data/metrics, Social proof, Certifications

---

# 5. Visual Art

Philosophy-first workflow. Two output modes.

## 5.1 Output Modes

| Mode | Output | When |
|------|--------|------|
| Static | PDF/PNG | Posters, print, design assets |
| Interactive | HTML (p5.js) | Generative art, explorable variations |

## 5.2 Workflow

### Step 1: Philosophy Creation
Name the movement (1-2 words). Articulate philosophy (4-6 paragraphs) covering:
- Static: space, form, color, scale, rhythm, hierarchy
- Interactive: computation, emergence, noise, parametric variation

### Step 2: Conceptual Seed
Identify subtle, niche reference — sophisticated, not literal. Jazz musician quoting another song.

### Step 3: Creation

**Static Mode:**
- Single page, highly visual, design-forward
- Repeating patterns, perfect shapes
- Sparse typography from `canvas-fonts/`
- Nothing overlaps, proper margins
- Output: `.pdf` or `.png` + philosophy `.md`

**Interactive Mode:**
1. Read `templates/viewer.html` first
2. Keep FIXED sections (header, sidebar, seed controls)
3. Replace VARIABLE sections (algorithm, parameters)
4. Seeded randomness: `randomSeed(seed); noiseSeed(seed);`
5. Output: single self-contained HTML

### Step 4: Refinement
Refine, don't add. Make it crisp. Polish into masterpiece.

---

# Quality Gates
**Design:**
- [ ] Mobile layout collapse (`w-full`, `px-4`) for high-variance designs
- [ ] `min-h-[100dvh]` not `h-screen`
- [ ] Empty, loading, error states provided
- [ ] Cards omitted where spacing suffices

**Motion:**
- [ ] Correct tool per selection matrix
- [ ] No GSAP + Framer mixed in same component
- [ ] All `useEffect` have cleanup returns
- [ ] `prefers-reduced-motion` respected
- [ ] Perpetual animations in `React.memo` leaf components
- [ ] Only GPU properties animated
- [ ] Heavy libraries lazy-loaded

**General:**
- [ ] Dependencies verified in `package.json`
- [ ] **No placeholder URLs** — grep the output for `unsplash`, `picsum`, `placeholder`, `placehold`, `via.placeholder`, `lorem.space`, `dummyimage`. If ANY found, STOP and replace with generated assets before delivering.
- [ ] **All media assets exist as local files** in the project's assets directory
- [ ] Asset prompts confirmed with user before generation

---

*React and Next.js are trademarks of Meta Platforms, Inc. and Vercel, Inc., respectively. Vue.js is a trademark of Evan You. Tailwind CSS is a trademark of Tailwind Labs Inc. Svelte and SvelteKit are trademarks of their respective owners. GSAP/GreenSock is a trademark of GreenSock Inc. Three.js, Framer Motion, Lottie, Astro, and all other product names are trademarks of their respective owners.*
