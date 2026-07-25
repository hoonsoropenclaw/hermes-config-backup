#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT=/home/hoonsoropenclaw/.hermes/scripts/linux-maintenance.sh
SANDBOX=$(mktemp -d /tmp/linux-maintenance-test.XXXXXXXX)
trap 'rm -rf -- "$SANDBOX"' EXIT
ROOT="$SANDBOX/root"
LOG="$SANDBOX/maintenance.jsonl"
mkdir -p "$ROOT/old-empty" "$ROOT/new-empty"
printf 'old\n' > "$ROOT/old.txt"
printf 'new\n' > "$ROOT/new.txt"
touch -d '10 days ago' "$ROOT/old.txt" "$ROOT/old-empty"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
assert_exists() { [[ -e $1 ]] || fail "expected to exist: $1"; }
assert_missing() { [[ ! -e $1 ]] || fail "expected missing: $1"; }

# Default must be non-destructive and produce valid JSONL.
"$SCRIPT" --tmp-root "$ROOT" --age-days 7 --log "$LOG" --no-zombie-nudge >/dev/null
assert_exists "$ROOT/old.txt"
assert_exists "$ROOT/old-empty"
python3 - "$LOG" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
assert rows and all(isinstance(row, dict) for row in rows)
assert any(row.get("event") == "would_remove_file" for row in rows)
assert any(row.get("event") == "native_tmpfiles" for row in rows)
assert rows[-1].get("event") == "run_finished"
PY

# Apply removes only old file and old empty directory.
: > "$LOG"
"$SCRIPT" --apply --tmp-root "$ROOT" --age-days 7 --log "$LOG" --no-zombie-nudge >/dev/null
assert_missing "$ROOT/old.txt"
assert_missing "$ROOT/old-empty"
assert_exists "$ROOT/new.txt"
assert_exists "$ROOT/new-empty"
python3 - "$LOG" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
last = rows[-1]
assert last["event"] == "run_finished"
assert last["rc"] == 0
assert last["files_removed"] == 1
assert last["dirs_removed"] == 1
assert last["errors"] == 0
PY

# Validation/error paths.
if "$SCRIPT" --tmp-root / --log "$LOG" >/dev/null 2>&1; then fail 'dangerous root accepted'; fi
if "$SCRIPT" --age-days nope --tmp-root "$ROOT" --log "$LOG" >/dev/null 2>&1; then fail 'invalid age accepted'; fi
if "$SCRIPT" --unknown --tmp-root "$ROOT" --log "$LOG" >/dev/null 2>&1; then fail 'unknown option accepted'; fi

printf 'PASS: default dry-run, apply cleanup, JSONL, native detection, and guardrails\n'
