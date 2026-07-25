# Camofox Session Log — Cookie Import Debug Notes

## Problem: "This endpoint requires CAMOFOX_API_KEY"

### Symptom
Cookie import to `POST /sessions/:tabId/cookies` returned:
```
{"error":"This endpoint requires CAMOFOX_API_KEY except for loopback requests in non-production environments."}
```

Even though `NODE_ENV=development` was set and curl was running from localhost.

### Root Cause
Docker bridge network mode (`-p 9377:9377`) assigns the container an IP like `172.17.0.2`.
When the request reaches the container, `req.socket.remoteAddress` is the Docker bridge IP,
NOT `127.0.0.1`. Camofox's loopback check `address === '127.0.0.1'` fails, so it requires
an API key even in development mode.

### Fix
Use `--network host` instead of port mapping:
```bash
docker run -d --name camofox-browser --restart unless-stopped --network host \
  -e NODE_ENV=development \
  camofox-browser:135.0.1-x86_64
```

### Verification
```bash
# From INSIDE the container, check what address the server sees:
docker exec camofox-browser ss -tln | grep 9377
# Should show 0.0.0.0:9377 (not 127.0.0.1:9377 exclusively)

# Health should still be OK:
curl -s http://localhost:9377/health

# Cookie import should work without auth:
curl -s -X POST "http://localhost:9377/sessions/$TAB_ID/cookies" \
  -H "Content-Type: application/json" \
  -d @/tmp/cookies.json
```

---

## Cookie Format Conversion Script

```python
import json

with open('cookies_export.json', 'r') as f:
    cookies = json.load(f)

converted = []
for c in cookies:
    converted.append({
        "name": c.get("name", ""),
        "value": c.get("value", ""),
        "domain": c.get("domain", ""),
        "path": c.get("path", "/"),
        "expires": c.get("expirationDate", 0),
        "httpOnly": c.get("httpOnly", False),
        "secure": c.get("secure", False)
    })

output = json.dumps({"cookies": converted}, indent=2)
with open('/tmp/cookies_for_camofox.json', 'w') as f:
    f.write(output)

print(f"Converted {len(converted)} cookies")
```

---

## Google Cookie Import — Actual Values

Successfully imported 26 Google cookies for session `d8679c30-a141-44f9-9b52-7a55661939d6`.
After import, navigating to `https://www.google.com/account` redirected to Google Sign-In,
confirming the cookies contain authentication state.

Key cookies present: SID, HSID, SSID, SAPISID, APISID, NID, AEC, __Secure-1PSID*, __Secure-3PSID*

---

## Makefile Quick Fix (for future rebuilds)

Edit `~/camofox-browser/Makefile` `run:` target to add `--network host`:
```makefile
run:
	@if ! docker image inspect $(IMAGE) > /dev/null 2>&1; then \
	  $(MAKE) build; \
	fi
	docker run -d --restart unless-stopped --name camofox-browser --network host -e NODE_ENV=development $(IMAGE)
```