# Creative Brand Profiles — DTCG 2025.10 Schema

## 目的

`creative_brand_profiles/` 是 brandkit skill 的品牌事實來源。當用戶要求生成品牌識別圖像時，必須先讀取此目錄的 JSON profile，而非猜測品牌屬性。

## 目錄內容

| 檔案 | 用途 |
|------|------|
| `user_default.json` | 通用預設品牌（無明確指定時 fallback） |
| `developer-tool-brutalist.tokens.json` | 開發工具品牌（精確、建構、控制） |
| `security-compliance.tokens.json` | 安全合規品牌（警戒、保護、信任） |

## DTCG 2025.10 結構約束

每個 `.tokens.json` 檔案必須包含：

```json
{
  "$metadata": {
    "name": "...",          // 品牌名稱
    "brand_category": "...", // 類別 slug
    "version": "1.0.0"
  },
  "color": {
    "$type": "color",
    "$root": { "$value": { "hex": "#...", "colorSpace": "srgb" } },
    "surface": { "$value": { "hex": "#...", "colorSpace": "srgb" } },
    "border": { ... },
    "accent": { "primary": { ... }, "secondary": { ... } },
    "text": { "primary": { ... }, "muted": { ... } },
    "status": { "error": { ... }, "success": { ... }, "warning": { ... } }
  },
  "typography": {
    "$type": "fontFamily",
    "heading": { "$value": "..." },
    "body": { "$value": "..." },
    "label": { "$value": "..." }
  },
  "spacing": {
    "$type": "dimension",
    "unit": { "$value": "4px" },
    "gutter": { "$value": "16px" },
    "section": { "$value": "32px" }
  },
  "logo_symbol": {
    "$description": "...",
    "shape_language": "geometric-minimal | geometric-linear | geometric-authoritative",
    "elements": ["..."],
    "construction": "..."
  },
  "texture": {
    "preferred": ["grain", "halftone", "none"],
    "density": "light | medium | minimal"
  },
  "mood": {
    "keywords": ["...", "..."],
    "reference_tone": "..."
  },
  "generation_prompt_seed": {
    "layout": "2×3 | 3×3 | 2×2 | 1×3 | 4×2",
    "composition": "...",
    "color_application": "...",
    "text_placement": "..."
  }
}
```

## 必備欄位

- `$metadata.name` — 品牌名稱（人類可讀）
- `$metadata.brand_category` — 類別 slug
- `color.$root` — 主背景色（hex + colorSpace）
- `color.accent.primary` — 主品牌色
- `logo_symbol.$description` — 標誌概念描述
- `generation_prompt_seed.layout` — 預設版型

## 品牌類別延伸指南

| category | 標誌元素 | 色彩傾向 | mood 關鍵字 |
|----------|---------|---------|------------|
| developer-tool | frame, crosshair, grid, bolt | yellow/cyan on dark | industrial, precise |
| security | shield, eye, seal, radiating-ring | cyan/green on dark | vigilant, institutional |
| luxury | monogram, seal, emboss, mark | gold on black | tasteful, restrained |
| gaming | dice, gem, card, trophy, signal | vivid on black | exciting, rewarding |
| productivity | path, check, block, calendar | blue on light/dark | focused, clear |
| voice-ai | waveform, mic, orb, speech-path | purple/cyan | fluid, intelligent |

## 新增品牌流程

1. 在 `creative_brand_profiles/` 建立 `*.tokens.json`
2. 驗證 JSON 語法：`jq empty *.tokens.json`
3. 確認包含所有必備欄位
4. 更新本檔案的「目錄內容」表格
