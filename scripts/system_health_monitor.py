#!/usr/bin/env python3
"""
系統健康儀表板監控器 - Raphael Endless Learning System
定時檢查：API配額、任務隊列、鎖檔狀態、專案完成率、系統負載
輸出 JSON 狀態供狀態網站使用
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from pathlib import Path as _Path
import subprocess
import time

# === 設定 ===
WORKSPACE = Path("/home/hoonsoropenclaw/.hermes")
LOGS_DIR = WORKSPACE / "logs"
EL_DIR = WORKSPACE / "evolution"
EL_PROJECTS = EL_DIR / "endless_mode" / "projects"
EL_LOCKS = EL_DIR / "endless_mode" / "locks"
EL_TASK_FILE = EL_DIR / "endless_mode" / "current_learning_task.txt"

OUTPUT_JSON = WORKSPACE / "status_dashboard" / "system_health.json"
OUTPUT_MD = EL_DIR / "endless_mode" / "system_health_report.md"

# === 工具函式 ===
def run_cmd(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, timeout=5).strip()
    except Exception:
        return ""

def read_file(path: Path) -> str:
    try:
        return path.read_text().strip()
    except Exception:
        return ""

def count_files(pattern: str) -> int:
    try:
        return len(list(Path("/home/hoonsoropenclaw/.hermes/evolution/endless_mode/projects").glob(pattern)))
    except Exception:
        return 0

# === 健康檢查模組 ===

def check_api_quota():
    """檢查 API 配額使用狀況"""
    try:
        log = read_file(LOGS_DIR / "api_quota_tracker.log")
        lines = [l for l in log.split("\n") if l.strip() and not l.startswith("#")]
        if lines:
            last = lines[-1]
            return {"status": "ok", "last_entry": last[:80]}
        return {"status": "unknown", "last_entry": "No data"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_current_task():
    """檢查當前任務"""
    task = read_file(EL_TASK_FILE)
    if not task:
        return {"status": "idle", "task": None}
    parts = task.split("|")
    return {
        "status": "active",
        "task": task,
        "project_id": parts[0] if parts else None,
        "domain": parts[1] if len(parts) > 1 else None,
        "timestamp": parts[2] if len(parts) > 2 else None
    }

def check_lock_files():
    """檢查鎖檔狀態"""
    locks = {}
    stale_count = 0
    now = time.time()
    try:
        for lf in EL_LOCKS.glob("*.lock"):
            content = read_file(lf)
            lock_time = int(content.strip()) if content.strip().isdigit() else 0
            age = now - lock_time if lock_time else 999999
            is_stale = age > 600
            if is_stale:
                stale_count += 1
            locks[lf.name] = {
                "lock_time": datetime.fromtimestamp(lock_time).strftime("%Y-%m-%d %H:%M:%S") if lock_time else "unknown",
                "age_seconds": int(age),
                "stale": is_stale
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "ok",
        "count": len(locks),
        "stale_count": stale_count,
        "locks": locks,
        "has_current_lock": (EL_LOCKS / "current.lock").exists()
    }

def check_project_completion_rate():
    """計算專案完成率"""
    try:
        projects_dir = EL_PROJECTS
        all_projects = [d for d in projects_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        
        total = len(all_projects)
        if total == 0:
            return {"total": 0, "completed": 0, "rate": 100}
        
        # Count projects with completed progress.md
        completed = 0
        recent = []
        for d in all_projects:
            pm = d / "progress.md"
            if pm.exists():
                content = pm.read_text()
                if "完成" in content or "completed" in content.lower():
                    completed += 1
                    recent.append(d.name)
        
        recent.sort(reverse=True)
        return {
            "total": total,
            "completed": completed,
            "rate": round(completed / total * 100, 1),
            "recent_projects": recent[:10]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_system_resources():
    """檢查系統資源"""
    try:
        # CPU load
        load1, load5, load15 = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        
        # Memory
        mem = run_cmd("free -m | awk 'NR==2{printf \"%s/%s\", $3, $2}'")
        mem_parts = mem.split("/") if "/" in mem else ["?", "?"]
        
        # Disk
        disk = run_cmd("df -h / | awk 'NR==2{print $5}'")
        
        # OpenClaw process
        openclaw = run_cmd("pgrep -f 'openclaw.*gateway' | wc -l")
        
        return {
            "load_1m": round(load1, 2),
            "load_5m": round(load5, 2),
            "memory_mb": f"{mem_parts[0]}/{mem_parts[1]}",
            "disk_usage": disk,
            "openclaw_running": int(openclaw) > 0 if openclaw.isdigit() else False
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_recent_activity():
    """檢查近期活動"""
    try:
        log_files = {
            "endless_mode": LOGS_DIR / "endless_mode.log",
            "lock_skip": LOGS_DIR / "lock_skip.log",
            "evolution": LOGS_DIR / "evolution_20260528.log",
        }
        
        activities = []
        for name, path in log_files.items():
            if path.exists():
                try:
                    lines = path.read_text().strip().split("\n")
                    if lines:
                        last = lines[-1][:100]
                        activities.append({"log": name, "last_line": last})
                except Exception:
                    pass
        
        return {"activities": activities}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_batch_progress():
    """檢查批次進度"""
    try:
        # Count EL_batch files in projects
        batch_files = list((EL_DIR / "endless_mode" / "projects").glob("EL_batch_*.md"))
        batch_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        recent_batches = []
        for bf in batch_files[:5]:
            content = bf.read_text()[:200]
            recent_batches.append({"name": bf.name, "preview": content[:80]})
        
        # Count completed projects today
        today = datetime.now().strftime("%Y-%m-%d")
        today_notes = list((EL_DIR / "notes").glob(f"{today}_*learning_report.md"))
        
        return {
            "batch_files_count": len(batch_files),
            "recent_batches": recent_batches,
            "today_reports": len(today_notes)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_dashboard_status():
    """檢查狀態網站更新狀況"""
    try:
        status_site = WORKSPACE / "status_dashboard"
        if not status_site.exists():
            return {"status": "not_deployed"}
        
        files = list(status_site.glob("*"))
        index_exists = (status_site / "index.html").exists()
        health_exists = (status_site / "system_health.json").exists()
        
        last_update = None
        if health_exists:
            mtime = (status_site / "system_health.json").stat().st_mtime
            last_update = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "status": "deployed" if index_exists else "incomplete",
            "files_count": len(files),
            "health_json_exists": health_exists,
            "last_health_update": last_update
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# === 主程式 ===
def main():
    print("🏥 Raphael System Health Monitor")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    health = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "3.0",
        "api_quota": check_api_quota(),
        "current_task": check_current_task(),
        "lock_files": check_lock_files(),
        "project_completion": check_project_completion_rate(),
        "system_resources": check_system_resources(),
        "recent_activity": check_recent_activity(),
        "batch_progress": check_batch_progress(),
        "dashboard_status": check_dashboard_status()
    }
    
    # 評估整體健康分數
    score = 100
    issues = []
    
    if health["lock_files"].get("stale_count", 0) > 0:
        score -= 10 * health["lock_files"]["stale_count"]
        issues.append(f"{health['lock_files']['stale_count']} stale lock(s)")
    
    if not health["system_resources"].get("openclaw_running", False):
        score -= 30
        issues.append("OpenClaw not running!")
    
    if health["current_task"].get("status") == "idle":
        score -= 10
        issues.append("No active task")
    
    health["health_score"] = max(0, score)
    health["health_issues"] = issues
    
    # 輸出 JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON output: {OUTPUT_JSON}")
    
    # 輸出 Markdown 報告
    md = f"""# 🏥 Raphael 系統健康報告

