"""
metrics.py — 系統資源指標蒐集
============================

純 psutil 實作，不呼叫外部命令。
回傳結構：list[Finding] —— 讓 alerts 模組統一處理。

Finding 結構：
{
    "key":      "cpu_percent",     # 唯一識別
    "level":    "warn" | "crit",
    "value":    87.5,
    "threshold": 80.0,
    "message":  "CPU 87.5% > 80%",
    "context":  {...},             # 額外資訊（cpu_count, mode, ...）
}
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import psutil

from config import thresholds as T


@dataclass
class Finding:
    key: str
    level: str            # "warn" | "crit"
    value: float
    threshold: float
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        """用於 cooldown 抑制的 fingerprint。

        同樣的 key + level + 同一個小時 → 同一個 fingerprint
        （避免同一個 warn 在 1 分鐘內重複發 60 次）
        """
        import datetime
        bucket = datetime.datetime.now().strftime("%Y-%m-%d:%H")
        return f"{self.key}:{self.level}:{bucket}"


# ---------------------------------------------------------------------------
# 資源採樣
# ---------------------------------------------------------------------------
def _sample_cpu() -> tuple[float, int]:
    """回傳 (cpu_percent, cpu_count)"""
    # 第一次呼叫會回 0，所以這裡 call 兩次（interval 給 1.0s）
    psutil.cpu_percent(interval=None)  # warm-up
    cpu = psutil.cpu_percent(interval=T.CPU_SAMPLE_INTERVAL_SEC)
    return float(cpu), int(psutil.cpu_count(logical=True) or 1)


def _sample_mem() -> dict[str, float]:
    v = psutil.virtual_memory()
    return {
        "percent": float(v.percent),
        "used_gb": round(v.used / (1024 ** 3), 2),
        "total_gb": round(v.total / (1024 ** 3), 2),
        "available_gb": round(v.available / (1024 ** 3), 2),
    }


def _sample_disks() -> list[dict[str, float]]:
    """跳過 virtual fs（tmpfs / overlay / devtmpfs / sysfs / proc）"""
    out = []
    SKIP_FSTYPES = {
        "tmpfs", "devtmpfs", "devpts", "sysfs", "proc", "cgroup",
        "cgroup2", "securityfs", "bpf", "autofs", "mqueue", "pstore",
        "debugfs", "tracefs", "hugetlbfs", "configfs", "fusectl",
        "ramfs", "binfmt_misc", "nsfs", "fuse.gvfsd-fuse",
    }
    for part in psutil.disk_partitions(all=False):
        if part.fstype in SKIP_FSTYPES:
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        out.append({
            "mountpoint": part.mountpoint,
            "device": part.device,
            "fstype": part.fstype,
            "percent": float(u.percent),
            "used_gb": round(u.used / (1024 ** 3), 2),
            "total_gb": round(u.total / (1024 ** 3), 2),
        })
    return out


def _sample_load() -> tuple[float, int]:
    la1 = float(psutil.getloadavg()[0])
    cpu_count = int(psutil.cpu_count(logical=True) or 1)
    return la1, cpu_count


def _sample_zombies() -> int:
    """統計當前所有狀態 == ZOMBIE 的 process 數量。"""
    import psutil
    n = 0
    for p in psutil.process_iter(["status"]):
        try:
            if p.info["status"] == psutil.STATUS_ZOMBIE:
                n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return n


# ---------------------------------------------------------------------------
# 主進入點：resource_finding()
# ---------------------------------------------------------------------------
def collect_all() -> list[Finding]:
    """跑所有資源檢查，回傳 findings 列表。"""
    findings: list[Finding] = []

    # CPU
    cpu, cpu_count = _sample_cpu()
    if cpu >= T.CPU_PERCENT_CRIT:
        findings.append(Finding(
            key="cpu_percent",
            level="crit",
            value=cpu,
            threshold=T.CPU_PERCENT_CRIT,
            message=f"CPU {cpu:.1f}% >= crit {T.CPU_PERCENT_CRIT}%",
            context={"cpu_count": cpu_count},
        ))
    elif cpu >= T.CPU_PERCENT_WARN:
        findings.append(Finding(
            key="cpu_percent",
            level="warn",
            value=cpu,
            threshold=T.CPU_PERCENT_WARN,
            message=f"CPU {cpu:.1f}% >= warn {T.CPU_PERCENT_WARN}%",
            context={"cpu_count": cpu_count},
        ))

    # MEM
    m = _sample_mem()
    if m["percent"] >= T.MEM_PERCENT_CRIT:
        findings.append(Finding(
            key="mem_percent",
            level="crit",
            value=m["percent"],
            threshold=T.MEM_PERCENT_CRIT,
            message=f"RAM {m['percent']:.1f}% ({m['used_gb']}G/{m['total_gb']}G) >= crit {T.MEM_PERCENT_CRIT}%",
            context=m,
        ))
    elif m["percent"] >= T.MEM_PERCENT_WARN:
        findings.append(Finding(
            key="mem_percent",
            level="warn",
            value=m["percent"],
            threshold=T.MEM_PERCENT_WARN,
            message=f"RAM {m['percent']:.1f}% ({m['used_gb']}G/{m['total_gb']}G) >= warn {T.MEM_PERCENT_WARN}%",
            context=m,
        ))

    # DISK
    for d in _sample_disks():
        mp = d["mountpoint"]
        if d["percent"] >= T.DISK_PERCENT_CRIT:
            findings.append(Finding(
                key=f"disk_percent:{mp}",
                level="crit",
                value=d["percent"],
                threshold=T.DISK_PERCENT_CRIT,
                message=f"Disk {mp} {d['percent']:.1f}% ({d['used_gb']}G/{d['total_gb']}G) >= crit {T.DISK_PERCENT_CRIT}%",
                context=d,
            ))
        elif d["percent"] >= T.DISK_PERCENT_WARN:
            findings.append(Finding(
                key=f"disk_percent:{mp}",
                level="warn",
                value=d["percent"],
                threshold=T.DISK_PERCENT_WARN,
                message=f"Disk {mp} {d['percent']:.1f}% ({d['used_gb']}G/{d['total_gb']}G) >= warn {T.DISK_PERCENT_WARN}%",
                context=d,
            ))

    # LOAD
    la1, cpu_count = _sample_load()
    la_per_cpu = la1 / cpu_count
    if la_per_cpu >= T.LOAD_AVG_PER_CPU_CRIT:
        findings.append(Finding(
            key="load_avg",
            level="crit",
            value=la1,
            threshold=T.LOAD_AVG_PER_CPU_CRIT * cpu_count,
            message=f"Load avg {la1:.2f} (per-cpu {la_per_cpu:.2f}) >= crit {T.LOAD_AVG_PER_CPU_CRIT}",
            context={"per_cpu": la_per_cpu, "cpu_count": cpu_count},
        ))
    elif la_per_cpu >= T.LOAD_AVG_PER_CPU_WARN:
        findings.append(Finding(
            key="load_avg",
            level="warn",
            value=la1,
            threshold=T.LOAD_AVG_PER_CPU_WARN * cpu_count,
            message=f"Load avg {la1:.2f} (per-cpu {la_per_cpu:.2f}) >= warn {T.LOAD_AVG_PER_CPU_WARN}",
            context={"per_cpu": la_per_cpu, "cpu_count": cpu_count},
        ))

    # ZOMBIE
    z = _sample_zombies()
    if z >= T.ZOMBIE_COUNT_CRIT:
        findings.append(Finding(
            key="zombie_count",
            level="crit",
            value=float(z),
            threshold=float(T.ZOMBIE_COUNT_CRIT),
            message=f"Zombie processes {z} >= crit {T.ZOMBIE_COUNT_CRIT}",
            context={"zombie_count": z},
        ))
    elif z >= T.ZOMBIE_COUNT_WARN:
        findings.append(Finding(
            key="zombie_count",
            level="warn",
            value=float(z),
            threshold=float(T.ZOMBIE_COUNT_WARN),
            message=f"Zombie processes {z} >= warn {T.ZOMBIE_COUNT_WARN}",
            context={"zombie_count": z},
        ))

    return findings


# ---------------------------------------------------------------------------
# 自我健康
# ---------------------------------------------------------------------------
def self_check() -> dict[str, Any]:
    """回傳本次的資源快照（給 report 用，不需要警報）。"""
    cpu, cpu_count = _sample_cpu()
    m = _sample_mem()
    disks = _sample_disks()
    la1, _ = _sample_load()
    z = _sample_zombies()
    return {
        "cpu_percent": cpu,
        "cpu_count": cpu_count,
        "mem": m,
        "disks": disks,
        "load_avg_1": la1,
        "zombie_count": z,
        "boot_time": psutil.boot_time(),
        "process_count": len(psutil.pids()),
    }
