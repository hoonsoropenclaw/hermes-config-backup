# Handoff Chain 路線 A — Pre-flight 對照表 (Step 0b 必跑)

**日期**：2026-06-11
**目的**：在派棒 1 (spec) 前、主 session 先畫「9 個 Must vs 現有架構」對照、找漏網
**這份是鏈上** Step 0b（架構師 ↔ PRD 對照）**的 ground truth 餵給棒 1**

---

## 對照表（依 PRD §1.1 Must 9 項 + 補強 3 項）

| Must | 描述 | 現有架構對應模組/Box | 程式位置 | 現況 | 路線 A 行動 |
|------|------|----------------------|----------|------|-------------|
| **M-01** | 公告 CRUD | announcements table + 4 endpoints (POST/GET/PATCH/DELETE) | `app/api/announcements/route.ts`、`app/api/announcements/[id]/route.ts` | ✅ API 全套;🟡 UI 只有 Create/Read (編輯+刪除 UI 路線 C 已補) | **路線 C 已完成** |
| **M-02** | 附件上傳 | attachments table + Supabase Storage bucket | `app/api/attachments/upload/route.ts`、`app/api/attachments/[id]/download/route.ts` | ✅ 程式完整、🟡 seed 沒資料、無真實上傳測試 | **補強 1 個 seed 附件** |
| **M-03** | 多標籤 | tags table + tagIds array (JSONB) | `lib/types.ts:Tag`、`app/api/tags/route.ts` | ✅ 完整 (含自建標籤 POST) | (無) |
| **M-04** | 標籤 OR/AND 篩選 | groups query param (base64url) + FilterPanel client | `components/FilterPanel.tsx`、`lib/repository.ts:listAnnouncements` | ✅ 完整 (含 NOT 排除) | (無) |
| **M-05** | 各處室獨立登入 | users.departmentCode + admin layout | `app/admin/layout.tsx`、`lib/auth.ts` | 🟡 **登入/角色對、處室隔離沒做** (admin 看到全部公告) | **路線 A 補 1: 處室隔離** |
| **M-06** | 5 層 RBAC | users.role enum 已有 6 種 (`sysadmin/dept_officer/teacher/parent/student/guest`) | `lib/types.ts:User`、seed 6 帳號 | ❌ 角色定義有、**沒 audience 欄位、沒 RBAC middleware、沒學生/家長/訪客登入** | **路線 A 補 2: 受眾分流 (audience 標籤類型 + 公告列表按角色過濾)** |
| **M-07** | 已讀/已簽追蹤 | `read_receipts` + `signature_receipts` 兩表 (架構有) | schema 沒這兩表、UI 沒按鈕、API 沒 endpoint | ❌ **架構有、工程完全沒做** | **路線 A 補 3: 簽收按鈕 + DB 表 + 後台統計** |
| **M-08** | 推播 | `web-push` npm 套件 + VAPID 金鑰 env | 架構有、零程式碼 | ❌ **架構有、工程完全沒做** (VAPID 金鑰也要申請) | **路線 A 跳過 (P2)** + 寫進 README v1 不做清單 |
| **M-09** | 行動裝置 RWD | Tailwind responsive (sm:/md:/lg:) | `app/**/*.tsx` 5+ 處 | ✅ 完整 | (無) |
| **🔐 密碼修改** | admin 端 | `app/api/auth/change-password` + `/admin/settings` | route + form 完整 | ✅ 路線 C 已完成 | (無) |
| **✏️ 編輯 UI** | M-01 UI 補完 | `/admin/announcements/[id]/edit` + AnnouncementEditor 加 `initial` prop | 完整 | ✅ 路線 C 已完成 | (無) |
| **🗑️ 刪除 UI** | M-01 UI 補完 | AnnouncementActions client component | 完整 | ✅ 路線 C 已完成 | (無) |

---

## 路線 A 補 3 缺口 — 詳細拆解

### 補 1：處室隔離 (M-05)

**現況**：`app/admin/announcements/page.tsx` 用 `mine = all.filter(a => a.publisherId === me.id)`（處室承辦只看自己），**但首頁 `app/page.tsx` 所有登入用戶看到全部公告**。

**目標改動**：
1. 新增 `/api/me` 補完 — 現有 `getCurrentUser()` 已 return basic user、不夠 → 加 `getCurrentUserFull()` 完整版（含 roleTagIds、subscriptionTagIds）
2. `lib/repository.ts:listAnnouncements` 加參數 `audienceTagIds?: string[]` — 若傳了就用 `EXISTS` 子句過濾（只撈有「命中受眾標籤」的公告）
3. `app/page.tsx` 用 `getCurrentUserFull()` 撈 `roleTagIds`、加到 `listAnnouncements({ audienceTagIds })`
4. **公告建表時**：admin 選的「受眾身分」標籤自動變 audience filter（已經是 tagIds 內、不用拆）
5. **特殊角色**：
   - `dept_officer`：看「自己處室 + 公開公告」
   - `sysadmin`：看全部
   - `teacher/parent/student/guest`：只看「公開」或自己 audience 命中

