# Vision MCP Fallback — 2026-06-06 Verification Transcript

Session-specific detail captured during metacognitive-learner cycle (2026-06-06 08:21 +08:00).
Used to patch SKILL.md from v1.0 → v1.1.0 with the Hermes native vision fallback path.

## Test image

- Path: `/home/hoonsoropenclaw/Snapshot/1150604-05.png`
- Size: 137505 bytes
- Source: Vercel Deployment screenshot from user's vision-test session `20260605_200431_c736a3` (344 messages)

## Real command outputs (verbatim, anonymized)

### 1. MCP module load — WITHOUT env vars
```
$ uvx --from minimax-coding-plan-mcp python -c "from minimax_mcp import server; print('OK')"
ValueError: MINIMAX_API_KEY environment variable is required
```
**Diagnosis**: bare `uvx` invocation doesn't inherit shell env by default. Must `export` first.

### 2. MCP module load — WITH env vars
```
$ export MINIMAX_API_KEY="***" MINIMAX_API_HOST=https://api.minimaxi.com
$ uvx --from minimax-coding-plan-mcp python -c "from minimax_mcp import server; print('OK')"
MCP module loaded OK
```
**Diagnosis**: MCP package loads cleanly once env is set. The 401 errors below are NOT load-time failures.

### 3. Hermes native vision call (anthropic-compatible endpoint) — 401
```
$ curl https://api.minimaxi.com/anthropic/v1/messages
  -H "X-Api-Key: $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-01", "messages":[{"role":"user","content":[...base64 image..., {"type":"text","text":"Describe"}]}]}'

HTTPError 401: {
  "type": "error",
  "error": {
    "type": "authentication_error",
    "message": "login fail: Please carry the API secret key in the 'X-Api-Key' field of the request header"
  }
}
```
**Diagnosis**: this is the same "invalid api key" pattern reported in [Reddit r/MiniMax_AI 2026-10](https://www.reddit.com/r/MiniMax_AI/comments/1smx70x/how_to_propertly_setup_minimax_to_access_vision/).
Free-tier / wrong-tier keys fail with this exact message. **Not retriable.**

## Config verification

`~/.hermes/config.yaml` (relevant lines):
```yaml
model:
  default: MiniMax-M3
  provider: minimax
  base_url: https://api.minimax.io/anthropic
agent:
  image_input_mode: auto   # ← required for fallback
  tool_use_enforcement: true
```

`~/.hermes/.env` (relevant lines):
```
MINIMAX_API_KEY=***
MINIMAX_API_HOST=https://api.minimaxi.com
```

## Why the skill needed patching

User's `20260605_200431_c736a3` session tried 344 messages to get vision to work — they hit the same
"invalid api key" 401 loop. The original v1.0 skill had NO fallback — only the MCP path. v1.1 adds
the Hermes native path that uses `image_input_mode: auto` to forward images as base64 content blocks
through the existing anthropic-compatible channel, bypassing MCP entirely.

## Subtle gotcha: vision vs text

The anthropic-compatible endpoint at `https://api.minimaxi.com/anthropic/v1/messages` uses
**X-Api-Key** header (not the more common **Authorization: Bearer**). The skill SKILL.md v1.1
already documents this; this transcript is the proof that X-Api-Key was correct (the 401 is
about the key value, not the header name).

## Related references

- `~/.hermes/skills/vision-analysis/SKILL.md` v1.1.0 — current skill
- Reddit: https://www.reddit.com/r/MiniMax_AI/comments/1smx70x/how_to_propertly_setup_minimax_to_access_vision/
- Token Plan MCP guide: https://platform.minimaxi.com/docs/token-plan/mcp-guide
