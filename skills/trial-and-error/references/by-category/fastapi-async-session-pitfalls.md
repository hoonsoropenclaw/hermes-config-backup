# FastAPI Async SQLAlchemy Session Lifecycle Pitfalls

**Created**: Cycle 539 (2026-07-26)  
**Source**: External research — GitHub FastAPI Discussion #6628, Matthew Brown 2026-02-03  
**Trigger keywords**: FastAPI / async SQLAlchemy / yield Depends / session lifecycle / stale read

---

## Pitfall 1: Stale Read — `yield Depends(get_db)` Caches Across Request Lifecycle

### The Problem

`yield Depends(get_db)` produces an `AsyncSession` that spans the **entire request lifecycle**, not per-query.

```python
# First query — cached in identity map
user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()

# External service modifies this user
external_service.update_user(user_id, {"role": "admin"})

# Second query — returns STALE cached object, not updated DB value
user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
# user.role is STILL the old value
```

### Why

`AsyncSession` identity map caches loaded objects by primary key. Second `select()` hits the cache, not the DB.

### Fix — After External Modification

```python
await db.refresh(user)  # forces fresh SELECT
# OR re-execute the query
user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
```

---

## Pitfall 2: `async def` + Sync Sessionmaker = Deadlock Under Load

### The Problem

```python
# WRONG — will deadlock under concurrent load
@app.post("/process")
async def process(db: Session = Depends(get_db_sync)):
    user = db.query(User).get(1)      # BLOCKING sync I/O
    external_service.update_user(1)
    user = db.query(User).get(1)        # deadlock or stale
    return "ok"
```

100 concurrent requests → **server freezes**. Confirmed: [GitHub FastAPI Discussion #6628](https://github.com/fastapi/fastapi/discussions/6628).

### Correct Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

async_engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10)
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False  # ← required
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

@app.post("/process")
async def process(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one()
    await db.refresh(user)  # ← fresh read after external modification
    return {"user": user}
```

### Decision Table

| Endpoint | Session | Execution | Safe? |
|----------|---------|-----------|-------|
| `async def` | `async_sessionmaker` | `await db.execute(...)` | ✅ |
| `def` (sync) | `sessionmaker` (sync) | `db.execute(...)` | ✅ |
| `async def` + sync session | `db.query()` | ❌ deadlock | |

---

## `expire_on_commit=False` — Required

```python
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

Without it, after `await db.commit()`, lazy-loaded attributes (`user.posts`, `user.profile`) raise `DetachedInstanceError` when accessed outside the transaction.

---

## `StaticPool` for Testing

```python
from sqlalchemy.pool import StaticPool

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # all executions share the same in-memory SQLite connection
)
```

Without `StaticPool`, in-memory SQLite data is **not shared** between connections.

---

## If→Then Rules

**If→Then #1 (Stale read prevention)**:
**If** FastAPI endpoint uses `yield Depends(get_db)` AND makes multiple reads of the same entity AND calls external services that may modify those entities  
**Then** after each external modification, call `await db.refresh(entity)` or re-execute the query — do not trust the identity map cache

**If→Then #2 (Async/sync deadlock)**:
**If** FastAPI endpoint is declared `async def`  
**Then** only use `async_sessionmaker` + `await db.execute(...)` inside it — never mix sync `sessionmaker` with `async def`, it deadlocks under concurrent load

**If→Then #3 (School bulletin FastAPI migration)**:
**If** migrating school-bulletin-system to FastAPI and using Supabase direct SQL queries  
**Then** apply async session patterns above; also convert `if/else` RBAC checks to FastAPI `Depends()` dependencies
