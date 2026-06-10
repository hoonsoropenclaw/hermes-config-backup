#!/usr/bin/env python3
"""
YouTube OAuth - Device Code Flow Template
=========================================

Reusable template for any Google API OAuth on N100 headless server.

Usage:
  1. Create OAuth client in Google Cloud Console as "TV and limited-input devices"
  2. Download JSON to ~/.local/share/hermes/secrets/<name>_client.json
  3. Add test user (your Google email) at OAuth consent screen
  4. Run: python3 this_script.py

Verified: 2026-06-07 (YouTube Data API v3, scope=youtube.readonly)
"""

import json
import os
import sys
import time
import requests

# ────────────────────────────────────────
# Configuration
# ────────────────────────────────────────
SECRETS_FILE = os.path.expanduser("~/.local/share/hermes/secrets/youtube_client.json")
TOKEN_FILE = os.path.expanduser("~/.hermes/youtube_tokens.json")
LOG_FILE = "/tmp/oauth_poll.log"

# ⚠️ Device Code Flow scope restrictions (verified):
#    youtube.readonly    ✅
#    subscriptions.readonly ❌ (use youtube.readonly instead, covers subscriptions.list)
#    youtube.force-ssl      ❌
#    openid/email/profile   ✅
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
]

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"


# ────────────────────────────────────────
# Logging (file-based, NOT stdout — see SKILL.md gotcha)
# ────────────────────────────────────────
def log(msg):
    """Write to log file with flush. Hermes background pipe doesn't flush print()."""
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")
        f.flush()


def reset_log():
    with open(LOG_FILE, "w") as f:
        f.write("")


# ────────────────────────────────────────
# OAuth Steps
# ────────────────────────────────────────
def load_oauth_config():
    if not os.path.exists(SECRETS_FILE):
        log(f"❌ Missing: {SECRETS_FILE}")
        sys.exit(1)
    with open(SECRETS_FILE) as f:
        data = json.load(f)
    installed = data.get("installed", data)
    return {
        "client_id": installed["client_id"],
        "client_secret": installed["client_secret"],
        "project_id": installed.get("project_id", "?"),
    }


def request_device_code(client_id, scopes):
    resp = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": " ".join(scopes)},
    )
    resp.raise_for_status()
    return resp.json()


def poll_for_token(client_id, client_secret, device_code, interval, expires_in):
    deadline = time.time() + expires_in
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        time.sleep(interval)
        remaining = int(deadline - time.time())
        log(f"   [{attempt:3d}] 等待中... 剩 {remaining:3d} 秒")

        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                timeout=15,
            )
        except Exception as e:
            log(f"   ⚠️  network error: {e}")
            continue

        if resp.status_code == 200:
            return resp.json()

        # ⚠️ Google returns HTTP 428 (not 200) for authorization_pending
        if resp.status_code in (400, 428):
            try:
                err = resp.json().get("error", "")
            except Exception:
                err = ""
            if err in ("authorization_pending", "slow_down"):
                if err == "slow_down":
                    interval += 5
                continue
            elif err == "expired_token":
                log("❌ Device code expired")
                sys.exit(1)
            elif err == "access_denied":
                log("❌ User denied access")
                sys.exit(1)
            else:
                log(f"❌ {err}: {resp.text[:200]}")
                sys.exit(1)

        log(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")
        sys.exit(1)
    log("❌ Timed out")
    sys.exit(1)


def save_tokens(tokens):
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    tokens["obtained_at"] = time.time()
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(TOKEN_FILE, 0o600)
    log(f"✅ Tokens saved: {TOKEN_FILE} (mode 600)")


def verify_and_list_subscriptions(access_token):
    """Verify token works and list first 20 subscriptions."""
    log("\n🔍 Verifying token...")
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet", "mine": "true", "maxResults": 5},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if r.status_code == 200:
        items = r.json().get("items", [])
        for it in items:
            log(f"   頻道: {it['snippet']['title']} (ID: {it['id']})")
    else:
        log(f"   ⚠️  channels.list: HTTP {r.status_code}")

    log("\n📺 Fetching subscriptions (first 20)...")
    r2 = requests.get(
        "https://www.googleapis.com/youtube/v3/subscriptions",
        params={"part": "snippet", "mine": "true", "maxResults": 20},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if r2.status_code == 200:
        subs = r2.json().get("items", [])
        log(f"   Found {len(subs)} subscriptions:")
        for s in subs:
            log(f"   - {s['snippet']['title']} ({s['snippet']['resourceId']['channelId']})")
    else:
        log(f"   subscriptions.list: HTTP {r2.status_code}")


# ────────────────────────────────────────
# Main
# ────────────────────────────────────────
def main():
    reset_log()
    log("=" * 60)
    log("YouTube OAuth - Device Code Flow")
    log("=" * 60)

    config = load_oauth_config()
    log(f"\nClient: {config['client_id'][:50]}...")
    log(f"Project: {config['project_id']}")

    device = request_device_code(config["client_id"], SCOPES)
    user_code = device["user_code"]
    device_code = device["device_code"]
    interval = device.get("interval", 5)
    expires_in = device.get("expires_in", 1800)
    verification_url = device.get("verification_url", "https://www.google.com/device")

    log("\n" + "=" * 60)
    log("📱 在你的 Windows Chrome 做這件事：")
    log("=" * 60)
    log(f"  網址：  {verification_url}")
    log(f"  代碼：  {user_code}")
    log("  動作：  選帳號 + 輸入代碼 + 按 [允許]")
    log("=" * 60)
    log("")

    tokens = poll_for_token(
        config["client_id"],
        config["client_secret"],
        device_code,
        interval,
        expires_in,
    )

    save_tokens(tokens)
    verify_and_list_subscriptions(tokens["access_token"])


if __name__ == "__main__":
    main()
