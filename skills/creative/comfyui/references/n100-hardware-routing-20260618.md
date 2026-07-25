# N100 Hardware Image Generation Routing (2026-06-18)

## Hardware Profile: N100 Mini PC

```
OS: Linux x86_64
CPU: Intel Alder Lake-N (UHD Graphics, integrated)
RAM: 31.1 GB
GPU: None (Intel UHD, no dedicated GPU)
Disk: 126 GB free
```

## hardware_check.py Result

```json
{
  "verdict": "cloud",
  "recommended_install_path": "comfy-cloud",
  "notes": [
    "No supported accelerator found (NVIDIA CUDA / AMD ROCm / Apple Silicon / Intel Arc).",
    "CPU-only ComfyUI works but is unusably slow for modern models — use Comfy Cloud."
  ]
}
```

**Conclusion**: Local ComfyUI CPU-only mode is not viable for modern Stable Diffusion / Flux models.

## Available Image Generation Paths on N100

| Tool | API Key Status | Feasibility |
|------|---------------|-------------|
| MiniMax image-01 | `MINIMAX_API_KEY` ✅ exists in `~/.hermes/.env` | ✅ Use immediately |
| ComfyUI Cloud | `COMFY_CLOUD_API_KEY` ❌ not set | ⚠️ Needs setup (paid) |
| Local ComfyUI (CPU) | N/A | ❌ Too slow for modern models |

## MiniMax Image-01 Details

- **Endpoint**: `POST https://api.minimax.io/v1/image_generation`
- **Auth**: `Authorization: Bearer $MINIMAX_API_KEY`
- **Known limitation**: Body-shape adjectives are de-escalated
  - "丰腴" → "athletic"
  - "curvy" → "standard"
  - Workaround: use situational/activity cues instead of direct body descriptors
- **mmx CLI**: not installed (`which mmx` → not found)
  - Install: `pipx install mmx` or `uvx mmx-mmmlib-mmnablas`
  - Or call REST API directly (see `references/rest-api.md`)

## Content Filter Notes

Both MiniMax image-01 and ComfyUI Cloud have content filters. Key difference:
- **MiniMax image-01**: centralized content filter on all generations; no way to override
- **ComfyUI Cloud**: can upload custom models/LoRAs (including NSFW-tuned ones); more flexibility

## Recommendations for N100

1. **Primary**: Use MiniMax image-01 for general creative work (already has API key)
2. **When MiniMax content filter blocks**: Set up ComfyUI Cloud (requires `COMFY_CLOUD_API_KEY`)
3. **Never**: Attempt local ComfyUI CPU generation for SDXL/Flux — it will be unusably slow

## Related Skills

- `comfyui`: Full ComfyUI skill (local + cloud)
- `hr-document-workflow`: Uses MiniMax image-01 for document illustration
