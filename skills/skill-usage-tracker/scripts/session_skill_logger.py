#!/usr/bin/env python3
"""
session_skill_logger.py
查詢 state.db 重建指定 session 的 skill 實際載入清單。

原理：Hermes 每次 skill_view 都會在 messages 表留下 tool_name='skill_view'。
state.db 是眞實的、被執行過的記錄，不依賴「自覺觸發」。

用法:
    # 查詢特定 session
    python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py --session 20260616_125207_dc21b806

    # 查詢所有 telegram session（最近 7 天）
    python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py --platform telegram --days 7

    # 查詢並寫入 skill-usage log（格式相容）
    python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py --session 20260616_125207_dc21b806 --write-log

    # 列出最近 N 個 session
    python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py --list-sessions 10
"""
import json
import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict

DB_PATH = Path.home() / ".hermes/state.db"
LOG_DIR = Path.home() / ".hermes/skill-usage"

# 排除清單（執行類工具，不計入 skill 追蹤）
EXCLUDED_TOOLS = {
    'terminal', 'execute_code', 'read_file', 'write_file', 'patch',
    'search_files', 'web_search', 'web_extract', 'browser_navigate',
    'browser_click', 'browser_type', 'browser_snapshot', 'browser_vision',
    'browser_console', 'browser_back', 'browser_press', 'browser_scroll',
    'browser_get_images', 'send_message', 'cronjob', 'clarify',
    'process', 'memory', 'todo', 'vision_analyze', 'delegate_task',
    'mcp_mempalace_mempalace_add_drawer', 'mcp_mempalace_mempalace_diary_read',
    'mcp_mempalace_mempalace_kg_timeline', 'mcp_mempalace_mempalace_list_drawers',
    'mcp_mempalace_mempalace_search', 'mcp_mempalace_mempalace_status',
    'text_to_speech',
}


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_session_skill_usage(session_id: str, conn=None) -> dict:
    """查詢某個 session 的所有 skill_view 調用，返回結構化數據。"""
    own_conn = conn is None
    if own_conn:
        conn = get_db()

    cur = conn.cursor()

    # 查詢該 session 的 skill_view 調用
    cur.execute("""
        SELECT id, timestamp, content
        FROM messages
        WHERE session_id = ? AND tool_name = 'skill_view'
        ORDER BY timestamp ASC
    """, (session_id,))

    skill_calls = []
    for row in cur.fetchall():
        content = row['content']
        skill_name = None
        # 解析 content（可能是 JSON 或純文字）
        if content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    skill_name = parsed.get('name', parsed.get('skill_name'))
            except (json.JSONDecodeError, TypeError):
                # 純文字格式：skill_view(name='xxx')
                import re
                m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", content)
                if m:
                    skill_name = m.group(1)

        if skill_name:
            ts = datetime.fromtimestamp(row['timestamp']).isoformat()
            skill_calls.append({'skill': skill_name, 'ts': ts, 'msg_id': row['id']})

    # 查詢 session 元數據
    cur.execute("""
        SELECT source, model, title, started_at, message_count
        FROM sessions
        WHERE id = ?
    """, (session_id,))
    row = cur.fetchone()
    session_meta = dict(row) if row else {}

    if own_conn:
        conn.close()

    # 去重（同一 skill 只留第一次）
    seen = OrderedDict()
    for call in skill_calls:
        if call['skill'] not in seen:
            seen[call['skill']] = call

    return {
        'session_id': session_id,
        'source': session_meta.get('source'),
        'model': session_meta.get('model'),
        'title': session_meta.get('title'),
        'started_at': datetime.fromtimestamp(session_meta['started_at']).isoformat() if session_meta.get('started_at') else None,
        'message_count': session_meta.get('message_count', 0),
        'skills_loaded': list(seen.keys()),
        'skill_calls': list(seen.values()),
        'skill_count': len(seen),
    }


def list_recent_sessions(limit: int = 10, platform: str = None, days: int = None) -> list:
    """列出最近的 session。"""
    conn = get_db()
    cur = conn.cursor()

    cutoff = None
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).timestamp()

    sql = """
        SELECT id, source, model, title, started_at, message_count
        FROM sessions
        WHERE id NOT LIKE 'cron_%%' AND source != 'cron'
    """
    params = []
    if cutoff:
        sql += " AND started_at > ?"
        params.append(cutoff)
    if platform:
        sql += " AND source = ?"
        params.append(platform)

    sql += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    sessions = []
    for r in rows:
        sessions.append({
            'id': r['id'],
            'source': r['source'],
            'model': r['model'],
            'title': r['title'],
            'started_at': datetime.fromtimestamp(r['started_at']).isoformat() if r['started_at'] else None,
            'message_count': r['message_count'],
        })
    return sessions


