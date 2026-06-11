# Long-Running Sub-Agent Profile Creation — 13-Step Recipe

> **Date verified**: 2026-06-11 (reverse-engineer profile creation, ground truth)
> **Trigger phrases**: "建一個常駐代理", "build a permanent sub-agent", "long-running agent", "monitoring agent", "常駐子代理"
> **Time budget**: 15-30 minutes for a complete profile
> **Skip-the-step detection**: If you finish in < 15 min, you probably skipped step 3 (copy trial-and-error SOP) or step 9 (write slim-history.md)

## The 13 Steps

### Step 1: Plan the role (5 min, do this FIRST)

Before any tooling, write down on paper (or in your scratchpad):

- **Trigger phrases**: What will users say to invoke this agent?
- **Input types**: What does the agent accept? (URLs, code, files, natural language, etc.)
- **Output artifacts**: What does the agent produce? (markdown reports, diagrams, code, dashboards, etc.)
- **Handoff targets**: Which other agents consume this agent's output?
- **禁止事項**: What must the agent NOT do? (this is where most role design fails)

**Why first**: Every step below assumes you know what the role is. If you skip this and start typing `hermes profile create`, you'll end up with a profile whose persona is "to be determined" and 50 skills you don't need.

### Step 2: `hermes profile create <name> --clone` (10s)

```bash
hermes profile create <name> --clone
```

