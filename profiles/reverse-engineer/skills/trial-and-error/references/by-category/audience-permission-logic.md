# Audience / 角色權限邏輯 — 最終定案（school-bulletin C 方案）

> 2026-06-11 路線 A 兩次踩坑 + 使用者三次改主意後定稿。
> **任何後續改 audience 邏輯前必讀這份**。
> **C 方案是使用者的最終決策** — 跟 PRD §4.3.4 v1 不一致是有意為之、不是 bug。

## 使用者決策歷程（保留作為未來決策參考）

| 順序 | 提案 | 使用者回應 | 結果 |
|------|------|-----------|------|
| 1 | v1 (棒 1 寫的)：dept_officer return true、其他看 audience | 「教務處登入後看到 2 個、未登入看到 4 個，這個邏輯正確嗎？」 | **抓到 bug**、棒 1 邏輯反了 |
| 2 | A 方案：砍掉角色矩陣、任何登入者看全部 + 任何人都可發布 | 「A 違反 PRD 4.3.4」 | **赫米斯拒絕執行** |
| 3 | A 修正：照使用者說的簡化 | 「更正，應該是 C 方案」 | **C 方案定案** |
| 4 | C 方案：dept_officer 看全部 + 受眾看 audience + 受眾不可發布 | (確認) | **最終版** |

**L3 教訓**：使用者改主意是常態、不要在前 1-2 次反對意見就鎖死方向、但**底線（PRD 安全邊界）要守住**。

## C 方案最終邏輯（2026-06-11 HEAD = `af26b33`）

### 角色權限矩陣（C 方案版）

| 角色 | 看公告 (首頁) | 發布 / 編刪 | TopBar 顯示 |
|------|---------------|-------------|------------|
| 訪客 (未登入) | 公開公告 (無 audience role tag) | 不可 | 「處室登入」按鈕 |
| dept_officer (6 個處室) | **全部公告** | ✅ | 處室名 · 姓名 |
| sysadmin (principal) | 全部公告 | ✅ | 處室名 · 姓名 |
| teacher / parent / student / guest | **audience 命中** 或 公開 | ❌ 403 | 處室名 · 姓名 (role) |

### 鐵律（C 方案）

#### 鐵律 1：「登入後 >= 未登入」永遠成立
- 未登入 = 看到「公開公告」(`a.tagIds` 完全不含 audience role tag)
- 任何登入者 = **至少** 看到跟未登入一樣多 + 額外的
- dept_officer 看全部是 C 方案的有意決定（**砍掉 PRD §4.3.4 的「處室隔離」條款**）
- **If** 你的實作讓登入後 < 未登入 **Then** = bug。立刻 sanity check。

#### 鐵律 2：dept_officer 看全部（C 方案特徵）
- 這跟 PRD §4.3.4 v1 不一致 = **使用者明確決定簡化**
- 不需要「教務處看不到總務處的水電維護」這種隔離
- 理由：處室承辦本來就該互通、不知道其他處室在發什麼才是問題

#### 鐵律 3：受眾（teacher / parent / student / guest）只可讀、不可寫
- 受眾角色登入後**不能發布、不能編輯、不能刪除**公告
- API 層 (POST/PATCH/DELETE `/api/announcements`) 必加 403 檢查
- TopBar 隱藏「發布公告」按鈕給受眾角色
- **不是「去 seed-demo 看」** — 是程式碼層強制擋

#### 鐵律 4：role 是 `text` 不是 enum（重要！影響 type 設計）
- `users.role` 欄位在 Supabase 是 `text` 不是 PostgreSQL enum
- TypeScript 端 `User['role']` 原本只有 `'dept_officer' | 'sysadmin'`
- 改 C 方案時**必同步擴充 type union**：
  ```typescript
  role: 'dept_officer' | 'sysadmin' | 'teacher' | 'parent' | 'student' | 'guest';
  ```
- 漏了這步 = tsc 報錯、seed-demo 編譯失敗

### `matchAudience` C 方案版

```typescript
function matchAudience(a, audience, roleTagIdSet) {
  // 1. 訪客 (audience = null/undefined) → 只看公開
  if (!audience) {
    const audienceRoleTagIds = a.tagIds.filter(tid => roleTagIdSet.has(tid));
    return audienceRoleTagIds.length === 0;  // 沒 role tag = 公開
  }

  // 2. sysadmin / dept_officer → 看全部
  if (audience.viewerIsSysadmin || audience.viewerIsDeptOfficer) return true;

  // 3. 受眾 (teacher/parent/student/guest) → audience 命中 或 公開
  const audienceRoleTagIds = a.tagIds.filter(tid => roleTagIdSet.has(tid));
  if (audienceRoleTagIds.length === 0) return true;  // 公開
  const viewerTags = audience.viewerRoleTagIds ?? [];
  return audienceRoleTagIds.some(tid => viewerTags.includes(tid));
}
```

### API 層權限擋（POST / PATCH / DELETE）

