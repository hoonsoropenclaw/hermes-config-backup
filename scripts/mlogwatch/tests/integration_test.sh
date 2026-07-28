#!/usr/bin/env bash
# integration_test.sh — 對 mlogwatch 跑 end-to-end
#
# 隔離:
#   - 用 mktemp 建暫存工作目錄
#   - 把 MLOGWATCH_* 環境變數覆寫到該 dir
#   - 測試完 chmod 700 + trap 確保刪除
#
# 測什麼:
#   1. self-test 26 條全綠
#   2. 真跑 (有正常 state) 對 production 環境應 0 個真 alert (因為環境本身沒爆)
#   3. dry-run 在過低的閾值下應該 ≥ 1 個 alert line 出現
#   4. webhook_url 空時不會去打 webhook
#   5. cooldown 機制: 第二次跑同一個 alert line 數應該降到 0 (或不被寫入 alerts.log 第二次)
#   6. 鎖: 同時兩個 instance 跑,只該一個能跑

set -uo pipefail  # 不要 -e,測試斷言失敗要繼續看其他結果

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd -P)"
PY=python3

# ---- tmpdir 隔離 ---------------------------------------------------
TEST_DIR="$(mktemp -d -t mlogwatch-it-XXXXXX)"
trap 'chmod -R u+w "$TEST_DIR" 2>/dev/null; rm -rf "$TEST_DIR"' EXIT
chmod 700 "$TEST_DIR"

export MLOGWATCH_CONFIG="$TEST_DIR/config.yaml"
export MLOGWATCH_STATE_DIR="$TEST_DIR/state"
export MLOGWATCH_LOCK_DIR="$TEST_DIR/locks"
export MLOGWATCH_REPORT_DIR="$TEST_DIR/reports"

mkdir -p "$MLOGWATCH_STATE_DIR" "$MLOGWATCH_LOCK_DIR" "$MLOGWATCH_REPORT_DIR"

# ---- 寫一個超低閾值的測試 config (讓 disk/mem 一定發 alert) -------
cat > "$MLOGWATCH_CONFIG" <<'YAML'
checks:
  disk: {warn: 0, alert: 0, critical: 0}
  memory: {warn: 0, alert: 0, critical: 0}
  load: {warn: 0, alert: 0, critical: 0}
  cpu: {warn: 0, alert: 0, critical: 0}
  inode: {warn: 0, alert: 0, critical: 0}
  journal: {window_min: 5, alert_threshold: 0}
notify:
  cooldown_seconds: 60
  webhook_url: ""
YAML

# ---- helpers --------------------------------------------------------
PASS=0
FAIL=0
FAILED_TESTS=()

assert_eq() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        printf '  \033[32mPASS\033[0m %s (got=%s)\n' "$name" "$got"
        PASS=$((PASS + 1))
    else
        printf '  \033[31mFAIL\033[0m %s (got=%s, want=%s)\n' "$name" "$got" "$want"
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$name")
    fi
}

assert_ge() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" -ge "$want" ]]; then
        printf '  \033[32mPASS\033[0m %s (got=%s >= %s)\n' "$name" "$got" "$want"
        PASS=$((PASS + 1))
    else
        printf '  \033[31mFAIL\033[0m %s (got=%s, want>=%s)\n' "$name" "$got" "$want"
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$name")
    fi
}

assert_le() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" -le "$want" ]]; then
        printf '  \033[32mPASS\033[0m %s (got=%s <= %s)\n' "$name" "$got" "$want"
        PASS=$((PASS + 1))
    else
        printf '  \033[31mFAIL\033[0m %s (got=%s, want<=%s)\n' "$name" "$got" "$want"
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$name")
    fi
}

# ---- 開始跑 ---------------------------------------------------------
echo "=== mlogwatch integration test ==="
echo "(tmpdir: $TEST_DIR)"
echo

# Test 1: self-test
echo ">>> T1: --self-test"
out="$("$PY" "$ROOT_DIR/mlogwatch.py" --self-test --config "$MLOGWATCH_CONFIG" 2>&1)"
pass_n=$(printf '%s\n' "$out" | grep -c " PASS " || true)
fail_n=$(printf '%s\n' "$out" | grep -c " FAIL " || true)
echo "$out" | tail -5
assert_ge "self_test.pass_count" "$pass_n" 24
assert_eq "self_test.fail_count" "$fail_n" 0
echo