def write_to_skill_usage_log(session_data: dict) -> Path:
    """將 session 資料寫入 skill-usage log（JSONL 格式）。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    log_file = LOG_DIR / f"{today}.jsonl"

    entry = {
        'ts': datetime.now().isoformat(),
        'session_id': session_data['session_id'],
        'platform': session_data.get('source', 'unknown'),
        'task_summary': session_data.get('title') or session_data['session_id'],
        'planned_skills': [],  # 未知（session 開始前沒記錄）
        'actual_skills': session_data['skills_loaded'],
        'task_result': 'reconstructed',  # 表示是事後重建
        'method': 'state_db_skill_view_query',
    }

    with open(log_file, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    return log_file


def main():
    parser = argparse.ArgumentParser(description='Hermes session skill profiler')
    parser.add_argument('--session', help='Session ID to analyze')
    parser.add_argument('--list-sessions', type=int, metavar='N', help='List N most recent non-cron sessions')
    parser.add_argument('--platform', help='Filter sessions by platform (telegram, cli, etc.)')
    parser.add_argument('--days', type=int, help='Only show sessions from last N days')
    parser.add_argument('--write-log', action='store_true', help='Write results to skill-usage log')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')

    args = parser.parse_args()

    if args.list_sessions:
        sessions = list_recent_sessions(limit=args.list_sessions, platform=args.platform, days=args.days)
        print(f"\n📋 最近 {args.list_sessions} 個非 cron session:")
        print("=" * 80)
        for s in sessions:
            print(f"  [{s['started_at'][:16]}] {s['source']:10s}  {s['id']}")
            if s['title']:
                print(f"       標題: {s['title']}")
        return

    if args.session:
        data = get_session_skill_usage(args.session)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"\n🔍 Session: {data['session_id']}")
            print(f"   來源: {data['source']} | Model: {data['model']}")
            print(f"   標題: {data.get('title', '(無)')}")
            print(f"   開始: {data['started_at']} | 訊息數: {data['message_count']}")
            print(f"\n   📊 實際載入 skill（共 {data['skill_count']} 個）:")
            if data['skills_loaded']:
                for skill in data['skills_loaded']:
                    first_call = next((c for c in data['skill_calls'] if c['skill'] == skill), {})
                    print(f"     • {skill} (首次: {first_call.get('ts', '?')[:19]})")
            else:
                print("     (無)")

        if args.write_log:
            path = write_to_skill_usage_log(data)
            print(f"\n   ✅ 已寫入: {path}")
        return

    # New: handle --platform + --days (reconstruct all matching sessions)
    if args.platform or args.days:
        sessions = list_recent_sessions(limit=100, platform=args.platform, days=args.days)
        print(f"\n📋 最近 {len(sessions)} 個 session ({'platform='+args.platform if args.platform else 'all'}{', days='+str(args.days) if args.days else ''}):")
        print("=" * 80)
        written = 0
        skipped = 0
        for s in sessions:
            print(f"\n  [{s['started_at'][:16]}] {s['source']:10s}  {s['id']}")
            if s['title']:
                print(f"       標題: {s['title']}")
            data = get_session_skill_usage(s['id'])
            print(f"       Skills ({data['skill_count']}): {', '.join(data['skills_loaded']) if data['skills_loaded'] else '(無 SKILL.md 載入)'}")
            if args.write_log:
                # Idempotency: skip if session_id already in today's log
                today = datetime.now().strftime('%Y-%m-%d')
                log_file = LOG_DIR / f"{today}.jsonl"
                already_logged = False
                if log_file.exists():
                    with open(log_file) as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())
                                if entry.get('session_id') == s['id']:
                                    already_logged = True
                                    break
                            except json.JSONDecodeError:
                                continue
                if already_logged:
                    print(f"       ⏭️  已存在，略過")
                    skipped += 1
                else:
                    path = write_to_skill_usage_log(data)
                    print(f"       ✅ 已寫入 skill-usage log")
                    written += 1
        if args.write_log:
            print(f"\n✅ 本次寫入 {written} 筆，略過 {skipped} 筆（已存在）")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
