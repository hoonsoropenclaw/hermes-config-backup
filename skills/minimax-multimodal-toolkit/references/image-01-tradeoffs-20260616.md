# image-01 Model Trade-offs: 2026-06-16 Session Log

## Session: 20260616_125207 (AI 圖片生成與風格限制)

### Prompt 1
```
young beautiful woman, portrait of a person, minimalist line art, clean lines, flat colors, high angle shot, bird's-eye view, studio lighting, professional lighting setup, softbox
```

**Result**: Model produced realistic photography instead of line art. Style + portrait + angle combination exceeded model's simultaneous constraint capacity.

**Output**: 2 of 4 images generated (partial rejection = content filter triggered)

### Prompt 2 (Comic book style variant)
```
young beautiful woman, comic book style, ink outlines, halftone patterns, high angle shot, bird's-eye view, looking down, studio lighting, professional lighting setup, softbox
```

**Result**: All 4 images generated. File sizes 350-470KB (vs ~200KB for first attempt) — larger size indicates more detail/halftone retained. However:
- `v2_001`: off-shoulder dress + elevated angle → boudoir aesthetic
- `v2_002`: dress slipped to collarbone + boudoir feel
- `v2_003`: best composition but outfit detail lost
- `v2_004`: similar to v2_003

**Lesson**: Even when style "wins" (comic book style held), clothing/angle combinations still trigger aesthetic filter.

### Key Observations

1. **Style keywords + portrait + angle = mutual interference**. The more constraints, the more degradation.
2. **Body-shape adjectives (豐滿) trigger de-escalation**: Model reduces to "safe athletic" baseline.
3. **Content filter doesn't reject outright** — it silently drops constraints. User may not realize what's missing.
4. **File size is an informal filter indicator**: 200KB vs 350-470KB difference reflects detail retention level.

### Recommendations for Future Sessions

1. Always ask user to rank priorities: Style vs Angle vs Realism
2. Test with `n=1` first before scaling to `n=4`
3. Warn user before generating about known trade-offs
4. When filter triggers, explain which keyword was likely the cause
