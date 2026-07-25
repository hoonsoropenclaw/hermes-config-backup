---
name: github-auth
description: "GitHub auth setup: HTTPS tokens, SSH keys, gh CLI login, multi-account switching."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Git, gh-cli, SSH, Setup, Multi-Account]
    related_skills: [github-pr-workflow, github-code-review, github-issues, github-repo-management]
---

# GitHub Authentication Setup

This skill sets up authentication so the agent can work with GitHub repositories, PRs, issues, and CI. It covers three paths:

- **`git` (always available)** — uses HTTPS personal access tokens or SSH keys
- **`gh` CLI (if installed)** — richer GitHub API access with a simpler auth flow
- **Multi-account operations** — `gh auth switch` + manual `hosts.yml` edits + `GH_TOKEN` env var, for working with more than one GitHub account in the same session

**Support file:** `scripts/load-alt-token.sh` — sources a secondary account's PAT from `~/.config/hermes/alt_gh_tokens/<user>` (mode 0600) into `GH_TOKEN` without ever putting the token into chat, and verifies the account it belongs to. Use this whenever the user gives you a token path.

## Detection Flow

When a user asks you to work with GitHub, run this check first:

```bash
# Check what's available
git --version
gh --version 2>/dev/null || echo "gh not installed"

# Check if already authenticated
gh auth status 2>/dev/null || echo "gh not authenticated"
git config --global credential.helper 2>/dev/null || echo "no git credential helper"
```

**Decision tree:**
1. If `gh auth status` shows authenticated → you're good, use `gh` for everything
2. If `gh` is installed but not authenticated → use "gh auth" method below
3. If `gh` is not installed → use "git-only" method below (no sudo needed)

---

## Method 1: Git-Only Authentication (No gh, No sudo)

This works on any machine with `git` installed. No root access needed.

### Option A: HTTPS with Personal Access Token (Recommended)

This is the most portable method — works everywhere, no SSH config needed.

**Step 1: Create a personal access token**

Tell the user to go to: **https://github.com/settings/tokens**

- Click "Generate new token (classic)"
- Give it a name like "hermes-agent"
- Select scopes:
  - `repo` (full repository access — read, write, push, PRs)
  - `workflow` (trigger and manage GitHub Actions)
  - `read:org` (if working with organization repos)
- Set expiration (90 days is a good default)
- Copy the token — it won't be shown again

**Step 2: Configure git to store the token**

```bash
# Set up the credential helper to cache credentials
# "store" saves to ~/.git-credentials in plaintext (simple, persistent)
git config --global credential.helper store

# Now do a test operation that triggers auth — git will prompt for credentials
# Username: <their-github-username>
# Password: <paste the personal access token, NOT their GitHub password>
git ls-remote https://github.com/<their-username>/<any-repo>.git
```

After entering credentials once, they're saved and reused for all future operations.

**Alternative: cache helper (credentials expire from memory)**

```bash
# Cache in memory for 8 hours (28800 seconds) instead of saving to disk
git config --global credential.helper 'cache --timeout=28800'
```

**Alternative: set the token directly in the remote URL (per-repo)**

```bash
# Embed token in the remote URL (avoids credential prompts entirely)
git remote set-url origin https://<username>:<token>@github.com/<owner>/<repo>.git
```

**Step 3: Configure git identity**

```bash
# Required for commits — set name and email
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
```

**Step 4: Verify**

```bash
# Test push access (this should work without any prompts now)
git ls-remote https://github.com/<their-username>/<any-repo>.git

# Verify identity
git config --global user.name
git config --global user.email
```

### Option B: SSH Key Authentication

Good for users who prefer SSH or already have keys set up.

**Step 1: Check for existing SSH keys**

```bash
ls -la ~/.ssh/id_*.pub 2>/dev/null || echo "No SSH keys found"
```

**Step 2: Generate a key if needed**

```bash
# Generate an ed25519 key (modern, secure, fast)
ssh-keygen -t ed25519 -C "their-email@example.com" -f ~/.ssh/id_ed25519 -N ""

# Display the public key for them to add to GitHub
cat ~/.ssh/id_ed25519.pub
```

Tell the user to add the public key at: **https://github.com/settings/keys**
- Click "New SSH key"
- Paste the public key content
- Give it a title like "hermes-agent-<machine-name>"

**Step 3: Test the connection**

```bash
ssh -T git@github.com
# Expected: "Hi <username>! You've successfully authenticated..."
```

