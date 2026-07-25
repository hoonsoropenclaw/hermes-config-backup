#!/bin/bash
#
# MIT No Attribution
#
# https://github.com/lentiancn/skills/blob/main/LICENSE
#
set -euo pipefail

# Arguments
BUILDER_NAME="${BUILDER_NAME:-}"
PLATFORM="${PLATFORM:-}"
PROVENANCE="${PROVENANCE:-false}"
SBOM="${SBOM:-false}"
TAGS=("${TAGS[@]}")
BUILD_ARGS=("${BUILD_ARGS[@]}")

# Validate required arguments
if [ -z "${BUILDER_NAME}" ]; then
    echo "ERROR: BUILDER_NAME is required. Usage: $0 <BUILDER_NAME>"
    exit 1
fi
if [ -z "${PLATFORM}" ]; then
    echo "ERROR: PLATFORM is required. Usage: $0 <PLATFORM>"
    exit 1
fi
if [ ${#TAGS[@]} -eq 0 ]; then
    echo "ERROR: At least one tag must be provided via TAGS environment variable"
    exit 1
fi

# Iterate over all provided tags and build args
TAG_ARGS=()
for tag in "${TAGS[@]}"; do
  if [ -n "${tag}" ]; then
    TAG_ARGS+=("--tag" "${tag}")
  fi
done
BUILD_ARG_ARGS=()
for buildArg in "${BUILD_ARGS[@]}"; do
  if [ -n "${buildArg}" ]; then
    BUILD_ARG_ARGS+=("--build-arg" "${buildArg}")
  fi
done

# Build and push Docker image using buildx with specified parameters
docker buildx build \
  --platform "${PLATFORM}" \
  "${TAG_ARGS[@]}" \
  "${BUILD_ARG_ARGS[@]}" \
  --provenance="${PROVENANCE}" --sbom="${SBOM}" \
  --builder "${BUILDER_NAME}" \
  --push .

echo "SUCCESS: Build and push completed successfully"
