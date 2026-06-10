# VNC + API Session Separation — Debugging Guide
**Updated**: 2026-05-31 — Added critical finding: VNC framebuffer ≠ browser API session

## The Core Concept

When Camofox is running with VNC enabled, there are **two independent sessions**:

```
┌─────────────────────────────────────────────────────┐
│  VNC Viewer (port 5900/6080)                        │
│  → Sees: Xvfb framebuffer (:161 default)            │
│  → May show: about:blank, old page, or empty screen │
│  → Black cursor = browser process alive but idle    │
│  → X cursor = browser fully shut down               │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Camofox API (port 9377)                            │
│  → Sees: camoufox browser session (own process)      │
│  → Active tabs, navigation, automation               │
│  → Completely independent from VNC                  │
└─────────────────────────────────────────────────────┘
```

**Key insight**: Loading a URL via the API does NOT update the VNC display. They are separate rendering contexts.

## The Login State Paradox — CRITICAL FINDING

> **If VNC shows YouTube logged in but `browser_navigate` shows "NOT LOGGED IN"** — this is EXPECTED, not a bug.

Both VNC and `browser_navigate` may show different login states because:

1. **VNC** connects to the Xvfb framebuffer — whatever page was last visible in that framebuffer session
2. **browser_navigate** uses the Camofox HTTP API session — a completely independent Playwright browser context

Even when you manually navigate in VNC and log into YouTube there, the cookies are written to `/tmp/playwright_firefoxdev_profile-XXXXXX/` (a temp profile). The API session has its own isolated cookie jar.

**If you need consistent login state:**
- Use the API exclusively (navigate, click, fill via API calls)
- OR use VNC exclusively for manual browsing
- Do NOT expect them to share cookies or login state

## Diagnostic Checklist

```bash
# Step 1: Check if browser API is healthy
curl http://localhost:9377/health
# Expected: {"ok":true,"running":true,"browserConnected":true,"browserRunning":true}

# Step 2: Check active tabs via API
curl "http://localhost:9377/tabs?userId=hermes"
# Returns: list of tabs with URLs and titles

# Step 3: Check VNC process is running
ps aux | grep -E 'x11vnc|websockify' | grep -v grep

# Step 4: Check Xvfb is running
ps aux | grep Xvfb | grep -v grep

# Step 5: Check which display Camoufox is using
ps aux | grep camoufox | head -5
# Look for DISPLAY=:161 in the output
```

## Common Patterns

### Pattern 1: VNC black + API working = NORMAL
- VNC shows black or stale page
- API shows active tab with URL and title
- **Action**: Nothing wrong — this is expected. Continue using browser API.

### Pattern 2: VNC shows X cursor = browser dead
- Browser idle-shutdown triggered
- **Fix**: Set `browserIdleTimeoutMs: 2592000000` in camofox.config.json, restart container

### Pattern 3: VNC shows browser window but page is wrong
- VNC shows a Firefox window but not the page you're automating
- **Action**: Use API to navigate — VNC is just for visual monitoring, not control

### Pattern 4: VNC shows logged in, API shows logged out = EXPECTED
- This is NOT a bug — VNC and API have independent cookie jars
- **Action**: Do not try to "fix" this — it is working as designed
- To get logged-in state in API, use API to navigate and log in there

## VNC Refresh Trick

If VNC shows stale content, try:
1. Move mouse in VNC window
2. Press Alt+Tab to cycle windows (if multiple)
3. Refresh VNC connection (disconnect and reconnect)

## Logging

To see x11vnc connection logs:
```bash
docker logs camofox-browser 2>&1 | grep -i vnc
```

x11vnc logs show client connections with frame rate and encoding:
```
client IP: 100.103.103.20
use encoding: ZRLE
frame rate: 472.6 KB/s
```

This confirms x11vnc is successfully capturing Xvfb — the black screen is session mismatch, not a capture failure.
