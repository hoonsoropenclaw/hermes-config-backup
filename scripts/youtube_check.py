#!/usr/bin/env python3
"""
YouTube 工具包：OAuth Device Code Flow + RSS Feed 抓取
=====================================================

兩個主要功能：
1. **OAuth 認證**（device code flow，headless 可用）
   - 你只需要在自己電腦的瀏覽器打 https://www.google.com/device + 輸入 user_code + 選帳號
   - 赫米斯在 N100 自動 polling 收 tokens + 存檔
2. **抓 YouTube 訂閱頻道新影片**（用公開 RSS feed，**不需 OAuth**）
   - 給定 channel_id 清單 → 抓每個頻道最新影片
   - 不消耗 YouTube API quota
   - 一行 curl 就能跑

## 必要環境
- Python 3.11+
- `requests` 套件（hermes venv 已裝）
- **OAuth client 必須是「TV 和 limited-input devices」類型**（不是電腦應用程式）

## 檔案路徑
- OAuth client JSON: `~/.local/share/hermes/secrets/youtube_client.json`（mode 600）
- OAuth tokens: `~/.hermes/youtube_tokens.json`（mode 600）
- 訂閱清單: `~/.hermes/youtube_subscriptions.json`（手動或從 API 抓）

## 用法
```bash
# 1. 跑 OAuth（首次使用、或 token 過期）
python3 ~/.hermes/scripts/youtube_check.py oauth

# 2. 抓你的 YouTube 訂閱清單（用 OAuth token）
python3 ~/.hermes/scripts/youtube_check.py fetch-subs

# 3. 抓所有訂閱頻道最新影片（用公開 RSS，不需 OAuth）
python3 ~/.hermes/scripts/youtube_check.py fetch-rss

# 4. 抓單一頻道 RSS
python3 ~/.hermes/scripts/youtube_check.py fetch-rss UCATnB3v_NkTTd9iD_4W2A-g
```

## 設計原則（給未來的赫米斯看）
- **誠實**：抓不到就說抓不到，不偽造資料
- **簡單**：用 Python 標準庫優先，feedparser 不需要
- **可重複執行**：每次跑都是冪等（idempotent）的
- **可離線工作**：OAuth 失敗時，RSS 部分仍能跑

## 更新
- 2026-06-07 建立（Hermes Agent 從 OpenClaw 試誤經驗整理）
"""

import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

# ────────────────────────────────────────
# 設定
# ────────────────────────────────────────
SECRETS_FILE = Path("~/.local/share/hermes/secrets/youtube_client.json").expanduser()
TOKEN_FILE = Path("~/.hermes/youtube_tokens.json").expanduser()
SUBS_FILE = Path("~/.hermes/youtube_subscriptions.json").expanduser()

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# Device Code Flow 合法 scope（其他會被 Google 擋）
VALID_DEVICE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "openid",
    "email",
    "profile",
]

# RSS feed template
RSS_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# ATOM XML namespace
ATOM = "{http://www.w3.org/2005/Atom}"


# ────────────────────────────────────────
# 工具函式
# ────────────────────────────────────────
def log(msg, end="\n"):
    print(msg, end=end, flush=True)


def load_oauth_config():
    """讀 OAuth client JSON"""
    if not SECRETS_FILE.exists():
        log(f"❌ 找不到 OAuth 設定: {SECRETS_FILE}")
        log("   請從 Google Cloud Console 下載 client_secret_*.json 放這個路徑")
        sys.exit(1)
    with open(SECRETS_FILE) as f:
        data = json.load(f)
    installed = data.get("installed", data)
    return {
        "client_id": installed["client_id"],
        "client_secret": installed["client_secret"],
        "project_id": installed.get("project_id", "unknown"),
    }


def save_tokens(tokens):
    """存 tokens + 設 mode 600"""
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    tokens["obtained_at"] = time.time()
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(TOKEN_FILE, 0o600)
    log(f"✅ Tokens 已存: {TOKEN_FILE} (mode 600)")


def load_tokens():
    """讀 tokens（如果存在）"""
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


