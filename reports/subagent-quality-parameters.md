# Subagent Quality Parameters in Hermes Agent

**Report Date:** May 31, 2026  
**Source Files:** `config.yaml`, `run_agent.py`, `delegate_tool.py`, `browser_camofox_state.py`, `session_search_tool.py`, `memory_manager.py`, `subagent-driven-development/SKILL.md`

---

## 1. delegate_task Parameters

### 1.1 Primary Parameters

| Parameter | Type | Required | Default | Effect on Quality |
|-----------|------|----------|---------|-------------------|
| `goal` | string | **Yes** | — | **Most critical.** The subagent's entire context is built around this. Vague goals produce generic/brittle outputs. Be specific and self-contained — subagent knows nothing about your conversation history. |
| `context` | string | No | `None` | Background information (file paths, error messages, project structure, constraints). **Directly proportional to output quality.** The more specific, the better. Empty context means the subagent must infer everything from the goal alone. |
| `toolsets` | list[string] | No | inherits parent's toolsets | Restricts available tools. **Too few** = subagent can't complete tasks. **Too many** = decision paralysis, slower execution. Recommended: `['terminal', 'file']` for implementation tasks. |
| `tasks` | list[dict] | No | `None` | Batch mode for parallel execution. Each dict has its own `goal`, `context`, `toolsets`, `role`. Max controlled by `delegation.max_concurrent_children`. |
| `role` | string | No | `"leaf"` | Controls delegation capability. `"leaf"` = cannot delegate further. `"orchestrator"` = can spawn own workers (bounded by `max_spawn_depth`). **Default is safe** — prevents runaway subagent trees. |
| `acp_command` | string | No | `None` | ACP command to execute in subagent's terminal. For specialized workflows. |
| `acp_args` | list[string] | No | `None` | Arguments for the ACP command. |

### 1.2 Ignored/Internal Parameters

| Parameter | Status | Notes |
|-----------|--------|-------|
| `max_iterations` | **IGNORED** | Subagent max iterations are controlled exclusively by `delegation.max_iterations` in config.yaml. The `delegate_task` kwarg is accepted but dropped with a debug log. This ensures users get predictable budget control. |
| `parent_agent` | **Internal** | Reference to parent AIAgent. Not exposed to the calling model. |

### 1.3 Per-Task Override Behavior

In batch mode (`tasks` array), per-task parameters override top-level values:
```python
# These override top-level if set in individual task dict:
task["goal"]       → always used
task["context"]    → if provided
task["toolsets"]   → if provided
task["role"]       → if provided
task["acp_command"] → if provided
task["acp_args"]   → if provided
```

---

## 2. config.yaml Delegation Parameters

Section: `delegation:`

| Parameter | Default | Min | Max | Effect on Quality |
|-----------|---------|-----|-----|-------------------|
| `model` | `""` (inherit) | — | — | Empty = subagent inherits parent's model. Set to override (e.g., `"claude-opus-4"`). **Use to route to faster/cheaper models for simple tasks.** |
| `provider` | `""` (inherit) | — | — | Empty = inherit parent's provider. Set to use different backend (e.g., `"anthropic"`). |
| `base_url` | `""` (inherit) | — | — | Direct OpenAI-compatible endpoint. When set, subagents use this instead of parent's credentials. Useful for proxy/relay setups. |
| `api_key` | `""` (inherit) | — | — | API key for the `base_url` endpoint. Empty = inherit from parent. |
| `api_mode` | `""` (inherit) | — | — | Protocol mode: `"chat_completions"`, `"codex_responses"`, etc. Auto-detected from URL when `base_url` is set. |
| `inherit_mcp_toolsets` | `true` | — | — | When `true`, subagents inherit MCP toolsets from parent. **Disable (`false`) to isolate subagents** — useful for security/performance but reduces capability. |
| `max_iterations` | `50` | 1 | — | **Hard budget.** Controls maximum tool-call loops per subagent. `50` is sufficient for most tasks. Increase for complex multi-step operations. |
| `child_timeout_seconds` | `1800` | 30 | — | Timeout per subagent in seconds (30 min default). Subagents exceeding this are marked `"timeout"` status. **Increase for long-running tasks.** |
| `reasoning_effort` | `""` (inherit) | — | — | Reasoning effort: `"low"`, `"medium"`, `"high"`. Empty = inherit from parent. **Higher = slower but more thorough reasoning.** |
| `max_concurrent_children` | `8` | 1 | soft cap >10 | **Key parallelism control.** Maximum simultaneous subagents. >10 shows cost warning. **Recommended: 5-6 for stability on typical hardware.** |
| `max_spawn_depth` | `1` | — | cap=5 | Maximum nesting depth of subagent delegation trees. `1` = flat (no nested delegation). Higher values allow orchestrator patterns but increase complexity/stability risk. |
| `orchestrator_enabled` | `true` | — | — | Whether `"orchestrator"` role subagents can actually delegate. `false` forces all to `"leaf"`. **Disable for simpler, more predictable workflows.** |
| `subagent_auto_approve` | `false` | — | — | Auto-approve dangerous commands in subagent threads. `false` = safe (auto-denies). `true` = YOLO for cron/batch. **Never set `true` in interactive sessions.** |

