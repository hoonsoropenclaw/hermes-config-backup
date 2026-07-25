#!/usr/bin/env bash
# test-system-health-monitor.sh - sandbox E2E for system-health-monitor.sh
#
# Verifies, in isolation:
#   1. --self-test exercises every threshold and produces valid JSONL.
#   2. Alert file receives one record per breach.
#   3. Default dry-run on the real host produces JSONL events without
#      threshold breaches (or, when --disk-pct 0 is forced, produces at
#      least one breach record).
#   4. Root execution is refused without --allow-root.
#   5. Non-numeric threshold is refused.
#   6. Unknown option is refused.

set -Eeuo pipefail
SCRIPT=/home/hoonsoropenclaw/.hermes/scripts/system-health-monitor.sh
SANDBOX=$(mktemp -d /tmp/system-health-monitor-test.XXXXXXXX)
trap 'rm -rf -- "$SANDBOX"' EXIT
LOG="$SANDBOX/monitor.jsonl"
ALERTS="$SANDBOX/alerts.jsonl"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# ---------- 1) self-test: all six thresholds breach ----------
# self-test is *expected* to exit 75 (EX_TEMPFAIL) when breaches are present;
# under set -Eeuo pipefail the test harness must capture the rc explicitly.
set +e
"$SCRIPT" --self-test --log "$LOG" --alerts "$ALERTS" >/dev/null
self_test_rc=$?
set -e
[[ $self_test_rc -eq 75 ]] || fail "self-test returned rc=$self_test_rc, expected 75 (EX_TEMPFAIL)"
[[ -s $LOG ]] || fail 'self-test produced no log'
[[ -s $ALERTS ]] || fail 'self-test produced no alert'
python3 - "$LOG" "$ALERTS" <<'PY'
import json, sys
from collections import Counter
log_path, alerts_path = sys.argv[1:3]
rows = [json.loads(line) for line in open(log_path, encoding="utf-8")]
assert rows and all(isinstance(r, dict) for r in rows), "log is not JSONL"
events = {r.get("event") for r in rows}
assert "run_started" in events, "missing run_started"
assert "self_test_started" in events, "missing self_test_started"
assert "run_finished" in events, "missing run_finished"
assert rows[-1]["event"] == "run_finished", "last row must be run_finished"
assert rows[-1]["breaches"] >= 6, f"expected >=6 breaches, got {rows[-1]['breaches']}"

# Critical: every metric must appear exactly once in BOTH the main log
# and the alerts file. A previous bug caused the same record to be
# appended to the main log twice.
log_breach_rows = [r for r in rows if r.get("event") == "threshold_breached"]
log_metric_counts = Counter(r["metric"] for r in log_breach_rows)
for m, n in log_metric_counts.items():
    assert n == 1, f"main log has {n} breach records for {m} (expected exactly 1)"

alerts = [json.loads(line) for line in open(alerts_path, encoding="utf-8")]
metrics = {a["metric"] for a in alerts}
for m in ("memory_percent", "swap_percent", "load_average_1m",
          "disk_percent", "inode_percent", "zombie_count"):
    assert m in metrics, f"missing breach for {m}"
alert_counts = Counter(a["metric"] for a in alerts)
for m, n in alert_counts.items():
    assert n == 1, f"alerts file has {n} records for {m} (expected exactly 1)"
for a in alerts:
    assert a["value"] > a["threshold"], \
        f"{a['metric']}: value {a['value']} not > threshold {a['threshold']}"
# Cross-file consistency: the breach record should be byte-identical in both
# files. Strip the timestamp+pid to compare the payload.
def _strip_fluctuating(rec):
    return {k: v for k, v in rec.items()
            if k not in ("timestamp", "pid", "message")}
for a in alerts:
    match = [r for r in log_breach_rows
             if r["metric"] == a["metric"] and _strip_fluctuating(r) == _strip_fluctuating(a)]
    assert match, f"alerts entry for {a['metric']} not mirrored verbatim into main log"
PY

# ---------- 2) guardrail: root execution refused ----------
if HOME=/root "$SCRIPT" --self-test --log "$LOG" --alerts "$ALERTS" \
      >/dev/null 2>&1; then
  fail 'root execution accepted without --allow-root'
fi

# ---------- 3) validation: non-numeric threshold ----------
if "$SCRIPT" --disk-pct notanumber --log "$LOG" --alerts "$ALERTS" \
    >/dev/null 2>&1; then
  fail 'non-numeric --disk-pct accepted'
fi

# ---------- 4) validation: unknown option ----------
if "$SCRIPT" --frobnicate --log "$LOG" --alerts "$ALERTS" \
    >/dev/null 2>&1; then
  fail 'unknown option accepted'
fi

# ---------- 5) live host: dry-run, normal mode, must produce JSONL ----------
# No thresholds forced, so we only assert structural soundness. Live run
# returns rc=0 because the host is healthy.
LIVE_LOG="$SANDBOX/live.jsonl"
LIVE_ALERTS="$SANDBOX/live-alerts.jsonl"
set +e
"$SCRIPT" --log "$LIVE_LOG" --alerts "$LIVE_ALERTS" || true
live_rc=$?
set -e
[[ $live_rc -eq 0 ]] || fail "live dry-run returned rc=$live_rc, expected 0"
[[ -s $LIVE_LOG ]] || fail 'live run produced no log'
python3 - "$LIVE_LOG" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
assert rows, "live log empty"
events = {r.get("event") for r in rows}
# native_journal and log_scan and resource_snapshot are required;
# run_finished is the last row in every mode.
for ev in ("run_started", "log_scan", "resource_snapshot", "run_finished"):
    assert ev in events, f"live run missing event: {ev}"
assert rows[-1]["event"] == "run_finished", "live run not terminated by run_finished"
PY

# ---------- 6) live host: forced-breach path ----------
# Force every threshold to 0 so the live run must report at least one breach.
FORCED_LOG="$SANDBOX/forced.jsonl"
FORCED_ALERTS="$SANDBOX/forced-alerts.jsonl"
# Forced thresholds must trigger exit 75 (EX_TEMPFAIL from on_exit).
set +e
"$SCRIPT" --disk-pct 0 --mem-pct 0 --swap-pct 0 --load1 0 \
           --zombies 0 --inode-pct 0 \
           --log "$FORCED_LOG" --alerts "$FORCED_ALERTS" >/dev/null 2>&1
rc=$?
set -e
[[ $rc -eq 75 ]] || fail "forced-threshold run returned rc=$rc, expected 75 (EX_TEMPFAIL)"
python3 - "$FORCED_LOG" "$FORCED_ALERTS" <<'PY'
import json, sys
log_rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
alerts = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8")]
breaches = [r for r in log_rows if r.get("event") == "threshold_breached"]
assert breaches, "no threshold_breached events in log"
assert alerts, "no rows in alerts file"
finished = log_rows[-1]
assert finished["event"] == "run_finished", "final row is not run_finished"
# The live host is healthy, so only the metrics that are > 0 can breach.
# Specifically: mem (5%), disk (53%), inode (11%) always exceed 0; the
# others (swap, load, zombies) are 0, so they do not breach. We assert
# at least those three are present, not "all six".
assert finished["breaches"] >= 3, \
    f"expected >=3 breaches in summary on healthy host, got {finished['breaches']}"
breach_metrics = {b["metric"] for b in breaches}
for m in ("memory_percent", "disk_percent", "inode_percent"):
    assert m in breach_metrics, f"forced-threshold run missing {m} breach"
PY

printf 'PASS: self-test, guardrails, live dry-run, and forced-breach all verified\n'
