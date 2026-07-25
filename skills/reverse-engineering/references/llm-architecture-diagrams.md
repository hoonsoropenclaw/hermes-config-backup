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

---

## Website Reverse Engineering — TRACE Workflow (2026-06-14)

### The Gap

The tool chain above (Steps 1-3) was designed for **codebases**. Websites require a different Record phase because the "source code" is not a local directory — it is a remote, dynamic, multi-page surface that requires active crawling. The TRACE protocol in `protocol.md` does not prescribe website-specific tools.

### Website TRACE变体

| TRACE Phase | Code (existing) | Website (new) |
|------------|-----------------|---------------|
| **Triage** | `ls`, file size scan | Firecrawl `/map` or `curl --sitemap` |
| **Record** | `grep`, `strace`, decompiler | Firecrawl `/scrape` (markdown) + Camofox (JS-heavy) |
| **Abstract** | LLM PlantUML → core components | LLM markdown → Container view |
| **Challenge** | falsifiable probe | verify key pages/routes exist |

### Firecrawl Tool Chain (Primary)

Firecrawl provides two distinct operations — **always use them in this order**:

```
Step 1 — /map  (fast URL discovery, no page content)
  → Returns: sitemap of all discovered URLs, grouped by path depth
  → Use for: understanding site structure, link inventory, scope bounding
  → Limit:  max 200 URLs per call; use pageLimit param

Step 2 — /scrape  (deep content extraction, one URL per call)
  → Returns: clean Markdown, metadata, screenshot URL
  → Use for: pages discovered in Step 1 that are architecturally significant
  → Best for: 10-20 pages (not all pages — scope control)
```

**If → Then**: If the target is a website with >50 pages, use `/map` first to get the full URL inventory, then hand-pick 10-20 architecturally distinct pages for `/scrape`. Do not crawl everything before abstracting — scope explodes and confidence drops.

### Camofox (Fallback for JS-heavy / Cloudflare-protected Sites)

Camofox (headless Firefox, in `skills/browser/camofox/`) renders and extracts content where Firecrawl's `/scrape` fails on Cloudflare or heavily JavaScript-rendered pages.

```bash
node ~/.hermes/skills/browser/camofox/scripts/camofox.js \
  --url https://example.com --output example.md
```

### Website → Mermaid Pipeline

After Record phase, feed scraped Markdown to LLM with this prompt template:

```
Analyze the following website content and produce a C4 Level 2 (Container view) architecture diagram in Mermaid format.

Requirements:
1. Use `graph LR` with subgraphs for each logical group of pages/endpoints
2. Label arrows with data flow labels (e.g., "HTTP GET", "Form POST", "WebSocket")
3. Do NOT produce a class diagram or sequence diagram as the primary view
4. Identify: frontend (browser), backend API, data store, external services

Content:
{scraped_markdown_here}
```

**If → Then**: If the LLM produces `graph TD` instead of `graph LR`, it is fixating on code-level abstractions. Force a rewrite with explicit "use graph LR" in the prompt. Websites are inherently left-to-right (request → response), not top-down (caller → callee).

### Anti-Patterns (Websites)

- **Crawling before mapping**: Running `/scrape` on arbitrary URLs without `/map` first wastes API credits and produces incomplete structure.
- **LLM fixating on Code view**: Without explicit "Container view" prompting, all major LLMs default to class-level output. Always specify "Level 2" or "Container view" in the prompt.
- **Scraping too many pages**: >20 pages from a website produces diagram noise. Pick pages by structural role (e.g., home, listing, detail, auth, API endpoint).

### Quick Reference

| Scenario | Tool | Command |
|----------|------|---------|
| Discover URL structure | Firecrawl `/map` | `POST /map` with `url` + `pageLimit=200` |
| Extract page content | Firecrawl `/scrape` | `POST /scrape` with `url` |
| JS-heavy or Cloudflare | Camofox | `node camofox.js --url <url> --output <file>` |
| Render Mermaid diagram | beautiful-mermaid | `node render.js diagram.mmd -t tokyo-night -p glass -o out.svg` |
