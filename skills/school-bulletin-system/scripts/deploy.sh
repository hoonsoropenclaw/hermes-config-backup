#!/bin/bash
# deploy.sh — Vercel deploy for school-bulletin
# Usage: bash deploy.sh [commit-message]
set -e

PROJECT_DIR="$HOME/permanent-projects/school-bulletin"
cd "$PROJECT_DIR"

MSG="${1:-fix: $(date +'%Y-%m-%d %H:%M') auto-deploy by hermes cron}"
echo "[deploy] Committing: $MSG"

git add -A
git commit -m "$MSG"
git push origin main

echo "[deploy] Waiting for Vercel deploy..."
sleep 15

# Poll until deploy completes
for i in $(seq 1 20); do
  # Get Vercel deployment status via API
  CURL_OUTPUT=$(curl -s "https://api.vercel.com/v13/deployments?teamId=__dev&project=school-bulletin" \
    -H "Authorization: Bearer $VERCEL_TOKEN" 2>/dev/null)
  # Parse JSON with python
  STATUS=$(echo "$CURL_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('deployments'):
    print(d['deployments'][0]['status'])
else:
    print('pending')
" 2>/dev/null || echo "pending")
  echo "[deploy] Attempt $i: $STATUS"
  if [ "$STATUS" = "ready" ]; then
    echo "[deploy] Deployed successfully"
    exit 0
  fi
  sleep 15
done

echo "[deploy] Timeout waiting for deploy, check Vercel dashboard"
exit 1
