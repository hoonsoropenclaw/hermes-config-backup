# OpenClaw → Hermes Migration Decision Framework

Use this when evaluating whether to keep, migrate, or delete an OpenClaw script or pattern in a Hermes environment.

## Decision Tree

```
Is Hermes's built-in mechanism already covering this?
├── YES → DELETE the OpenClaw script
└── NO  → Is it a REASONING/LEARNING task?
         ├── YES → Keep as skill, drive with cron+subagent
         └── NO  → Is it a MECHANICAL MONITORING task?
                  ├── YES → Keep as script (low overhead, fixed logic)
                  └── NO  → Consider archiving / deeper analysis
```

## What Hermes Already Has (Delete OpenClaw equivalents)

| OpenClaw Pattern | Hermes Built-in |
|-----------------|-----------------|
| `memory_isolation.sh` | `memory` tool, session persistence |
| `session_cleanup.sh` | `hermes sessions` command |
| `sync_learning_to_memory.sh` | `skill_manage` for structured skills |
| `update_memory.sh` / `update_raphael_memory.sh` | `memory` tool |
| `efficiency_review.sh` | Hermes has built-in reasoning |
| `quota_guard.sh` / `api_quota_monitor.sh` | OpenClaw-only (no quota on Hermes) |
| `evolution_main.sh` / `evolution_credential_check.sh` | OpenClaw CLI commands |
| `agent_factory.sh` | `delegate_task` is Hermes's equivalent |

## When to Keep as Script (Mechanical/Monitoring)

These are legitimate keep-as-script cases:
- **System health monitoring** (disk/memory/CPU checks)
- **Watchdog** (process crash detection + restart)
- **Hardware monitoring** (N100 specific metrics)
- **Backup routines** (pure file operations)
- **External service health checks** (MCP servers)

## When to Migrate to Cron+Subagent (Reasoning Tasks)

| OpenClaw Pattern | Hermes Migration |
|-----------------|------------------|
| `gap_auditor.py` (self-reflection) | `metacognitive-learner` skill + `hermes cron` |
| `parallel_executor.sh` (parallel learning) | `delegate_task` in cron job |
| `adaptive_learner.sh` (adaptive pacing) | Subagent reasoning in cron job |
| `endless_cron_trigger.sh` | `hermes cron` schedule |
| `mempalace_kg_auto_expander.py` | Keep as script initially; evaluate later |

## Extracting Value from Large Project Directories

When OpenClaw has 900+ project directories (e.g., `endless_mode/projects/`):

1. **Don't migrate project source code** — most are one-off experiments
2. **Extract the learning essence** — use parallel `delegate_task` subagents:
   - Subagent 1: admin/school/hr domain → `learning_extract.md`
   - Subagent 2: finance domain → `learning_extract_finance.md`
   - Subagent 3: tech domain → `learning_extract_tech.md`
3. **Source locations to extract from**:
   - `SKILL_CATALOG.md` — already condensed, highest quality
   - `progress.md` files — concrete "what I did / what I learned"
   - `notes/*.md` — learning reports
4. **Delete the projects** after extraction (saves ~300MB+)
5. **Target format**: If→Then experience rules

## Mempalace Scripts

`mempalace_ifthen_extractor.py`, `mempalace_kg_auto_expander.py`, `mempalace_cli.py`:
- Keep at path `~/.openclaw/workspace/scripts/` initially
- Evaluate after `metacognitive-learner` cron job runs for a while
- These complement (not replace) Hermes's native skill/memory system