---
name: agent-orchestrator
description: Meta-skill that orchestrates all agents in the ecosystem. Automatic skill scanning, capability matching, multi-skill workflow coordination, and registry management.
risk: safe
source: community
date_added: "2026-03-06"
author: renat
tags:
- orchestration
- multi-agent
- workflow
- automation
---

# Agent Orchestrator

## Overview

Meta-skill that orchestrates all agents in the ecosystem. Automatic skill scanning, capability matching, multi-skill workflow coordination, and registry management.

## When to Use This Skill

- When you need to coordinate multiple skills for a complex task.
- When you need to discover which skills are available in the environment.
- When you need to route a user request to the best-matching skills.
- When building or managing a multi-agent system.

## Do Not Use This Skill When

- The task is unrelated to agent orchestration.
- A simpler, more specific tool can handle the request.
- The user needs general-purpose assistance without domain expertise.

## How It Works

This meta-skill functions as a central decision and coordination layer for the entire skills ecosystem. It performs automatic scanning, identifies relevant agents, and orchestrates multiple skills for complex tasks.

## Principle: Zero Manual Intervention

- **Always scan** before processing any request.
- New skills are **auto-detected and included** when SKILL.md is created in any subfolder.
- Removed skills are **auto-excluded** from the registry.
- No manual commands are needed to register new skills.

---

## Mandatory Workflow (Every Request)

Execute these steps BEFORE processing any user request.

## Step 1: Auto-Discovery (Scan)

```bash
python agent-orchestrator/scripts/scan_registry.py
```

Ultra-fast (<100ms) via MD5 hash cache. Only re-processes changed files.
Returns JSON with summary of all skills found.

## Step 2: Skill Matching

```bash
python agent-orchestrator/scripts/match_skills.py "<user request>"
```

Returns JSON with skills ranked by relevance. Interpret results:

| Result              | Action                                                  |
|:---------------------|:--------------------------------------------------------|
| `matched: 0`        | No relevant skill. Operate normally without skills.     |
| `matched: 1`        | One relevant skill. Load its SKILL.md and follow it.   |
| `matched: 2+`       | Multiple skills. Execute Step 3 (orchestration).       |

## Step 3: Orchestration (If Matched >= 2)

```bash
python agent-orchestrator/scripts/orchestrate.py --skills skill1,skill2 --query "<user request>"
```

Returns execution plan with pattern, step order, and data flow between skills.

## Quick Shortcut (Simple Queries)

Steps 1+2 can be combined:
```bash
python agent-orchestrator/scripts/scan_registry.py && python agent-orchestrator/scripts/match_skills.py "<user request>"
```

---

## Skill Registry

The registry lives at:
```
agent-orchestrator/data/registry.json
```

## Search Locations

The scanner looks for SKILL.md in:
1. `.claude/skills/*/` (skills registered in Claude Code)
2. `*/` (standalone skills at top-level)
3. `*/*/` (skills in subfolders, up to depth 3)

## Metadata Per Skill

Each registry entry contains:

| Field          | Description                                          |
|:---------------|:-----------------------------------------------------|
| name           | Skill name (from YAML frontmatter)                   |
| description    | Full description (includes triggers)                |
| location       | Absolute path to directory                          |
| skill_md       | Absolute path to SKILL.md                            |
| registered     | Whether in .claude/skills/ (true/false)              |
| capabilities   | Capability tags (auto-extracted + explicit)         |
| triggers       | Activation keywords extracted from description       |
| language       | Primary language (python/nodejs/bash/none)           |
| status         | active / incomplete / missing                       |

## Registry Commands

```bash
## Quick Scan (Uses Hash Cache)
python agent-orchestrator/scripts/scan_registry.py

## Detailed Status Table
python agent-orchestrator/scripts/scan_registry.py --status

## Full Re-Scan (Ignores Cache)
python agent-orchestrator/scripts/scan_registry.py --force
```

---

## Matching Algorithm

For each request, the matcher scores skills using:

