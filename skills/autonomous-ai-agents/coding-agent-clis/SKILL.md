---
name: coding-agent-clis
description: "Coding-agent CLI umbrella - delegate autonomous coding work to Claude Code, OpenAI Codex, or OpenCode. Each sub-skill is a standalone package with vendor-specific command vocabulary, mode-of-operation, dialog handling, and pitfalls. This umbrella is the discovery entry point."
version: 1.0.0
author: Hermes Agent (curator consolidation pass 2026-06-27)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Claude-Code, Codex, OpenCode, Delegation, PTY, Automation]
    triggers:
      - coding agent
      - delegate coding
      - sub-agent coding
      - claude code
      - openai codex
      - opencode
      - autonomous coder
      - coding CLI
      - spawn coder
---

# Coding-Agent CLIs - Class-Level Umbrella

> **Discoverability index for the 3 coding-agent CLI sub-skills in this cluster.** Each sub-skill is a complete, standalone package covering one vendor's CLI. This umbrella tells you **which one to load** for your task and **how they relate**.

## When to use this umbrella

Load this skill when the task is "delegate a coding job to an external AI CLI" and you need to pick the right vendor (Claude Code vs Codex vs OpenCode). If you already know which one, load that sub-skill directly.

## Sub-skill decision tree

```
Which vendor's coding-agent CLI do you want to delegate to?
|
+- Anthropic's Claude Code CLI
|  -> claude-code                (Hermes orchestration guide: print mode, interactive PTY, complete CLI flags, pitfalls)
|
+- OpenAI's Codex CLI
|  -> codex                       (exec one-shots, --full-auto vs --yolo, parallel worktrees)
|
+- OpenCode (provider-agnostic, open-source)
   -> opencode                    (opencode run for one-shots, TUI sessions, multi-provider)
```

## Why three skills (not one)?

Each vendor CLI has its own:
- **CLI command vocabulary** (`claude -p` vs `codex exec` vs `opencode run`)
- **Auth flow** (`claude auth login` browser OAuth vs `OPENAI_API_KEY` vs `opencode auth login`)
- **Mode of operation** (Claude's `-p` print mode + interactive tmux, Codex's exec + sandbox, OpenCode's run + TUI)
- **PTY / dialog handling** (different prompt patterns to script)
- **Pitfalls** (Claude's `--dangerously-skip-permissions` dialog default, Codex's "no git repo" refusal, OpenCode's `/exit` is invalid command)

A maintainer writes one umbrella plus three vendor-specific packages, not one mega-skill that tries to cover all three vendors' CLI surfaces.

## Cross-cutting conventions

All three sub-skills share these patterns:

- **Always use `pty=true`** for interactive TUI sessions (`opencode` interactive, Codex interactive)
- **Print mode (`claude -p` / `codex exec` / `opencode run`)** for one-shot automation, no PTY needed
- **Background + `process(action="poll")`** for long-running tasks
- **`--max-turns`** (Claude) / `--full-auto` / `--yolo` (Codex) / `--thinking` (OpenCode) for cost + runaway control
- **Scope to a single worktree / workdir** when running parallel sessions

## Quick command cheatsheet

| Action | Claude Code | Codex | OpenCode |
|---|---|---|---|
| One-shot task | `claude -p 'task'` | `codex exec 'task'` | `opencode run 'task'` |
| Interactive TUI | `claude` (needs tmux) | `codex` (needs pty) | `opencode` (needs pty) |
| Auto-approve file changes | `--dangerously-skip-permissions` | `--full-auto` (sandboxed) or `--yolo` (no sandbox) | (defaults differ) |
| Resume session | `claude -r <id>` | `codex exec --resume` | `opencode -s <id>` |
| Continue last session | `claude -c` | n/a | `opencode -c` |
| Worktree integration | `--worktree [name]` | (use git worktree manually) | (use git worktree manually) |

## Sub-skill package locations

All 3 packages live at `~/.hermes/skills/autonomous-ai-agents/<name>/`:

| Sub-skill | Path | Trigger words |
|---|---|---|
| claude-code | `autonomous-ai-agents/claude-code/` | `claude -p`, `claude code`, Anthropic coding |
| codex | `autonomous-ai-agents/codex/` | `codex exec`, OpenAI coding agent |
| opencode | `autonomous-ai-agents/opencode/` | `opencode run`, provider-agnostic coder |

## Version

1.0.0 - 2026-06-27 curator consolidation pass. Created from 3 narrow skills (`claude-code`, `codex`, `opencode`) merged into one discovery umbrella.
