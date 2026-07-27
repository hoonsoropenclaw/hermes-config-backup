#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_syswatch.py - Inject synthetic state + logs and verify syswatch fires
the expected alerts. This is a smoke test for threshold logic; not a unit
test framework — stdlib only.
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# We import syswatch as a module.
import importlib.util
spec = importlib.util.spec_from_file_location("syswatch", HERE / "syswatch.py")
syswatch = importlib.util.module_from_spec(spec)
sys.modules["syswatch"] = syswatch  # Required for @dataclass on Python 3.12+
spec.loader.exec_module(syswatch)


def make_fake_log(tmp: Path, kind: str, count: int, minutes_ago: int = 5) -> Path:
    """Write fake auth.log / syslog entries that match the regexes."""
    p = tmp / ("fake_auth.log" if kind == "auth" else "fake_syslog")
    lines = []
    # syslog timestamp format
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    ts = now.strftime("%b %d %H:%M:%S")
    if kind == "auth":
        for i in range(count):
            src = f"203.0.113.{i % 255}"
            lines.append(f"{ts} host sshd[1234]: Failed password for invalid user root from {src} port 50{str(i).zfill(2)} ssh2")
    elif kind == "syslog-oom":
        for i in range(count):
            lines.append(f"{ts} host kernel: Out of memory: Killed process {1234+i} (python3) total-vm:123456kB, anon-rss:12345kB")
    elif kind == "syslog-segfault":
        for i in range(count):
            lines.append(f"{ts} host kernel: python3[1234]: segfault at 0 ip 0x7f.. sp 0x7f.. error 4 in libc-2.31.so")
    elif kind == "syslog-disk":
        for i in range(count):
            lines.append(f"{ts} host kernel: blk_update_request: I/O error, dev sda, sector {i*8}")
    p.write_text("\n".join(lines) + "\n")
    return p


def main() -> int:
    import io
    import contextlib

    failures = []
    stdout_buf = io.StringIO()
    with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(stdout_buf):
        tmp = Path(td)
        # 1. Build a test config with very low thresholds.
        cfg = json.loads((HERE / "config.json").read_text())
        cfg["log_scan"]["auth_log_path"] = str(make_fake_log(tmp, "auth", 25))
        cfg["log_scan"]["syslog_path"] = str(make_fake_log(tmp, "syslog-segfault", 12))
        cfg["log_scan"]["segfault_threshold_warn"] = 3
        cfg["log_scan"]["segfault_threshold_critical"] = 10
        cfg["log_scan"]["ssh_failed_login_threshold_warn"] = 5
        cfg["log_scan"]["ssh_failed_login_threshold_critical"] = 20
        cfg["alerts"]["output_dir"] = str(tmp / "out")
        cfg["alerts"]["fallback_output_dir"] = str(tmp / "out2")
        cfg["alerts"]["urgent_flag_path"] = str(tmp / "urgent")
        cfg["alerts"]["fallback_urgent_flag_path"] = str(tmp / "urgent2")
        cfg["alerts"]["console"] = False
        cfg["alerts"]["cooldown_seconds_between_alerts"] = 0

        # 2. Patch output paths for fake log files.
        report = syswatch.run_once(cfg, dry_run=True, json_only=True)
        # run_once returns dict; --json-only also prints to stdout but stdout
        # is redirected to /dev/null in non-interactive test.

        # 3. Verify alerts fired.
        by_cat = {a["category"]: a for a in report["alerts"]}
        if "auth" not in by_cat:
            failures.append("expected auth alert for 25 failed logins (>= 20 critical)")
        elif by_cat["auth"]["severity"] != "CRITICAL":
            failures.append(f"expected auth=CRITICAL, got {by_cat['auth']['severity']}")

        if "segfault" not in by_cat:
            failures.append("expected segfault alert for 12 segfaults (>= 10 critical)")
        elif by_cat["segfault"]["severity"] != "CRITICAL":
            failures.append(f"expected segfault=CRITICAL, got {by_cat['segfault']['severity']}")

        # 4. Verify auth top offenders were extracted
        auth_stats = report["auth"]
        if auth_stats["failed_passwords"] != 25:
            failures.append(f"expected 25 failed_passwords, got {auth_stats['failed_passwords']}")
        if not auth_stats["top_attacking_ips"]:
            failures.append("expected top_attacking_ips populated")

        # 5. Test OOM kill path (EMERGENCY)
        cfg2 = json.loads(json.dumps(cfg))
        cfg2["log_scan"]["syslog_path"] = str(make_fake_log(tmp, "syslog-oom", 4))
        report2 = syswatch.run_once(cfg2, dry_run=True, json_only=True)
        oom_alert = next((a for a in report2["alerts"] if a["category"] == "oom"), None)
        if oom_alert is None:
            failures.append("expected oom alert")
        elif oom_alert["severity"] != "EMERGENCY":
            failures.append(f"expected oom=EMERGENCY (>=3), got {oom_alert['severity']}")

        # 6. Test disk error path (WARN)
        cfg3 = json.loads(json.dumps(cfg))
        cfg3["log_scan"]["syslog_path"] = str(make_fake_log(tmp, "syslog-disk", 3))
        cfg3["log_scan"]["disk_error_threshold_warn"] = 2
        cfg3["log_scan"]["disk_error_threshold_critical"] = 10
        report3 = syswatch.run_once(cfg3, dry_run=True, json_only=True)
        de_alert = next((a for a in report3["alerts"] if a["category"] == "disk_error"), None)
        if de_alert is None:
            failures.append("expected disk_error alert")
        elif de_alert["severity"] != "WARN":
            failures.append(f"expected disk_error=WARN, got {de_alert['severity']}")

        # 7. Test clean state (no alerts)
        cfg4 = json.loads(json.dumps(cfg))
        cfg4["log_scan"]["auth_log_path"] = "/nonexistent/auth.log"
        cfg4["log_scan"]["syslog_path"] = "/nonexistent/syslog"
        report4 = syswatch.run_once(cfg4, dry_run=True, json_only=True)
        if report4["overall_severity"] != "INFO":
            failures.append(f"expected INFO for clean state, got {report4['overall_severity']}")
        if report4["alert_count"] != 0:
            failures.append(f"expected 0 alerts for clean state, got {report4['alert_count']}")

    if failures:
        print(f"❌ {len(failures)} failure(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("✅ all 7 threshold scenarios passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())