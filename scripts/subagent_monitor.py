#!/usr/bin/env python3
"""
OpenClaw Subagent Monitor & Task Manager
拉斐爾無盡學習系統 - Subagent 優化工具
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

# 嘗試讀取 OpenClaw 配置
CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"

def get_openclaw_sessions() -> dict:
    """取得目前所有 sessions"""
    try:
        result = subprocess.run(
            ["openclaw", "sessions", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"取得 sessions 失敗: {e}")
    return {}

def get_subagent_stats(sessions: dict) -> dict:
    """分析 subagent 統計"""
    active_subagents = []
    completed_subagents = []
    
    for session in sessions.get("sessions", []):
        if "subagent" in session.get("session_key", ""):
            info = {
                "session_key": session.get("session_key"),
                "status": session.get("status", "unknown"),
                "model": session.get("model", "unknown"),
                "created": session.get("created_at", "unknown")
            }
            if session.get("status") == "active":
                active_subagents.append(info)
            else:
                completed_subagents.append(info)
    
    return {
        "active_count": len(active_subagents),
        "completed_count": len(completed_subagents),
        "active_subagents": active_subagents,
        "completed_subagents": completed_subagents[-10:]  # 最近10個
    }

def create_subagent_task(task_name: str, task_description: str, model: str = "deepseek") -> dict:
    """
    建立 subagent 任務範本
    這是一個任務描述生成器，不是實際執行
    """
    return {
        "task_name": task_name,
        "task_description": task_description,
        "model": model,
        "created_at": datetime.now().isoformat(),
        "status": "template_ready"
    }

def generate_spawn_command(task: dict, context: str = "isolated") -> str:
    """
    生成 sessions_spawn 命令
    實際執行需要手動或透過 API
    """
    task_name = task.get("task_name", "unnamed_task")
    task_desc = task.get("task_description", "")
    model = task.get("model", "deepseek")
    
    # 這裡生成的是任務範本，實際 subagent 需透過 OpenClaw API spawn
    return f"""
# Subagent Spawn 範例命令
# 實際執行需透過 OpenClaw sessions_spawn tool

task: {task_desc}
context: {context}  # 'isolated' 或 'fork'
model: {model}
"""

def print_dashboard():
    """列印監控儀表板"""
    sessions = get_openclaw_sessions()
    stats = get_subagent_stats(sessions)
    
    print("=" * 60)
    print("🦞 拉斐爾 Subagent 監控儀表板")
    print("=" * 60)
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"活躍 Subagent: {stats['active_count']}")
    print(f"已完成 Subagent: {stats['completed_count']}")
    print("-" * 60)
    
    if stats['active_subagents']:
        print("🔄 活躍 Subagent:")
        for sa in stats['active_subagents']:
            print(f"  - {sa['session_key']} | {sa['status']} | {sa['model']}")
    else:
        print("📭 無活躍 Subagent")
    
    if stats['completed_subagents']:
        print("\n✅ 最近完成的 Subagent:")
        for sa in stats['completed_subagents']:
            print(f"  - {sa['session_key']} | {sa['model']}")
    
    print("=" * 60)

def main():
    """主程式"""
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw Subagent Monitor")
    parser.add_argument("--dashboard", "-d", action="store_true", help="顯示監控儀表板")
    parser.add_argument("--stats", "-s", action="store_true", help="顯示統計資訊")
    parser.add_argument("--create-task", "-c", nargs=2, metavar=("NAME", "DESC"), help="建立任務範本")
    
    args = parser.parse_args()
    
    if args.dashboard:
        print_dashboard()
    elif args.create_task:
        task = create_subagent_task(args.create_task[0], args.create_task[1])
        print(json.dumps(task, indent=2, ensure_ascii=False))
    else:
        print_dashboard()

if __name__ == "__main__":
    main()