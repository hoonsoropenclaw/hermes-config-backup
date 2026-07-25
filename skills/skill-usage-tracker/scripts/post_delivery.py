#!/usr/bin/env python3
"""
post_delivery.py — 任務交付後的 skill 使用量統計 + 評分邀請產生器。

為什麼需要這個：
- Layer 2 的 session_skill_logger 只追蹤 skill_view（SKILL.md 載入）
- 但真實工作量往往在 execute_code / vision_analyze / terminal 等隱性工具
- post_delivery.py 從 state.db 讀取完整 tool_call 分佈，計算「隱性技能強度」

用法:
    python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
        --session 20260616_125207_dc21b806

輸出:
    - tool_call 分佈（所有工具）
    - 隱性技能強度評估
    - 自動生成「標準評分邀請格式」
"""
import json
import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DB_PATH = Path.home() / ".hermes/state.db"
LOG_DIR = Path.home() / ".hermes/skill-usage"

# 工具 → 隱性技能 domain 映射
# 當某工具使用次數高時，代表對應的隱性技能在工作
TOOL_TO_SKILL_DOMAIN = {
    'execute_code': 'Python 腳本與資料處理',
    'terminal': 'Shell 腳本與系統指令',
    'read_file': '檔案讀取與內容理解',
    'write_file': '檔案寫入與產出生成',
    'patch': '程式碼修改與修補',
    'search_files': '程式碼搜尋與分析',
    'web_search': '網路資訊檢索',
    'web_extract': '網頁內容提取',
    'browser_navigate': '瀏覽器自動化操作',
    'browser_click': '瀏覽器 UI 互動',
    'browser_vision': '視覺化瀏覽器操作',
    'vision_analyze': '圖片視覺分析',
    'session_search': '對話歷史檢索',
    'skills_list': '技能清單查詢',
    'skill_view': '技能文檔查閱（顯性）',
    'delegate_task': '子任務委派',
}

# 隱性技能 domain 的「高用量」閾值
DOMAIN_HIGH_USAGE = 3


def get_session_tool_distribution(session_id: str) -> dict:
    """從 state.db 查詢某 session 的完整 tool_call 分佈。

    sessions.id = full session ID (e.g. '20260616_125207_dc21b806')
    messages.session_id = same full session ID
    使用 LIKE prefix 匹配以支援部分 session ID（如 '20260616_125207_dc21'）
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # messages.session_id 是 full ID，用 LIKE prefix 匹配
    cur.execute("""
        SELECT tool_name, COUNT(*) as cnt
        FROM messages
        WHERE session_id LIKE ? AND tool_name IS NOT NULL AND tool_name != ''
        GROUP BY tool_name
        ORDER BY cnt DESC
    """, (session_id.rstrip() + '%',))
    rows = cur.fetchall()

    # sessions.id 是 full ID，也用 LIKE prefix 匹配
    cur.execute("""
        SELECT source, model, title, started_at, message_count
        FROM sessions WHERE id LIKE ?
    """, (session_id.rstrip() + '%',))
    meta_row = cur.fetchone()
    meta = dict(meta_row) if meta_row else {}

    conn.close()

    total_calls = sum(r['cnt'] for r in rows)
    explicit_skills = []
    implicit_domains = []

    for r in rows:
        tool = r['tool_name']
        cnt = r['cnt']
        domain = TOOL_TO_SKILL_DOMAIN.get(tool)
        if tool == 'skill_view':
            explicit_skills.append({'tool': tool, 'cnt': cnt})
        elif domain and cnt >= DOMAIN_HIGH_USAGE:
            implicit_domains.append({'domain': domain, 'tool': tool, 'cnt': cnt})

    return {
        'session_id': session_id,
        'source': meta.get('source'),
        'title': meta.get('title'),
        'started_at': datetime.fromtimestamp(meta['started_at']).isoformat() if meta.get('started_at') else None,
        'message_count': meta.get('message_count', 0),
        'total_tool_calls': total_calls,
        'tool_distribution': [{'tool': r['tool_name'], 'cnt': r['cnt']} for r in rows],
        'explicit_skills': explicit_skills,
        'implicit_domains': implicit_domains,
        'implicit_skill_strength': 'high' if len(implicit_domains) >= 3 else 'medium' if len(implicit_domains) >= 1 else 'low',
    }


def generate_report(data: dict) -> str:
    """根據 tool 分佈生成文字報告。"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"Session: {data['session_id']}")
    lines.append(f"主題: {data.get('title') or '(無)'}")
    lines.append(f"總 tool calls: {data['total_tool_calls']}")
    lines.append("")

    # Tool 分佈
    lines.append("Tool 使用分佈:")
    for item in data['tool_distribution'][:10]:
        pct = item['cnt'] / data['total_tool_calls'] * 100 if data['total_tool_calls'] else 0
        bar = "█" * int(pct / 5)
        lines.append(f"  {item['tool']:40s} {item['cnt']:3d}x ({pct:5.1f}%) {bar}")
    lines.append("")

    # 隱性技能強度
    strength = data['implicit_skill_strength']
    emoji = "🔴" if strength == 'high' else "🟡" if strength == 'medium' else "🟢"
    lines.append(f"{emoji} 隱性技能強度: {strength.upper()}")

    if data['implicit_domains']:
        lines.append("主要隱性技能:")
        for d in data['implicit_domains']:
            lines.append(f"  - {d['domain']} ({d['tool']} {d['cnt']}x)")

    return "\n".join(lines)


