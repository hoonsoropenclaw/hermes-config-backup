#!/usr/bin/env python3
"""
sysmonitor — Linux 系統日誌 + 資源監控腳本
==========================================

功能：
- 採樣 CPU / RAM / Disk / Load / Zombie process
- 增量掃描 /var/log/{syslog, kern.log, auth.log}（支援 rotate）
- 跑 journalctl -p err..alert 抓 last 1h critical
- 透過 console + log + (optional) Telegram 發 alert
- 15 分鐘 cooldown 抑制 / 日上限 20 條 / 連續 crit 升級
- 每次跑都寫一份 JSON report 到 reports/

使用：
    python3 sysmonitor.py               # 跑一次
    python3 sysmonitor.py --once        # 等同
    python3 sysmonitor.py --loop 60     # 每 60 秒跑一次（測試用）
    python3 sysmonitor.py --dry-run     # 不發 alert，只掃描
    python3 sysmonitor.py --config /path/to/override.py

部署 cron：
    * * * * * /usr/bin/python3 /home/hoonsoropenclaw/.hermes/scripts/sysmonitor/sysmonitor.py --once >> /home/hoonsoropenclaw/.hermes/scripts/sysmonitor/logs/cron.log 2>&1

設計約束：
- 標準庫 + psutil；不引入第三方程式
- 任何 sub-process 失敗不影響主流程
- log offset 持久化在 state/state.json（rotate 自動重置）
- 沒 Telegram token 也能跑（降級）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import traceback
from pathlib import Path

# 確保 import 找得到
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import thresholds as T  # noqa: E402
from state.state import State       # noqa: E402
import metrics                       # noqa: E402
import logscan                       # noqa: E402
import alert                         # noqa: E402


BASE_DIR = Path(__file__).resolve().parent
STATE_DIR = BASE_DIR / "state"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"


# ---------------------------------------------------------------------------
# 報告
# ---------------------------------------------------------------------------
def write_report(findings: list, log_hits: list, sc: dict, stats: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"report_{ts}.json"

    payload = {
        "ts": dt.datetime.now().isoformat(),
        "self_check": _sanitize_for_json(sc),
        "findings": [_finding_to_dict(f) for f in findings],
        "log_hits": [_loghit_to_dict(h) for h in log_hits],
        "alert_stats": stats,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def _finding_to_dict(f) -> dict:
    return {
        "key": f.key,
        "level": f.level,
        "value": f.value,
        "threshold": f.threshold,
        "message": f.message,
        "context": f.context,
    }


def _loghit_to_dict(h) -> dict:
    return {
        "source": h.source,
        "line": h.line,
        "level": h.level,
        "matched_pattern": h.matched_pattern,
    }


def _sanitize_for_json(d: dict) -> dict:
    """把 psutil 物件轉成純 dict，避免 json.dump 失敗。"""
    out = dict(d)
    if "boot_time" in out:
        out["boot_time"] = dt.datetime.fromtimestamp(out["boot_time"]).isoformat()
    return out


# ---------------------------------------------------------------------------
# 連續 crit 升級
# ---------------------------------------------------------------------------
def upgrade_consecutive_crit(findings: list, state: State) -> list:
    """如果某個 crit key 連續 N 個週期，把 warn → crit 升級、或加註 escalation。"""
    crit_keys = {f.key for f in findings if f.level == "crit"}
    all_keys = {f.key for f in findings}

    for key in list(state._data["consecutive_crit"].keys()):
        if key not in crit_keys:
            state.reset_crit(key)

    for f in findings:
        if f.level == "crit":
            n = state.bump_crit(f.key)
            if n >= T.CRIT_CONSECUTIVE_THRESHOLD:
                f.message = f"{f.message} [ESCALATED ×{n}]"
        # warn 也 bump 一下（為了 reset）
        elif f.level == "warn" and f.key in crit_keys:
            state.reset_crit(f.key)

    return findings


# ---------------------------------------------------------------------------
# 主循環
# ---------------------------------------------------------------------------
def run_once(state: State, dry_run: bool = False) -> int:
    """單次檢查。回傳 0=ok, 1=有 crit。"""
    started = time.time()

    # 1. 採集
    sc = metrics.self_check()
    findings = metrics.collect_all()

    # 2. 連續 crit 升級
    findings = upgrade_consecutive_crit(findings, state)

    # 3. 掃日誌（包含 journalctl）
    log_hits, new_offsets = logscan.scan_all(state)

    # 4. 持久化 offset
    for path, offset in new_offsets.items():
        state.set_offset(path, offset)

    # 5. 發 alert
    if dry_run:
        stats = {ch: 0 for ch in T.ALERT_CHANNELS}
    else:
        stats = alert.dispatch(findings, log_hits, state)

    # 6. 寫報告
    report_path = write_report(findings, log_hits, sc, stats)

    # 7. 健全報告
    alert.print_summary(findings, log_hits, stats, sc, state)

    # 8. 存 state（盡力而為，失敗只記錄、不中斷）
    try:
        state.save()
    except Exception as e:
        print(f"[sysmonitor] WARNING: state save failed: {e}", file=sys.stderr)

    # 9. 退出碼（crit from either source → 1）
    elapsed = time.time() - started
    print(f"[sysmonitor] cycle done in {elapsed:.2f}s → report={report_path}", file=sys.stderr)
    has_crit = (
        any(f.level == "crit" for f in findings)
        or any(h.level == "crit" for h in log_hits)
    )
    return 1 if has_crit else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Linux 系統監控")
    parser.add_argument("--once", action="store_true", default=True,
                        help="跑一次（預設）")
    parser.add_argument("--loop", type=int, metavar="SECONDS",
                        help="每 N 秒跑一次（測試用，預設給 60）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只掃描，不發 alert")
    parser.add_argument("--state-file", type=str,
                        help="自訂 state 檔位置")
    args = parser.parse_args()

    # state
    if args.state_file:
        state = State(state_file=Path(args.state_file))
    else:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = State()

    # 啟動 banner
    print(
        f"[sysmonitor] starting  ts={dt.datetime.now().isoformat()}  "
        f"host={os.uname().nodename}  dry_run={args.dry_run}",
        file=sys.stderr,
    )

    try:
        if args.loop:
            interval = max(5, args.loop)
            print(f"[sysmonitor] loop mode: every {interval}s  (Ctrl-C to stop)", file=sys.stderr)
            while True:
                run_once(state, dry_run=args.dry_run)
                time.sleep(interval)
        else:
            return run_once(state, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n[sysmonitor] interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[sysmonitor] FATAL: {e}", file=sys.stderr)
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
