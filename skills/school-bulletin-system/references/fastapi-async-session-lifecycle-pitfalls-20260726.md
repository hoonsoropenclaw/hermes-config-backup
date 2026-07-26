# FastAPI Async SQLAlchemy Session Lifecycle Pitfalls

**Created**: Cycle 539 (2026-07-26)  
**Source**: External research — GitHub FastAPI Discussion #6628, Matthew Brown 2026-02-03  
**Validated**: Theoretical (backed by concrete reproduction case in FastAPI Discussion)

---

## Pitfall 1: Stale Read — `yield Depends(get_db)` Caches Across Request Lifecycle

### The Problem

`yield Depends(get_db)` produces an `AsyncSession` that spans the **entire request lifecycle**, not per-query.

First query:
```python
user = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one()
```

External service modifies that user:
```python
external_service.update_user(user_id, {"role": "admin"})
```

Second query — **returns stale cached data**, not the updated value:
```python
user = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one()
# user.role is STILL the old value — session cached it
```

### Why It Happens

`AsyncSession` from `async_sessionmaker` with default settings **caches loaded objects**. The SQLAlchemy identity map holds `User` instances by primary key. The second `select()` returns the cached instance, never hitting the DB.

### Fix — Two Options

**Option A: Explicit refresh after external modification**
```python
user = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one()
# ... call external service that modifies user ...
await db.refresh(user)  # ← forces fresh SELECT
```

**Option B: Re-execute the query**
```python
user = result.scalar_one()
# ... external modification ...
user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
```

Option B is more reliable when you can't predict where external calls happen.

### When This Matters

- Any request that calls **external APIs** that modify DB records mid-request
- Any request with **multiple reads** of the same entity
- Background tasks, webhooks, or queued jobs that do DB + external API round-trips

---

## Pitfall 2: `async def` + Sync Sessionmaker = Deadlock Under Load

### The Problem

If an endpoint is declared `async def` but uses a **synchronous** `sessionmaker`:

```python
# WRONG — will deadlock under concurrent load
sync_session_maker = sessionmaker(bind=engine)
@app.post("/process")
async def process(db: Session = Depends(get_db_sync)):
    user = db.query(User).get(1)  # ← BLOCKING sync I/O in async context
    external_service.update_user(1)
    user = db.query(User).get(1)  # ← may return stale or deadlock
    return "ok"
```

100 concurrent requests → **server freezes completely**. Confirmed in [GitHub FastAPI Discussion #6628](https://github.com/fastapi/fastapi/discussions/6628).

### Why It Happens

`async def` runs on the asyncio event loop. Sync I/O (`.query()`, `db.execute()`) **blocks the entire event loop** — no other request can be processed while the DB call is waiting.

### Correct Pattern

```python
# CORRECT
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

async_engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10)
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False  # ← required to avoid detached session errors on lazy-loaded relationships
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

@app.post("/process")
async def process(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one()
    # ... call external service ...
    await db.refresh(user)  # ← fresh read after external modification
    return {"user": user}
```

### Decision Table

| Endpoint type | Session maker | Execution |
|--------------|---------------|-----------|
| `async def` | `async_sessionmaker` | `await db.execute(...)` |
| `def` (sync) | `sessionmaker` (sync) | `db.execute(...)` (no await) |
| ❌ `async def` + sync sessionmaker = deadlock | | |

---

## `expire_on_commit=False` — Why It Matters

```python
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # ← required
)
```

Without this, after `await db.commit()`, any lazy-loaded attributes (`user.posts`, `user.profile`) will raise `DetachedInstanceError` if accessed outside the transaction.

---

## StaticPool for Testing

In test environments with in-memory SQLite:

```python
from sqlalchemy.pool import StaticPool

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # ← all executions share the same connection
)
```

Without `StaticPool`, each `await session.execute()` in tests gets a different connection, and in-memory SQLite data is **not shared between connections**.

---

## If→Then Rules

**If→Then #1 (Stale read prevention)**:
**If** an endpoint uses `yield Depends(get_db)` AND performs multiple reads of the same entity AND calls external services that may modify those entities  
**Then** after each external modification, call `await db.refresh(entity)` or re-execute the query — do not rely on the identity map cache

**If→Then #2 (Async/sync deadlock prevention)**:
**If** declaring a FastAPI endpoint as `async def`  
**Then** only use `async_sessionmaker` + `await db.execute(...)` inside it  
**Never** mix a sync `sessionmaker` with an `async def` endpoint — it deadlocks under concurrent load

**If→Then #3 (School bulletin FastAPI migration)**:
**If** migrating `school-bulletin-system` from Next.js Route Handlers to FastAPI  
**Then** the backend will need per-endpoint RBAC checks (currently `if/else` in route handlers) → convert to FastAPI `Depends()` dependencies; also apply the async session patterns above for any Supabase direct SQL queries
