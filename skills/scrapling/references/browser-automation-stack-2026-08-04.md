# Browser Automation Stack — Layer Model (2026-08-04)

## Core Insight

Browser automation for anti-bot sites has **three distinct layers**:

| Layer | Role | Tools |
|-------|------|-------|
| **1. Fetch/Runtime** | HTTP requests, CDP, WebDriver | curl, requests, Playwright, nodriver CDP |
| **2. Fingerprint/Stealth** | Browser fingerprint hiding, headless disguise | camoufox lib, Camofox Docker, nodriver |
| **3. Parsing/Adaptation** | Element location, structure learning, anti-change | scrapling, BeautifulSoup |

**scrapling** handles Layer 3 (adaptive parsing).
**camoufox / Camofox / nodriver** handle Layer 2 (fingerprint).
**Playwright** handles Layer 1+2 (but with poor stealth).

## Complementary Combinations

| Target | Best Stack |
|--------|-----------|
| Simple static site | scrapling `Fetcher` alone |
| Cloudflaremoderate site | scrapling `StealthyFetcher` (has built-in stealth) |
| Strict Cloudflare + Chrome target | **scrapling + nodriver** (Layer 3 + Layer 2) |
| Strict Cloudflare + Firefox target | **scrapling + camoufox lib** (Layer 3 + Layer 2) |
| Need cookie auth + scraping | **Camofox Docker** (Layer 2 + cookie jar) + scrapling post-processing |
| Full browser automation with auth | Camofox Docker (port 9377) with its own API |

## Key 2026-08-04 Findings

1. **Camofox Docker often stale**: `browserConnected: false` on port 9377 despite API server running
2. **camoufox lib v0.5.4** installed in hermes-agent venv but needs `camoufox.fetch()` (713MB)
3. **nodriver** not installed, VM CDP matching issues unresolved
4. **scrapling** has built-in `StealthyFetcher` that handles Turnstile — no external browser needed for moderate anti-bot

## scrapling + camoufox Combo Example

```python
# When scrapling's built-in stealth isn't enough, add camoufox
import camoufox
from scrapling.fetchers import Fetcher

# Use camoufox as the "browser backend" for scrapling
browser = camoufox.Camoufox(headless=True).start()
# ... feed cookies/session from camoufox into scrapling if needed
```

## Decision Tree (Updated)

```
Need browser automation?
│
├─ No anti-bot → curl / web_extract / requests → DONE
│
├─ Moderate anti-bot (basic Cloudflare)
│   └─ scrapling StealthyFetcher → DONE
│
├─ Strict anti-bot + scraping + element adaptation needed
│   └─ scrapling StealthyFetcher + camoufox lib (layer 2+3)
│
├─ Cookie auth required (Google, YouTube)
│   └─ Camofox Docker (port 9377) — cookies + fingerprint
│
└─ Chrome target + strictest anti-bot
    └─ nodriver (~90% bypass) — but VM env issues remain
```

## Reference

- camofox skill: `browser/camofox/SKILL.md` — Layer 2 (fingerprint) coverage
- scrapling skill: `scrapling/SKILL.md` — Layer 3 (parsing) coverage
- nodriver benchmark: `browser/camofox/references/nodriver-setup-guide-2026-07-31.md`
- camoufox v0.5.4 API: `browser/camofox/references/camoufox-standalone-v054-2026-08-04.md`