**Step 4: Configure git to use SSH for GitHub**

```bash
# Rewrite HTTPS GitHub URLs to SSH automatically
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

**Step 5: Configure git identity**

```bash
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
```

---

## Method 2: gh CLI Authentication

If `gh` is installed, it handles both API access and git credentials in one step.

### Interactive Browser Login (Desktop)

```bash
gh auth login
# Select: GitHub.com
# Select: HTTPS
# Authenticate via browser
```

### Token-Based Login (Headless / SSH Servers)

```bash
echo "<THEIR_TOKEN>" | gh auth login --with-token

# Set up git credentials through gh
gh auth setup-git
```

**Security pitfall — never paste tokens in chat.** LLM session logs can be retained, indexed, or shipped to third parties (debug uploads, retrieval, evaluation). If a user pastes a PAT directly in the conversation, treat it as compromised even if the model has redaction enabled — redaction is an output-layer filter, the raw string is already in the input/context. Tell the user to:

1. Revoke that token immediately on GitHub
2. Generate a new one and write it to a file outside the chat, e.g. `~/.config/hermes/alt_gh_tokens/<username>` (mode 0600)
3. Tell you the path; you read the file directly

### Verify

```bash
gh auth status
```

---

## Method 3: Multi-Account Operations (gh CLI + GitHub API)

This is the common case where one user has two GitHub accounts (e.g. a personal account and one created by an older agent install) and the agent needs to operate on both in the same session.

### How gh Stores Multiple Accounts

`gh` keeps all accounts for a hostname in a single YAML file (`~/.config/gh/hosts.yml` on Linux). Only one is "active" at a time:

```yaml
github.com:
    users:
        hoonsoropenclaw:
            oauth_token: ghp_AAA...
        hoonsor:
            oauth_token: ghp_BBB...
    git_protocol: ssh
    user: hoonsoropenclaw          # the active one
    oauth_token: ghp_AAA...
```

### Switching Active Account

```bash
# List / check who's active
gh auth status

# Switch
gh auth switch --user <username>
```

`gh auth switch` only swaps the active pointer — it does not validate the token. If the other account's token is expired, the switch succeeds but every API call returns 401.

### Pitfall: `gh auth login --with-token` May Refuse the Token

`gh auth login` validates the token with GitHub's API before storing it. It rejects the token with `error validating token: missing required scope 'read:org'` even when the token would otherwise work for the operations you care about (e.g. `delete_repo`, `repo`).

**Symptoms:**
```
$ echo "$TOKEN" | gh auth login --hostname github.com --with-token
error validating token: missing required scope 'read:org'
```

**Why it happens:** gh hard-requires `read:org` on the stored credential because `gh` itself uses that scope for org-level queries (e.g. `gh repo list --org`). If the user only needs the token for raw API calls, this scope is irrelevant.

**Workaround — manual hosts.yml edit:**

```bash
# 1. Back up the file
cp ~/.config/gh/hosts.yml ~/.config/gh/hosts.yml.bak

# 2. Append the new account to the users map
#    Read the current file, add the new account under `users:`, write it back
python3 - <<'PY'
from pathlib import Path
import os
p = Path.home() / ".config/gh/hosts.yml"
token = os.environ["NEW_GH_TOKEN"]   # load from your isolated file
yml = p.read_text()
if "newusername:" not in yml:
    yml = yml.replace(
        "    users:\n        existinguser:\n            oauth_token: " + "ghp_EXISTING..." + "\n",
        "    users:\n        existinguser:\n            oauth_token: " + "ghp_EXISTING..." + "\n        newusername:\n            oauth_token: " + token + "\n"
    )
    p.write_text(yml)
PY

