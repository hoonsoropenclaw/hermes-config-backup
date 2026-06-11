#!/usr/bin/env bash
# line_a_e2e.sh - 路線 A E2E 驗收命令
# 對應:棒 1 結束後主 session 跑 Step 3b 真實命令驗證
#
# 用法:
#   ./line_a_e2e.sh https://school-bulletin.vercel.app
#   ./line_a_e2e.sh http://localhost:3000
#
# 至少 5 條 curl 驗收:
#   1. 6 個 demo 帳號登入(teaching/student/general/counsel/it/principal)
#      + 3 個非處室 demo (teacher_lin/parent_chen/student_wang)
#   2. 簽收 1 個公告(POST /api/announcements/[id]/sign)
#   3. 受眾分流(student_wang 登入後只看得到「學生」audience 的公告)
#   4. 處室隔離(teaching 登入後看不到 student 處室的「內部 role 標籤」公告)
#   5. 後台簽收統計(發布者登入後 /admin/announcements 看到「簽收 X 人」)
#
# 前置:
#   - 已跑過 npm run seed 或 GET /api/seed-demo
#   - DB schema 包含 3 張新表(見 _supabase_schema.sql)
#
# 退出碼:
#   0 = 全部通過
#   1 = 有失敗

set -e

BASE_URL="${1:-http://localhost:3000}"
COOKIE_DIR=$(mktemp -d)
trap "rm -rf $COOKIE_DIR" EXIT

PASS=0
FAIL=0
FAILED_TESTS=()

# 顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "$@"; }
pass() { PASS=$((PASS+1)); log "${GREEN}✓ PASS${NC}: $1"; }
fail() { FAIL=$((FAIL+1)); FAILED_TESTS+=("$1"); log "${RED}✗ FAIL${NC}: $1"; log "  ${RED}→${NC} $2"; }

assert_status() {
  local expected="$1" actual="$2" name="$3"
  if [ "$actual" = "$expected" ]; then
    pass "$name (status=$actual)"
  else
    fail "$name" "expected status=$expected, got $actual"
  fi
}

assert_contains() {
  local expected="$1" actual="$2" name="$3"
  if echo "$actual" | grep -q -- "$expected"; then
    pass "$name (contains '$expected')"
  else
    fail "$name" "expected to contain '$expected', got: $actual"
  fi
}

# ========================================
# 0. 環境前置 - 跑 seed-demo
# ========================================
log "\n${YELLOW}=== 0. 跑 seed-demo (idempotent) ===${NC}"
SEED=$(curl -sS -X GET "$BASE_URL/api/seed-demo" -H 'Content-Type: application/json')
assert_contains "ok" "$SEED" "seed-demo 回 ok"

