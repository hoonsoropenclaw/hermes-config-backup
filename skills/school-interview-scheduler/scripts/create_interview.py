#!/usr/bin/env python3
"""
create_interview.py — 建立 Google Calendar 面試事件 + Google Meet 連結

用法:
    python3 create_interview.py --candidate "張三" --email "zhangsan@gmail.com" \
        --datetime "2026-06-20 10:00" --position "數學教師" --duration 60

依賴:
    google-api-python-client, google-auth
    設定完成後可呼叫 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --check
"""
import argparse
import datetime
import json
import os
import sys
import time
import uuid
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home()) + "/.hermes"))
TOKEN_FILE = str(HERMES_HOME) + "/google_token.json"

# ─── Google API imports ───────────────────────────────────────────────────────
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth.exceptions
except ImportError:
    print(json.dumps({"error": "google-api-python-client 或 google-auth 未安裝"}))
    sys.exit(1)


# ─── Auth ────────────────────────────────────────────────────────────────────

def load_oauth2_token():
    """從 google_token.json 讀取 OAuth2 user credentials，自動 refresh 過期 token。"""
    tf = Path(TOKEN_FILE)
    if not tf.exists():
        return None
    creds = Credentials.from_authorized_user_info(json.loads(tf.read_text()))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tf.write_text(creds.to_json())
    return creds


def load_service_account():
    """從 GOOGLE_APPLICATION_CREDENTIALS 環境變數讀取 Service Account。"""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        return None
    return service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )


def build_calendar_service():
    """建立 Google Calendar API service。優先使用 Service Account（Google Workspace），
    備援 OAuth2 user token。"""
    creds = load_service_account()
    if creds:
        return build("calendar", "v3", credentials=creds, static_discovery=False)
    creds = load_oauth2_token()
    if creds:
        return build("calendar", "v3", credentials=creds, static_discovery=False)
    print(json.dumps({
        "error": "未設定 Google 認證。請先執行: "
                 "python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py calendar"
    }))
    sys.exit(1)


# ─── Datetime parsing ─────────────────────────────────────────────────────────

def parse_datetime(dt_str):
    """解析 '2026-06-20 10:00' 為 datetime。"""
    return datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


# ─── Core API call with error handling ───────────────────────────────────────

def create_interview(candidate, email, datetime_str, position, duration_minutes=60):
    """建立 Google Calendar event + Google Meet 連結。

    錯誤處理：
    - 401 Unauthorized: token 過期或無效 → 提示重新執行 OAuth 設定流程
    - 429 Rate Limit: 短時間請求過多 → 指數退避重試（最多 3 次）
    - 403 Forbidden: 無 Calendar 寫入權限 → 提示檢查 OAuth 範圍
    - 400 Bad Request: 參數錯誤 → 回傳詳細錯誤
    """
    service = build_calendar_service()
    start_dt = parse_datetime(datetime_str)
    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
    request_id = str(uuid.uuid4())  # Google Meet 需要 unique requestId

    event = {
        "summary": f"【面試】{candidate} - {position}",
        "description": (
            f"面試職位：{position}\n"
            f"面試方式：Google Meet 視訊\n\n"
            f"請在面試開始前 5 分鐘進入會議。"
        ),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Taipei"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Taipei"},
        "attendees": [{"email": email, "displayName": candidate}],
        "conferenceData": {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {"type": "eventHangout"},
            }
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email",  "minutes": 60},
                {"method": "popup",  "minutes": 15},
            ],
        },
    }

    # ── API call with retry logic ─────────────────────────────────────────
    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            created = (
                service.events()
                .insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1,   # ← 建立 Google Meet 的關鍵參數
                    sendUpdates="all",           # ← 自動寄送邀請給與會者
                )
                .execute()
            )
            break  # 成功，跳出重試迴圈

        except HttpError as e:
            status_code = e.resp.status
            error_body = json.loads(e.content.decode()) if e.content else {}

            if status_code == 401:
                # Unauthorized — token 過期/無效，OAuth 設定問題
                print(json.dumps({
                    "error": "Google API 401 Unauthorized",
                    "detail": "OAuth token 過期或無效。請重新執行 OAuth 設定流程：",
                    "fix": "python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py calendar",
                    "api_error": str(e),
                }))
                sys.exit(1)

            elif status_code == 429:
                # Rate Limit — 指數退避
                if attempt < max_retries:
                    wait_seconds = 2 ** attempt  # 2, 4, 8 秒
                    print(f"# 429 Rate Limit，第 {attempt} 次嘗試，等待 {wait_seconds} 秒後重試...")
                    time.sleep(wait_seconds)
                    continue
                else:
                    print(json.dumps({
                        "error": "Google Calendar API 429 Rate Limit",
                        "detail": "短時間請求過多，已達最大重試次數",
                        "fix": "請稍後再試，或聯繫 Google Workspace 管理員提高 API quota",
                        "api_error": str(e),
                    }))
                    sys.exit(1)

            elif status_code == 403:
                print(json.dumps({
                    "error": "Google API 403 Forbidden",
                    "detail": "無 Calendar 寫入權限，請檢查 OAuth 範圍是否包含 calendar.events",
                    "api_error": str(e),
                }))
                sys.exit(1)

            else:
                # 其他 HttpError（400, 404, 500 等）
                print(json.dumps({
                    "error": f"Google API error {status_code}",
                    "detail": error_body.get("error", {}).get("message", str(e)),
                    "api_error": str(e),
                }))
                sys.exit(1)

        except google.auth.exceptions.RefreshError as e:
            # OAuth token refresh 失敗（常見於手動撤銷授權）
            print(json.dumps({
                "error": "Google OAuth token refresh 失敗",
                "detail": "可能已撤銷授權，請重新執行 OAuth 流程",
                "fix": "刪除 google_token.json 後重新執行 OAuth 設定",
                "api_error": str(e),
            }))
            sys.exit(1)

    else:
        # 迴圈正常結束但沒有 break（不應該發生）
        print(json.dumps({"error": "建立面試事件失敗，已達最大重試次數"}))
        sys.exit(1)

    # ── 解析 Meet URL ────────────────────────────────────────────────────
    meet_url = None
    for ep in created.get("conferenceData", {}).get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            meet_url = ep.get("uri")
            break

    return {
        "event_id": created["id"],
        "meet_url": meet_url,
        "calendar_url": created.get("htmlLink"),
        "candidate": candidate,
        "email": email,
        "position": position,
        "datetime": datetime_str,
        "duration_minutes": duration_minutes,
        "status": created.get("status"),
    }


# ─── CLI entry point ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="建立 Google Calendar 面試事件 + Meet 連結")
    ap.add_argument("--candidate", required=True, help="候選人姓名")
    ap.add_argument("--email",    required=True, help="候選人 email")
    ap.add_argument("--datetime", required=True, help="面試時間 (YYYY-MM-DD HH:MM)")
    ap.add_argument("--position", required=True, help="應徵職位")
    ap.add_argument("--duration", type=int, default=60, help="面試時間（分鐘, 預設 60）")
    args = ap.parse_args()

    try:
        result = create_interview(
            candidate=args.candidate,
            email=args.email,
            datetime_str=args.datetime,
            position=args.position,
            duration_minutes=args.duration,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
