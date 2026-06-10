#!/usr/bin/env python3
"""
YouTube OAuth 認證腳本
- 從 ~/.local/share/hermes/secrets/youtube_client.json 讀 OAuth 設定
- 跑 OAuth flow (port 8765)
- 把 tokens 存到 ~/.hermes/youtube_tokens.json
- 自動列出訂閱 + 查新影片

更新日期：2026-06-07 (改用 secrets JSON)
"""

import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode
import requests

# ────────────────────────────────────────
# 設定
# ────────────────────────────────────────
SECRETS_FILE = os.path.expanduser("~/.local/share/hermes/secrets/youtube_client.json")
TOKEN_FILE = os.path.expanduser("~/.hermes/youtube_tokens.json")
CHANNELS_FILE = os.path.expanduser("~/.hermes/cache/youtube/channels.json")
REDIRECT_URI = "http://localhost:8765"
PORT = 8765

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/subscriptions.readonly",
]


def load_client_config():
    """從 JSON 讀 client_id / client_secret"""
    if not os.path.exists(SECRETS_FILE):
        print(f"❌ 找不到 {SECRETS_FILE}")
        print(f"請先把 client_secret_*.json 放到該位置")
        sys.exit(1)
    data = json.loads(open(SECRETS_FILE).read())
    if "installed" not in data:
        print(f"❌ JSON 不是 'installed' 類型（電腦應用程式）")
        print(f"   看到的是: {list(data.keys())}")
        sys.exit(1)
    installed = data["installed"]
    return {
        "client_id": installed["client_id"],
        "client_secret": installed["client_secret"],
        "project_id": installed.get("project_id", "?"),
    }


# ────────────────────────────────────────
# OAuth Handler
# ────────────────────────────────────────
class OAuthHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        if "code=" in self.path:
            query = self.path.split("?", 1)[1]
            params = dict(p.split("=") for p in query.split("&"))
            OAuthHandler.auth_code = params.get("code")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;padding:40px;text-align:center'>"
                b"<h1 style='color:green'>&#10004; Authorization Successful!</h1>"
                b"<p>You may close this window and return to the terminal.</p>"
                b"</body></html>"
            )
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code")

    def log_message(self, format, *args):
        pass


def get_auth_url(client_id):
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"


def exchange_code_for_tokens(code, client_id, client_secret):
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=30)
    return r.json()


def refresh_access_token(refresh_token, client_id, client_secret):
    data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=30)
    return r.json()


def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
    os.chmod(TOKEN_FILE, 0o600)
    print(f"✅ Tokens 已儲存到 {TOKEN_FILE} (權限 600)")


def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None


# ────────────────────────────────────────
# YouTube API
# ────────────────────────────────────────
def get_subscriptions(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    subscriptions = []
    next_page = "https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=50"
    while next_page:
        r = requests.get(next_page, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"❌ 訂閱 API 錯誤：{r.status_code} - {r.text[:200]}")
            return subscriptions
        data = r.json()
        for item in data.get("items", []):
            channel = item["snippet"]
            subscriptions.append({
                "channel_id": channel["resourceId"]["channelId"],
                "title": channel["title"],
                "description": channel.get("description", ""),
            })
        next_page = data.get("nextPageToken")
        if next_page:
            next_page = f"https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=50&pageToken={next_page}"
        else:
            next_page = None
    return subscriptions


def get_channel_uploads_playlist_id(channel_id, access_token):
    """取得頻道的 'uploads' playlist ID（用來查最新影片）"""
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "contentDetails", "id": channel_id},
        headers=headers, timeout=30
    )
    if r.status_code != 200:
        return None
    items = r.json().get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_playlist_videos(playlist_id, access_token, max_results=3):
    """取得 playlist 內最新影片"""
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        params={
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": max_results,
        },
        headers=headers, timeout=30
    )
    if r.status_code != 200:
        return []
    items = r.json().get("items", [])
    videos = []
    for item in items:
        snippet = item["snippet"]
        videos.append({
            "video_id": snippet["resourceId"]["videoId"],
            "title": snippet["title"],
            "published_at": snippet["publishedAt"],
            "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}",
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
        })
    return videos