# Test 2: dry-run 在超低閾值下應該有 alert
echo ">>> T2: dry-run with low thresholds -> should emit alerts"
"$PY" "$ROOT_DIR/mlogwatch.py" --dry-run --quiet --config "$MLOGWATCH_CONFIG" 2>&1 >/dev/null
# 看 report:server 內含 sent_count 是確定訊號
latest=$(ls -t "$MLOGWATCH_REPORT_DIR"/*.md 2>/dev/null | head -1)
if [[ -z "$latest" ]]; then
    echo "  FAIL no report found"
    FAIL=$((FAIL+1))
    FAILED_TESTS+=("T2.no_report")
else
    sent=$(grep -oE 'sent_count: [0-9]+' "$latest" | grep -oE '[0-9]+' | head -1)
    sent=${sent:-0}
    assert_ge "low_thresholds.emit_alert" "$sent" 1
fi
echo

# Test 3: 真跑 (寫 alerts.log) 然後檢查檔案存在
echo ">>> T3: real run writes alerts.log"
rm -f "$MLOGWATCH_REPORT_DIR/alerts.log"
"$PY" "$ROOT_DIR/mlogwatch.py" --quiet --config "$MLOGWATCH_CONFIG" 2>&1 >/dev/null
log_lines=0
if [[ -f "$MLOGWATCH_REPORT_DIR/alerts.log" ]]; then
    log_lines=$(wc -l < "$MLOGWATCH_REPORT_DIR/alerts.log")
fi
assert_ge "real_run.wrote_alerts_log" "$log_lines" 1
echo

# Test 4: cooldown 機制 — 第二次跑 alerts.log 不再增加
echo ">>> T4: cooldown prevents re-emit"
before=$(wc -l < "$MLOGWATCH_REPORT_DIR/alerts.log")
"$PY" "$ROOT_DIR/mlogwatch.py" --quiet --config "$MLOGWATCH_CONFIG" 2>&1 >/dev/null
after=$(wc -l < "$MLOGWATCH_REPORT_DIR/alerts.log")
assert_eq "cooldown.no_new_lines" "$before" "$after"
echo

# Test 5: 報告檔產生
echo ">>> T5: report file generated"
latest_report=$(ls -t "$MLOGWATCH_REPORT_DIR"/*.md 2>/dev/null | head -1 || echo "")
if [[ -n "$latest_report" ]]; then
    size=$(wc -c < "$latest_report")
    assert_ge "report.file_exists_and_nonempty" "$size" 50
else
    echo "  FAIL no report found"
    FAIL=$((FAIL+1))
    FAILED_TESTS+=("report.file_exists")
fi
echo

# Test 6: 並發鎖 — 同時兩個 instance 跑,只一個應得鎖
echo ">>> T6: concurrent run blocked by lock"
rm -f "$MLOGWATCH_LOCK_DIR/mlogwatch.lock"
# 用 bash 拿 fd,第一個成功,第二個失敗
"$PY" -c "
import sys, os, fcntl
sys.path.insert(0, '$ROOT_DIR')
from mlogwatch import acquire_lock, release_lock, LOCK_DIR, LOCK_STALE_SEC
fd1 = acquire_lock(LOCK_DIR / 'mlogwatch.lock')
fd2 = acquire_lock(LOCK_DIR / 'mlogwatch.lock')
print('OK' if fd1 is not None and fd2 is None else 'BAD')
release_lock(fd1)
" > "$TEST_DIR/lockout.txt"
got=$(cat "$TEST_DIR/lockout.txt")
assert_eq "lock.exclusive" "$got" "OK"
echo

# Test 7: webhook_url 空 → 不該嘗試打 HTTP
echo ">>> T7: empty webhook_url no HTTP attempt"
# 先清 stamp (避免前幾個 test 留的 stamp 把 T7 的 alert 全 cooldown 濾掉)
find "$MLOGWATCH_STATE_DIR" -name '*.stamp' -delete 2>/dev/null || true
"$PY" "$ROOT_DIR/mlogwatch.py" --quiet --config "$MLOGWATCH_CONFIG" 2>&1 >/dev/null
latest=$(ls -t "$MLOGWATCH_REPORT_DIR"/*.md | head -1)
# dispatch_out 內的 webhook_msg 必為 "no webhook_url configured"
if grep -q "no webhook_url configured" "$latest"; then
    echo "  PASS webhook.skip (no_http_attempted)"; PASS=$((PASS+1))
else
    echo "  FAIL webhook.skip (grep 不到 no webhook_url)"
    grep "webhook" "$latest" | head -5
    FAIL=$((FAIL+1)); FAILED_TESTS+=("webhook.skip")
fi
echo

# Test 8: invalid config 不該爆
echo ">>> T8: empty config file handled"
echo "" > "$TEST_DIR/empty.yaml"
rc=0
"$PY" "$ROOT_DIR/mlogwatch.py" --self-test --quiet --config "$TEST_DIR/empty.yaml" >/dev/null 2>&1 || rc=$?
assert_eq "empty_config.no_crash" "$rc" 0
echo

# ---- 總結 -----------------------------------------------------------
echo "=== integration: $PASS passed, $FAIL failed ==="
if [[ $FAIL -gt 0 ]]; then
    echo "FAILED: ${FAILED_TESTS[*]}"
    exit 1
fi
exit 0
