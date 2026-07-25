#!/usr/bin/env bash
# Linux temporary-file maintenance and zombie diagnostics (conservative by default).
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly SCRIPT_NAME=${0##*/}
TMP_ROOT=${TMP_ROOT:-/tmp}
MAX_AGE_DAYS=${MAX_AGE_DAYS:-7}
LOG_FILE=${LOG_FILE:-"$HOME/.local/state/linux-maintenance/maintenance.jsonl"}
LOCK_FILE=${LOCK_FILE:-"${XDG_RUNTIME_DIR:-/tmp}/linux-maintenance-${UID}.lock"}
DRY_RUN=true
NUDGE_ZOMBIES=true
VERBOSE=false
FILES_REMOVED=0
DIRS_REMOVED=0
ERRORS=0
ZOMBIES_FOUND=0
PARENTS_NUDGED=0
WORK_DIR=""

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Conservatively removes old, user-owned regular files and empty directories from
one non-root temporary tree. Default mode is dry-run. Zombies cannot be killed;
--apply may send SIGCHLD to a same-user parent so it can call wait(2).

Options:
  --dry-run              Preview only (default)
  --apply                Perform deletion and same-user SIGCHLD nudges
  --tmp-root DIR         Temporary tree (default: /tmp)
  --age-days N           Entries older than N whole days (default: 7)
  --log FILE             Append JSONL logs to FILE
  --no-zombie-nudge      Report zombies without signaling parents
  --verbose              Emit per-item DEBUG records
  -h, --help             Show this help
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 64; }

