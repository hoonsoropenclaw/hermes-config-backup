# CAMFOX / CAMOFOX Configuration Guide

## Naming: CAMFOX vs CAMOFOX

- `CAMFOX_URL` — the HTTP endpoint of the Camofox API server (port 9377)
- `CAMOFOX_URL` — same thing, historically the name was `camofox` but user shortened to `CAMFOX`
- Both names work as aliases; Hermes resolves them to the same internal key

## Setting CAMFOX_URL

### Method 1: config.yaml (preferred, persistent)

Edit `~/.hermes/config.yaml`:
```yaml
browser:
  engine: auto
  camofox:
    managed_persistence: false
    url: http://localhost:9377
    user_id: hermes
    session_key: google-main
    adopt_existing_tab: false
    rewrite_loopback_urls: false
    loopback_host_alias: host.docker.internal
```

Note: The `url` key under `camofox:` is the same as `CAMFOX_URL`.

### Method 2: .env file

```bash
echo 'CAMFOX_URL=http://localhost:9377' >> ~/.hermes/env
echo 'CAMFOX_USER_ID=hermes' >> ~/.hermes/env
echo 'CAMFOX_SESSION_KEY=google-main' >> ~/.hermes/env
```

Note: `~/.hermes/.env` is a protected file — use `terminal` with `tee` or `echo >>` instead of direct write.

### Method 3: Shell environment (session-only)

```bash
export CAMFOX_URL=http://localhost:9377
export CAMFOX_USER_ID=hermes
export CAMFOX_SESSION_KEY=google-main
```

## Verifying Configuration

```bash
# Check Hermes config loads correctly
curl -s http://localhost:9377/health
# Expected: {"ok":true,"running":true,"browserConnected":true,"browserRunning":true}

# Check Camofox tabs (uses CAMFOX_USER_ID from config)
curl -s "http://localhost:9377/tabs?userId=hermes"
```

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CAMFOX_URL not found` in logs | Config key misspelled | Use `camofox.url` in YAML, not `camfox_url` |
| `userId required` error | `user_id` not set in config | Set `user_id: hermes` in config.yaml |
| Browser returns 401 | Using bridge network instead of `--network host` | Rebuild container with `--network host` |
| Health OK but cookies fail | `NODE_ENV=development` not set | Add `-e NODE_ENV=development` to docker run |

##camofox vs browser.engine

When `browser.engine: auto` is set, Hermes picks the available browser tool
automatically. The `camofox:` section under `browser:` provides connection details.

If you want to force Camofox:
```yaml
browser:
  engine: camofox
  camofox:
    url: http://localhost:9377
```