```typescript
// 3 個端點都要加（C 方案）
if (me.role !== 'dept_officer' && me.role !== 'sysadmin') {
  return NextResponse.json(
    { error: { code: 'FORBIDDEN', message: '您的角色沒有 X 公告的權限。處室承辦才能 X 公告。' } },
    { status: 403 }
  );
}
```

### TopBar 隱藏「發布公告」按鈕

```typescript
const canPublish = me?.role === 'dept_officer' || me?.role === 'sysadmin';
// ...
{canPublish && <Link href="/admin/announcements/new">發布公告</Link>}
// 受眾角色額外顯示 role label
{me.role !== 'dept_officer' && me.role !== 'sysadmin' && (
  <span className="ml-1 text-xs text-ink-400">({me.role})</span>
)}
```

## E2E 驗收 SOP（C 方案版、每次改 audience 邏輯必跑）

### 9 帳號 + 未登入 必跑

```bash
BASE=https://school-bulletin.vercel.app  # 或本機 mirror
for u in principal teaching student general counsel it teacher_lin parent_chen student_wang; do
  curl -sS -c /tmp/c-$u.cookie -X POST $BASE/api/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$u\",\"password\":\"School@2026\"}"
  ann_count=$(curl -sS -b /tmp/c-$u.cookie "$BASE/api/announcements?limit=20" | jq '.data | length')
  me_role=$(curl -sS -b /tmp/c-$u.cookie "$BASE/api/auth/me" | jq -r '.data.role')
  echo "$u: role=$me_role anns=$ann_count"
done
# 未登入
ann_count=$(curl -sS "$BASE/api/announcements?limit=20" | jq '.data | length')
echo "(未登入): anns=$ann_count"
```

### Pass 條件（C 方案、demo 資料 4 個公告）

| 帳號 | 預期 role | 預期看到 | 預期 POST 公告 |
|------|-----------|---------|---------------|
| 未登入 | - | 1（公開） | 401 |
| principal | sysadmin | 4 | 201 |
| teaching | dept_officer | 4 | 201 |
| student | dept_officer | 4 | 201 |
| general | dept_officer | 4 | 201 |
| counsel | dept_officer | 4 | 201 |
| it | dept_officer | 4 | 201 |
| teacher_lin | teacher | 3（audience 命中） | 403 |
| parent_chen | parent | 3（audience 命中） | 403 |
| student_wang | student | 4（audience 命中） | 403 |

### 反向檢查（任何 fail = bug）

- ✅ 任何登入者看到的 >= 未登入
- ✅ dept_officer 看全部 4 個（不是只看到本處室）
- ✅ 受眾角色 = 403 中文錯誤訊息「您的角色沒有發布公告的權限。處室承辦才能發布公告。」

## 反模式（C 方案版）

### ❌ 反模式 A：v1 PRD 處室隔離
```typescript
if (aud.viewerIsDeptOfficer) {
  if (audienceRoleTagIds.length === 0) return true;
  if (a.publisherDept === aud.viewerDept) return true;
  return false;  // ❌ 教務處看不到總務處的水電
}
```
**為什麼錯**：使用者已決定 C 方案、不要 PRD §4.3.4 v1 處室隔離。

### ❌ 反模式 B：受眾可發布
```typescript
// 沒擋 me.role = teacher/parent/student
if (!me) return 401;
// 直接允許發布
```
**為什麼錯**：teacher_lin 登入可以發全校公告 = 嚴重安全漏洞。即使 C 方案簡化部分權限、**寫入權限要守住**。

### ❌ 反模式 C：忘記擴充 TypeScript type
```typescript
// seed-demo 寫 role: a.role  // a.role 可能是 'teacher'
// 但 User['role'] 只有 'dept_officer' | 'sysadmin'
// → tsc TS2322 報錯
```
**為什麼錯**：漏 type 擴充 = 整個 seed-demo 編譯失敗、無法跑 = 沒 demo 帳號可測。

## Schema migration 對應

C 方案要把現有 DB 裡的 3 個受眾帳號 role 從 `dept_officer` 改為 `teacher` / `parent` / `student`：

```sql
UPDATE users SET role = 'teacher' WHERE username = 'teacher_lin';
UPDATE users SET role = 'parent' WHERE username = 'parent_chen';
UPDATE users SET role = 'student' WHERE username = 'student_wang';
```

**If** 你跑 C 方案 **Then** 必跑這 3 行 SQL（直接 psql 連 Supabase、不用 migration tool）
**Then** 跟 `User['role']` type 擴充**同步進行**（任何一邊漏了 = 編譯或 runtime 失敗）

## L3 教訓

1. **改 audience 邏輯必先讀這份** — 不要從程式碼反推行為
2. **「登入後 >= 未登入」是聖經** — 任何能讓登入變少的邏輯 = bug
3. **使用者改主意是常態** — PRD 是起點、不是終點；使用者確認的新方案要尊重
4. **底線要守住** — 即使簡化 PRD、寫入權限（受眾不可發布）不能砍
5. **TypeScript type + DB schema 同步** — 改 role union 必同時改兩邊
6. **race condition 測試 9 帳號要 retry** — 第一次 login 偶爾 401、curl 重試就過、不算 bug