Auto-creates:
- `~/.hermes/profiles/<name>/` with config, .env, SOUL.md, skills/ cloned from default
- `~/.local/bin/<name>` wrapper (but it's wrong — see step 8)
- Note: the auto-wrapper uses `hermes chat` form, not `hermes -p <name>` form. You'll fix it in step 8.

**DO NOT** use `--clone-all` — that copies sessions, logs, and cron history, polluting the new profile.

### Step 3: Copy trial-and-error SOP (5s, **DO NOT SKIP**)

```bash
mkdir -p ~/.hermes/profiles/<name>/skills/trial-and-error/references/sops/
cp -r ~/.hermes/profiles/consumer-researcher/skills/trial-and-error/references/sops/* \
      ~/.hermes/profiles/<name>/skills/trial-and-error/references/sops/
```

**Why**: The default `~/.hermes/skills/trial-and-error/` is in a **minimal-rebuild state** (2026-06-11 onwards). It only has `by-category/audience-permission-logic.md` and the SKILL.md body. The `references/sops/profile-slimming-sop.md` (which you'll need in step 7) lives in the per-profile copies of trial-and-error, not in the default.

**How to verify the SOP got copied**:
```bash
ls ~/.hermes/profiles/<name>/skills/trial-and-error/references/sops/
# Should show: profile-slimming-sop.md
```

### Step 4: Write `persona.md` at profile root

`~/.hermes/profiles/<name>/persona.md` should contain:

```markdown
# <Role Name in Chinese + English>

You are <one-sentence role description>.

## In the agent roster
<Where this agent sits, what it hands off to>

## Core beliefs
<5-10 principles, in numbered list>

## 6-step workflow
<The actual work the agent does>

## Deliverables format
<What the output looks like>

## Handoff to downstream
<Which other agents consume this output, and how>

## 禁止事項
<What the agent must NOT do>

## Skill library overview
<Table of skills, grouped by category, with byte counts>

## Language and style
<繁體中文 by default for this user's setup>
```

**Length budget**: 200-400 lines is normal. < 100 lines = under-specified, agent will improvise. > 600 lines = over-engineered, agent will get confused by edge cases.

### Step 5: Write the agent's defining skill (1-2 unique skills)

This is the **methodology skill** — the codified "how to do this role's job." Without this, the agent re-invents its workflow every session.

Location: `~/.hermes/profiles/<name>/skills/<defining-skill-name>/SKILL.md`

```markdown
---
name: <skill-name>
description: <one-line trigger>
---

# <Skill Title>

## When to use
<Trigger conditions>

## Core methodology
<Numbered steps, each with concrete commands>

## Pitfalls
<What goes wrong, what to do instead>

## Verification
<How to know you did it right>
```

**Anti-pattern**: Don't write a 50-line vague skill. Write a 200-400 line specific skill with exact commands and exact pitfalls. The persona says WHAT, the skill says HOW.

**If** the role is generic (e.g. "researcher"), no unique skill is needed — persona is enough. **If** the role has a specific technique (e.g. "reverse engineer must produce 8-view architecture diagrams"), the technique MUST be in a skill, not just the persona.

### Step 6: `hermes -p <name> skills opt-out --remove --yes` (5s)

```bash
hermes -p <name> skills opt-out --remove --yes
```

This:
- Writes `~/.hermes/profiles/<name>/.no-bundled-skills` marker (prevents future `hermes update` from re-seeding)
- Removes ~65 unmodified bundled skills
- Keeps user-edited, hub-installed, and local skills

**Verify**:
```bash
ls ~/.hermes/profiles/<name>/.no-bundled-skills  # marker exists
hermes -p <name> skills list 2>&1 | tail -1     # count dropped
```

### Step 7: Whitelist prune with Python (10s)

Use Python with `shutil.rmtree`, NOT shell glob, NOT `hermes skills disable`:

```python
import os, shutil

PROFILE_DIR = f"/home/hoonsoropenclaw/.hermes/profiles/<name>/skills"

# 1. Get actual disk list
actual = set(
    d for d in os.listdir(PROFILE_DIR)
    if not d.startswith(".")
    and d not in {"_meta"}
    and os.path.isdir(os.path.join(PROFILE_DIR, d))
)

# 2. Define whitelist (own + hermes infra + role-specific)
KEEP = {
    # Hermes infrastructure (5)
    "general-workflow", "user-collaboration-style", "trial-and-error",
    "workspace-folder-layout", "anti-panic-protocol",
    # Anti-slop (3)
    "anti-pattern-czar", "anti-slop-design", "antislop",
    # Defensive coding (4)
    "bash-defensive-patterns", "python-anti-patterns",
    "python-observability", "python-resilience",
    # ... role-specific (varies)
    # Defining skill (1-2)
    "<your-defining-skill>",
}

# 3. Drop the rest
to_remove = sorted(actual - KEEP)
for name in to_remove:
    path = os.path.join(PROFILE_DIR, name)
    if os.path.isdir(path): shutil.rmtree(path)
    elif os.path.isfile(path): os.remove(path)
```

**Why not shell glob**: `rm -rf profiles/<name>/skills/{a,b,c,...}` can fail silently on a typo. Python with explicit set comparison is fail-loud.

**Why not `hermes skills disable`**: It just adds a marker, doesn't free disk space, and the skill is still loaded into context.

### Step 8: Fix the wrapper script

The auto-created wrapper at `~/.local/bin/<name>` looks like:
```bash
#!/bin/sh
exec hermes chat "$@"  # WRONG — uses default profile
```

Fix it to:
```bash
#!/bin/sh
exec hermes -p <name> "$@"
```

```bash
chmod 755 ~/.local/bin/<name>
cat ~/.local/bin/<name>  # verify
```

### Step 9: Write `skills/_meta/slim-history.md`

`~/.hermes/profiles/<name>/skills/_meta/slim-history.md` should be the **decision record**:

```markdown
# <Name> Profile — Skill 精瘦紀錄

> 建立日期: YYYY-MM-DD

## 建立歷程
| 階段 | 時間 | 動作 | skill 數變化 |
|------|------|------|------------|
| 建立 | ... | `hermes profile create ... --clone` | 0 → ~194 |
| 修補 trial-and-error | ... | 從 consumer-researcher cp 進 SOP | 不變 |
| 新增自寫 skill | ... | 寫 <defining-skill> | 194 → 195 |
| Opt-out bundled | ... | `skills opt-out --remove --yes` | 195 → 193 |
| 精瘦 opt-out | ... | 依白名單刪除 | 193 → <N> |

## 精瘦決策
### <Category 1> (N 個)
- skill A: 為什麼保留
- skill B: 為什麼保留

### <Category 2> (N 個)
- ...

## 對標其他常駐代理的 skill 數量
| Profile | skill 數 | 角色 |
|---------|---------|------|
| ... | ... | ... |
| <this> | <N> | <role> |

## 驗證 4 件套
- [x] 專屬 skill 還在
- [x] 4 個通用必留
- [x] default 依然完整
- [x] opt-out marker 存在
```

### Step 10: Run 4-件套 verification (30s)

```bash
PROFILE=~/.hermes/profiles/<name>

# 1. Own skill present
test -f $PROFILE/skills/<defining-skill>/SKILL.md && echo "✓ defining skill" || echo "✗ MISSING"

# 2. 4 hermes infrastructure skills present
for s in general-workflow trial-and-error user-collaboration-style workspace-folder-layout; do
  test -d $PROFILE/skills/$s && echo "✓ $s" || echo "✗ MISSING $s"
done

# 3. Default profile untouched
DEFAULT_COUNT=$(ls ~/.hermes/skills/ | wc -l)
echo "default has $DEFAULT_COUNT skills (should be ~196)"

# 4. opt-out marker
test -f $PROFILE/.no-bundled-skills && echo "✓ marker" || echo "✗ MISSING marker"
```

**If any check fails, STOP.** Don't proceed to step 11. The profile is broken.

### Step 11: Update trial-and-error with the new profile's name

The default trial-and-error skill should know about the new常駐代理 so future agents can reference it. Patch the existing `references/sops/profile-slimming-sop.md` or the main `SKILL.md` to mention the new profile in examples.

### Step 12: Document in mental model

The user might keep a written list of profiles. Update it (or note in your reply to the user) that a new profile was created.

### Step 13: Smoke test

```bash
hermes -p <name> skills list 2>&1 | tail -1
# Expected: "0 hub-installed, 2 builtin, N local — N+2 enabled, 0 disabled"
# where N is 30-50

hermes profile list 2>&1 | grep <name>
# Expected: <name>    MiniMax-M3    stopped    <name>    —

~/.local/bin/<name> --help 2>&1 | head -5
# Expected: hermes help output
```

**If smoke test passes, the profile is ready for use.**

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Skipping step 3 (copy trial-and-error SOP) | Next time you try to slim a new profile, can't find the SOP, lose 30 min re-creating it | Always cp the SOP |
| Skipping step 5 (defining skill) | Agent re-invents its workflow every session, inconsistent output | Write 1-2 skills, even short ones |
| Skipping step 9 (slim-history) | 6 months later, can't remember why the profile is configured this way, refactor breaks | Write the decision record immediately |
| Using `--clone-all` instead of `--clone` | New profile inherits old sessions, logs, cron history — polluted state | Always `--clone` |
| Wrapper uses `hermes chat` instead of `hermes -p <name>` | `<name>` command invokes default profile, not the new one | Fix wrapper in step 8 |
| Forgetting `cross_profile=true` on `write_file` | Writing to `profiles/<other>/**` gets blocked by soft guard | Always pass `cross_profile=true` for non-default profile paths |

## Time Budgets (Reality Check)

| Profile complexity | Realistic time |
|-------------------|----------------|
| 1-file defining skill, simple persona | 15-20 min |
| 1-2 file defining skill, detailed persona | 25-40 min |
| Complex multi-skill defining methodology | 45-90 min |

If you finish faster than the table says, you probably skipped something. The reverse-engineer profile (8-view methodology, 13-step recipe) took ~40 minutes including verification.

## Integration with Other Skills

- **`trial-and-error`**: Always has the "精瘦 SOP 真實位置" warning about needing to copy from another profile. Update trial-and-error when you create a new常駐代理.
- **`agent-orchestration-multi-agent-optimize`**: The 13-step recipe in this file is the canonical reference. The main SKILL.md has a quick checklist version.
- **`agent-identity-management`**: The new profile is now an "agent" — the new identity should be documented there too if the user's setup includes an agent registry.
