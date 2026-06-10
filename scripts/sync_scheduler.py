#!/usr/bin/env python3
"""
sync_scheduler.py
每天自動比對 cron job 清單與 scheduler.html，有差異時更新並部署
"""

import subprocess, re, json, datetime, sys
from pathlib import Path

LOG_FILE = Path("/home/hoonsoropenclaw/sync_scheduler.log")
STATUS_SITE = Path("/home/hoonsoropenclaw/hermes-status-site")
SCHEDULER_HTML = STATUS_SITE / "tabs" / "scheduler.html"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run_hermes_crons():
    """Parse hermes cron list output into structured list"""
    try:
        result = subprocess.run(
            ["hermes", "cron", "list"],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout + result.stderr
    except Exception as e:
        log(f"ERROR: hermes cron list failed: {e}")
        return []

    jobs = []
    # Pattern: UUID [active/paused] / Name: / Schedule: / Next run: / Last run: / (Skills: | Mode: | Script:)
    # Split by double newlines or job boundaries
    job_blocks = re.split(r'\n\s*\n', output.strip())
    
    for block in job_blocks:
        block = block.strip()
        if not block or block.startswith("─") or block.startswith("│"):
            continue
        
        id_m = re.search(r'^([0-9a-f]{10,})', block)
        name_m = re.search(r'Name:\s+(.+)', block)
        sched_m = re.search(r'Schedule:\s+(.+)', block)
        next_m = re.search(r'Next run:\s+(.+)', block)
        last_m = re.search(r'Last run:\s+(.+?)(?:\s+(ok|error|never))?\s*$', block, re.MULTILINE)
        skills_m = re.search(r'Skills:\s+(.+)', block)
        mode_m = re.search(r'Mode:\s+(.+)', block)
        script_m = re.search(r'Script:\s+(.+)', block)
        state_m = re.search(r'\[(\w+)\]', block)
        
        if id_m and name_m:
            last_run_text = last_m.group(1).strip() if last_m else ''
            last_status = last_m.group(2) or 'never' if last_m else 'never'
            name = name_m.group(1).strip()
            
            jobs.append({
                'id': id_m.group(1)[:8],
                'name': name,
                'schedule': sched_m.group(1).strip() if sched_m else '-',
                'next_run': next_m.group(1).strip() if next_m else '-',
                'last_run': last_run_text,
                'last_status': last_status,
                'state': state_m.group(1).lower() if state_m else 'unknown',
                'skills': skills_m.group(1).strip() if skills_m else ('no-agent' if mode_m else '-'),
                'is_no_agent': bool(mode_m) or bool(script_m),
            })

    return jobs

def detect_changes(html_content, new_jobs):
    """Check if scheduler.html needs updating"""
    existing_names = set(re.findall(r'data-cron-name="([^"]+)"', html_content))
    new_names = set(j['name'] for j in new_jobs)
    return new_names != existing_names, existing_names, new_names

def status_tag(status):
    if status == 'ok': return 'tag-green'
    if status == 'error': return 'tag-red'
    return 'tag-yellow'

def state_tag(state):
    if state == 'active': return 'tag-green'
    if state == 'paused': return 'tag-yellow'
    return 'tag-red'

def build_tbody(jobs):
    rows = []
    for job in jobs:
        rows.append(f'''<tr data-cron-name="{job['name']}">
    <td style="text-align:center"><span class="tag tag-blue" style="font-family:monospace">{job['id']}</span></td>
    <td><span class="skill-name" style="font-weight:600">{job['name']}</span></td>
    <td><code style="font-size:11px;background:rgba(59,130,246,0.12);padding:2px 8px;border-radius:4px;white-space:nowrap">{job['schedule']}</code></td>
    <td style="font-size:12px;color:#94a3b8;white-space:nowrap">{job['next_run'][:16]}</td>
    <td><span class="tag {status_tag(job['last_status'])}">{job['last_status']}</span></td>
    <td style="font-size:12px;color:#94a3b8">{job['skills']}</td>
</tr>''')
    return '\n'.join(rows)

def main():
    log("===== 排程同步開始 =====")
    
    jobs = run_hermes_crons()
    log(f"取得 {len(jobs)} 個 cron jobs")
    
    if not SCHEDULER_HTML.exists():
        log(f"ERROR: {SCHEDULER_HTML} not found")
        sys.exit(1)
    
    with open(SCHEDULER_HTML) as f:
        html = f.read()
    
    changed, old_names, new_names = detect_changes(html, jobs)
    
    if not changed:
        log("scheduler.html 與 cron job 清單相同，不需要更新")
        log("===== 排程同步完成 =====\n")
        return
    
    log(f"差異偵測: 新增={new_names - old_names}, 移除={old_names - new_names}")
    log("開始更新 scheduler.html...")
    
    # Build new tbody
    new_tbody = build_tbody(jobs)
    
    # Replace tbody
    tbody_pat = re.compile(r'<tbody[^>]*>(.*?)</tbody>', re.DOTALL)
    m = tbody_pat.search(html)
    if m:
        new_html = html[:m.start()] + f'<tbody>\n{new_tbody}\n        </tbody>' + html[m.end():]
    else:
        log("WARNING: no tbody found")
        new_html = html
    
    # Update job count in section title
    new_html = re.sub(
        r'(排程任務 \(\d+\))',
        f'排程任務 ({len(jobs)})',
        new_html
    )
    
    with open(SCHEDULER_HTML, "w") as f:
        f.write(new_html)
    
    log(f"scheduler.html 已更新 ({len(jobs)} jobs)")
    
    # Deploy
    log("部署 hermes-status-site...")
    try:
        subprocess.run(["git", "add", "-A"], cwd=STATUS_SITE, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: sync scheduler {datetime.date.today().isoformat()}"],
            cwd=STATUS_SITE, check=True
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=STATUS_SITE, check=True)
        token = subprocess.run(
            ["bash", "-c", "echo $VERCEL_API_TOKEN"],
            capture_output=True, text=True
        ).stdout.strip()
        if token:
            result = subprocess.run(
                ["vercel", "--prod", "--token", token],
                cwd=STATUS_SITE, capture_output=True, text=True
            )
            log(f"Vercel: {result.stdout[-200:]}")
        else:
            log("VERCEL_API_TOKEN not set, skipping Vercel deploy")
    except subprocess.CalledProcessError as e:
        log(f"ERROR during deploy: {e}")
    
    log("===== 排程同步完成 =====\n")

if __name__ == "__main__":
    main()