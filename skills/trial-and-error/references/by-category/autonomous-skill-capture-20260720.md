# Autonomous Skill Capture — Persistent Memory for Learned Patterns
**Source**: Mem0 (ECAIAgent Memory 2025) + MemPalace (Hermes MCP) + arXiv:2603.07670v1
**Created**: Cycle 530 (2026-07-20)
**Type**: D3-learn (實作型)

---

## Background

**The core gap**: Hermes has MemPalace MCP (L3 cross-agent memory relay) + trial-and-error skills (procedural knowledge), but no mechanism for **automatic skill extraction from accumulated experience**. The existing skills were all created manually by the metacognitive learner during D3-learn cycles. There is no autonomous loop that says "user approved this pattern 3+ times → auto-create a skill."

**Current state**:
- MemPalace = L3 relay for cross-agent memory (manual writes via MCP calls)
- trial-and-error/ = manually maintained SOPs created during metacognitive cycles
- creative-style-memory SOP = style parameters, not skill patterns
- No "experience → skill" auto-conversion loop

**Industry landscape (2026)**:
- Mem0 (ECAIAgent Memory 2025, arXiv:2504.19414): Multi-scope memory — user_id/session_id/agent_id scopes; facts extracted and stored in vector DB;Mem0 API (`mem0ai/mem0`) for Python/LangChain
- Cognee: Graph-vector hybrid; 6 memory modalities (vector, graph, BM25, claim store, temporal tables, structured); `cognee` Python package
- Letta (agentic memory): Agent-managed memory with self-improvement loop
- Hermes's MemPalace = graph-native memory with HNSW index + semantic search

---

## If→Then Patterns

**If→Then #1: Pattern Repetition Detection (skill-worthy event)**

> **If** [A successful pattern is used/repeated 3+ times across sessions without requiring modification]
> **Then** [Trigger autonomous skill capture]:
> 1. Log the pattern with MemPalace: subject=`pattern_<type>`, predicate=`used_n_times`, object=`<description>`
> 2. After 3rd use, generate a draft SOP in trial-and-error/by-category/
> 3. Notify main session: "Pattern '<name>' used 3 times — draft SOP created at `<path>`, review and confirm to activate"
> 4. **Do not** auto-activate — require human review (prevents noise/skew from being codified)
> **Why**: Mem0's core finding — "the difference between prototype and production-grade agent is whether the agent can remember" (mem0.ai 2026). Multi-scope memory tags (user_id for cross-session, session_id for conversation-scoped) enable this. 3-repetition threshold filters noise while catching real patterns.

**If→Then #2: Cross-Session Preference Memory (user-level)**

> **If** [User approves/expresses satisfaction with a response, especially a creative output]
> **Then** [Extract preference to MemPalace with user_id scope]:
> - Subject: `user_<telegram_id>_preference`
> - Predicate: `approved_style` / `rejected_style` / `preferred_workflow`
> - Object: `{json: {detail: "...", context: "...", timestamp: "..."}}`
> - Scope: `user_id` = persistent across sessions; `session_id` = current session only
> **Why**: Mem0 multi-scope memory design (user_id/session_id/agent_id/run_id). User preferences compound over time — a preference approved once should inform future sessions indefinitely. MemPalace HNSW semantic search retrieves these at conversation start.

**If→Then #3: Session Resume Context Injection (context continuity)**

> **If** [New session starts OR user returns after 7+ days of inactivity]
> **Then** [Query MemPalace for relevant context before first response]:
> 1. Query: `mempalace__mempalace_search(query="user preferences, recent approved patterns, skill gaps addressed")`
> 2. Parse results → inject into session context as `<memory_context>` block
> 3. If MemPalace returns low confidence (<0.4), fall back to session history reconstruction
> **Why**: arXiv:2603.07670v1 (Memory for Autonomous LLM Agents) — "memory turns a stateless text generator into a genuinely adaptive agent." MemPalace semantic search enables this without manual context management.

**If→Then #4: Skill Activation from MemPalace Retrieval**

> **If** [MemPalace search returns a relevant SOP/drawer with score > 0.6]
> **Then** [Automatically load the skill with skill_view before proceeding]:
> 1. Extract skill name from MemPalace result
> 2. Call `skill_view(name="<skill_name>")` to load it
> 3. Apply the SOP in the current workflow
> 4. **Do not** replace active user instructions — SOPs are defaults that apply when user hasn't specified otherwise
> **Why**: The 3-layer memory system (Session/Task/Long-term per Mem0) means MemPalace IS long-term. Semantic retrieval score > 0.6 = high relevance. Skill auto-loading closes the "SOP exists but never called" D2 gap from Cycle 525.

**If→Then #5: MemPalace Write/Read Consistency Verification**

> **If** [A critical memory write is performed (user preference, skill update, workflow decision)]
> **Then** [Verify write succeeded before proceeding]:
> 1. Write to MemPalace with `mempalace__mempalace_add_drawer`
> 2. Immediately read back with `mempalace__mempalace_get_drawer` using returned drawer_id
> 3. If read-back content ≠ written content → retry once, then alert main session
> **Why**: MemPalace MCP is Hermes's only L3 relay for cross-agent memory. No write confirmation = potential coordination failure (MAST taxonomy: 36.94% coordination failures). Write-read verification is the only reliable confirmation.

---

## Hermes-Specific Implementation Notes

- **MemPalace MCP**: Graph-native, HNSW index, semantic search. Primary API: `mempalace__mempalace_search()` + `mempalace__mempalace_add_drawer()`
- **Mem0 API**: `pip install mem0ai` — multi-scope memory (user_id/session_id/agent_id). Alternative if MemPalace proves insufficient for pattern detection
- **Mem0 vs MemPalace distinction**: MemPalace = Hermes-native graph memory with semantic search; Mem0 = general-purpose agent memory layer with multi-scope tagging. MemPalace is preferred for Hermes-internal knowledge; Mem0 could bridge external agent systems
- **Existing creative SOPs**: 7 confirmed at `trial-and-error/references/by-category/creative-*`. None are auto-loaded from MemPalace — this SOP fills that gap
- **No auto-skill creation without human review**: Pattern detection → draft SOP → human approval → activation. Prevents noise from becoming codified procedure
- **Session resume flow**: session start → MemPalace search → context injection → first response informed by past patterns
