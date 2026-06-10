# Subagent ↔ Main Agent Communication Patterns

## TO_MEMORY Block Pattern

When a subagent needs to persist data to the main agent's memory system, it **cannot call `memory` tools directly** (subagents lack this tool). Instead, embed the data in a `[TO_MEMORY]` block at the **top** of the response:

```
## 寫入赫米斯 Memory
[TO_MEMORY]
category: 經驗
內容: ...
[/TO_MEMORY]
```

The main agent parses this block and writes to memory. **Top of response**, not the end — because the subagent output IS the final deliverable.

## Subagent Output Finality Rule

**Subagent output = final output.** The main agent receives the subagent's response verbatim and delivers it. It does NOT re-reason, re-summarize, or re-format.

- If you want formatting/structure, do it inside the subagent
- Don't say "赫米斯主體會幫你..." — just give the complete conclusion
- `[TO_MEMORY]` at top is the ONE exception the main agent parses

## Cron Job + Subagent Pattern (Replaces OpenClaw Shell Scripts)

For 24/7 autonomous learning, use:
1. `hermes cron create` with `no_agent=False`, `deliver='local'`
2. In `skills`, include the learning skill (e.g. `metacognitive-learner`) + `session_search`
3. The cron job's prompt tells the subagent to search sessions, identify gaps, research, produce If→Then
4. Subagent puts `[TO_MEMORY]` at top → main agent writes to memory

This replaces the OpenClaw pattern of cron+bash scripts for continuous learning. The key difference: subagent can *reason* about what to learn next, rather than executing fixed shell logic.

## Skill Name Format

In `hermes cron create`'s `skills` array, use the **directory name** (e.g. `metacognitive-learner`), not `metacognitive_learner` with underscores.