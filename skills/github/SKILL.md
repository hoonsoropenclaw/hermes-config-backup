---
name: github
description: "Interact with GitHub using the `gh` CLI. Use `gh issue`, `gh pr`, `gh run`, and `gh api` for issues, PRs, CI runs, and advanced queries."
---

# GitHub Skill

Use the `gh` CLI to interact with GitHub. Always specify `--repo owner/repo` when not in a git directory, or use URLs directly.

## Pull Requests

Check CI status on a PR:
```bash
gh pr checks 55 --repo owner/repo
```

List recent workflow runs:
```bash
gh run list --repo owner/repo --limit 10
```

View a run and see which steps failed:
```bash
gh run view <run-id> --repo owner/repo
```

View logs for failed steps only:
```bash
gh run view <run-id> --repo owner/repo --log-failed
```

## API for Advanced Queries

The `gh api` command is useful for accessing data not available through other subcommands.

Get PR with specific fields:
```bash
gh api repos/owner/repo/pulls/55 --jq '.title, .state, .user.login'
```

## JSON Output

Most commands support `--json` for structured output.  You can use `--jq` to filter:

```bash
gh issue list --repo owner/repo --json number,title --jq '.[] | "\(.number): \(.title)"'
```

## Multi-Account / Switching `gh` Identities

A single `github.com` host can hold multiple accounts in `~/.config/gh/hosts.yml`, but only one is **active** at a time. Use this when the user has more than one GitHub identity (e.g. a personal account + an Organization/bot account, or one per agent like `hoonsoropenclaw` + `hoonsor`).

### Discover what's installed

```bash
gh auth status          # shows ALL accounts on github.com, marks the active one
gh auth status -h github.com   # same, explicit hostname
# Note: `gh auth list` does NOT exist in older gh versions. Don't guess it.
```

### Switch the active account (do this BEFORE running repo-scoped commands)

```bash
gh auth switch --user <login>
```

`gh auth switch --user` is the canonical way to flip the active account. After every cross-account task, switch back to the user's default — don't leave the session on a non-default identity.

### Adding a second account

```bash
# Newer gh: `gh auth login --with-token` reads the token from stdin.
# It looks up the user from the token and stores it under that login.
# Older gh (pre-2.40-ish) does NOT support `--user` on `auth login` — let gh
# derive the user from the token instead. Passing `--user` to `auth login`
# fails with "unknown flag: --user".
echo "ghp_NEW_TOKEN" | gh auth login --hostname github.com --with-token
```

`gh auth login --with-token` may swap the active account to the newly-added one as a side-effect. If you don't want that, immediately run `gh auth switch --user <default>` after adding.

### Verify a token is valid BEFORE assuming login succeeded

`gh auth login` can return exit 0 even if the token is later rejected by the API. Always probe:

```bash
GH_TOKEN=<token> gh api user --hostname github.com
# If you see "Bad credentials" / HTTP 401, the token is dead — don't trust it.
```

`gh auth status` does NOT call `/user`; it just decodes what is in `hosts.yml`. A 401 in `gh api` is the only real validity check.

### Dual-platform deletion protocol (GitHub + Vercel + etc.)

When a "clean up" task spans two systems (e.g. "delete these repos AND their deployed Vercel projects"), do not batch into one script. The blast radii differ and the rollback paths differ:

| | GitHub repo | Vercel project |
|---|---|---|
| Reversible? | 30 days via `Settings → Deleted repositories` | **No** — instant and permanent |
| API | `DELETE /repos/{owner}/{repo}` | `DELETE /v9/projects/{id}` |
| Side effects | Webhooks/deploy keys stop firing | Custom domains freed, env vars lost |
| Pre-flight | None | Capture env vars first |

**The protocol:**

