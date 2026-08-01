# NL Task Decomposition: Heuristic Parsing vs LLM-Based Planning

**Source**: Metacognitive session 2026-07-31 + arxiv.org/html/2510.09244v1 + DSPy v3.2.1
**Date**: July 31, 2026
**Why**: Closes the gap between "Orchestrator receives ambiguous task" and "Orchestrator produces structured sub-task plan" — the step BEFORE delegation that the SKILL.md's delegation patterns don't cover.

---

## The Gap: parse_intent() Is Brittle

From the Whisper voice-web-automation session (July 29-30, 2026):

```
Heuristic approach (what we built):
  "go to X, click the button, extract the title"
    → regex: if "go to" → navigate
    → if "click" → click  
    → if "extract" → extract
    → hard-coded activation words, fixed action set

Problem: Novel action types or failure recovery
  → requires new if-branch in code
  → cannot adapt to misclassified commands
  → no self-correction on failure
```

This is the **Task Decomposition** problem — the first step an Orchestrator must solve before any delegation happens.

---

## Two Decomposition Strategies

### Strategy 1: Heuristic Parsing (Legacy)

```python
ACTIVATION = {
    'navigate': ['go to', 'open', 'visit'],
    'click':    ['click', 'tap', 'press'],
    'extract':  ['extract', 'get', 'scrape'],
}

def find_action(phrase):
    for action, keywords in ACTIVATION.items():
        for kw in keywords:
            if kw in phrase.lower():
                return action
    return None  # Unknown → falls through
```

**When it works**: ≤10 actions, closed domain, consistent phrasing
**When it fails**: Open domain, novel actions, multi-lingual, failure recovery

### Strategy 2: LLM-Based Decomposition (DSPy ReAct)

```python
import dspy
from dspy import Signature, Predict

# Declarative signature — describes WHAT, not HOW
class TaskDecompose(Signature):
    """Decompose a natural language command into structured workflow steps."""
    command = dspy.InputField(desc="raw user command in any language")
    steps = dspy.OutputField(
        desc="JSON array of {action, params}, e.g. "
             \"[{'action':'navigate','params':{'url':'https://...'}}, "
             \"{'action':'click','params':{'selector':'button'}}]\"
    )

# Simple approach: use Predict
decomposer = Predict(TaskDecompose)

# Better approach: ReAct with tool feedback
class TaskDecomposeReAct(Signature):
    """Decompose command, use tools to validate each step."""
    command = dspy.InputField()
    steps = dspy.OutputField(desc="structured JSON steps")

def validate_url(url: str) -> bool:
    """Check if URL is well-formed."""
    return url.startswith('http')

react_decomposer = dspy.ReAct(TaskDecomposeReAct, tools=[validate_url])

result = react_decomposer(
    command="go to news.ycombinator.com and click the first story"
)
# steps = "[{'action':'navigate','params':{'url':'https://news.ycombinator.com'}}, ...]"
```

**Key principle**: The LLM decides actions dynamically from tool descriptions — no hard-coded activation words.

---

## arxiv Research: Task Decomposition Taxonomy

From arxiv.org/html/2510.09244v1:

| Method | Behavior | When to Use |
|--------|----------|-------------|
| **Sequential Decomposition** | Full plan before execution | Linear pipelines, known steps |
| **Interleaved Decomposition** | Plan adapts based on feedback | Dynamic environments, failure recovery |
| **DPPM** (Decompose, Plan in Parallel, Merge) | Sub-tasks planned concurrently | Independent parallel workstreams |

