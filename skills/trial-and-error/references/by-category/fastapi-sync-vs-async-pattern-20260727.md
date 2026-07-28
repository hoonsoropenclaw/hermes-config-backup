# FastAPI Sync vs Async Pattern Selection (Cycle 549)

**Category**: backend-development / FastAPI
**Created**: Cycle 549 (2026-07-27)
**Source**: D3-learn — school bulletin FastAPI Phase 1 migration planning

---

## If→Then

**If→Then #1 (FastAPI pattern selection for CRUD migrations)**:

> **If** choosing between sync and async SQLAlchemy for a FastAPI migration from Next.js Route Handlers
> **Then** start with Quote API's sync pattern (`sessionmaker` + `def` + `db.execute()`) — production-proven (72 tests) and avoids 3 async pitfall categories
> **When async is better**: only when workload has high concurrent I/O waiting (many simultaneous external API calls within one request) AND team is comfortable with async session discipline
> **Evidence**: Quote API (`/home/hoonsoropenclaw/permanent-projects/quote-api/`) — full CRUD, pagination, filtering, rate limiting, 72 tests passing with sync pattern
> **Full analysis**: `school-bulletin-system/references/fastapi-sync-vs-async-decision-20260727.md`

---

## The Three Async Pitfall Categories

| # | Pitfall | Symptom | Fix |
|---|---------|---------|-----|
| 1 | Stale read | `yield Depends(get_db)` caches across entire request lifecycle; multiple reads of same entity return stale data | `await db.refresh()` or re-execute query after external modifications |
| 2 | Async/sync deadlock | `async def` + sync `sessionmaker` blocks event loop under concurrent load | Use `async_sessionmaker` + `await db.execute()` OR use `def` (not `async def`) with sync sessionmaker |
| 3 | `expire_on_commit=False` | After `await db.commit()`, lazy-loaded relationships raise `DetachedInstanceError` | Always set `expire_on_commit=False` in `async_sessionmaker` |

## Why Sync Wins for Bulletin-Scale Workloads

- **Quote API evidence**: 72 tests, production deployed, full CRUD + rate limiting
- **Complexity**: sync = `def` + `db.execute()` (no await); async = must manage `await` everywhere
- **Bulletin read patterns**: simple queries, few external calls — async benefit negligible
- **Supabase connection**: use `postgresql+psycopg2://` (sync driver) — avoids needing `asyncpg` + `async_sessionmaker`

---

## Supabase Connection Pattern (Sync)

```python
# Connect FastAPI to Supabase PostgreSQL using sync SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# psycopg2 driver (sync) — keeps simple sync pattern
SUPABASE_DB_URL = "postgresql://postgres.xxx@db.xxx.supabase.co:5432/postgres"
engine = create_engine(SUPABASE_DB_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

> **Note**: Install psycopg2: `uv pip install psycopg2-binary` (or `pip install psycopg2-binary`)

---

## Uvicorn Proxy Trust Is a Server-Layer Boundary (2026-07-28)

**If→Then #2 (rate-limit identity behind Uvicorn)**:

> **If** a FastAPI rate limiter keys by client IP **Then** the application must use only `request.client.host` from the ASGI scope; do not parse raw `X-Forwarded-For` / `X-Real-IP` again in app code. Configure trust once at Uvicorn with `proxy_headers` + a narrow `forwarded_allow_ips` list.
> **Why**: Uvicorn may rewrite `request.client.host` before FastAPI sees the request. Conversely, app-level raw-header parsing can bypass Uvicorn's trusted-proxy allowlist. In a real TCP smoke test, an injected `X-Forwarded-For` changed the limiter bucket until the runner used `--no-proxy-headers`; the durable fix was a secure-by-default runner plus ASGI-scope-only keying.
> **Verification**: exhaust one bucket, send another request with a forged `X-Forwarded-For`, and require `429 + Retry-After`. Test through a real Uvicorn TCP process, not only `TestClient`.

## SQLite Data Directory Must Not Chmod Existing Shared Parents (2026-07-28)

**If→Then #3 (SQLite file-mode hardening)**:

> **If** a service creates a private SQLite DB directory **Then** create that new directory under `umask(0077)` and set `0700`; set DB/WAL/SHM to `0600`.
> **If** the configured parent directory already exists with a broader mode **Then** fail closed with a clear error; do not silently `chmod 0700` an existing shared directory such as `/tmp` or a project root.
> **Verification**: regression test an existing `0755` parent, assert startup raises, parent mode remains `0755`, and no DB file is created.

## Related Files

- `school-bulletin-system/references/fastapi-sync-vs-async-decision-20260727.md` — full decision analysis
- `school-bulletin-system/references/fastapi-async-session-lifecycle-pitfalls-20260726.md` — 3 async pitfall categories
- `school-bulletin-system/references/fastapi-backend-upgrade-path-20260725.md` — Phase 1-4 upgrade roadmap
- `/home/hoonsoropenclaw/permanent-projects/quote-api/` — FastAPI reference (72 tests)
