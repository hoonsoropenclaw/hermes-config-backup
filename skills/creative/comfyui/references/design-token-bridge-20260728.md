# Design Token → ComfyUI Bridge (2026-07-28)

## The Problem

Design tokens (`tokens.json`, W3C DTCG format) describe brand visual language — colors, spacing, typography, radii, shadows. But they are static JSON; they do not generate ComfyUI prompts or workflow parameters. The bridge between "we use `--brand-coral: #e76f51`" and "generate an image with that coral accent" requires a **semantic translation layer**.

## Token Format (W3C DTCG 2025.10)

```json
{
  "color": {
    "brand/coral": { "$value": "#e76f51", "$type": "color" },
    "neutral/paper": { "$value": "#f5f2eb", "$type": "color" }
  },
  "typography": {
    "display/newsreader": { "$value": "Newsreader, serif", "$type": "fontFamily" }
  }
}
```

Style Dictionary v5 transforms DTCG JSON → CSS custom properties, SCSS, iOS, Android. But this is only code generation — it does not produce prompts.

## The Semantic Translation Layer

The actual bridge is a prompt constructor that reads token metadata and produces style descriptions:

```
tokens.json                              ComfyUI prompt injection
┌─────────────────────┐                 ┌──────────────────────────────────────┐
│ color/brand/coral   │──→ semantic ──→ │ "warm coral accent (#e76f51),        │
│ #e76f51             │   description    │   editorial serif typography,        │
│ $type: color        │                 │   generous negative space"            │
└─────────────────────┘                 └──────────────────────────────────────┘
```

### Prompt Constructor Pattern

```python
import json

def tokens_to_prompt_descriptors(tokens_json: dict) -> list[str]:
    """Convert W3C DTCG token dict to semantic prompt fragments."""
    fragments = []
    for key, val in tokens_json.items():
        if isinstance(val, dict) and "$value" in val:
            v = val["$value"]
            t = val.get("$type", "")
            if t == "color":
                fragments.append(f"color {v}")  # naive: just hex
            elif t == "fontFamily":
                fragments.append(f"typography: {v}")
    return fragments

def build_style_prompt(tokens_path: str, subject: str) -> str:
    tokens = json.load(open(tokens_path))
    desc = tokens_to_prompt_descriptors(tokens)
    return f"{subject}, {' '.join(desc)}"
```

A production constructor uses `$extensions` or a parallel `semantic-descriptions.json` to store visual adjectives ("warm coral accent" instead of raw hex).

## ComfyUI Parameter Injection

Once you have a prompt string, inject it into the workflow API JSON:

```python
import json, copy

def inject_prompt(workflow_path: str, prompt_text: str, output_path: str):
    with open(workflow_path) as f:
        wf = copy.deepcopy(json.load(f))

    for node_id, node in wf.items():
        if node.get("class_type") == "CLIPTextEncode":
            if "text" in node["inputs"]:
                node["inputs"]["text"] = prompt_text
            elif "text_g" in node["inputs"] and "text_l" in node["inputs"]:
                # SDXL: split across both text encoders
                node["inputs"]["text_g"] = prompt_text
                node["inputs"]["text_l"] = prompt_text.replace(",", ". ")

    with open(output_path, "w") as f:
        json.dump(wf, f)
```

See `workflow-format.md` §Parameter Injection for the full pattern.

## Style Reference vs. Token Semantic Layer

| Approach | Mechanism | Tool |
|----------|-----------|------|
| **Token semantic layer** | Token JSON → prompt text → ComfyUI | Style Dictionary + custom prompt constructor |
| **Style reference** | Style image → IPAdapter / `--first-frame` | ComfyUI IPAdapter nodes or mmx `--first-frame` |

Use both together: token layer provides the *description*, reference image provides the *visual anchor*.

## W3C DTCG Spec

- **Format**: https://www.designtokens.org/tr/drafts/format (2025.10 draft)
- **Style Dictionary v5**: https://styledictionary.com — transforms DTCG JSON → CSS/SCSS/iOS/Android
- **Key syntax**: `$value` (token value), `$type` (semantic type), `$extensions` (custom metadata)

## If→Then

```
IF user has a brand design system (tokens.json) and wants brand-consistent AI image generation
THEN → tokens.json describes WHAT the brand looks like, not HOW to prompt for it
     → a semantic translation layer is required: token metadata → visual adjective prompt fragment
     → Style Dictionary transforms token FORMAT, not prompt CONTENT
     → use ComfyUI workflow_api.json parameter injection for the actual prompt
     → complement with IPAdapter style reference (ComfyUI) or --first-frame (mmx)

IF user asks for "brand-consistent images" without a reference image
THEN → ask if they have tokens.json or a style guide; if yes, build the bridge
     → if no tokens, use style-consistency-20260721.md reference anchoring pattern
```