**預估改動檔案**：5 個檔、約 1 小時
**新增 SQL**：不需要（tagIds 已經能表達 audience）

---

### 補 2：受眾分流 (M-06 子項)

**現況**：users 有 6 個 role enum、**但沒人用** — seed 都用 `dept_officer`/`sysadmin`、沒學生/家長登入

**目標改動**：
1. 改 seed：`/api/seed-demo` 加 3 個非處室 demo 帳號（teacher / parent / student）、各指派 audience tag
2. 加 `users.roleTagIds: string[]` 實際用於 audience 過濾（schema 已有、沒存值）
3. 公告「受眾身分」標籤（role 類型）— 建公告 UI 已有、announcement tagIds 內含 → 上面補 1 已經會用
4. **「學生看不到處室內部公告」**：在 announcement 列表 query 加 filter（teacher/parent/student role 只能看 visibility='public' 或 audience 含自己的 role tag）

**預估改動檔案**：3 個檔、約 45 分鐘
**新增 SQL**：需 ALTER users ADD COLUMN role_tag_ids text[] (或 jsonb) — idempotent migration

---

### 補 3：簽收 (M-07)

**現況**：架構有 `signature_receipts` table 設計、**schema 沒建、API 沒做、UI 沒按鈕**

**目標改動**：
1. **建表**：`signature_receipts` (id, announcement_id, user_id, signed_at, ip, user_agent) + `read_receipts` (id, announcement_id, user_id, read_at)
2. **API**：
   - `POST /api/announcements/[id]/sign` — 簽收
   - `GET /api/announcements/[id]/receipts` — 後台看簽收回條
   - `GET /api/me/signatures` — 個人簽收紀錄
3. **UI**：
   - 公告詳情頁：登入時若 requireSignature=true 顯示「我已簽收」按鈕（按下就 POST）
   - 未登入時不顯示
   - 簽收後顯示「✅ 已於 X 時間簽收」
4. **後台統計**（admin 列表）：顯示「簽收 X/Y」

**預估改動檔案**：4 個檔 + 1 個 SQL migration、約 1 小時
**新增 SQL**：2 張新表 (signature_receipts + read_receipts)

---

## 路線 A 排程（單棒規劃）

**只用 1 棒 engineering-lead**、**不串多棒**：
- 3 個缺口**都改同個檔**（repository.ts、listAnnouncements）→ 改一次比分 3 次省 context
- 估總共 2-3 小時實作（含 build 測試）
- 棒 4 = **主 session 接手**驗收（不再派 sub-agent、自己跑 4 步驗收）

---

## 跳過項目（要寫進 README v1 不做清單）

| Must | 跳過理由 | v2 規劃 |
|------|----------|---------|
| M-08 推播 | VAPID 金鑰需申請、web-push 套件整合 + service worker 估 1-2 天 | v1.1 評估是否加 Line Bot 替代 |
| 5 層 RBAC 完整 | 學生/家長/訪客登入需加 email/SSO 整合 | v2 評估 Google Classroom OAuth |
| 排程發布 | PRD §1.2 沒列、目前都是即時發 | v1.1 |
| 公告過期自動下線 (expireAt) | PRD §1.1 沒列 | v1.1 + Vercel Cron |

---

## 棒 1 prompt 草稿（用 timeout-sop §1.5 範本）

```
=== 棒 1: engineering-lead 任務 ===

你是 engineering-lead。任務：補完 3 個 PRD Must 缺口。

【必要產出】
1. 「完成度清單」對 9 個 Must + 3 補強 (見 handoff-chain-acceptance-sop.md Step 3a):
   | Must | 狀態 | 實作位置 (檔案/函式/行) | 驗收建議 |
   | ... |

2. 「架構 box → Must 對照表」(見 Step 0b):
   | 架構 box | 對應 Must | 程式位置 |

【必要實作】
- 補 1 (M-05 處室隔離): 見 pre-flight 補 1 段
- 補 2 (M-06 受眾分流): 見 pre-flight 補 2 段
- 補 3 (M-07 簽收): 見 pre-flight 補 3 段

【跳過】
- M-08 推播: 寫進 README 「v1 不做」段

【技術約束】
- 用 Supabase 已建好的表、新加 table 用 _supabase_schema.sql 一致風格
- 用 Tiptap 3 (已裝) - 不要裝新 rich text
- 用 Tailwind - 跟現有 class 一致
- timeout=1200s、background=true、notify=true

【必跑】(棒結尾自檢)
- npm run build 0 error
- curl 6 demo 帳號 (teaching/student/...) 登入都成功
- 跑至少 3 條新功能 curl 驗證 (簽收/受眾/隔離)
- 完成度清單 12 條全填 (9 Must + 3 補強)

【輸出】
- 寫到 ~/.hermes/handoff/school-bulletin/ 補 1/2/3 的 deliverable
- 跑 deliverable_audit.md 更新 (從 55% 升到 80%+)
```

---

**啟動：派棒 1 嗎？** 估 2-3 小時（含 5 分鐘監控、build 10 分鐘、deploy 2 分鐘、4 步驗收 30 分鐘）
