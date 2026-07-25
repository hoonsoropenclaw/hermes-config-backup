#!/usr/bin/env bash
# ==============================================================================
# School Bulletin — Seed Demo Data
# 用途: 初始化 Supabase DB 的 demo 帳號 + 標籤
# 前提: .env.local 已設定 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
# 跑法: bash scripts/seed.sh
#       或從 hermes 直接: bash ~/.hermes/skills/school-bulletin-system/scripts/seed.sh
# ==============================================================================
set -euo pipefail

PROJECT_DIR="$HOME/permanent-projects/school-bulletin"

# Load env from .env.local (supabase credentials)
ENV_FILE="$PROJECT_DIR/.env.local"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ .env.local not found at $ENV_FILE"
  echo "   Copy .env.example to .env.local and fill in SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY"
  exit 1
fi

# Extract required vars (no 'export' prefix needed for this script's own subprocess)
SUPABASE_URL="$(grep '^SUPABASE_URL=' "$ENV_FILE" | cut -d= -f2 | tr -d ' \r' | sed 's/^"//;s/"$//')"
SUPABASE_SERVICE_ROLE_KEY="$(grep '^SUPABASE_SERVICE_ROLE_KEY=' "$ENV_FILE" | cut -d= -f2 | tr -d ' \r' | sed 's/^"//;s/"$//')"

if [[ -z "$SUPABASE_URL" || "$SUPABASE_URL" == *"placeholder"* || "$SUPABASE_URL" == '"'* ]]; then
  echo "❌ SUPABASE_URL is empty or placeholder in .env.local"
  exit 1
fi

if [[ -z "$SUPABASE_SERVICE_ROLE_KEY" || "$SUPABASE_SERVICE_ROLE_KEY" == *"placeholder"* || "$SUPABASE_SERVICE_ROLE_KEY" == '"'* ]]; then
  echo "❌ SUPABASE_SERVICE_ROLE_KEY is empty or placeholder in .env.local"
  exit 1
fi

echo "=== School Bulletin Seed ==="
echo "Project : $PROJECT_DIR"
echo "Supabase: ${SUPABASE_URL:0:40}..."
echo ""

# Export env so tsx subprocess sees them (tsx does NOT auto-load .env.local)
export SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY

cd "$PROJECT_DIR"
npm run seed
echo ""
echo "=== Seed complete ==="
echo ""
echo "Demo accounts:"
echo "  principal  / School@2026  (sysadmin — 校長室)"
echo "  teaching   / School@2026  (dept_officer — 教務處)"
echo "  student    / School@2026  (dept_officer — 學務處)"
echo "  general    / School@2026  (dept_officer — 總務處)"
echo "  counsel    / School@2026  (dept_officer — 輔導處)"
echo "  it         / School@2026  (dept_officer — 資訊組)"
