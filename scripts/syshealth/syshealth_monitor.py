#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
syshealth_monitor.py — 系統健康檢查與閾值告警 (stdlib-only)

設計原則 (從 trial-and-error L3 教訓歸納):
  - stdlib-only (urllib/dataclass/subprocess/argparse) — 不依賴 psutil/requests
  - SNR 精簡輸出: --brief 給 Telegram/cron, 預設寫詳細 log
  - 5 個獨立檢查器 (CPU/RAM/Disk/Journal/Processes), 各可關閉
  - 退出碼: 0=OK / 1=warning / 2=critical
  - 不動 /etc、不寫 cron jobs (紅區)

使用:
  python3 syshealth_monitor.py                 # 完整檢查 + 詳細 log
  python3 syshealth_monitor.py --brief         # 1-2 行精簡輸出
  python3 syshealth_monitor.py --check cpu     # 只跑 CPU
  python3 syshealth_monitor.py --dry-run       # 不發告警, 只列問題
  python3 syshealth_monitor.py --config <path> # 自訂 YAML

作者: 赫米斯 (miniMax-M3)
建立: 2026-07-28
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ───────────────────────── 常數 ─────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = Path.home() / ".hermes/config/syshealth.yaml"
DEFAULT_LOG_DIR = Path.home() / ".hermes/logs/syshealth"
SCRIPT_VERSION = "1.0.0"


# ───────────────────────── 資料結構 ─────────────────────────
@dataclass
class Threshold:
    """單一閾值: warn 黃燈, crit 紅燈"""
    warn: float
    crit: float

    def check(self, value: float) -> tuple[str, float]:
        """回傳 (level, headroom). level ∈ {ok, warn, crit}"""
        if value >= self.crit:
            return ("crit", value - self.crit)
        if value >= self.warn:
            return ("warn", value - self.warn)
        return ("ok", self.warn - value)


@dataclass
class CheckResult:
    name: str
    level: str  # ok / warn / crit / skip / error
    message: str
    value: Optional[float] = None
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ───────────────────────── 預設閾值 ─────────────────────────
DEFAULT_THRESHOLDS = {
    "cpu_load_per_core": Threshold(warn=0.8, crit=1.5),
    "ram_used_pct":      Threshold(warn=75.0, crit=90.0),
    "swap_used_pct":     Threshold(warn=25.0, crit=50.0),
    "disk_used_pct":     Threshold(warn=75.0, crit=90.0),
    "journal_errors_1h": Threshold(warn=5,   crit=20),
    "zombie_procs":      Threshold(warn=1,   crit=5),
}