**ALFWorld benchmark** (computer use agents):
- Human: 72.36% task completion
- Best LLM agent (2025): 42.9%
- Gap cause: interleaved decomposition failure (can't recover from mis-classified action)

---

## DSPy v3.2.1 API (Current)

```python
import dspy

# Step 1: Configure LM (v3 API — NOT dspy.LM())
dspy.configure(lm=dspy.LM('openai/gpt-4o-mini'))

# Step 2: Signature = declarative contract
class Decompose(Signature):
    command = dspy.InputField(desc="natural language command")
    steps = dspy.OutputField(desc="JSON array of {action, params}")

# Step 3: Choose module
predictor = Predict(Decompose)           # Direct call
cot = ChainOfThought(Decompose)          # With reasoning steps
react = ReAct(Decompose, tools=[...])    # With tool use (requires tools)

# Step 4: Use it
result = predictor(command="navigate to example.com and extract the heading")
print(result.steps)
```

---

## Integration: Where Decomposition Fits in Orchestrator Flow

```
User command (ambiguous)
    │
    ▼
[Task Decomposition]        ← NEW: this is what heuristic parsing does poorly
    │                        LLM-based: DSPy Signature + ReAct
    ▼
Structured sub-tasks
    │
    ├─→ Worker A (parallel)  ← delegation patterns (existing SKILL.md content)
    ├─→ Worker B (parallel)
    └─→ Worker C (sequential)
    │
    ▼
[Result Aggregation]        ← handoff contract output_format
    │
    ▼
Validated deliverable
```

---

## If→Then Rules

**If** the user command contains ≤10 known action types AND phrasing is consistent
**Then** heuristic parsing (activation words) is sufficient and faster (no LLM call)

**If** the domain is open (novel action types, multi-lingual, or failure recovery needed)
**Then** use DSPy Signature + ReAct decomposition:
  - `class Decompose(Signature): command → steps` 
  - `ReAct(Decompose, tools=[validator_functions])`
  - Each tool = a named function with docstring describing what it validates/does

**If** the Orchestrator must decompose once and execute many times
**Then** invest in DSPy optimization (BootstrapFewShot) — amortizes LLM call cost across runs

**If** sub-tasks from decomposition will run in parallel
**Then** use DPPM pattern: decompose → plan in parallel → merge results
  - This is exactly the Asynchronous sub-agent pattern from delegation-patterns-foundations.md

---

## Example: Upgrading parse_intent() to DSPy

**Before** (heuristic, in `voice-web-automation.html`):
```javascript
const ACTIVATION = {
    navigate: ['go to', 'open', 'navigate to'],
    click:    ['click', 'tap', 'press'],
    type:     ['type', 'enter', 'fill'],
    // ... fixed set
};

function findAction(phrase) {
    for (const [action, keywords] of Object.entries(ACTIVATION)) {
        for (const kw of keywords) {
            if (phrase.toLowerCase().includes(kw)) return action;
        }
    }
    return null;  // Unknown → silently skipped
}
```

**After** (DSPy-style, server-side Python):
```python
import dspy

class CommandDecompose(Signature):
    """Parse a voice command into structured automation steps."""
    command = dspy.InputField(desc="raw transcribed voice command")
    steps = dspy.OutputField(
        desc="JSON array: [{'action':str, 'params':dict}, ...]"
    )

dspy.configure(lm=dspy.LM('openai/gpt-4o-mini'))
decomposer = dspy.ChainOfThought(CommandDecompose)

# Available tools
def validate_url(url: str) -> str:
    """Validate and normalize a URL."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def guess_selector(phrase: str) -> str:
    """Guess CSS selector from natural language hint."""
    # ... heuristic selector logic
    return selector

react = dspy.ReAct(CommandDecompose, tools=[validate_url, guess_selector])

result = react(command="go to news.ycombinator.com and click the first story")
# result.steps = JSON string → parse and execute
```

**Key upgrade benefit**: When the command is ambiguous or contains an unseen action type, the LLM can ask clarifying questions or propose alternatives via the ReAct loop — heuristic parsing just returns `null`.

---

## Related

- `references/delegation-patterns-foundations.md` — what happens AFTER decomposition (delegation patterns)
- `references/sub-agent-coding-integration-cost.md` — integration cost of sub-agent parallel writes
- `dspy` skill — DSPy v3 API and module reference
