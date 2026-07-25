#!/usr/bin/env python3
"""
N100 System Monitor - OpenClaw Integration
系統監控腳本，支援 CPU、記憶體、磁碟、網路監控
並可與 OpenClaw 無縫整合
"""

import psutil
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import argparse


class SystemMonitor:
    """N100 系統監控器"""
    
    def __init__(self):
        self.boot_time = psutil.boot_time()
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_check = time.time()
    
    def get_cpu_info(self) -> Dict:
        """取得 CPU 資訊"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # CPU 溫度（如果可用）
        temps = {}
        try:
            temps = psutil.sensors_temperatures()
        except:
            pass
        
        return {
            "percent": cpu_percent,
            "count": cpu_count,
            "freq_mhz": cpu_freq.current if cpu_freq else None,
            "temps": temps
        }
    
    def get_memory_info(self) -> Dict:
        """取得記憶體資訊"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": swap.percent
        }
    
    def get_disk_info(self) -> List[Dict]:
        """取得磁碟資訊"""
        partitions = psutil.disk_partitions()
        disks = []
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent
                })
            except PermissionError:
                continue
        
        return disks
    
    def get_disk_io(self) -> Dict:
        """取得磁碟 I/O 速率"""
        current = psutil.disk_io_counters()
        now = time.time()
        interval = now - self.last_check
        
        read_bytes = current.read_bytes - self.last_disk_io.read_bytes
        write_bytes = current.write_bytes - self.last_disk_io.write_bytes
        
        self.last_disk_io = current
        self.last_check = now
        
        return {
            "read_mb_s": round((read_bytes / interval) / (1024**2), 2),
            "write_mb_s": round((write_bytes / interval) / (1024**2), 2),
            "total_read_mb": round(current.read_bytes / (1024**2), 2),
            "total_write_mb": round(current.write_bytes / (1024**2), 2)
        }
    
    def get_network_info(self) -> Dict:
        """取得網路資訊"""
        net = psutil.net_io_counters()
        now = time.time()
        interval = now - self.last_check
        
        sent_bytes = net.bytes_sent - self.last_net_io.bytes_sent
        recv_bytes = net.bytes_recv - self.last_net_io.bytes_recv
        
        self.last_net_io = net
        self.last_check = now
        
        return {
            "sent_mb_s": round((sent_bytes / interval) / (1024**2), 2),
            "recv_mb_s": round((recv_bytes / interval) / (1024**2), 2),
            "total_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "total_recv_mb": round(net.bytes_recv / (1024**2), 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errors": net.errin + net.errout,
            "drops": net.dropin + net.dropout
        }
    
    def get_processes(self, top: int = 10) -> List[Dict]:
        """取得耗費資源最多的程序"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 按 CPU 使用率排序
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return processes[:top]
    
    def get_uptime(self) -> Dict:
        """取得系統運行時間"""
        uptime_seconds = time.time() - self.boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        return {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "total_seconds": int(uptime_seconds)
        }
    
    def get_all(self) -> Dict:
        """取得所有監控資料"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disks": self.get_disk_info(),
            "disk_io": self.get_disk_io(),
            "network": self.get_network_info(),
            "uptime": self.get_uptime()
        }
    
    def format_text(self, data: Optional[Dict] = None) -> str:
        """格式化輸出為易讀文字"""
        if data is None:
            data = self.get_all()
        
        lines = [
            "═" * 50,
            "  N100 系統監控報告",
            "  " + data["timestamp"],
            "═" * 50,
            "",
            "📊 CPU",
            f"   使用率: {data['cpu']['percent']}%",
            f"  核心數: {data['cpu']['count']}",
            f"   頻率: {data['cpu']['freq_mhz']} MHz" if data['cpu']['freq_mhz'] else "   頻率: N/A",
            "",
            "🧠 記憶體",
            f"   總計: {data['memory']['total_gb']} GB",
            f"   使用: {data['memory']['used_gb']} GB ({data['memory']['percent']}%)",
            f"   可用: {data['memory']['available_gb']} GB",
            "",
            "💾 磁碟",
        ]
        
        for disk in data['disks']:
            lines.append(f"   {disk['mountpoint']} ({disk['fstype']})")
            lines.append(f"     總計: {disk['total_gb']} GB | 使用: {disk['percent']}%")
        
        lines.extend([
            "",
            "🌐 網路",
            f"   上傳: {data['network']['sent_mb_s']} MB/s",
            f"   下載: {data['network']['recv_mb_s']} MB/s",
            f"   總傳輸: {data['network']['total_sent_mb']} MB 上傳 / {data['network']['total_recv_mb']} MB 下載",
            "",
            "⏱️ 運行時間",
            f"   {data['uptime']['days']} 天 {data['uptime']['hours']} 小時 {data['uptime']['minutes']} 分鐘",
            "═" * 50
        ])
        
        return "\n".join(lines)


def continuous_monitor(interval: int = 5, count: Optional[int] = None):
    """持續監控模式"""
    monitor = SystemMonitor()
    iteration = 0
    
    print("開始 N100 系統監控 (Ctrl+C 停止)")
    print(f"更新間隔: {interval} 秒")
    print()
    
    try:
        while count is None or iteration < count:
            print(monitor.format_text(), end="\033[2J\033[H")
            time.sleep(interval)
            iteration += 1
    except KeyboardInterrupt:
        print("\n監控已停止")


def main():
    parser = argparse.ArgumentParser(description="N100 系統監控工具")
    parser.add_argument("-j", "--json", action="store_true", help="JSON 格式輸出")
    parser.add_argument("-c", "--continuous", action="store_true", help="持續監控模式")
    parser.add_argument("-i", "--interval", type=int, default=5, help="監控間隔（秒）")
    parser.add_argument("-n", "--count", type=int, help="監控次數")
    parser.add_argument("-o", "--output", type=str, help="輸出到檔案")
    
    args = parser.parse_args()
    
    monitor = SystemMonitor()
    
    if args.continuous:
        continuous_monitor(args.interval, args.count)
    else:
        data = monitor.get_all()
        output = json.dumps(data, indent=2) if args.json else monitor.format_text(data)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"已儲存至 {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()