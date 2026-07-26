#!/usr/bin/env python3
"""
hermes-watchdog.py — Linux 系統日誌與資源監控腳本
====================================================

設計原則：
  - 純 Python 3 stdlib（除 PyYAML 讀 config；缺則降級走內建預設）
  - 單檔可獨立跑、可包進 cron、可包進 systemd timer
  - 失敗永不退出非零（監控腳本自己死會造成監控空洞）
  - 告警去重：同 fingerprint 冷卻 N 秒，避免每輪洗版
  - 輸出：JSON append 到 alert log + 可選 notify-send

呼叫方式：
  python3 hermes-watchdog.py                    # 跑一次（cron / 手動 / debug）
  python3 hermes-watchdog.py --daemon           # 進入迴圈（systemd timer 風格）
  python3 hermes-watchdog.py --check-config     # 驗證 config + 列出目前設定，退出
  python3 hermes-watchdog.py --mode both        # log | notify | both（預設 both）
  python3 hermes-watchdog.py --once --verbose   # 一次跑 + 詳細輸出

不修改任何系統服務、不動 systemd、不寫 /etc。
所有狀態（alert log）寫在 ~/.hermes/scripts/hermes-watchdog.alerts.log
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------- 路徑常數（相對於使用者家目錄，絕對不寫 /etc）----------
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "hermes-watchdog.config.yaml"
ALERT_LOG = SCRIPT_DIR / "hermes-watchdog.alerts.log"
STATE_FILE = SCRIPT_DIR / "hermes-watchdog.state.json"  # 冷卻狀態持久化

HOSTNAME = socket.gethostname()
SCRIPT_VERSION = "1.0.0"

# ---------- 預設閾值（config 缺欄位時走這）----------
DEFAULTS = {
    "sample_interval_seconds": 60,
    "alert_cooldown_seconds": 1800,
    "journal_lookback_seconds": 300,
    "thresholds": {
        "cpu_percent_warn": 85, "cpu_percent_crit": 95,
        "mem_percent_warn": 80, "mem_percent_crit": 92,
        "swap_percent_warn": 50, "swap_percent_crit": 80,
        "disk_percent_warn": 85, "disk_percent_crit": 95,
        "load_per_cpu_warn": 1.5, "load_per_cpu_crit": 3.0,
    },
    "log_patterns": [
        {"id": "oom_killer", "priority": "crit", "pattern": "Out of memory|Killed process", "source": "kernel"},
        {"id": "segfault", "priority": "crit", "pattern": "segfault at|general protection fault", "source": "kernel"},
        {"id": "kernel_panic", "priority": "crit", "pattern": "kernel panic|BUG: soft lockup", "source": "kernel"},
        {"id": "io_error", "priority": "crit", "pattern": "I/O error|EXT4-fs error|XFS .* error", "source": "kernel"},
        {"id": "sshd_bruteforce", "priority": "warn", "pattern": "Failed password|Invalid user", "source": "sshd"},
        {"id": "service_failed", "priority": "crit", "pattern": "Failed with result|service entered failed state", "source": "systemd"},
        {"id": "hermes_gateway_down", "priority": "crit", "pattern": "Gateway unavailable|HermesAgent.*exited", "source": "hermes-agent"},
    ],
    "notify": {"enabled": True, "desktop_title_prefix": "[hermes-watchdog]"},
}


# ---------- Config 載入（PyYAML 缺則降級，不會硬掛）----------
def load_config(path: Path) -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy defaults
    if not path.exists():
        return cfg
    try:
        import yaml  # type: ignore
        with path.open() as f:
            user_cfg = yaml.safe_load(f) or {}
    except ImportError:
        sys.stderr.write(f"[warn] PyYAML missing, using built-in defaults (config at {path} ignored)\n")
        return cfg
    except Exception as e:
        sys.stderr.write(f"[warn] failed to parse {path}: {e}\n")
        return cfg

    # 淺合併：top-level 覆寫，但 thresholds/log_patterns 整塊取代（YAML 結構清晰時整塊替換比較不會出錯）
    for k, v in user_cfg.items():
        if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


# ---------- 資料結構 ----------
@dataclass
class Alert:
    ts: str
    severity: str           # "warn" | "crit"
    source: str             # "cpu" | "mem" | "disk" | "swap" | "load" | "log:<pattern_id>"
    metric: str             # "cpu_percent" | "sshd_fail" | ...
    value: float
    threshold: float
    message: str
    fingerprint: str        # 用於冷卻去重
    host: str = HOSTNAME
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- 冷卻狀態 ----------
class CooldownStore:
    """同 fingerprint 在 cooldown 秒內不重發。狀態持久化避免重啟後洗版。"""

    def __init__(self, path: Path, cooldown: int):
        self.path = path
        self.cooldown = cooldown
        self.state: dict[str, float] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.state = json.loads(self.path.read_text())
            except Exception:
                self.state = {}

    def _save(self):
        try:
            # 修剪過期 entry，避免檔案無限膨脹
            now = time.time()
            self.state = {k: v for k, v in self.state.items() if now - v < self.cooldown * 2}
            self.path.write_text(json.dumps(self.state, indent=2))
        except Exception as e:
            sys.stderr.write(f"[warn] failed to persist cooldown state: {e}\n")

    def should_emit(self, fingerprint: str) -> bool:
        last = self.state.get(fingerprint, 0)
        if time.time() - last < self.cooldown:
            return False
        self.state[fingerprint] = time.time()
        self._save()
        return True


# ---------- 資源收集器 ----------
class ResourceSampler:
    """從 /proc 直接讀，避免外部依賴（top/ps 在不同發行版行為不一致）"""

    def __init__(self, thresholds: dict):
        self.thresholds = thresholds
        self._prev_cpu: Optional[tuple[int, ...]] = None  # /proc/stat 第一行

    def sample_cpu(self) -> Optional[float]:
        """讀兩次 /proc/stat 算 busy%。這次只取一次（單輪呼叫），回傳 None。
        真實的 CPU% 需要與前一次取樣 diff — 在 sample_once() 內處理。"""
        try:
            with open("/proc/stat") as f:
                for line in f:
                    if line.startswith("cpu "):
                        parts = list(map(int, line.split()[1:]))
                        return parts  # 回傳原始 tick，交給 _compute_cpu_percent
            return None
        except Exception:
            return None

    def _compute_cpu_percent(self, current: tuple[int, ...]) -> Optional[float]:
        """與前次取樣 diff，計算 busy = 100 - idle%"""
        if self._prev_cpu is None:
            self._prev_cpu = current
            return None
        # 第一次只記基線，第二輪才出數字
        prev = self._prev_cpu
        self._prev_cpu = current
        if len(current) < 4 or len(prev) < 4:
            return None
        deltas = [c - p for c, p in zip(current, prev)]
        total = sum(deltas)
        if total <= 0:
            return None
        idle = deltas[3] + (deltas[4] if len(deltas) > 4 else 0)
        return round(100.0 * (total - idle) / total, 1)

    def sample_mem(self) -> Optional[dict]:
        """從 /proc/meminfo 算 mem% + swap%"""
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.strip().split()[0])  # kB
            total = info.get("MemTotal", 0)
            avail = info.get("MemAvailable", 0)
            if total <= 0:
                return None
            used_pct = round(100.0 * (total - avail) / total, 1)
            swap_total = info.get("SwapTotal", 0)
            swap_free = info.get("SwapFree", 0)
            swap_pct = round(100.0 * (swap_total - swap_free) / swap_total, 1) if swap_total > 0 else 0.0
            return {"mem_percent": used_pct, "swap_percent": swap_pct}
        except Exception:
            return None

    def sample_load(self) -> Optional[dict]:
        try:
            with open("/proc/loadavg") as f:
                parts = f.read().split()
            load1 = float(parts[0])
            try:
                cores = os.cpu_count() or 1
            except Exception:
                cores = 1
            return {"load1": load1, "per_cpu": round(load1 / cores, 2), "cores": cores}
        except Exception:
            return None

    def sample_disks(self) -> list[dict]:
        """所有掛載點（非虛擬、非 tmpfs）"""
        results = []
        try:
            with open("/proc/mounts") as f:
                mounts = f.readlines()
            seen = set()
            for line in mounts:
                parts = line.split()
                if len(parts) < 3:
                    continue
                device, mountpoint, fstype = parts[0], parts[1], parts[2]
                if fstype in ("tmpfs", "devtmpfs", "proc", "sysfs", "devpts", "cgroup", "cgroup2", "overlay", "squashfs"):
                    continue
                if mountpoint in seen or not mountpoint.startswith("/"):
                    continue
                seen.add(mountpoint)
                try:
                    st = os.statvfs(mountpoint)
                    total = st.f_blocks * st.f_frsize
                    free = st.f_bfree * st.f_frsize
                    if total <= 0:
                        continue
                    used_pct = round(100.0 * (total - free) / total, 1)
                    results.append({"mount": mountpoint, "fstype": fstype, "device": device, "used_pct": used_pct})
                except (PermissionError, OSError):
                    continue
        except Exception:
            pass
        return results

    def sample_once(self, cooldown: CooldownStore, verbose: bool = False) -> list[Alert]:
        alerts: list[Alert] = []
        thr = self.thresholds

        # CPU（需要兩次取樣，第一輪只記基線）
        cpu_raw = self.sample_cpu()
        cpu_pct = self._compute_cpu_percent(cpu_raw) if cpu_raw else None
        if cpu_pct is not None:
            sev = None
            if cpu_pct >= thr["cpu_percent_crit"]:
                sev = "crit"
            elif cpu_pct >= thr["cpu_percent_warn"]:
                sev = "warn"
            if sev:
                alerts.append(self._mk_alert(sev, "cpu", "cpu_percent", cpu_pct,
                                              thr[f"cpu_percent_{sev}"],
                                              f"CPU 使用率 {cpu_pct}% 持續偏高"))

        # Memory + Swap
        mem = self.sample_mem()
        if mem:
            mp = mem["mem_percent"]
            sev = "crit" if mp >= thr["mem_percent_crit"] else ("warn" if mp >= thr["mem_percent_warn"] else None)
            if sev:
                alerts.append(self._mk_alert(sev, "mem", "mem_percent", mp,
                                              thr[f"mem_percent_{sev}"],
                                              f"記憶體使用率 {mp}%"))
            sp = mem["swap_percent"]
            sev = "crit" if sp >= thr["swap_percent_crit"] else ("warn" if sp >= thr["swap_percent_warn"] else None)
            if sev:
                alerts.append(self._mk_alert(sev, "swap", "swap_percent", sp,
                                              thr[f"swap_percent_{sev}"],
                                              f"Swap 使用率 {sp}%"))

        # Load average
        load = self.sample_load()
        if load:
            lpc = load["per_cpu"]
            sev = "crit" if lpc >= thr["load_per_cpu_crit"] else ("warn" if lpc >= thr["load_per_cpu_warn"] else None)
            if sev:
                alerts.append(self._mk_alert(sev, "load", "load_per_cpu", lpc,
                                              thr[f"load_per_cpu_{sev}"],
                                              f"Load avg {load['load1']} ({lpc}/core, {load['cores']} cores)"))

        # Disks
        for disk in self.sample_disks():
            u = disk["used_pct"]
            sev = "crit" if u >= thr["disk_percent_crit"] else ("warn" if u >= thr["disk_percent_warn"] else None)
            if sev:
                alerts.append(self._mk_alert(sev, "disk", "disk_percent", u,
                                              thr[f"disk_percent_{sev}"],
                                              f"磁碟 {disk['mount']} 使用率 {u}% ({disk['fstype']})",
                                              extra={"mount": disk["mount"], "fstype": disk["fstype"]}))

        if verbose:
            print(f"[debug] cpu={cpu_pct} mem={mem} load={load} disks={self.sample_disks()}", file=sys.stderr)
        return alerts

    def _mk_alert(self, sev: str, source: str, metric: str, value: float, threshold: float,
                  message: str, extra: Optional[dict] = None) -> Alert:
        # 冷卻 fingerprint：severity + source + metric + (extra 關鍵欄位)
        ext_key = ""
        if extra:
            for k in ("mount", "pattern_id"):
                if k in extra:
                    ext_key += f"|{k}={extra[k]}"
        fp = f"{sev}|{source}|{metric}{ext_key}|{HOSTNAME}"
        return Alert(
            ts=datetime.now(timezone.utc).isoformat(),
            severity=sev, source=source, metric=metric,
            value=value, threshold=threshold,
            message=message, fingerprint=fp,
            extra=extra or {},
        )


# ---------- Journal 收集器 ----------
class JournalSampler:
    """用 journalctl 拉過去 N 秒的 err/crit/alert/emerg 訊息"""

    def __init__(self, patterns: list[dict], lookback: int):
        self.patterns = patterns
        self.lookback = lookback
        # 編譯 regex 一次
        self.compiled = []
        for p in patterns:
            try:
                self.compiled.append({**p, "regex": re.compile(p["pattern"])})
            except re.error as e:
                sys.stderr.write(f"[warn] bad regex for {p.get('id')}: {e}\n")

    def sample(self, verbose: bool = False) -> list[Alert]:
        if not shutil.which("journalctl"):
            if verbose:
                print("[debug] journalctl not found, skipping log scan", file=sys.stderr)
            return []
        # 優先級 err+ = err/crit/alert/emerg
        cmd = [
            "journalctl", "--since", f"{self.lookback} seconds ago",
            "-p", "err", "--no-pager", "-o", "short", "-q"
        ]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            sys.stderr.write("[warn] journalctl timeout\n")
            return []
        if out.returncode != 0:
            return []
        alerts: list[Alert] = []
        # 按行解析（short 格式：時間戳 PRIORITY 主體）
        for line in out.stdout.splitlines():
            for p in self.compiled:
                if p["regex"].search(line):
                    sev = p.get("priority", "warn")
                    fp = f"{sev}|log:{p['id']}|{HOSTNAME}"
                    alerts.append(Alert(
                        ts=datetime.now(timezone.utc).isoformat(),
                        severity=sev,
                        source="log",
                        metric=p["id"],
                        value=0.0,
                        threshold=0.0,
                        message=f"[{p['id']}] {line[:300]}",
                        fingerprint=fp,
                        extra={"pattern_id": p["id"], "raw": line[:500], "log_source": p.get("source", "")},
                    ))
                    break  # 一行只升級一次
        if verbose:
            print(f"[debug] journal lines scanned: {len(out.stdout.splitlines())}, alerts: {len(alerts)}", file=sys.stderr)
        return alerts


# ---------- 輸出器 ----------
class Alerter:
    def __init__(self, mode: str, notify_cfg: dict, alert_log: Path):
        self.mode = mode
        self.notify_cfg = notify_cfg
        self.alert_log = alert_log

    def emit(self, alerts: list[Alert], verbose: bool = False):
        if not alerts:
            return
        if self.mode in ("log", "both"):
            self._write_log(alerts)
        if self.mode in ("notify", "both") and self.notify_cfg.get("enabled"):
            self._send_notify(alerts)
        if verbose or self.mode == "stdout":
            for a in alerts:
                print(json.dumps(a.to_dict(), ensure_ascii=False))

    def _write_log(self, alerts: list[Alert]):
        try:
            with self.alert_log.open("a") as f:
                for a in alerts:
                    f.write(json.dumps(a.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            sys.stderr.write(f"[warn] failed to write alert log: {e}\n")

    def _send_notify(self, alerts: list[Alert]):
        if not shutil.which("notify-send"):
            return  # headless / 沒裝桌面通知 → 靜默略過
        title_prefix = self.notify_cfg.get("desktop_title_prefix", "[hermes-watchdog]")
        for a in alerts:
            icon = "dialog-critical" if a.severity == "crit" else "dialog-warning"
            try:
                subprocess.run(
                    ["notify-send", "-u", "critical" if a.severity == "crit" else "normal",
                     "-i", icon, f"{title_prefix} {a.severity.upper()}", a.message],
                    timeout=2,
                )
            except Exception:
                pass  # 通知永遠不能 fail the script


# ---------- 主迴圈 ----------
def run_once(cfg: dict, mode: str, verbose: bool) -> int:
    cooldown = CooldownStore(STATE_FILE, cfg["alert_cooldown_seconds"])
    resource = ResourceSampler(cfg["thresholds"])
    journal = JournalSampler(cfg["log_patterns"], cfg["journal_lookback_seconds"])
    alerter = Alerter(mode, cfg["notify"], ALERT_LOG)

    all_alerts: list[Alert] = []
    all_alerts.extend(resource.sample_once(cooldown, verbose=verbose))
    all_alerts.extend(journal.sample(verbose=verbose))

    # 過濾冷卻
    fresh = [a for a in all_alerts if cooldown.should_emit(a.fingerprint)]
    suppressed = len(all_alerts) - len(fresh)
    if verbose and suppressed:
        print(f"[debug] {suppressed} alerts suppressed by cooldown", file=sys.stderr)

    alerter.emit(fresh, verbose=verbose)
    return 0


def run_daemon(cfg: dict, mode: str, verbose: bool):
    interval = cfg["sample_interval_seconds"]
    cooldown = CooldownStore(STATE_FILE, cfg["alert_cooldown_seconds"])
    resource = ResourceSampler(cfg["thresholds"])
    journal = JournalSampler(cfg["log_patterns"], cfg["journal_lookback_seconds"])
    alerter = Alerter(mode, cfg["notify"], ALERT_LOG)

    stop = {"flag": False}
    def _handle(*_):
        stop["flag"] = True
        print("\n[daemon] signal received, finishing current cycle then exiting", flush=True)
    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)

    print(f"[daemon] hermes-watchdog v{SCRIPT_VERSION} on {HOSTNAME}, interval={interval}s, mode={mode}", flush=True)
    while not stop["flag"]:
        try:
            run_once(cfg, mode, verbose)
        except Exception as e:
            sys.stderr.write(f"[daemon] cycle error (continuing): {e}\n")
        # 中斷睡眠可被 signal 提前打斷
        for _ in range(interval):
            if stop["flag"]:
                break
            time.sleep(1)
    print("[daemon] exited cleanly", flush=True)


def check_config(cfg: dict):
    print(f"hermes-watchdog v{SCRIPT_VERSION} on {HOSTNAME}")
    print(f"  config file:    {DEFAULT_CONFIG} ({'exists' if DEFAULT_CONFIG.exists() else 'missing (using defaults)'})")
    print(f"  alert log:      {ALERT_LOG}")
    print(f"  state file:     {STATE_FILE}")
    print(f"  interval:       {cfg['sample_interval_seconds']}s")
    print(f"  cooldown:       {cfg['alert_cooldown_seconds']}s")
    print(f"  journal lookback: {cfg['journal_lookback_seconds']}s")
    print(f"  thresholds:")
    for k, v in cfg["thresholds"].items():
        print(f"    {k}: {v}")
    print(f"  log patterns:   {len(cfg['log_patterns'])}")
    for p in cfg["log_patterns"]:
        print(f"    [{p['priority']}] {p['id']:25s} source={p.get('source','?'):12s} pattern={p['pattern']}")
    print(f"  notify enabled: {cfg['notify'].get('enabled')}")
    # 工具可用性
    for tool in ("journalctl", "notify-send"):
        print(f"  {tool:14s} {'available' if shutil.which(tool) else 'MISSING'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="hermes-watchdog: Linux 系統資源與日誌監控腳本")
    parser.add_argument("--mode", choices=["log", "notify", "both", "stdout"], default="both",
                        help="告警輸出通道（預設 both：寫 log + notify-send）")
    parser.add_argument("--once", action="store_true", help="只跑一輪就退出（預設行為）")
    parser.add_argument("--daemon", action="store_true", help="進入迴圈，每 N 秒跑一次")
    parser.add_argument("--check-config", action="store_true", help="列出目前設定與工具可用性後退出")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="config 檔路徑")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細輸出到 stderr")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.check_config:
        check_config(cfg)
        return 0

    if args.daemon:
        run_daemon(cfg, args.mode, args.verbose)
        return 0

    return run_once(cfg, args.mode, args.verbose)


if __name__ == "__main__":
    # 監控腳本不該讓自己死，捕捉所有 main 級錯誤寫 stderr 後回 0
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[fatal] {e}\n")
        sys.exit(0)