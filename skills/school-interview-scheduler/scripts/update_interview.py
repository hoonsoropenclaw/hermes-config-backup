#!/usr/bin/env python3
"""update_interview.py — 更新或取消 Google Calendar 面試事件"""
import argparse, datetime, json, os, sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home()) + "/.hermes"))
TOKEN_FILE=str(Path.home()) + "/.hermes/google_token.json"

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print(json.dumps({"error": "google-api-python-client 或 google-auth 未安裝"}))
    sys.exit(1)


def build_service():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        return build("calendar", "v3", credentials=creds, static_discovery=False)
    tf = Path(TOKEN_FILE)
    if tf.exists():
        creds = Credentials.from_authorized_user_info(json.loads(tf.read_text()))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            tf.write_text(creds.to_json())
        return build("calendar", "v3", credentials=creds, static_discovery=False)
    print(json.dumps({"error": "未設定 Google 認證"}))
    sys.exit(1)


def parse_datetime(dt_str):
    return datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-id", required=True)
    ap.add_argument("--datetime", help="新時間 (YYYY-MM-DD HH:MM)")
    ap.add_argument("--cancel", action="store_true", help="取消此事件")
    args = ap.parse_args()
    service = build_service()

    if args.cancel:
        service.events().delete(calendarId="primary", eventId=args.event_id, sendUpdates="all").execute()
        print(json.dumps({"status": "deleted", "event_id": args.event_id}))
        return

    if not args.datetime:
        print(json.dumps({"error": "需提供 --datetime 或 --cancel"}))
        sys.exit(1)

    start_dt = parse_datetime(args.datetime)
    end_dt = start_dt + datetime.timedelta(minutes=60)
    patched = (
        service.events()
        .patch(
            calendarId="primary",
            eventId=args.event_id,
            body={
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Taipei"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Taipei"},
            },
            sendUpdates="all",
        )
        .execute()
    )
    print(json.dumps({"status": "updated", "event_id": patched["id"], "datetime": args.datetime}))


if __name__ == "__main__":
    main()
