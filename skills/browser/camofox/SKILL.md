---
name: camofox
description: |
  Camofox (camoufox-based Firefox) headless browser for Hermes Agent — Docker deployment,
  anti-detection cookie import, and authenticated browsing sessions. Use when:
  - Setting up a Camofox browser container on N100/Linux
  - Importing cookies from Chrome Cookie-Editor extension for authenticated browsing
  - Navigating Google, OpenAI, or other sites that block headless browsers
  - Configuring CAMOFOX_URL / CAMOFOX_USER_ID / CAMOFOX_SESSION_KEY in Hermes
triggers:
  - camofox setup
  - camofox docker
  - camofox cookies import
  - camoufox anti-detection browser
  - CAMFOX_URL
  - CAMFOX
  - CAMOFOX_URL
  - CAMOFOX
  - CAMOFOX_SESSION_KEY
  - CAMOFOX_USER_ID
  - camofox vnc
  - x11vnc camofox
  - remote browser n100
version: 1.2.0
---

# Camofox Browser Setup & Operations

## ⚠️ Pre-Flight Health Check (MANDATORY — do this before any operation)

**Every time** you need to use Camofox, verify the browser engine is connected first:

```bash
# Run this before ANY camofox operation
HEALTH=$(curl -s http://localhost:9377/health)
echo "$HEALTH" | python3 -c "
import sys, json
d = json.load(sys.stdin)
connected = d.get('browserConnected', False)
running = d.get('browserRunning', False)
if not (connected and running):
    print('⚠️  browserConnected={}, browserRunning={}'.format(connected, running))
    print('Browser engine disconnected. Run: docker restart camofox-browser')
    print('Wait 2-3 minutes, then re-check health.')
    sys.exit(1)
else:
    print('✅ Browser engine healthy')
"
```

**If the check fails**: Run `docker restart camofox-browser` and wait 2-3 minutes before retrying. This catches the browser engine disconnect proactively instead of failing mid-task.

---

## Overview
Camofox is a camoufox-based anti-detection Firefox browser running in Docker on N100.
It provides authenticated browsing sessions by importing cookies from Chrome's Cookie-Editor extension.

---

## Docker Deployment

### Critical: Use `--network host` Mode

Camofox MUST be started with `--network host`, NOT `-p 9377:9377`.

**Reason**: With bridge network (`-p`), Docker assigns the container an IP like `172.17.0.x`.
Requests from `localhost:9377` arrive at the container with `remoteAddress` that is NOT
`127.0.0.1`, so Camofox's loopback exception does not trigger and an API key is required.
With `--network host`, the container shares the host's network stack and `remoteAddress`
is correctly `127.0.0.1`.

### Persistent Startup Command (with volume mounts)
```bash
mkdir -p ~/.camofox-docker/{profiles,camoufox}

docker run -d --name camofox-browser --restart unless-stopped --network host \
  -e NODE_ENV=development \
  -v /home/hoonsoropenclaw/.camofox-docker/profiles:/root/.camofox/profiles \
  -v /home/hoonsoropenclaw/.camofox-docker/camoufox:/root/.camoufox \
  camofox-browser:135.0.1-x86_64
```

**Persistent volumes**:
- `~/.camofox-docker/profiles` → `/root/.camofox/profiles` (browser profiles, cookies)
- `~/.camofox-docker/camoufox` → `/root/.camoufox` (camoufox configuration)

**Do NOT mount cache** (`~/.camofox-docker/cache` → `/root/.cache`): The camoufox binary
(~713MB) is downloaded on each startup if not cached, which takes ~2-3 minutes.
Mounting cache causes the pre-warm to fail because the host's cache directory has wrong
ownership after a container restart. Let camoufox re-download on each start.

### Building the Image
```bash
cd ~/camofox-browser
make build    # Builds camofox-browser:135.0.1-x86_64
make up       # Runs the container (edit Makefile's run: target to add --network host)
```

---

## Cookie Import Workflow

### Step 1: Export Cookies from Chrome

1. Install the **Cookie-Editor** Chrome extension
2. Navigate to the target site (e.g., Google)
3. Click Cookie-Editor → "Export" → "Export as JSON"
4. Copy the JSON content

