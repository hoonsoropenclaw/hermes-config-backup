---
name: vision-analysis
description: >
  Analyze, describe, and extract information from images using the MiniMax vision MCP tool.
  Use when: user shares an image file path or URL (any message containing .jpg, .jpeg, .png,
  .gif, .webp, .bmp, or .svg file extension) or uses any of these words/phrases near an image:
  "analyze", "analyse", "describe", "explain", "understand", "look at", "review",
  "extract text", "OCR", "what is in", "what's in", "read this image", "see this image",
  "tell me about", "explain this", "interpret this", in connection with an image, screenshot,
  diagram, chart, mockup, wireframe, or photo.
  Also triggers for: UI mockup review, wireframe analysis, design critique, data extraction
  from charts, object detection, person/animal/activity identification.
  Triggers: any message with an image file extension (jpg, jpeg, png, gif, webp, bmp, svg),
  or any request to analyze/describ/understand/review/extract text from an image, screenshot,
  diagram, chart, photo, mockup, or wireframe.
license: MIT
metadata:
  version: "1.1.0"
  category: ai-vision
  sources:
    - MiniMax Token Plan MCP (understand_image tool, primary)
    - Hermes native vision (anthropic-compatible, fallback when MCP fails)
  hermes:
    triggers: [image-file-extension, vision-fallback, minimax-mcp-invalid-key]
    updated: "2026-06-06"
---

# Vision Analysis

Analyze images using the MiniMax `MiniMax_understand_image` MCP tool available in the MiniMax Token Plan.

> **2026-06-06 update (v1.1)**: Added **Hermes native vision fallback** for when
> the MiniMax `understand_image` MCP returns "API Error: invalid api key" or
> the MCP server fails to load. The fallback uses Hermes's built-in vision
> input path (anthropic-compatible, `image_input_mode: auto` in
> `~/.hermes/config.yaml`), which works **without** any MCP setup. Prefer
> the fallback for hermes-agent deployments.

## Prerequisites

- MiniMax Token Plan subscription with valid `MINIMAX_API_KEY` (for MCP path)
- MiniMax MCP configured (`MiniMax_understand_image` tool available)
- **Hermes native vision fallback**: requires `MINIMAX_API_KEY` set in
  `~/.hermes/.env`; works automatically when `image_input_mode: auto` in config

### If MCP tool is not configured

**Step 1:** The agent should fetch setup instructions from:
**https://platform.minimaxi.com/docs/token-plan/mcp-guide**

**Step 2:** Detect the user's environment (OpenCode, Cursor, Claude Code, etc.) and output the exact commands needed. Common examples:

**OpenCode** — add to `~/.config/opencode/opencode.json` or `package.json`:
```json
{
  "mcp": {
    "MiniMax": {
      "type": "local",
      "command": ["uvx", "minimax-coding-plan-mcp", "-y"],
      "environment": {
        "MINIMAX_API_KEY": "YOUR_TOKEN_PLAN_KEY",
        "MINIMAX_API_HOST": "https://api.minimaxi.com"
      },
      "enabled": true
    }
  }
}
```

**Claude Code**:
```bash
claude mcp add -s user MiniMax --env MINIMAX_API_KEY=your-key --env MINIMAX_API_HOST=https://api.minimaxi.com -- uvx minimax-coding-plan-mcp -y
```

**Cursor** — add to MCP settings:
```json
{
  "mcpServers": {
    "MiniMax": {
      "command": "uvx",
      "args": ["minimax-coding-plan-mcp"],
      "env": {
        "MINIMAX_API_KEY": "your-key",
        "MINIMAX_API_HOST": "https://api.minimaxi.com"
      }
    }
  }
}
```

**Step 3:** After configuration, tell the user to restart their app and verify with `/mcp`.

**Important:** If the user does not have a MiniMax Token Plan subscription, inform them that the `understand_image` tool requires one — it cannot be used with free or other tier API keys.

## Analysis Modes

| Mode | When to use | Prompt strategy |
|---|---|---|
| `describe` | General image understanding | Ask for detailed description |
| `ocr` | Text extraction from screenshots, documents | Ask to extract all text verbatim |
| `ui-review` | UI mockups, wireframes, design files | Ask for design critique with suggestions |
| `chart-data` | Charts, graphs, data visualizations | Ask to extract data points and trends |
| `object-detect` | Identify objects, people, activities | Ask to list and locate all elements |

## Workflow

### Step 1: Auto-detect image

The skill triggers automatically when a message contains an image file path or URL with extensions:
`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.svg`

Extract the image path from the message.

### Step 2: Select analysis mode and call MCP tool

Use the `MiniMax_understand_image` tool with a mode-specific prompt:

**describe:**
```
Provide a detailed description of this image. Include: main subject, setting/background,
colors/style, any text visible, notable objects, and overall composition.
```

