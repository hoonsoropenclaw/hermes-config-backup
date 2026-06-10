# Cross-Service Mapping for Repo Cleanup

When you delete a batch of repos, you usually also need to delete the deploy targets on Vercel / Netlify / Render / Railway / Fly that point at them. The challenge is the mapping is not always 1:1: a Vercel project name may not match its GitHub repo (e.g. `deploy-temp` linking to `Rimuru_and_Raphael`), some repos have no Vercel project, and some Vercel projects have no GitHub repo. This reference gives a working recipe for Vercel (the most common case) and notes the pattern for the others.

## Vercel: Find Every Project Mapping to a GitHub Repo

### 1. Load the Vercel token

The Vercel API token usually lives in `~/.hermes/.env` as `VERCEL_API_TOKEN`. Load it via `set -a; . ~/.hermes/.env; set +a`, or read it out with Python.

For a personal hobby account, the API works without a `teamId` query param. For team accounts, you must pass `?teamId=<team-slug-or-id>` on every call — read it from `GET /v2/teams` and cache.

### 2. List all projects

```bash
curl -s "https://api.vercel.com/v9/projects?limit=100" \
  -H "Authorization: Bearer $VERCEL_API_TOKEN"
```

Response shape (relevant fields per project):

```json
{
  "id": "prj_XXX",
  "name": "deploy-temp",
  "link": {
    "type": "github",
    "org": "hoonsor",
    "repo": "Rimuru_and_Raphael",
    "repoId": 1232104299
  }
}
```

`link` is `null` if the project was created without a Git connection.

### 3. Join with the GitHub delete list on TWO keys

A project maps to a repo if EITHER:

- `project.name == <github repo name>` (the typical case), OR
- `project.link.repo == <github repo name>` AND `project.link.org == <github account>` (catches misnamed projects that still link to the right repo)

```python
import json, urllib.request, os

# GitHub side: build the set of repos to delete
gh_token = os.environ["GH_TOKEN"]
gh_repos_to_delete = {...}  # set of repo names from the user

# Vercel side: list all projects
vercel_token = os.environ["VERCEL_API_TOKEN"]
req = urllib.request.Request("https://api.vercel.com/v9/projects?limit=100",
                             headers={"Authorization": "Bearer " + vercel_token})
projects = json.loads(urllib.request.urlopen(req, timeout=15).read())["projects"]

# Build the join
vercel_match = {}
for p in projects:
    name = p["name"]
    link = p.get("link") or {}
    if name in gh_repos_to_delete:
        vercel_match[name] = {"id": p["id"], "name": name,
                               "via": "name",
                               "link_repo": link.get("repo")}
    elif link.get("repo") in gh_repos_to_delete:
        vercel_match[link["repo"]] = {"id": p["id"], "name": name,
                                      "via": "link.repo",
                                      "link_repo": link.get("repo")}

# Surface the mismatches loudly
for repo, m in vercel_match.items():
    if m["name"] != repo:
        print(f"  ⚠️  {repo} maps to Vercel project named '{m['name']}' (joined via {m['via']})")
```

### 4. Before deleting, capture environment variables

Vercel project env vars are encrypted at rest and **gone forever** when the project is deleted. The right time to back them up is *before* the delete call, not after. Only do this if the user asks (env vars often contain API keys — don't write them anywhere the user didn't agree to).

```python
import json, urllib.request, os
vercel_token = os.environ["VERCEL_API_TOKEN"]

env_backup = {}
for repo, m in vercel_match.items():
    pid = m["id"]
    req = urllib.request.Request(
        f"https://api.vercel.com/v9/projects/{pid}/env",
        headers={"Authorization": "Bearer " + vercel_token}
    )
    envs = json.loads(urllib.request.urlopen(req, timeout=15).read())["envs"]
    env_backup[m["name"]] = {e["key"]: e.get("value", "<encrypted — value not returned by API>")
                              for e in envs}

# Write to a file the user explicitly asked for
backup_path = os.path.expanduser("~/vercel-env-backup-2026-06-05.json")
with open(backup_path, "w") as f:
    json.dump(env_backup, f, indent=2)
print(f"backed up env for {len(env_backup)} projects to {backup_path}")
```

**Heads up about encryption**: Vercel returns env values in plaintext for projects you own, but only if you authenticate with the right scope. If you get `<encrypted>` for every value, your token lacks the `env:read` scope — regenerate the token with full project access.

### 5. Delete the Vercel project

`DELETE /v9/projects/{id-or-name}` — this is immediate and irreversible. The status code 204 means success; 404 means already gone (treat as success); 403 means your token doesn't own the project (likely cross-team mistake).

```python
import urllib.request, urllib.error
for repo, m in vercel_match.items():
    pid = m["id"]
    req = urllib.request.Request(
        f"https://api.vercel.com/v9/projects/{pid}",
        method="DELETE",
        headers={"Authorization": "Bearer " + vercel_token}
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        print(f"  ✓ deleted: {m['name']} (was linked to {repo})")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  · already gone: {m['name']}")
        else:
            print(f"  ✗ FAILED ({e.code}): {m['name']} — {e.reason}")
```

### 6. Then delete the GitHub repos

See `../SKILL.md` Section 11 — but the sequencing matters: **delete Vercel first**, then GitHub. If GitHub goes first and Vercel fails, Vercel will keep polling a dead repo and accumulate errors. Reversed, the worst case is "Vercel gone, GitHub repos in 30-day trash" — recoverable.

## Other Services — Pattern Equivalents

| Service | List projects | Get env / config | Delete | Notes |
|---------|---------------|-------------------|--------|-------|
| Netlify | `GET https://api.netlify.com/api/v1/sites?per_page=100` with `-H "Authorization: Bearer <token>"` | `GET /api/v1/sites/{id}` | `DELETE /api/v1/sites/{id}` | Site name is the join key with the GitHub repo (usually) |
| Render | `GET https://api.render.com/v1/services?limit=100` with `-H "Authorization: Bearer <token>"` | `GET /v1/services/{id}` | `DELETE /v1/services/{id}` | `service.repo` is the join key |
| Railway | `POST https://backboard.railway.com/graphql/v2` with `query { projects { services { id name repo } } }` | same query | `serviceDelete` mutation | GraphQL, paginate via `cursor` |
| Fly | `GET https://api.fly.io/apps` with `Authorization: Bearer <token>` (Fly uses machines internally; this returns the app list) | n/a (env in fly.toml in the repo) | `DELETE /v1/apps/{name}` | No secrets in Fly the same way — they're in the repo as `fly.toml` |

For each, the recipe is the same shape:

1. List the resources on the service side
2. Join on the right key (`name`, `repo`, `link.repo`) against the GitHub delete set
3. Print a dry-run table showing every join
4. Capture env/secrets if the user asked
5. Delete, then switch to GitHub

## Sequencing Reminder

Destructive order: **irreversible service first, recoverable service last**.

- Vercel / Netlify / Render / Railway / Fly deletes: irreversible
- GitHub repo deletes: 30-day recoverable trash

So: Vercel first → GitHub second. Same principle for any other "Git-deploys-to-X" pair (Cloudflare Pages, etc.).
