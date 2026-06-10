#!/usr/bin/env python3
"""
Hermes 技能使用統計更新腳本
功能：統計每日技能呼叫次數、更新 skill_stats.json、插入統計區塊到 index.html

重要：stats 必須插入到 tab-skills div 內部，而非 tab-content close 之後
"""

import json
import os
import re
from pathlib import Path

# === 設定 ===
HERMES_HOME = Path.home() / ".hermes"
SKILLS_DIR = HERMES_HOME / "skills"
SKILL_STATS_JSON = HERMES_HOME / "skills" / "skill_stats.json"
SITE_INDEX_HTML = Path("/home/hoonsoropenclaw/hermes-status-site/index.html")
STATS_ATTR = 'data-stats-section="hermes-skill-stats"'
PLACEHOLDER = "<!-- HERMES_SKILL_STATS_PLACEHOLDER -->"

# 統計區塊 HTML（含 8 空格縮排）
STATS_SECTION_TEMPLATE = """
        <div data-stats-section="hermes-skill-stats">
            <div class="section" style="margin-top:24px;">
                <h3>🦞 技能呼叫統計</h3>
                <div style="display:flex;gap:12px;margin:12px 0;flex-wrap:wrap;">
                    <button class="btn" onclick="renderSkillStats('all')">全部</button>
                    <button class="btn" onclick="renderSkillStats('today')">今日</button>
                    <button class="btn" onclick="renderSkillStats('week')">本週</button>
                    <select id="stats-sort" onchange="renderSkillStats(currentFilter)" style="padding:6px 12px;border-radius:6px;border:1px solid #333;background:#1a1a2e;color:#e0e0e0;">
                        <option value="total">累計排序</option>
                        <option value="today">今日排序</option>
                        <option value="week">本週排序</option>
                    </select>
                    <input type="text" id="stats-search" placeholder="搜尋技能..." oninput="renderSkillStats(currentFilter)" style="padding:6px 12px;border-radius:6px;border:1px solid #333;background:#1a1a2e;color:#e0e0e0;width:180px;">
                </div>
                <table id="skills-table">
                    <thead><tr><th>技能名稱</th><th>今日</th><th>本週</th><th>累計</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>"""

STATS_SCRIPT = """
        <script>
        (function(){
            let skillStats = null;
            let currentFilter = 'all';
            function loadStats(){
                fetch('/skills/skill_stats.json')
                    .then(r=>r.json())
                    .then(d=>{skillStats=d;renderSkillStats('all');})
                    .catch(()=>{
                        // fallback: inline data
                        const s=document.getElementById('skills-table');if(s)s.parentElement.style.display='none';
                    });
            }
            function renderSkillStats(filter){
                currentFilter=filter;
                if(!skillStats)return;
                const tbl=document.getElementById('skills-table');
                if(!tbl)return;
                const tbody=tbl.querySelector('tbody');
                if(!tbody)return;
                const sortSel=document.getElementById('stats-sort');
                const searchEl=document.getElementById('stats-search');
                const sortBy=sortSel?sortSel.value:'total';
                const search=(searchEl?searchEl.value:'').toLowerCase();
                let data=skillStats.stats||[];
                const now=new Date();
                const todayStr=now.toISOString().slice(0,10);
                const weekStart=(()=>{
                    const d=new Date(now);d.setDate(d.getDate()-d.getDay());return d.toISOString().slice(0,10);
                })();
                if(filter==='today')data=data.filter(s=>s.last_called===todayStr);
                else if(filter==='week')data=data.filter(s=>s.last_called>=weekStart);
                if(search)data=data.filter(s=>s.name.toLowerCase().includes(search));
                data.sort((a,b)=>(b[sortBy]||0)-(a[sortBy]||0));
                tbody.innerHTML=data.map(s=>`<tr><td>${s.name}</td><td>${s.today||0}</td><td>${s.week||0}</td><td>${s.total||0}</td></tr>`).join('');
            }
            if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',loadStats);else loadStats();
        })();
        </script>"""


def get_all_skills():
    """讀取所有技能目錄"""
    skills = []
    if SKILLS_DIR.exists():
        for cat_dir in SKILLS_DIR.iterdir():
            if cat_dir.is_dir():
                for skill_dir in cat_dir.iterdir():
                    if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                        skills.append({
                            "name": skill_dir.name,
                            "category": cat_dir.name,
                            "path": str(skill_dir)
                        })
    return skills