### Step 2: Convert Cookie Format

Camofox's API expects a different format than Cookie-Editor's export.

**Cookie-Editor format** (not directly usable):
```json
{
  "domain": ".google.com",
  "expirationDate": 1814369476.990356,
  "hostOnly": false,
  "httpOnly": false,
  "name": "SID",
  "path": "/",
  "sameSite": null,
  "secure": true,
  "session": false,
  "storeId": null,
  "value": "..."
}
```

**Camofox API format** (required):
```json
{
  "cookies": [
    {
      "name": "SID",
      "value": "...",
      "domain": ".google.com",
      "path": "/",
      "expires": 1814369476.990356,
      "httpOnly": true,
      "secure": true
    }
  ]
}
```

Conversion rules:
- `expirationDate` → `expires`
- `httpOnly`, `secure` pass through as-is
- `sameSite`, `hostOnly`, `session`, `storeId` are omitted
- All cookies wrapped in `{"cookies": [...]}`

### Step 3: Create Camofox Tab and Import

```bash
# Create a tab
TAB_RESPONSE=$(curl -s -X POST http://localhost:9377/tabs \
  -H "Content-Type: application/json" \
  -d '{"userId": "hermes", "sessionKey": "google-main", "url": "https://www.google.com"}')
TAB_ID=$(echo $TAB_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['tabId'])")

# Import cookies
curl -s -X POST "http://localhost:9377/sessions/$TAB_ID/cookies" \
  -H "Content-Type: application/json" \
  -d @/path/to/converted_cookies.json
```

Expected response: `{"ok":true,"userId":"...","count":26}`

---

## Camofox API Reference

### Health Check
```bash
curl -s http://localhost:9377/health
# Returns: {"ok":true,"engine":"camoufox","browserConnected":true,"browserRunning":true}
```

### List Tabs
```bash
curl -s "http://localhost:9377/tabs?userId=hermes"
```

### Navigate a Tab
```bash
curl -s -X POST "http://localhost:9377/tabs/$TAB_ID/navigate" \
  -H "Content-Type: application/json" \
  -d '{"userId": "hermes", "url": "https://www.google.com/account"}'
```

### Get Tab Snapshot
```bash
curl -s "http://localhost:9377/tabs/$TAB_ID/snapshot?userId=hermes"
```

### Delete Tab
```bash
curl -s -X DELETE "http://localhost:9377/tabs/$TAB_ID?userId=hermes"
```

---

## Hermes Configuration

### config.yaml (browser section)
```yaml
browser:
  engine: auto
  camofox:
    managed_persistence: false
    user_id: hermes
    session_key: google-main
    adopt_existing_tab: false
    rewrite_loopback_urls: false
    loopback_host_alias: host.docker.internal
```

### .env (alternative via env vars)
```
CAMOFOX_URL=http://localhost:9377
CAMOFOX_USER_ID=hermes
CAMOFOX_SESSION_KEY=google-main
CAMOFOX_ADOPT_EXISTING_TAB=false
```

Note: `~/.hermes/config.yaml` and `~/.hermes/.env` are protected files.
Write to them using `patch` with exact old_string matching, or set via env vars.

---

## VNC Remote Access (noGUI Linux)

Camofox can be accessed remotely via VNC when running on a headless N100 Linux machine.

### How it works

Camofox launches a virtual framebuffer (Xvfb) instead of a real display.
x11vnc + websockify expose this virtual display as:
- **VNC**: port `5900`
- **noVNC web**: port `6080/vnc.html` (browser-based, works from any device)

### Startup sequence

```bash
# Xvfb :136 + x11vnc + websockify
export DISPLAY=:136
x11vnc -display :136 -rfbport 5900 -shared -forever -bg
websockify --web=/usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900
```

The container's `start.sh` should auto-launch these; verify:
```bash
ss -tlnp | grep -E "5900|6080"
# Expected: 0.0.0.0:5900 (x11vnc) and 0.0.0.0:6080 (websockify)
```

### Connection options

**Direct VNC** (from Windows VNC Viewer):
```
100.88.38.80:5900
```