**時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**健康分數**: {health['health_score']}/100

## 健康狀況

| 檢查項目 | 狀態 | 說明 |
|----------|------|------|
| OpenClaw 運行 | {'✅ 正常' if health['system_resources'].get('openclaw_running') else '❌ 停止'} | Load: {health['system_resources'].get('load_1m', '?')} |
| 鎖檔管理 | {'✅ 正常' if health['lock_files'].get('stale_count', 0) == 0 else f'⚠️ {health["lock_files"]["stale_count"]} 過期'} | {health['lock_files'].get('count', 0)} 個鎖檔 |
| 專案完成率 | {health['project_completion'].get('rate', 0)}% | {health['project_completion'].get('completed', 0)}/{health['project_completion'].get('total', 0)} 完成 |
| 狀態網站 | {'✅ 已部署' if health['dashboard_status'].get('status') == 'deployed' else '❌ 未部署'} | {health['dashboard_status'].get('last_health_update', 'N/A')} |
| 當前任務 | {'✅ ' + health['current_task'].get('task', '')[:50] if health['current_task'].get('status') == 'active' else '🔴 空閒'} | |

## 系統資源

- **負載**: {health['system_resources'].get('load_1m', '?')} (1m) / {health['system_resources'].get('load_5m', '?')} (5m)
- **記憶體**: {health['system_resources'].get('memory_mb', '?')}
- **磁碟**: {health['system_resources'].get('disk_usage', '?')}

## 待處理問題

{chr(10).join([f'- ⚠️ {issue}' for issue in issues]) if issues else '- ✅ 無重大問題'}

## 近期專案 ({health['project_completion'].get('total', 0)} 個)

{chr(10).join([f'- {p}' for p in health['project_completion'].get('recent_projects', [])[:8]]) if health['project_completion'].get('recent_projects') else '- 無記錄'}

---
*拉斐爾無盡學習系統 v3.0 | 自動生成*
"""
    
    with open(OUTPUT_MD, "w") as f:
        f.write(md)
    print(f"✅ Markdown report: {OUTPUT_MD}")
    
    # 印出摘要
    print()
    print(f"🏥 健康分數: {health['health_score']}/100")
    if issues:
        print("⚠️  問題:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ 無重大問題")
    
    print()
    print(f"📊 專案完成率: {health['project_completion'].get('rate', 0)}% ({health['project_completion'].get('completed', 0)}/{health['project_completion'].get('total', 0)})")
    print(f"🔒 鎖檔: {health['lock_files'].get('count', 0)} ({health['lock_files'].get('stale_count', 0)} 過期)")
    print(f"📡 OpenClaw: {'✅ 運行中' if health['system_resources'].get('openclaw_running') else '❌ 停止'}")

if __name__ == "__main__":
    main()
