#!/usr/bin/env python3
"""
技能使用統計腳本 v3
- 讀取 .usage.json 獲取累計使用次數
- 解析 messages DB 計算每日呼叫次數
- 輸出 skill_stats.json 供網頁使用
- 更新 tabs/skills.html（獨立檔案，idempotent）
"""

import sqlite3, json, datetime, re
from pathlib import Path

HERMES_DIR = Path.home() / ".hermes"
USAGE_FILE = HERMES_DIR / "skills" / ".usage.json"
STATS_FILE = HERMES_DIR / "skills" / "skill_stats.json"
SKILLS_HTML = Path.home() / "hermes-status-site" / "tabs" / "skills.html"
DB_PATH = HERMES_DIR / "state.db"

# Marker to detect if stats section already exists
STATS_TABLE_ID = 'id="skills-table"'
STATS_SECTION_MARKER = 'data-stats-section="hermes-skill-stats"'

def load_usage():
    if not USAGE_FILE.exists():
        return {}
    with open(USAGE_FILE, encoding='utf-8') as f:
        return json.load(f)

def get_daily_counts():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    today = datetime.date.today()
    today_start = datetime.datetime.combine(today, datetime.time.min).timestamp()
    today_end = datetime.datetime.combine(today, datetime.time.max).timestamp()

    cur.execute("""
        SELECT id, session_id, tool_calls, content, tool_name, timestamp
        FROM messages
        WHERE tool_name IN ('skill_view', 'skill_manage', 'skills_list')
        AND timestamp >= ?
        ORDER BY timestamp DESC
    """, (today_start,))

    rows = cur.fetchall()
    conn.close()

    daily_counts = {}
    for row in rows:
        msg_id, session_id, tool_calls, content, tool_name, ts = row
        if tool_name == 'skill_view':
            try:
                if tool_calls:
                    tc = json.loads(tool_calls)
                    skill_name = tc.get('name') if isinstance(tc, dict) else None
                else:
                    skill_name = None
            except:
                skill_name = None

            if skill_name:
                daily_counts[skill_name] = daily_counts.get(skill_name, 0) + 1

        elif tool_name == 'skills_list':
            daily_counts['__all__'] = daily_counts.get('__all__', 0) + 1

    return daily_counts

def build_stats():
    usage = load_usage()
    daily = get_daily_counts()

    history = {}
    if STATS_FILE.exists():
        with open(STATS_FILE, encoding='utf-8') as f:
            hist_data = json.load(f)
            history = hist_data.get('daily', {})

    today_key = datetime.date.today().strftime('%Y-%m-%d')
    history[today_key] = daily

    total_counts = {}
    for skill_name, info in usage.items():
        total_counts[skill_name] = info.get('use_count', 0)

    stats = {
        'generated_at': datetime.datetime.now().isoformat(),
        'total_skills': len(usage),
        'daily': history,
        'cumulative': total_counts,
        'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats

def generate_tbody_rows(stats):
    """Generate only the tbody rows for the stats table"""
    usage = load_usage()
    daily = stats.get('daily', {}).get(datetime.date.today().strftime('%Y-%m-%d'), {})
    cumulative = stats.get('cumulative', {})

    skills_data = []
    for skill_name, info in usage.items():
        use_count = cumulative.get(skill_name, 0)
        today_count = daily.get(skill_name, 0)
        last_used = info.get('last_used_at', None)
        if last_used:
            last_used = last_used[:10]

        skills_data.append({
            'name': skill_name,
            'use_count': use_count,
            'today_count': today_count,
            'last_used': last_used,
            'state': info.get('state', 'active'),
            'created_at': info.get('created_at', '')[:10] if info.get('created_at') else ''
        })

    # Sort by use_count descending
    skills_data.sort(key=lambda x: x['use_count'], reverse=True)

    rows_html = ''
    for rank, skill in enumerate(skills_data, 1):
        last_used = skill['last_used'] or '-'
        state_class = 'tag-green' if skill['state'] == 'active' else 'tag-yellow'
        today_display = f'<span style="color:#10b981; font-weight:600;">{skill["today_count"]}</span>' if skill['today_count'] > 0 else '-'

        rows_html += f'''<tr class="skill-row">
                        <td style="color:#64748b; font-size:12px;">#{rank}</td>
                        <td><span class="skill-name" style="font-weight:600; color:#f1f5f9;">{skill["name"]}</span></td>
                        <td style="font-size:13px;">{today_display}</td>
                        <td><span style="color:#3b82f6; font-weight:700; font-size:14px;">{skill["use_count"]}</span></td>
                        <td style="color:#94a3b8; font-size:12px;">{last_used}</td>
                        <td><span class="tag {state_class}">{skill["state"]}</span></td>
                        <td style="color:#64748b; font-size:11px;">{skill["created_at"] or "-"}</td>
                    </tr>
'''

    return rows_html

def update_skills_html(stats):
    """Update tabs/skills.html - replace tbody rows with fresh data, idempotent"""
    if not SKILLS_HTML.exists():
        print(f"WARNING: {SKILLS_HTML} not found, skipping HTML update")
        return

    with open(SKILLS_HTML, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate new rows
    new_rows = generate_tbody_rows(stats)

    # Check if stats table already exists
    if STATS_TABLE_ID not in content:
        print("WARNING: skills-table not found in tabs/skills.html, skipping HTML update")
        return

    # Strategy: replace everything between <tbody> and </tbody>
    # Find the tbody that contains skill-row elements
    tbody_pattern = re.compile(r'(<tbody>)\s*\n(.*?)(\s*</tbody>)', re.DOTALL)
    match = tbody_pattern.search(content)

    if not match:
        print("WARNING: could not find tbody in tabs/skills.html")
        return

    new_content = content[:match.start()] + '<tbody>\n' + new_rows + '            </tbody>' + content[match.end():]

    with open(SKILLS_HTML, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Updated skills.html with {stats['total_skills']} skills, sorted by use_count desc")

def main():
    print("技能使用統計腳本 v3 開始執行...")
    stats = build_stats()
    update_skills_html(stats)

    top_skill = max(stats['cumulative'].items(), key=lambda x: x[1]) if stats['cumulative'] else ('none', 0)
    print(f"完成！統計 {stats['total_skills']} 個技能")
    print(f"累計呼叫最多: {top_skill[0]} ({top_skill[1]}次)")
    print(f"更新時間: {stats['last_updated']}")

if __name__ == '__main__':
    main()