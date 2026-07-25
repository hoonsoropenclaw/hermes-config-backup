#!/bin/bash
# ~/.hermes/scripts/run_regression.sh
# Regression testing: baseline snapshot vs current for API endpoints
# Usage: bash run_regression.sh <base_url> [output_dir]

set -euo pipefail

BASE_URL="${1:-}"
OUT_DIR="${2:-/tmp/regression_$(date +%Y%m%d_%H%M%S)}"
BASELINE_DIR="${BASELINE_DIR:-/tmp/regression_baseline}"

if [ -z "$BASE_URL" ]; then
  echo "Usage: bash $0 <base_url> [output_dir]"
  echo "Example: bash $0 https://school-bulletin.vercel.app"
  exit 1
fi

mkdir -p "$OUT_DIR" "$BASELINE_DIR"

echo "=== API Regression Test ==="
echo "Target: $BASE_URL"
echo "Output: $OUT_DIR"
echo "Baseline: $BASELINE_DIR"
echo ""

# Test endpoints — customize per project
ENDPOINTS=(
  "/api/departments"
  "/api/announcements?page=1&limit=10"
)

PASS=0
FAIL=0
NEW_BASELINE=0

for ep in "${ENDPOINTS[@]}"; do
  slug=$(echo "$ep" | tr '/?=&' '_')
  current_file="$OUT_DIR/${slug}.json"
  baseline_file="$BASELINE_DIR/${slug}.json"

  # Fetch current
  status=$(curl -s -o "$current_file" -w "%{http_code}" \
    "$BASE_URL$ep" 2>/dev/null || echo "000")

  if [ "$status" = "000" ]; then
    echo "🛑 $ep — CONNECTION FAILED"
    ((FAIL++))
    continue
  fi

  if [ "$status" -ge 500 ]; then
    echo "🛑 $ep — HTTP $status (server error)"
    ((FAIL++))
    continue
  fi

  # Format JSON consistently for comparison
  if command -v jq &> /dev/null && [ -s "$current_file" ]; then
    jq --sort-keys -c '.' < "$current_file" > "${current_file}.tmp" 2>/dev/null || true
    mv "${current_file}.tmp" "$current_file"
  fi

  if [ -f "$baseline_file" ]; then
    if diff "$baseline_file" "$current_file" > /dev/null 2>&1; then
      echo "✅ $ep — HTTP $status, no regression"
      ((PASS++))
    else
      echo "❌ $ep — HTTP $status, REGRESSION DETECTED"
      ((FAIL++))
      echo "--- diff ---"
      diff "$baseline_file" "$current_file" | head -30
      echo "--- end diff ---"
    fi
  else
    echo "🆕 $ep — HTTP $status, no baseline (created)"
    cp "$current_file" "$baseline_file"
    ((NEW_BASELINE++))
    ((PASS++))
  fi
done

echo ""
echo "=== Result: $PASS passed, $FAIL failed, $NEW_BASELINE new baselines ==="
if [ $FAIL -eq 0 ]; then
  echo "✅ OK to deploy"
  exit 0
else
  echo "❌ DO NOT DEPLOY — regressions detected"
  exit 1
fi