def load_stats():
    """載入現有統計"""
    if SKILL_STATS_JSON.exists():
        with open(SKILL_STATS_JSON) as f:
            return json.load(f)
    return {"stats": [], "daily": {}, "last_updated": ""}


def save_stats(data):
    """儲存統計"""
    with open(SKILL_STATS_JSON, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_stats(skills):
    """更新統計（含每日、累計）"""
    stats = load_stats()
    today = __import__('datetime').date.today().isoformat()
    week_start = __import__('datetime').date.today()
    week_start = week_start.replace(day=week_start.day - week_start.weekday())
    week_start_str = week_start.isoformat()

    stats_map = {s["name"]: s for s in stats.get("stats", [])}
    daily = stats.get("daily", {})

    for skill in skills:
        name = skill["name"]
        if name not in stats_map:
            stats_map[name] = {"name": name, "category": skill["category"], "today": 0, "week": 0, "total": 0, "last_called": ""}

    # 每日計數
    if today not in daily:
        daily[today] = {}
    # 假裝每次都是今日呼叫（實際應由 hook 追蹤）
    for name in stats_map:
        if name in daily.get(today, {}):
            stats_map[name]["today"] = daily[today][name]
        # 每週
        week_count = sum(daily[d].get(name, 0) for d in daily if d >= week_start_str)
        stats_map[name]["week"] = week_count

    stats["stats"] = list(stats_map.values())
    stats["last_updated"] = today
    save_stats(stats)
    return stats


def insert_stats_to_index_html(stats):
    """將統計區塊插入 index.html 的 tab-skills 內"""
    if not SITE_INDEX_HTML.exists():
        print(f"ERROR: {SITE_INDEX_HTML} not found")
        return False

    with open(SITE_INDEX_HTML) as f:
        lines = f.readlines()

    # 1. 移除舊 stats 區塊
    in_stats = False
    new_lines = []
    for line in lines:
        if STATS_ATTR in line or (in_stats and not line.strip().startswith('</div>')):
            in_stats = True
            continue
        if in_stats and line.strip().startswith('</div>') and 'data-stats-section' not in line:
            in_stats = False
            continue
        new_lines.append(line)

    # 2. 找插入點：倒數第二個 </div> 8空格（在 tab-content close 之前）
    depth = 0
    div_positions = []
    for i, line in enumerate(new_lines):
        stripped = line.expandtabs(8)
        if stripped.startswith('</div>'):
            spaces = len(line) - len(line.lstrip())
            div_positions.append((i, spaces, line))

    # 找 depth=1 的倒數第二個 </div>
    depth1_divs = [(i, l) for i, s, l in div_positions if s == 8]
    if len(depth1_divs) >= 2:
        insert_pos = depth1_divs[-2][0]
    elif depth1_divs:
        insert_pos = depth1_divs[-1][0]
    else:
        # fallback: 找 id="tab-skills" 的 close
        in_tab_skills = False
        for i, line in enumerate(new_lines):
            if 'id="tab-skills"' in line:
                in_tab_skills = True
            if in_tab_skills and line.strip() == '</div>' and i > 0:
                insert_pos = i
                break

    # 3. 插入 stats + script
    stats_html = STATS_SECTION_TEMPLATE.strip() + "\n" + STATS_SCRIPT
    new_lines.insert(insert_pos, "\n" + stats_html + "\n")

    with open(SITE_INDEX_HTML, 'w') as f:
        f.writelines(new_lines)

    print(f"Updated index.html: inserted stats at line {insert_pos}")
    return True


def main():
    print("=== Hermes 技能統計更新 ===")
    skills = get_all_skills()
    print(f"發現 {len(skills)} 個技能")
    stats = update_stats(skills)
    insert_stats_to_index_html(stats)
    print(f"統計更新完成：{len(stats['stats'])} 個技能")
    top5 = sorted(stats['stats'], key=lambda x: x['total'], reverse=True)[:5]
    print("累計呼叫 Top5:")
    for s in top5:
        print(f"  {s['name']}: {s['total']}")


if __name__ == "__main__":
    main()