#!/usr/bin/env bash
# run.sh — mlogwatch 入口 wrapper
#
# 用法:
#   ./run.sh                跑一次 (exit 0 = 無 alert, 1 = 有 alert)
#   ./run.sh --self-test    跑單元測試
#   ./run.sh --dry-run      跑但不發通知
#
# 為什麼另外包一層 bash:
#   - 讓 cron / systemd 直接呼 ./run.sh,不用管 python3 路徑
#   - 用 bash defensive patterns (set -Eeuo pipefail) 提前擋錯
#   - 路徑動態計算,移到任何位置都能跑

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"

cd "$SCRIPT_DIR"
exec python3 "$SCRIPT_DIR/mlogwatch.py" "$@"