def filter_ai_channels(subscriptions):
    ai_keywords = [
        "ai", "artificial", "intelligence", "machine", "learning", "deep learning",
        "neural", "gpt", "llm", "openai", "anthropic", "google deepmind",
        "nvidia", "hugging face", "langchain", "automation", "agent",
        "python", "tech", "coding", "programming", "tutorial",
    ]
    ai_channels = []
    for sub in subscriptions:
        title_lower = sub["title"].lower()
        desc_lower = sub["description"].lower()
        for kw in ai_keywords:
            if kw in title_lower or kw in desc_lower:
                ai_channels.append(sub)
                break
    return ai_channels


# ────────────────────────────────────────
# Main
# ────────────────────────────────────────
def main():
    print("=" * 60)
    print("YouTube OAuth 認證 + 訂閱查詢")
    print("=" * 60)

    cfg = load_client_config()
    print(f"\n📋 OAuth 用戶端: {cfg['client_id'][:40]}...")
    print(f"📋 專案: {cfg['project_id']}")
    print(f"📋 Redirect URI: {REDIRECT_URI}")

    # ─── 1. 確認 / 取得 tokens ───
    tokens = load_tokens()

    if tokens and "refresh_token" in tokens:
        print("\n📁 發現已儲存的 tokens，嘗試刷新...")
        new = refresh_access_token(tokens["refresh_token"], cfg["client_id"], cfg["client_secret"])
        if "access_token" in new:
            print("✅ Access token 刷新成功")
            tokens["access_token"] = new["access_token"]
            if "expires_in" in new:
                tokens["expires_in"] = new["expires_in"]
            if "refresh_token" not in new and "refresh_token" in tokens:
                new["refresh_token"] = tokens["refresh_token"]
            tokens.update(new)
            save_tokens(tokens)
        else:
            print(f"❌ Refresh 失敗: {new}")
            print("   需要重新走 OAuth flow")
            tokens = None

    if not tokens or "access_token" not in tokens:
        print("\n🔗 開始 OAuth flow...")
        url = get_auth_url(cfg["client_id"])
        print(f"\n請在瀏覽器中訪問：\n  {url}\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass

        server = HTTPServer(("localhost", PORT), OAuthHandler)
        print(f"🔥 HTTP 伺服器運行中 ({REDIRECT_URI})")
        print("📌 授權完成後，此視窗會自動繼續...")
        server.handle_request()

        if not OAuthHandler.auth_code:
            print("❌ 沒收到 authorization code")
            sys.exit(1)

        print("\n🔑 收到 authorization code，交換 tokens...")
        tokens = exchange_code_for_tokens(
            OAuthHandler.auth_code, cfg["client_id"], cfg["client_secret"]
        )
        if "access_token" not in tokens:
            print(f"❌ Token 交換失敗: {tokens}")
            sys.exit(1)
        save_tokens(tokens)

    # ─── 2. 抓訂閱 ───
    print("\n" + "=" * 60)
    print("📺 取得訂閱頻道中...")
    print("=" * 60)
    subscriptions = get_subscriptions(tokens["access_token"])
    print(f"\n📊 總共訂閱了 {len(subscriptions)} 個頻道")

    # ─── 3. 分類 AI 相關 ───
    ai_channels = filter_ai_channels(subscriptions)
    print(f"🤖 其中 {len(ai_channels)} 個可能與 AI 有關")

    # ─── 4. 儲存 channels ───
    with open(CHANNELS_FILE, "w") as f:
        json.dump({
            "all": subscriptions,
            "ai_related": ai_channels,
            "fetched_at": time.time(),
        }, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 頻道列表已儲存到 {CHANNELS_FILE}")

    # ─── 5. 查最新影片（前 5 個 AI 頻道示範）───
    print("\n" + "=" * 60)
    print("🎬 查最新影片（AI 相關頻道前 5 個）")
    print("=" * 60)
    for ch in ai_channels[:5]:
        pl_id = get_channel_uploads_playlist_id(ch["channel_id"], tokens["access_token"])
        if not pl_id:
            print(f"\n  ❌ {ch['title']}: 找不到 uploads playlist")
            continue
        videos = get_playlist_videos(pl_id, tokens["access_token"], max_results=2)
        print(f"\n  📺 {ch['title']}")
        for v in videos:
            print(f"     • {v['title']}")
            print(f"       {v['url']} ({v['published_at']})")

    print("\n🎉 完成！")


if __name__ == "__main__":
    main()