# ───────────────────────── 載入 YAML config（沒有 PyYAML 用最簡解析）─────────────────────────
def load_config(path: Path) -> dict:
    """極簡 YAML 解析: 只支援 key: value 兩層, 不引號字串, 不 list。
    完整功能 → 建議裝 PyYAML; 為了 stdlib-only 我們用 regex。
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict = {}
    section = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        # 區段標題 (e.g. "cpu:")
        m = re.match(r"^([a-z_]+):\s*$", line)
        if m:
            section = m.group(1)
            out[section] = {}
            continue
        # key: value 配對
        m = re.match(r"^(\s+)([a-z_]+):\s*([0-9.+-]+|true|false)\s*$", line + " ")
        # 修正: 行末可能沒空白, 直接重試
        if not m:
            m = re.match(r"^(\s+)([a-z_]+):\s*([0-9.+-]+|true|false)\s*", line)
        if m and section:
            key, _, val = m.group(2), m.group(1), m.group(3)
            if val in ("true", "false"):
                out[section][key] = (val == "true")
            else:
                try:
                    out[section][key] = float(val)
                except ValueError:
                    out[section][key] = val
    return out


def merge_thresholds(cfg: dict) -> dict:
    """合併 YAML config 到預設閾值 (cfg 值優先)"""
    result = {k: Threshold(v.warn, v.crit) for k, v in DEFAULT_THRESHOLDS.items()}
    for section, vals in cfg.items():
        if section in result and isinstance(vals, dict):
            for k, v in vals.items():
                if hasattr(result[section], k) and isinstance(v, (int, float)):
                    setattr(result[section], k, float(v))
    return result


# ───────────────────────── 工具 ─────────────────────────
def run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """跑 subprocess, 回傳 (rc, stdout, stderr). 不 raise."""
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return (p.returncode, p.stdout, p.stderr)
    except subprocess.TimeoutExpired:
        return (124, "", f"timeout after {timeout}s: {' '.join(cmd)}")
    except FileNotFoundError as e:
        return (127, "", str(e))


def safe_read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ───────────────────────── 5 個檢查器 ─────────────────────────
def check_cpu(th: Threshold) -> CheckResult:
    rc, out, err = run(["uptime"])
    if rc != 0:
        return CheckResult("cpu", "error", f"uptime failed: {err}")
    # uptime 格式: "... load average: 0.51, 0.97, 1.05"
    m = re.search(r"load average:\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)", out)
    if not m:
        return CheckResult("cpu", "error", "cannot parse uptime load average")
    load1 = float(m.group(1))
    nproc = os.cpu_count() or 1
    load_per_core = load1 / nproc
    level, headroom = th.check(load_per_core)
    return CheckResult(
        name="cpu",
        level=level,
        message=f"load1={load1:.2f} ({load_per_core:.2f}/core, nproc={nproc})",
        value=round(load_per_core, 3),
        detail={"load1": load1, "load5": float(m.group(2)), "load15": float(m.group(3)), "nproc": nproc},
    )


def check_ram(th_ram: Threshold, th_swap: Threshold) -> CheckResult:
    rc, out, err = run(["free", "-m"])
    if rc != 0:
        return CheckResult("ram", "error", f"free failed: {err}")
    # Mem: total used free shared buff/cache available
    mem_line, swap_line = "", ""
    for line in out.splitlines():
        if line.startswith("Mem:"):
            mem_line = line
        elif line.startswith("Swap:"):
            swap_line = line
    if not mem_line:
        return CheckResult("ram", "error", "no Mem line in free output")

    def parse(line: str) -> tuple[int, int]:
        nums = [int(x) for x in re.findall(r"\d+", line)]
        return nums[0], nums[1]  # total, used

    mem_total, mem_used = parse(mem_line)
    ram_pct = (mem_used / mem_total * 100) if mem_total else 0.0
    level_ram, _ = th_ram.check(ram_pct)

    swap_pct, swap_total, swap_used = 0.0, 0, 0
    level_swap = "ok"
    if swap_line:
        swap_total, swap_used = parse(swap_line)
        swap_pct = (swap_used / swap_total * 100) if swap_total else 0.0
        level_swap, _ = th_swap.check(swap_pct)

    # 整體 RAM 跟 swap 取較嚴重者
    order = {"ok": 0, "warn": 1, "crit": 2, "error": 3, "skip": 0}
    overall = max([level_ram, level_swap], key=lambda x: order.get(x, 0))
    return CheckResult(
        name="ram",
        level=overall,
        message=f"RAM {ram_pct:.1f}% ({mem_used}/{mem_total}MB), swap {swap_pct:.1f}% ({swap_used}/{swap_total}MB)",
        value=round(ram_pct, 2),
        detail={
            "ram_pct": ram_pct, "ram_used_mb": mem_used, "ram_total_mb": mem_total,
            "swap_pct": swap_pct, "swap_used_mb": swap_used, "swap_total_mb": swap_total,
        },
    )


def check_disk(th: Threshold, mounts: list[str]) -> CheckResult:
    targets = mounts if mounts else ["/"]
    parts: list[str] = []
    worst = "ok"
    details = {}
    for m in targets:
        rc, out, err = run(["df", "--output=source,size,used,avail,pcent", m])
        if rc != 0:
            details[m] = {"error": err or "df failed"}
            worst = "error"
            continue
        lines = [l for l in out.splitlines() if l.strip() and not l.startswith("Filesystem")]
        if not lines:
            details[m] = {"error": "no output"}
            worst = "error"
            continue
        # 取最後一行 (mount bind 會多行)
        row = lines[-1].split()
        # pcent 欄含 "%"
        try:
            used_pct = float(row[4].rstrip("%"))
            used_mb = int(row[2])
            avail_mb = int(row[3])
            total_mb = int(row[1])
        except (IndexError, ValueError) as e:
            details[m] = {"error": f"parse fail: {e}"}
            worst = "error"
            continue
        lvl, _ = th.check(used_pct)
        details[m] = {
            "used_pct": used_pct, "used_mb": used_mb,
            "avail_mb": avail_mb, "total_mb": total_mb, "level": lvl,
        }
        parts.append(f"{m}={used_pct:.1f}%")
        order = {"ok": 0, "warn": 1, "crit": 2, "error": 3, "skip": 0}
        if order.get(lvl, 0) > order.get(worst, 0):
            worst = lvl
    return CheckResult(
        name="disk",
        level=worst,
        message=" | ".join(parts) if parts else "no mounts checked",
        detail=details,
    )


def check_journal(th: Threshold, since: str = "-1h") -> CheckResult:
    """計數 systemd journal 過去 1 小時的 err/emerg/alert/crit 數"""
    # 先檢查 journalctl 可用 + persistent journal
    rc, _, _ = run(["journalctl", "--no-pager", "-n", "1"], timeout=5)
    if rc != 0:
        return CheckResult("journal", "skip", "journalctl unavailable or no logs", value=0)
    rc, out, err = run(
        ["journalctl", "--no-pager", "-q", "--priority=err", f"-S", since, "--output=short"],
        timeout=15,
    )
    if rc not in (0, 1):  # rc=1 = no entries, 也算 OK
        return CheckResult("journal", "error", f"journalctl failed: {err.strip()[:120]}")
    err_count = sum(1 for line in out.splitlines() if line.strip())
    level, headroom = th.check(err_count)
    return CheckResult(
        name="journal",
        level=level,
        message=f"{err_count} err entries in last 1h (headroom={headroom:+.0f} vs {level})",
        value=float(err_count),
        detail={"since": since, "count": err_count, "threshold_warn": th.warn, "threshold_crit": th.crit},
    )


def check_zombies(th: Threshold) -> CheckResult:
    rc, out, err = run(["ps", "-eo", "stat=,comm=", "--no-headers"])
    if rc != 0:
        return CheckResult("zombies", "error", f"ps failed: {err}")
    zombie_count = sum(1 for line in out.splitlines() if line.startswith("Z"))
    level, headroom = th.check(zombie_count)
    return CheckResult(
        name="zombies",
        level=level,
        message=f"{zombie_count} zombie process(es)",
        value=float(zombie_count),
        detail={"count": zombie_count},
    )


# ───────────────────────── 主流程 ─────────────────────────
CHECK_FUNCS = {
    "cpu":     lambda th, cfg: check_cpu(th["cpu_load_per_core"]),
    "ram":     lambda th, cfg: check_ram(th["ram_used_pct"], th["swap_used_pct"]),
    "disk":    lambda th, cfg: check_disk(th["disk_used_pct"], cfg.get("disk_mounts", [])),
    "journal": lambda th, cfg: check_journal(th["journal_errors_1h"], cfg.get("journal_since", "-1h")),
    "zombies": lambda th, cfg: check_zombies(th["zombie_procs"]),
}


def run_checks(only: Optional[list[str]], thresholds: dict, cfg: dict) -> list[CheckResult]:
    results = []
    for name, fn in CHECK_FUNCS.items():
        if only and name not in only:
            results.append(CheckResult(name=name, level="skip", message="not requested"))
            continue
        try:
            results.append(fn(thresholds, cfg))
        except Exception as e:  # noqa: BLE001 — 任何單一檢查錯誤不影響其他
            results.append(CheckResult(name=name, level="error", message=f"exception: {e!r}"))
    return results


def format_brief(results: list[CheckResult]) -> str:
    """精簡 1 行 (Telegram/cron 友好)"""
    counts = {"ok": 0, "warn": 0, "crit": 0, "error": 0, "skip": 0}
    crit_msgs = []
    for r in results:
        counts[r.level] = counts.get(r.level, 0) + 1
        if r.level in ("crit", "error"):
            crit_msgs.append(f"{r.name}={r.message}")
    if counts["crit"] == 0 and counts["error"] == 0:
        return f"✅ syshealth OK — {counts['ok']} checks pass, {counts['skip']} skipped"
    issues = "; ".join(crit_msgs)[:200]
    return f"❌ syshealth ALERT — {counts['crit']} crit, {counts['error']} err, {counts['warn']} warn | {issues}"


def write_log(results: list[CheckResult], log_dir: Path) -> Optional[Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir / f"syshealth-{ts}.log"
    payload = {
        "timestamp": ts,
        "script_version": SCRIPT_VERSION,
        "results": [r.to_dict() for r in results],
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except OSError as e:
        sys.stderr.write(f"[syshealth] cannot write log: {e}\n")
        return None


def exit_code_for(results: list[CheckResult]) -> int:
    if any(r.level in ("crit", "error") for r in results):
        return 2
    if any(r.level == "warn" for r in results):
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="System health monitor — 5 checks, stdlib-only",
    )
    p.add_argument("--brief", action="store_true", help="one-line output for cron/Telegram")
    p.add_argument("--check", choices=list(CHECK_FUNCS.keys()), help="run only one check")
    p.add_argument("--dry-run", action="store_true", help="do not write log file")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="YAML config path")
    p.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR, help="log output dir")
    p.add_argument("--show-default-config", action="store_true",
                   help="print default thresholds YAML and exit")
    return p.parse_args()


def show_default_config() -> None:
    """給使用者一個起點, 複製到 ~/.hermes/config/syshealth.yaml 改閾值"""
    lines = ["# syshealth_monitor.py thresholds (override by copying to ~/.hermes/config/syshealth.yaml)", ""]
    for k, v in DEFAULT_THRESHOLDS.items():
        lines.append(f"{k.replace('_per_core', '_load_per_core').split('_')[0] if k == 'cpu_load_per_core' else k}:")
        lines.append(f"  warn: {v.warn}")
        lines.append(f"  crit: {v.crit}")
        lines.append("")
    print("\n".join(lines))


def main() -> int:
    args = parse_args()
    if args.show_default_config:
        show_default_config()
        return 0

    cfg = load_config(args.config) if args.config else {}
    thresholds = merge_thresholds(cfg)

    only = [args.check] if args.check else None
    results = run_checks(only, thresholds, cfg)

    # 詳細 log 寫檔 (除非 --dry-run)
    if not args.dry_run:
        log_path = write_log(results, args.log_dir)
    else:
        log_path = None

    # 輸出
    if args.brief:
        print(format_brief(results))
    else:
        print(f"== syshealth_monitor.py v{SCRIPT_VERSION} — {datetime.now().isoformat(timespec='seconds')} ==")
        for r in results:
            print(f"  [{r.level.upper():4}] {r.name:8} {r.message}")
        if log_path:
            print(f"\nlog: {log_path}")

    return exit_code_for(results)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stderr.write("\n[syshealth] interrupted\n")
        sys.exit(130)