**Browser-based** (no VNC Viewer needed):
```
http://100.88.38.80:6080/vnc.html
```

**SSH tunnel** (if firewall blocks direct access):
```powershell
ssh -L 5900:localhost:5900 -L 6080:localhost:6080 hoonsoropenclaw@100.88.38.80
# Then connect VNC Viewer to localhost:5900
```

If SSH tunnel fails with `channel open failed: Connection refused`, the VNC services
on the host may not be running. Start them manually:
```bash
export DISPLAY=:136
x11vnc -display :136 -rfbport 5900 -shared -forever &
websockify --web=/usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900 &
```

### VNC in camofox.config.json

Edit `/app/camofox.config.json` inside the container to enable:
```json
{
  "vnc": {
    "enabled": true,
    "resolution": "1920x1080"
  }
}
```

Restart the container after editing: `docker restart camofox-browser`

### Firewall check

If direct VNC/noVNC fails, check if ports are blocked:
```bash
# On N100, test locally first
curl http://localhost:6080/vnc.html
# If local works but remote doesn't → firewall issue

# On Windows, test connectivity
Test-NetConnection -ComputerName 100.88.38.80 -Port 5900
Test-NetConnection -ComputerName 100.88.38.80 -Port 6080
```

### Keep session alive

Xvfb display :136 may go idle and close the browser. Keep a tab active:
```bash
# Navigate to Google periodically to prevent idle timeout
curl -s -X POST "http://localhost:9377/tabs/$TAB_ID/navigate" \
  -H "Content-Type: application/json" \
  -d '{"userId": "hermes", "url": "https://www.google.com"}'
```

---

## Alternative: nodriver（Chrome 系目標）

Camofox 是 Firefox 系。對於 Chrome 系目標且需要最高隱蔽性，nodriver 是更強的選擇：

- **Benchmark**：31 個 Cloudflare 目標零封鎖（標準 Playwright 大量失敗）
- **原理**：直接用 CDP（Chrome DevTools Protocol）溝通，繞過 WebDriver binary
- **基本用法**：
```python
import nodriver as driver
import asyncio

async def main():
    browser = await driver.start()
    tab = await browser.get("https://target-site.com")
    elem = await tab.find("input[name='q']", timeout=5)
    await elem.type("search query")

asyncio.run(main())
```

**安裝方式**（2026-06 更新）：
```bash
# 方法1：建立獨立 venv（推薦，避免 PEP 668 限制）
python3 -m venv /tmp/nodriver-env
/tmp/nodriver-env/bin/pip install nodriver

# 方法2：系統 python3 有 PEP 668 限制，需要額外處理
/usr/bin/python3 -m pip install nodriver  # 會失敗，見下面說明
```

**常見問題**：
- 赫米斯的 venv（`~/.hermes/hermes-agent/venv/bin/python3`）沒有 pip，請用上面的 venv 方式
- 系統 python3（`/usr/bin/python3`，Python 3.12）在 Ubuntu 24.04 有 PEP 668 `externally-managed-environment` 限制
  - 不要用 `--break-system-packages`，會破壞系統 Python
  - 正確做法是建立獨立 venv（如上）
- nodriver 需要系統有 Chrome/Chromium 可執行檔。若無，agent-browser 是替代方案

**何時用 nodriver vs Camofox**：
- Chrome 系 + anti-bot 嚴格 → nodriver（需有 Chrome）
- Firefox 系 + 已有 Camofox 部署 → Camofox
- 快速任務 + 無 anti-bot → agent-browser（已安裝，見 browser/agent-browser）

---

## Pitfalls

1. **Bridge network (`-p`) breaks loopback auth**: Always use `--network host`.
   - See `references/camofox-debug-notes.md` for the detailed root-cause analysis of this issue.
2. **Mounting cache volume breaks camoufox pre-warm**: Do NOT mount `/root/.cache`.
   Camoufox downloads ~713MB on each launch. If the host cache directory has wrong ownership
   (from a previous container run), the pre-warm fails with
   "Version information not found at /root/.cache/camoufox/version.json".
   Let camoufox re-download on each startup — it's fast enough (~2-3 min).