---

## 3. Memory / Long-Term Memory Tools

### 3.1 What Subagents Can Access

| Tool | Access | Notes |
|------|--------|-------|
| `session_search` | **Yes** | FTS5-backed search over SQLite session DB. Subagents can recall past sessions. **Key for continuity.** |
| `memory` (write) | **BLOCKED** | Subagents cannot write to shared MEMORY.md. This is intentional — prevents cross-contamination. |
| Memory context (read) | **BLOCKED** | Subagents get no automatic access to parent's memory context. Pass relevant info via `context` parameter. |

### 3.2 MemoryManager Architecture

The parent agent runs a `MemoryManager` that orchestrates memory providers:
- **Prefetch**: Before each turn, `memory_manager.prefetch_all(user_message)` injects relevant context
- **Post-turn sync**: `memory_manager.sync_all()` writes learned facts back
- **System prompt**: `memory_manager.build_system_prompt()` adds memory context to system message

**Subagents do NOT share the parent's MemoryManager.** They get:
1. A fresh `AIAgent` instance with `skip_memory=True` (no memory plugin)
2. `session_search` tool for explicit recall from the session DB
3. Nothing else — no implicit memory context

### 3.3 SessionDB / session_search Tool

From `session_search_tool.py`:
```
session_search(query="auth refactor", limit=3)     # Discovery: FTS5 search
session_search(session_id="...", around_message_id=12345, window=10)  # Scroll: message window
session_search()                                    # Browse: recent sessions
```

**Subagent recall pattern:**
```python
# In parent, after subagent completes:
delegate_task(
    goal="Review code quality",
    context="... (include session_search output for context)"
)
```

### 3.4 Memory Blocked Tools (DELEGATE_BLOCKED_TOOLS)

```python
DELEGATE_BLOCKED_TOOLS = frozenset([
    "delegate_task",  # no recursive delegation
    "clarify",        # no user interaction
    "memory",         # no writes to shared MEMORY.md
    "send_message",   # no cross-platform side effects
    "execute_code",   # children should reason step-by-step
])
```

---

## 4. Context Structuring for Maximum Quality/Stability

### 4.1 Best Practices from subagent-driven-development Skill

**The Golden Rule:** "Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context."

**Good context structure:**
```python
context = """
TASK FROM PLAN:
- Create: src/models/user.py
- Add User class with email (str) and password_hash (str) fields
- Use bcrypt for password hashing
- Include __repr__ for debugging

FOLLOW TDD:
1. Write failing test in tests/models/test_user.py
2. Run: pytest tests/models/test_user.py -v (verify FAIL)
...

PROJECT CONTEXT:
- Python 3.11, Flask app in src/app.py
- Existing models in src/models/
- Tests use pytest, run from project root
- bcrypt already in requirements.txt

OUTPUT FORMAT:
- Critical Issues: [must fix]
- Verdict: APPROVED or REQUEST_CHANGES
"""
```

### 4.2 Context Quality Scale

| Quality | Context Amount | Effect |
|---------|---------------|--------|
| **PEAK** | Full task spec + exact file paths + error messages + expected output format + project conventions | Subagent performs exactly as needed, minimal iteration |
| **GOOD** | Task description + relevant files + constraints | Subagent generally succeeds, minor clarification may be needed |
| **DEGRADING** | Task only, no specifics | Subagent improvises — inconsistent results, possible spec violations |
| **POOR** | Minimal/ambiguous goal | Subagent wastes iterations or produces off-target output |

### 4.3 What Must Be in Context (Subagent Knows Nothing About)

The subagent has **zero knowledge** of:
- Parent conversation history
- Previously read files
- Previous tool results
- User preferences/tone
- Project-wide conventions

**Always include:**
1. **File paths** (exact, absolute when possible)
2. **Error messages** (if debugging/fixing)
3. **Expected output format**
4. **Language/tone requirements** (if non-English or specific style)
5. **Project conventions** (testing framework, style rules, etc.)

### 4.4 Context Injection via [TO_MEMORY]

From the skill doc:
> "The ONE exception: `[TO_MEMORY]` blocks at the top of subagent output get parsed by the main agent and written to memory."

```python
# Subagent output:
[TO_MEMORY]
- User prefers Chinese responses for auth error messages
- bcrypt is the required hashing algorithm
- MIN_PASSWORD_LENGTH = 8
[/TO_MEMORY]

# Main implementation here...
```

---

## 5. Identity Persistence Patterns

### 5.1 Browser Identity (Camofox)

From `browser_camofox_state.py`:

```python
def get_camofox_identity(task_id: Optional[str] = None) -> Dict[str, str]:
    scope_root = str(get_camofox_state_dir())
    logical_scope = task_id or "default"
    
    user_digest = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"camofox-user:{scope_root}",
    ).hex[:10]
    
    session_digest = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"camofox-session:{scope_root}:{logical_scope}",
    ).hex[:16]
    
    return {
        "user_id": f"hermes_{user_digest}",       # Stable per Hermes profile
        "session_key": f"task_{session_digest}",   # Stable per task
    }
```

