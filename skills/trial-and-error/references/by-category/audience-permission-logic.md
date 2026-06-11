# Audience / 角色權限邏輯 — 最終定案（school-bulletin C 方案）

> 2026-06-11 路線 A 兩次踩坑 + 使用者三次改主意後定稿。
> **任何後續改 audience 邏輯前必讀這份**。
> **C 方案是使用者的最終決策** — 跟 PRD §4.3.4 v1 不一致是有意為之、不是 bug。

## 使用者決策歷程（保留作為未來決策參考）

| 順序 | 提案 | 使用者回應 | 結果 |
|------|------|-----------|------|
| 1 | v1 (棒 1 寫的)：dept_officer return true、其他看 audience | 「教務處登入後看到 2 個、未登入看到 4 個，這個邏輯正確嗎？」 | **抓到 bug**、棒 1 邏輯反了 |
| 2 | A 方案：砍掉角色矩陣、任何登入者看全部 + 任何人都可發布 | 「A 違反 PRD 4.3.4」 | **赫米斯拒絕執行** |
| 3 | A 修正：照使用者說的簡化 | 「更正，應該是 C 方案」 | **C 方案 v1 定案** |
| 4 | C v1：dept_officer 看全部 + 受眾看 audience + 受眾不可發布 | (確認) | 第一版上線 |
| 5 | **v3 反轉**：訪客只看到公開 → **訪客預設看全部** | 「訪客要能看到全部的公告才對，公告預設本來就是對外」 | **C 方案 v3** |
| 6 | **v4 簡化**：受眾 (teacher_lin/parent_chen) 還是看 audience → **登入後也看全部** | 「teacher_lin、parent_chen 都應該要看到 4 個公告、設定帳號登入的目的在於看到訪客看不到的『內部公告』，所以在『內部公告』這個機制完成之前，任何人都應該看到全部的『外部公告』」 | **C 方案 v4 最終定案** |

**L3 教訓**：使用者改主意是常態、不要在前 1-2 次反對意見就鎖死方向、但**底線（PRD 安全邊界）要守住**。

**L3 教訓 v3**：「公告預設對外」是公開學校網站的基本原則 — 在沒有「內部公告」機制前、未登入訪客應該看全部。「登入後變少」是 UX 倒車、不是資安。

**L3 教訓 v4（最高層級）**：「登入後能看到的 >= 未登入」是設計聖經 — 帳號登入的價值 = 看到訪客看不到的「內部公告」。在「內部公告」機制尚未建立的過渡期、登入者**不該被 audience 過濾**、否則登入 = 看更少 = 登入動機消失 = 設計 bug。

## C 方案 v4 最終邏輯（2026-06-11 HEAD = `ee67325`）

### 角色權限矩陣（C 方案 v4 版）

| 角色 | 看公告 (首頁) | 發布 / 編刪 | TopBar 顯示 |
|------|---------------|-------------|------------|
| **訪客 (未登入)** | **全部公告（v4 過渡期）** | 不可 | 「處室登入」按鈕 |
| dept_officer (6 個處室) | **全部公告** | ✅ | 處室名 · 姓名 |
| sysadmin (principal) | 全部公告 | ✅ | 處室名 · 姓名 |
| teacher / parent / student / guest | **全部公告（v4 簡化、登入後也看全部）** | ❌ 403 | 處室名 · 姓名 (role) |

### 鐵律（C 方案 v4）

#### 鐵律 1（v4 取代 v3）：過渡期 = 所有人都看全部
- v4 推翻 v3「受眾 audience 命中 + 公開」邏輯
- v4 理由（使用者親口）：**「登入的目的 = 看到『內部公告』。在『內部公告』機制完成之前 = 任何人都應該看到全部的『外部公告』」**
- 在「內部公告」機制 (isInternal 欄位) 建立前、**所有視角 = return true**
- 理由：登入後 < 未登入 = 登入動機消失 = 設計 bug
- **If** 你目前沒有 isInternal / audience_type 機制 **Then** matchAudience = `return true`、不要做任何 audience 過濾
- **If** 你看到 matchAudience 在受眾分支寫「audience.some(...)」**Then** = v3 舊邏輯、必升級 v4

#### 鐵律 2：dept_officer 看全部（C 方案特徵、不變）
- 這跟 PRD §4.3.4 v1 不一致 = **使用者明確決定簡化**
- 不需要「教務處看不到總務處的水電維護」這種隔離
- 理由：處室承辦本來就該互通、不知道其他處室在發什麼才是問題

#### 鐵律 3：受眾（teacher / parent / student / guest）只可讀、不可寫
- 受眾角色登入後**不能發布、不能編輯、不能刪除**公告
- API 層 (POST/PATCH/DELETE `/api/announcements`) 必加 403 檢查
- TopBar 隱藏「發布公告」按鈕給受眾角色
- **不是「去 seed-demo 看」** — 是程式碼層強制擋
- v4 重點：受眾登入後**看到全部**（不是 audience 命中）— 鐵律 1 過渡期邏輯

