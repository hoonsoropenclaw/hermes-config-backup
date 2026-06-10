#!/usr/bin/env python3
"""
MCP Server Health Monitor - N100 OpenClaw 專用
監控本機運行中的 MCP servers 健康狀態
"""

import json
import subprocess
import psutil
import time
from datetime import datetime
from typing import Dict, List, Any

# MCP Server 列表
MCP_SERVERS = {
    "mempalace": {"command": "python3", "args": ["-m", "mempalace.mcp_server"], "type": "python"},
    "github": {"command": "mcp-server-github", "type": "node"},
    "slack": {"command": "mcp-server-slack", "type": "node"},
    "brave-search": {"command": "mcp-server-brave-search", "type": "node"},
    "filesystem": {"command": "mcp-server-filesystem", "args": ["/home/hoonsoropenclaw/.hermes"], "type": "node"},
    "supabase": {"command": "supabase-mcp-server", "type": "node"},
    "notebooklm": {"command": "notebooklm-mcp", "args": ["server"], "type": "node"},
}

def get_process_tree() -> Dict[str, Dict]:
    """取得所有 MCP 相關行程"""
    processes = {}
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            cmdline = info.get('cmdline', [])
            if not cmdline:
                continue
            cmd_str = ' '.join(cmdline)
            
            for name, config in MCP_SERVERS.items():
                cmd = config['command']
                if cmd in cmd_str or (len(cmdline) > 1 and cmdline[-1].endswith(cmd.replace('mcp-server-', ''))):
                    processes[name] = {
                        'pid': info['pid'],
                        'cmdline': cmd_str,
                        'cpu_percent': info.get('cpu_percent', 0),
                        'memory_mb': info['memory_info'].rss / 1024 / 1024 if info.get('memory_info') else 0,
                        'healthy': True
                    }
        except (psutil.NoProcess, psutil.AccessDenied):
            pass
    return processes

def get_system_resources() -> Dict[str, Any]:
    """取得系統資源使用狀況"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_mb": memory.available / 1024 / 1024,
        "disk_percent": disk.percent,
        "disk_free_gb": disk.free / 1024 / 1024 / 1024
    }

def check_gateway_health() -> Dict[str, Any]:
    """檢查 OpenClaw Gateway 健康狀態"""
    try:
        # 嘗試讀取 gateway 狀態
        result = subprocess.run(
            ['openclaw', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "status": "healthy" if result.returncode == 0 else "degraded",
            "output": result.stdout[:500] if result.stdout else "",
            "error": result.stderr[:200] if result.stderr else ""
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Gateway check timed out"}
    except FileNotFoundError:
        return {"status": "unknown", "error": "openclaw CLI not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def generate_health_report() -> Dict[str, Any]:
    """產生完整健康報告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    processes = get_process_tree()
    resources = get_system_resources()
    gateway = check_gateway_health()
    
    # 計算健康狀態
    server_count = len(processes)
    expected_count = len(MCP_SERVERS)
    missing_servers = [name for name in MCP_SERVERS if name not in processes]
    
    if server_count == 0:
        overall_health = "critical"
    elif len(missing_servers) > 0:
        overall_health = "degraded"
    elif resources['memory_percent'] > 90 or resources['cpu_percent'] > 90:
        overall_health = "degraded"
    else:
        overall_health = "healthy"
    
    return {
        "timestamp": timestamp,
        "overall_health": overall_health,
        "servers": {
            "detected": server_count,
            "expected": expected_count,
            "missing": missing_servers,
            "details": processes
        },
        "resources": resources,
        "gateway": gateway
    }

def print_report(report: Dict[str, Any]):
    """格式化輸出報告"""
    print(f"\n{'='*60}")
    print(f"📊 MCP Server Health Report - {report['timestamp']}")
    print(f"{'='*60}")
    
    # 總體狀態
    emoji_map = {"healthy": "✅", "degraded": "⚠️", "critical": "🚨"}
    emoji = emoji_map.get(report['overall_health'], "❓")
    print(f"\n{emoji} Overall Status: {report['overall_health'].upper()}")
    
    # MCP Servers
    print(f"\n📡 MCP Servers ({report['servers']['detected']}/{report['servers']['expected']}):")
    if report['servers']['details']:
        for name, info in report['servers']['details'].items():
            print(f"  ✓ {name}: PID={info['pid']}, CPU={info['cpu_percent']:.1f}%, MEM={info['memory_mb']:.1f}MB")
    if report['servers']['missing']:
        for name in report['servers']['missing']:
            print(f"  ✗ {name}: NOT RUNNING")
    
    # 系統資源
    r = report['resources']
    print(f"\n💻 System Resources:")
    print(f"  CPU: {r['cpu_percent']:.1f}%")
    print(f"  Memory: {r['memory_percent']:.1f}% ({r['memory_available_mb']:.0f}MB available)")
    print(f"  Disk: {r['disk_percent']:.1f}% ({r['disk_free_gb']:.1f}GB free)")
    
    # Gateway
    gw = report['gateway']
    print(f"\n🚪 Gateway: {gw.get('status', 'unknown').upper()}")
    if gw.get('error'):
        print(f"  Error: {gw['error'][:100]}")

if __name__ == "__main__":
    report = generate_health_report()
    print_report(report)
    
    # 區域健康檢查模式
    if len(report['servers']['missing']) > 0:
        print(f"\n⚠️ Missing servers: {', '.join(report['servers']['missing'])}")
        exit(1)
    else:
        exit(0)
