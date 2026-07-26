---
name: hallmark
description: "Anti-AI-slop design skill for greenfield pages, audits, redesigns, and brand studies. Produces CSS-formatted HTML that looks and feels designed — not generated."
version: 2.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hallmark:
    migrated: 2026-07-26
    reason: "SKILL.md exceeded 300 lines / 20 KB — split into references/"
    previous_size: "552 lines / 62 KB"
---

# Hallmark

Anti-AI-slop design skill for greenfield pages, audits, redesigns, and brand studies.

## Quick reference

| Topic | Reference file |
|-------|---------------|
| How to use + discipline principles | `references/hallmark-01-usage.md` |
| Disciplines across every verb | `references/hallmark-02-disciplines.md` |
| When brief is a component | `references/hallmark-03-component.md` |
| Design flow: pre-flight → macrostructure | `references/hallmark-04a-preflight-macrostructure.md` |
| Design flow: memory → theme → ruleset | `references/hallmark-04b-memory-theme.md` |
| Design flow: hero → preview → build | `references/hallmark-04c-hero-preview-build.md` |
| Design flow: slop test | `references/hallmark-04d-slop-test.md` |
| hallmark audit / redesign / study commands | `references/hallmark-05-commands.md` |
| Output contract & scope | `references/hallmark-06-output-contract.md` |

## Usage

```markdown
/hallmark [greenfield | audit | redesign | study] <brief>
```

- **greenfield**: New page from scratch — full hallmark design flow
- **audit**: Check existing page against hallmark principles
- **redesign**: Improve existing page
- **study**: Analyze brand and produce design DNA

## Key principles

1. **Layout before detail** — pick macrostructure first
2. **Typography is structure** — not decoration
3. **Whitespace is active** — never passive padding
4. **Color has meaning** — not random palette
5. **Motion with purpose** — not gratuitous animation

## Troubleshooting

- **Vague brief**: Ask clarifying questions before generating
- **Style not matching brand**: Run `hallmark study` first to load brand DNA
- **Output too generic**: Increase specificity in brief or add reference URLs
