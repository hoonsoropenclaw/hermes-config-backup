# 路線 A 完成度清單 (Step 3a 規範,棒 1 自我驗收)

**日期**:2026-06-11
**執行者**:engineering-lead
**對象**:主 session 後續跑 Step 1-4 驗收用
**對應檔**:本檔為路線 A 棒 1 結束時的 self-audit,12 行表必填(9 Must + 3 補強)

---

## 完成度清單 (9 Must + 3 補強)

| # | Must | 描述 | 狀態 | 實作位置 (檔案 / 函式 / 行) | 驗收建議 |
|---|------|------|------|--------------------------|----------|
| 1 | **M-01** | 公告 CRUD | ✅ | `app/api/announcements/route.ts` POST/GET 全部、`app/api/announcements/[id]/route.ts` PATCH/DELETE、`app/admin/announcements/page.tsx` UI(路線 C 已完成) | `curl -X POST /api/announcements` + GET + PATCH + DELETE,4 method 跑通 |
| 2 | **M-02** | 附件上傳 | ✅ | `app/api/attachments/upload/route.ts` (Supabase Storage)、`app/api/attachments/[id]/download/route.ts` | `curl -F file=@x.pdf /api/attachments/upload` 後看 DB row + Storage bucket |
| 3 | **M-03** | 多標籤 (5 類) | ✅ | `app/api/tags/route.ts` GET/POST + `lib/repository.ts:listTags` + `components/FilterPanel.tsx` | `curl /api/tags` 撈到 22+ 個 seed 標籤(grade/class/department/activity/role) |
| 4 | **M-04** | 標籤 OR/AND 篩選 | ✅ | `lib/repository.ts:matchAnnouncement` (line 456-) | `curl '/api/announcements?groups=...'` 用 base64url JSON |
| 5 | **M-05** | 處室隔離 | ✅ 路線 A 補 1 | `lib/repository.ts:matchAudience` (line 417-438) + `app/page.tsx` (line 44-55) 套 audience | `curl` teaching 帳號登入後只能看到「教務處 + 公開」公告;看不到 student 處室內部公告 |
| 6 | **M-06** | 5 層 RBAC | 🟡 v1 簡化 | `lib/repository.ts:matchAudience` (3 規則) + `app/api/seed-demo/route.ts` 加 3 個非處室 demo (`teacher_lin`/`parent_chen`/`student_wang`) + `user_role_assignments` 表 | `curl` student_wang 登入後看不到「教師專屬」公告;parent_chen 看不到「教師專屬」公告 |
| 7 | **M-07** | 已讀/已簽追蹤 | ✅ 路線 A 補 3 | `lib/repository.ts:signature_receipts CRUD` (line 564-) + `app/api/announcements/[id]/sign/route.ts` + `app/api/announcements/[id]/receipts/route.ts` + `app/api/me/signatures/route.ts` + `app/announcements/[id]/SignatureButton.tsx` + `app/admin/announcements/page.tsx` 加「簽收 X 人」 | `curl -X POST /api/announcements/<id>/sign` 後看 DB row;`curl /api/me/signatures` 撈到自己的簽收紀錄;後台 admin 列表看到「簽收 N 人」 |
| 8 | **M-08** | 推播 | ❌ v1 不做 | (空) | (已在 README「v1 不做」段列) |
| 9 | **M-09** | 行動裝置 RWD | ✅ | 全專案 Tailwind responsive(`sm:`/`md:`/`lg:`) | 開瀏覽器縮放視窗測 |
| 10 | **🔐 密碼修改補強** | admin 改密碼 | ✅ 路線 C | `app/api/auth/change-password/route.ts` + `/admin/settings` | `curl -X POST /api/auth/change-password` |
| 11 | **✏️ 編輯 UI 補強** | M-01 編輯 | ✅ 路線 C | `/admin/announcements/[id]/edit/page.tsx` + `AnnouncementEditor.tsx` 加 `initial?` prop | 開瀏覽器點「編輯」 |
| 12 | **🗑️ 刪除 UI 補強** | M-01 刪除 | ✅ 路線 C | `AnnouncementActions.tsx` | 開瀏覽器點「刪除」+ 確認 |

---

