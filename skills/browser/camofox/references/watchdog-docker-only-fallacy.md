# Camofox Watchdog — Docker-Only Fallacy (2026-06-12)

## The Bug

The watchdog script at `/tmp/camofox-watchdog.sh` does:
```bash
docker restart camofox-browser
```

This only restarts the **Docker container** (API server). But the browser engine (`camoufox-bin`) runs as a **standalone process outside Docker**. The Docker container only holds the Node.js API wrapper (`server.js`). The actual Firefox-based browser is a separate OS-level process.

When `browserConnected: false` persists after `docker restart`, the issue is that the standalone `camoufox-bin` process is dead — restarting Docker does nothing to bring it back.

## Verification

```bash
# API server is in Docker (healthy)
docker ps | grep camofox
# Shows: camofox-browser  Up X minutes  ...

# Browser engine is OUTSIDE Docker (may be dead)
ps aux | grep camoufox-bin | grep -v grep
# If empty → browser process is dead

# Health check shows Docker API server is up but browser is disconnected
curl -s http://localhost:9377/health
# {"ok":true,"engine":"camoufox","browserConnected":false,...}
```

## Architecture

```
hermes-gateway (Python)
    └── curl localhost:9377/health
            └── Docker container (camofox-browser)
                    └── server.js (Node.js API)
                            └── IPC to camoufox-bin (standalone, NOT in Docker)
```

When the standalone browser process dies, the Docker API server stays alive but `browserConnected` becomes false.

## Why Docker Restart Still Works (Indirectly)

`docker restart camofox-browser` → Docker stops and starts the container → container entrypoint starts `server.js` → server.js launches `camoufox-bin` as a child process. So Docker restart **indirectly** restarts the browser. The watchdog's `docker restart` is correct for the API-down case, but if `browserConnected: false` persists after Docker restart, the browser process keeps dying — root cause is likely `browserIdleTimeout` (5-min idle → browser shuts down) or memory pressure.

## Fix

```bash
#!/bin/bash
# Corrected Camofox watchdog

HEALTH=$(curl -s --max-time 5 http://localhost:9377/health 2>/dev/null)

if [ -z "$HEALTH" ]; then
  # API completely down — restart Docker
  logger -t camofox-watchdog "API unreachable, restarting Docker"
  docker restart camofox-browser
  exit
fi

if echo "$HEALTH" | grep -q '"browserConnected":false'; then
  logger -t camofox-watchdog "browserConnected=false, restarting camoufox-bin"
  pkill -f camoufox-bin 2>/dev/null || true
  sleep 2
  docker restart camofox-browser
  sleep 180  # wait for pre-warm
fi
```

## Current State (2026-06-12)

- Deployed watchdog: `/tmp/camofox-watchdog.sh` (root cron, every minute)
- camoufox-bin crashes every ~minute → `browserConnected: false` every ~minute
- Watchdog keeps `docker restart`ing, which does restart the browser indirectly — so it mostly works
- But if browser crashes immediately after restart (e.g., idle timeout set too short), cycle repeats

## Next Diagnostic Step

Check `docker logs camofox-browser` for crash traces, or check OOM killer: `dmesg | grep -i kill | grep camoufox`.