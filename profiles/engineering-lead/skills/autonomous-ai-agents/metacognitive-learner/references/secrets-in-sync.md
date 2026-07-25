# Secrets in Sync: Token Masking for Public Git Repos

## Problem Statement

When `sync_md_files.py` reads MD files (MEMORY.md, etc.) and writes them to `assets/md-files.json` for the hermes-status-site GitHub repo, any **real API tokens embedded in those MD files** get copied into the JSON. When the cron job commits and pushes, GitHub Secret Scanning detects the `vcp_...` token pattern and blocks the push with:

```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Push cannot contain secrets
remote:   —— Vercel Personal Access Token ——
remote:   locations:
remote:     - commit: a4c146122893ec25fa22bb20ecb1096e7db690b2
remote:       path: assets/md-files.json:40
```

## Root Cause

- `MEMORY.md` records real tokens like `vcp_***REDACTED***` for documentation purposes
- `sync_md_files.py` line 59-64 reads `"content": content` directly from each MD file and writes to JSON
- The JSON is committed and pushed to a **public** GitHub repo, triggering push protection

## Solution: Token Masking in Sync Scripts

Add a regex-based masking step **before** writing content to JSON:

```python
import re

# Common token patterns to mask
TOKEN_PATTERNS = [
    (r'vcp_[a-zA-Z0-9]{20,}', '[Vercel Token]'),
    (r'ghp_[a-zA-Z0-9]{36}', '[GitHub Token]'),
    (r'sk-[a-zA-Z0-9]{48}', '[OpenAI Key]'),
    (r'gho_[a-zA-Z0-9]{36}', '[GitHub OAuth]'),
    (r'glpat-[a-zA-Z0-9]{20,}', '[GitLab Token]'),
]

def mask_secrets(content: str) -> str:
    """Replace all known secret patterns with [REDACTED] markers."""
    for pattern, replacement in TOKEN_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content
```

In `sync_md_files.py`, change line 59-64 from:
```python
files_data.append({
    "name": fname,
    "content": content,  # ← raw content with real tokens
    ...
})
```

To:
```python
files_data.append({
    "name": fname,
    "content": mask_secrets(content),  # ← tokens replaced with [REDACTED]
    ...
})
```

## Why Not Use Environment Variables in Deploy?

The `deploy()` function at line 77 already uses `os.environ.get("VERCEL_TOKEN", ...)` with a hardcoded fallback for the **runtime token used to call Vercel CLI** — that's fine because:
1. It's not committed to the repo (used only at runtime)
2. Environment variables are the correct place for runtime credentials

The problem is the **documentation tokens** inside MD files that get synced as data, not credentials.

## GitHub Bypass Limitation

The official GitHub bypass flow (per docs) requires:
1. Same user who pushed (you must be authenticated as the committer)
2. Visit the `unblock-secret` URL within 3 hours
3. Select a reason and click "Allow me to push this secret"

**For automated cron jobs**: There is no way to complete this bypass interactively. The only real fix is **prevention** — mask tokens before they enter the repo.

## If→Then Rules

- **If** a push to a public GitHub repo is blocked with "Push cannot contain secrets" and the secret is a `vcp_...` or similar known token format
- **Then** the issue is not the cron job script — it's the sync script copying MD file content directly into committed JSON files
- **Then** add token masking (the `mask_secrets()` function above) to the sync script before writing to JSON

- **If** you need to document a real API token in memory
- **Then** store it in a **private** location or TOOLS.md (which is not synced to public repos), not in MEMORY.md which gets synchronized