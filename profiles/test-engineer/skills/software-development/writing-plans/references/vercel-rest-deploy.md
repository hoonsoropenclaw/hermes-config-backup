# Vercel Deployment via REST API

When CLI interactive auth isn't available, use the Vercel REST API directly.

## Deploy Flow

```python
import json, urllib.request, base64, os

TOKEN = 'vcp_...'  # from ~/.hermes/.env
PROJECT_ID = 'prj_...'  # from vercel project URL
BASE = '/path/to/project'

# 1. Gather all files (skip .env.local and secrets)
files = []
SKIP = {'.env.local', '.env', 'node_modules'}
for root, dirs, filenames in os.walk(BASE):
    for fname in filenames:
        if fname in SKIP:
            continue
        rel = os.path.relpath(os.path.join(root, fname), BASE).replace(os.sep, '/')
        with open(os.path.join(root, fname), 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        files.append({'file': rel, 'data': data, 'encoding': 'base64'})

# 2. Deploy
payload = json.dumps({
    'name': 'hermes-portal',
    'project': PROJECT_ID,          # NOT 'projectId'
    'target': 'production',
    'files': files
}).encode()

req = urllib.request.Request(
    'https://api.vercel.com/v13/deployments',
    data=payload,
    headers={
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    },
    method='POST'
)

with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read())
    print(f"Deploy URL: https://{result['url']}")
```

## Critical Discovery

- **`project` field (NOT `projectId`)** — Vercel API rejects `projectId` with 400 error
- **Token format** — `vcp_` prefix, no dots, valid for REST API
- **CLI vs API** — `vercel --token=TOKEN` fails with "must not contain dots" because CLI does extra validation; API directly works

---

## Environment Variables — Non-Interactive Sync

### Tool: vercel-env-push (Recommended First Choice)

Vercel CLI's `vercel env add` requires interactive login, which fails in automated/CI environments. `vercel-env-push` fills this gap:

```bash
npm install -g vercel-env-push
vercel-env-push .env.local production preview development --token VERCEL_TOKEN --yes
```

**Token:** `~/.hermes/.env` → `VERCEL_API_TOKEN` (format: `vcp_...`, NOT `vca_`)

**⚠️ Critical Limitation:** If you push to a single environment, variables from OTHER environments get deleted. **Always push to all at once:**
```bash
vercel-env-push .env.local production preview development --token TOKEN --yes
```

### When npm Tool Is Unavailable — Vercel REST API

```python
# Add env var via API
payload = json.dumps({
    'key': 'AGENT_API_KEY',
    'value': '0770415',
    'target': ['production', 'preview', 'development'],
    'type': 'encrypted'
}).encode()

req = urllib.request.Request(
    f'https://api.vercel.com/v4/projects/{PROJECT_ID}/env',
    data=payload,
    headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'},
    method='POST'
)
```

### Redeploy After Env Change

**Vercel does NOT auto-redeploy when you change environment variables.** New env vars require a fresh deployment to take effect:
```bash
vercel --token TOKEN --yes  # triggers redeploy
```

### If→Then Rules

**If**: Need to sync local `.env.local` to Vercel non-interactively
**Then**: Use `vercel-env-push <file> production preview development --token TOKEN --yes`

**If**: `vercel-env-push` pushes to one environment and others lose vars
**Then**: Push to all environments at once (production + preview + development together)

**If**: Vercel env var values match but API still returns 401
**Then**: Redeploy (new env vars require fresh deployment to take effect)

**If**: Verify Vercel API token works
**Then**: `curl -H "Authorization: Bearer *** https://api.vercel.com/v2/user"`

### References
- https://github.com/HiDeoo/vercel-env-push
- https://vercel.com/docs/cli/env

---

**Required vars for Hermes Portal:**
```
SUPABASE_URL=https://nhjyucwvqdkihklbaleo.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
AGENT_API_KEY=hms_he...
```

## Deployment Verification

```bash
# Test homepage (may redirect to Vercel login for unverified domains)
curl -I https://your-project.vercel.app/

# Test API
curl https://your-project.vercel.app/api/works
# Expected: JSON response (may need auth header depending on endpoint)
```

## Vercel Authentication Gotcha

Free-tier Vercel projects require login to view — if deployment succeeds but browser shows vercel.com/login, that's expected behavior. User needs to verify via the Dashboard or use a custom domain.

## References

- Vercel Deploy API: https://vercel.com/docs/rest-api#endpoints/deployments/create-a-deployment
- Project field name in API: `"project"` not `"projectId"` (discovered via error message)