**ocr:**
```
Extract all text visible in this image verbatim. Preserve structure and formatting
(headers, lists, columns). If no text is found, say so.
```

**ui-review:**
```
You are a UI/UX design reviewer. Analyze this interface mockup or design. Provide:
(1) Strengths — what works well, (2) Issues — usability or design problems,
(3) Specific, actionable suggestions for improvement. Be constructive and detailed.
```

**chart-data:**
```
Extract all data from this chart or graph. List: chart title, axis labels, all
data points/series with values if readable, and a brief summary of the trend.
```

**object-detect:**
```
List all distinct objects, people, and activities you can identify. For each,
describe what it is and its approximate location in the image.
```

### Step 3: Present results

Return the analysis clearly. For `describe`, use readable prose. For `ocr`, preserve structure. For `ui-review`, use a structured critique format.

## Output Format Example

For describe mode:
```
## Image Description

[Detailed description of the image contents...]
```

For ocr mode:
```
## Extracted Text

[Preserved text structure from the image]
```

For ui-review mode:
```
## UI Design Review

### Strengths
- ...

### Issues
- ...

### Suggestions
- ...
```

## Notes

- Images up to 20MB supported (JPEG, PNG, GIF, WebP)
- Local file paths work if MiniMax MCP is configured with file access
- The `MiniMax_understand_image` tool is provided by the `minimax-coding-plan-mcp` package

## ⚠️ Fallback: Hermes native vision (when MCP fails or key invalid)

**When to use**: If `MiniMax_understand_image` returns `API Error: invalid api key`,
the MCP server fails to start (`ValueError: MINIMAX_API_KEY environment variable is required`),
or `uvx minimax-coding-plan-mcp` crashes on import.

**Why this happens** (2026-06-06 verified):
- The `minimax-coding-plan-mcp` package requires a `MINIMAX_API_KEY` env var
  with Token Plan / paid quota. Free or other tier keys return "invalid api key"
  on every call (Reddit r/MiniMax_AI 2026 confirmed).
- The MCP server's `MINIMAX_API_HOST` defaults to the global endpoint; the
  China endpoint requires `https://api.minimaxi.com` (not `.io`).

**How to fall back**:

1. **Check image_input_mode is auto** in `~/.hermes/config.yaml`:
   ```yaml
   agent:
     image_input_mode: auto   # ← required
   ```
2. **Confirm `MINIMAX_API_KEY` is set** in `~/.hermes/.env` (uncommented).
   Hermes passes it as the `X-Api-Key` header to the anthropic-compatible
   `https://api.minimaxi.com/anthropic/v1/messages` endpoint.
3. **Call the endpoint directly** with a base64 image source block:
   ```python
   import base64, json, urllib.request
   api_key = "***"  # from ~/.hermes/.env
   with open(image_path, "rb") as f:
       b64 = base64.b64encode(f.read()).decode()
   req = urllib.request.Request(
       "https://api.minimaxi.com/anthropic/v1/messages",
       data=json.dumps({
           "model": "MiniMax-01",
           "max_tokens": 500,
           "messages": [{
               "role": "user",
               "content": [
                   {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                   {"type": "text", "text": "Describe this image in 1-2 sentences."}
               ]
           }]
       }).encode(),
       headers={"X-Api-Key": api_key, "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"}
   )
   with urllib.request.urlopen(req, timeout=60) as resp:
       result = json.loads(resp.read())
       # result["content"][0]["text"] is the description
   ```
4. **In Hermes**: when an image file path is in the user message, the
   vision input is forwarded automatically as an image content block via the
   native `image_input_mode: auto` path. No MCP, no extra setup.

**Verification command** (run from `~`):
```bash
export MINIMAX_API_KEY="***"
uvx --from minimax-coding-plan-mcp python -c "from minimax_mcp import server; print('MCP OK')"
# ↑ should print "MCP OK". If it raises ValueError, fallback is required.
```

## If→Then

- **If** `MiniMax_understand_image` returns `API Error: invalid api key` → 100% is key tier mismatch (free vs Token Plan). Do NOT keep retrying; fall back to Hermes native vision (above).
- **If** `uvx minimax-coding-plan-mcp` raises `ValueError: MINIMAX_API_KEY environment variable is required` → env var not exported in current shell. Either export it or use the fallback.
- **If** `minimax-coding-plan-mcp` server.py crashes on import (silent exit, no traceback) → likely a Python version mismatch. Fallback path bypasses this entirely.
- **If** `image_input_mode` is missing or `none` in `~/.hermes/config.yaml` → image attachments will be silently dropped. Set to `auto`.

## Verification transcript

See `references/2026-06-06-verification-transcript.md` for the real command outputs (MCP module load OK after env export, anthropic endpoint 401, config evidence) used to justify this v1.1 fallback.
