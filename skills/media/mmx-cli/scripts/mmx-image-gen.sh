#!/usr/bin/env bash
# mmx-image-gen.sh - MiniMax mmx-cli image generation wrapper
# Usage: mmx-image-gen.sh "prompt text" [output_dir] [aspect_ratio]
# Output dir default: /tmp/mmx-gen/
# Aspect ratio default: 16:9

set -euo pipefail

PROMPT="${1:-}"
OUTPUT_DIR="${2:-/tmp/mmx-gen}"
ASPECT="${3:-16:9}"

if [[ -z "$PROMPT" ]]; then
    echo "Usage: $0 <prompt> [output_dir] [aspect_ratio]"
    echo "  aspect_ratio: 16:9 (default), 1:1, 4:3, 3:4, 9:16"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Read API key from hermes .env using grep (safe, no glob issues)
ENV_FILE="$HOME/.hermes/.env"
API_KEY=""

if [[ -f "$ENV_FILE" ]]; then
    # Use grep with fixed string (not regex) to avoid *** glob issues
    KEY_LINE=$(grep -F "MINIMAX_API_KEY=" "$ENV_FILE" 2>/dev/null | grep -v "^#" | head -1 || true)
    if [[ -n "$KEY_LINE" ]]; then
        API_KEY=$(echo "$KEY_LINE" | cut -d'=' -f2- | tr -d '"' | xargs)
    fi
fi

if [[ -z "$API_KEY" ]]; then
    echo "Error: MINIMAX_API_KEY not found in $ENV_FILE" >&2
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/img_${TIMESTAMP}.jpg"

echo "Generating image..." >&2
echo "  Prompt: $PROMPT" >&2
echo "  Output: $OUTPUT_FILE" >&2

# Call mmx-cli via npx (auto-installs if needed)
RESULT=$(npx -y mmx-cli image generate     --api-key "$API_KEY"     --prompt "$PROMPT"     --aspect-ratio "$ASPECT"     2>/dev/null)

# Parse JSON response - look for "saved" array
SAVED=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    saved = d.get('saved', [])
    print(saved[0] if saved else '')
except:
    print('')
" 2>/dev/null || true)

if [[ -n "$SAVED" && -f "$SAVED" ]]; then
    cp "$SAVED" "$OUTPUT_FILE"
    echo "OK: $OUTPUT_FILE"
    echo "$OUTPUT_FILE"
elif [[ -f "$RESULT" ]]; then
    # Fallback: result might be a file path
    cp "$RESULT" "$OUTPUT_FILE"
    echo "OK: $OUTPUT_FILE"
    echo "$OUTPUT_FILE"
else
    echo "Error: generation failed" >&2
    echo "Raw result: $RESULT" >&2
    exit 1
fi
