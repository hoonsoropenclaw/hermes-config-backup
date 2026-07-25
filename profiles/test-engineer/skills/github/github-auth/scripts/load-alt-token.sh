#!/bin/bash
# Load a secondary GitHub account's token from the isolated alt-token directory
# and export it as GH_TOKEN for the current shell.
#
# Usage:
#   source scripts/load-alt-token.sh <username>
#   GH_TOKEN="$GH_TOKEN" gh api user
#
# Required env / file layout:
#   ~/.config/hermes/alt_gh_tokens/<username>   (mode 0600, contains the token only)
#
# Why this script exists:
#   The user told you a second account's PAT path. Never read it into a code
#   string literal that could land in chat logs. Source this script to get the
#   token into the env without it ever being typed or echoed in this session.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: source $0 <github-username>" >&2
  return 1 2>/dev/null || exit 1
fi

USER="$1"
TOKEN_DIR="${HERMES_ALT_GH_TOKEN_DIR:-$HOME/.config/hermes/alt_gh_tokens}"
TOKEN_FILE="$TOKEN_DIR/$USER"

if [ ! -r "$TOKEN_FILE" ]; then
  echo "error: token file not found: $TOKEN_FILE" >&2
  echo "       expected layout: $TOKEN_DIR/<username>  (mode 0600)" >&2
  return 1 2>/dev/null || exit 1
fi

# Refuse to operate on a world-readable token
MODE=$(stat -c '%a' "$TOKEN_FILE" 2>/dev/null || stat -f '%Lp' "$TOKEN_FILE" 2>/dev/null)
if [ "${MODE:0:2}" != "60" ] && [ "${MODE:0:1}" != "6" ]; then
  echo "error: $TOKEN_FILE is not mode 0600 (got $MODE). Fix with: chmod 600 $TOKEN_FILE" >&2
  return 1 2>/dev/null || exit 1
fi

export GH_TOKEN
GH_TOKEN=$(cat "$TOKEN_FILE")

# Quick sanity check: this should be a PAT, not a stray file
case "$GH_TOKEN" in
  ghp_*|github_pat_*|ghs_*|gho_*|ghu_*)
    : # looks right
    ;;
  *)
    echo "warning: token does not start with a known GitHub PAT prefix" >&2
    ;;
esac

# Verify the token works AND report which account it is for.
# This proves we picked the right file before any destructive operations.
ACCT=$(curl -sS -H "Authorization: Bearer $GH_TOKEN" https://api.github.com/user \
       | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('login','?'))" 2>/dev/null)

if [ -z "$ACCT" ] || [ "$ACCT" = "?" ]; then
  echo "error: token in $TOKEN_FILE is invalid or network call failed" >&2
  unset GH_TOKEN
  return 1 2>/dev/null || exit 1
fi

if [ "$ACCT" != "$USER" ]; then
  echo "warning: token in $TOKEN_FILE belongs to '$ACCT', not '$USER'" >&2
fi

echo "✓ GH_TOKEN loaded for account: $ACCT" >&2