3. **Cookies disappear on container restart**: Mount `~/.camofox-docker/profiles` to
   `/root/.camofox/profiles` for persistence across restarts.
4. **All endpoints require `userId`**: Every API call needs `?userId=xxx` or body param.
5. **Tab ID = Session ID**: The tab ID returned from `POST /tabs` is used as the session ID
   for subsequent cookie/snapshot operations.
6. **`sameSite` not supported in Camofox format**: Omit it from converted cookies.
7. **Camofox server binds to all interfaces with `--network host`**: The API is exposed on
   `0.0.0.0:9377`. This is fine for local use; do not expose port 9377 externally without
   setting `CAMOFOX_API_KEY`.
8. **Browser engine disconnects (`browserConnected: false`)**: The camoufox browser process can crash independently of the API server process. The API server stays alive (`docker ps` shows container running) but `browserConnected` becomes false. Detected reactively (task fails) unless watchdog is deployed. **Recovery**: `docker restart camofox-browser` + wait 2-3 min. See `references/camofox-session-recovery.md`.
9. **Watchdog only restarts Docker, not the browser process — `browserConnected: false` persists**: The deployed watchdog (`/tmp/camofox-watchdog.sh`) does `docker restart camofox-browser`, but the browser engine (`camoufox-bin`) runs as a **standalone process outside Docker**. The Docker container only holds the Node.js API server. Restarting Docker restarts the API server, which then relaunches the browser as a child process — so Docker restart **indirectly** fixes it. However, if the browser keeps crashing, the root cause is likely the `browserIdleTimeout` (5-min idle → shutdown) or memory pressure. **Full diagnosis**: `ps aux | grep camoufox-bin` to check if browser process is alive; `docker logs camofox-browser` for crash traces. See `references/watchdog-docker-only-fallacy.md` (2026-06-12).
10. **Watchdog script permission issue (cron runs as root, skill dir is 0700)**: The script at `skills/browser/camofox/scripts/camofox-watchdog.sh` is owned by `hoonsoropenclaw` with `drwx------` (0700). Cron runs as root which cannot enter the `.hermes` directory. **Fix**: Copy to `/tmp/camofox-watchdog.sh` and update crontab:
   ```bash
   cp ~/.hermes/skills/browser/camofox/scripts/camofox-watchdog.sh /tmp/camofox-watchdog.sh
   chmod +x /tmp/camofox-watchdog.sh
   # Rewrite script to be self-contained (no hermes path refs)
   # Update crontab: * * * * * /tmp/camofox-watchdog.sh >> /tmp/camofox-watchdog.log 2>&1
   ```
10. **SKILL.md exists ≠ skill is operational**: A complete SKILL.md file means nothing if the underlying environment variables are commented out in `.env` or the service is unhealthy. Always verify: (1) SKILL.md exists, (2) `.env` vars are uncommented with valid values, (3) service health check passes. All three must be true.

---

## Verification

```bash
# Step 1: Verify container is running
docker ps | grep camofox

# Step 2: Verify browser engine is connected (MANDATORY)
curl -s http://localhost:9377/health | python3 -m json.tool
# Expected: browserConnected: true, browserRunning: true
# If false: docker restart camofox-browser && sleep 180

# Step 3: Verify tabs are accessible
curl -s "http://localhost:9377/tabs?userId=hermes" | python3 -m json.tool

# Step 4: Cookie import success — check response for "count": N
```

---

## YouTube Authentication — Critical Lesson

**Cookie import success ≠ login success** for YouTube. This is the #1 failure mode.

### YouTube Login ≠ Google Login (CRITICAL)

YouTube and Google are **separate login systems**. Even if logged into Google.com, YouTube.com shows "Sign in" until you log into YouTube specifically. The `LOGIN_INFO` cookie only appears after a manual YouTube.com sign-in.

**To get `LOGIN_INFO`**: Connect via VNC to N100, navigate to `youtube.com` (not `google.com`), click "Sign in" and complete YouTube's separate flow, then **immediately** extract cookies.sqlite before any restart.

### The IP Mismatch Problem

