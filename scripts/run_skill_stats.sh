#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUS_SITE="/home/hoonsoropenclaw/hermes-status-site"

# === 自我修復：git push rejection recovery ===
deploy_with_git_recovery() {
  local max_retries=2
  local attempt=0

  while [ $attempt -le $max_retries ]; do
    attempt=$((attempt + 1))
    echo "[deploy] Attempt $attempt/$((max_retries + 1))"

    # Stage and commit (only if changes exist)
    git add -A
    if git diff --cached --quiet; then
      echo "[deploy] No changes to commit, skipping git push"
    else
      git commit -m "chore: skill stats $(date '+%Y-%m-%dT%H:%M')" || {
        # Author not configured — auto-fix and retry
        git config user.email "hermes@local" 2>/dev/null || true
        git config user.name "Hermes Agent" 2>/dev/null || true
        git commit -m "chore: skill stats $(date '+%Y-%m-%dT%H:%M')" || {
          echo "[deploy] WARN: git commit failed, skipping push"
          return 0
        }
      }
    fi

    # Try push
    if git push origin main 2>&1; then
      echo "[deploy] ✓ git push succeeded"
      return 0
    else
      echo "[deploy] git push rejected — attempting recovery (attempt $attempt)"

      # Fetch remote state
      git fetch origin main

      # Check if we are behind
      local local_hash=$(git rev-parse HEAD)
      local remote_hash=$(git rev-parse origin/main)

      if [ "$local_hash" = "$remote_hash" ]; then
        echo "[deploy] Already synced (local == remote), push likely succeeded on retry"
        return 0
      fi

      if [ $attempt -gt $max_retries ]; then
        echo "[deploy] FATAL: max retries reached, giving up"
        return 1
      fi

      # Recovery: rebase onto origin/main
      echo "[deploy] Rebasing onto origin/main..."
      if git rebase origin/main 2>&1; then
        echo "[deploy] ✓ rebase succeeded"
      else
        # Rebase conflict — abort and force-reset to origin/main
        echo "[deploy] WARN: rebase conflict, resetting to origin/main (losing local-only commits)"
        git rebase --abort 2>/dev/null || true
        git reset --hard origin/main
        # Regenerate stats (local commits lost)
        echo "[deploy] Regenerating stats after reset..."
        python3 "$SCRIPT_DIR/skill_usage_stats.py"
        git add -A
        git commit -m "chore: skill stats $(date '+%Y-%m-%dT%H:%M')" || return 0
      fi
    fi
  done
}

# === Main ===
python3 "$SCRIPT_DIR/skill_usage_stats.py"

cd "$STATUS_SITE"
deploy_with_git_recovery

# Vercel deploy (non-blocking — push matters most)
if [ -n "${VERCEL_API_TOKEN:-}" ]; then
  vercel --prod --yes --token "${VERCEL_API_TOKEN}" 2>&1 || echo "[vercel] WARN: deploy failed, but git push succeeded"
else
  echo "[vercel] SKIP: VERCEL_API_TOKEN not set"
fi

echo "[deploy] Done at $(date '+%Y-%m-%dT%H:%M')"