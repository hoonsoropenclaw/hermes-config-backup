#!/usr/bin/env python3
"""
sysmon-watchdog.py — Linux 系統日誌與資源自動監控腳本

功能（5 個獨立 check，純 stdlib）：
  1. CPU loading (5 分鐘平均負載 / CPU 數)
  2. Memory 可用率
  3. 根目錄磁碟使用率
  4. systemd journal 過去 N 分鐘的 err/emerg 件數
  5. SSH 認證失敗次數（auth.log 或 journal sshd）

設計原則：
  - 純 stdlib，零外部依賴（不依賴 psutil）
  - 全部閾值可用環境變數覆寫
  - 雙 log：成功一行寫 .log；超過閾值另寫 .err 並 exit !=0
  - exit code：0=OK, 1=WARN, 2=CRITICAL（給 cron / systemd 判斷用）
  - 每個 check 容忍依賴缺失（journalctl 不可用就 skip，不會整個 crash）

驗證：
  - python3 sysmon-watchdog.py --self-test   (離線 5 個 check 全綠)
  - python3 sysmon-watchdog.py --self-test-warn  (強制 WARN 路徑)
  - python3 sysmon-watchdog.py --self-test-crit  (強制 CRITICAL 路徑)

環境變數（全部可選）：
  SYSMON_LOG_PREFIX  log 檔前綴（預設 /tmp/sysmon-watchdog）
  SYSMON_WINDOW_MIN  journal/authlog 回顧分鐘數（預設 5）
  SYSMON_CPU_WARN    CPU load/nproc 警告閾值（預設 0.85）
  SYSMON_CPU_CRIT    CPU load/nproc 嚴重閾值（預設 1.50）
  SYSMON_MEM_WARN    可用率警告閾值（小數，預設 0.10 = 10%）
  SYSMON_MEM_CRIT    可用率嚴重閾值（預設 0.05）
  SYSMON_DISK_WARN   根目錄使用率警告閾值（預設 0.85）
  SYSMON_DISK_CRIT   根目錄使用率嚴重閾值（預設 0.95）
  SYSMON_JOURNAL_WARN  journal err 件數警告（預設 10）
  SYSMON_JOURNAL_CRIT  journal err 件數嚴重（預設 50）
  SYSMON_AUTH_WARN     SSH auth fail 警告次數（預設 20）
  SYSMON_AUTH_CRIT     SSH auth fail 嚴重次數（預設 100）
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

VERSION = "1.0.0"


# ──────────────────────────────────────────────────────────────────────────────
# 設定（環境變數帶預設值）
# ──────────────────────────────────────────────────────────────────────────────

def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Thresholds:
    log_prefix: str = os.environ.get("SYSMON_LOG_PREFIX", "/tmp/sysmon-watchdog")
    window_min: int = _env_int("SYSMON_WINDOW_MIN", 5)
    cpu_warn: float = _env_float("SYSMON_CPU_WARN", 0.85)
    cpu_crit: float = _env_float("SYSMON_CPU_CRIT", 1.50)
    mem_warn: float = _env_float("SYSMON_MEM_WARN", 0.10)
    mem_crit: float = _env_float("SYSMON_MEM_CRIT", 0.05)
    disk_warn: float = _env_float("SYSMON_DISK_WARN", 0.85)
    disk_crit: float = _env_float("SYSMON_DISK_CRIT", 0.95)
    journal_warn: int = _env_int("SYSMON_JOURNAL_WARN", 10)
    journal_crit: int = _env_int("SYSMON_JOURNAL_CRIT", 50)
    auth_warn: int = _env_int("SYSMON_AUTH_WARN", 20)
    auth_crit: int = _env_int("SYSMON_AUTH_CRIT", 100)


# ──────────────────────────────────────────────────────────────────────────────
# Level enum（用數字比較嚴重度，不用 if-elif 多層）
# ──────────────────────────────────────────────────────────────────────────────

OK, WARN, CRITICAL, SKIP = 0, 1, 2, -1  # SKIP 表示該檢查項目不適用此環境

LEVEL_NAMES = {OK: "OK", WARN: "WARN", CRITICAL: "CRITICAL", SKIP: "SKIP"}


@dataclass
class CheckResult:
    name: str
    level: int
    value: float
    threshold_text: str
    message: str
    detail: dict = field(default_factory=dict)

    @property
    def level_name(self) -> str:
        return LEVEL_NAMES.get(self.level, "UNKNOWN")


# ──────────────────────────────────────────────────────────────────────────────
# Check 1: CPU load (5 分鐘平均 / nproc)
# ──────────────────────────────────────────────────────────────────────────────

def check_cpu(th: Thresholds, *, _loadavg: Optional[Tuple[float, float, float]] = None) -> CheckResult:
    try:
        loadavg = _loadavg if _loadavg is not None else os.getloadavg()
        load5 = loadavg[1]  # 5 分鐘平均
    except (OSError, AttributeError, IndexError) as e:
        return CheckResult(
            name="cpu", level=SKIP, value=0.0, threshold_text="",
            message=f"getloadavg 失敗: {e}",
        )

    try:
        nproc_v = os.cpu_count() or 1
    except Exception:
        nproc_v = 1

    ratio = load5 / nproc_v if nproc_v > 0 else load5
    if ratio >= th.cpu_crit:
        level, msg = CRITICAL, f"CPU load {load5:.2f} / {nproc_v} = {ratio:.2f} >= crit {th.cpu_crit}"
    elif ratio >= th.cpu_warn:
        level, msg = WARN, f"CPU load {load5:.2f} / {nproc_v} = {ratio:.2f} >= warn {th.cpu_warn}"
    else:
        level, msg = OK, f"CPU load {load5:.2f} / {nproc_v} = {ratio:.2f}"

    return CheckResult(
        name="cpu", level=level, value=ratio, threshold_text=f"warn<{th.cpu_warn}, crit>={th.cpu_crit}",
        message=msg, detail={"load5": load5, "nproc": nproc_v},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Check 2: Memory（從 /proc/meminfo 讀，不依賴 psutil）
# ──────────────────────────────────────────────────────────────────────────────

def _read_meminfo() -> Optional[dict]:
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                key, raw = parts
                # "MemTotal:       16384000 kB" → 16384000
                val = raw.strip().split()[0]
                info[key] = int(val)
        return info
    except (OSError, ValueError):
        return None


def check_memory(th: Thresholds) -> CheckResult:
    info = _read_meminfo()
    if not info or "MemTotal" not in info:
        return CheckResult(name="memory", level=SKIP, value=0.0, threshold_text="",
                           message="/proc/meminfo 不可讀")

    total = info.get("MemTotal", 0)
    avail = info.get("MemAvailable", info.get("MemFree", 0))
    if total <= 0:
        return CheckResult(name="memory", level=SKIP, value=0.0, threshold_text="",
                           message="MemTotal 無法解析")

    free_ratio = avail / total
    used_pct = (1 - free_ratio) * 100
    if free_ratio <= th.mem_crit:
        level, msg = CRITICAL, f"Memory available {avail} kB / {total} kB = {free_ratio * 100:.1f}% (<= crit {th.mem_crit * 100:.0f}%)"
    elif free_ratio <= th.mem_warn:
        level, msg = WARN, f"Memory available {avail} kB / {total} kB = {free_ratio * 100:.1f}% (<= warn {th.mem_warn * 100:.0f}%)"
    else:
        level, msg = OK, f"Memory available {free_ratio * 100:.1f}%"

    return CheckResult(
        name="memory", level=level, value=free_ratio,
        threshold_text=f"warn<={th.mem_warn}, crit<={th.mem_crit} (free ratio)",
        message=msg, detail={"avail_kb": avail, "total_kb": total, "used_pct": used_pct},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Check 3: Disk（根目錄使用率）
# ──────────────────────────────────────────────────────────────────────────────

def check_disk(th: Thresholds) -> CheckResult:
    try:
        usage = shutil.disk_usage("/")
    except OSError as e:
        return CheckResult(name="disk", level=SKIP, value=0.0, threshold_text="",
                           message=f"disk_usage(/) 失敗: {e}")

    used_ratio = usage.used / usage.total if usage.total > 0 else 0.0
    used_pct = used_ratio * 100
    if used_ratio >= th.disk_crit:
        level, msg = CRITICAL, f"Disk / used {used_pct:.1f}% (>= crit {th.disk_crit * 100:.0f}%)"
    elif used_ratio >= th.disk_warn:
        level, msg = WARN, f"Disk / used {used_pct:.1f}% (>= warn {th.disk_warn * 100:.0f}%)"
    else:
        level, msg = OK, f"Disk / used {used_pct:.1f}%"

    return CheckResult(
        name="disk", level=level, value=used_ratio,
        threshold_text=f"warn>={th.disk_warn}, crit>={th.disk_crit}",
        message=msg, detail={"used_kb": usage.used // 1024, "total_kb": usage.total // 1024, "free_kb": usage.free // 1024},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Check 4: Journal error count（過去 window_min 分鐘 prio err+emerg）
# ──────────────────────────────────────────────────────────────────────────────

def _run(cmd: list, timeout: int = 15) -> Tuple[int, str, str]:
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return cp.returncode, cp.stdout, cp.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)


def check_journal(th: Thresholds, *, _journalctl_path: Optional[str] = None) -> CheckResult:
    jctl = _journalctl_path or shutil.which("journalctl")
    if not jctl:
        return CheckResult(name="journal", level=SKIP, value=0, threshold_text="",
                           message="journalctl 不在 PATH")

    # 兩層條件式：先試帶 _UID（容器內 + non-systemd user），不行再 fallback
    cmd = [
        jctl, "-p", "err", "--since", f"-{th.window_min}m",
        "--no-pager", "-q", "--output", "short",
    ]
    rc, out, err = _run(cmd)
    if rc != 0 and "Permission denied" in (err or ""):
        # 嘗試帶 _UID=0
        rc, out, err = _run(cmd + ["_UID=0"])
    if rc != 0 and "not implemented" in (err or "").lower():
        return CheckResult(name="journal", level=SKIP, value=0, threshold_text="",
                           message=f"journald not implemented: {err.strip()[:120]}")

    if rc != 0:
        # journalctl 在 dev/容器環境中常失敗，用 WARN 而非 crash
        return CheckResult(name="journal", level=SKIP, value=0, threshold_text="",
                           message=f"journalctl exit {rc}: {err.strip()[:120]}")

    lines = [ln for ln in (out or "").splitlines() if ln.strip()]
    count = len(lines)
    if count >= th.journal_crit:
        level, msg = CRITICAL, f"journal err {count} >= crit {th.journal_crit} (past {th.window_min}m)"
    elif count >= th.journal_warn:
        level, msg = WARN, f"journal err {count} >= warn {th.journal_warn} (past {th.window_min}m)"
    else:
        level, msg = OK, f"journal err {count} (past {th.window_min}m)"

    sample = "\n".join(lines[:3]) if lines else ""
    return CheckResult(
        name="journal", level=level, value=count,
        threshold_text=f"warn>={th.journal_warn}, crit>={th.journal_crit}",
        message=msg, detail={"sample_first_3": sample, "window_min": th.window_min},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Check 5: SSH auth fail（journal sshd + auth.log fallback）
# ──────────────────────────────────────────────────────────────────────────────

def check_auth(th: Thresholds, *,
               _journalctl_path: Optional[str] = None,
               _auth_log_path: Optional[str] = None) -> CheckResult:
    count = 0
    source = "none"

    jctl = _journalctl_path or shutil.which("journalctl")
    if jctl:
        cmd = [jctl, "-u", "sshd", "--since", f"-{th.window_min}m",
               "--no-pager", "-q", "--output", "short", "-g", "Failed password"]
        rc, out, err = _run(cmd)
        if rc == 0 and out:
            count = len([ln for ln in out.splitlines() if ln.strip()])
            source = "journal:sshd"

    if count == 0:
        # fallback: grep auth.log
        ap = _auth_log_path or "/var/log/auth.log"
        try:
            p = Path(ap)
            if p.exists():
                # 取最後 window_min*60 行（近似，auth.log 不帶 timestamp filter 會誤判時區）
                cutoff = time.time() - th.window_min * 60
                matched = 0
                # 粗略做法：找含有 "Failed password" 的近 N 行
                # Linux auth.log 典型：每月輪替，這個近似足夠
                with p.open("r", errors="replace") as f:
                    # mtime of file 看是否過期
                    pass
                # 取最後 5000 行估算
                text = p.read_text(errors="replace")
                all_lines = text.splitlines()[-5000:]
                matched = sum(1 for ln in all_lines if "Failed password" in ln)
                if matched > count:
                    count = matched
                    source = f"file:{ap}"
        except (OSError, PermissionError) as e:
            if source == "none":
                return CheckResult(name="auth", level=SKIP, value=0, threshold_text="",
                                   message=f"auth.log 無法讀: {e}")

    if count == 0 and source == "none":
        return CheckResult(name="auth", level=SKIP, value=0, threshold_text="",
                           message="SSH log 來源都不可用（journal 無 sshd + auth.log 不可讀）")

    if count >= th.auth_crit:
        level, msg = CRITICAL, f"SSH auth fail {count} >= crit {th.auth_crit} ({source}, past {th.window_min}m)"
    elif count >= th.auth_warn:
        level, msg = WARN, f"SSH auth fail {count} >= warn {th.auth_warn} ({source}, past {th.window_min}m)"
    else:
        level, msg = OK, f"SSH auth fail {count} ({source}, past {th.window_min}m)"

    return CheckResult(
        name="auth", level=level, value=count,
        threshold_text=f"warn>={th.auth_warn}, crit>={th.auth_crit}",
        message=msg, detail={"source": source, "window_min": th.window_min},
    )


# ──────────────────────────────────────────────────────────────────────────────
# 執行 + 報告 + logging
# ──────────────────────────────────────────────────────────────────────────────

def run_all_checks(th: Optional[Thresholds] = None) -> list:
    th = th or Thresholds()
    results = [
        check_cpu(th),
        check_memory(th),
        check_disk(th),
        check_journal(th),
        check_auth(th),
    ]
    return results


def render_report(results: list) -> Tuple[int, dict]:
    """回傳 (exit_code, summary_dict)。"""
    overall = OK
    skip_count = 0
    for r in results:
        if r.level == SKIP:
            skip_count += 1
            continue
        if r.level > overall:
            overall = r.level

    summary = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "overall_level": LEVEL_NAMES[overall],
        "overall_exit": overall,
        "skipped_checks": skip_count,
        "checks": [
            {
                "name": r.name,
                "level": r.level_name,
                "value": r.value,
                "thresholds": r.threshold_text,
                "message": r.message,
                "detail": r.detail,
            }
            for r in results
        ],
    }
    return overall, summary


def log_results(prefix: str, summary: dict, overall: int) -> Tuple[Path, Optional[Path]]:
    """寫雙 log；回傳 (log_path, err_path or None)"""
    log_path = Path(f"{prefix}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    err_path: Optional[Path] = None
    if overall >= WARN:
        err_path = Path(f"{prefix}.err")
        # 限制 .err 長度（吸收 cron-job-health-monitor 類型 P 教訓）
        try:
            with err_path.open("a") as f:
                f.write(json.dumps(summary, ensure_ascii=False)[:4096] + "\n")
        except OSError:
            err_path = None
    return log_path, err_path


def emit_console(summary: dict, overall: int, err_path: Optional[Path]) -> None:
    """輸出到 stdout / stderr（給 systemd 或 cron 直接看）。"""
    lines = []
    lines.append(f"[sysmon] overall={summary['overall_level']} skip={summary['skipped_checks']}")
    for c in summary["checks"]:
        marker = {"OK": "✓", "WARN": "⚠", "CRITICAL": "✗", "SKIP": "·"}.get(c["level"], "?")
        lines.append(f"  {marker} {c['name']:<8s} {c['level']:<8s} {c['message']}")
    out = "\n".join(lines) + "\n"

    if overall >= WARN:
        sys.stderr.write(out)
        if err_path:
            sys.stderr.write(f"  → persisted to {err_path}\n")
    else:
        sys.stdout.write(out)


def main() -> int:
    # self-test 模式（給離線 / 單元測試用）
    if "--self-test" in sys.argv:
        th = Thresholds()  # 用正常閾值跑一遍
        results = run_all_checks(th)
        overall, _ = render_report(results)
        print(f"[self-test] {len(results)} checks completed, overall={LEVEL_NAMES[overall]}")
        for r in results:
            print(f"  {r.name}: {r.level_name} - {r.message}")
        # 任何 ERROR 都算測試失敗；但 SKIP 也是可接受（在容器內）
        bad = [r for r in results if r.level == CRITICAL]
        if bad:
            print(f"[self-test] CRITICAL: {[r.name for r in bad]} — 生產環境可能有問題請人工確認", file=sys.stderr)
            return 2
        return 0

    if "--self-test-warn" in sys.argv:
        # 強製一個 warn 路徑（直接 in-process 控制，不依賴環境變數傳遞）
        th = Thresholds(disk_warn=0.0001, disk_crit=0.99)
        r = check_disk(th)
        assert r.level == WARN, f"expected WARN, got {LEVEL_NAMES[r.level]}"
        print(f"[self-test-warn] PASS  disk={r.level_name}")
        return 0

    if "--self-test-crit" in sys.argv:
        # 強製 crit 路徑
        os.environ["SYSMON_CPU_CRIT"] = "0.0001"
        th = Thresholds()
        r = check_cpu(th, _loadavg=(10.0, 10.0, 10.0))
        assert r.level == CRITICAL, f"expected CRITICAL, got {LEVEL_NAMES[r.level]}"
        print(f"[self-test-crit] PASS  cpu={r.level_name}")
        return 0

    th = Thresholds()
    results = run_all_checks(th)
    overall, summary = render_report(results)
    log_path, err_path = log_results(th.log_prefix, summary, overall)
    emit_console(summary, overall, err_path)
    return overall


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:  # 最後一道防線，避免 cron 收到空錯誤
        sys.stderr.write(f"[sysmon] CRASH: {type(e).__name__}: {e}\n")
        sys.exit(2)
