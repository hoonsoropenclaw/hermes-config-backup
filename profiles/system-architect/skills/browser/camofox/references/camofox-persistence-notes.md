# Camofox Persistence Setup Notes (2026-05-31)

## Problem: Cookies Disappeared After Container Restart

**Symptom**: After `docker stop` + `docker start`, previously imported cookies were gone.
The browser profile was stored inside the container's `/root/.camofox/profiles/` which is
ephemeral.

**Solution**: Mount host directories as volumes to persist browser data across restarts.

## Persistent Startup Command

```bash
mkdir -p ~/.camofox-docker/{profiles,camoufox}

docker run -d --name camofox-browser --restart unless-stopped --network host \
  -e NODE_ENV=development \
  -v /home/hoonsoropenclaw/.camofox-docker/profiles:/root/.camofox/profiles \
  -v /home/hoonsoropenclaw/.camofox-docker/camoufox:/root/.camoufox \
  camofox-browser:135.0.1-x86_64
```

## Volume Mounts

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `~/.camofox-docker/profiles` | `/root/.camofox/profiles` | Browser profiles (cookies, sessions) |
| `~/.camofox-docker/camoufox` | `/root/.camoufox` | Camoufox configuration |

## Cache Mount Pitfall — DO NOT MOUNT /root/.cache

**Problem**: Initially tried to mount `~/.camofox-docker/cache` → `/root/.cache`.

**Result**: Pre-warm failed with:
```
"Version information not found at /root/.cache/camoufox/version.json.
Please run `camoufox fetch` to install."
```

**Root cause**: When the container first ran without the cache mount, it created
`/root/.cache/` owned by root inside the container. When we later tried to mount
the host's `~/.camofox-docker/cache/` (which was also created by root), Docker created
new files inside the mounted directory with root ownership, making them unreadable by
the camoufox process running as a different user.

**Workaround**: Do not mount cache. Let camoufox re-download on each startup (~2-3 min).

## Verification Results

After `docker restart camofox-browser`:

1. **Profiles survived**: `~/.camofox-docker/profiles/` retained the
   `8da9bc670425101e670f0e6b89eb99e1/` profile directory
2. **Cookies persisted**: Re-import was NOT needed after restart
3. **Camoufox binary re-downloaded**: Took ~2-3 minutes in background, browser came up fine

## Running Without loginctl enable-linger

If `loginctl enable-linger` has not been run, Docker containers do not auto-start on boot.
To enable:

```bash
sudo loginctl enable-linger $(whoami)
```

This allows user-level services (including Docker containers with `--restart unless-stopped`)
to start at boot without a user login.

## Updated Makefile run target

The `~/camofox-browser/Makefile` `run:` target should be updated to:
```makefile
run:
	@if ! docker image inspect $(IMAGE) > /dev/null 2>&1; then \
	  $(MAKE) build; \
	fi
	mkdir -p ~/.camofox-docker/{profiles,camoufox}
	docker run -d --restart unless-stopped --name camofox-browser --network host \
	  -e NODE_ENV=development \
	  -v /home/hoonsoropenclaw/.camofox-docker/profiles:/root/.camofox/profiles \
	  -v /home/hoonsoropenclaw/.camofox-docker/camoufox:/root/.camoufox \
	  $(IMAGE)
```