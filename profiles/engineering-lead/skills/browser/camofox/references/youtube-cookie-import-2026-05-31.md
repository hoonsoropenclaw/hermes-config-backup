# Camofox Session Notes — YouTube Cookie Import (2026-05-31, updated 2026-06-01)

## Environment
- N100 mini PC (100.88.38.80)
- Camofox Docker image: `camofox-browser:135.0.1-x86_64`
- Container: `camofox-browser` (network=host, NODE_ENV=development)

## CRITICAL FINDING: YouTube Login ≠ Google Login

**Even if logged into Google.com, YouTube.com still shows "Sign in".**

The user had successfully logged into Google.com multiple times (confirmed via VNC). Yet YouTube.com consistently showed "Sign in". LOGIN_INFO cookie never appeared in cookies.sqlite.

**Root cause**: Google login and YouTube login are **completely separate systems**. The LOGIN_INFO cookie for YouTube only appears after:
1. Navigating specifically to `youtube.com` (not `google.com`)
2. Completing YouTube's own sign-in flow (which may look similar to Google's but is separate)

**What this means for cookie debugging**:
- If cookies.sqlite has 5 YouTube cookies but NO LOGIN_INFO → user logged into Google but never YouTube
- LOGIN_INFO cookie size: ~319 chars, httpOnly, secure, sameSite=none
- YouTube.com page state is cached by Google's SPA — refreshing or checking "Sign in" button text is unreliable

**Action**: For YouTube cookies to work, user must manually log into YouTube.com (not Google.com) on the target machine. Export cookies IMMEDIATELY after successful YouTube login, before any browser restart.

---

## Earlier Session Findings (2026-05-31)

### YouTube Cookie Import Results

**What Worked**
- Cookies successfully imported via Camofox API → stored in `storage-state.json`
- LOGIN_INFO cookie (319 chars) present in storage-state.json
- Camofox health check returns all `true`

**What Didn't Work**
- YouTube shows "Sign in" despite valid LOGIN_INFO cookie
- **Root cause**: IP geolocation mismatch (cookies created on Windows PC IP, used from N100 IP)
- SPA navigation caching causes stale page state on `youtube.com`

### LOGIN_INFO Format (from Chrome cookies)
```
LOGIN_INFO=AFmmF2swRQIgLU4yDZuPkGaf1HMQ7OQj4Yrn9...:QUQ3MjNmeXIzdlVqNjVmdnZ6dDA5aUNyX0kxM2pnR29tYzRCb0dzMGJHdUl4Ym9OOTJPbkRPby0zeE5IWDNiMTVsbUdGanlPREFKWUJlblZzd2xySkJxVnFhRWd1Wm5td3NROFZndk03MHF6ZEtub0NTZWViaW5Bb3pUc0M4SVd0Ti1hNGIyMGphZ0p0S0RhVG5NZFozOWtyZnF3SE1tWG9B
```
Format: `signature:base64url-encoded-data` — both parts are URL-safe base64.

### Verified Working Approaches
1. Navigate to direct channel URLs: `youtube.com/channel/{id}?disable_polymer=1`
2. Check `storage-state.json` directly for LOGIN_INFO presence (not `document.cookie` which hides HttpOnly cookies)

### Profile IDs Created
- YouTube profile: `510e18edc14023b175e33138a9232a65` (userId: `hermes-youtube`)
- Google profile: `5d8d4865-29ca-4949-8dab-1b8f43322940`

### Camofox Health Response
```json
{"ok":true,"running":true,"browserConnected":true,"browserRunning":true}
```

## VNC Setup on N100

### Status (2026-05-31)
- x11vnc: listening on `0.0.0.0:5900`
- websockify: listening on `0.0.0.0:6080`
- Xvfb display: `:161`
- noVNC path: `/usr/share/novnc/vnc.html`

### Manual start commands (if auto-start fails)
```bash
export DISPLAY=:161
x11vnc -display :161 -rfbport 5900 -shared -forever &
websockify --web=/usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900 &
```

### Connection test
```bash
# Local test on N100
curl http://localhost:6080/vnc.html   # Should return HTML

# Remote test from Windows
Test-NetConnection -ComputerName 100.88.38.80 -Port 5900
Test-NetConnection -ComputerName 100.88.38.80 -Port 6080
```

### SSH tunnel troubleshooting
`channel 3: open failed: connect failed: Connection refused` = VNC service not running on N100.
Start it manually (see above). Direct VNC (`100.88.38.80:5900`) bypasses this issue.

### noVNC browser URL
```
http://100.88.38.80:6080/vnc.html
```

## Key Lesson

**Cookie import success ≠ Login success** when IP address changes. YouTube's fraud detection rejects sessions from IPs different from where cookies were created. Workarounds:
1. Residential proxy matching cookie origin IP
2. Manual login on N100 to create fresh cookies
3. Accept limitation and use cookie method only for IPs that match origin

**CRITICAL NEW FINDING (2026-06-01)**: YouTube login ≠ Google login. Even when a user has logged into Google.com, YouTube.com still shows "Sign in" until YouTube-specific login is completed. The LOGIN_INFO cookie **never appears** from Google login alone — it only exists after a separate YouTube.com login flow.

If cookies.sqlite shows only 5 YouTube cookies with no LOGIN_INFO, the user logged into Google but never YouTube. Direct VNC login on N100 is the only guaranteed path to real LOGIN_INFO cookies.