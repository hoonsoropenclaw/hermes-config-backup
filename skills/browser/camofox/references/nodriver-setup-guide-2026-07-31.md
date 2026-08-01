# nodriver Setup Guide (2026-07-31)

## Status: NOT YET INSTALLED

The camofox SKILL.md references nodriver as an alternative for Chrome-based anti-bot targets,
but the `/tmp/nodriver-env` venv has **not been created yet**. This reference documents
the benchmark findings and exact setup steps.

## Benchmark Summary (2026)

| Tool | Cloudflare Bypass | Async | Setup |
|------|------------------|-------|-------|
| nodriver | ~90% (31/31 zero block) | ✅ Full async | Low (one-liner) |
| Camoufox | ~80% | ❌ Sync only | Medium |
| Playwright | <20% | ✅ Async | Low |
| Patchright | ~70% | ✅ Async | Low (drop-in Playwright) |

**Source**: `techinz/browsers-benchmark` repo, `scrapfly.io/blog/posts/best-stealth-browsers`

## Chrome Binary Available (no install needed)

nodriver can reuse existing Chrome/Chromium binaries:
```bash
# Playwright cache (use this)
ls ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome

# Selenium cache (fallback)
ls ~/.cache/selenium/chrome/linux64/*/chrome
```

## Setup Commands (execute in order)

```bash
# Step 1: Create venv (avoid PEP 668 on system python)
python3 -m venv /tmp/nodriver-env

# Step 2: Install nodriver v0.50.3 (verified 2026-07-31)
/tmp/nodriver-env/bin/pip install nodriver

# Step 3: Verify installation
/tmp/nodriver-env/bin/python3 -c "import nodriver; print('nodriver', nodriver.__version__)"

# Step 4: Find latest Playwright Chromium
CHROME=$(ls -t ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome | head -1)
echo "Using: $CHROME"

# Step 5: Working test (nodriver v0.50.3 + N100 headless)
/tmp/nodriver-env/bin/python3 << 'EOF'
import nodriver
import asyncio

async def main():
    browser = await nodriver.start(
        browser_executable_path='/home/hoonsoropenclaw/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',
        headless=True,
        sandbox=False,            # MANDATORY on N100 (root user)
        browser_args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
    )
    tab = await browser.get("https://example.com")
    # CDP navigation is async — tab.url starts empty, wait for CDP confirmation
    await asyncio.sleep(2)
    print(f"Title: {tab.title}")   # property, NOT method
    print(f"URL: {tab.url}")       # populated after CDP handshake
    await browser.stop()           # stop() last — closes the asyncio loop

asyncio.run(main())
EOF
```

**Critical N100 headless flags**: `sandbox=False` is MANDATORY on N100 (running as root).
Add `--disable-gpu --disable-dev-shm-usage` for headless stability.

## API Differences from Playwright

| Playwright | nodriver |
|-----------|----------|
| `page.title()` | `tab.title` (property) |
| `page.content()` | `tab.evaluate('document.documentElement.outerHTML')` |
| `page.goto(url)` | `tab = await browser.get(url)` |
| `browser.close()` | `await browser.stop()` |

## When to Use nodriver vs Camofox

- **Chrome-based site + strict anti-bot** → nodriver
- **Firefox-based site** → Camofox
- **Quick task + no anti-bot** → agent-browser (already installed)
- **Need cookies from existing browser** → Camofox (has cookie import API)

## Verification Checklist

After setup, run:
- [ ] `/tmp/nodriver-env/bin/python3 -c "import nodriver"` succeeds
- [ ] Basic navigation to example.com works
- [ ] Cloudflare test (e.g. https://example.com with CF challenge) passes