## 路線 A 補完實際進度

| 補完項 | 狀態 | 程式碼新增/修改 |
|--------|------|----------------|
| 補 1: 處室隔離 (M-05) | ✅ | `lib/repository.ts` 加 `AudienceFilter` 介面 + `matchAudience()` 同步函式;`app/page.tsx` 從 session 撈 `me` + `getUserRoleTagIds()` 套到 listAnnouncements |
| 補 2: 受眾分流 (M-06) | ✅ | `app/api/seed-demo/route.ts` 加 3 個非處室 demo (`teacher_lin`/`parent_chen`/`student_wang`),各指派 1 個 `tags.type='role'`(教師/家長/學生);公告 sample 加 role 標籤 |
| 補 3: 簽收 (M-07) | ✅ | 3 張新表 SQL(`_supabase_schema.sql` line 86-132)、3 個 API、新增 `SignatureButton.tsx`、詳情頁掛上、後台公告列表加「簽收 N 人」 |

---

## 新建 / 修改檔案清單

### 新建 (5 個)

1. `app/api/announcements/[id]/sign/route.ts` — POST 簽收
2. `app/api/announcements/[id]/receipts/route.ts` — GET 已讀/已簽名單
3. `app/api/me/signatures/route.ts` — GET 個人簽收紀錄
4. `app/announcements/[id]/SignatureButton.tsx` — Client 按鈕
5. `README.md` — 完整文件 + v1 不做清單

### 修改 (8 個)

1. `lib/types.ts` — 加 `ReadReceipt` / `SignatureReceipt` / `UserRoleAssignment` / `AudienceFilter` / `RoleTagName` 型別
2. `lib/repository.ts` — 加 3 張新表 CRUD + `listAnnouncements` 改寫支援 audience 過濾
3. `lib/auth.ts` — `getCurrentUser()` 多撈 `roleTagIds` 回傳
4. `app/api/announcements/route.ts` — GET 從 session 撈 audience 套用
5. `app/api/seed-demo/route.ts` — 加 3 個非處室 demo + 公告加 role 標籤
6. `app/page.tsx` — 套用 audience 過濾
7. `app/announcements/[id]/page.tsx` — 加「我已簽收」按鈕
8. `app/admin/announcements/page.tsx` — 加「簽收 N 人」統計
9. `_supabase_schema.sql` (handoff 目錄) — 加 3 張新表 DDL + RLS

### 新建 SQL (3 張新表 + 索引)

```
user_role_assignments
  PRIMARY KEY (user_id, role_tag_id)
  FK → users(id) ON DELETE CASCADE
  FK → tags(id) ON DELETE CASCADE

signature_receipts
  id TEXT PK, announcement_id, user_id, signed_at, ip_address, user_agent
  UNIQUE INDEX (announcement_id, user_id)

read_receipts
  id TEXT PK, announcement_id, user_id, read_at
  UNIQUE INDEX (announcement_id, user_id)
```

---

## 已知簡化與妥協

1. **M-06 5 層 RBAC 簡化**:users.role 仍只有 2 種 enum(dept_officer/sysadmin),受眾身分(teacher/parent/student/guest)走既有 tags.type='role' + user_role_assignments 對應表。v2 才擴 enum。
2. **M-07 已讀未實作 UI 自動觸發**:read_receipts 表已建好,但詳情頁進入時自動標記已讀的 hook 還沒寫(只後台用 countSignatures 統計)。v1.1 加。
3. **departments 表 seed**:目前 departments 表用 `INSERT ... ON CONFLICT DO NOTHING`,不依賴 seed(已在 _supabase_schema.sql 直接寫死)。
4. **附件下載無處室隔離**:詳情頁附件下載未加 audience 檢查,v1.1 加。

---

## 跑過的驗證

- ✅ `npm run typecheck` 0 error
- ✅ `npm run build` 0 error(新增 3 個 API route 出現)
- ⏳ `npm run dev` + 6 demo 帳號登入(等部署後跑 E2E)
- ⏳ E2E curl 6 demo + 簽收 + 受眾分流 + 處室隔離(見 `line_a_e2e.sh`)

---

**棒 1 self-audit 完成**,待主 session 跑 Step 1-4 驗收。
