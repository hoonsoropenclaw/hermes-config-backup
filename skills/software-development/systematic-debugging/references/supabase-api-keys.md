# Supabase API Key Reference Card

## Three Types of Supabase Keys

| Key Type | Format | Used For | Doesn't Work For |
|----------|--------|----------|-----------------|
| **Service Role** | `sb_secret_...` | REST API (`{ref}.supabase.co/rest/v1/`) — read/write tables | Management API (`api.supabase.com`) |
| **Anon/Publishable** | `sb_publishable_...` | REST API (public data only) | Management API, authenticated operations |
| **Personal Access Token (PAT)** | `sbp_...` | Management API (`api.supabase.com/v1/`) | REST API (not recognized) |

## JWT Structure

Supabase JWT tokens (`eyJ...`) decode to:
```json
{
  "iss": "supabase",
  "ref": "nhjyucwvqdkihklbaleo",   // project ref
  "role": "service_role",           // or "anon", "authenticated"
  "iat": 1778154401,
  "exp": 2093730401
}
```

- `role: service_role` → REST API full write access
- `role: anon` → REST API public read only

## Debugging Checklist

**When getting 403 on management API:**
1. ✅ Verify the key format — PAT (`sbp_`) goes to `api.supabase.com`, NOT service role (`sb_secret_`)
2. ✅ Verify the account — PAT permissions are account-level, not project-level
3. ❌ Do NOT use `sb_secret_` for management API — it only works for REST
4. ❌ Do NOT use `sb_publishable_` for management API — wrong key type

**Quick test commands:**
```bash
# Test REST API (works with sb_secret_ or JWT)
curl "https://{ref}.supabase.co/rest/v1/" \
  -H "apikey: {sb_secret_or_jwt}" \
  -H "Authorization: Bearer {sb_secret_or_jwt}"
# Expected: swagger JSON

# Test management API (needs PAT only)
curl -X POST "https://api.supabase.com/v1/projects/{ref}/database/query" \
  -H "Authorization: Bearer {sbp_...}" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1"}'
# Expected: {"response": null} not 403
```

## Fallback When Management API Blocked

If PAT gets 403, the only path is **manual SQL in Dashboard**:

```
Supabase Dashboard → Project → SQL Editor → Run SQL
```

Service role key + REST API is sufficient for all data operations once tables exist.