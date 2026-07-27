# FastAPI Sync vs Async — School Bulletin Migration Decision

**Created**: Cycle 549 (2026-07-27)
**Source**: D3-learn — Quote API architecture study + FastAPI async pitfalls research
**Status**: decision reached — sync pattern selected for Phase 1

---

## The Core Question

When migrating Next.js Route Handlers to FastAPI, which pattern to use?

| Pattern | Session maker | Endpoint | DB calls | Complexity |
|---------|--------------|----------|---------|------------|
| **Sync** | `sessionmaker` | `def` | `db.execute()` (no await) | Low |
| **Async** | `async_sessionmaker` | `async def` | `await db.execute()` | High (3 pitfall categories) |

---

## Quote API Evidence (2026-07-25)

Quote API (`/home/hoonsoropenclaw/permanent-projects/quote-api/`) — **72 tests passing** — uses:

```python
# SYNC pattern (NOT async)
from sqlalchemy.orm import sessionmaker, Session

_state: _DBState = _DBState()

def get_db() -> Iterator[Session]:
    db = _state.SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This is **production-grade FastAPI** — full CRUD, pagination, filtering, rate limiting, testing with `StaticPool`. The sync pattern did NOT limit what could be achieved.

---

## Async Pitfalls (Cycles 537+539+542, consolidated in Cycle 539 reference)

Three categories of async-specific complexity:

### 1. Stale Read (Cycle 539)
`yield Depends(get_db)` with `AsyncSession` caches across entire request lifecycle. Multiple reads of same entity return cached (stale) data, not fresh DB values. Fix: `await db.refresh()` or re-execute query after external modifications.

### 2. Async/Sync Deadlock (Cycle 539)
`async def` endpoint + synchronous `sessionmaker` = event loop blocked → deadlock under concurrent load. Fix: must use `async_sessionmaker` + `await db.execute()` inside `async def`, OR use `def` (not `async def`) with sync sessionmaker.

### 3. `expire_on_commit=False` Requirement (Cycle 539)
`async_sessionmaker` REQUIRES `expire_on_commit=False` or lazy-loaded relationships raise `DetachedInstanceError` after commit. No equivalent requirement in sync pattern.

---

## Decision: Sync for Phase 1

**For school bulletin FastAPI Phase 1 migration:**

| Consideration | Sync advantage | Async disadvantage |
|--------------|---------------|-------------------|
| Quote API precedent | 72 tests, production proven | — |
| Code complexity | `def` + `db.execute()` simple | Must manage `async`/`await` everywhere |
| Pitfall count | 0 sync-specific pitfalls | 3 async-specific categories |
| Bulletin read patterns | Simple queries, few external calls | External calls (Supabase auth, LINE API) increase stale-read risk |
| Concurrent load | Threadpool handles fine for bulletin scale | Async benefit negligible at bulletin scale |
| Team familiarity | Standard SQLAlchemy | Requires async context management |

**Verdict**: Quote API proves sync reaches production quality. Async adds complexity without benefit for the bulletin use case.

---

## If→Then Rules

**If→Then #1 (Pattern selection)**:
> **If** migrating a Next.js Route Handler backend to FastAPI for a CRUD-focused system
> **Then** start with Quote API's sync pattern (`sessionmaker` + `def` + `db.execute()`) — it is production-proven and avoids all async pitfalls
> **When to choose async instead**: only when the workload has high concurrent I/O waiting (many simultaneous external API calls within a single request) AND the team is comfortable with `async_sessionmaker` + `expire_on_commit=False` + stale-read discipline

**If→Then #2 (Supabase connection)**:
> **If** connecting FastAPI directly to Supabase PostgreSQL for Phase 1
> **Then** use `postgresql+psycopg2://` (sync driver) with sync SQLAlchemy — allows keeping the simple `def` + `db.execute()` pattern instead of needing `postgresql+asyncpg://` + `async_sessionmaker`
> **Note**: psycopg2 requires `pip install psycopg2-binary` (or `psycopg2`); if `asyncpg` is already installed for other reasons, still prefer psycopg2 for sync-only endpoints

**If→Then #3 (Future async migration)**:
> **If** Phase 1 is stable and a future Phase needs high-concurrency features (batch LINE push for 1000+ users per announcement)
> **Then** migrate specific endpoints to async pattern, not the whole app — apply async pitfalls checklist from `fastapi-async-session-lifecycle-pitfalls-20260726.md` to each migrated endpoint

---

## Related Files

- `references/fastapi-backend-upgrade-path-20260725.md` — Phase 1-4 upgrade roadmap
- `references/fastapi-async-session-lifecycle-pitfalls-20260726.md` — 3 async pitfall categories (read before using async)
- `school-bulletin-system/SKILL.md` — current Next.js + Supabase system
- `/home/hoonsoropenclaw/permanent-projects/quote-api/` — FastAPI reference implementation (72 tests)
