# FastAPI Sync SQLAlchemy — QueuePool Deadlock Bug (GitHub #15353)

**Created**: Cycle 557 (2026-07-29)
**Source**: D3-learn — GitHub FastAPI Discussion #15353 research
**Status**: CRITICAL — affects all FastAPI apps using sync SQLAlchemy session DI

---

## The Bug

Using `def get_db() → Iterator[Session]` + sync SQLAlchemy (the official FastAPI docs pattern) causes **deadlocks under load** even at modest concurrency.

| Component | Default | Problem |
|-----------|---------|---------|
| anyio threadpool | **40 threads** | Each sync request holds 1 thread for **entire request lifetime** (including Pydantic serialization) |
| SQLAlchemy pool | `pool_size=5, max_overflow=10` = **15 max connections** | Hard ceiling |
| Result | 40 threads competing for 15 connections | **QueuePool timeout → 30s deadlocks** |

The root cause: Pydantic serialization happens *after* the route handler returns but *before* the connection is returned to the pool. A sync endpoint holds a DB connection for the full request lifecycle including serialization.

**FastAPI collaborator confirmed** (YuriiMotov, April 2026):
> *"Yes, this is a real issue. See PR #12066. Until this issue has been fixed, I don't know any way to overcome this other than switching to async DB connection."*

Reference: https://github.com/fastapi/fastapi/discussions/15353

---

## Does It Affect school-bulletin-system?

**YES** — `references/fastapi-sync-vs-async-decision-20260727.md` chose sync `get_db()` for "low complexity", but that decision did NOT account for the connection ceiling.

Current risk: If bulletin system receives **15+ concurrent requests** (e.g., all teachers checking announcements simultaneously after a broadcast), pool exhaustion → 30s timeout.

At current scale (small school): acceptable risk, but **architecturally unsound for growth**.

---

## Three Fix Options

### Option A: fastapi-overflow (Easiest — no code change)

```bash
pip install fastapi-overflow
```

Then in `main.py`:
```python
from fastapi_overflow import MonkeyPatch
MonkeyPatch.patch()
```

The monkeypatch releases the DB connection back to the pool **before Pydantic serialization**, solving the deadlock without changing any ORM calls.

**Verification**: With `pool_timeout=5`, high-load test (e.g., `ab -n 100 -c 20`) should complete in < 30s with no timeout errors.

### Option B: Async SQLAlchemy (Full migration)

Migrate to `async def get_db() → AsyncGenerator[AsyncSession, None]` + `AsyncSession.execute()`. Requires:
- All ORM calls: `db.query(X)` → `await db.execute(select(X))`
- All sync session methods: `session.add()` → `await session.add()`
- `run_in_threadpool()` wrappers for any sync-only operations

**Pitfalls** (documented in `references/fastapi-async-session-lifecycle-pitfalls-20260726.md`):
- Stale read: `yield Depends()` caches session across request lifecycle
- Async/sync deadlock: blocking in async context
- `expire_on_commit=False` required for lazy loading post-commit

### Option C: Pool/Tuning + PgBouncer (Operational complexity)

```python
import anyio
# Increase thread limiter
anyio.to_thread.current_default_thread_limiter().total_tokens = 80

# Match SQL pool
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=60,  # Must be >= threadpool tokens
    pool_timeout=5,    # Fail fast instead of 30s wait
    pool_pre_ping=True,
    pool_recycle=1800
)
```

Then add **PgBouncer in transaction-pooling mode** (otherwise 4 replicas × 80 = 320 connections against Postgres `max_connections=100`).

---

## Recommended Action for school-bulletin-system

**Short-term**: `pip install fastapi-overflow` and apply monkeypatch — lowest risk, no code change needed.

**Long-term**: When migrating to FastAPI backend (Phase 2 of the upgrade path), use `async def get_db()` + `AsyncSession` from the start to avoid the deadlock ceiling.

---

## If→Then Rules

**If** FastAPI app using sync `get_db()` + `Session` receives > 15 concurrent requests
**Then** expect `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out` after 30s

**If** seeing unexplained 30s timeouts in FastAPI under load
**Then** check `pool_timeout` value — if 30s (default), the pool exhaustion is the cause

**If** school-bulletin-system needs to scale beyond ~15 concurrent users
**Then** apply `fastapi-overflow` monkeypatch first, then plan AsyncSession migration
