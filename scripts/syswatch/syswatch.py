#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
syswatch.py - Linux system log + resource monitor with threshold alerting.

Usage:
    syswatch.py [--once] [--dry-run] [--json-only] [--config PATH]

Design principles (2026-07-27):
  - stdlib only (no third-party deps)
  - never embeds secret tokens in source (no *** filter trap)
  - falls back from /var/log/* to ~/.local/share/* on permission errors
  - cooldown between repeated alerts to prevent alert storms
  - emits both human console + structured JSON report (rotates daily)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
HOSTNAME = socket.gethostname()

UTC_NOW = lambda: datetime.now(timezone.utc)
ISO = lambda dt: dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ----------------------------- severity model -----------------------------

SEVERITY_ORDER = ["INFO", "WARN", "CRITICAL", "EMERGENCY"]
SEV_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}


def max_sev(a: str, b: str) -> str:
    return a if SEV_RANK[a] >= SEV_RANK[b] else b


# ----------------------------- config loader ------------------------------

DEFAULT_CONFIG_LOCATIONS = [
    "/home/hoonsoropenclaw/.hermes/scripts/syswatch/config.json",
    "./syswatch.config.json",
    "/etc/syswatch/config.json",
]


def load_config(path: str | None) -> dict:
    if path:
        candidates = [path]
    else:
        env = os.environ.get("SYSWATCH_CONFIG")
        candidates = [env] if env else []
        candidates += DEFAULT_CONFIG_LOCATIONS

    for c in candidates:
        try:
            with open(c, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
                cfg["_loaded_from"] = c
                return cfg
        except FileNotFoundError:
            continue
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[syswatch] WARN: failed to load config {c}: {exc}", file=sys.stderr)

    raise SystemExit(
        "[syswatch] ERROR: no usable config found. Tried:\n  "
        + "\n  ".join(candidates)
        + "\nSet SYSWATCH_CONFIG or pass --config PATH."
    )


# ----------------------------- alert dataclass ----------------------------

@dataclass
class Alert:
    category: str            # "cpu" | "memory" | "disk" | "swap" | "load" | "iowait" | "auth" | "oom" | "segfault" | "disk_error"
    severity: str            # "INFO" | "WARN" | "CRITICAL" | "EMERGENCY"
    metric: str              # human-readable metric name
    observed: Any            # numeric or string observation
    threshold: Any           # threshold value(s)
    detail: str = ""         # free-form context
    evidence: list[str] = field(default_factory=list)  # sampled log lines


# ----------------------------- resource checks ----------------------------

def read_loadavg() -> tuple[float, float, float]:
    raw = Path("/proc/loadavg").read_text().split()
    return float(raw[0]), float(raw[1]), float(raw[2])


def read_meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            num = v.strip().split()[0]
            out[k.strip()] = int(num)  # kB
    return out


def read_stat() -> dict[str, int]:
    """Aggregate /proc/stat CPU line (cpu line = aggregate across cores)."""
    cpu = {}
    for line in Path("/proc/stat").read_text().splitlines():
        if line.startswith("cpu "):
            parts = line.split()
            labels = ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal", "guest", "guest_nice"]
            for i, label in enumerate(labels):
                if i + 1 < len(parts):
                    cpu[label] = int(parts[i + 1])
            cpu["total"] = sum(cpu[l] for l in labels if l in cpu)
            cpu["busy"] = cpu["total"] - cpu.get("idle", 0) - cpu.get("iowait", 0)
            return cpu
    return cpu


def sample_cpu(prev: dict[str, int] | None, interval: float = 1.0) -> tuple[dict, float, float]:
    """Sample CPU twice with `interval` between samples. Returns (new_stat, busy%, iowait%)."""
    s1 = read_stat()
    if prev is None:
        time.sleep(interval)
        s2 = read_stat()
    else:
        s2 = read_stat()
        time.sleep(interval)
        s1 = prev  # reuse prior sample

    d_total = s2["total"] - s1["total"]
    d_busy = s2["busy"] - s1["busy"]
    d_iowait = s2.get("iowait", 0) - s1.get("iowait", 0)
    if d_total <= 0:
        return s2, 0.0, 0.0
    busy_pct = 100.0 * d_busy / d_total
    iowait_pct = 100.0 * d_iowait / d_total
    return s2, busy_pct, iowait_pct


def check_cpu_and_load(alerts: list[Alert], cfg: dict, ncpu: int) -> dict:
    th = cfg["thresholds"]
    # CPU + iowait sample
    _, cpu_pct, iowait_pct = sample_cpu(None, interval=1.0)

    if cpu_pct >= th["cpu_percent_critical"]:
        alerts.append(Alert("cpu", "CRITICAL", "cpu_busy_pct", round(cpu_pct, 1), th["cpu_percent_critical"]))
    elif cpu_pct >= th["cpu_percent_warn"]:
        alerts.append(Alert("cpu", "WARN", "cpu_busy_pct", round(cpu_pct, 1), th["cpu_percent_warn"]))

    if iowait_pct >= th["iowait_percent_critical"]:
        alerts.append(Alert("iowait", "CRITICAL", "iowait_pct", round(iowait_pct, 1), th["iowait_percent_critical"]))
    elif iowait_pct >= th["iowait_percent_warn"]:
        alerts.append(Alert("iowait", "WARN", "iowait_pct", round(iowait_pct, 1), th["iowait_percent_warn"]))

    # Load average (normalized per CPU)
    l1, l5, l15 = read_loadavg()
    l1_per_cpu = l1 / ncpu
    l5_per_cpu = l5 / ncpu
    worst = max(l1_per_cpu, l5_per_cpu)
    if worst >= th["load_per_cpu_critical"]:
        sev = "CRITICAL"
    elif worst >= th["load_per_cpu_warn"]:
        sev = "WARN"
    else:
        sev = "INFO"
    if sev != "INFO":
        alerts.append(Alert(
            "load", sev, "load_per_cpu",
            {"l1_per_cpu": round(l1_per_cpu, 2), "l5_per_cpu": round(l5_per_cpu, 2), "l15_raw": l15, "ncpu": ncpu},
            {"warn": th["load_per_cpu_warn"], "critical": th["load_per_cpu_critical"]},
        ))

    return {"cpu_busy_pct": round(cpu_pct, 1), "iowait_pct": round(iowait_pct, 1),
            "load1": l1, "load5": l5, "load15": l15, "load1_per_cpu": round(l1_per_cpu, 2)}


def check_memory(alerts: list[Alert], cfg: dict) -> dict:
    th = cfg["thresholds"]
    mem = read_meminfo()
    total = mem.get("MemTotal", 1)
    avail = mem.get("MemAvailable", mem.get("MemFree", 0))
    used_pct = 100.0 * (total - avail) / total if total else 0.0
    swap_total = mem.get("SwapTotal", 0)
    swap_free = mem.get("SwapFree", 0)
    swap_used_pct = 100.0 * (swap_total - swap_free) / swap_total if swap_total else 0.0

    if used_pct >= th["memory_percent_critical"]:
        alerts.append(Alert("memory", "CRITICAL", "mem_used_pct", round(used_pct, 1), th["memory_percent_critical"]))
    elif used_pct >= th["memory_percent_warn"]:
        alerts.append(Alert("memory", "WARN", "mem_used_pct", round(used_pct, 1), th["memory_percent_warn"]))

    if swap_total and swap_used_pct >= th["swap_percent_critical"]:
        alerts.append(Alert("swap", "CRITICAL", "swap_used_pct", round(swap_used_pct, 1), th["swap_percent_critical"]))
    elif swap_total and swap_used_pct >= th["swap_percent_warn"]:
        alerts.append(Alert("swap", "WARN", "swap_used_pct", round(swap_used_pct, 1), th["swap_percent_warn"]))

    return {
        "mem_total_kb": total, "mem_avail_kb": avail,
        "mem_used_pct": round(used_pct, 1),
        "swap_total_kb": swap_total, "swap_used_pct": round(swap_used_pct, 1) if swap_total else None,
    }


def check_disk(alerts: list[Alert], cfg: dict) -> list[dict]:
    th = cfg["thresholds"]
    exclude = set(cfg.get("exclude_fs_types", []))
    mounts = cfg.get("monitored_mounts") or ["/"]
    results = []
    seen_mounts = set()
    for m in mounts:
        try:
            usage = shutil.disk_usage(m)
        except (FileNotFoundError, OSError) as exc:
            alerts.append(Alert("disk", "WARN", "disk_usage_error", str(exc), m, detail=f"path={m}"))
            continue
        used_pct = 100.0 * usage.used / usage.total if usage.total else 0.0
        entry = {
            "mount": m,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "used_pct": round(used_pct, 1),
        }
        results.append(entry)
        seen_mounts.add(m)

        if used_pct >= th["disk_percent_critical"]:
            alerts.append(Alert("disk", "CRITICAL", "disk_used_pct", round(used_pct, 1), th["disk_percent_critical"],
                                detail=f"mount={m} free={usage.free // (1024*1024)}MB"))
        elif used_pct >= th["disk_percent_warn"]:
            alerts.append(Alert("disk", "WARN", "disk_used_pct", round(used_pct, 1), th["disk_percent_warn"],
                                detail=f"mount={m}"))

    # Also walk /proc/mounts to find non-excluded real filesystems we haven't seen.
    try:
        for line in Path("/proc/mounts").read_text().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            device, mount, fstype = parts[0], parts[1], parts[2]
            if fstype in exclude or mount in seen_mounts:
                continue
            try:
                usage = shutil.disk_usage(mount)
            except (FileNotFoundError, OSError, PermissionError):
                continue
            used_pct = 100.0 * usage.used / usage.total if usage.total else 0.0
            entry = {
                "mount": mount, "fstype": fstype,
                "total_bytes": usage.total, "used_bytes": usage.used,
                "free_bytes": usage.free, "used_pct": round(used_pct, 1),
            }
            results.append(entry)
            seen_mounts.add(mount)
            if used_pct >= th["disk_percent_critical"]:
                alerts.append(Alert("disk", "CRITICAL", "disk_used_pct", round(used_pct, 1),
                                    th["disk_percent_critical"], detail=f"mount={mount} fstype={fstype}"))
            elif used_pct >= th["disk_percent_warn"]:
                alerts.append(Alert("disk", "WARN", "disk_used_pct", round(used_pct, 1),
                                    th["disk_percent_warn"], detail=f"mount={mount} fstype={fstype}"))
    except (FileNotFoundError, PermissionError) as exc:
        alerts.append(Alert("disk", "INFO", "disk_scan_partial", str(exc), "/proc/mounts"))

    return results


# ----------------------------- log scan -----------------------------------

# auth.log patterns
RE_FAILED_PASSWORD = re.compile(
    r"Failed password for (?:invalid user )?(\S+) from (\S+) port \d+"
)
RE_INVALID_USER = re.compile(r"Invalid user (\S+) from (\S+)")
RE_ACCEPTED_PASSWORD = re.compile(r"Accepted (?:password|publickey) for (\S+) from (\S+)")
RE_SESSION_OPENED = re.compile(r"pam_unix\(sshd:session\): session opened for user (\S+)")
RE_SESSION_CLOSED = re.compile(r"pam_unix\(sshd:session\): session closed for user (\S+)")

# syslog patterns
RE_OOM_KILL = re.compile(r"oom-kill|Out of memory|Killed process \d+ \((\S+)\)")
RE_SEGFAULT = re.compile(r"segfault at .* ip .* sp .* error \d+ in (\S+)")
RE_DISK_ERROR = re.compile(r"I/O error|blk_update_request: .* I/O error|EXT4-fs error|Buffer I/O error")
RE_KERNEL_PANIC = re.compile(r"Kernel panic - not syncing|BUG: unable to handle kernel")


def _scan_recent_file(path: Path, patterns: list[re.Pattern], since: datetime) -> list[tuple[re.Pattern, str]]:
    """Tail-scan a log file for matching lines newer than `since`. Returns [(pattern, line), ...]."""
    if not path.exists():
        return []
    try:
        # Read whole file — auth.log on a small system fits in memory easily.
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except (PermissionError, OSError) as exc:
        return [("PERMISSION_ERROR", f"cannot read {path}: {exc}")]  # type: ignore

    hits = []
    for line in content.splitlines():
        # syslog timestamp format: "Jul 27 18:02:03 host ..."
        m = re.match(r"^([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*)$", line)
        if not m:
            continue
        try:
            ts_str = m.group(1)
            year = UTC_NOW().year
            ts = datetime.strptime(f"{year} {ts_str}", "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts < since:
            continue
        for pat in patterns:
            if pat.search(line):
                hits.append((pat, line))
                break
    return hits


def check_auth_log(alerts: list[Alert], cfg: dict) -> dict:
    ls = cfg["log_scan"]
    auth_path = Path(ls["auth_log_path"])
    now = UTC_NOW()
    stats = {"scanned": False, "failed_passwords": 0, "invalid_users": 0,
             "accepted": 0, "sessions_opened": 0, "sessions_closed": 0,
             "top_attacking_ips": [], "top_targeted_users": []}

    if not auth_path.exists():
        return stats

    fp_window = now - timedelta(minutes=ls["ssh_failed_login_window_minutes"])
    iu_window = now - timedelta(minutes=ls["ssh_invalid_user_window_minutes"])

    failed_ips: dict[str, int] = {}
    failed_users: dict[str, int] = {}
    invalid_ips: dict[str, int] = {}
    invalid_users: dict[str, int] = {}

    try:
        with auth_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                # parse ts
                m = re.match(r"^([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*)$", line)
                if not m:
                    continue
                try:
                    year = now.year
                    ts = datetime.strptime(f"{year} {m.group(1)}", "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                mf = RE_FAILED_PASSWORD.search(line)
                if mf and ts >= fp_window:
                    stats["failed_passwords"] += 1
                    failed_ips[mf.group(2)] = failed_ips.get(mf.group(2), 0) + 1
                    user = mf.group(1)
                    failed_users[user] = failed_users.get(user, 0) + 1

                mi = RE_INVALID_USER.search(line)
                if mi and ts >= iu_window:
                    stats["invalid_users"] += 1
                    invalid_ips[mi.group(2)] = invalid_ips.get(mi.group(2), 0) + 1
                    invalid_users[mi.group(1)] = invalid_users.get(mi.group(1), 0) + 1

                if RE_ACCEPTED_PASSWORD.search(line) and ts >= fp_window:
                    stats["accepted"] += 1
                if RE_SESSION_OPENED.search(line) and ts >= fp_window:
                    stats["sessions_opened"] += 1
                if RE_SESSION_CLOSED.search(line) and ts >= fp_window:
                    stats["sessions_closed"] += 1

        stats["scanned"] = True
    except (PermissionError, OSError) as exc:
        alerts.append(Alert("auth", "WARN", "auth_log_unreadable", str(exc), ls["auth_log_path"]))
        return stats

    # Top offenders
    stats["top_attacking_ips"] = sorted(failed_ips.items(), key=lambda kv: -kv[1])[:5]
    stats["top_targeted_users"] = sorted(failed_users.items(), key=lambda kv: -kv[1])[:5]
    stats["top_invalid_ips"] = sorted(invalid_ips.items(), key=lambda kv: -kv[1])[:5]
    stats["top_invalid_users"] = sorted(invalid_users.items(), key=lambda kv: -kv[1])[:5]

    # Alert evaluation
    fp_count = stats["failed_passwords"]
    if fp_count >= ls["ssh_failed_login_threshold_critical"]:
        sev = "CRITICAL"
    elif fp_count >= ls["ssh_failed_login_threshold_warn"]:
        sev = "WARN"
    else:
        sev = None
    if sev:
        sample = [f"src_ip={ip} count={c}" for ip, c in stats["top_attacking_ips"][:3]]
        alerts.append(Alert(
            "auth", sev, "ssh_failed_logins", fp_count,
            {"warn": ls["ssh_failed_login_threshold_warn"],
             "critical": ls["ssh_failed_login_threshold_critical"]},
            detail=f"window={ls['ssh_failed_login_window_minutes']}min",
            evidence=sample,
        ))

    iu_count = stats["invalid_users"]
    if iu_count >= ls["ssh_invalid_user_threshold_critical"]:
        sev = "CRITICAL"
    elif iu_count >= ls["ssh_invalid_user_threshold_warn"]:
        sev = "WARN"
    else:
        sev = None
    if sev:
        sample = [f"src_ip={ip} count={c}" for ip, c in stats["top_invalid_ips"][:3]]
        alerts.append(Alert(
            "auth", sev, "ssh_invalid_users", iu_count,
            {"warn": ls["ssh_invalid_user_threshold_warn"],
             "critical": ls["ssh_invalid_user_threshold_critical"]},
            detail=f"window={ls['ssh_invalid_user_window_minutes']}min",
            evidence=sample,
        ))

    return stats


def check_syslog(alerts: list[Alert], cfg: dict) -> dict:
    ls = cfg["log_scan"]
    now = UTC_NOW()
    syslog_path = Path(ls["syslog_path"])

    stats = {"scanned": False, "oom_kills": 0, "segfaults": 0,
             "disk_errors": 0, "kernel_panics": 0,
             "top_segfault_procs": [], "oom_kill_processes": []}

    if not syslog_path.exists():
        return stats

    oom_window = now - timedelta(minutes=ls["oom_kill_lookback_minutes"])
    seg_window = now - timedelta(minutes=ls["segfault_lookback_minutes"])
    disk_window = now - timedelta(minutes=ls["disk_error_lookback_minutes"])

    oom_procs: dict[str, int] = {}
    seg_procs: dict[str, int] = {}
    oom_lines: list[str] = []
    seg_lines: list[str] = []
    disk_lines: list[str] = []
    panic_lines: list[str] = []

    try:
        with syslog_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*)$", line)
                if not m:
                    continue
                try:
                    year = now.year
                    ts = datetime.strptime(f"{year} {m.group(1)}", "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                if RE_KERNEL_PANIC.search(line):
                    panic_lines.append(line.strip())
                    stats["kernel_panics"] += 1
                elif RE_OOM_KILL.search(line) and ts >= oom_window:
                    oom_lines.append(line.strip())
                    stats["oom_kills"] += 1
                    pm = RE_OOM_KILL.search(line)
                    if pm:
                        proc = pm.group(1)
                        oom_procs[proc] = oom_procs.get(proc, 0) + 1
                elif RE_SEGFAULT.search(line) and ts >= seg_window:
                    seg_lines.append(line.strip())
                    stats["segfaults"] += 1
                    sm = RE_SEGFAULT.search(line)
                    if sm:
                        proc = sm.group(1)
                        seg_procs[proc] = seg_procs.get(proc, 0) + 1
                elif RE_DISK_ERROR.search(line) and ts >= disk_window:
                    disk_lines.append(line.strip())
                    stats["disk_errors"] += 1

        stats["scanned"] = True
    except (PermissionError, OSError) as exc:
        alerts.append(Alert("oom", "WARN", "syslog_unreadable", str(exc), ls["syslog_path"]))
        return stats

    stats["top_segfault_procs"] = sorted(seg_procs.items(), key=lambda kv: -kv[1])[:5]
    stats["oom_kill_processes"] = sorted(oom_procs.items(), key=lambda kv: -kv[1])[:5]

    if stats["oom_kills"] > 0:
        sev = "EMERGENCY" if stats["oom_kills"] >= 3 else "CRITICAL"
        alerts.append(Alert(
            "oom", sev, "oom_kill_count", stats["oom_kills"], 1,
            detail=f"window={ls['oom_kill_lookback_minutes']}min",
            evidence=oom_lines[:3],
        ))

    seg_count = stats["segfaults"]
    seg_sev = None
    if seg_count >= ls["segfault_threshold_critical"]:
        seg_sev = "CRITICAL"
    elif seg_count >= ls["segfault_threshold_warn"]:
        seg_sev = "WARN"
    if seg_sev and seg_count > 0:
        alerts.append(Alert(
            "segfault", seg_sev, "segfault_count", seg_count,
            {"warn": ls["segfault_threshold_warn"],
             "critical": ls["segfault_threshold_critical"]},
            detail=f"window={ls['segfault_lookback_minutes']}min top={stats['top_segfault_procs'][:3]}",
            evidence=seg_lines[:3],
        ))

    disk_count = stats["disk_errors"]
    disk_sev = None
    if disk_count >= ls["disk_error_threshold_critical"]:
        disk_sev = "CRITICAL"
    elif disk_count >= ls["disk_error_threshold_warn"]:
        disk_sev = "WARN"
    if disk_sev and disk_count > 0:
        alerts.append(Alert(
            "disk_error", disk_sev, "disk_io_error_count", disk_count,
            {"warn": ls["disk_error_threshold_warn"],
             "critical": ls["disk_error_threshold_critical"]},
            detail=f"window={ls['disk_error_lookback_minutes']}min",
            evidence=disk_lines[:3],
        ))

    if stats["kernel_panics"] > 0:
        alerts.append(Alert(
            "kernel", "EMERGENCY", "kernel_panic_count", stats["kernel_panics"], 0,
            evidence=panic_lines[:3],
        ))

    return stats


# ----------------------------- output / cooldown --------------------------

def ensure_output_paths(cfg: dict) -> tuple[Path, Path]:
    """Return (log_file_path, report_dir). Falls back to user dir if /var/log/syswatch is not writable."""
    a = cfg["alerts"]
    primary = Path(a["output_dir"])
    fallback = Path(a["fallback_output_dir"])

    def _usable(p: Path) -> bool:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".syswatch.touch"
            test.write_text("ok")
            test.unlink()
            return True
        except (PermissionError, OSError):
            # Best-effort cleanup if mkdir created the dir but write failed.
            try:
                if p.exists() and not any(p.iterdir()):
                    p.rmdir()
            except OSError:
                pass
            return False

    # Ensure fallback always exists (it lives under our $HOME, no permission issues).
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    out_dir = primary if _usable(primary) else fallback
    # Re-check both are usable; if primary failed, ensure fallback is finalized.
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        out_dir = fallback
        out_dir.mkdir(parents=True, exist_ok=True)

    log_path = out_dir / a["log_basename"]
    report_dir = out_dir
    return log_path, report_dir


def cooldown_active(urgent_flag: Path, cooldown_seconds: int) -> bool:
    """Return True if urgent flag exists AND is newer than cooldown_seconds."""
    if not urgent_flag.exists():
        return False
    try:
        age = time.time() - urgent_flag.stat().st_mtime
        return age < cooldown_seconds
    except OSError:
        return False


def write_urgent_flag(urgent_flag: Path, cooldown_seconds: int) -> bool:
    """Write urgent flag. Returns True if we actually wrote (i.e., not in cooldown)."""
    if cooldown_active(urgent_flag, cooldown_seconds):
        return False
    urgent_flag.parent.mkdir(parents=True, exist_ok=True)
    urgent_flag.write_text(ISO(UTC_NOW()) + "\n")
    return True


def rotate_reports(report_dir: Path, keep_days: int) -> int:
    """Remove report files older than keep_days. Returns count removed."""
    if keep_days <= 0:
        return 0
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for p in report_dir.glob("syswatch-report-*.json"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def render_console(report: dict) -> str:
    sev = report["overall_severity"]
    icon = {"INFO": "ℹ️ ", "WARN": "⚠️ ", "CRITICAL": "🔴", "EMERGENCY": "🚨"}.get(sev, "•")
    lines = []
    lines.append(f"{icon} syswatch @ {HOSTNAME} | {report['started_at']} | severity={sev}")
    lines.append("─" * 60)
    r = report["resources"]
    mem = r.get("memory", {})
    swap_pct = mem.get("swap_used_pct")
    swap_str = f"{swap_pct}%" if swap_pct is not None else "n/a"
    lines.append(
        f"cpu={r['cpu_busy_pct']}% iowait={r['iowait_pct']}% "
        f"load1={r['load1']} (per_cpu={r['load1_per_cpu']}) "
        f"mem={mem.get('mem_used_pct')}% "
        f"swap={swap_str}"
    )
    for d in r["disks"]:
        lines.append(f"disk {d['mount']:<12} {d['used_pct']}% used of {d['total_bytes']//(1024**3)}GB")
    a = report["auth"]
    if a.get("scanned"):
        lines.append(
            f"auth: failed_logins={a['failed_passwords']} (win={report['config_meta'].get('auth_window_min')}min) "
            f"invalid_users={a['invalid_users']} accepted={a['accepted']}"
        )
    s = report["syslog"]
    if s.get("scanned"):
        lines.append(
            f"syslog: oom_kills={s['oom_kills']} segfaults={s['segfaults']} "
            f"disk_errors={s['disk_errors']} kernel_panics={s['kernel_panics']}"
        )
    if report["alerts"]:
        lines.append("─" * 60)
        lines.append(f"alerts ({len(report['alerts'])}):")
        for al in report["alerts"]:
            lines.append(
                f"  [{al['severity']:>9}] {al['category']:>10} {al['metric']}={al['observed']} "
                f"(threshold={al['threshold']})"
            )
            if al.get("detail"):
                lines.append(f"               ↳ {al['detail']}")
    lines.append("─" * 60)
    return "\n".join(lines)


def try_syslog(ident: str, msg: str) -> bool:
    """Best-effort write to /dev/log via logger(1). Returns True on success."""
    try:
        subprocess.run(["logger", "-t", ident, msg], check=False, timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return False


# ----------------------------- main orchestrator --------------------------

def run_once(cfg: dict, dry_run: bool, json_only: bool) -> dict:
    started = UTC_NOW()
    ncpu = os.cpu_count() or 1
    alerts: list[Alert] = []

    resources: dict = {}
    resources.update(check_cpu_and_load(alerts, cfg, ncpu))
    resources["memory"] = check_memory(alerts, cfg)
    resources["disks"] = check_disk(alerts, cfg)

    auth_stats = check_auth_log(alerts, cfg)
    syslog_stats = check_syslog(alerts, cfg)

    finished = UTC_NOW()

    # Determine overall severity
    overall = "INFO"
    for al in alerts:
        overall = max_sev(overall, al.severity)

    report = {
        "schema_version": SCHEMA_VERSION,
        "hostname": HOSTNAME,
        "started_at": ISO(started),
        "finished_at": ISO(finished),
        "duration_ms": int((finished - started).total_seconds() * 1000),
        "ncpu": ncpu,
        "config_meta": {
            "config_path": cfg.get("_loaded_from"),
            "auth_window_min": cfg["log_scan"]["ssh_failed_login_window_minutes"],
        },
        "resources": resources,
        "auth": auth_stats,
        "syslog": syslog_stats,
        "alerts": [asdict(a) for a in alerts],
        "overall_severity": overall,
        "alert_count": len(alerts),
    }

    # Cooldown handling
    urgent_path = Path(cfg["alerts"]["urgent_flag_path"])
    fallback_urgent = Path(cfg["alerts"]["fallback_urgent_flag_path"])
    cooldown_sec = cfg["alerts"].get("cooldown_seconds_between_alerts", 600)

    # Choose urgent path based on writability
    chosen_urgent = urgent_path
    try:
        chosen_urgent.parent.mkdir(parents=True, exist_ok=True)
        chosen_urgent.write_text("test"); chosen_urgent.unlink()
    except (PermissionError, OSError):
        chosen_urgent = fallback_urgent

    urgent_written = False
    if overall in ("CRITICAL", "EMERGENCY") and not dry_run:
        urgent_written = write_urgent_flag(chosen_urgent, cooldown_sec)

    # Outputs
    log_path, report_dir = ensure_output_paths(cfg)
    if not dry_run:
        # JSON report (rotated daily)
        report_file = report_dir / f"syswatch-report-{started.strftime('%Y%m%d-%H%M%S')}.json"
        try:
            report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        except OSError as exc:
            print(f"[syswatch] WARN: failed to write report: {exc}", file=sys.stderr)
        # Append to rolling log
        try:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": ISO(finished), "severity": overall,
                                     "alert_count": len(alerts)}) + "\n")
        except OSError as exc:
            print(f"[syswatch] WARN: failed to append log: {exc}", file=sys.stderr)
        # Rotation
        rotate_reports(report_dir, cfg["alerts"].get("keep_reports_days", 14))

    # Console
    if not json_only and cfg["alerts"].get("console", True):
        print(render_console(report))
        if urgent_written:
            print(f"[syswatch] urgent flag written to {chosen_urgent}")

    # Best-effort syslog
    if not dry_run and overall in ("WARN", "CRITICAL", "EMERGENCY"):
        try_syslog(cfg["alerts"].get("syslog_ident", "syswatch"),
                   f"{overall} host={HOSTNAME} alerts={len(alerts)} "
                   f"cpu={resources.get('cpu_busy_pct')}% mem={resources.get('memory', {}).get('mem_used_pct')}%")

    if json_only:
        print(json.dumps(report, ensure_ascii=False))

    return report


# ----------------------------- CLI ----------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Linux system log + resource monitor with alerting.")
    p.add_argument("--config", help="Path to config JSON (default: autodetect).")
    p.add_argument("--once", action="store_true", default=True,
                   help="Run once and exit (default behaviour).")
    p.add_argument("--loop", type=int, metavar="SECONDS",
                   help="Run continuously every N seconds.")
    p.add_argument("--dry-run", action="store_true", help="Don't write outputs, just print.")
    p.add_argument("--json-only", action="store_true", help="Emit only the JSON report to stdout.")
    p.add_argument("--init-config", metavar="PATH",
                   help="Write the default config to PATH and exit.")
    args = p.parse_args()

    if args.init_config:
        # Write the bundled default config
        default_cfg_path = DEFAULT_CONFIG_LOCATIONS[0]
        target = Path(args.init_config)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(Path(default_cfg_path).read_text())
        print(f"[syswatch] wrote default config to {target}")
        return 0

    cfg = load_config(args.config)

    if args.loop:
        interval = max(5, args.loop)
        try:
            while True:
                run_once(cfg, args.dry_run, args.json_only)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[syswatch] interrupted", file=sys.stderr)
            return 130
    else:
        try:
            report = run_once(cfg, args.dry_run, args.json_only)
        except Exception as exc:
            tb = traceback.format_exc()
            print(f"[syswatch] FATAL: {exc}\n{tb}", file=sys.stderr)
            try:
                try_syslog("syswatch", f"FATAL host={HOSTNAME} exc={exc}")
            except Exception:
                pass
            return 2
        return 1 if report["overall_severity"] in ("CRITICAL", "EMERGENCY") else 0


if __name__ == "__main__":
    sys.exit(main())