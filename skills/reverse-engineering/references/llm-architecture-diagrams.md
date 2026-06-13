# LLM + Architecture Diagrams for Reverse Engineering

## Key Research Findings

### arxiv 2511.05165v1 — RE + LLM Semi-Automated SAD Generation

A three-step pipeline generates Software Architecture Descriptions (SADs) from source code:

```
Step 1 (Static): Source Code → Enterprise Architect → Detailed Class Diagram
     ↓
Step 2 (Abstraction): PlantUML → GPT-4o → Core Component Identification
     ↓
Step 3 (Behavioral): Component Source → Few-shot Prompting → State Machine Diagram
```

**Key insight**: GPT-4o can correctly filter architectural noise (exclude auxiliary classes) and identify core components from a full PlantUML diagram. LLM acts as an abstraction filter, not just a code reader.

**Few-shot prompting for behavioral views**:
- General examples: LLM-generated simple cases (car door, freelance developer)
- Expert examples: Cross-domain transfer from ground truth of another system
- Domain examples: Same-domain within the project — best results combine expert + domain knowledge

### C4 Model (Simon Brown, c4model.com)

The C4 model provides a 4-level hierarchy that maps well to reverse engineering deliverables:

| Level | Name | What it shows | Reverse-engineer output |
|-------|------|--------------|------------------------|
| 1 | System Context | The whole system and users | `*-context.md` |
| 2 | Container | Applications, databases, services | `*-module-graph.md` (視角 1) |
| 3 | Component | Groupings of related code | `*-interface-map.md` (視角 2) |
| 4 | Code | Individual classes/functions | Traces, artifact notes |

### IcePanel LLM Comparison

All major LLMs (GPT-4o, Claude, Gemini) tend to fixate on generating **Code-level diagrams** and struggle to produce Context and Container views. This means:
- Always explicitly prompt for Container-level abstraction first
- Filter out low-level detail before asking for diagrams

### bitsmuggler/c4-skill (Claude Code)

A Claude Code skill that generates C4 models from existing codebases using Structurizr DSL. Reference: `github.com/bitsmuggler/c4-skill`. This is the only LLM-native C4 generation tool built specifically for AI coding agents.

## Practical Tool Chain for Reverse Engineering Diagrams

### Step 1: Generate Mermaid source (in-context or via prompt)

For a code base:
```
Analyze this source code and produce:
1. A Mermaid graph TD showing module dependencies (Container view)
2. A Mermaid stateDiagram-v2 for the main state machine
3. A Mermaid sequenceDiagram for the critical request path
```

For a website:
```
Crawl this site (max 50 pages, 4 levels deep) and produce:
1. A Mermaid graph LR with subgraphs for each page/endpoint
2. A Mermaid sequenceDiagram for the main user interaction flow
```

### Step 2: Render with beautiful-mermaid

```bash
# Tokyo-night + glass is the default for architecture diagrams
node ~/.hermes/skills/beautiful-mermaid/scripts/render.js \
  diagram.mmd -t tokyo-night -p glass -o output.svg

# For presentations: dracula + gradient
node ~/.hermes/skills/beautiful-mermaid/scripts/render.js \
  diagram.mmd -t dracula -p gradient -o output.svg

# For light docs: github-light + default
node ~/.hermes/skills/beautiful-mermaid/scripts/render.js \
  diagram.mmd -t github-light -p default -o output.svg
```

### Step 3: Deliver the .mmd source alongside the rendered output

The raw Mermaid source is version-controllable and editable downstream. Always save `.mmd` files to `~/reverse-engineering/<target>/diagrams/` alongside rendered PNG/SVG.

## Anti-Patterns

- **LLM-only diagrams without source code grounding**: LLMs hallucinate relationships. Always start with TRACE Record phase (observe actual behavior) before generating diagrams.
- **Skipping Container view for Code view**: Downstream engineers need the high-level map before the detail. Always produce C4 Level 2 before Level 4.
- **Single diagram for a complex target**: One diagram cannot capture 8 perspectives. Use different diagram types for different questions.
