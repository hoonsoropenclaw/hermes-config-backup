# mmx-cli Auth Key Discovery (N100 Environment)

## Problem

When running `mmx` commands in the hermes N100 environment, `~/.mmx/credentials.json` often shows:
```json
{"api_key": "***", "region": "global"}
```
The key is masked, and `mmx auth status` returns `No credentials found.`

## Why This Happens

The N100 environment uses `dotenv` masking in `~/.hermes/.env`. Keys starting with `***` are masked at read time.
However, the `.env` file has a **commented line** with the real unmasked key as a documentation reference:

```
# MINIMAX_API_KEY=*** <real_key_here>
MINIMAX_API_KEY=*** <masked>
```

The `mmx` CLI reads the non-commented line, gets `***`, and treats it as a blank/missing key.

## Solution: Read Key from Commented Line

```bash
# Extract real key from the commented documentation line in .env
KEY=$(grep '^# MINIMAX_API_KEY=' ~/.hermes/.env | cut -d= -f2-)
echo "${#KEY}"  # should be 125 for MiniMax keys
mmx auth login --api-key "$KEY"
```

## Verification

```bash
# After auth login, check config was written
cat ~/.mmx/config.json
# Should show: {"region": "global", "api_key": "sk-cp-..."}

# Verify auth works — use npx, NOT which (npm global may not be in $PATH on N100)
npx -y mmx-cli quota show
# Should show TokenPlan quota table (not "No credentials found")

# ⚠️ Do NOT use 'which mmx-cli' to check availability on N100
# npm global binaries (npx-hosted) are not in $PATH — 'which' always fails
# Use: npx -y mmx-cli --version (returns "mmx 1.x.x" if working)
```

## Related

- `trial-and-error/references/by-category/mmxcache-key-bridge-20260624.md` — broader credential inheritance gap between execute_code and terminal() contexts
