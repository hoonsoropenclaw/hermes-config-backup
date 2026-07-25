# Camofox Session Recovery & Health Monitoring Guide

## Problem: Browser Engine Disconnected

### Symptom
```json
{
  "ok": true,
  "browserConnected": false,
  "browserRunning": false,
  "activeTabs": 0,
  "activeSessions": 0
}
```

Even though the Docker container is running (`docker ps | grep camofox` shows `Up`), the camoufox engine inside has disconnected or failed to pre-warm.

### Root Cause
Camoufox pre-warm requires downloading a ~713MB binary on first launch. If `/root/.cache` is mounted from the host (via `-v ~/.camofox-docker/camoufox:/root/.camoufox`), the host cache directory may have wrong ownership after a container restart, causing the pre-warm to fail silently.

**This is NOT the same as the loopback auth issue** (which was fixed by `--network host`). This is a browser engine failure inside a running container.

### Recovery Procedure

```bash
# Step 1: Verify the disconnect
curl -s http://localhost:9377/health | python3 -m json.tool
# Expected: browserConnected: false, browserRunning: false

# Step 2: Restart the container (preserves profiles volume mount)
docker restart camofox-browser

# Step 3: Wait 2-3 minutes for camoufox pre-warm
sleep 180

# Step 4: Verify recovery
curl -s http://localhost:9377/health | python3 -m json.tool
# Expected: browserConnected: true, browserRunning: true

# Step 5: If authentication needed, re-import cookies
# (See SKILL.md Cookie Import Workflow)
```

---

## Production-Grade Health Monitoring (Recommended)

The recovery procedure above is reactive — it only helps AFTER the engine has already disconnected. For a headless browser that should be available 24/7, deploy **active health monitoring** that detects and fixes disconnects automatically, before they impact user tasks.

### Option A: docker-autoheal (Simplest, Production-Recommended)

This watches Docker's native HEALTHCHECK status and restarts any unhealthy container automatically. It requires zero custom scripts and works for all containers with a healthcheck defined.

**Step 1: Add a healthcheck to the camofox container**
```bash
docker update \
  --health-cmd "curl -f http://localhost:9377/health 2>/dev/null | grep -q 'browserConnected.*true' || exit 1" \
  --health-interval=60s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=180s \
  camofox-browser
```

**Step 2: Start the autoheal watcher**
```bash
docker run -d \
  --name autoheal \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  willfarrell/autoheal

# Verify it's running
docker ps | grep autoheal
```

**How it works**: autoheal polls Docker every 5 seconds, checks which containers have a `health_status=unhealthy` status, and calls `docker restart` on them. The camofox container's `curl -f ...` healthcheck command runs every 60 seconds — if it fails 3 consecutive times, Docker marks the container `unhealthy`, and autoheal restarts it.

**Advantages over cron-based watchdog**:
- Native Docker integration — no custom scripts or crontab entries
- Works for ALL containers with healthcheck defined, not just camofox
- autoheal container itself is stateless and restarts on failure
- Health status visible via `docker ps --format "{{.Names}} {{.Status}}"`

### Option B: Custom Watchdog Script (More Flexible)

Use this when you need custom logging, alerting, or conditional logic beyond simple restart.

**Script**: `scripts/camofox-watchdog.sh`
```bash
#!/bin/bash
# Camofox Health Watchdog — checks every minute
# Restarts the container if browserConnected is false, with logging

HEALTH=$(curl -s --max-time 5 http://localhost:9377/health 2>/dev/null)
if [ -z "$HEALTH" ]; then
  # API unreachable — container may be down
  logger -t camofox-watchdog "API unreachable, restarting container"
  docker restart camofox-browser
  exit
fi

if echo "$HEALTH" | grep -q '"browserConnected":false'; then
  logger -t camofox-watchdog "browserConnected=false, restarting camofox-browser"
  docker restart camofox-browser
fi
```

**Install**:
```bash
chmod +x ~/.hermes/skills/browser/camofox/scripts/camofox-watchdog.sh
# Add to crontab
(crontab -l 2>/dev/null; echo "* * * * * /home/hoonsoropenclaw/.hermes/skills/browser/camofox/scripts/camofox-watchdog.sh") | crontab -
```

**View logs**: `tail -f /var/log/syslog | grep camofox-watchdog`

### Option C: Simple Cron (Minimal)

For a quick check without any additional containers:
```bash
# Check every 10 minutes, restart if browser is down
*/10 * * * * curl -s http://localhost:9377/health | grep -q '"browserRunning":true' || docker restart camofox-browser
```

**Limitation**: No logging when a restart fires, no alerting, no visibility into why it restarted.

---

## Why NOT Mounting Cache Breaks Pre-warm

| Scenario | Pre-warm Result |
|----------|-----------------|
| No cache mount | camoufox downloads ~713MB on each startup →2-3 min wait but works |
| Host cache mount with wrong ownership | Pre-warm fails silently → browserConnected: false |
| Correct cache mount | Rarely works because container restart changes ownership |

**Conclusion**: Do NOT mount `~/.camofox-docker/camoufox` to `/root/.camoufox`. Let camoufox re-download each time. The download is fast enough (~2-3 min) and avoids ownership issues.

### External References

- **GitHub Issue #20507** (NousResearch/hermes-agent): "Session closed unexpectedly when use camofox as browser tool" — confirms session is lost after AI task completes
- **GitHub Issue #15645** (openclaw/openclaw): "Persist browser cookies/sessions across managed browser restarts" — CDP does not flush cookies to SQLite on disk; cookies exist only in memory
- **willfarrell/docker-autoheal** (GitHub ~15k stars): Production-grade container health monitor — https://github.com/willfarrell/docker-autoheal

### Differential: Loopback Auth vs. Browser Engine Disconnect

| Symptom | Cause | Fix |
|---------|-------|-----|
| `{"error":"This endpoint requires CAMOFOX_API_KEY..."}` | Bridge network (`-p`) instead of `--network host` | Use `--network host` |
| `browserConnected: false, browserRunning: false` | Cache mount ownership issue OR camoufox pre-warm failure | Restart container, do NOT mount cache |
| `consecutiveFailures: N` (high count) | Repeated connection failures | Check container logs: `docker logs camofox-browser` |
