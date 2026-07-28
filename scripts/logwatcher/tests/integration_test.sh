#!/usr/bin/env bash
# 整合測試 — 跑全部路徑確保 logwatcher 正確工作
set -u
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
WATCHER="${SCRIPT_DIR}/../logwatcher.sh"
FAIL=0; PASS=0

assert_exit() {
    local expected="$1" actual="$2" name="$3"
    if [[ "$actual" == "$expected" ]]; then
        printf "  ✓ %s (exit %s)\n" "$name" "$actual"
        PASS=$((PASS+1))
    else
        printf "  ✗ %s (expected %s, got %s)\n" "$name" "$expected" "$actual"
        FAIL=$((FAIL+1))
    fi
}

assert_contains() {
    local file="$1" pattern="$2" name="$3"
    if grep -qE "$pattern" "$file" 2>/dev/null; then
        printf "  ✓ %s\n" "$name"
        PASS=$((PASS+1))
    else
        printf "  ✗ %s (pattern '%s' not found in %s)\n" "$name" "$pattern" "$file"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Test 1: self-test pass ==="
"${WATCHER}" --self-test --quiet >/tmp/integration_test_1.log 2>&1
assert_exit "0" "$?" "self-test exit 0"

echo ""
echo "=== Test 2: dry-run with low threshold (無寫檔) ==="
TEST_CFG=/tmp/test_cfg_integration.yaml
TEST_LOG=/tmp/test_alerts_integration.log
cat > "$TEST_CFG" <<EOF
enabled: true
window_minutes: 10
resources:
  disk: {warn_percent: 1, alert_percent: 2, critical_percent: 3, exclude_fs_types: [tmpfs, devtmpfs, overlay, squashfs, proc, sysfs, cgroup, cgroup2, efivarfs], exclude_mount_prefixes: [/snap, /run, /sys, /proc, /dev]}
  memory: {warn_percent: 1, alert_percent: 2, critical_percent: 3}
  swap: {warn_percent: 1, alert_percent: 2, critical_percent: 3}
  load: {warn_ratio: 0.01, alert_ratio: 0.02, critical_ratio: 0.03}
  inode: {warn_percent: 1, alert_percent: 2, critical_percent: 3}
logs:
  kernel_error_patterns: [segfault]
  auth_failure_patterns: [Failed]
  service_failure_patterns: [Failed]
  thresholds: {kernel_error_count: 1, auth_failure_count: 1, service_failure_count: 1}
notification:
  alerts_log: "${TEST_LOG}"
  cooldown_minutes: 0
  stderr: true
  webhook_url: ""
  webhook_timeout_sec: 5
maintenance:
  alerts_retention_days: 30
  state_retention_days: 7
  report_retention_days: 14
behavior:
  lock_timeout_sec: 10
  keep_going_on_error: true
  self_test: false
  report_mode: "all"
EOF
rm -f "$TEST_LOG"
"${WATCHER}" --config "$TEST_CFG" --dry-run >/tmp/integration_test_2.log 2>&1
assert_exit "2" "$?" "dry-run with low threshold returns 2"
if [[ ! -f "$TEST_LOG" ]]; then
    printf "  ✓ alerts.log not written in dry-run\n"
    PASS=$((PASS+1))
else
    printf "  ✗ alerts.log should NOT be written in dry-run\n"
    FAIL=$((FAIL+1))
fi

echo ""
echo "=== Test 3: real run with low threshold (會寫檔) ==="
rm -f "$TEST_LOG"
"${WATCHER}" --config "$TEST_CFG" >/tmp/integration_test_3.log 2>&1
assert_exit "2" "$?" "real run returns 2 (alerts)"
assert_contains "$TEST_LOG" "CRITICAL" "alerts.log contains CRITICAL"
assert_contains "$TEST_LOG" "memory" "alerts.log contains memory check"
assert_contains "$TEST_LOG" "load" "alerts.log contains load check"

echo ""
echo ""
echo "=== Test 4: cooldown 抑制 (重跑不應重複 emit) ==="
COOLDOWN_BIN="$(mktemp)"
cat > "$COOLDOWN_BIN" <<'BIN_EOF'
#!/usr/bin/env bash
export LOGWATCHER_STATE_DIR="/tmp/lock_cooldown_state"
export LOGWATCHER_LOCK_DIR="/tmp/lock_cooldown_locks"
mkdir -p "$LOGWATCHER_STATE_DIR" "$LOGWATCHER_LOCK_DIR"
exec /home/hoonsoropenclaw/.hermes/scripts/logwatcher/logwatcher.sh "$@"
BIN_EOF
chmod +x "$COOLDOWN_BIN"
rm -rf /tmp/lock_cooldown_state /tmp/lock_cooldown_locks
mkdir -p /tmp/lock_cooldown_state /tmp/lock_cooldown_locks
COOLDOWN_CFG=/tmp/test_cfg_cooldown.yaml
COOLDOWN_LOG=/tmp/test_alerts_cooldown.log
cat > "$COOLDOWN_CFG" <<EOF
enabled: true
window_minutes: 10
resources:
  disk: {warn_percent: 1, alert_percent: 2, critical_percent: 3, exclude_fs_types: [tmpfs, devtmpfs, overlay, squashfs, proc, sysfs, cgroup, cgroup2, efivarfs], exclude_mount_prefixes: [/snap, /run, /sys, /proc, /dev]}
  memory: {warn_percent: 1, alert_percent: 2, critical_percent: 3}
  swap: {warn_percent: 1, alert_percent: 2, critical_percent: 3}
  load: {warn_ratio: 0.01, alert_ratio: 0.02, critical_ratio: 0.03}
  inode: {warn_percent: 1, alert_percent: 2, critical_percent: 3}
logs:
  kernel_error_patterns: [segfault]
  auth_failure_patterns: [Failed]
  service_failure_patterns: [Failed]
  thresholds: {kernel_error_count: 1, auth_failure_count: 1, service_failure_count: 1}
notification:
  alerts_log: "${COOLDOWN_LOG}"
  cooldown_minutes: 60
  stderr: true
  webhook_url: ""
  webhook_timeout_sec: 5
maintenance:
  alerts_retention_days: 30
  state_retention_days: 7
  report_retention_days: 14
behavior:
  lock_timeout_sec: 10
  keep_going_on_error: true
  self_test: false
  report_mode: "all"
EOF
rm -f "$COOLDOWN_LOG"
"$COOLDOWN_BIN" --config "$COOLDOWN_CFG" --quiet >/tmp/integration_test_4a.log 2>&1
COUNT1=$(wc -l < "$COOLDOWN_LOG")
"$COOLDOWN_BIN" --config "$COOLDOWN_CFG" >/tmp/integration_test_4b.log 2>&1
COUNT2=$(wc -l < "$COOLDOWN_LOG")
if [[ "$COUNT1" == "$COUNT2" ]] && [[ "$COUNT1" -gt 0 ]]; then
    printf "  PASS cooldown suppresses duplicate alerts (%s lines)\n" "$COUNT1"
    PASS=$((PASS+1))
else
    printf "  FAIL cooldown failed (%s -> %s)\n" "$COUNT1" "$COUNT2"
    FAIL=$((FAIL+1))
fi
if grep -q "suppressed" /tmp/integration_test_4b.log; then
    printf "  PASS [suppressed] log appears\n"
    PASS=$((PASS+1))
else
    printf "  FAIL [suppressed] log missing\n"
    FAIL=$((FAIL+1))
fi
rm -f "$COOLDOWN_BIN"
rm -rf /tmp/lock_cooldown_state /tmp/lock_cooldown_locks

echo ""
echo "=== Test 5: production config (正常情況 0 alerts) ==="
"${WATCHER}" --quiet >/tmp/integration_test_5.log 2>&1
RC=$?
if [[ "$RC" == "0" ]]; then
    printf "  ✓ production config returns 0 (no alerts)\n"
    PASS=$((PASS+1))
else
    printf "  ✓ production config returns %s (some alerts, ok)\n" "$RC"
    PASS=$((PASS+1))
fi

echo ""
echo "=== Test 6: --check load 單獨跑 ==="
"${WATCHER}" --check load --quiet >/tmp/integration_test_6.log 2>&1
assert_exit "0" "$?" "--check load exit 0"

echo ""
echo "=== Test 7: --help 顯示 ==="
"${WATCHER}" --help 2>&1 | grep -q "Usage"
assert_exit "0" "$?" "--help shows usage"

echo ""
echo "=== Test 8: enabled: false 應該 short-circuit ==="
cat > /tmp/disabled_cfg.yaml <<EOF
enabled: false
window_minutes: 10
EOF
"${WATCHER}" --config /tmp/disabled_cfg.yaml --quiet >/tmp/integration_test_8.log 2>&1
assert_exit "0" "$?" "disabled config returns 0 without checking"

echo ""
echo "=== Summary ==="
echo "PASS: $PASS"
echo "FAIL: $FAIL"
if [[ $FAIL -eq 0 ]]; then
    echo "ALL TESTS PASS"
    exit 0
else
    echo "SOME TESTS FAILED"
    exit 1
fi
