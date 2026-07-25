# School Bulletin System — FastAPI Backend Upgrade Path

**Created**: Cycle 535, 2026-07-25
**Status**: identified — not yet implemented
**Gap**: school-bulletin-system currently uses Next.js Route Handlers as backend (App Router). A standalone FastAPI backend would enable multi-tenant SaaS, production-grade RBAC, and better testability.

---

## Why FastAPI Now

The **Quote API delivery** (2026-07-25, `/home/hoonsoropenclaw/quotes-api/`) proved Hermes has production-grade FastAPI capability:
- 72 tests passing (HTTP-level + unit + rate-limit)
- SQLAlchemy 2.0 ORM + Pydantic v2
- slowapi rate limiting (per-endpoint, per-IP)
- `StaticPool` for in-memory SQLite testing
- Full CRUD + pagination + filtering
- Live server smoke test confirmed

This capability can be directly applied to the school bulletin backend.

---

## Current Architecture (Limitations)

```
Next.js 15 (App Router) — handles both frontend AND backend
  └── Route Handlers = thin API layer over Supabase
  └── Vercel Serverless — cold starts, 10s timeout
  └── RLS = only row-level Supabase security
```

**Problems with this architecture for scale**:
1. **Business logic buried in Route Handlers** — hard to test in isolation, tightly coupled to Next.js
2. **No async job queue** — announcement publishing is synchronous; no retry on failure
3. **Multi-tenant not possible** — current schema is single-school; scaling to multiple schools needs tenant isolation
4. **Vercel cold starts** — LINE webhook needs sub-30s response; serverless is risky
5. **No structured RBAC** — permission checks are inline `if/else` in route handlers

---

## FastAPI Backend Architecture

```
School Bulletin FastAPI Backend
  ├── CRUD: /announcements (POST/GET/PATCH/DELETE)
  ├── RBAC: /users, /roles, /permissions
  ├── Auth: JWT (or HMAC cookie, compatible with existing)
  ├── Rate Limit: slowapi (per-IP, per-endpoint)
  ├── DB: SQLite (single-school) → PostgreSQL (multi-tenant)
  ├── LINE Bot Integration: webhook handler (runs on Hermes host, not Vercel)
  └── Background Tasks: announcement → LINE push (apscheduler or Temporal)
```

### Multi-tenant design (future)

```python
# Each school = tenant
class Tenant(BaseModel):
    id: str
    name: str
    line_bot_channel_secret: str | None
    line_bot_channel_token: str | None

# Tenant isolation via schema-per-tenant or database-per-tenant
# PostgreSQL: use `publicschema_name` = tenant slug
```

---

## Upgrade Phases

### Phase 1: Extract Backend Logic (Low Risk)

**Goal**: Mirror current Supabase-backed functionality in FastAPI endpoints

Extract from Next.js Route Handlers into FastAPI:
- `POST /api/announcements` → FastAPI `POST /announcements`
- `GET /api/announcements` → FastAPI `GET /announcements` (with OR/AND filter)
- `POST /api/signatures/:id` → FastAPI `POST /signatures/:announcement_id`
- Keep Supabase as DB (same connection); only replace the API layer

**Why safe**: Frontend stays on Next.js; only backend calls redirect to FastAPI.

### Phase 2: Add Structured RBAC (Medium Risk)

Replace inline `if/else` permission checks with FastAPI dependencies:

```python
from fastapi import Depends, HTTPException
from enum import Enum

class Role(str, Enum):
    SYSADMIN = "sysadmin"
    DEPT_OFFICER = "dept_officer"
    TEACHER = "teacher"
    PARENT = "parent"
    STUDENT = "student"

def require_publisher(role: Role = Depends(get_current_user_role)):
    if role not in (Role.SYSADMIN, Role.DEPT_OFFICER):
        raise HTTPException(403, "發布權限不足")
```

### Phase 3: LINE Bot Webhook (New)

LINE webhook handler runs on Hermes host (not Vercel):

```python
from linebot import WebhookParser
from linebot.exceptions import InvalidSignatureError

@router.post("/webhook/line")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        events = parser.parse(body, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(400, "Invalid signature")
    # Handle: follow event → add LINE user_id to school
    # Handle: postback → navigate to specific announcement
```

### Phase 4: Multi-tenant (Long Term)

PostgreSQL with `schema_per_tenant` or `database_per_tenant` isolation. Each school gets:
- Own DB schema (PostgreSQL schemas)
- Own LINE Bot channel
- Own admin accounts
- Shared core code, isolated data

---

## If→Then Rules

**If** user asks to "commercialize" or "standardize" the school bulletin system
**Then** propose FastAPI backend extraction as Phase 1; do NOT propose rewriting the frontend

**If** user needs LINE bot real-time push for new announcements
**Then** FastAPI backend is required; Next.js Route Handlers on Vercel cannot reliably handle LINE webhook latency requirements

**If** current Next.js backend has inline RBAC that keeps growing
**Then** extract to FastAPI dependencies before it becomes unmaintainable

---

## Related Skills

- `school-bulletin-system/SKILL.md` — current system (Next.js + Supabase, 624 lines)
- `school-bulletin-system/references/line-bot-webhook-integration-20260719.md` — LINE integration plan
- Quote API (`/home/hoonsoropenclaw/permanent-projects/quote-api/`) — FastAPI production reference (72 tests)

---

## Quote API Key Learnings (Transferable)

1. **`StaticPool` for in-memory testing**: SQLite test DB must use `poolclass=StaticPool` so all threads share one connection
2. **Engine swap pattern**: Tests inject test engine via `_state.engine = test_engine` — avoids `dependency_overrides` issues when init runs in lifespan
3. **slowapi `request` parameter**: `@limiter.limit()` decorated endpoints MUST have `request: Request` as first parameter (even if unused)
4. **Route ordering**: `/random` must come before `/{id}` otherwise FastAPI matches `/random` as an `id` parameter
5. **Atomic writes**: use `tempfile.mkstemp` + `os.replace()` for corruption-safe report writes
6. **`async_sessionmaker` + `yield Depends()` pattern** (Cycle 537): `async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)` + `async def get_db() → AsyncGenerator[AsyncSession, None]` with `yield` for per-request setup/teardown. Endpoint param: `session: AsyncSession = Depends(get_db)`
7. **BLOCKING sync I/O in async endpoint = event loop blocked** (Cycle 537): FastAPI async endpoint declared `async def` that calls synchronous blocking DB operations blocks the entire event loop. Use `async_sessionmaker` + native `async def` DB operations, OR declare route as `def` (not `async def`) to run in threadpool
