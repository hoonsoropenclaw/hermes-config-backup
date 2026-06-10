#!/bin/bash
#
# MIT No Attribution
#
# https://github.com/lentiancn/skills/blob/main/LICENSE
#
set -euo pipefail

# Arguments
BUILDER_NAME="${BUILDER_NAME:-defaultbuilder}"
BUILD_CONCURRENCY="${BUILD_CONCURRENCY:-4}"

# Register cross-platform emulators for multi-architecture builds
docker run --privileged --rm tonistiigi/binfmt:latest --install all

# Remove existing buildx builder instance if it exists
docker buildx rm "$BUILDER_NAME" 2>/dev/null || true

# Clean up all cached Docker buildx resources
docker buildx prune -a -f 2>/dev/null || true

# Create a new docker-container driver builder with concurrency settings
docker buildx create \
    --name "$BUILDER_NAME" \
    --driver docker-container \
    --driver-opt env.BUILDKIT_MAX_PARALLELISM="$BUILD_CONCURRENCY" \
    --driver-opt env.BUILDKIT_CONCURRENCY="$BUILD_CONCURRENCY" \
    --use \
    --platform \
        linux/amd64,\
        linux/arm64,\
        linux/arm/v7,\
        linux/arm/v6,\
        linux/arm/v5,\
        linux/386,\
        linux/riscv64,\
        linux/ppc64le,\
        linux/s390x

# Bootstrap and verify the builder instance
docker buildx inspect "$BUILDER_NAME" --bootstrap

echo "SUCCESS: initted"
