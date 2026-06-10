# strands-agents-sops — Installation & Skill Generation

## Installation

```bash
/usr/bin/pip3 install strands-agents-sops --break-system-packages
# DO NOT use: hermes-agent/venv/bin/pip (has no modules)
# DO NOT use: python3 from venv (pip missing inside venv)
```

The CLI becomes available as: `python3 -m strands_agents_sops`

## Generate Anthropic Skills

```bash
python3 -m strands_agents_sops skills --output-dir ~/.hermes/skills/strands-skills-generated
```

**Output:** 5 skills with SKILL.md + frontmatter:
- `pdd/` — Prompt-Driven Development (18,649 bytes)
- `code-assist/` — TDD implementation workflow (27,591 bytes)
- `code-task-generator/` — Plan → task breakdown (13,643 bytes)
- `codebase-summary/` — Codebase analysis + docs (16,665 bytes)
- `eval/` — Evaluation workflow (39,058 bytes)

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `No module named strands_agents_sops` after pip install | Installed into wrong Python environment | Use `/usr/bin/pip3` not venv pip |
| `pip's dependency resolver` warning | crewai version conflicts (ignore) | Works fine despite warnings |
| `ReadableLogRecord` import error | opentelemetry version mismatch (ignore) | CLI still works |
| skill_view fails for strands skills | Path uses underscores not hyphens | `skill_view(name="code-assist")` not `code_assist` |

## Skill Activation Path

```
skill_view(name="pdd")
  → read SKILL.md
  → follow Steps section
  → output goes to .agents/planning/<project>/
```

## Directory Conventions

| Convention | Path |
|------------|------|
| PDD SOP standard output | `.agents/planning/<project-name>/` |
| Hermes projects folder | `~/.hermes/projects/<project-name>/` |
| Both are interchangeable for program-project-planner | Both accepted |

## PDD ↔ program-project-planner Integration

PDD's 8-step workflow (Clarify → Research → Design → Plan) maps to:
- PDD Step 2-3 (Clarify + Research) → program-project-planner State 2 (PRD + idea-honing.md)
- PDD Step 4-5 (Design + Iteration Checkpoint) → program-project-planner State 2e (detailed-design.md)
- PDD Step 6-7 (Implementation Plan) → program-project-planner State 4 (Execution_Plan.md with Given-When-Then)

Key enhancement from PDD: **one question at a time**, never batch-ask. Record Q&A in `idea-honing.md`.