#### 鐵律 4：role 是 `text` 不是 enum（重要！影響 type 設計、不變）
- `users.role` 欄位在 Supabase 是 `text` 不是 PostgreSQL enum
- TypeScript 端 `User['role']` 原本只有 `'dept_officer' | 'sysadmin'`
- 改 C 方案時**必同步擴充 type union**：
  ```typescript
  role: 'dept_officer' | 'sysadmin' | 'teacher' | 'parent' | 'student' | 'guest';
  ```
- 漏了這步 = tsc 報錯、seed-demo 編譯失敗

#### 鐵律 5（v4 新增）：matchAudience 過渡期 = noop
- v4 程式碼直接 `return true`、不再 `audience.some(...)`
- `roleTagIdSet` 參數保留但用 `void` 標記、留給未來啟用 audience 過濾時
- **If** 你在 v4 之後看到 matchAudience 還在過濾 role tag **Then** 該檔案沒升級

### `matchAudience` C 方案 v4 版（v4 簡化關鍵）

```typescript
function matchAudience(a, audience, roleTagIdSet) {
  // v4 簡化: 過渡期 = 任何視角(訪客/處室/受眾)都看全部
  // 原因: 「內部公告」機制未建立前,登入者不該被 audience 過濾
  //      (登入後 < 未登入 = 登入動機消失 = 設計 bug)
  void roleTagIdSet;  // 保留參數,未來啟用 audience 過濾時用
  return true;
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

### Pass 條件（C 方案 v4、demo 資料 4 個公告）

| 帳號 | 預期 role | 預期看到 | 預期 POST 公告 |
|------|-----------|---------|---------------|
| **未登入** | - | **4（過渡期看全部）** | 401 |
| principal | sysadmin | 4 | 201 |
| teaching | dept_officer | 4 | 201 |
| student | dept_officer | 4 | 201 |
| general | dept_officer | 4 | 201 |
| counsel | dept_officer | 4 | 201 |
| it | dept_officer | 4 | 201 |
| **teacher_lin** | teacher | **4（v4 簡化、不再 audience 過濾）** | 403 |
| **parent_chen** | parent | **4（v4 簡化、不再 audience 過濾）** | 403 |
| **student_wang** | student | **4（v4 簡化、不再 audience 過濾）** | 403 |

### 反向檢查（任何 fail = bug、v4 版）

- ✅ **未登入訪客 = 4** = v4 過渡期邏輯生效
- ✅ **teacher_lin / parent_chen / student_wang = 4** = v4 簡化生效（v3 是 3 個）
- ✅ dept_officer 看全部 4 個（不是只看到本處室）
- ✅ 受眾角色 = 403 中文錯誤訊息「您的角色沒有發布公告的權限。處室承辦才能發布公告。」
- ✅ 所有 9 個登入帳號 + 未登入 = 都看到 4（v4 過渡期）
- ❌ **任何角色看到 < 4 = bug**（demo 資料只有 4 個公告、過渡期不該過濾）

## 反模式（C 方案 v3 版）

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

### ❌ 反模式 D（v4 新增、取代 v3 版本的 D）：matchAudience 還在做過濾
```typescript
// v3 寫法（v4 不適用）
function matchAudience(a, audience, roleTagIdSet) {
  const isGuest = !audience.viewerIsSysadmin && ...;
  if (isGuest) return true;  // ← v3 反轉
  // 對已登入受眾做 audience.some() 過濾  ← v3 邏輯
  if (audienceRoleTagIds.length === 0) return true;
  return audienceRoleTagIds.some(tid => viewerTags.includes(tid));
}
```
**為什麼錯（v4）**：「內部公告」機制未建立前、登入者不該被 audience 過濾、否則登入後看到比未登入少 = 設計 bug。v4 直接 `return true`。

**If** 你看到 matchAudience 不是 `return true` 開頭 **Then** 該檔案是 v1/v2/v3 舊版、必升級 v4。

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
2. **「登入後能看到的 >= 未登入」是設計聖經（v4 最高層級）** — 帳號登入的價值 = 看到訪客看不到的「內部公告」。在「內部公告」機制尚未建立的過渡期、登入者不該被 audience 過濾。否則登入 = 看更少 = 登入動機消失
3. **「公告預設對外」是公開學校網站的基本原則（v3）** — 在沒有「內部公告」機制前、未登入訪客應該看全部。「登入後變少」是 UX 倒車、不是資安
4. **使用者改主意是常態** — PRD 是起點、不是終點；使用者確認的新方案要尊重（v1→A→C v1→C v3→C v4 共 5 次改）
5. **底線要守住** — 即使簡化 PRD、寫入權限（受眾不可發布）不能砍。鐵律 3 不受 audience 簡化影響
6. **TypeScript type + DB schema 同步** — 改 role union 必同時改兩邊
7. **race condition 測試 9 帳號要 retry** — 第一次 login 偶爾 401、curl 重試就過、不算 bug
8. **鐵律 1 的 v4 邏輯 = 「無 audience 機制 = return true」** — 比 v3 還更簡化：完全不要做角色判斷。matchAudience 過渡期 = noop
9. **v4 是設計過渡期** — 當「內部公告」(isInternal / audience_type) 機制建立時、matchAudience 才有邏輯可寫。在那之前 = noop 對的