def get_valid_access_token():
    """拿到一個有效的 access token（過期就自動 refresh）"""
    tokens = load_tokens()
    if not tokens:
        log("❌ 沒有 tokens，請先跑 `python3 youtube_check.py oauth`")
        sys.exit(1)

    # 還有 5 分鐘以上就不 refresh
    if tokens.get("expires_at", 0) > time.time() + 300:
        return tokens["access_token"]

    # refresh
    if not tokens.get("refresh_token"):
        log("❌ 沒有 refresh_token，請重跑 OAuth")
        sys.exit(1)

    config = load_oauth_config()
    log(f"🔄 Refreshing access token...")
    resp = requests.post(TOKEN_URL, data={
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    })
    if resp.status_code != 200:
        log(f"❌ Refresh 失敗: HTTP {resp.status_code}")
        log(f"   {resp.text[:300]}")
        log("   解決：重跑 `python3 youtube_check.py oauth`")
        sys.exit(1)

    new_tokens = resp.json()
    # 保留舊的 refresh_token（refresh response 通常不包含新 refresh_token）
    new_tokens["refresh_token"] = new_tokens.get("refresh_token") or tokens["refresh_token"]
    save_tokens(new_tokens)
    return new_tokens["access_token"]


# ────────────────────────────────────────
# OAuth Device Code Flow
# ────────────────────────────────────────
def cmd_oauth():
    """跑 OAuth Device Code Flow"""
    log("=" * 60)
    log("YouTube OAuth - Device Code Flow")
    log("=" * 60)

    config = load_oauth_config()
    log(f"\n📋 Client ID: {config['client_id']}")
    log(f"   Project: {config['project_id']}")

    # 申請 device code
    log("\n🔗 請求 device code...")
    resp = requests.post(DEVICE_CODE_URL, data={
        "client_id": config["client_id"],
        "scope": VALID_DEVICE_SCOPES[0],  # youtube.readonly
    })
    if resp.status_code != 200:
        log(f"❌ HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    device = resp.json()
    log(f"   拿到 device_code")

    user_code = device["user_code"]
    verification_url = device["verification_url"]
    device_code = device["device_code"]
    interval = device.get("interval", 5)
    expires_in = device.get("expires_in", 1800)

    log("\n" + "=" * 60)
    log("📱 立刻去你電腦的瀏覽器：")
    log("=" * 60)
    log(f"  1. 打開：{verification_url}")
    log(f"  2. 輸入：{user_code}")
    log(f"  3. 選帳號 + 按 [允許]")
    log("=" * 60)
    log(f"\n⏳ 開始 polling（每 {interval} 秒，30 分鐘內有效）...")

    # Polling
    deadline = time.time() + expires_in
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        time.sleep(interval)
        remaining = int(deadline - time.time())
        log(f"   [{attempt:3d}] 等待中... 剩 {remaining:3d} 秒", end="\r")

        try:
            r = requests.post(TOKEN_URL, data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }, timeout=15)
        except Exception as e:
            log(f"\n   ⚠️  網路錯誤: {e}")
            continue

        if r.status_code == 200:
            tokens = r.json()
            save_tokens(tokens)
            log(f"\n\n✅ OAuth 成功！")
            log(f"   refresh_token: {'✅' if tokens.get('refresh_token') else '❌'}")
            log(f"   scope: {tokens.get('scope')}")
            return

        if r.status_code in (400, 403, 428):
            try:
                err = r.json().get("error", "")
            except Exception:
                err = ""

            if err == "authorization_pending":
                continue
            elif err == "slow_down":
                interval += 5
                log(f"\n   ⏸️  slow_down → 間隔改 {interval} 秒")
                continue
            elif err == "access_denied":
                log(f"\n\n❌ 你按了 [拒絕]")
                sys.exit(1)
            else:
                log(f"\n\n❌ 錯誤: {err} - {r.text[:200]}")
                sys.exit(1)

        log(f"\n\n❌ HTTP {r.status_code}: {r.text[:200]}")
        sys.exit(1)

    log(f"\n\n❌ 等待超時（{expires_in}s）")
    sys.exit(1)


