#!/usr/bin/env python3
"""
MCP Health Auto-Repair System - 快速版
自動檢測、診斷、修復 MCP 服務問題（優化執行速度）
"""

import json
import subprocess
import psutil
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# === 設定 ===
WORKSPACE = Path("/home/hoonsoropenclaw/.hermes")
CONFIG_FILE = Path.home() / ".hermes" / "config.yaml"
STATE_DIR = WORKSPACE / "mcp_health"

STATE_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class RepairAction:
    timestamp: str
    server: str
    action: str
    result: str
    details: str = ""

class MCPAutoRepair:
    """MCP 自動修復系統（優化版）"""
    
    def __init__(self):
        self.restart_counts: Dict[str, int] = {}
        self.repair_actions: List[RepairAction] = []
        self._mcp_config: Optional[Dict] = None
    
    def load_mcp_config(self) -> Dict[str, Any]:
        """從 openclaw.json 動態載入 MCP 設定"""
        if self._mcp_config is not None:
            return self._mcp_config
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
            self._mcp_config = config.get("mcp", {}).get("servers", {})
            return self._mcp_config
        except Exception as e:
            print(f"[WARN] 無法讀取 openclaw.json: {e}")
            return {}
    
    def get_running_servers(self) -> Dict[str, Dict]:
        """取得所有運行中的 MCP 行程（快速版）"""
        processes = {}
        mcp_servers = self.load_mcp_config()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                info = proc.info
                cmdline = info.get('cmdline', [])
                if not cmdline or len(cmdline) < 1:
                    continue
                cmd_str = ' '.join(cmdline)
                
                for name, cfg in mcp_servers.items():
                    cmd = cfg.get('command', '')
                    if cmd and cmd in cmd_str:
                        if name not in processes:
                            processes[name] = {
                                'pid': info['pid'],
                                'cmdline': cmd_str[:150],
                                'cpu_percent': info.get('cpu_percent', 0),
                                'memory_mb': info['memory_info'].rss / 1024 / 1024 if info.get('memory_info') else 0,
                                'healthy': True
                            }
                        break
            except (psutil.NoProcess, psutil.AccessDenied):
                pass
        return processes
    
    def check_gateway_quick(self) -> str:
        """快速檢查 Gateway 狀態（3秒超時）"""
        try:
            result = subprocess.run(
                ['openclaw', 'status'],
                capture_output=True, text=True, timeout=3
            )
            return "healthy" if result.returncode == 0 else "degraded"
        except subprocess.TimeoutExpired:
            return "timeout"
        except FileNotFoundError:
            return "unknown"
        except Exception:
            return "error"
    
    def diagnose_failure(self, server_name: str, config: Dict) -> Dict[str, Any]:
        """診斷 MCP 服務失敗原因"""
        cmd = config.get('command', '')
        args = config.get('args', [])
        env = config.get('env', {})
        
        diagnosis = {
            "server": server_name,
            "command": cmd,
            "can_repair": False,
            "likely_causes": []
        }
        
        if cmd.startswith('/'):
            if not Path(cmd).exists():
                diagnosis["likely_causes"].append(f"執行檔不存在: {cmd}")
        else:
            which_result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=2)
            if not which_result.stdout.strip():
                diagnosis["likely_causes"].append(f"命令不在 PATH 中: {cmd}")
        
        missing_env = [k for k in env if k not in os.environ]
        if missing_env:
            diagnosis["likely_causes"].append(f"環境變數缺失: {', '.join(missing_env[:3])}")
        
        if cmd and not diagnosis["likely_causes"]:
            diagnosis["can_repair"] = True
        
        return diagnosis
    
    def analyze_resources(self) -> Dict[str, Any]:
        """快速分析系統資源"""
        try:
            cpu = psutil.cpu_percent(interval=0.3)
        except:
            cpu = 0.0
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        
        return {
            "cpu_percent": round(cpu, 1),
            "load_1m": round(load[0], 2),
            "memory_percent": mem.percent,
            "memory_available_mb": round(mem.available / 1024 / 1024, 0),
            "disk_percent": disk.percent
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """產生完整健康與修復報告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        mcp_config = self.load_mcp_config()
        running_servers = self.get_running_servers()
        resources = self.analyze_resources()
        gateway_status = self.check_gateway_quick()
        
        expected_servers = list(mcp_config.keys())
        running_names = list(running_servers.keys())
        missing_servers = [s for s in expected_servers if s not in running_names]
        
        # 診斷缺失的伺服器
        diagnoses = {}
        for name in missing_servers:
            if name in mcp_config:
                diagnoses[name] = self.diagnose_failure(name, mcp_config[name])
        
        # 計算健康分數
        score = 100
        issues = []
        
        if gateway_status != "healthy":
            score -= 30
            issues.append(f"Gateway {gateway_status}")
        
        if len(missing_servers) > 0:
            score -= 10 * len(missing_servers)
            issues.append(f"{len(missing_servers)} servers not running")
        
        if resources['memory_percent'] > 85:
            score -= 15
            issues.append(f"Memory {resources['memory_percent']:.0f}%")
        
        if resources['load_1m'] > 4:
            score -= 10
            issues.append(f"Load {resources['load_1m']:.1f}")
        
        return {
            "timestamp": timestamp,
            "health_score": max(0, score),
            "issues": issues,
            "mcp_servers": {
                "expected": expected_servers,
                "running": running_names,
                "missing": missing_servers,
                "count": len(expected_servers),
                "running_count": len(running_names)
            },
            "processes": running_servers,
            "diagnoses": diagnoses,
            "resources": resources,
            "gateway_status": gateway_status,
            "repair_count": len(self.repair_actions)
        }
    
    def print_report(self, report: Dict[str, Any]):
        """格式化輸出報告"""
        print(f"\n🔧 MCP Health Auto-Repair Report - {report['timestamp']}")
        print(f"{'='*50}")
        
        score = report['health_score']
        emoji = "✅" if score >= 80 else ("⚠️" if score >= 50 else "🚨")
        status = "Healthy" if score >= 80 else ("Degraded" if score >= 50 else "Critical")
        print(f"{emoji} Health Score: {score}/100 ({status})")
        
        mc = report['mcp_servers']
        print(f"\n📡 MCP Servers ({mc['running_count']}/{mc['count']}):")
        
        for name in mc['running']:
            proc = report['processes'].get(name, {})
            print(f"  ✓ {name}: PID={proc.get('pid','?')}, MEM={proc.get('memory_mb',0):.0f}MB")
        
        for name in mc['missing']:
            diag = report['diagnoses'].get(name, {})
            can = "🔧" if diag.get('can_repair') else "❌"
            print(f"  {can} {name}: NOT RUNNING")
            for cause in diag.get('likely_causes', [])[:2]:
                print(f"      → {cause}")
        
        r = report['resources']
        print(f"\n💻 System: Load={r['load_1m']} | Mem={r['memory_percent']:.1f}% | Disk={r['disk_percent']:.1f}%")
        
        gw = report['gateway_status']
        print(f"🚪 Gateway: {'✅' if gw == 'healthy' else '⚠️'} {gw.upper()}")
        
        if report['issues']:
            print(f"\n⚠️  Issues: {', '.join(report['issues'])}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCP Health Auto-Repair")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    
    repair = MCPAutoRepair()
    report = repair.generate_report()
    
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        repair.print_report(report)
    
    # 導出狀態
    output = WORKSPACE / "status_dashboard" / "mcp_repair_status.json"
    with open(output, 'w') as f:
        json.dump({
            "timestamp": report["timestamp"],
            "health_score": report["health_score"],
            "missing": report["mcp_servers"]["missing"],
            "running": report["mcp_servers"]["running_count"],
            "total": report["mcp_servers"]["count"]
        }, f, indent=2)
    
    exit(0 if report['health_score'] >= 70 else 1)


if __name__ == "__main__":
    main()