| Criterion                   | Points | Example                               |
|:----------------------------|:-------|:--------------------------------------|
| Skill name in query         | +15    | "use web-scraper" -> web-scraper      |
| Exact keyword trigger       | +10    | "scrape" -> web-scraper               |
| Capability category match   | +5     | data-extraction -> web-scraper        |
| Word overlap                | +1     | Query words in description            |
| Project boost               | +20    | Skill assigned to active project       |

Minimum threshold: 5 points. Skills below this are ignored.

## Match With Project

```bash
python agent-orchestrator/scripts/match_skills.py --project my-project "query here"
```

Skills assigned to the project receive +20 automatic boost.

---

## Orchestration Patterns

When multiple skills are relevant, the orchestrator classifies the pattern:

## 1. Sequential Pipeline

Skills form a chain where the output of one feeds into the next.

**When:** Mix of "producer" skills (data-extraction, government-data) and "consumer" skills (messaging, social-media).

**Example:** web-scraper collects prices -> whatsapp-cloud-api sends alert

```
user_query -> web-scraper -> whatsapp-cloud-api -> result
```

## 2. Parallel Execution

Skills work independently on different aspects of the request.

**When:** All skills have the same role (all producers or all consumers).

**Example:** instagram publishes post + whatsapp sends notification (both receive the same content)

```
user_query -> [instagram, whatsapp-cloud-api] -> aggregated_result
```

## 3. Primary + Support

One skill is primary; others provide supporting data.

**When:** One skill scores much higher than others (>= 2x).

**Example:** whatsapp-cloud-api sends message (primary) + web-scraper provides data (support)

```
user_query -> whatsapp-cloud-api (primary) + web-scraper (support) -> result
```

## Details in `References/Orchestration-Patterns.Md`

---

## Project Management

Assigning skills to projects enables relevance boost and persistent context.

## Project File

```
agent-orchestrator/data/projects.json
```

## Operations

**Create project:**
Add entry to projects.json:
```json
{
  "name": "project-name",
  "created_at": "2026-02-25T12:00:00",
  "skills": ["web-scraper", "whatsapp-cloud-api"],
  "description": "Project description"
}
```

**Add skill to project:** Update the project's `skills` array.

**Remove skill from project:** Remove from the `skills` array.

**Query project skills:** Read projects.json and list assigned skills.

---

## Adding New Skills

To add a new skill to the ecosystem:

1. Create a folder anywhere under `skills root:`
2. Create a `SKILL.md` with YAML frontmatter:
```yaml
---
name: my-new-skill
description: "Description with activation keywords..."
---

## Skill Documentation

```
3. **Done!** Auto-discovery detects it automatically on the next request.

Optionally, for native Claude Code discovery:
4. Copy SKILL.md to `.claude/skills/<name>/SKILL.md`

## Explicit Capability Tags (Optional)

Add to frontmatter for more precise matching:
```yaml
capabilities: [data-extraction, web-automation]
```

---

## Check Status of All Skills

```bash
python agent-orchestrator/scripts/scan_registry.py --status
```

## Interpret Status

| Status     | Meaning                                        |
|:-----------|:-----------------------------------------------|
| active     | SKILL.md with name + description present        |
| incomplete | SKILL.md exists but name or description missing |
| missing    | Directory exists but no SKILL.md                |

---

## Best Practices

- Provide clear, specific context about your project and requirements.
- Review all suggestions before applying them to production code.
- Combine with other complementary skills for comprehensive analysis.

## Common Pitfalls

- Using this skill for tasks outside its domain expertise.
- Applying recommendations without understanding your specific context.
- Not providing enough project context for accurate analysis.

## Related Skills

- `multi-advisor` - Complementary skill for enhanced analysis.
- `task-intelligence` - Complementary skill for enhanced analysis.

## Limitations
- Use this skill only when the task clearly matches the scope described above.
- Do not treat the output as a substitute for environment-specific validation, testing, or expert review.
- Stop and ask for clarification if required inputs, permissions, safety boundaries, or success criteria are missing.