# ────────────────────────────────────────
# 抓 YouTube 訂閱清單（用 OAuth）
# ────────────────────────────────────────
def cmd_fetch_subs():
    """抓你 YouTube 帳號的訂閱頻道清單，存成 JSON"""
    log("📺 抓 YouTube 訂閱清單...")

    access_token = get_valid_access_token()
    log(f"   Token 有效")

    subs = []
    next_page_token = None
    while True:
        params = {
            "part": "snippet",
            "mine": "true",
            "maxResults": 50,
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        r = requests.get(
            f"{YOUTUBE_API_BASE}/subscriptions",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if r.status_code != 200:
            log(f"❌ HTTP {r.status_code}: {r.text[:200]}")
            sys.exit(1)

        data = r.json()
        for item in data.get("items", []):
            subs.append({
                "channel_id": item["snippet"]["resourceId"]["channelId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"].get("description", ""),
            })

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    # 存
    SUBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUBS_FILE, "w") as f:
        json.dump({
            "subscriptions": subs,
            "count": len(subs),
            "fetched_at": time.time(),
        }, f, indent=2, ensure_ascii=False)

    log(f"\n✅ 抓到 {len(subs)} 個訂閱")
    log(f"   存到: {SUBS_FILE}")
    for sub in subs[:10]:
        log(f"   - {sub['title']} ({sub['channel_id']})")
    if len(subs) > 10:
        log(f"   ... 還有 {len(subs) - 10} 個")


# ────────────────────────────────────────
# 抓 RSS（不需 OAuth）
# ────────────────────────────────────────
def fetch_channel_rss(channel_id, max_entries=3):
    """抓單一頻道的最新影片（公開 RSS）"""
    url = RSS_FEED_URL.format(channel_id=channel_id)
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

    try:
        root = ET.fromstring(resp.content)
    except Exception as e:
        return None, f"XML 解析失敗: {e}"

    entries = []
    for entry in root.findall(f"{ATOM}entry")[:max_entries]:
        title_el = entry.find(f"{ATOM}title")
        link_el = entry.find(f"{ATOM}link")
        pub_el = entry.find(f"{ATOM}published")
        author_el = entry.find(f"{ATOM}author/{ATOM}name")

        title = title_el.text if title_el is not None else "?"
        link = link_el.attrib.get("href", "?") if link_el is not None else "?"
        pub = pub_el.text if pub_el is not None else ""
        author = author_el.text if author_el is not None else "?"

        # 算幾天前
        days_ago = "?"
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            delta = (datetime.now(timezone.utc) - dt).days
            days_ago = f"{delta} 天前" if delta > 0 else "今天"
        except Exception:
            pass

        entries.append({
            "title": title,
            "url": link,
            "published": pub,
            "days_ago": days_ago,
            "author": author,
        })

    return entries, None


def cmd_fetch_rss(channel_id=None):
    """抓所有訂閱頻道（從 SUBS_FILE）或單一頻道 RSS"""
    if channel_id:
        channels = [{"channel_id": channel_id, "title": channel_id}]
    else:
        if not SUBS_FILE.exists():
            log(f"❌ 找不到訂閱清單: {SUBS_FILE}")
            log(f"   請先跑 `python3 youtube_check.py fetch-subs`")
            log(f"   或傳 channel_id: `python3 youtube_check.py fetch-rss UCxxxxx`")
            sys.exit(1)
        with open(SUBS_FILE) as f:
            data = json.load(f)
        channels = data["subscriptions"]

    log("=" * 70)
    log(f"📺 抓 {len(channels)} 個頻道最新影片（公開 RSS）")
    log("=" * 70)

    total = 0
    for ch in channels:
        cid = ch["channel_id"]
        title = ch.get("title", cid)
        entries, err = fetch_channel_rss(cid, max_entries=3)
        if err:
            log(f"\n❌ {title}: {err}")
            continue

        log(f"\n📺 {title}")
        for entry in entries:
            log(f"   • [{entry['days_ago']}] {entry['title']}")
            log(f"     {entry['url']}")
            total += 1

    log(f"\n{'=' * 70}")
    log(f"✅ 共抓 {total} 支影片")
    log(f"   純公開 RSS，無 API quota 消耗")


# ────────────────────────────────────────
# Main
# ────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        log("用法：")
        log("  python3 youtube_check.py oauth         # 跑 OAuth（首次）")
        log("  python3 youtube_check.py fetch-subs    # 抓訂閱清單（需 OAuth）")
        log("  python3 youtube_check.py fetch-rss     # 抓所有訂閱 RSS（不需 OAuth）")
        log("  python3 youtube_check.py fetch-rss <channel_id>  # 抓單一頻道")
        sys.exit(1)

    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "oauth":
        cmd_oauth()
    elif cmd == "fetch-subs":
        cmd_fetch_subs()
    elif cmd == "fetch-rss":
        cmd_fetch_rss(channel_id=arg)
    else:
        log(f"❌ 未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
