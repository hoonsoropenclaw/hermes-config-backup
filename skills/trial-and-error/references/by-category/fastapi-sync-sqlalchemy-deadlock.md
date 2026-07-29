# FastAPI Sync SQLAlchemy — QueuePool Deadlock Bug (GitHub #15353)

**Created**: Cycle 557 (2026-07-29)
**Source**: D3-learn — GitHub FastAPI Discussion #15353 research
**Severity**: CRITICAL — affects all FastAPI apps using sync SQLAlchemy session DI
**FastAPI collaborator confirmed**: YuriiMotov, April 2026 — *"Yes, this is a real issue. See PR #12066."*

---

## The Bug

Using `def get_db() → Iterator[Session]` + sync SQLAlchemy (the official FastAPI docs pattern) causes **deadlocks under load** even at modest concurrency.

| Component | Default | Problem |
|-----------|---------|---------|
| anyio threadpool | **40 threads** | Each sync request holds 1 thread for **entire request lifetime** (including Pydantic serialization) |
| SQLAlchemy pool | `pool_size=5, max_overflow=10` = **15 max connections** | Hard ceiling |
| Result | 40 threads competing for 15 connections | **QueuePool timeout → 30s deadlocks** |

Root cause: Pydantic serialization happens *after* the route handler returns but *before* the DB connection is returned to the pool. A sync endpoint holds a connection for the full request lifecycle including serialization.

Reference: https://github.com/fastapi/fastapi/discussions/15353

---

## Three Fix Options

### Option A: fastapi-overflow (Easiest — no code change)

```bash
pip install fastapi-overflow
```

```python
# main.py
from fastapi_overflow import MonkeyPatch
MonkeyPatch.patch()
```

Releases connection before Pydantic serialization. **No ORM changes needed.**

**Verification**: With `pool_timeout=5`, high-load test (`ab -n 100 -c 20`) should complete in < 30s with no timeout errors.

### Option B: Async SQLAlchemy (Full migration)

Migrate to `async def get_db() → AsyncGenerator[AsyncSession, None]` + `AsyncSession.execute()`.

Required changes:
- All `db.query(X)` → `await db.execute(select(X))`
- All `session.add()` → `await session.add()`
- `run_in_threadpool()` wrappers for sync-only operations

**Pitfalls**: stale read (`yield Depends` caches session), async/sync deadlock, `expire_on_commit=False` required post-commit.

### Option C: Pool/Tuning + PgBouncer (Operational complexity)

```python
import anyio
anyio.to_thread.current_default_thread_limiter().total_tokens = 80

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=60,  # Must be >= threadpool tokens
    pool_timeout=5,    # Fail fast instead of 30s wait
    pool_pre_ping=True,
    pool_recycle=1800
)
```

Then add **PgBouncer in transaction-pooling mode** — otherwise 4 replicas × 80 = 320 connections against Postgres `max_connections=100`.

---

## school-bulletin-system Status

**Uses sync `get_db()` pattern** — chose sync for "low complexity" but did NOT account for 15-connection ceiling.

Risk: If bulletin receives **15+ concurrent requests** (e.g., all teachers checking after broadcast) → 30s QueuePool timeout.

**Short-term fix**: `pip install fastapi-overflow` + monkeypatch — zero code change.

**Long-term**: When migrating to FastAPI backend, use `async def get_db()` + `AsyncSession` from the start.

---

## If→Then Rules

**If** FastAPI app uses sync `def get_db()` + `Session` and receives > 15 concurrent requests
**Then** expect `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out` after 30s

**If** seeing unexplained 30s timeouts in FastAPI under load
**Then** check `pool_timeout` — if 30s (default), pool exhaustion is the cause

**If** school-bulletin-system needs to scale beyond ~15 concurrent users
**Then** apply `fastapi-overflow` monkeypatch first, then plan AsyncSession migration
