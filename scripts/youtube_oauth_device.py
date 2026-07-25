#!/usr/bin/env python3
"""
YouTube OAuth - Device Code Flow 版本
=====================================

不需要瀏覽器、不需要 HTTP server、不需要 VNC、SSH tunnel。

流程：
1. 從 ~/.local/share/hermes/secrets/youtube_client.json 讀 OAuth 設定
2. 呼叫 Google Device Code endpoint 拿 user_code + device_code
3. 印出 user_code + verification URL 給使用者
4. 使用者在自己電腦的瀏覽器打開 URL + 輸入 user_code + 授權
5. 赫米斯輪詢 token endpoint 拿到 access_token + refresh_token
6. 存到 ~/.hermes/youtube_tokens.json

參考：
- https://developers.google.com/identity/oauth2/web/guides/use-code-model
- https://developers.google.com/identity/oauth2/limited-input-device

更新：2026-06-07（改用 Device Code Flow，N100 headless 可用）
"""

import json
import os
import sys
import time
import requests

# ────────────────────────────────────────
# 設定
# ────────────────────────────────────────
SECRETS_FILE = os.path.expanduser("~/.local/share/hermes/secrets/youtube_client.json")
TOKEN_FILE = os.path.expanduser("~/.hermes/youtube_tokens.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/subscriptions.readonly",
]

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# ────────────────────────────────────────
# 主流程
# ────────────────────────────────────────

def load_oauth_config():
    """從 youtube_client.json 讀 client_id / client_secret"""
    if not os.path.exists(SECRETS_FILE):
        print(f"❌ 找不到 OAuth 設定檔: {SECRETS_FILE}")
        print("   請把從 Google Cloud 下載的 client_secret_*.json 放到該位置")
        sys.exit(1)

    with open(SECRETS_FILE) as f:
        data = json.load(f)

    # 「installed」應用程式類型
    installed = data.get("installed", data)
    return {
        "client_id": installed["client_id"],
        "client_secret": installed["client_secret"],
        "project_id": installed.get("project_id", "unknown"),
    }


def request_device_code(client_id, scopes):
    """向 Google 請求 device code + user code"""
    resp = requests.post(DEVICE_CODE_URL, data={
        "client_id": client_id,
        "scope": " ".join(scopes),
    })
    resp.raise_for_status()
    return resp.json()


def poll_for_token(client_id, client_secret, device_code, interval, expires_in):
    """輪詢直到使用者授權完成"""
    print(f"\n⏳ 開始輪詢 Google token endpoint（每 {interval} 秒）...")
    print(f"   Token 將在 {expires_in} 秒後過期")
    deadline = time.time() + expires_in

    while time.time() < deadline:
        time.sleep(interval)
        remaining = int(deadline - time.time())
        print(f"   等待授權中...（剩餘 {remaining} 秒）", end="\r")

        resp = requests.post(TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 400:
            err = resp.json().get("error", "")
            if err == "authorization_pending":
                continue  # 使用者還沒按允許
            elif err == "slow_down":
                interval += 5  # Google 要我們慢一點
                continue
            elif err == "expired_token":
                print("\n❌ Device code 過期了，請重新執行")
                sys.exit(1)
            elif err == "access_denied":
                print("\n❌ 使用者拒絕授權")
                sys.exit(1)
            else:
                print(f"\n❌ 未知錯誤: {err}")
                print(f"   Response: {resp.text}")
                sys.exit(1)
        else:
            print(f"\n❌ HTTP {resp.status_code}: {resp.text}")
            sys.exit(1)

    print("\n❌ 等待超時，請重新執行")
    sys.exit(1)


def save_tokens(tokens, token_file):
    """把 tokens 存到 json 檔"""
    # 加上過期時間戳
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    tokens["obtained_at"] = time.time()

    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=2)

    # 設定檔案權限 600
    os.chmod(token_file, 0o600)
    print(f"\n✅ Tokens 已存到: {token_file}")
    print(f"   權限: mode 600 (僅擁有者可讀寫)")


def verify_tokens(access_token):
    """用 access token 抓用戶自己的 YouTube 頻道清單驗證"""
    print(f"\n🔍 驗證 tokens...")
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={
            "part": "snippet",
            "mine": "true",
            "maxResults": 1,
            "access_token": access_token,
        },
    )
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", [])
        if items:
            channel = items[0]
            title = channel["snippet"]["title"]
            print(f"✅ 驗證成功！你的 YouTube 頻道: {title}")
            return True
        else:
            print("✅ Token 有效（但你可能沒有 YouTube 頻道）")
            return True
    else:
        print(f"❌ 驗證失敗: {resp.status_code} {resp.text}")
        return False


def main():
    print("=" * 60)
    print("YouTube OAuth - Device Code Flow")
    print("=" * 60)

    # 1. 讀設定
    print(f"\n📋 讀取 OAuth 設定: {SECRETS_FILE}")
    config = load_oauth_config()
    print(f"   Client ID: {config['client_id'][:40]}...")
    print(f"   Project: {config['project_id']}")
    print(f"   Scopes: {len(SCOPES)} 個")

    # 2. 請求 device code
    print(f"\n🔗 向 Google 請求 Device Code...")
    device_data = request_device_code(config["client_id"], SCOPES)
    user_code = device_data["user_code"]
    verification_url = device_data["verification_url"]
    device_code = device_data["device_code"]
    interval = device_data.get("interval", 5)
    expires_in = device_data.get("expires_in", 1800)

    # 3. 印出使用者要做的步驟
    print("\n" + "=" * 60)
    print("📱 接下來請你在 你自己的瀏覽器（Windows Chrome / Edge）做這件事：")
    print("=" * 60)
    print(f"\n  第 1 步：打開網址")
    print(f"          👉  {verification_url}")
    print(f"\n  第 2 步：Google 會問你登入帳號（用你要授權的那個 YouTube 帳號）")
    print(f"\n  第 3 步：輸入這組代碼")
    print(f"          👉  {user_code}")
    print(f"\n  第 4 步：選你要給的權限範圍 + 按 [允許]")
    print(f"\n  這裡可以關掉視窗。赫米斯會自動偵測到你按了允許。")
    print("=" * 60)

    # 4. 輪詢 token
    print(f"\n⏳ 等待你授權...")
    tokens = poll_for_token(
        config["client_id"],
        config["client_secret"],
        device_code,
        interval,
        expires_in,
    )

    # 5. 存 tokens
    save_tokens(tokens, TOKEN_FILE)

    # 6. 驗證
    if verify_tokens(tokens["access_token"]):
        print("\n" + "=" * 60)
        print("🎉 全部完成！你現在可以用赫米斯查 YouTube 訂閱了")
        print("=" * 60)
        print(f"\n接下來可以跑：")
        print(f"  python3 ~/.hermes/scripts/youtube_oauth_device.py --list-subs")
    else:
        print(f"\n⚠️  Tokens 存了但驗證失敗，請手動確認")


if __name__ == "__main__":
    main()
