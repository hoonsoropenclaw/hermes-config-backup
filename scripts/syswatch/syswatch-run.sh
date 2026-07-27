#!/usr/bin/env bash
# syswatch-run.sh - cron-friendly wrapper for syswatch.py
#
# Usage in cron:
#   */5 * * * * /home/hoonsoropenclaw/.hermes/scripts/syswatch/syswatch-run.sh
#
# Or via Hermes cron (see /home/hoonsoropenclaw/.hermes/cron/jobs.json).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOG_DIR="${SYSWATCH_LOG_DIR:-/home/hoonsoropenclaw/.local/share/syswatch/log}"
mkdir -p "$LOG_DIR"

# Timeout: 90s — syswatch should finish in ~2s under normal conditions,
# leave headroom for slower NFS / heavy disk scans.
exec timeout 90 "$PYTHON_BIN" "$SCRIPT_DIR/syswatch.py" "$@" >> "$LOG_DIR/wrapper.log" 2>&1