# 3. gh won't pick up the new account without a refresh, and `gh auth refresh`
#    on older versions doesn't accept --user. Either:
#    a) `gh auth switch --user newusername` (works in modern gh, but only sets
#       active pointer — does not re-validate the token against the API)
#    b) Skip gh for this account entirely and use GH_TOKEN env var (see below)
```

### Pitfall: Manually Overwriting hosts.yml Wipes Other Accounts

When you write `hosts.yml` by hand, it is very easy to overwrite the `oauth_token:` line for the *active* user at the top of the file (the YAML has both a per-user block AND a top-level `oauth_token` field — gh uses whichever is in scope). If `gh auth status` then says "Failed to log in to account X — token is invalid", you truncated the existing account.

**Always back up before editing:**

```bash
cp ~/.config/gh/hosts.yml ~/.config/gh/hosts.yml.bak
```

To restore: `cp ~/.config/gh/hosts.yml.bak ~/.config/gh/hosts.yml`.

### Bypass Pattern: Use `GH_TOKEN` env var for the Second Account

If `gh` refuses to store the second account, or you don't want to muck with `hosts.yml`, drive the second account entirely through the GitHub REST API with a `GH_TOKEN` env var:

```bash
export GH_TOKEN="<token from isolated file>"
gh api user                    # uses GH_TOKEN, not the active gh account
gh api user/repos?per_page=100
gh api -X DELETE repos/<owner>/<repo>
unset GH_TOKEN                  # clear before falling back to gh
```

This works because `gh` checks `GH_TOKEN` first and only falls back to `hosts.yml` if it's unset. The `gh` command's own argument parsing stays the same; only the credential source changes.

### Switch-Back Discipline

When working on a multi-account task, always switch back to the default account when the task ends, even if the next task is also on the secondary account. The cost of a missed switch (operating on the wrong repo as the wrong user) is much higher than the cost of a deliberate switch.

```bash
# At end of task:
gh auth switch --user <default-account>
gh auth status    # confirm
```

### Recommended: One Source of Truth Per Account

For each non-default account, store its token in one isolated file outside chat, chat logs, and any agent memory:

```
~/.config/hermes/alt_gh_tokens/<username>     # mode 0600
```

Then load it on demand:

```bash
export GH_TOKEN="$(cat ~/.config/hermes/alt_gh_tokens/<username>)"
```

Add this pattern to user memory so future sessions know the accounts exist and where the tokens live, without the token value ever entering the conversation:

```
## GitHub accounts
- default: <default_user>
- secondary: <secondary_user>, token at ~/.config/hermes/alt_gh_tokens/<secondary_user>
- switch rule: only switch to <secondary_user> when user explicitly says so;
  switch back to <default_user> when the task ends
```

---

## Using the GitHub API Without gh

When `gh` is not available, you can still access the full GitHub API using `curl` with a personal access token. This is how the other GitHub skills implement their fallbacks.

### Setting the Token for API Calls

```bash
# Option 1: Export as env var (preferred — keeps it out of commands)
export GITHUB_TOKEN="<token>"

# Then use in curl calls:
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user
```

### Extracting the Token from Git Credentials

If git credentials are already configured (via credential.helper store), the token can be extracted:

```bash
# Read from git credential store
grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
```

### Helper: Detect Auth Method

Use this pattern at the start of any GitHub workflow:

```bash
# Try gh first, fall back to git + curl
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  echo "AUTH_METHOD=gh"
elif [ -n "$GITHUB_TOKEN" ]; then
  echo "AUTH_METHOD=curl"
elif [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
  export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
  echo "AUTH_METHOD=curl"
elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
  export GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  echo "AUTH_METHOD=curl"
else
  echo "AUTH_METHOD=none"
  echo "Need to set up authentication first"
fi
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `git push` asks for password | GitHub disabled password auth. Use a personal access token as the password, or switch to SSH |
| `remote: Permission to X denied` | Token may lack `repo` scope — regenerate with correct scopes |
| `fatal: Authentication failed` | Cached credentials may be stale — run `git credential reject` then re-authenticate |
| `ssh: connect to host github.com port 22: Connection refused` | Try SSH over HTTPS port: add `Host github.com` with `Port 443` and `Hostname ssh.github.com` to `~/.ssh/config` |
| Credentials not persisting | Check `git config --global credential.helper` — must be `store` or `cache` |
| Multiple GitHub accounts | See **Method 3** above — `gh auth switch --user` for the happy path; manual `hosts.yml` edit when `gh auth login` rejects the token; `GH_TOKEN` env var as the universal bypass |
| `gh auth login` rejects a token with "missing required scope 'read:org'" | Use Method 3's manual `hosts.yml` edit or the `GH_TOKEN` env var pattern — gh's hard requirement on `read:org` is just for its own org queries, not for the operations you need |
| After editing `hosts.yml` by hand, `gh auth status` says "token is invalid" for the previously-working account | You overwrote the active account's `oauth_token` field. Restore from `~/.config/gh/hosts.yml.bak` and re-do the edit more carefully — append, don't replace |
| `gh: command not found` + no sudo | Use git-only Method 1 above — no installation needed |
