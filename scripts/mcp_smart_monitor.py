#!/usr/bin/env python3
"""
MCP Smart Health Monitor - 改良版
自動檢測、診斷、並提供復原建議給 MCP 服務
"""

import json
import subprocess
import psutil
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# === 設定 ===
WORKSPACE = Path("/home/hoonsoropenclaw/.hermes")
CONFIG_FILE = Path.home() / ".hermes" / "config.yaml"
LOG_DIR = Path("/tmp/openclaw")
STATE_DIR = WORKSPACE / "mcp_health"
LAST_STATE = STATE_DIR / "last_check.json"

STATE_DIR.mkdir(parents=True, exist_ok=True)

# === MCP Server 配置（從 openclaw.json 讀取）===
def load_mcp_servers() -> Dict[str, Dict]:
    """從 openclaw.json 動態載入 MCP 設定"""
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        return config.get("mcp", {}).get("servers", {})
    except Exception as e:
        print(f"[WARN] 無法讀取 openclaw.json: {e}")
        return {}

def get_process_tree() -> Dict[str, Dict]:
    """取得所有 MCP 相關行程"""
    processes = {}
    mcp_servers = load_mcp_servers()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            cmdline = info.get('cmdline', [])
            if not cmdline or len(cmdline) < 1:
                continue
            cmd_str = ' '.join(cmdline)
            
            # 遍歷所有 MCP server 配置，嘗試匹配
            for name, cfg in mcp_servers.items():
                cmd = cfg.get('command', '')
                args = cfg.get('args', [])
                
                # 簡單匹配：config 中的 command 是否出現在 cmdline 字串中
                if cmd and cmd in cmd_str:
                    if name not in processes:  # 不要覆蓋已存在的
                        processes[name] = {
                            'pid': info['pid'],
                            'cmdline': cmd_str[:100],
                            'cpu_percent': info.get('cpu_percent', 0),
                            'memory_mb': info['memory_info'].rss / 1024 / 1024 if info.get('memory_info') else 0,
                            'healthy': True,
                            'config': cfg
                        }
                    break
        except (psutil.NoProcess, psutil.AccessDenied):
            pass
    return processes

def get_system_resources() -> Dict[str, Any]:
    """取得系統資源使用狀況"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
    except:
        cpu_percent = 0.0
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
    
    return {
        "cpu_percent": round(cpu_percent, 1),
        "load_1m": round(load[0], 2),
        "load_5m": round(load[1], 2),
        "memory_percent": memory.percent,
        "memory_available_mb": round(memory.available / 1024 / 1024, 0),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 1)
    }

def check_gateway_status() -> Dict[str, Any]:
    """檢查 OpenClaw Gateway 狀態"""
    try:
        result = subprocess.run(
            ['openclaw', 'status'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return {"status": "healthy", "raw": result.stdout[:200]}
        return {"status": "degraded", "error": result.stderr[:100]}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except FileNotFoundError:
        return {"status": "unknown", "error": "openclaw CLI not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def analyze_mcp_failure(server_name: str, config: Dict) -> Dict[str, Any]:
    """分析單一 MCP 服務失敗原因，提供復原指令"""
    cmd = config.get('command', '')
    args = config.get('args', [])
    env = config.get('env', {})
    
    diagnosis = {
        "server": server_name,
        "command": cmd,
        "args": args,
        "env_keys": list(env.keys()),
        "likely_causes": [],
        "recovery_commands": []
    }
    
    # 檢查環境變數
    missing_env = []
    for key in env:
        if key not in os.environ and key not in ['HOME', 'USER']:
            missing_env.append(key)
    if missing_env:
        diagnosis["likely_causes"].append(f"環境變數缺失: {', '.join(missing_env)}")
    
    # 檢查執行檔
    if cmd.startswith('/'):
        if not Path(cmd).exists():
            diagnosis["likely_causes"].append(f"執行檔不存在: {cmd}")
    else:
        which_result = subprocess.run(['which', cmd], capture_output=True, text=True)
        if not which_result.stdout.strip():
            diagnosis["likely_causes"].append(f"命令不在 PATH 中: {cmd}")
    
    # 生成復原指令
    if cmd:
        env_str = ' '.join([f'{k}="{v}"' for k, v in env.items()])
        full_cmd = f"{env_str} {cmd} {' '.join(args)}".strip()
        diagnosis["recovery_commands"].append(full_cmd)
        
        # 測試模式的指令
        diagnosis["recovery_commands"].append(f"cd ~ && {full_cmd} &")
    
    return diagnosis

def generate_full_report() -> Dict[str, Any]:
    """產生完整健康報告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    mcp_servers = load_mcp_servers()
    processes = get_process_tree()
    resources = get_system_resources()
    gateway = check_gateway_status()
    
    # 計算狀態
    expected_servers = list(mcp_servers.keys())
    running_servers = list(processes.keys())
    missing_servers = [s for s in expected_servers if s not in running_servers]
    
    # 計算健康分數
    score = 100
    issues = []
    
    if gateway['status'] == 'timeout':
        score -= 20  # Gateway timeout but still running
    elif gateway['status'] != 'healthy':
        score -= 40
        issues.append(f"Gateway {'timeout' if gateway['status'] == 'timeout' else 'degraded'}")
    
    if missing_servers:
        score -= 15 * len(missing_servers)
        issues.append(f"{len(missing_servers)} MCP servers not running")
    
    if resources['memory_percent'] > 85:
        score -= 20
        issues.append(f"Memory high: {resources['memory_percent']}%")
    
    if resources['load_1m'] > 3:
        score -= 10
        issues.append(f"Load high: {resources['load_1m']}")
    
    # 詳細分析缺失的 servers
    diagnoses = {}
    for name in missing_servers:
        if name in mcp_servers:
            diagnoses[name] = analyze_mcp_failure(name, mcp_servers[name])
    
    return {
        "timestamp": timestamp,
        "health_score": max(0, score),
        "issues": issues,
        "mcp_servers": {
            "expected": expected_servers,
            "running": running_servers,
            "missing": missing_servers,
            "count": len(expected_servers),
            "running_count": len(running_servers)
        },
        "processes": processes,
        "diagnoses": diagnoses,
        "resources": resources,
        "gateway": gateway
    }

