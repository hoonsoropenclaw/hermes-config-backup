#!/usr/bin/env python3
"""
linux_ops_monitor.py — Linux 系統日誌與資源監控腳本

用途：
  掃描 systemd journal 錯誤/嚴重日誌 + 系統資源（CPU/RAM/Disk/Load/IO） +
  systemd unit 健康狀態；超過閾值時輸出告警。常駐或 cron 模式皆可。

用法：
  python3 linux_ops_monitor.py --once              # 跑一次、退出碼反映告警等級
  python3 linux_ops_monitor.py --once --dry-run    # 顯示所有檢查結果（不發告警）
  python3 linux_ops_monitor.py --daemon --interval 300  # 背景常駐、每 5 分鐘跑一次
  python3 linux_ops_monitor.py --since 1h          # 只看最近 1 小時的 journal
  python3 linux_ops_monitor.py --config /path/cfg  # 自訂 config

退出碼：
  0 = OK
  1 = WARN（資源 / 服務有異常但非緊急）
  2 = CRITICAL（磁碟將滿 / OOM / 關鍵服務掛掉 / journal 嚴重錯誤）
  3 = 腳本本身錯誤（無法讀 journal / 讀不到 /proc）

設計：
  - 無第三方依賴（std lib only）
  - state file 記錄「上次告警時間 / 計數」，避免重複打擾
  - 所有命令都走 subprocess + timeout（不會卡死）
  - 任何 sub-check 失敗都不會讓整個腳本崩潰（fail-soft）
  - 對外動作只有「寫本地 alert log」+「stdout」，無 API 呼叫（安全）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ============================================================================
# 預設設定（可被 config 覆蓋）
# ============================================================================

DEFAULT_CONFIG: dict[str, Any] = {
    # 資源閾值
    "thresholds": {
        "cpu_pct": 85.0,            # 平均 CPU 使用率超過 85% 持續 N 次 → warn
        "cpu_pct_critical": 95.0,
        "mem_pct": 85.0,            # 記憶體使用率
        "mem_pct_critical": 95.0,
        "disk_pct": 80.0,           # 磁碟使用率（任何一個掛載點）
        "disk_pct_critical": 90.0,
        "load_per_cpu": 1.5,        # loadavg / nproc
        "load_per_cpu_critical": 3.0,
        "io_wait_pct": 30.0,        # iostat 不可得時跳過
    },
    # journal 相關
    "journal": {
        "priority": "warning",  # warning = err/crit/alert/emerg 全含
        "since": "15m",         # 每次掃描的時間窗口
        "max_lines": 200,       # 最多抓幾行（>= 200 表示爆量）
        "max_err_count": 30,    # 在窗口內 err 級以上超過這個數才算 WARN
        "ignore_patterns": [    # 已知雜訊，忽略
            r"\.scope.*deactivated",
            r"session.*logged out",
            r"Started Daily apt download activities",
            r"Connection reset by peer",
            r"php-fpm.*Connection refused",
        ],
        "critical_patterns": [  # 命中即 CRITICAL
            r"Out of memory",
            r"Killed process",
            r"\bsegfault\b",
            r"kernel panic",
            r"I/O error.*dev",
            r"read-only file system",
            r"failed to start.*service",
            r"systemd\[[0-9]+\]:.*Failed with result",
        ],
    },
    # systemd unit 健康
    "units": {
        # 標記為關鍵的服務（任一非 active 立即 CRITICAL）
        "critical": [
            "ssh.service",
            "systemd-journald.service",
            "cron.service",
        ],
        # 要列入健康檢查的服務（failed/inactive 才 WARN）
        "watched": [
            "rsyslog.service",
            "systemd-timesyncd.service",
        ],
    },
    # 告警去重
    "alerting": {
        "state_file": "~/.hermes/state/linux_ops_monitor_state.json",
        "alert_log": "~/.hermes/logs/linux_ops_monitor_alerts.log",
        "cooldown_seconds": 1800,   # 同一個 alert key 30 分鐘內只告一次
        "max_alerts_per_run": 50,
    },
    # 行為
    "behavior": {
        "io_sample_interval_sec": 2,  # /proc/stat 兩次取樣間隔（短取樣易誤判）
        "command_timeout_sec": 10,
    },
}


# ============================================================================
# 資料結構
# ============================================================================

@dataclass
class Finding:
    """單一檢查結果"""
    source: str         # 例如 "journal" / "memory" / "disk" / "unit:ssh.service"
    severity: str       # "ok" | "warn" | "critical"
    metric: str         # 例如 "memory_pct" / "journal_priority"
    value: Any          # 數值或文字
    message: str        # 人讀的訊息
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    """整體報告"""
    host: str
    timestamp: float
    findings: list[Finding] = field(default_factory=list)

    @property
    def worst_severity(self) -> str:
        order = {"ok": 0, "warn": 1, "critical": 2}
        if not self.findings:
            return "ok"
        return max(
            (f.severity for f in self.findings),
            key=lambda s: order.get(s, 0),
        )

    @property
    def n_warn(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warn")

    @property
    def n_critical(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "timestamp": self.timestamp,
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(self.timestamp)),
            "worst_severity": self.worst_severity,
            "n_findings": len(self.findings),
            "n_warn": self.n_warn,
            "n_critical": self.n_critical,
            "findings": [f.to_dict() for f in self.findings],
        }


# ============================================================================
# 工具
# ============================================================================

def expand(p: str) -> str:
    return os.path.expanduser(os.path.expandvars(p))


def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """執行命令、支援 timeout、回傳 (exit_code, stdout, stderr)"""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", str(e)
    except Exception as e:
        return 1, "", f"exec error: {e}"


def safe_read_file(path: Path, max_bytes: int = 200_000) -> str:
    """讀檔但限制大小 + 容錯"""
    try:
        if not path.exists():
            return ""
        size = path.stat().st_size
        with path.open("r", errors="replace") as f:
            if size > max_bytes:
                # 從尾部讀最新的（tail）
                f.seek(size - max_bytes)
                f.readline()  # 丢掉不完整首行
            return f.read()
    except PermissionError:
        return ""
    except Exception:
        return ""


def parse_pct(s: str) -> float | None:
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    return float(m.group(1)) if m else None


# ============================================================================
# 檢查模組
# ============================================================================

def check_memory(thresholds: dict) -> Finding:
    """記憶體使用率"""
    try:
        with open("/proc/meminfo") as f:
            data = f.read()
        total = parse_kb(re.search(r"MemTotal:\s+(\d+)", data).group(1))
        avail = parse_kb(re.search(r"MemAvailable:\s+(\d+)", data).group(1))
        if not total or not avail:
            return Finding("memory", "ok", "memory_pct", None, "unable to parse /proc/meminfo")
        used_pct = (total - avail) / total * 100.0
        sev = "ok"
        if used_pct >= thresholds["mem_pct_critical"]:
            sev = "critical"
        elif used_pct >= thresholds["mem_pct"]:
            sev = "warn"
        return Finding(
            "memory", sev, "memory_pct", round(used_pct, 1),
            f"memory used {used_pct:.1f}% (total={total}KB avail={avail}KB)",
            {"total_kb": total, "avail_kb": avail},
        )
    except Exception as e:
        return Finding("memory", "ok", "memory_pct", None, f"meminfo error: {e}")


def parse_kb(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s.strip())
    except ValueError:
        return None


def check_disk(thresholds: dict) -> Finding:
    """磁碟使用率（所有掛載點）"""
    try:
        # POSIX -P（避免被 cmd line 截斷）。排除 tmpfs/overlay/devtmpfs/squashfs
        rc, out, _ = run_cmd(["df", "-P", "-x", "tmpfs", "-x", "devtmpfs",
                              "-x", "overlay", "-x", "squashfs"], timeout=5)
        if rc != 0 or not out.strip():
            return Finding("disk", "ok", "disk_pct", None, "df failed")
        lines = out.strip().splitlines()[1:]  # 跳 header
        critical = []
        warns = []
        worst: dict | None = None
        for line in lines:
            parts = line.split()
            if len(parts) < 6:
                continue
            # Filesystem 1024-blocks Used Available Capacity Mounted-on
            source, size, used, avail, pcent, target = parts[:6]
            pct = parse_pct(pcent)
            if pct is None:
                continue
            if pct >= thresholds["disk_pct_critical"]:
                critical.append({"target": target, "pct": pct, "source": source})
            elif pct >= thresholds["disk_pct"]:
                warns.append({"target": target, "pct": pct, "source": source})
            if worst is None or pct > worst["pct"]:
                worst = {"target": target, "pct": pct, "source": source}
        if critical:
            return Finding(
                "disk", "critical", "disk_pct", critical,
                f"critical disk usage: {[(c['target'], c['pct']) for c in critical]}",
                {"critical": critical, "warn": warns, "worst": worst},
            )
        if warns:
            return Finding(
                "disk", "warn", "disk_pct", warns,
                f"disk usage warning: {[(w['target'], w['pct']) for w in warns]}",
                {"warn": warns, "worst": worst},
            )
        return Finding(
            "disk", "ok", "disk_pct", worst["pct"] if worst else 0,
            f"disk usage OK (worst: {worst})" if worst else "no mounted filesystems",
            {"worst": worst},
        )
    except Exception as e:
        return Finding("disk", "ok", "disk_pct", None, f"disk check error: {e}")


def check_load(thresholds: dict, nproc: int) -> Finding:
    """load average / nproc"""
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
        load1 = float(parts[0])
        ratio = load1 / nproc if nproc else load1
        sev = "ok"
        if ratio >= thresholds["load_per_cpu_critical"]:
            sev = "critical"
        elif ratio >= thresholds["load_per_cpu"]:
            sev = "warn"
        return Finding(
            "load", sev, "load1_per_cpu", round(ratio, 2),
            f"load1={load1} nproc={nproc} ratio={ratio:.2f}",
            {"load1": load1, "load5": float(parts[1]), "load15": float(parts[2]), "nproc": nproc},
        )
    except Exception as e:
        return Finding("load", "ok", "load1_per_cpu", None, f"load check error: {e}")


def check_cpu(thresholds: dict, sample_interval: int) -> Finding:
    """用 /proc/stat 兩次取樣計算忙碌率（簡化版，包含 iowait）"""
    try:
        def read_stat() -> dict[str, int]:
            with open("/proc/stat") as f:
                line = f.readline()  # cpu  line
            cols = line.split()
            return {k: int(v) for k, v in zip(cols[1:], cols[1:]) if v.isdigit()}

        a = read_stat()
        if sample_interval > 0:
            time.sleep(sample_interval)
        b = read_stat()

        # 合計（排除 idle / iowait）
        total_a = sum(v for k, v in a.items() if k != "cpu")
        total_b = sum(v for k, v in b.items() if k != "cpu")
        idle_a = a.get("idle", 0) + a.get("iowait", 0)
        idle_b = b.get("idle", 0) + b.get("iowait", 0)
        total_delta = total_b - total_a
        idle_delta = idle_b - idle_a
        iowait_delta = b.get("iowait", 0) - a.get("iowait", 0)
        if total_delta <= 0:
            return Finding("cpu", "ok", "cpu_pct", 0.0, "no delta in /proc/stat")
        busy_pct = (total_delta - idle_delta) / total_delta * 100.0
        iowait_pct = iowait_delta / total_delta * 100.0
        sev = "ok"
        # 短取樣容易誤判 → busy 95% 這種只能算 WARN；只有 iowait 高才升 CRITICAL
        if iowait_pct >= thresholds["io_wait_pct"]:
            sev = "critical"
        elif busy_pct >= thresholds["cpu_pct_critical"]:
            sev = "warn"
        elif busy_pct >= thresholds["cpu_pct"]:
            sev = "warn"
        return Finding(
            "cpu", sev, "cpu_pct", round(busy_pct, 1),
            f"cpu busy {busy_pct:.1f}% iowait {iowait_pct:.1f}% over {sample_interval}s",
            {"sample_interval_sec": sample_interval, "total_delta": total_delta,
             "idle_delta": idle_delta, "iowait_pct": round(iowait_pct, 1)},
        )
    except Exception as e:
        return Finding("cpu", "ok", "cpu_pct", None, f"cpu check error: {e}")


def check_journal(cfg: dict) -> list[Finding]:
    """掃描 systemd journal 錯誤/嚴重日誌"""
    findings: list[Finding] = []
    if not shutil.which("journalctl"):
        return [Finding("journal", "ok", "journal", None, "journalctl not available")]

    priority = cfg.get("priority", "err")
    since = cfg.get("since", "15m")
    max_lines = cfg.get("max_lines", 500)
    ignore_re = [re.compile(p) for p in cfg.get("ignore_patterns", [])]
    crit_re = [re.compile(p, re.IGNORECASE) for p in cfg.get("critical_patterns", [])]

    # 把短的相對時間（"15m"/"1h"）轉成 systemd 一定接受的格式（"15 minutes ago"）
    raw_since = cfg.get("since", "15 minutes ago")
    since_str = "15 minutes ago"
    if isinstance(raw_since, str):
        s = raw_since.strip()
        m = re.fullmatch(r"(\d+)\s*([smhdw])", s)
        if m:
            n, u = int(m.group(1)), m.group(2)
            unit_map = {"s": "seconds", "m": "minutes", "h": "hours",
                        "d": "days", "w": "weeks"}
            since_str = f"{n} {unit_map[u]} ago"
        else:
            since_str = s

    cmd = ["journalctl", f"--priority={priority}", f"--since={since_str}",
           "--no-pager", "-q", f"--lines={max_lines}", "--output=short"]
    rc, out, err = run_cmd(cmd, timeout=15)
    if rc != 0:
        # journalctl 在 container / 沒 journald 時會失敗 → 不算嚴重
        return [Finding("journal", "ok", "journal", None,
                        f"journalctl unavailable ({rc}): {err.strip()[:120]}")]

    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return [Finding("journal", "ok", "journal", 0, "no errors in window")]

    # 過濾已知雜訊
    critical_hits = []
    error_hits = []
    for line in lines:
        if any(p.search(line) for p in ignore_re):
            continue
        if any(p.search(line) for p in crit_re):
            critical_hits.append(line)
        else:
            error_hits.append(line)

    if critical_hits:
        findings.append(Finding(
            "journal", "critical", "critical_pattern", len(critical_hits),
            f"{len(critical_hits)} critical-pattern matches in journal",
            {"samples": critical_hits[:5]},
        ))
    # 只有「錯誤量爆多」才 WARN（少量雜訊忽略）
    max_err = cfg.get("max_err_count", 30)
    if len(error_hits) >= max_err:
        findings.append(Finding(
            "journal", "warn", "err_priority", len(error_hits),
            f"{len(error_hits)} journal entries at priority>={priority} (>= max_err_count={max_err})",
            {"samples": error_hits[:5]},
        ))
    elif error_hits:
        # 不告警但有資料，記成 ok 細節
        findings.append(Finding(
            "journal", "ok", "journal", len(error_hits),
            f"{len(error_hits)} journal entries at priority>={priority} (below threshold {max_err})",
            {"samples": error_hits[:3]},
        ))

    if not findings:
        findings.append(Finding("journal", "ok", "journal", 0, "no notable journal entries"))
    return findings


def check_units(cfg: dict) -> list[Finding]:
    """systemd unit 健康"""
    findings: list[Finding] = []
    if not shutil.which("systemctl"):
        return [Finding("units", "ok", "units", None, "systemctl not available")]

    critical = set(cfg.get("critical", []))
    watched = set(cfg.get("watched", []))
    all_units = list(critical | watched)
    if not all_units:
        return [Finding("units", "ok", "units", 0, "no units configured")]

    for unit in all_units:
        rc, out, _ = run_cmd(
            ["systemctl", "is-active", unit],
            timeout=5,
        )
        state = out.strip() or ("unknown" if rc != 0 else "active")
        # failed / inactive / unknown
        if state != "active":
            sev = "critical" if unit in critical else "warn"
            findings.append(Finding(
                "units", sev, f"unit:{unit}", state,
                f"{unit} is {state}",
                {"unit": unit, "is_critical": unit in critical},
            ))
    if not findings:
        findings.append(Finding("units", "ok", "units", len(all_units),
                                f"all {len(all_units)} watched units active"))
    return findings


# ============================================================================
# 告警去重 / 持久化
# ============================================================================

class AlertState:
    """簡單的告警去重 state file（JSON）"""
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, float] = {}
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                self.data = json.loads(self.path.read_text())
        except Exception:
            self.data = {}

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2))
        except Exception as e:
            print(f"[warn] failed to save state: {e}", file=sys.stderr)

    def should_alert(self, key: str, cooldown: int) -> bool:
        last = self.data.get(key, 0)
        return (time.time() - last) >= cooldown

    def mark_alerted(self, key: str):
        self.data[key] = time.time()


def emit_alert(state: AlertState, finding: Finding, cfg: dict, dry_run: bool) -> bool:
    """把 finding 寫進 alert log（如果沒 cooldown）。回傳是否真的有發送。"""
    if finding.severity == "ok":
        return False
    key = f"{finding.source}:{finding.metric}:{finding.severity}"
    cooldown = cfg["alerting"]["cooldown_seconds"]
    if not state.should_alert(key, cooldown):
        return False

    log_path = Path(expand(cfg["alerting"]["alert_log"]))
    record = {
        "host": socket.gethostname(),
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "severity": finding.severity,
        "source": finding.source,
        "metric": finding.metric,
        "value": finding.value,
        "message": finding.message,
    }
    if not dry_run:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[warn] failed to write alert log: {e}", file=sys.stderr)
        state.mark_alerted(key)
    # 印到 stdout（cron 會收，daemon 模式會送到 log）
    print(f"[{finding.severity.upper():8}] {finding.source}:{finding.metric} = {finding.value} | {finding.message}")
    return True


# ============================================================================
# 主流程
# ============================================================================

def load_config(path: Path | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if not path or not path.exists():
        return cfg
    try:
        with path.open() as f:
            user_cfg = json.load(f)
        # 兩層 deep merge
        for k, v in user_cfg.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    except Exception as e:
        print(f"[warn] failed to load config {path}: {e}", file=sys.stderr)
    return cfg


def collect_findings(cfg: dict) -> Report:
    """跑所有檢查、回傳 Report"""
    host = socket.gethostname()
    report = Report(host=host, timestamp=time.time())

    th = cfg["thresholds"]
    nproc_v = os.cpu_count() or 1
    sample_interval = cfg["behavior"]["io_sample_interval_sec"]

    # 資源檢查（每個都單獨 try，fail-soft）
    checks = [
        ("memory", lambda: check_memory(th)),
        ("disk", lambda: check_disk(th)),
        ("load", lambda: check_load(th, nproc_v)),
        ("cpu", lambda: check_cpu(th, sample_interval)),
    ]
    for name, fn in checks:
        try:
            f = fn()
            if isinstance(f, Finding):
                report.findings.append(f)
            elif isinstance(f, list):
                report.findings.extend(f)
        except Exception as e:
            report.findings.append(Finding(name, "ok", name, None, f"check crashed: {e}"))

    # journal
    try:
        for f in check_journal(cfg["journal"]):
            report.findings.append(f)
    except Exception as e:
        report.findings.append(Finding("journal", "ok", "journal", None, f"journal crashed: {e}"))

    # units
    try:
        for f in check_units(cfg["units"]):
            report.findings.append(f)
    except Exception as e:
        report.findings.append(Finding("units", "ok", "units", None, f"units crashed: {e}"))

    return report


def run_once(cfg: dict, dry_run: bool, emit_alerts: bool = True) -> Report:
    """跑一次完整檢查"""
    report = collect_findings(cfg)
    state = AlertState(Path(expand(cfg["alerting"]["state_file"])))

    if emit_alerts:
        # 限制最多 alerts（防止 flood）
        max_alerts = cfg["alerting"]["max_alerts_per_run"]
        sent = 0
        for f in report.findings:
            if f.severity == "ok":
                continue
            if sent >= max_alerts:
                print(f"[warn] reached max_alerts_per_run={max_alerts}, suppressing remaining")
                break
            if emit_alert(state, f, cfg, dry_run):
                sent += 1
        state.save()

    # 印 summary
    sev = report.worst_severity
    iso = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(report.timestamp))
    print(f"\n=== {report.host} @ {iso} ===")
    print(f"worst_severity={sev} findings={len(report.findings)} "
          f"warn={report.n_warn} critical={report.n_critical}")
    if dry_run:
        for f in report.findings:
            tag = f.severity.upper().ljust(8)
            print(f"  [{tag}] {f.source}:{f.metric} = {f.value} | {f.message}")
    return report


def run_daemon(cfg: dict, interval: int, dry_run: bool):
    """背景常駐模式"""
    print(f"[daemon] start interval={interval}s pid={os.getpid()}", flush=True)

    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True
        print("\n[daemon] stopping...", flush=True)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while not stop:
        try:
            run_once(cfg, dry_run=dry_run, emit_alerts=True)
        except Exception as e:
            print(f"[daemon] check failed: {e}", file=sys.stderr, flush=True)
        # 睡 interval 秒，但允許信號中斷
        for _ in range(interval):
            if stop:
                break
            time.sleep(1)
    print("[daemon] stopped", flush=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Linux 系統日誌與資源監控腳本")
    ap.add_argument("--once", action="store_true", help="跑一次就退出")
    ap.add_argument("--daemon", action="store_true", help="常駐模式")
    ap.add_argument("--interval", type=int, default=300, help="daemon 模式下檢查間隔（秒）")
    ap.add_argument("--dry-run", action="store_true", help="只顯示、不寫 alert log / state")
    ap.add_argument("--config", type=Path, help="自訂 config JSON 路徑")
    ap.add_argument("--since", default=None, help="journal since（如 15m / 2h / 2024-01-01）")
    ap.add_argument("--json", action="store_true", help="輸出 JSON 報告到 stdout（不發告警）")
    ap.add_argument("--test", action="store_true",
                    help="把閾值全部壓成 0、強制觸發所有告警路徑（驗證腳本可發 alert）")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    if args.since:
        cfg["journal"]["since"] = args.since
    if args.test:
        # 驗證用途：閾值歸零，所有檢查都會落入 warn/critical
        cfg["thresholds"]["cpu_pct"] = 0.0
        cfg["thresholds"]["cpu_pct_critical"] = 0.0
        cfg["thresholds"]["mem_pct"] = 0.0
        cfg["thresholds"]["mem_pct_critical"] = 0.0
        cfg["thresholds"]["disk_pct"] = 0.0
        cfg["thresholds"]["disk_pct_critical"] = 0.0
        cfg["thresholds"]["load_per_cpu"] = 0.0
        cfg["thresholds"]["load_per_cpu_critical"] = 0.0
        cfg["thresholds"]["io_wait_pct"] = 0.0
        cfg["journal"]["max_err_count"] = 1
        cfg["journal"]["ignore_patterns"] = []  # 不忽略，觸發 crit pattern
        cfg["alerting"]["cooldown_seconds"] = 0   # 立刻可告
        cfg["alerting"]["max_alerts_per_run"] = 1000
        print("[test] thresholds forced to 0, will trigger all alert paths", file=sys.stderr)

    if args.json:
        report = collect_findings(cfg)
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0

    if args.daemon:
        run_daemon(cfg, args.interval, args.dry_run)
        return 0

    # 預設 --once
    report = run_once(cfg, dry_run=args.dry_run, emit_alerts=True)
    sev = report.worst_severity
    return {"ok": 0, "warn": 1, "critical": 2}.get(sev, 3)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
