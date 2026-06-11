# Full-Stack Coding Agent: Skill Integration Reference

## The Gap (2026-06-11)

Hermes has all the components for autonomous coding, but no skill wires them together. Each component works in isolation:

- `code-assist` (auto mode) — full TDD workflow, but requires manual invocation
- `agent-orchestration-multi-agent-optimize` — Worker handoff contract, but no skill references it for coding tasks
- `ai-agent-development` — Phase 1-7 roadmap, but phases must be manually sequenced

**Result:** A "write a complete feature" task requires the agent to manually figure out which skill to invoke when. A proper integration skill solves this.

## Available Components

### code-assist (strands-skills-generated)
- **Location:** `~/.hermes/skills/strands-skills-generated/code-assist/SKILL.md`
- **Mode:** `interactive` (pause for user confirm) or `auto` (run without interruption)
- **Workflow:** Explore → Plan → Code → Commit
- **Key parameters:** `task_description`, `mode`, `repo_root`, `project_name`
- **Quality gates:** RED (failing test) → GREEN (passing test) → REFACTOR

### agent-orchestration-multi-agent-optimize
- **Orchestrator-Worker handoff contract:** task + context + constraints + output_format
- **Profiling:** coordinated profiling for multi-agent cost optimization
- **Trigger:** spawning sub-agents for parallel workstreams

### ai-agent-development Phase 7 Evaluation
- **Quality gates:** Agent logic working → Tools integrated → Memory functional → Orchestration tested → Evaluation passing
- **Source:** `ai-agent-development/SKILL.md` Phase 7

## Integration Pattern

```
User task (rough idea)
  │
  ▼
ai-agent-development Phase 1-2 (Design + Single Agent)
  │  → define purpose, capabilities, tool integration
  ▼
code-assist (auto mode) — TDD implementation
  │  → Explore → Plan → Code → Commit
  │  → no user interruption in auto mode
  ▼
agent-orchestration (if sub-agents needed)
  │  → handoff: task + context + constraints + output_format
  ▼
ai-agent-development Phase 7 (Evaluation)
  │  → quality gates checklist
  ▼
Deliver
```

## Claude Code CLI /agent Mode Reference

Claude Code CLI (`claude code`) supports an `/agent` mode that runs fully autonomously:
- Receives a task description
- Plans and executes without user confirmation
- Returns results on completion

**This is the target UX** for the integration skill: "give it a task, it delivers code."

## If→Then Rules

**If** you need to autonomously implement a complete coding task
**Then** invoke `code-assist` with `mode: auto`, gate with Phase 7 quality checklist, use Orchestrator-Worker contract only if spawning sub-agents

**If** `code-assist` in auto mode encounters a decision point that would benefit from user input
**Then** pause and ask, do not guess — auto mode means "no prompting for confirmation," not "no asking for clarification when stuck"

**If** a sub-agent is needed for parallel workstreams
**Then** use `agent-orchestration-multi-agent-optimize` handoff format: task + context + constraints + output_format

## Related
- `hermes-internal.md` — Hermes internal architecture notes
- `agent-orchestration-multi-agent-optimize/SKILL.md` — Orchestrator-Worker contract
- `strands-skills-generated/code-assist/SKILL.md` — TDD workflow (452 lines)