YouTube rejects cookies when the IP that created them differs from the IP using them. This is NOT a Camofox bug — it's YouTube fraud detection.

**Workarounds**:
1. **Residential proxy** matching the cookie origin IP
2. **Direct login on N100** via VNC (fresh cookies = no IP mismatch)
3. **Bypass SPA caching** with `?disable_polymer=1` query param

### Verify Login Status (don't trust SPA UI)

```bash
# Check LOGIN_INFO cookie is present (LOGIN_INFO is HttpOnly — never in document.cookie)
curl http://localhost:9377/tabs/$TAB_ID/cookies?domain=.youtube.com

# Or query storage-state.json directly
cat ~/.camofox-docker/profiles/$PROFILE_HASH/storage-state.json | python3 -m json.tool | grep -i LOGIN_INFO
```

### Cookie Import vs Actual Login — Root Cause Table

| Root cause | Symptom | Fix |
|------------|---------|-----|
| IP geolocation mismatch | valid cookies, login still fails | Use proxy or login on N100 |
| YouTube ≠ Google login | LOGIN_INFO missing from cookies.sqlite | Manual YouTube.com sign-in |
| LOGIN_INFO is HttpOnly | not in `document.cookie` | Check cookies.sqlite / storage-state.json directly |
| SPA cache | stale "Sign in" button text | Add `?disable_polymer=1` to URL |

Full session log with LOGIN_INFO format spec: `references/youtube-cookie-import-2026-05-31.md`.

---

## VNC vs Browser API Session Separation (CRITICAL)

**VNC and the browser tool API operate on DIFFERENT sessions** — this is the #1 cause of "VNC shows black screen" confusion:

- **VNC** → shows the raw Xvfb framebuffer (the visible `about:blank`, stale page, or empty desktop of the VNC session)
- **Browser API** → operates on its own isolated Playwright context with full automation control

A page loaded via the API (`browser_navigate`) is **NOT visible** in VNC, and vice versa. Camofox's `server.js` calls `newContext()` for each new tab, creating a brand-new isolated context that does NOT share cookies, localStorage, or IndexedDB with other contexts.

### The Login State Paradox

If VNC shows YouTube logged in but `browser_navigate` shows "NOT LOGGED IN" — this is **EXPECTED**, not a bug. Both VNC and `browser_navigate` may show different login states because they have independent cookie jars in `/tmp/playwright_firefoxdev_profile-XXXXXX/`.

**If you need consistent login state**:
- Use the API exclusively (navigate, click, fill via API calls) — OR —
- Use VNC exclusively for manual browsing
- Do NOT expect them to share cookies or login state

### Diagnostic checklist

```bash
# Step 1: API health
curl http://localhost:9377/health

# Step 2: Active tabs
curl "http://localhost:9377/tabs?userId=hermes"

# Step 3: VNC processes
ps aux | grep -E 'x11vnc|websockify' | grep -v grep

# Step 4: Xvfb display in use
docker exec camofox-browser ps aux | grep Xvfb
# Look for /usr/bin/Xvfb :NNN -screen 0 1920x1080x24
```

### Common VNC patterns

| Pattern | Meaning | Action |
|---------|---------|--------|
| VNC black + API works | VNC and API are different sessions | Normal — use API |
| VNC black + X cursor (mouse cross) | Browser idle-shutdown completed | Set `browserIdleTimeoutMs: 2592000000` and restart |
| VNC black + black cursor (no X) | Early-stage idle-shutdown, before X appears | Same as above |
| VNC shows logged in, API shows logged out | Independent cookie jars | Expected — use one interface only |

Full diagnostic guide: `references/vnc-debugging.md`.

---

### OAuth on N100 Headless — Complete Recipe (CRITICAL)

**Problem**: Running OAuth flow (e.g. YouTube, Google) on N100 is painful because:
- N100 is headless → no browser, no VNC desktop
- Google OAuth requires user to click "Allow" in a real browser
- "未加密連線" warning in noVNC is normal (no SSL), NOT a bug
- "VNC shows black screen + API works" is normal (different sessions — see VNC vs API section above)

**Three OAuth strategies, in order of preference**:

#### Strategy 1: Device Code Flow (BEST for N100, 5 min setup)

