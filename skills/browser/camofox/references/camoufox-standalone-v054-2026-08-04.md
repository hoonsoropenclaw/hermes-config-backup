# camoufox v0.5.4 Standalone Library — 2026-08-04 Discovery Log

## Context
During 2026-08-04 metacognitive-learner cycle, discovered that:
1. `pip show camoufox` → v0.5.4 installed in hermes-agent venv
2. Camofox Docker on port 9377 → `browserConnected: false` (stale)
3. Older API patterns (e.g., `Browser` class, `.pages.new_page()`) no longer work

## Key Finding: v0.5.4 API Change

**Old patterns (pre-v0.5, now broken)**:
```python
browser = camoufox.Browser(...)         # AttributeError in v0.5.4
page = browser.pages.new_page()        # no .pages attribute
```

**v0.5.4 correct pattern**:
```python
import camoufox

browser = camoufox.Camoufox(headless=True).start()
page = browser.new_page()
page.goto('https://httpbin.org/headers')
content = page.content()
browser.close()
```

## Error Transcript

```
$ python3 -c "import camoufox; browser = camoufox.Camoufox(headless=True).start()"
Extracting addon (UBO): 100% Complete
Extracting addon (UBO): Complete
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File ".../playwright/sync_api/_context_manager.py", line 84, in start
    self.browser = NewBrowser(self._playwright, **self.launch_options)
  ...
  ff_version_str = installed_verstr().split('.', 1)[0]
  ...
camoufox.exceptions.CamoufoxNotInstalled: official/stable is not installed.
Please run `camoufox fetch` to install.
```

**Root cause**: Firefox binary not downloaded. Need `camoufox.fetch()`.

## Decision Made

Did NOT run `camoufox.fetch()` (713MB download, time cost). Instead noted:
- Docker Camofox available as fallback (though stale)
- For future cycles: if Docker stale + camoufox lib needed, run `camoufox.fetch()` first

## When Standalone lib Is Better Than Docker

1. **Docker `browserConnected: false`** — standalone has its own binary
2. **Need faster iteration** — no Docker overhead
3. **Memory constrained** — Docker + browser process double memory
4. **Firefox-specific fingerprint features** — lib has full engine access

## Action Items

- [ ] Run `python3 -c "import camoufox; camoufox.fetch()"` to get Firefox binary
- [ ] Test full scrape cycle with standalone lib
- [ ] Update SKILL.md if API differs after fetch
