# Skill Selection Routing — D3-learn Cycle 501

## Gap: Hermes Automatic Skill Selection (164 Skills, Zero Routing)

**Identified**: Cycle 501, 2026-07-16
**Trigger**: User-delegated learning task

---

## Problem Statement

Hermes has 164 skills in `~/.hermes/skills/` but **no automatic skill selection mechanism**.
Every skill is manually triggered by the operator or by exact name matching in `skill_view()`.
The system cannot autonomously:
1. Discover which skill best matches a user request
2. Route a complex request to the right specialized sub-skill
3. Build a dynamic capability map at startup

All existing creative skills (mmx-cli, creative pipeline, etc.) are **manually invoked**, not auto-routed.

---

## Theory Research (4 Sources)

### 1. REDEREF — Recursive Delegation + Dynamic Capability Discovery (ICLR 2026)
**URL**: https://openreview.net/forum?id=bQgaTaN2eG
- Online Bayesian delegation (Thompson sampling) for dynamic routing
- Calibrated self-reflection via LLM judge for credit assignment
- Text-appropriate aggregation using selection with evidence checks
- Memory-aware belief updates for long-term adaptation
- Key insight: recursive re-routing loop recovers 60%+ of initially failed tasks

### 2. BELLA — Budget-Efficient LLM Selection via Automated Skill-Profiling (arXiv:2602.02386, 2026-02)
**URL**: https://papers.cool/arxiv/2602.02386
- Decomposes LLM outputs to extract granular skills required (critic-based profiling)
- Clusters skills into structured capability matrices
- Multi-objective optimization for cost-performance trade-offs
- Provides natural-language rationale for model routing recommendations
- Key insight: **skill profiling** (not benchmark scores) is the right unit for routing

### 3. AMRO-S — Multi-Agent LLM Routing via Ant Colony Optimization (arXiv:2603.12933, 2026-03)
**URL**: https://papers.cool/arxiv/2603.12933v1
- SFT small language model for intent inference (low-overhead semantic interface)
- Decomposes routing memory into task-specific pheromone specialists
- Quality-gated asynchronous update mechanism
- Key insight: pheromone patterns = interpretable routing evidence

### 4. LobeHub agent-capability-discovery Skill
**URL**: https://lobehub.com/skills/neversight-skills_feed-agent-capability-discovery
- Scans repository's skill directories
- Parses each `skill.yaml` to build searchable global map
- Use at system startup to populate internal tool list
- Use during routing to select best specialized skill
- Key insight: skill discovery is metadata-only (does not execute skills)

---

## Core Understanding

**The fundamental gap**: Hermes treats skills as **static, manually-invoked** tools.
Modern agent systems (REDEREF, AMRO-S, LobeHub) treat skills as **dynamically discoverable, routable** capabilities.

| Dimension | Hermes Current | Target State |
|-----------|--------------|-------------|
| Skill selection | Manual, by name | Automatic, by intent match |
| New skills | Invisible unless operator knows | Auto-discovered at startup |
| Skill conflict | No resolution | Probabilistic routing with confidence |
| Routing evidence | None | Structured routing trace |
| Cost optimization | Static model selection | Skill-level routing |

**Critical insight from REDEREF**: The recursive re-routing loop is what recovers failed tasks — not the initial routing. Hermes needs a **retry with reflection** mechanism, not just initial skill selection.

**Critical insight from BELLA**: The right routing unit is **granular skills** (not models, not tasks). Hermes 164-skill library is already the right granularity; the missing piece is the **profiling and matching layer**.

---

## If→Then Rules

**If** Hermes receives a user request and no explicit skill is named
**Then** Use intent classification (creative vs non-creative vs multi-agent) to narrow to skill category, then use keyword/trigger matching against SKILL.md `triggers` metadata field
**Reason**: Hermes skills already have YAML frontmatter with `triggers`; this is de facto capability declaration that can be used for routing without new infrastructure

**If** Hermes needs to select among multiple candidate skills for one request
**Then** Apply Thompson sampling (randomized exploration) over confidence-ranked skills — don't always pick highest confidence, but weight by confidence with epsilon-greedy exploration
**Reason**: REDEREF research shows Bayesian delegation with Thompson sampling outperforms deterministic highest-confidence routing

**If** A skill selection fails (wrong skill chosen) on a complex task
**Then** Trigger recursive re-routing: reflect on failure, re-score remaining skills, try next candidate
**Reason**: REDEREF data shows recursive re-routing loop recovers 60%+ of initially failed tasks; Hermes has no retry-with-reflection mechanism currently

**If** Designing a new Hermes skill for distribution
**Then** Include `triggers` array in YAML frontmatter with ≥5 specific trigger phrases AND a `capabilities` section describing input/output/edge cases
**Reason**: LobeHub agent-capability-discovery confirms standardized metadata enables routing automation; skill.yaml format would enable the discovery layer

---

## Next Steps (D4 Structural)

1. **Immediate**: Populate `triggers` field in all existing skills' SKILL.md frontmatter (currently many are missing)
2. **Short-term**: Implement simple keyword-match router in `skill_view()` that auto-suggests skills by trigger overlap
3. **Medium-term**: Integrate LobeHub agent-capability-discovery pattern — scan skills/ at startup, build lightweight in-memory capability map
4. **Long-term**: Implement REDEREF-style recursive re-routing with reflection on failure

---

## Validation Commands

```bash
# Verify Hermes skill count
find ~/.hermes/skills -name SKILL.md | wc -l
# Expected: 164

# Verify zero skill.yaml files (no structured metadata)
find ~/.hermes/skills -name "skill.yaml" -o -name "skill.yml" | wc -l
# Expected: 0

# Verify multi-model-routing-cheatsheet exists (closest existing routing mechanism)
ls ~/.hermes/skills/devops/multi-model-routing-cheatsheet/SKILL.md
# Expected: file exists (237 lines)
```