Google supports this for **"TV and limited-input devices"** OAuth client type. Zero browser, zero VNC, zero SSH tunnel. User just types a code in their own Chrome.

**What works on Device Code Flow** (verified 2026-06-07):
| Scope | Device Flow? |
|-------|-------------|
| `youtube.readonly` | ✅ |
| `openid`, `email`, `profile` | ✅ |
| `subscriptions.readonly` | ❌ invalid |
| `youtube.force-ssl` | ❌ invalid |

**Setup steps**:
1. Google Cloud Console → APIs & Services → Credentials → Create OAuth client
2. **Application type: "TV and limited-input devices"** (NOT "Desktop" / "Web")
3. Download JSON → move to `~/.local/share/hermes/secrets/<name>_client.json`
4. **MUST add test users** at OAuth consent screen (otherwise "Access blocked")
5. Run device code script (see `scripts/youtube_oauth_device.py` template below)
6. Script prints `https://www.google.com/device` + `user_code` (e.g. `RVL-HBW-BHR`)
7. User opens URL in their own browser, enters code, clicks Allow
8. Script polls `/token` endpoint every 5s, saves tokens when user authorizes

**Polling loop gotcha**: Google returns **HTTP 428** with `authorization_pending` (NOT 200). Don't `raise_for_status()` — branch on status code:
```python
if resp.status_code == 200:
    tokens = resp.json()  # success
elif resp.status_code in (400, 428):
    err = resp.json().get('error', '')
    if err in ('authorization_pending', 'slow_down'):
        continue  # still waiting
    elif err == 'access_denied':
        break  # user refused
```

**Device Code Flow will 401 if client type is "Desktop / Computer app"** — even though Google downloads both as `{"installed": {...}}` JSON. The JSON structure is identical; the difference is in the **consent screen / API console settings**, not the file. Must recreate client as TV type.

**Background process stdout gotcha** (Hermes-specific): If running device code polling via `terminal(background=true)`, `process.log()` may NOT show output mid-loop because the Hermes background pipe buffer doesn't flush on partial-line prints. **Always write polling progress to a log file** (`/tmp/oauth_poll.log`) and tail it from a separate terminal call. The script must `open(..., 'a').write() + flush()` after each line, not just `print()`.

#### Strategy 2: Localhost redirect with HTTP server (FALLBACK if you must use Desktop client type)

Requires:
- User can reach a port on N100 from their browser (SSH tunnel or open firewall)
- HTTP server in script listens on `localhost:8765` for OAuth callback
- User authorizes in their browser → Google redirects to `http://localhost:8765/?code=...` → script captures code → exchanges for tokens

**Why this fails on N100 out of the box**:
- N100 port 8765 not reachable from Windows by default (firewall blocks)
- SSH tunnel (`ssh -L 8765:localhost:8765`) is the standard fix
- noVNC web UI shows "未加密連線" warning that confuses users but is benign (no SSL)
- VNC shows "black screen" because VNC sees Xvfb framebuffer (empty), but Playwright API uses its own context — the two don't share state

#### Strategy 3: RSS / public API (NO auth needed)

If you only need **channel new videos** (not user subscriptions), use YouTube's public RSS:
```
https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxx
```
No auth, no client, no tokens. User provides channel_id list manually.

**When to use which**:
- Need user-specific data (subscriptions, watch history, playlists) → Strategy 1 (Device Code)
- Already have Desktop client type, can't recreate → Strategy 2 (Localhost)
- Only need public channel feeds → Strategy 3 (RSS)

### Black Screen on VNC — Idle Shutdown Fix (CRITICAL)

**Symptom**: VNC connects but shows black screen with cross cursor (mouse X).

**Root cause**: Browser idle-shutdown after 5 minutes of no active sessions (default `browserIdleTimeoutMs: 300000`).

**Fix**:
1. Edit `/app/camofox.config.json` inside the container, add:
   ```json
   {
     "browserIdleTimeoutMs": 2592000000
   }
   ```
2. Restart container: `docker restart camofox-browser`
3. vnc-watcher auto-starts x11vnc connected to the current Xvfb display

