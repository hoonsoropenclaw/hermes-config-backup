#!/usr/bin/env python3
"""
OAuth 2.0 Device Authorization Grant — polling skeleton
========================================================

可重跑的 OAuth Device Code polling 骨架。N100 headless 環境**唯一乾淨**的 OAuth 解法。

## 為什麼需要這個腳本

N100 是 headless 伺服器（無瀏覽器、無 X server 可互動）。要在上面跑 OAuth：
- ❌ Localhost redirect URI flow（需要開 HTTP server 接 callback，瀏覽器要登入 Google 跳回）→ N100 跑不起來
- ❌ SSH tunnel + Windows Chrome 跑 OAuth → 麻煩、依賴 Windows
- ❌ noVNC + camofox 視覺化登入 → 黑畫面問題（見 browser-automation.md）
- ✅ **Device Code Flow** → 拿到 user_code，使用者**自己**的瀏覽器輸入 → callback 不需要瀏覽器

## 為什麼這個腳本存在

OAuth Device Code polling **有 3 個特殊 error code** 一定要正確處理（見 `secrets-and-env.md`）：

- `authorization_pending` → 使用者還沒按允許，**繼續 polling**
- `slow_down` → Google 要我放慢，**interval += 5，繼續 polling**（**不是錯！很多 script 誤判**）
- `access_denied` → 使用者按拒絕，**break**

加上：
- `interval` 預設 5 秒（太快會 rate limit）
- `expires_in` 預設 1800 秒（30 分鐘）
- **寫到 file log 而非 stdout**（避免 Hermes background tool 的 stdout buffer 問題）
- **舊的 device_code 會作廢**：重拿新的會讓前一個 user_code 立刻死掉（見 `secrets-and-env.md`）

## 使用方式

```bash
# 1. 確認有 OAuth client JSON（TV/limited-input 類型，**不是**電腦應用程式）
#    路徑：~/.local/share/hermes/secrets/<service>_client.json
#    結構：{"installed": {"client_id": "...", "client_secret": "...", ...}}

# 2. 跑這個腳本
python3 scripts/oauth_device_poll.py \
    --client-json ~/.local/share/hermes/secrets/youtube_client.json \
    --scope 'https://www.googleapis.com/auth/youtube.readonly' \
    --token-out ~/.hermes/youtube_tokens.json

# 3. 印出 user_code + verification URL → 給使用者

# 4. 使用者在自己電腦的瀏覽器（不是 N100）：
#    - 打開 https://www.google.com/device
#    - 輸入 user_code
#    - 選帳號 + 按 [允許]

# 5. 這個 script 自動 polling → 收到 200 → 存 tokens 到 --token-out
```

## 修改要點

要給新服務用：
1. 改 `--client-json` 路徑
2. 改 `--scope`（**只支援 4 個**：`youtube.readonly` / `openid` / `email` / `profile`，其他可能 `invalid_scope`）
3. 改 `--token-out` 輸出路徑

要看 polling 狀態：
```bash
tail -f /tmp/oauth_poll.log
```

更新：2026-06-07
"""

import argparse
import json
import os
import sys
import time

import requests

# ────────────────────────────────────────
# 常數
# ────────────────────────────────────────
DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"

LOG_FILE = "/tmp/oauth_poll.log"  # 寫到 file 而非 stdout（避開 Hermes background buffer 問題）


# ────────────────────────────────────────
# Log helper
# ────────────────────────────────────────

def log(msg, end="\n", flush=True):
    """寫一行到 LOG_FILE，**不要** print 到 stdout（background tool 看不到）"""
    with open(LOG_FILE, "a") as f:
        f.write(msg + end)
        if flush:
            f.flush()


def reset_log():
    with open(LOG_FILE, "w") as f:
        f.write("")


# ────────────────────────────────────────
# OAuth flow
# ────────────────────────────────────────

def load_client(path):
    if not os.path.exists(path):
        log(f"❌ 找不到 OAuth client JSON: {path}")
        sys.exit(1)
    with open(path) as f:
        d = json.load(f)
    installed = d.get("installed", d)  # "installed" 是 Desktop/TV/limited-input 都用的 wrapper
    return {
        "client_id": installed["client_id"],
        "client_secret": installed["client_secret"],
        "project_id": installed.get("project_id", "?"),
    }


def request_device_code(client_id, scope):
    """向 Google 拿 device_code + user_code"""
    log(f"向 Google 請求 device code (client_id={client_id[:40]}..., scope={scope})")
    resp = requests.post(DEVICE_CODE_URL, data={
        "client_id": client_id,
        "scope": scope,
    })
    log(f"  HTTP {resp.status_code}: {resp.text[:300]}")
    resp.raise_for_status()
    return resp.json()