def print_report(report: Dict[str, Any]):
    """美化輸出報告"""
    print(f"\n{'='*60}")
    print(f"📊 MCP Smart Health Report - {report['timestamp']}")
    print(f"{'='*60}")
    
    # 健康分數
    score = report['health_score']
    if score >= 80:
        emoji, color = "✅", "Healthy"
    elif score >= 50:
        emoji, color = "⚠️", "Degraded"
    else:
        emoji, color = "🚨", "Critical"
    print(f"\n{emoji} Health Score: {score}/100 ({color})")
    
    # MCP Servers
    mc = report['mcp_servers']
    print(f"\n📡 MCP Servers ({mc['running_count']}/{mc['count']}):")
    
    # 運行的 servers
    for name in mc['running']:
        proc = report['processes'].get(name, {})
        print(f"  ✓ {name}: PID={proc.get('pid','?')}, MEM={proc.get('memory_mb',0):.0f}MB")
    
    # 缺失的 servers
    for name in mc['missing']:
        diag = report['diagnoses'].get(name, {})
        print(f"  ✗ {name}: NOT RUNNING")
        causes = diag.get('likely_causes', [])
        if causes:
            for cause in causes:
                print(f"      → {cause}")
    
    # 系統資源
    r = report['resources']
    print(f"\n💻 System Resources:")
    print(f"  Load: {r['load_1m']} (1m) / {r['load_5m']} (5m)")
    print(f"  Memory: {r['memory_percent']:.1f}% ({r['memory_available_mb']:.0f}MB avail)")
    print(f"  Disk: {r['disk_percent']:.1f}% ({r['disk_free_gb']}GB free)")
    
    # Gateway
    gw = report['gateway']
    gw_emoji = "✅" if gw['status'] == 'healthy' else "⚠️"
    print(f"\n🚪 Gateway: {gw_emoji} {gw.get('status', 'unknown').upper()}")
    
    # 問題摘要
    if report['issues']:
        print(f"\n⚠️  Issues:")
        for issue in report['issues']:
            print(f"   - {issue}")

def export_json(report: Dict[str, Any], output_path: Path):
    """匯出 JSON 報告"""
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON exported: {output_path}")

def main():
    # 產生報告
    report = generate_full_report()
    
    # 顯示報告
    print_report(report)
    
    # 匯出 JSON
    output_json = WORKSPACE / "status_dashboard" / "mcp_health.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    export_json(report, output_json)
    
    # 保存狀態
    state = {
        "timestamp": report["timestamp"],
        "health_score": report["health_score"],
        "missing_servers": report["mcp_servers"]["missing"],
        "running_count": report["mcp_servers"]["running_count"],
        "count": report["mcp_servers"]["count"]
    }
    with open(LAST_STATE, 'w') as f:
        json.dump(state, f, indent=2)
    
    # 返回健康分數作為 exit code
    exit(0 if report['health_score'] >= 80 else 1)

if __name__ == "__main__":
    main()
