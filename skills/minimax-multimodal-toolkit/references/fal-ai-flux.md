# FAL.ai FLUX — Alternative Image Provider (2026-06-17)

FAL.ai FLUX.1-dev is the recommended alternative to MiniMax `image-01` when the user's prompt contains body-description or composition constraints that image-01 cannot handle.

## Why FAL.ai over image-01

| Constraint | image-01 | FLUX.1-dev |
|---|---|---|
| "curvy / 豐滿 / voluptuous / hourglass" | De-escalates to athletic lean | ✅ Renders as requested |
| "bird's-eye / overhead / looking down" + portrait | ❌ Cannot bind | ✅ Works |
| NSFW / body-explicit content | Heavy filter | Minimal filter |
| Cost | ~$0.001/image | ~$0.025/image |
| Setup | `mmx-cli` (installed) | Requires `FAL_KEY` |

## API Quick Reference

```python
import fal_client

# Synchronous (waits for generation)
result = fal_client.subscribe(
    "fal-ai/flux/dev",
    arguments={"prompt": "A curvy hourglass figure gymnast on balance beam", "image_size": "portrait"}
)
image_url = result.images[0].url

# Async with webhook
fal_client.submit(
    "fal-ai/flux/dev",
    arguments={"prompt": "..."},
    webhook_url="https://your-webhook.com/fal-callback"
)
```

## LiteLLM interface (if FAL_AI_API_KEY is in env)

```bash
export FAL_KEY="your-key"
litellm --model fal_ai/fal-ai/flux-pro/v1.1 "A curvy gymnast"
```

## hermes integration path

1. Check `~/.hermes/.env` for `FAL_KEY`
2. If present → use `fal_client` Python SDK or LiteLLM
3. If absent → tell user "image-01 doesn't support this; to use FLUX, add FAL_KEY to ~/.hermes/.env"

## Models available on FAL.ai (2026 pricing)

- `fal-ai/flux/dev` — FLUX.1 dev, 12B params, ~$0.025/image
- `fal-ai/flux-pro/v1.1` — FLUX.1 pro, balanced speed/quality, ~$0.025-0.04/image
- `fal-ai/flux-pro/v1.1-ultra` — Ultra quality
- `fal-ai/recraft/v3` — Multiple style options
- `fal-ai/ideogram/v3` — Lettering-first creative model, ~$0.06/image

Source: fal.ai pricing page (2026)
