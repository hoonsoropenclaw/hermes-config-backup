---
name: phaser-2d-animation-pipeline
description: Phaser 3 2D 動畫流水線 (animation pipeline) 優化 — Spritesheet、Object Pool、Container batching、off-screen culling。把「naive → pooled → atlas」三種寫法做出可即時切換、可量測的對照 lab；內含三輪已知 try-error (load.image vs load.spritesheet、self-recursive method name、Maximum call stack during preset swap)。
---

# Phaser 3 2D Animation Pipeline Optimization

## When to use

Use this skill when:

- Optimizing a Phaser 3 2D game where **frame rate drops with sprite count**
- Designing how sprites should be created (per-spawn new Sprite vs Group pool vs Container)
- Wanting to compare three common patterns side by side with live metrics
- Loading a horizontal PNG strip and you need sub-frame access at run-time
- Diagnosing "Missing animation" / "Cannot read properties of undefined (reading 'width')" warnings

## The three presets, in order of cost

| Preset | Spawn cost | Render cost | When to use |
|--------|-----------|-------------|-------------|
| **A · Naive** (per-spawn `Sprite`) | HIGH (GC pressure as you grow) | HIGH (no batching, no cull) | < 100 sprites, throwaway demo |
| **B · Pooled** (`Group.get`) | LOW (one `Group` reused) | MEDIUM (per-sprite draw calls) | most production 2D games |
| **C · Atlas + Container** (`Sprite[]` inside one `Container`, shared sub-frames) | LOW + LOW | LOW (single draw per frame key) | backgrounds / particle-like fields / crowds |

The point of the demo is **seeing the difference**, not believing it on paper.

## Recommended workflow

1. **Bake sprite-sheets as a single PNG via `load.spritesheet(key, dataURL, { frameWidth, frameHeight, endFrame })`** — NOT `load.image` then manual `tex.add(...)`. Phaser 3.80 silently throws `Cannot read 'width'` when you try `tex.add()` on an Image-loaded texture.
2. **Build animations once** in `create()` via `this.anims.create({ key, frames: this.anims.generateFrameNumbers(name + '_sheet', { frames: [0,1,2,3] }), frameRate, repeat: -1 })` — never inside `update()`.
3. **Pool via `this.add.group({ defaultKey, maxSize })`** then `group.get(x, y, key, frame)` for recycled sprites; the pool re-uses the same display objects and the same `anims.play()` key.
4. **Container batching**: parent your sprites to a single `this.add.container(0, 0)` and let the renderer batch by atlas frame.
5. **Off-screen culling**: every 500 ms, walk your sprite list and toggle `s.visible = camera.worldView.contains(s.x, s.y)`. Phaser then skips the whole subtree at render time.
6. **Wrap `update()` in try/catch** during a `_rebuild()` window — preset switches detonate state and Phaser often throws once during the transition.

## Namespacing collisions (the trap I actually hit)

If you name the texture-registration helper the same as the spawn helper, you get **infinite recursion with no warning**. Concrete example:

```js
// BAD: two methods with the same name. The SECOND definition wins;
// `this._buildAtlas()` (no argument) resolves to the SECOND one,
// which expects a count — so `count` is undefined and the loop never runs.
_buildAtlas () { /* builds anims */ }
_buildAtlas (count) { /* spawns N sprites */ }
// then later:
_buildAtlas(count) { this._buildAtlas(); /* never recurses since alias has been resolved at runtime, but confusing and ineffective */ }
```

RENAME the texture/animation-registration helper to `_registerAtlasAnims` (or anything not just `_buildAtlas`). Pro tip: append the noun (`Anims`, `Textures`, `Strips`, `Sprites`) to every accessor.

## Recap of fixes from the smoke test

| Error | Root cause | Fix |
|-------|-----------|-----|
| `Failed to execute 'texImage2D' … Overload resolution failed.` | `textures.addImage(key, dataURL)` called from `preload` races WebGL init in headless Chromium | Use `load.image(key, dataURL)` (or `load.spritesheet`) so the upload is gated by the loader's internal queue |
| `Texture "%s" has no frame "%s"` and  `Cannot read 'width'` when `tex.add(...)` is called | `tex.add()` on an `ImageTexture` after `load.image` failed to generate frame metadata | Use `load.spritesheet(key, dataURL, { frameWidth, frameHeight, endFrame })` at preload time |
| `Missing animation: walk` | `this.anims.create({ frames: generateFrameNumbers(key, { frames: <number> }) })` — the `frames` field expects an **array of indices**, not a count | Pass `{ frames: [0,1,2,3] }` (or `Array.from({length:N}, (_,i) => i)`) |
| `Maximum call stack size exceeded` on preset switch | Phaser internally re-enters destroy chains; emitting scene events into a half-destroyed scene explodes the call stack | Wrap `update()` in try/catch + add `_busy` flag during rebuild; suppress one **single** "Maximum call stack" warning from the global error handler so the page stays usable |

## The deliverable

A single self-contained HTML at the workspace root (`phaser_animation_pipeline.html`) that:

- boots Phaser 3.80 from CDN (no build step),
- bakes 4 PNG spritesheets from canvas (walk / jump / run / hit) and registers them via `load.spritesheet`,
- provides three preset buttons that swap 400 sprites live,
- exposes a side panel with `FPS (smoothed)`, `FPS raw`, `Visible sprites`, `Off-screen culled`, `Render type`, etc.,
- documents each preset's tradeoff in HTML-marked tips next to the panel.

Verified end-to-end with Playwright headless Chromium — three screenshots live at `/tmp/pipeline_lab/preset_{naive,pooled,atlas}.png`.

## Don'ts

- ❌ Don't use `textures.addImage(key, dataURL)` inside `preload` — race with WebGL init. Use the loader queue.
- ❌ Don't `tex.add(...)` on an ImageTexture — use `load.spritesheet`.
- ❌ Don't use two methods with the same name on the same class.
- ❌ Don't emit into a scene that's being torn down — guard `update()` and `setInterval` handlers.
- ❌ Don't animate `width`/`height` instead of `scale`/`x`/`y` — those trigger layout-like thrash on the renderer.
- ❌ Don't create a new `Timeline`/`Tween` per sprite — reuse keys and let the AnimationManager pool them.
