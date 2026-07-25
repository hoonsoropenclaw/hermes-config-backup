# School Bulletin — seed.sh D3 Exit — 2026-06-23

## 背景

`school-bulletin-system` skill 的 SKILL.md ⬜ 缺口追蹤的最後一項。2026-06-23 cycle 完成 D3 exit。

## 產出

`~/.hermes/skills/school-bulletin-system/scripts/seed.sh` — mtime 2026-06-23 00:55

功能：讀取 `$HOME/permanent-projects/school-bulletin/.env.local`，解析並去除雙引號，export 後執行 `npm run seed`（tsx 走 `lib/db.ts` 的 `getSupabaseAdmin()`）。

## 三個坑 + 修復

### 坑 1：路徑計算錯誤
```bash
# 錯 — 相對推導會變成 $HOME/.hermes/school-bulletin
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")/school-bulletin"

# 修復：直接 hardcode
PROJECT_DIR="$HOME/permanent-projects/school-bulletin"
```

### 坑 2：.env.local 值帶雙引號
症狀：`Error: Invalid supabaseUrl: Must be a valid HTTP or HTTPS URL.`
```bash
# .env.local: SUPABASE_URL="https://xxx.supabase.co"
# 修復：sed 去除雙引號
SUPABASE_URL="$(grep '^SUPABASE_URL=' "$ENV_FILE" | cut -d= -f2 | tr -d ' \r' | sed 's/^"//;s/"$//')"
```

### 坑 3：tsx 不自動讀取 .env.local
症狀：`Error: Supabase env 缺失。需要 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.`
```bash
export SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY
cd "$PROJECT_DIR" && npm run seed
```

## 驗證

```bash
$ bash ~/.hermes/skills/school-bulletin-system/scripts/seed.sh
=== School Bulletin Seed ===
✓ Users already seeded (9 found), skip
# (tags re-run 報 duplicate key — 見已知限制)
```

## 已知限制

`scripts/seed.ts` 的 `seedTags()` 無 idempotency，re-run 報 `duplicate key`。屬於專案原始碼問題，非 wrapper 問題。

## If→Then

**If** 從 skill scripts/ 目錄呼叫專案 wrapper  
**Then** 直接 hardcode 絕對路徑，不要相對推導

**If** 用 `grep|cut -d=` 從 `.env.local` 取值  
**Then** 用 `sed 's/^"//;s/"$//'` 去除雙引號

**If** 在 shell script 呼叫 `npm run X`  
**Then** `export` env vars 前後一致，並注意 tsx 不像 next.js 那樣自動讀 `.env.local`