def poll_for_token(client_id, client_secret, device_code, interval, expires_in):
    """Polling 直到拿到 tokens 或過期。**正確處理 slow_down 不是錯**。"""
    log("")
    log(f"⏳ 開始 polling (interval={interval}s, expires_in={expires_in}s)")
    deadline = time.time() + expires_in
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        time.sleep(interval)
        remaining = int(deadline - time.time())
        log(f"   [{attempt:3d}] 等待中... 剩 {remaining:3d} 秒")

        try:
            resp = requests.post(TOKEN_URL, data={
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }, timeout=15)
        except requests.RequestException as e:
            log(f"   ⚠️  網路錯誤: {e}，繼續 polling")
            continue

        # HTTP 200 = 成功（其他狀態碼都不是錯，是「等待中」）
        if resp.status_code == 200:
            return resp.json()

        # 400 / 403 / 428 都是「正常等待中」的 error code，**不要 raise_for_status**
        if resp.status_code in (400, 403, 428):
            try:
                err = resp.json().get("error", "")
            except Exception:
                err = ""

            if err == "authorization_pending":
                # 使用者還在輸入代碼 / 想事情，繼續等
                continue
            elif err == "slow_down":
                # **不是錯**！Google 要我放慢。間隔加 5 秒，繼續
                interval += 5
                log(f"   ⏸️  slow_down → interval 改為 {interval}s，繼續 polling")
                continue
            elif err == "access_denied":
                # 使用者按了拒絕
                log("   ❌ 使用者按了 [拒絕]")
                return None
            elif err == "expired_token":
                # device_code 過期了
                log("   ❌ device_code 過期，請重跑這個 script")
                return None
            else:
                # 未知錯誤
                log(f"   ❌ 未預期 error: {err}")
                log(f"      {resp.text[:300]}")
                return None

        # 其他 HTTP code（500 等）才是真正的 server 問題
        log(f"   ❌ HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    log(f"   ❌ polling 超時（{expires_in}s）")
    return None


def save_tokens(tokens, out_path):
    """存 tokens（加 expires_at timestamp），mode 600"""
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    tokens["obtained_at"] = time.time()
    with open(out_path, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(out_path, 0o600)
    log(f"\n✅ Tokens 已存: {out_path} (mode 600)")
    log(f"   access_token: {tokens.get('access_token', '?')[:30]}...")
    log(f"   refresh_token: {'有' if tokens.get('refresh_token') else '無'}")
    log(f"   expires_in: {tokens.get('expires_in')}s ({tokens.get('expires_in', 0)//60} 分鐘)")
    log(f"   scope: {tokens.get('scope', '?')}")


# ────────────────────────────────────────
# CLI
# ────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OAuth Device Code Flow polling skeleton (N100 headless friendly)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--client-json",
        default=os.path.expanduser("~/.local/share/hermes/secrets/youtube_client.json"),
        help="OAuth client JSON 路徑（要 TV/limited-input 類型，**不是電腦應用程式**）",
    )
    parser.add_argument(
        "--scope",
        default="https://www.googleapis.com/auth/youtube.readonly",
        help=(
            "OAuth scope。**只支援 4 個**：youtube.readonly / openid / email / profile。"
            "youtube.force-ssl / subscriptions.readonly 會回 invalid_scope。"
        ),
    )
    parser.add_argument(
        "--token-out",
        default=os.path.expanduser("~/.hermes/youtube_tokens.json"),
        help="tokens 輸出路徑（會 chmod 600）",
    )
    args = parser.parse_args()

    reset_log()
    log("=" * 60)
    log("OAuth Device Code Flow")
    log("=" * 60)

    # 1. 讀 client
    client = load_client(args.client_json)
    log(f"Client ID: {client['client_id']}")
    log(f"Project:   {client['project_id']}")
    log(f"Scope:     {args.scope}")

    # 2. 拿 device code
    device = request_device_code(client["client_id"], args.scope)
    user_code = device["user_code"]
    device_code = device["device_code"]
    interval = device.get("interval", 5)
    expires_in = device.get("expires_in", 1800)
    verification_url = device.get("verification_url", "https://www.google.com/device")

    log("")
    log("=" * 60)
    log("📱 給使用者的指示（**唯一有效的 user_code**）")
    log("=" * 60)
    log(f"  1. 打開：{verification_url}")
    log(f"  2. 輸入：{user_code}    ← **這個代碼 30 分鐘內有效**")
    log("  3. 選你的 Google 帳號 + 按 [允許]")
    log("")
    log(f"  ⚠️  如果你之前已經輸入過別的 user_code，**那是舊的、已作廢**")
    log(f"      Google 同 client 同時間只允許一個 active device_code")
    log("=" * 60)
    log("")

    # 3. polling
    tokens = poll_for_token(
        client["client_id"],
        client["client_secret"],
        device_code,
        interval,
        expires_in,
    )

    if tokens is None:
        log("\n❌ 沒拿到 tokens，看上方 log 找原因")
        sys.exit(1)

    # 4. 存
    save_tokens(tokens, args.token_out)
    log("\n🎉 完成！")


if __name__ == "__main__":
    main()
