# Sub-Agent Coding Integration Cost — Evidence & Recipes

> **Date**: 2026-06-11
> **Experiment**: Todo App (Next.js 14 + TypeScript + in-memory DB), 4 files, 1 endpoint family (4 HTTP methods)
> **Test matrix**: 3 modes × 1 round each
> **Full report**: `~/reverse-engineering/todo-app/exp-1-3-compare.md`

## TL;DR

| Mode | Wall time | Integration time | Total | Quality |
|------|-----------|------------------|-------|---------|
| **R1: Solo write** | 131s | 30s (1 trivial fix) | **161s** | 100% |
| **R2: Spawn 3 sub-agents, rough ticket** | 109s | 71s (2 big issues) | **180s** | 100% functional, 60% style consistency |
| **R3: Spawn 3 sub-agents, 6-rule spec** | ~545s (npm failure, not real cost) | 60s (2 small issues) | **~605s** (inflated) | 100% functional, 95% style consistency |

**Headline finding**: At M-task scale (2-3 tickets), spawning sub-agents does **not** save wall time. It saves main-session context occupancy. The hidden cost is integration — every (worker × shared-interface) pair can drift, and you as Orchestrator are the integrator.

## The 4 Hard Integration Issues (with fixes)

### Issue 1: Default vs named export mismatch

**Symptom**:
- Worker A (lib/db.ts) wrote `export const db = { list, create, update, deleteTodo }` (named)
- Worker B (app/api/todos/route.ts) wrote `import db from "@/lib/db"` (default)
- Result: `TS1192: Module ... has no default export`

**Why solo writers don't hit this**: The solo writer wrote `lib/db.ts` 30 seconds before `route.ts`. They remember what they exported. Workers' contexts are isolated.

**Fix in ticket**: Specify the exact export form. Don't just say "write lib/db.ts" — say `Use "export const db = { list, create, update, deleteTodo }" object form. Do NOT use named function exports.`

### Issue 2: Function signature drift

**Symptom**:
- Worker A wrote `list(): Todo[]` (no params, just returns all)
- Worker B wrote `db.list(filter)` (passes filter)
- Result: `TS2554: Expected 0 arguments, but got 1`

**Why solo writers don't hit this**: Same as above — they remember. Workers don't.

**Fix in ticket**: List every function signature verbatim. Don't say "support filtering" — say `list(filter: FilterType = "all"): Todo[]`.

### Issue 3: Return type drift (void vs boolean)

**Symptom**:
- Worker A wrote `deleteTodo(id: string): void` (throws on missing)
- Worker B wrote `if (!db.deleteTodo(id)) { return 404 }` (expects boolean)
- Result: `TS1345: An expression of type 'void' cannot be tested for truthiness`

**Why solo writers don't hit this**: They have one mental model. Workers invent their own error-handling conventions per ticket.

**Fix in ticket**: Specify the error handling convention. `deleteTodo returns boolean: true on success, false if id not found. Caller must check.`

### Issue 4: catch(e) with no `e` declared

**Symptom**:
- Worker C (page.tsx) wrote `catch { setError(e.message) }` — uses `e` but didn't declare
- ESLint error: `'e' is defined but never used` (in TS strict mode)
- Result: 3 lint errors per page.tsx

**Why solo writers don't hit this**: Solo writer usually writes `catch (e) { console.error(e); setError(e.message) }` out of habit.

**Fix in ticket**: Add to coding standards: `Always use catch (e) and check e instanceof Error: catch (e) { setError(e instanceof Error ? e.message : "default") }`.

## Ticket Template (Copy-Paste Ready)

```markdown
## Ticket T-N: [layer name]

### Files to create
- `path/to/file-a.ts`
- `path/to/file-b.tsx`

### Exact export shape (MUST match)
- `lib/db.ts`: `export const db = { list, create, update, deleteTodo }` (object form)
- `lib/types.ts`: `export type Todo = {...}` and `export type FilterType = "all" | "active" | "completed"` (named)

### Exact function signatures (MUST match)
- `list(filter: FilterType = "all"): Todo[]` — sorted by createdAt desc
- `create(title: string): Todo` — id = uuid, completed=false, createdAt=Date.now()
- `update(id: string, data: Partial<Pick<Todo, "completed">>): Todo | null` — null if not found
- `deleteTodo(id: string): boolean` — true on success, false if id not found

### API contract (if applicable)
- GET /api/todos?filter=all|active|completed → { todos: Todo[] }
- POST /api/todos { title } → 201 { todo } | 400 { error: "title required" }
- PATCH /api/todos { id, completed? } → 200 { todo } | 404 { error: "not found" }
- DELETE /api/todos?id=xxx → 200 { ok: true } | 404 { error: "not found" }

### Coding standards (MUST follow)
1. Double quotes only (no single quotes)
2. TypeScript strict mode, no `any`
3. `import { db } from "@/lib/db"` (named import, NOT default)
4. Always use `try { ... } catch (e) { setError(e instanceof Error ? e.message : "default") }` (catch (e) is mandatory, no `catch {}` shorthand)
5. `deleteTodo` not `delete` (avoids JS keyword)

### Files you must NOT touch
- `app/page.tsx` (UI layer)
- `lib/db.ts` (if you're not T-1)

### Verification before reporting DONE
- `tsc --noEmit` returns 0 errors
- File exists at the specified path
- All exported names match the spec exactly

### Working directory
Create the project at `<shared path>`. Other workers will use the same path; later workers should treat existing files as a continuation, not a conflict.
```

## Integration Verification Script (Orchestrator runs after workers return)

```bash
# 1. Verify file presence
for f in lib/types.ts lib/db.ts app/page.tsx app/api/todos/route.ts; do
  test -f "$PROJECT_DIR/$f" && echo "✓ $f" || echo "✗ MISSING: $f"
done

# 2. Cross-file import audit
echo "--- Default vs named import check ---"
grep -rn "import.*from '@/lib" app/ lib/ | grep -E "^[^:]+:[^:]+:import +[a-zA-Z_]+ +from" | head -20
# Manually verify: no `import db from` (should be `import { db } from`)

# 3. Signature drift check
echo "--- Function signature check ---"
grep -E "^export const db|^function (list|create|update|deleteTodo)" lib/db.ts

# 4. Build
cd "$PROJECT_DIR" && npm run build 2>&1 | tail -10

# 5. Type check
cd "$PROJECT_DIR" && npx tsc --noEmit 2>&1 | tail -10
```

## When to Skip This Pattern Entirely

Don't bother with sub-agents for coding if:

- The task is S-size (1 ticket, 1-2 files) — overhead exceeds gain
- The interfaces are still being designed — workers can't pin signatures to a moving target
- You, the Orchestrator, will be the one doing integration anyway — you might as well write the code
- The codebase is unfamiliar to you and you need to learn it by writing it

## Cost-Benefit Decision Table

| Task shape | Solo | Spawn | Notes |
|------------|------|-------|-------|
| 1 ticket, ≤ 2 files | ✓ | ✗ | Solo always faster |
| 2-3 tickets, 4-8 files, known interfaces | ✓ | ~ | Solo is faster wall-time; spawn saves your context |
| 2-3 tickets, 4-8 files, **unknown** interfaces | ✓ | ✗ | Spawn produces 2-3 signature mismatches |
| 5+ tickets, 10+ files, known interfaces | ~ | ✓ | Spawn wins; you can't hold it in context |
| 5+ tickets, 10+ files, unknown interfaces | ✗ | ~ | Design interfaces first (spec), then spawn |