**Config keys (`config.yaml`):**
```yaml
browser:
  camofox:
    managed_persistence: false   # Set true to enable Hermes-managed identity
    user_id: ''                  # Override (normally auto-derived)
    session_key: ''             # Override (normally auto-derived)
    adopt_existing_tab: false
    rewrite_loopback_urls: false
    loopback_host_alias: host.docker.internal
```

### 5.2 Subagent Identity Parameters

In `AIAgent.__init__` (from `run_agent.py`):

| Parameter | Purpose | Pass Through? |
|-----------|---------|---------------|
| `user_id` | Primary user identifier | Inherited by subagents |
| `user_id_alt` | Alternate user ID | Inherited |
| `user_name` | Display name | Inherited |
| `chat_id` | Chat/conversation ID | Inherited |
| `chat_name` | Chat name | Inherited |
| `chat_type` | Chat type | Inherited |
| `thread_id` | Thread ID | Inherited |
| `gateway_session_key` | Gateway session key | Inherited |
| `session_id` | Local session identifier | Inherited |

**Identity inheritance path:**
```
Parent AIAgent → _build_child_agent() → Child AIAgent
                 ↓
        _resolve_delegation_credentials()
        _resolve_child_credential_pool()
```

### 5.3 Session Persistence

```yaml
sessions:
  auto_prune: false
  retention_days: 90
  vacuum_after_prune: true
  write_json_snapshots: false
```

- Sessions persist for 90 days by default
- `session_search` can recall from this history
- Subagents share the same session DB for cross-agent recall

### 5.4 Credential Pool Sharing

```python
def _resolve_child_credential_pool(effective_provider, parent_agent):
    # Rule 1: Same provider → share parent's pool (cooldown/rotation sync)
    # Rule 2: Different provider → load that provider's own pool
    # Rule 3: No pool → child uses inherited fixed credentials
```

---

## 6. Subagent Output Finality

**Critical architectural note from SKILL.md:**

> "In Hermes, subagent output IS the final deliverable. The main agent does NOT re-reason, re-summarize, or re-format it."

**Implications:**
1. If you want formatted output, **the subagent must do it**
2. Don't write prompts like "the main agent will process this"
3. `[TO_MEMORY]` blocks are the **only** exception — parsed and written to memory by main agent

---

## 7. Configuration Recommendations

### 7.1 For Stability (Production)

```yaml
delegation:
  max_concurrent_children: 5    # Below warning threshold
  max_spawn_depth: 1            # Flat structure only
  orchestrator_enabled: false   # Disable nested delegation
  child_timeout_seconds: 1800   # 30 min
  max_iterations: 50
  subagent_auto_approve: false  # Safe default
  inherit_mcp_toolsets: true    # Full capability
```

### 7.2 For Throughput (Batch/Parallel)

```yaml
delegation:
  max_concurrent_children: 8   # Parallel batch tasks
  max_spawn_depth: 1
  orchestrator_enabled: false
  child_timeout_seconds: 600    # 10 min per task
  max_iterations: 50
  subagent_auto_approve: true   # For unattended batch
```

### 7.3 For Complex Orchestration

```yaml
delegation:
  max_concurrent_children: 4    # Conservative for complex trees
  max_spawn_depth: 2            # Allow one level of nesting
  orchestrator_enabled: true     # Enable orchestrator role
  child_timeout_seconds: 2400   # 40 min for complex tasks
  max_iterations: 100           # Larger budget
```

---

## 8. Parameter Summary Table

| Parameter | Location | Default | QoQ Impact | Rec. Value |
|-----------|----------|---------|------------|------------|
| `goal` | delegate_task() | required | **Critical** — defines all output | Specific, self-contained, actionable |
| `context` | delegate_task() | None | **High** — quality proportional to detail | Full spec + file paths + constraints |
| `toolsets` | delegate_task() | inherit | **Medium** — capability vs. focus | `['terminal', 'file']` for impl |
| `role` | delegate_task() | `"leaf"` | **Medium** — safety vs. flexibility | `"leaf"` for most tasks |
| `tasks` | delegate_task() | None | **High** — batch efficiency | Up to `max_concurrent_children` |
| `delegation.max_iterations` | config.yaml | 50 | **High** — iteration budget | 50-100 for complex tasks |
| `delegation.child_timeout_seconds` | config.yaml | 1800 | **Medium** — prevent runaway | 600-1800 depending on task |
| `delegation.max_concurrent_children` | config.yaml | 8 | **High** — parallelism | 5-6 stable, 8 max throughput |
| `delegation.max_spawn_depth` | config.yaml | 1 | **Medium** — complexity | 1 for safety |
| `delegation.subagent_auto_approve` | config.yaml | false | **High** — security | Always false in interactive |
| `delegation.inherit_mcp_toolsets` | config.yaml | true | **Medium** — capability | true unless isolating |

---

*Report generated from Hermes Agent source analysis. Parameters verified against run_agent.py (line 317-454), delegate_tool.py (lines 1918-2801), config.yaml (lines 353-366), and SKILL.md (subagent-driven-development).*