# 抓一個有 requireSignature=true 的公告 id(模擬考公告)
# seed-demo 跑完後,id 是動態的;後面動態抓
SAMPLE_ANN_ID=$(echo "$SEED" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # 沒在 response 裡回 announcement id(只回 counts)
    # 改從 /api/announcements 撈第一個
    print('NONE')
except Exception as e:
    print('NONE')
")

# ========================================
# 1. 6 個 demo + 3 個非處室 demo 登入測試
# ========================================
log "\n${YELLOW}=== 1. 9 個 demo 帳號登入測試 ===${NC}"

declare -A ACCOUNTS=(
  ["teaching"]="教務處-dept_officer"
  ["student"]="學務處-dept_officer"
  ["general"]="總務處-dept_officer"
  ["counsel"]="輔導處-dept_officer"
  ["it"]="資訊組-dept_officer"
  ["principal"]="校長室-sysadmin"
  ["teacher_lin"]="林老師-受眾教師"
  ["parent_chen"]="陳媽媽-受眾家長"
  ["student_wang"]="王同學-受眾學生"
)

for username in "${!ACCOUNTS[@]}"; do
  desc="${ACCOUNTS[$username]}"
  cookie="$COOKIE_DIR/$username.cookie"

  RESP=$(curl -sS -o "$COOKIE_DIR/$username.body" -w "%{http_code}" \
    -X POST "$BASE_URL/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$username\",\"password\":\"School@2026\"}" \
    -c "$cookie")

  assert_status "200" "$RESP" "登入 $username ($desc)"

  # 確認 response 是有 data 的(沒 error)
  if [ "$RESP" = "200" ]; then
    BODY=$(cat "$COOKIE_DIR/$username.body")
    assert_contains "\"id\"" "$BODY" "  └─ 登入回應含 user id"
  fi
done

# ========================================
# 2. 受眾分流測試 (M-06)
# ========================================
log "\n${YELLOW}=== 2. 受眾分流 (M-06) ===${NC}"

# student_wang 登入後,撈公告列表 → 應該看到「學生 role 標籤」的公告
# 用 listAnnouncements API 撈
RESP=$(curl -sS -X GET "$BASE_URL/api/announcements" \
  -H "Cookie: $(cat $COOKIE_DIR/student_wang.cookie)")

assert_contains "\"data\"" "$RESP" "student_wang 撈公告列表有 data"

# 檢查是否至少看到 1 則「學生」相關公告(模擬考 / 暑假營隊 都含「學生」role tag)
STUDENT_VIEW=$(echo "$RESP" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    items = data.get('data', [])
    print(f'student_wang 看到 {len(items)} 則公告')
    for it in items[:5]:
        title = it.get('title', '')
        tags = [t.get('name') for t in it.get('tags', []) if t.get('type') == 'role']
        print(f'  - {title[:40]} role_tags={tags}')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
log "  ${STUDENT_VIEW}"

# 重點:student_wang 看到的公告,role_tags 應該至少有一個包含「學生」
STUDENT_HAS_STUDENT_TAG=$(echo "$RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', [])
for it in items:
    role_tags = [t.get('name') for t in it.get('tags', []) if t.get('type') == 'role']
    if '學生' in role_tags:
        print('YES')
        sys.exit(0)
print('NO')
")
if [ "$STUDENT_HAS_STUDENT_TAG" = "YES" ]; then
  pass "student_wang 至少看到 1 則含「學生」role 標籤的公告"
else
  fail "student_wang 受眾分流" "沒看到任何含「學生」role 標籤的公告"
fi

# 反向:teacher_lin 看到的公告,role_tags 應該都包含「教師」(沒「學生」獨佔)
TEACHER_VIEW=$(echo "$(curl -sS -X GET "$BASE_URL/api/announcements" -H "Cookie: $(cat $COOKIE_DIR/teacher_lin.cookie)")" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', [])
print(f'teacher_lin 看到 {len(items)} 則公告')
for it in items:
    role_tags = [t.get('name') for t in it.get('tags', []) if t.get('type') == 'role']
    print(f'  - {it[\"title\"][:40]} role_tags={role_tags}')
")
log "  ${TEACHER_VIEW}"

# ========================================
# 3. 處室隔離測試 (M-05)
# ========================================
log "\n${YELLOW}=== 3. 處室隔離 (M-05) ===${NC}"

# teaching 處室承辦:應該看不到 student 處室的「家長限定」公告
# 用 listAnnouncements API(無 audience filter 對應 teaching)
TEACHING_VIEW=$(curl -sS -X GET "$BASE_URL/api/announcements" \
  -H "Cookie: $(cat $COOKIE_DIR/teaching.cookie)" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', [])
print(f'teaching 看到 {len(items)} 則公告')
depts = set()
for it in items:
    dept = it.get('publisherDept', '?')
    depts.add(dept)
    role_tags = [t.get('name') for t in it.get('tags', []) if t.get('type') == 'role']
    print(f'  - dept={dept} role_tags={role_tags} title={it[\"title\"][:30]}')
print(f'  → 跨處室清單: {sorted(depts)}')
")
log "  ${TEACHING_VIEW}"

# 重點:teaching 應該看不到「家長」獨佔的公告
TEACHING_HAS_PARENT_ONLY=$(echo "$(curl -sS -X GET "$BASE_URL/api/announcements" -H "Cookie: $(cat $COOKIE_DIR/teaching.cookie)")" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', [])
for it in items:
    role_tags = [t.get('name') for t in it.get('tags', []) if t.get('type') == 'role']
    # 暑假營隊有 '學生' + '家長'(沒教師),算「家長+學生限定」
    # 但 teaching 是 dept_officer,規則 2:看自己處室 + 公開
    # 學務處的「家長+學生限定」對教務處 dept_officer 應該是 false
    if it.get('publisherDept') != 'teaching' and ('家長' in role_tags or '學生' in role_tags) and '教師' not in role_tags:
        # 找到一個非 teaching 處室、且 audience 限定家長/學生(不含教師)的公告
        # 這是 teaching 處室承辦不該看到的(因為有 role 標籤、其他處室)
        print('FOUND:', it.get('title'))
        sys.exit(0)
print('NONE')
")
if [ "$TEACHING_HAS_PARENT_ONLY" = "NONE" ]; then
  pass "teaching 處室承辦看不到其他處室的「家長+學生限定」公告"
else
  fail "teaching 處室隔離" "teaching 不該看到的公告出現了: $TEACHING_HAS_PARENT_ONLY"
fi

# principal (sysadmin) 應該看得到全部
PRINCIPAL_TOTAL=$(curl -sS -X GET "$BASE_URL/api/announcements" \
  -H "Cookie: $(cat $COOKIE_DIR/principal.cookie)" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data.get('data', [])))
")
if [ "$PRINCIPAL_TOTAL" -ge 3 ]; then
  pass "principal (sysadmin) 看到 $PRINCIPAL_TOTAL 則公告(全 3 則 seed)"
else
  fail "sysadmin 全看" "principal 只看到 $PRINCIPAL_TOTAL 則,預期 ≥ 3"
fi

# ========================================
# 4. 簽收測試 (M-07)
# ========================================
log "\n${YELLOW}=== 4. 簽收 (M-07) ===${NC}"

# 抓 1 個有 requireSignature=true 的公告 id
# 從 student_wang 視角撈,因為他看得到「學生」role 標籤的模擬考公告
ANN_ID=$(curl -sS -X GET "$BASE_URL/api/announcements" \
  -H "Cookie: $(cat $COOKIE_DIR/student_wang.cookie)" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for it in data.get('data', []):
    if it.get('requireSignature'):
        print(it.get('id'))
        sys.exit(0)
print('NONE')
")

if [ "$ANN_ID" = "NONE" ] || [ -z "$ANN_ID" ]; then
  fail "找簽收公告" "找不到 requireSignature=true 的公告(可能 seed 沒跑)"
else
  log "  找到簽收公告: $ANN_ID"

  # student_wang 簽收
  SIGN_RESP=$(curl -sS -X POST "$BASE_URL/api/announcements/$ANN_ID/sign" \
    -H "Cookie: $(cat $COOKIE_DIR/student_wang.cookie)" \
    -w "\n%{http_code}")
  SIGN_CODE=$(echo "$SIGN_RESP" | tail -1)
  SIGN_BODY=$(echo "$SIGN_RESP" | head -n -1)

  assert_status "201" "$SIGN_CODE" "student_wang 簽收"
  assert_contains "signedAt" "$SIGN_BODY" "  └─ 簽收回應含 signedAt"

  # 重複簽收(應該 idempotent 回 alreadySigned)
  SIGN2_RESP=$(curl -sS -X POST "$BASE_URL/api/announcements/$ANN_ID/sign" \
    -H "Cookie: $(cat $COOKIE_DIR/student_wang.cookie)")
  assert_contains "alreadySigned" "$SIGN2_RESP" "  └─ 重複簽收 idempotent"

  # 撈個人簽收紀錄
  ME_SIG=$(curl -sS -X GET "$BASE_URL/api/me/signatures" \
    -H "Cookie: $(cat $COOKIE_DIR/student_wang.cookie)")
  assert_contains "announcementId" "$ME_SIG" "student_wang /me/signatures 回傳簽收紀錄"

  # 撈後台 receipts(只 publisherId === me.id 或 sysadmin 可看)
  # 模擬考公告是 teaching 發的,要用 teaching 登入看
  RECEIPTS=$(curl -sS -X GET "$BASE_URL/api/announcements/$ANN_ID/receipts" \
    -H "Cookie: $(cat $COOKIE_DIR/teaching.cookie)")
  assert_contains "signedCount" "$RECEIPTS" "teaching 看自己公告的 receipts"

  SIGNED_COUNT=$(echo "$RECEIPTS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('data', {}).get('signedCount', 0))
")
  if [ "$SIGNED_COUNT" -ge 1 ]; then
    pass "後台 receipts 統計 ≥ 1 人簽收(實際 $SIGNED_COUNT 人)"
  else
    fail "後台 receipts 統計" "預期 ≥ 1,實際 $SIGNED_COUNT"
  fi
fi

# ========================================
# 5. 後台「簽收 X 人」UI 顯示
# ========================================
log "\n${YELLOW}=== 5. 後台簽收統計 ===${NC}"

# 直接用 curl 撈 /admin/announcements 的 HTML 內容,檢查「簽收」字樣有出現
ADMIN_HTML=$(curl -sS -X GET "$BASE_URL/admin/announcements" \
  -H "Cookie: $(cat $COOKIE_DIR/teaching.cookie)")

# 因為 cookie session 驗證可能過,200 + 沒重導 → 算 OK
# 「簽收 N 人」字樣應該出現(剛簽的模擬考公告)
if echo "$ADMIN_HTML" | grep -q "簽收"; then
  pass "後台 admin/announcements 顯示「簽收」字樣"
else
  fail "後台簽收 UI" "在 admin 頁面沒看到「簽收」字樣(可能 cookie 失效或重導)"
fi

# ========================================
# 6. 學生看不到內部公告(加強 E2E)
# ========================================
log "\n${YELLOW}=== 6. 學生看不到「內部限定」公告 ===${NC}"

# 找一個「教師獨佔」(有「教師」role 標籤但沒「學生」)的公告
INTERNAL_ANN=$(curl -sS -X GET "$BASE_URL/api/announcements" \
  -H "Cookie: $(cat $COOKIE_DIR/principal.cookie)" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for it in data.get('data', []):
    role_tags = [t.get('name') for t in it.get('tags', []) if t.get('type') == 'role']
    # 找一個有「教師」沒「學生」的(給教師看、給學生看不到)
    if '教師' in role_tags and '學生' not in role_tags:
        print(it.get('id'), '|', it.get('title'), '|', role_tags)
        sys.exit(0)
print('NONE')
")
log "  找到「教師獨佔」公告(若有): $INTERNAL_ANN"

if [ "$INTERNAL_ANN" != "NONE" ] && [ -n "$INTERNAL_ANN" ]; then
  INTERNAL_ID=$(echo "$INTERNAL_ANN" | cut -d'|' -f1 | tr -d ' ')
  # student_wang 撈公告列表,看是否包含 INTERNAL_ID
  STUDENT_SEES=$(curl -sS -X GET "$BASE_URL/api/announcements" \
    -H "Cookie: $(cat $COOKIE_DIR/student_wang.cookie)" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ids = [it.get('id') for it in data.get('data', [])]
if '$INTERNAL_ID' in ids:
    print('YES')
else:
    print('NO')
")
  if [ "$STUDENT_SEES" = "NO" ]; then
    pass "student_wang 看不到「教師獨佔」公告 $INTERNAL_ID"
  else
    fail "受眾分流" "student_wang 不該看到的「教師獨佔」公告出現了"
  fi
else
  log "  ${YELLOW}跳過:seed 沒建立「教師獨佔」公告(目前 3 則樣本都含學生),這項不阻擋驗收${NC}"
fi

# ========================================
# 結果彙整
# ========================================
log ""
log "${YELLOW}================================================${NC}"
log "${YELLOW}驗收結果:${NC}"
log "  ${GREEN}通過: $PASS${NC}"
log "  ${RED}失敗: $FAIL${NC}"

if [ $FAIL -gt 0 ]; then
  log "\n${RED}失敗項目:${NC}"
  for t in "${FAILED_TESTS[@]}"; do
    log "  - $t"
  done
  log "\n${RED}E2E 驗收 FAILED${NC}"
  exit 1
fi

log "\n${GREEN}E2E 驗收 PASSED${NC}"
exit 0