def generate_invitation(data: dict) -> str:
    """生成「標準評分邀請格式」。"""
    explicit = [s['tool'].replace('skill_view: ', '') for s in data.get('explicit_skills', [])]
    implicit = [d['domain'] for d in data.get('implicit_domains', [])]

    all_skills = explicit + implicit
    skills_str = "、".join(all_skills) if all_skills else "（未能識別）"

    lines = []
    lines.append("")
    lines.append("---")
    lines.append(f"📊 這次任務使用了：{skills_str}")
    lines.append("⭐ 請評分（1-5星）：")
    lines.append("   - 整體組合：？")
    lines.append("   - 個別（如果有特別滿意/不滿意的部分）：？")
    lines.append("")
    lines.append("   不用每項都評，隨便給幾顆星都好，沒有壓力。")
    return "\n".join(lines)


def write_log(session_id: str, data: dict, rating: int = None, comment: str = None):
    """寫入 skill-usage JSONL log。"""
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    explicit = [s['tool'].replace('skill_view: ', '') for s in data.get('explicit_skills', [])]
    implicit = [d['domain'] for d in data.get('implicit_domains', [])]

    entry = {
        "ts": datetime.now().isoformat(),
        "session_id": session_id,
        "platform": data.get('source'),
        "task_summary": data.get('title'),
        "planned_skills": [],
        "actual_skills": explicit,
        "implicit_skills": implicit,
        "tool_call_distribution": data.get('tool_distribution', []),
        "implicit_skill_strength": data.get('implicit_skill_strength'),
        "task_result": "reconstructed",
        "method": "post_delivery_tool_analysis",
        "combo_rating": rating,
        "comment": comment,
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"✅ 已寫入: {log_file}")


def main():
    parser = argparse.ArgumentParser(description="任務交付後 tool 使用分析 + 評分邀請")
    parser.add_argument('--session', required=True, help="Session ID（支援部分前綴）")
    parser.add_argument('--write', action='store_true', help="寫入 skill-usage log")
    parser.add_argument('--rating', type=int, help="直接附上評分（1-5）")
    parser.add_argument('--comment', help="直接附上評語")
    args = parser.parse_args()

    data = get_session_tool_distribution(args.session)

    print(generate_report(data))
    print(generate_invitation(data))

    if args.write:
        write_log(args.session, data, args.rating, args.comment)


if __name__ == "__main__":
    main()