**Prevention**: Keep at least one session/tab alive at all times. Periodically navigate a tab to a non-trivial URL to prevent idle timeout:
```bash
curl -s -X POST "http://localhost:9377/tabs/$TAB_ID/navigate" \
  -H "Content-Type: application/json" \
  -d '{"userId": "hermes", "url": "https://www.google.com"}'
```

---

## Xvfb Display Number Is Dynamic (NOT :161)

On N100 setups, Camofox's `vnc-watcher` dynamically assigns Xvfb displays on each container restart — `:161` is **NOT** a fixed value. After container restart:

- First restart: `:203`
- Second restart: `:180`
- Always verify with: `docker exec camofox-browser ps aux | grep Xvfb`

All Firefox content processes inherit this display. `x11vnc` must connect to the **current** display, not a hardcoded value:

```bash
# Find current Xvfb display
docker exec camofox-browser ps aux | grep Xvfb
# Output: /usr/bin/Xvfb :NNN -screen 0 1920x1080x24
#          ↑ this number changes on every restart

# Connect x11vnc to that display
export DISPLAY=:NNN   # use the number from above
x11vnc -display :NNN -rfbport 5900 -shared -forever -bg
websockify --web=/usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900
```

If x11vnc fails with "could not obtain listening port", the previous x11vnc instance is still running:
```bash
killall x11vnc
sleep 2
# then restart with the new display number
```

---

## Reference Files

- `references/watchdog-deployment-notes.md` — **（2026-06-06 新增）** Watchdog 部署完整 SOP：自包含腳本準備、0700 權限問題解決、crontab 部署步驟、驗證清單。watchdog script 存在 ≠ 真的在跑，完整部署需同時滿足 script 可執行 + cron 已部署 + 權限可達三條件。
- `references/camofox-persistence-notes.md` — Cache mount pitfall, persistence verification
  results, and updated Makefile run target with volume mounts.
- `references/camofox-debug-notes.md` — Root-cause analysis of the bridge-network loopback
  auth failure, with working cookie conversion script and Makefile fix.
- `references/camfox-url-config.md` — CAMFOX_URL vs CAMOFOX_URL naming, all 3 config methods
  (yaml/.env/shell), and common setup issues.
- `references/camfox-env-setup.md` — Environment variables (CAMFOX_URL, CAMFOX_API_KEY,
  CAMOUFOX_EXECUTABLE, NODE_ENV) and common errors table.
- `references/camofox-session-recovery.md` — Browser engine disconnect diagnosis, recovery
  procedure, and three active health monitoring options (docker-autoheal, custom watchdog
  script, simple cron). **Start here when `browserConnected: false`.**
- `references/vnc-debugging.md` — VNC + API session separation, the login-state paradox,
  diagnostic checklist, and common patterns.
- `references/youtube-cookie-import-2026-05-31.md` — YouTube cookie import session log with
IP-mismatch analysis and the critical finding: **YouTube Login ≠ Google Login**.
- `references/oauth-headless-recipe.md` — **(2026-06-07 新增)** Complete recipe for running Google OAuth on N100 headless server. Three strategies (Device Code Flow, Localhost Redirect, RSS), why VNC black screen happens, why Desktop client type fails Device Code, scope restrictions, test users trap, background process logging gotcha, full session log of the 2-hour YouTube OAuth debugging session.
- `scripts/camofox-watchdog.sh` — Production watchdog script for auto-restart on disconnect. Note: see `references/watchdog-docker-only-fallacy.md` for critical architectural note — Docker restart targets API server, not the browser process directly.
- `scripts/cookie-convert.py` — Python script to convert Cookie-Editor JSON export to
  Camofox API format. Run: `python3 scripts/cookie-convert.py cookies-export.json`.
- `scripts/youtube_oauth_device.py` — **(2026-06-07 新增)** Reusable YouTube OAuth template using Device Code Flow. Reads from `~/.local/share/hermes/secrets/youtube_client.json`, writes tokens to `~/.hermes/youtube_tokens.json`, writes progress to `/tmp/oauth_poll.log`. Adapted to N100 headless (no browser, no VNC needed). User just types a code in their own Chrome.