while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --apply) DRY_RUN=false; shift ;;
    --tmp-root) [[ $# -ge 2 ]] || die "Missing value for $1"; TMP_ROOT=$2; shift 2 ;;
    --age-days) [[ $# -ge 2 ]] || die "Missing value for $1"; MAX_AGE_DAYS=$2; shift 2 ;;
    --log) [[ $# -ge 2 ]] || die "Missing value for $1"; LOG_FILE=$2; shift 2 ;;
    --no-zombie-nudge) NUDGE_ZOMBIES=false; shift ;;
    --verbose) VERBOSE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; (($# == 0)) || die "Unexpected positional arguments: $*" ;;
    *) die "Unknown option: $1" ;;
  esac
done

[[ $MAX_AGE_DAYS =~ ^[0-9]+$ ]] || die "age-days must be a non-negative integer"
for cmd in realpath find ps flock stat mktemp python3; do
  command -v "$cmd" >/dev/null 2>&1 || { printf 'ERROR: required command not found: %s\n' "$cmd" >&2; exit 69; }
done
[[ -d $TMP_ROOT && ! -L $TMP_ROOT ]] || { printf 'ERROR: invalid temporary root: %s\n' "$TMP_ROOT" >&2; exit 66; }
TMP_ROOT=$(realpath -e -- "$TMP_ROOT")
case "$TMP_ROOT" in
  /|/bin|/boot|/dev|/etc|/home|/lib|/lib64|/proc|/root|/run|/sbin|/sys|/usr|/var)
    printf 'ERROR: refusing dangerous root: %s\n' "$TMP_ROOT" >&2; exit 77 ;;
esac
[[ -w $TMP_ROOT || $DRY_RUN == true ]] || { printf 'ERROR: temporary root is not writable: %s\n' "$TMP_ROOT" >&2; exit 73; }

mkdir -p -- "$(dirname -- "$LOG_FILE")"
touch -- "$LOG_FILE"
chmod 600 "$LOG_FILE" 2>/dev/null || true
mkdir -p -- "$(dirname -- "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || { printf 'ERROR: another maintenance run is active\n' >&2; exit 75; }
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/linux-maintenance.XXXXXXXX")

log_json() {
  local level=$1 event=$2 message=$3
  local fields='{}'
  local record
  [[ $# -lt 4 ]] || fields=$4
  record=$(python3 - "$level" "$event" "$message" "$fields" "$$" <<'PY'
import datetime, json, os, sys
level, event, message, fields, pid = sys.argv[1:]
try:
    extra = json.loads(fields)
except json.JSONDecodeError:
    extra = {"raw_fields": fields, "fields_decode_error": True}
record = {
    "timestamp": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"),
    "level": level, "event": event, "pid": int(pid), "message": message,
}
record.update(extra)
print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
PY
  )
  printf '%s\n' "$record" >> "$LOG_FILE"
  [[ $level != DEBUG || $VERBOSE == true ]] && printf '%s\n' "$record" >&2 || true
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
  log_json ERROR command_failed "Unhandled command failure" "$(json_fields rc "$rc" line "$line" command "$command")"
  return "$rc"
}

on_exit() {
  local rc=$?
  trap - ERR EXIT
  [[ -z $WORK_DIR ]] || rm -rf -- "$WORK_DIR"
  log_json INFO run_finished "Maintenance run finished" "$(json_fields rc "$rc" files_removed "$FILES_REMOVED" dirs_removed "$DIRS_REMOVED" zombies_found "$ZOMBIES_FOUND" parents_nudged "$PARENTS_NUDGED" errors "$ERRORS")"
  exit "$rc"
}
trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR
trap on_exit EXIT
trap 'log_json WARN interrupted "Interrupted by SIGINT"; exit 130' INT
trap 'log_json WARN interrupted "Interrupted by SIGTERM"; exit 143' TERM

report_native_tmpfiles() {
  if ! command -v systemd-tmpfiles >/dev/null 2>&1; then
    log_json INFO native_tmpfiles "systemd-tmpfiles is unavailable" '{"available":false}'
    return
  fi
  local rules="$WORK_DIR/tmpfiles.rules"
  systemd-tmpfiles --cat-config 2>/dev/null | grep -E '^[[:space:]]*[dDqQxXvVeE][+!~-]*[[:space:]]+/(tmp|var/tmp)(/|[[:space:]])' > "$rules" || true
  local count
  count=$(wc -l < "$rules")
  log_json INFO native_tmpfiles "Detected native systemd tmpfiles coverage; prefer it for fleet-wide policy" "$(json_fields available true matching_rules "$count")"
}

collect_candidates() {
  local kind=$1 output=$2
  local errfile rc=0
  errfile="$WORK_DIR/find-$kind.err"
  case "$kind" in
    files) find -P "$TMP_ROOT" -xdev -mindepth 1 -type f -uid "$UID" -mtime "+$MAX_AGE_DAYS" -print0 >"$output" 2>"$errfile" || rc=$? ;;
    dirs) find -P "$TMP_ROOT" -xdev -depth -mindepth 1 -type d -uid "$UID" -empty -mtime "+$MAX_AGE_DAYS" -print0 >"$output" 2>"$errfile" || rc=$? ;;
    *) return 64 ;;
  esac
  if [[ -s $errfile ]]; then
    while IFS= read -r line; do log_json WARN candidate_scan_warning "$line" "$(json_fields kind "$kind")"; done < "$errfile"
  fi
  ((rc == 0)) || log_json WARN candidate_scan_partial "Continuing with readable paths" "$(json_fields kind "$kind" rc "$rc")"
}

cleanup_temp() {
  local path file_list="$WORK_DIR/files.list" dir_list="$WORK_DIR/dirs.list"
  log_json INFO temp_cleanup_started "Scanning temporary tree" "$(json_fields root "$TMP_ROOT" age_days "$MAX_AGE_DAYS" dry_run "$DRY_RUN" uid "$UID")"
  collect_candidates files "$file_list"
  while IFS= read -r -d '' path; do
    [[ -f $path && ! -L $path ]] || { log_json WARN candidate_changed "File changed after scan" "$(json_fields path "$path")"; continue; }
    [[ $(stat -c %u -- "$path" 2>/dev/null || printf invalid) == "$UID" ]] || { log_json WARN owner_changed "File owner changed after scan" "$(json_fields path "$path")"; continue; }
    if [[ $DRY_RUN == true ]]; then
      log_json INFO would_remove_file "Dry-run candidate" "$(json_fields path "$path")"
    elif rm -f -- "$path"; then
      ((FILES_REMOVED+=1))
      if [[ $VERBOSE == true ]]; then
        log_json DEBUG removed_file "Removed old file" "$(json_fields path "$path")"
      fi
    else
      ((ERRORS+=1)); log_json ERROR remove_file_failed "Failed to remove old file" "$(json_fields path "$path")"
    fi
  done < "$file_list"

  collect_candidates dirs "$dir_list"
  while IFS= read -r -d '' path; do
    [[ -d $path && ! -L $path ]] || { log_json WARN candidate_changed "Directory changed after scan" "$(json_fields path "$path")"; continue; }
    [[ $(stat -c %u -- "$path" 2>/dev/null || printf invalid) == "$UID" ]] || { log_json WARN owner_changed "Directory owner changed after scan" "$(json_fields path "$path")"; continue; }
    if [[ $DRY_RUN == true ]]; then
      log_json INFO would_remove_empty_dir "Dry-run candidate" "$(json_fields path "$path")"
    elif rmdir -- "$path" 2>/dev/null; then
      ((DIRS_REMOVED+=1))
      if [[ $VERBOSE == true ]]; then
        log_json DEBUG removed_empty_dir "Removed old empty directory" "$(json_fields path "$path")"
      fi
    else
      log_json WARN empty_dir_not_removed "Directory changed or became busy" "$(json_fields path "$path")"
    fi
  done < "$dir_list"
  return 0
}

handle_zombies() {
  local pid ppid owner state command parent_uid current_user parent_binary parent_exe
  current_user=$(id -un)
  while read -r pid ppid owner state command; do
    [[ $state == Z* ]] || continue
    ((ZOMBIES_FOUND+=1))
    parent_binary=$(ps -p "$ppid" -o comm= 2>/dev/null || printf unavailable)
    parent_exe=$(readlink -f "/proc/$ppid/exe" 2>/dev/null || printf unavailable)
    log_json WARN zombie_detected "Zombie requires parent-side wait(2); investigate parent binary" "$(json_fields zombie_pid "$pid" parent_pid "$ppid" owner "$owner" zombie_command "$command" parent_binary "$parent_binary" parent_exe "$parent_exe" action_required root_cause_parent_reaping_bug)"
    [[ $NUDGE_ZOMBIES == true && $DRY_RUN == false && $ppid -gt 1 ]] || continue
    parent_uid=$(stat -c %u -- "/proc/$ppid" 2>/dev/null || printf invalid)
    if [[ $owner == "$current_user" && $parent_uid == "$UID" ]] && kill -0 "$ppid" 2>/dev/null; then
      if kill -s CHLD "$ppid" 2>/dev/null; then
        ((PARENTS_NUDGED+=1)); log_json INFO sigchld_sent "Nudged same-user parent to reap children" "$(json_fields parent_pid "$ppid" zombie_pid "$pid" parent_binary "$parent_binary")"
      else
        ((ERRORS+=1)); log_json ERROR sigchld_failed "Failed to signal zombie parent" "$(json_fields parent_pid "$ppid" zombie_pid "$pid" parent_binary "$parent_binary")"
      fi
    else
      log_json WARN parent_not_signaled "Parent not owned, missing, or PID was reused" "$(json_fields parent_pid "$ppid" zombie_pid "$pid")"
    fi
  done < <(ps -eo pid=,ppid=,user=,stat=,comm=)
}

log_json INFO run_started "Linux maintenance started" "$(json_fields version 3 dry_run "$DRY_RUN" tmp_root "$TMP_ROOT")"
report_native_tmpfiles
cleanup_temp
handle_zombies
