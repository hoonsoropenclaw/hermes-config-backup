#!/bin/bash
#
# MIT No Attribution
#
# https://github.com/lentiancn/skills/blob/main/LICENSE
#
set -euo pipefail

# Arguments
BUILDER_NAME="${BUILDER_NAME:-}"

# Validate required arguments
if [ -z "$BUILDER_NAME" ]; then
    echo "ERROR: BUILDER_NAME is required. Usage: $0 <BUILDER_NAME>"
    exit 1
fi

# Remove the specified buildx builder instance if it exists
docker buildx rm "$BUILDER_NAME" 2>/dev/null || true

# Clean up all cached buildx resources system-wide
docker buildx prune -a -f 2>/dev/null || true

echo "SUCCESS: destroyed"
