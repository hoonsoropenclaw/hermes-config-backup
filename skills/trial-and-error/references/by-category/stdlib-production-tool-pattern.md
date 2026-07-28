# stdlib-first Production Tool Pattern

**Created**: Cycle 538 (2026-07-26)
**Source**: Telegram Weather Bot project — `/home/hoonsoropenclaw/projects/weather-bot/`
**Validated**: 12 unit tests + 4 smoke tests (all passing)

---

## L3: stdlib-First Production Tool Architecture

When building a "message received → API call → reply" bot, stdlib (`urllib` + `signal` + `dataclass`) is sufficient and preferable to pulling third-party deps.

### Why stdlib

| Approach | Deps | Lines |适合场景 |
|---------|------|-------|---------|
| stdlib (`urllib`) | **0** | ~50-100 | 3-endpoint simple bots |
| `requests` | 1 dep | ~80 | Any HTTP |
| `python-telegram-bot` | pulls `httpx`+`tornado` | 292+ | Complex dialog flows |

For a "message → API → reply" 3-step pipeline, framework overhead is over-engineering.

---

## Architecture: Module Separation

```
wttr_weather.py   — Weather API module, standalone CLI-able
telegram_bot.py   — Telegram bot: long-polling + signal handling + 3-layer defense
run.sh           — Launcher
test_unit.py     — Mock-based unit tests (no network)
test_smoke.py    — Network smoke tests
```

**Benefit**: `wttr_weather.py` usable independently (CLI, cron job, other bot).
`telegram_bot.py` only owns "Telegram ↔ weather API" routing.

---

## Three-Layer Defense Pattern

| Layer | Mechanism | Code location |
|-------|-----------|---------------|
| L1 allowlist | `TELEGRAM_ALLOWED_USERS` env, user_id check | telegram_bot.py |
| L2 rate-limit | in-memory token bucket, 3s cooldown/user | telegram_bot.py |
| L3 sanitization | `_sanitize()` strips lone surrogates, UTF-16 encode/decode | wttr_weather.py |

---

## Long-Polling vs Webhook Decision

**Prefer long-polling** when: N100 headless, no public domain, no HTTPS cert needed.
**Use webhook** when: already have public HTTPS endpoint, real-time <5s needed, high volume.

### Long-Polling Implementation

```python
offset = 0
while running:
    updates = getUpdates(timeout=30, offset=offset)
    for update in updates:
        process(update)
        offset = update['update_id'] + 1  # NOT += 1
```

Key: use `offset = update_id + 1` (absolute), not `offset += 1`.

---

## Common Python Stdlib Pitfalls

### Pitfall 1: Surrogate Pair in f-strings

```python
# WRONG
f"\\ud83d\\udccd {line}"   # two lone surrogates → UnicodeEncodeError

# CORRECT
f"📍 {line}"               # direct emoji literal
```

### Pitfall 2: Free API `lang=` affects only one-liner, not JSON data

For wttr.in: `lang=zh` only affects `format=3` output. `format=j1` JSON fields are always English.
**Fix**: Build `CONDITION_ZH` dict client-side for i18n.

### Pitfall 3: Unicode escapes in source for Chinese

```python
# WRONG — unreadable
footer = "_\u64a5\u8d70\u6642\u9593_: 2026-07-25"

# CORRECT — readable
footer = "_查詢時間_: 2026-07-25"
```

---

## If→Then Rules

**If→Then #1**: **If** building a simple bot (message → API → reply) **Then** use stdlib + module separation. 3 endpoints don't need a framework.

**If→Then #2**: **If** `UnicodeEncodeError: surrogates not allowed` **Then** replace `\ud83d\udccd` surrogate escapes with direct emoji literals.

**If→Then #3**: **If** free API has `lang=` but JSON data is still English **Then** build i18n dict client-side — `lang=` only affects human-readable output.

**If→Then #4**: **If** implementing long-polling graceful shutdown **Then** set flag in signal handler, break loop, then call `getUpdates(offset=offset)` once more with `timeout=0` to ack the final absolute cursor. Prevents Telegram redelivery on reconnect.

**If→Then #5**: **If** `sendMessage` fails and the update offset is deliberately not advanced for at-least-once redelivery **Then** roll back that request's rate-limit reservation before returning failure. Otherwise, Telegram redelivers the same update, the cooldown consumes it as "too fast", and the bot acknowledges a rate-limit reply instead of the original result. Make rollback compare the exact reservation timestamp so it cannot erase a newer concurrent reservation.

**If→Then #6**: **If** a Telegram Bot API URL embeds the token in its path **Then** production API bases must use HTTPS; allow plain HTTP only for loopback (`127.0.0.1`, `localhost`, `::1`) tests, and raise sanitized transport exceptions with `from None` so the original request URL (and token) cannot appear in a traceback.

**If→Then #7**: **If** a launcher reads `.env` without `python-dotenv` **Then** do not `source` it and do not accept arbitrary names. Parse only an explicit key allowlist, reject symlinks, and reject group/world-readable modes. Otherwise keys such as `PYTHONPATH` can turn configuration into a Python import-control surface even though no shell command is sourced.

**If→Then #8**: **If** mocked bot tests pass **Then** still run a hybrid smoke: real weather HTTPS + loopback Telegram HTTP server, asserting `getUpdates → weather → sendMessage → update_id+1 → final ack`. This caught a real Open-Meteo display defect where `admin1` and `country` were both `Taiwan`; location components must be case-insensitively deduplicated.

**Failure classification rule**: preserve the final failure domain after bounded retries. Exhausted HTTP 5xx/429 must remain `HTTP_ERROR`; DNS/timeout/socket failures remain `NETWORK_ERROR`. Do not collapse both into a generic network error after the retry loop.

---

## Verification

```bash
python3 test_unit.py          # → 12/12 passed
python3 test_smoke.py         # → ALL OK
python3 wttr_weather.py Paris # → "Paris: ☀️ +30°C"
```

---

## HTMLParser + Atomic Output Pitfalls（GitHub Trending，2026-07-27）

### Pitfall 5: HTML void elements must not increase parser depth

Python `HTMLParser.handle_starttag()` also receives void elements such as `img`, `br`, and `meta`. These elements do not have matching end tags in normal HTML. If a stateful card parser increments its nesting depth for every start tag, one `img` can leave the depth permanently off by one and prevent the surrounding `article` from closing.

**If→Then**: **If** a stdlib `HTMLParser` uses depth to delimit records **Then** maintain a `VOID_ELEMENTS` set and do not increment depth for those tags; for `br` inside captured text, append a space so words do not concatenate.

**Regression fixture**: include both `<br>` inside a description and `<img>` inside the same record, followed by a second record. Assert both records parse successfully.

### Pitfall 6: fixed sibling `.tmp` names collide under concurrent automation

`output.with_name(f".{output.name}.tmp")` is atomic for one process but not concurrency-safe: two cron runs can overwrite or replace the same temp file.

**If→Then**: **If** an automated script atomically updates an output that can have overlapping runs **Then** use `tempfile.mkstemp(dir=output.parent, prefix=f".{output.name}.", suffix=".tmp")`, write + flush + `os.fsync()`, then `os.replace()`; delete the temp file on exceptions.

**Verification**: output exists, no `.<name>.*.tmp` remains, and invalid input leaves the previous successful output unchanged.
