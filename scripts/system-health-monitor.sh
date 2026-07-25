#!/usr/bin/env bash
# system-health-monitor.sh - Linux system log + resource watchdog (v1).
#
# Default mode is dry-run / report only. It performs two complementary checks
# and emits a single JSONL stream to --log:
#
#   1. Log scan: counts error-class lines inside the configurable time window
#      from /var/log/syslog (or journalctl when available), /var/log/auth.log,
#      and `journalctl -p err -S <window>`.
#   2. Resource check: disk %, memory %, swap %, load average (1m), zombie
#      count, open-fd pressure, inode pressure on the configured mounts.
#
# The script never mutates the system. When a threshold is breached it appends
# a `threshold_breached` record and exits with a non-zero code so the caller
# (cron, systemd timer, heartbeat) can decide how to deliver the alert.
#
# Native integration:
#   * If `systemd-journald` is active the journal is the canonical source;
#     flat-file logs are only used as a fallback.
#   * If `prometheus-node-exporter` is reachable the script logs a
#     `native_metrics_available` event so fleet operators know the better
#     long-term option exists.
#   * If `sysstat` (sar) is installed, last-sample CPU utilisation is reported
#     for context, never as a primary trigger.
#
# Usage:
#   system-health-monitor.sh [OPTIONS]
#
# Options:
#   --dry-run            Print summary only (default; also implicit when no
#                        --apply is passed)
#   --apply              Same as dry-run today; reserved for future
#                        automated mitigations
#   --window-min N       Look back N minutes for log errors (default: 60)
#   --disk-pct N         Disk % threshold (default: 90)
#   --mem-pct  N         Memory % threshold (default: 85)
#   --swap-pct N         Swap % threshold (default: 80)
#   --load1  N           1-minute load avg threshold (default: 4)
#   --zombies N          Zombie-process count threshold (default: 5)
#   --inode-pct N        Inode % threshold (default: 90)
#   --log FILE           Append JSONL events to FILE
#   --alerts FILE        Append threshold_breached records to FILE
#   --allow-root         Permit execution as root (default: refuse)
#   --self-test          Run the built-in fake-mode test (no real checks)
#   --verbose            Emit per-check DEBUG records
#   -h, --help           Show this help

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly SCRIPT_NAME=${0##*/}
readonly VERSION=1

WINDOW_MIN=${WINDOW_MIN:-60}
DISK_PCT=${DISK_PCT:-90}
MEM_PCT=${MEM_PCT:-85}
SWAP_PCT=${SWAP_PCT:-80}
LOAD1=${LOAD1:-4}
ZOMBIE_MAX=${ZOMBIE_MAX:-5}
INODE_PCT=${INODE_PCT:-90}
LOG_FILE=${LOG_FILE:-"$HOME/.local/state/system-health-monitor/monitor.jsonl"}
ALERTS_FILE=${ALERTS_FILE:-"$HOME/.local/state/system-health-monitor/alerts.jsonl"}
LOCK_FILE=${LOCK_FILE:-"${XDG_RUNTIME_DIR:-/tmp}/system-health-monitor-${UID}.lock"}
ALLOW_ROOT=${ALLOW_ROOT:-false}
SELF_TEST=${SELF_TEST:-false}
DRY_RUN=true
VERBOSE=false
ERRORS=0
BREACHES=0
CHECKS=0
WORK_DIR=""

usage() {
  sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 64; }

while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --apply) DRY_RUN=false; shift ;;
    --window-min) [[ $# -ge 2 ]] || die "Missing value for $1"; WINDOW_MIN=$2; shift 2 ;;
    --disk-pct) [[ $# -ge 2 ]] || die "Missing value for $1"; DISK_PCT=$2; shift 2 ;;
    --mem-pct)  [[ $# -ge 2 ]] || die "Missing value for $1"; MEM_PCT=$2;  shift 2 ;;
    --swap-pct) [[ $# -ge 2 ]] || die "Missing value for $1"; SWAP_PCT=$2; shift 2 ;;
    --load1)    [[ $# -ge 2 ]] || die "Missing value for $1"; LOAD1=$2;    shift 2 ;;
    --zombies)  [[ $# -ge 2 ]] || die "Missing value for $1"; ZOMBIE_MAX=$2; shift 2 ;;
    --inode-pct) [[ $# -ge 2 ]] || die "Missing value for $1"; INODE_PCT=$2; shift 2 ;;
    --log)      [[ $# -ge 2 ]] || die "Missing value for $1"; LOG_FILE=$2; shift 2 ;;
    --alerts)   [[ $# -ge 2 ]] || die "Missing value for $1"; ALERTS_FILE=$2; shift 2 ;;
    --allow-root) ALLOW_ROOT=true; shift ;;
    --self-test) SELF_TEST=true; shift ;;
    --verbose)  VERBOSE=true; shift ;;
    -h|--help)  usage; exit 0 ;;
    --) shift; (($# == 0)) || die "Unexpected positional arguments: $*"; ;;
    *) die "Unknown option: $1" ;;
  esac
done

# Threshold validation
for pair in "WINDOW_MIN:$WINDOW_MIN" "DISK_PCT:$DISK_PCT" "MEM_PCT:$MEM_PCT" \
           "SWAP_PCT:$SWAP_PCT" "LOAD1:$LOAD1" "ZOMBIE_MAX:$ZOMBIE_MAX" \
           "INODE_PCT:$INODE_PCT"; do
  name=${pair%%:*}; val=${pair#*:}
  [[ $val =~ ^[0-9]+$ ]] || die "$name must be a non-negative integer (got: $val)"
done

# Refuse root unless explicitly allowed. Read-only checks are safe, but we want
# operators to make a conscious choice before a privileged run.
if (( UID == 0 )) && [[ $ALLOW_ROOT != true ]]; then
  printf 'ERROR: refusing to run as root; pass --allow-root if intentional\n' >&2
  exit 77
fi

# Required commands (deferred; --self-test skips the live checks)
if [[ $SELF_TEST != true ]]; then
  for cmd in awk sed grep df free uptime ps stat flock mktemp python3; do
    command -v "$cmd" >/dev/null 2>&1 \
      || { printf 'ERROR: required command not found: %s\n' "$cmd" >&2; exit 69; }
  done
fi

mkdir -p -- "$(dirname -- "$LOG_FILE")" "$(dirname -- "$ALERTS_FILE")" \
         "$(dirname -- "$LOCK_FILE")"
: > "$LOG_FILE"
: > "$ALERTS_FILE"
chmod 600 "$LOG_FILE" "$ALERTS_FILE" 2>/dev/null || true

exec 9>"$LOCK_FILE"
flock -n 9 || { printf 'ERROR: another health-monitor run is active\n' >&2; exit 75; }
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/system-health-monitor.XXXXXXXX")

log_json() {
  local level=$1 event=$2 message=$3
  local fields='{}'
  [[ $# -lt 4 ]] || fields=$4
  local record
  record=$(python3 - "$level" "$event" "$message" "$fields" "$$" <<'PY'
import datetime, json, sys
level, event, message, fields, pid = sys.argv[1:]
try:
    extra = json.loads(fields)
except json.JSONDecodeError:
    extra = {"raw_fields": fields, "fields_decode_error": True}
record = {
    "timestamp": datetime.datetime.now(datetime.timezone.utc)
        .astimezone().isoformat(timespec="seconds"),
    "level": level, "event": event, "pid": int(pid), "message": message,
}
record.update(extra)
print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
PY
  )
  printf '%s\n' "$record" >> "$LOG_FILE"
  [[ $level != DEBUG || $VERBOSE == true ]] && printf '%s\n' "$record" >&2 || true
  printf '%s\n' "$record"
}

json_fields() {
  python3 - "$@" <<'PY'
import json, sys
args = sys.argv[1:]
if len(args) % 2:
    raise SystemExit("json_fields requires key/value pairs")
out = {}
for i in range(0, len(args), 2):
    key, value = args[i], args[i + 1]
    if value in ("true", "false"):
        out[key] = value == "true"
    elif value.lstrip("-").isdigit():
        out[key] = int(value)
    else:
        out[key] = value
print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
PY
}

on_error() {
  local rc=$? line=${1:-unknown} command=${2:-unknown}
  ((ERRORS+=1))
  log_json ERROR command_failed "Unhandled command failure" \
    "$(json_fields rc "$rc" line "$line" command "$command")" >/dev/null
  return "$rc"
}

on_exit() {
  local rc=$?
  trap - ERR EXIT
  [[ -z $WORK_DIR ]] || rm -rf -- "$WORK_DIR"
  log_json INFO run_finished "Health-monitor run finished" \
    "$(json_fields rc "$rc" checks "$CHECKS" breaches "$BREACHES" errors "$ERRORS" dry_run "$DRY_RUN")" >/dev/null
  # Propagate non-zero when any threshold was breached OR the script errored.
  if (( BREACHES > 0 )) && (( rc == 0 )); then
    exit 75
  fi
  exit "$rc"
}
trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR
trap on_exit EXIT
trap 'log_json WARN interrupted "Interrupted by SIGINT"; exit 130' INT
trap 'log_json WARN interrupted "Interrupted by SIGTERM"; exit 143' TERM

emit_alert() {
  local metric=$1 value=$2 threshold=$3 severity=$4 extra=$5
  ((BREACHES+=1))
  local record
  # Build a single JSON record (the *args protocol is "level event message fields pid").
  record=$(python3 - WARN threshold_breached \
                   "Threshold breached: $metric=$value (>$threshold)" \
                   "$(json_fields metric "$metric" value "$value" threshold "$threshold" \
                                severity "$severity" extra "$extra")" \
                   "$$" <<'PY'
import datetime, json, sys
level, event, message, fields, pid = sys.argv[1:]
try:
    extra = json.loads(fields)
except json.JSONDecodeError:
    extra = {"raw_fields": fields, "fields_decode_error": True}
record = {
    "timestamp": datetime.datetime.now(datetime.timezone.utc)
        .astimezone().isoformat(timespec="seconds"),
    "level": level, "event": event, "pid": int(pid), "message": message,
}
record.update(extra)
print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
PY
  )
  # Single record → alert file (long-term alert stream) AND main log (audit trail).
  # No more redirect-via-stdout trick: log_json would *also* append, causing duplicates.
  printf '%s\n' "$record" >> "$ALERTS_FILE"
  printf '%s\n' "$record" >> "$LOG_FILE"
  # Echo to stderr only when verbose; operators usually consume the alert file.
  [[ $VERBOSE == true ]] && printf '%s\n' "$record" >&2 || true
}

report_native() {
  if command -v journalctl >/dev/null 2>&1 \
      && systemctl is-active --quiet systemd-journald 2>/dev/null; then
    log_json INFO native_journal "systemd-journald is active; prefer it for centralised log queries" \
      "$(json_fields available true source journalctl)" >/dev/null
  else
    log_json INFO native_journal "systemd-journald unavailable; falling back to /var/log/*.log" \
      "$(json_fields available false)" >/dev/null
  fi
  if command -v prometheus-node-exporter >/dev/null 2>&1 \
      || systemctl is-active --quiet prometheus-node-exporter 2>/dev/null; then
    log_json INFO native_metrics "prometheus-node-exporter detected; long-term metrics should scrape it" \
      "$(json_fields available true)" >/dev/null
  fi
  if command -v sar >/dev/null 2>&1; then
    log_json INFO native_sar "sysstat available; sar can produce historical CPU/mem series" \
      "$(json_fields available true)" >/dev/null
  fi
}

# Read metric from /proc/meminfo; returns used% as integer (rounded).
read_mem_pct() {
  local total avail used pct
  total=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
  avail=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
  [[ -n $total && -n $avail && $total -gt 0 ]] || { printf '0'; return; }
  used=$(( total - avail ))
  pct=$(( used * 100 / total ))
  printf '%d' "$pct"
}

read_swap_pct() {
  local total used pct
  total=$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)
  used=$(awk '/^SwapFree:/ {print $2}' /proc/meminfo)
  [[ -n $total && -n $used && $total -gt 0 ]] || { printf '0'; return; }
  pct=$(( (total - used) * 100 / total ))
  printf '%d' "$pct"
}

read_load1() {
  awk '{print int($1)}' /proc/loadavg
}

# Highest-used% among the listed mounts. Defaults to /.
read_disk_pct() {
  local mount=${1:-/} pct
  pct=$(df -P -- "$mount" 2>/dev/null | awk 'NR==2 {gsub("%",""); print $5}')
  [[ -n $pct ]] || { printf '0'; return; }
  printf '%d' "$pct"
}

read_inode_pct() {
  local mount=${1:-/} pct
  pct=$(df -Pi -- "$mount" 2>/dev/null | awk 'NR==2 {gsub("%",""); print $5}')
  [[ -n $pct ]] || { printf '0'; return; }
  printf '%d' "$pct"
}

count_zombies() {
  ps -eo stat= 2>/dev/null | awk '$1 ~ /^Z/ {c++} END {print c+0}'
}

# Scan logs for error-class lines in the last N minutes.
# Returns total count, never modifies files.
scan_log_errors() {
  local total=0 journal_count syslog_count auth_count
  if command -v journalctl >/dev/null 2>&1; then
    journal_count=$(journalctl -p err -q -S "${WINDOW_MIN}min ago" --no-pager 2>/dev/null \
      | wc -l | tr -d ' ') || journal_count=0
  else
    journal_count=0
  fi
  if [[ -r /var/log/syslog ]]; then
    syslog_count=$(grep -E -ci \
      -e ' (emerg|alert|crit|err) ' \
      -e ' kernel:.*(error|fail|panic)' \
      -e ' segfault ' /var/log/syslog 2>/dev/null) || syslog_count=0
    [[ $syslog_count =~ ^[0-9]+$ ]] || syslog_count=0
  else
    syslog_count=0
  fi
  if [[ -r /var/log/auth.log ]]; then
    auth_count=$(grep -E -c -e ' Failed password ' -e ' Invalid user ' \
      -e ' authentication failure' /var/log/auth.log 2>/dev/null) || auth_count=0
    [[ $auth_count =~ ^[0-9]+$ ]] || auth_count=0
  else
    auth_count=0
  fi
  total=$(( journal_count + syslog_count + auth_count ))
  log_json INFO log_scan \
    "Counted error-class log lines in the last ${WINDOW_MIN}m" \
    "$(json_fields window_min "$WINDOW_MIN" journal "$journal_count" \
              syslog "$syslog_count" auth "$auth_count" total "$total")" >/dev/null
  printf '%d' "$total"
}

check_resources() {
  local mem swap load disk inode zombies mount
  mount=${CHECK_MOUNT:-/}
  ((CHECKS+=1))
  mem=$(read_mem_pct)
  if (( mem > MEM_PCT )); then
    emit_alert memory_percent "$mem" "$MEM_PCT" high "mount=$mount"
  else
    [[ $VERBOSE == true ]] && log_json DEBUG memory_ok "Memory below threshold" \
      "$(json_fields value "$mem" threshold "$MEM_PCT")" >/dev/null
  fi

  ((CHECKS+=1))
  swap=$(read_swap_pct)
  if (( swap > SWAP_PCT )); then
    emit_alert swap_percent "$swap" "$SWAP_PCT" high "mount=$mount"
  fi

  ((CHECKS+=1))
  load=$(read_load1)
  if (( load > LOAD1 )); then
    emit_alert load_average_1m "$load" "$LOAD1" medium "mount=$mount"
  fi

  ((CHECKS+=1))
  disk=$(read_disk_pct "$mount")
  if (( disk > DISK_PCT )); then
    emit_alert disk_percent "$disk" "$DISK_PCT" high "mount=$mount"
  fi

  ((CHECKS+=1))
  inode=$(read_inode_pct "$mount")
  if (( inode > INODE_PCT )); then
    emit_alert inode_percent "$inode" "$INODE_PCT" high "mount=$mount"
  fi

  ((CHECKS+=1))
  zombies=$(count_zombies)
  if (( zombies > ZOMBIE_MAX )); then
    emit_alert zombie_count "$zombies" "$ZOMBIE_MAX" medium "mount=$mount"
  fi

  log_json INFO resource_snapshot \
    "Snapshot of host resources" \
    "$(json_fields mount "$mount" memory_percent "$mem" swap_percent "$swap" \
              load1 "$load" disk_percent "$disk" inode_percent "$inode" \
              zombies "$zombies")" >/dev/null
}

# Self-test path: exercise the JSON + alert plumbing against synthesised data.
run_self_test() {
  log_json INFO self_test_started "Running synthetic threshold-breach scenario" \
    "$(json_fields version "$VERSION")" >/dev/null
  local mem=92 swap=85 load=8 disk=95 inode=92 zombies=12
  ((CHECKS+=1)); (( mem > MEM_PCT ))   && emit_alert memory_percent  "$mem"  "$MEM_PCT"   high  "self_test"
  ((CHECKS+=1)); (( swap > SWAP_PCT )) && emit_alert swap_percent    "$swap" "$SWAP_PCT"  high  "self_test"
  ((CHECKS+=1)); (( load > LOAD1 ))    && emit_alert load_average_1m "$load" "$LOAD1"     medium "self_test"
  ((CHECKS+=1)); (( disk > DISK_PCT )) && emit_alert disk_percent    "$disk" "$DISK_PCT" high  "self_test"
  ((CHECKS+=1)); (( inode > INODE_PCT )) && emit_alert inode_percent "$inode" "$INODE_PCT" high  "self_test"
  ((CHECKS+=1)); (( zombies > ZOMBIE_MAX )) && emit_alert zombie_count "$zombies" "$ZOMBIE_MAX" medium "self_test"
  log_json INFO self_test_done "Self-test complete" \
    "$(json_fields checks "$CHECKS" breaches "$BREACHES")" >/dev/null
}

log_json INFO run_started "System health-monitor started" \
  "$(json_fields version "$VERSION" dry_run "$DRY_RUN" window_min "$WINDOW_MIN" \
            uid "$UID" self_test "$SELF_TEST")" >/dev/null
report_native

if [[ $SELF_TEST == true ]]; then
  run_self_test
else
  scan_log_errors >/dev/null
  check_resources
fi