1. **Map first.** For every name the user gave you, look up: GitHub repo (does it exist? private/public? has forks?), Vercel project (does it exist? what's the project_id? is the env non-empty?). Build a cross-reference table.
2. **Back up anything irrecoverable.** Vercel env vars (encrypted blobs) cannot be re-derived. `GET /v9/projects/{id}/env` and write to `~/vercel-env-backup-<timestamp>.json` (mode 0600). GitHub repo contents can be cloned first if there's any doubt: `gh repo clone owner/name /tmp/backup-name`.
3. **Print the dry-run table.** Show the user exactly: count, names, target systems, what survives, what doesn't. Get explicit confirmation ("go" / "ok" / "執行") before any DELETE.
4. **Do the irreversible side first.** Vercel goes before GitHub — if you crash mid-batch, the worst case is "some GitHub repos still exist" (reversible) rather than "some Vercel projects gone" (not).
5. **Verify both sides after.** `gh repo list` and `vercel projects ls` (or `GET /v9/projects`) — both should show the expected post-state.
6. **Restore gh to the default account.** `gh auth switch --user <default>` at the end. The user should not be left on an alt account.
7. **Keep the temp work files until the user confirms.** Don't pre-emptively delete `/tmp/*-results.json`. The user may want to grep them later, and the data is already on disk.

Don't skip step 1. Skipping it is how you discover the day after that "Rimuru_and_Raphael" was linked to a Vercel project called `deploy-temp`, not `rimuru-and-raphael`, and the delete script silently no-op'd.

### Token storage pattern for alt accounts

For long-lived alt accounts (the user said "I'll come back to this"), keep the token in an isolated file with restricted permissions, NOT in `~/.bashrc` / `~/.zshrc` / shell history:

```bash
mkdir -p ~/.config/hermes/alt_gh_tokens
chmod 700 ~/.config/hermes/alt_gh_tokens
: > ~/.config/hermes/alt_gh_tokens/<account-label>
chmod 600 ~/.config/hermes/alt_gh_tokens/<account-label>
# user pastes the token into the file via editor
```

Read it in scripts as:
```bash
export GH_TOKEN=$(cat ~/.config/hermes/alt_gh_tokens/<account-label>)
```

Cost: 42 bytes. Benefit: future sessions can switch accounts in one command; nothing leaks to shell history; nothing visible in `env | grep TOKEN` (because the env var is only exported in the script that needs it).

### NEVER paste a token into chat

The user gave me a GitHub PAT directly in the conversation once. I should have refused and asked for it via a file path. The right workflow when the user says "here is a token" or pastes a credential:

1. STOP. Treat the token as compromised the moment it lands in any LLM session log.
2. Recommend the user revoke it and reissue with minimal scopes + short expiry.
3. Ask for the token to be written to an isolated file instead, e.g.:
   ```bash
   mkdir -p ~/.config/hermes/alt_gh_tokens
   chmod 700 ~/.config/hermes/alt_gh_tokens
   : > ~/.config/hermes/alt_gh_tokens/<account-label>
   chmod 600 ~/.config/hermes/alt_gh_tokens/<account-label>
   # user pastes the token into that file with their editor
   ```
4. Then read it with `read_file` or pipe it into `gh auth login --with-token`. Do NOT echo it back, do NOT pass it via `env=` in `subprocess.run` (that string ends up in process listings / debug dumps).
5. After the session, suggest deleting the file if it's a one-shot credential.

### `gh auth login --with-token` may reject valid tokens

If the token lacks `read:org` scope, `gh auth login` exits 1 with:

```
error validating token: missing required scope 'read:org'
```

…and the new account is **not** added to `hosts.yml`. The token is fine for direct API calls (it works for `user`, `user/repos`, `DELETE /repos/...`); gh is just being strict about its own metadata. Two escapes:

**Option A — direct API, no `gh` involvement (cleanest for one-shot cleanup jobs):**
```bash
export GH_TOKEN=...
gh api user            # verify
gh api user/repos --paginate   # list
gh api -X DELETE repos/owner/name  # delete
```
`gh api` honors `GH_TOKEN` (and `GITHUB_TOKEN`) from the environment without touching `~/.config/gh/hosts.yml`. Use this when you only need a second account for a bounded task and don't want to risk mutating the main account's gh state.

**Option B — manually append the account to `hosts.yml`:**
```yaml
github.com:
    users:
        mainuser:
            oauth_token: ghp_MAIN
        altuser:
            oauth_token: ghp_ALT
    git_protocol: ssh
    user: mainuser
    oauth_token: ghp_MAIN
```
Back up the file first (`cp ~/.config/gh/hosts.yml{,.bak}`). `gh auth status` may temporarily show the alt account as "active" or complain about scopes until you `gh auth switch --user mainuser`. This is cosmetic; `gh api` and `gh repo` commands work fine.

**Rule of thumb:** If the user says "I just need to do X with this alt account" and X is a one-shot API task, go Option A. If they want gh CLI ergonomics (`gh repo list`, `gh pr`, etc.) across many commands, Option B.

### `gh auth status` is NOT a token-validity check

`gh auth status` decodes whatever is in `hosts.yml` and reports it. It does **not** call the GitHub API. A token that was revoked upstream still shows as "✓ Logged in" in `gh auth status`.

The only real check:
```bash
GH_TOKEN=<token> gh api user --hostname github.com
# If HTTP 401 Bad credentials → token is dead, regardless of what hosts.yml says
```

A token can also be valid for `user` but lack scopes for some operations. Common gotcha: classic PAT with `repo` but no `delete_repo` → can list repos, can `DELETE` is rejected. Verify with `gh api user` (any successful call) and read the `scopes` line in `gh auth status`.

### `gh repo list --json` field names are GitHub-API-native, not friendly

The `--json` output uses the **raw GitHub API field names**, which differ from `gh repo view`'s display columns. The common ones:

| Display (`gh repo view`) | `--json` field | Notes |
|---|---|---|
| visibility (PUBLIC/PRIVATE) | `private` (bool) | NOT `isPrivate`, NOT `visibility` |
| fork | `fork` (bool) | same |
| archived | `archived` (bool) | same |
| stars | `stargazers_count` | number |
| last push | `pushed_at` | ISO 8601 string |
| created | `created_at` | ISO 8601 string |
| description | `description` | nullable string |

Filter combinations useful for audit-style tasks:
```bash
# All repos the user owns (incl. private), no forks
gh repo list <user> --limit 200 --json name,private,description,pushedAt \
  --no-archived --source

# Only private repos
gh repo list <user> --json name,private --jq '.[] | select(.private)'
```

For a full audit including private repos the token MUST have `repo` scope (classic PAT) or "Metadata: Read" + "Administration: Read" (fine-grained). Without it, the API silently drops private repos from the list — you'll think you saw everything and miss half.

### Default + on-demand account pattern (matches this user's setup)

User `hoonsoropenclaw` keeps a default GitHub identity and one or more alt accounts. The expected behavior:

- Default for ALL general operations: the main identity.
- Switch to an alt account ONLY when the user explicitly names it ("用 hoonsor", "switch to X", "operate as Y").
- After the alt-account task completes, switch back to default automatically.
- Never operate on the default account while a non-default is active unless told to.

The `gh auth status` check + a `gh auth switch --user <default>` at the end of any cross-account task is the minimum enforcement.

### Listing repos for an account

```bash
gh repo list <owner> --limit 200 \
  --json name,nameWithOwner,private,fork,description,createdAt,updatedAt,pushedAt,stargazersCount,url \
  --no-archived --source
```

The default visibility filter is public-only. If the user has private repos you want to audit (the common case for "OpenClaw left a mess" cleanup), make sure the token has `repo` scope. Without it, private repos silently disappear from the list.

For batch delete after a user-approved list, the safe sequence is:

1. Show the user the candidate list.
2. Have them reply with EXACT names (or a glob).
3. For each repo: `gh repo delete <owner>/<name> --yes` (the `--yes` is required; gh will otherwise prompt interactively and hang the script).
4. Verify with a second `gh repo list` pass.

Never run an unfiltered delete across a user's account. Always require a human-confirmed list.
