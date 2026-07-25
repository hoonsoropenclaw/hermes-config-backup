---
name: github-workflows
description: "GitHub workflow umbrella - discover and load the right skill for GitHub work. Covers authentication (gh CLI, PAT, SSH, multi-account), repository management (clone/create/fork/release/secrets), issue triage, PR lifecycle (branch/CI/merge), and PR/code review. Each sub-skill is a standalone package; this umbrella is the discovery entry point."
version: 1.0.0
author: Hermes Agent (curator consolidation pass 2026-06-27)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Repositories, Pull-Requests, Issues, Code-Review, Releases, Multi-Account, gh-cli]
    triggers:
      - github
      - gh cli
      - gh auth
      - gh pr
      - gh issue
      - git push
      - pull request
      - github api
      - PAT
      - personal access token
      - ssh key github
      - multi-account github
      - repository create
      - fork repo
      - gh release
      - issue triage
      - pr review
      - code review
---

# GitHub Workflows - Class-Level Umbrella

> **Discoverability index for the 5 GitHub sub-skills in this cluster.** Each sub-skill is a complete, standalone package (SKILL.md + references/ + templates/ + scripts/). This umbrella tells you **which one to load** for your task and **how they fit together**.

## When to use this umbrella

Load this skill when the task mentions GitHub and you need to figure out which sub-skill has the actual workflow. If you already know you need a specific sub-skill, load it directly.

## Sub-skill decision tree

```
What do you need to do?
|
+- Authenticate (gh CLI, PAT, SSH, multi-account)
|  -> github-auth                (scripts/load-alt-token.sh + scripts/gh-env.sh)
|
+- Create/clone/fork a repo, manage releases, secrets, Actions, bulk operations
|  -> github-repo-management     (references/cross-service-mapping.md, references/github-api-cheatsheet.md)
|
+- Create/triage/label/assign GitHub issues
|  -> github-issues              (templates/feature-request.md, templates/bug-report.md)
|
+- PR lifecycle: branch -> commit -> push -> CI -> merge
|  -> github-pr-workflow         (templates/pr-body-*.md, references/conventional-commits.md, references/ci-troubleshooting.md)
|
+- Review a PR or local diff (inline comments, formal review)
   -> github-code-review         (references/review-output-template.md)
```

## Auth detection - the one piece of code shared by all 5

All 5 sub-skills carry the same `gh -> git + curl` fallback block. Run this ONCE at the top of any GitHub task to set `AUTH`, `GITHUB_TOKEN`, `OWNER`, `REPO`.

For multi-account switching (the harder part) load `github-auth` directly - it has the full Method 3 with manual `hosts.yml` editing and `GH_TOKEN` env var bypass.

## Cross-cutting conventions

- **Commit messages** use Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
- **PR body templates** are stored under `github-pr-workflow/templates/`. Copy and adapt; never commit the template itself.
- **Issue templates** are stored under `github-issues/templates/`.
- **Review output format** is the structured template at `github-code-review/references/review-output-template.md`.
- **CI failures** -> `github-pr-workflow/references/ci-troubleshooting.md`.
- **Bulk operations across services** (e.g. GitHub + Vercel + Netlify) -> `github-repo-management/references/cross-service-mapping.md`.
- **Alt-token loading** for a non-default account -> `github-auth/scripts/load-alt-token.sh`.
- **GH env helper** -> `github-auth/scripts/gh-env.sh`.

## Sub-skill package locations

All 5 packages live at `~/.hermes/skills/github/<name>/`:

| Sub-skill | Path | Support files |
|---|---|---|
| github-auth | `github/github-auth/` | `scripts/load-alt-token.sh`, `scripts/gh-env.sh` |
| github-repo-management | `github/github-repo-management/` | `references/cross-service-mapping.md`, `references/github-api-cheatsheet.md` |
| github-issues | `github/github-issues/` | `templates/feature-request.md`, `templates/bug-report.md` |
| github-pr-workflow | `github/github-pr-workflow/` | `templates/pr-body-bugfix.md`, `templates/pr-body-feature.md`, `references/conventional-commits.md`, `references/ci-troubleshooting.md` |
| github-code-review | `github/github-code-review/` | `references/review-output-template.md` |

## Why a single umbrella (vs. 5 separate skills)

- Agents search skills by **description** when they see a GitHub keyword. With 5 narrow skills, an agent might miss the right one. With one umbrella that holds the decision tree, the agent always lands on `github-workflows` and is pointed at the right sub-skill in one hop.
- The 5 sub-skills share a 30-line auth-detection block (copy-pasted in all 5). The umbrella centralizes the pointer.
- New GitHub workflows (e.g. GitHub Projects, GitHub Discussions, GitHub Codespaces) get added under this umbrella - the discoverability stays intact.

## Version

1.0.0 - 2026-06-27 curator consolidation pass. Created from 5 narrow skills (`github-auth`, `github-repo-management`, `github-issues`, `github-pr-workflow`, `github-code-review`) merged into one discovery umbrella.
