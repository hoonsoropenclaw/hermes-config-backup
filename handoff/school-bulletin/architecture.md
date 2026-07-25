# 校園公告系統 :  系統架構文件 (Architecture)

**專案 slug**: school-bulletin
**整合者**: system-architect
**整合時間**: 2026-06-11
**上游產出**: prd.md (product-planner) + consumer-needs-research.md (consumer-researcher v2)
**語言規範**: 繁體中文,無 em-dash (U+2014)
**範圍宣告**: 本文件只描述「用什麼技術、為什麼、怎麼落地、怎麼交接給 engineering-lead」,不含前端 component 程式碼 (留給 engineering-lead 寫)、不含時程估計

---

## 目錄

1. 技術選型 (Frontend / Backend / DB / Storage / Deploy)
2. 資料模型 (TypeScript interface)
3. 標籤 OR/AND/Nested/NOT query 具體實作 (PostgreSQL SQL)
4. REST API 設計
5. Auth 設計 (JWT + bcrypt)
6. 附件上傳流程
7. Vercel 環境變數清單
8. 給 engineering-lead 的接力清單 (套件、資料夾、開發順序)

---

## 1. 技術選型

> 選型原則:MVP 範圍 (單一中型高中、1,000-3,000 學生、教職員 100-300 人)、開發速度快、擴展到 v2/v3 不需重寫、與 Vercel 部署生態系整合度高。

### 1.1 Frontend:Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui

- **選 Next.js 15** 是因為:(a) 同一個專案支援 SSR (公告列表 SEO 友善、未登入訪客可看 public 公告) 跟 CSR (後台互動) 不必拆兩個專案;(b) 內建 route handler 寫 API 不必再起後端 server (MVP 階段可省一台機器);(c) Vercel 一鍵部署零設定。
- **選 TypeScript** 是因為資料模型複雜 (公告 / 標籤 / 使用者 / 處室 / 附件 / 簽收 共 6 個核心實體),強型別能在編譯期抓出欄位打錯,這是「沒有 QA team」的單人開發者唯一保護。
- **選 Tailwind + shadcn/ui** 是因為:(a) shadcn/ui 是 copy-paste 進專案的元件 (不是 npm 依賴),改樣式不被上游綁住;(b) 公告系統 90% 是表單 + 列表 + 卡片,Tailwind 寫 utility class 比寫 CSS 模組快 3 倍;(c) 全部都是 RWD,手機優先時 Tailwind 的 `md:` `lg:` 寫法比 media query 清楚。

**為何不選**:
- ❌ Vite + React Router:SSR 要自己架、SEO 跟公告列表的 RSC 優化都做不到
- ❌ Nuxt 3:團隊不熟 Vue、生態系比 Next 小 (校園公告這規模的元件庫 shadcn/ui 是首選)
- ❌ 純 client-side SPA:SEO 跟「未登入訪客看 public 公告」做不到
- **替代方案與改用時機**:若 v3 要做「原生 APP」可改用 Expo + React Native 共用 business logic 層

### 1.2 Backend:Next.js Route Handlers (MVP) → 之後可拆 Express/Fastify (v2+)

- **MVP 階段直接用 Next.js Route Handlers** (`app/api/*/route.ts`):(a) 跟前端共用 TypeScript 型別,改 schema 不會前端後端脫鉤;(b) 部署只一個服務,Vercel 直接支援;(c) middleware (auth check、rate limit、CSRF) 寫在 `middleware.ts` 一處搞定。
- **Node.js runtime 選 Edge** (預設) 給唯讀 API (公告列表、標籤列表、查詢),**選 Node.js** 給寫入 API (發布公告、上傳附件) - 因為 Edge runtime 沒有 multipart parser 跟 file system 存取。
- **v2 拆出去時機** : 當 (a) API QPS > 500 或 (b) 需要背景 worker (推播批次寄送、附件掃毒) 時,把寫入 API 拆到獨立的 Node.js 服務 (Hono 或 Fastify),共用同一個 PostgreSQL 跟 Cloudflare R2。

**為何不選**:
- ❌ Supabase / Firebase BaaS : 標籤 OR/AND 巢狀篩選要寫 raw SQL,Supabase 的 RLS 表達不了「同類型 OR、跨類型 AND」這種 4 層巢狀;且 BaaS 對 RWD 客製化 UI 不友善
- ❌ GraphQL : 學校標案業主只熟 REST,GraphQL 多了 N+1 跟 schema 管理成本,效益不抵
- ❌ tRPC : 雖跟 Next.js 整合好,但本系統的「公告列表 + 標籤篩選」是純讀,用 REST + OpenAPI 對未來「校務系統介接」比較標準

### 1.3 Database:PostgreSQL 16 (Neon 託管)

- **選 PostgreSQL** 是因為:(a) 標籤 OR/AND 巢狀篩選需要 `WITH RECURSIVE` 或 `array_agg` + `EXISTS`,這是 PG 的強項;(b) JSONB 欄位可存「進階篩選器」的結構化 query (v2);(c) 全文搜尋內建 `tsvector` (MVP 用 pg 全文搜尋,v2 才考慮 Meilisearch)。
- **託管在 Neon** : (a) serverless 自動休眠,Vercel 部署免費方案可吃;(b) branch database (pre-production 環境可開一個 branch database 像 git branch 一樣);(c) 連線從 Vercel Edge 走 serverless driver (`@neondatabase/serverless`) 不需要 connection pool。
- **資料表策略**:`announcements`、`tags`、`announcement_tags` (多對多)、`users`、`departments`、`attachments`、`read_receipts`、`signature_receipts`、`subscriptions`、`audit_logs`、`saved_filters` 共 11 張表 + seed 6 個處室帳號。

**為何不選**:
- ❌ MySQL : `EXISTS` 巢狀效能差、JSONB 沒有 (要用 `JSON` 欄位、查詢沒 index)
- ❌ MongoDB : 公告跟標籤是多對多 + 5 種類型 + 巢狀篩選,NoSQL 寫起來 query 又臭又長,完全不是 NoSQL 強項
- ❌ SQLite : 單機檔案,多 Vercel region 部署時無法共享;且 `EXISTS` 巢狀在 SQLite 寫起來限制多
- **何時改** : 若 v3 要支援「跨校 multi-tenant」,用「shared database + tenant_id 欄位」即可,不必搬資料庫;若規模到 10+ 萬公告,改用 Citus (PG 分散式) 或搬 Aurora

### 1.4 Storage:Cloudflare R2 (S3 相容) - 附件本體

- **選 R2** 是因為:(a) **零 egress 費用** (這點對附件下載是殺手級優勢,學校每天 1,000+ 人下載報名表);(b) 跟 S3 API 完全相容,SDK 直接用 `@aws-sdk/client-s3` 不必換;(c) 單檔上限 5 TB,遠超 50MB 附件需求。
- **存什麼** : 附件本體 (PDF、Word、Excel、圖片、zip) + 縮圖 (圖片附件的 200x200 預覽) + 附件 metadata (mime、size、sha256) 在 PostgreSQL 才有。
- **Bucket 結構** : `school-bulletin-prod/attachments/<year>/<month>/<uuid>.<ext>` (按年月分前綴方便 lifecycle rule)。
- **URL 策略** : 附件下載 **不走 R2 公開 URL**,而是後端 `/api/attachments/:id/download` proxy 出去 (見 §6.4),這樣才能做存取控制跟稽核;圖片 / PDF 預覽 (v2-01) 才用時效簽名 URL (R2 presigned URL,1 小時 expiry)。

**為何不選**:
- ❌ Vercel Blob : 跟 Vercel 整合好但 egress 收費 (附件下載頻繁會爆預算)
- ❌ AWS S3 : egress 費用高、跟 Cloudflare 比起來貴約 5-10 倍
- ❌ Supabase Storage : 5GB 免費額度太小,50MB 附件約 100 個就滿了
- ❌ 自建 MinIO : 多一台 VM 要維運、學校標案業主不會接受「機房要再加一台」
- **何時改** : 若 v2 預覽附件用 Office online (需 Microsoft 365 訂閱),R2 不夠,改 AWS S3 (有 S3 Object Lambda) 或自建 LibreOffice headless 預轉檔

### 1.5 Deploy:Vercel (Hobby / Pro plan)

- **選 Vercel** 是因為:(a) Next.js 原生整合,`git push` 即部署;(b) Preview deployments 給每個 PR 獨立 URL (業主 / stakeholder 預覽用);(c) Edge Network 全球 CDN 對台灣學校夠用;(d) 環境變數管理、custom domain、analytics 內建。
- **環境分層** : `production` (正式) + `preview` (PR 預覽) + `development` (本地),Vercel 環境變數可分層設定。
- **CI/CD** : GitHub → Vercel 自動部署;主分支 push = production,PR = preview;不用自己寫 workflow。
- **Database migration** : 用 `drizzle-kit` 跑 migration,Vercel build hook 觸發 (build command = `pnpm db:push` 或自建 migration script)。
- **Cron job** : Vercel Cron (每天 02:00 跑備份驗證、每月 1 號跑過期公告清理) - 用 Next.js `app/api/cron/*` + `vercel.json` 設定。

**為何不選**:
- ❌ 校內機房自建 : MVP 階段學校 IT 沒人力維運;v2 之後若業主要求可加 Docker Compose 部署包
- ❌ Cloudflare Pages : 雖有 Pages Functions 但對 Next.js 支援沒 Vercel 好 (middleware 行為有差異)
- ❌ Railway / Render : 價格跟 Vercel 接近但 ecosystem 較弱 (沒 Preview deployments 的品質)
- **何時改** : 若 v3 要在中國部署,改用阿里雲 / 騰訊雲 (中國法遵需 ICP 備案,Vercel 在中國無 CDN)

### 1.6 附屬選型 (其他該提到的)

| 類別 | 選擇 | 原因 (1 句) |
|------|------|-------------|
| ORM | Drizzle ORM | TypeScript-first、零 runtime overhead、SQL 語法透明 (複雜 query 仍可寫 raw SQL) |
| Auth | Auth.js (NextAuth v5) + JWT | 內建 CSRF / session 處理、支援 email/password 跟未來 OAuth (校務系統 SSO) |
| Password hashing | bcrypt (cost 12) | PRD §5.2 要求;業界標準、Node.js 生態成熟 |
| Push notification | Web Push (VAPID) + 未來 FCM/APNs | MVP 推播只到「已加入主畫面的 PWA」使用者;原生 APP 推播留 v3 |
| 全文搜尋 | PostgreSQL `tsvector` (MVP) | 不必額外服務;v2 流量大再換 Meilisearch |
| Email 寄送 | Resend | API 簡單、有 Vercel 整合、免費額度 3,000/月 夠 MVP |
| 檔案掃毒 | ClamAV (自建) 或 Cloudmersive AV API | MVP 用 Cloudmersive 託管 (不用自建 daemon),每月 500 次免費 |
| 監控 | Vercel Analytics + Sentry (免費方案) | PV / API 響應時間 / 前端錯誤自動收 |
| 日誌 | Vercel Log Drains → CloudWatch 或自接 Loki | MVP 階段 Vercel 內建 Logs 夠用 |
| 測試 | Vitest (unit) + Playwright (E2E) | Vitest 跟 Vite 整合好、Playwright 跨瀏覽器 (Chrome/Safari/Firefox) |

---

## 2. 資料模型 (TypeScript Interface)

> 全部用 PostgreSQL 實作,以下 interface 對應 Drizzle schema (給 engineering-lead 直接照抄)。
> 命名:snake_case (DB 欄位) ↔ camelCase (TS 屬性),Drizzle 自動轉換。

### 2.1 核心實體 (5 個)

```typescript
// 公告 - 系統核心
interface Announcement {
  id: string;                  // UUID, primary key
  title: string;               // 1-200 字
  content: string;             // 純文字,支援換行 (MVP 不做 rich text)
  publisherId: string;         // FK → users.id
  publisherDept: string;       // FK → departments.code,從 token 帶入不可改
  status: 'published' | 'archived';  // MVP 不做 draft
  visibility: 'internal' | 'public';
  requireSignature: boolean;   // 是否需簽收
  signatureDeadline: Date | null;     // requireSignature=true 時必填
  publishAt: Date;             // 發布時間,MVP 預設 = 建立時間
  expireAt: Date | null;       // v2 過期自動下線
  createdAt: Date;
  updatedAt: Date;
  deletedAt: Date | null;      // 軟刪除
}

// 標籤 - 5 種類型,單一 table + type enum
interface Tag {
  id: string;                  // UUID
  type: 'grade' | 'class' | 'department' | 'activity' | 'role';
  name: string;                // 顯示名稱,同 type 內不可重複 (DB unique index)
  description: string | null;
  color: string | null;        // hex
  createdBy: string;           // FK → users.id
  createdAt: Date;
  isActive: boolean;           // 停用後不可掛新公告
}

// 公告 ↔ 標籤 多對多 (一則公告至少 1 個、最多 10 個)
interface AnnouncementTag {
  announcementId: string;      // FK
  tagId: string;               // FK
  createdAt: Date;
  // 複合主鍵 (announcementId, tagId)
}

// 使用者 - 6 種角色 (PRD §4.3.4)
interface User {
  id: string;
  email: string;               // unique
  passwordHash: string;        // bcrypt
  name: string;
  role: 'sysadmin' | 'dept_officer' | 'teacher' | 'parent' | 'student' | 'guest';
  departmentCode: string | null;  // FK → departments.code,dept_officer 必填
  gradeTagId: string | null;   // FK → tags.id (type=grade),student 必填
  classTagId: string | null;   // FK → tags.id (type=class),student 必填
  roleTagIds: string[];        // FK → tags.id (type=role) array,多身分 (例:家長+校友)
  subscriptionTagIds: string[];// FK → tags.id array,訂閱的標籤
  mustChangePassword: boolean; // 首次登入強制變更
  isActive: boolean;
  lastLoginAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

// 處室 - 6 個 seed
interface Department {
  code: string;                // PK:'academic' | 'student_affairs' | 'general_affairs' | 'counseling' | 'principal' | 'sysadmin'
  name: string;                // '教務處' | '學務處' | ...
  defaultEmailPrefix: string;  // 'academic.officer' | ...
}
```

### 2.2 業務實體 (4 個)

```typescript
// 附件 - 跟公告多對多 (一則公告可有 0-N 個附件,一個附件可重複用於多則公告)
interface Attachment {
  id: string;                  // UUID
  fileName: string;            // 原始檔名
  mimeType: string;            // 'application/pdf' | ...
  sizeBytes: number;           // < 50MB (單檔)
  sha256: string;              // 校驗用
  r2Key: string;               // 'attachments/2026/06/<uuid>.pdf'
  uploadedBy: string;          // FK → users.id
  scanStatus: 'pending' | 'clean' | 'infected' | 'error';
  scanCheckedAt: Date | null;
  createdAt: Date;
  deletedAt: Date | null;
}

// 公告 ↔ 附件 多對多
interface AnnouncementAttachment {
  announcementId: string;
  attachmentId: string;
  // 複合主鍵
}

// 已讀紀錄 - 進入公告詳情頁自動寫入
interface ReadReceipt {
  id: string;
  announcementId: string;      // FK
  userId: string;              // FK
  readAt: Date;                // 進入詳情頁的時間
  // 唯一索引 (announcementId, userId) - 同一則同一使用者只記一筆
}

// 簽收紀錄 - 使用者點 [我已確認簽收] 觸發
interface SignatureReceipt {
  id: string;
  announcementId: string;      // FK
  userId: string;              // FK
  signedAt: Date;              // 點擊時間
  ipAddress: string;           // 稽核用
  userAgent: string;           // 稽核用
  // 唯一索引 (announcementId, userId)
}
```

### 2.3 支援實體 (2 個)

```typescript
// 訂閱 - 跟使用者的 subscriptionTagIds 重複?不,這裡存「已儲存的篩選條件」(query 結構)
interface SavedFilter {
  id: string;
  userId: string;              // FK
  name: string;                // '我的課表' | '我的活動' | ...
  queryJson: string;           // 篩選條件 JSON,結構見 §3.5
  isDefault: boolean;          // 登入後預設套用
  createdAt: Date;
  updatedAt: Date;
}

// 稽核日誌 - 系統管理員動作 + 附件下載行為
interface AuditLog {
  id: string;
  actorId: string | null;      // FK → users.id,system action 為 null
  action: string;              // 'TAG_CREATE' | 'USER_DELETE' | 'ATTACHMENT_DOWNLOAD' | ...
  targetType: string;          // 'tag' | 'user' | 'attachment' | ...
  targetId: string | null;
  metadataJson: string;        // 動作細節 (JSON)
  ipAddress: string;
  userAgent: string;
  createdAt: Date;
  // 保留 1 年 (PRD §5.2)
}
```

### 2.4 實體關係總覽 (用文字描述,見 §3.6 Mermaid 圖)

- `User` (1) - (N) `Announcement` (發布者關係)
- `Department` (1) - (N) `User` (dept_officer 歸屬)
- `Announcement` (N) - (N) `Tag` (透過 `AnnouncementTag`)
- `Announcement` (N) - (N) `Attachment` (透過 `AnnouncementAttachment`)
- `Announcement` (1) - (N) `ReadReceipt` / `SignatureReceipt`
- `User` (N) - (N) `Tag` (透過 `User.subscriptionTagIds` JSONB 或 join table,MVP 用 JSONB 簡化)
- `User` (1) - (N) `SavedFilter`

### 2.5 重要索引 (SQL DDL hint,給 engineering-lead)

```sql
-- 公告列表分頁 + 標籤篩選的關鍵索引
CREATE INDEX idx_announcements_publish_at ON announcements (publish_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_announcement_tags_tag_id ON announcement_tags (tag_id, announcement_id);
CREATE INDEX idx_announcement_tags_announcement_id ON announcement_tags (announcement_id, tag_id);

-- 標籤唯一性 + 依類型查詢
CREATE UNIQUE INDEX idx_tags_type_name ON tags (type, name) WHERE is_active = true;

-- 使用者登入
CREATE UNIQUE INDEX idx_users_email ON users (email) WHERE is_active = true;

-- 已讀 / 已簽 去重
CREATE UNIQUE INDEX idx_read_unique ON read_receipts (announcement_id, user_id);
CREATE UNIQUE INDEX idx_signature_unique ON signature_receipts (announcement_id, user_id);

-- 全文搜尋
CREATE INDEX idx_announcements_search ON announcements USING gin (to_tsvector('simple', title || ' ' || content));
```

---

## 3. 標籤 OR/AND/Nested/NOT Query 具體實作

> 這是整個系統的核心。PRD §4.2.5 列出 4 種篩選模式,本節給出 PostgreSQL 具體 SQL 跟查詢策略。

### 3.1 篩選語意對照表

| PRD 場景 | 篩選語意 | SQL 結構 |
|----------|----------|----------|
| §4.2.5.1 基本 OR | 公告 ⊇ {[模擬考] OR [升學]} | `EXISTS (... OR ...)` |
| §4.2.5.2 基本 AND | 公告 ⊇ {[高二] AND [自然組]} | `EXISTS (... AND ...)` |
| §4.2.5.3 巢狀 | 公告 ⊇ {([模擬考] OR [升學]) AND [高三]} | `(group1 OR group2) AND group3` |
| §4.2.5.4 NOT | 公告 ⊇ {[高三] AND NOT [模擬考]} | `EXISTS(高三) AND NOT EXISTS(模擬考)` |

### 3.2 篩選條件的 JSON 結構 (前端送後端的格式)

```typescript
// 前端 → 後端的篩選條件 payload
type FilterCondition = {
  // 葉節點:單一標籤
  tagId: string;
  exclude: boolean;            // true = NOT 條件
} | {
  // 群組節點:巢狀
  operator: 'AND' | 'OR';
  conditions: FilterCondition[];
};

// MVP 簡化:只支援「group 內 OR、group 間 AND」,JSON 結構最簡化為:
interface MvpFilter {
  // 每個 group 內是 OR
  groups: Array<{
    // group 內每個 tag 可設 exclude
    tagIds: string[];
    excludeTagIds: string[];
  }>;
  // group 之間是 AND
}

// 範例:([模擬考] OR [升學]) AND [高三] AND NOT [模擬考]
// 對應:
// groups: [
//   { tagIds: ['模擬考', '升學'], excludeTagIds: [] },        // group 1: OR
//   { tagIds: ['高三'], excludeTagIds: [] },                  // group 2: AND
//   { tagIds: [], excludeTagIds: ['模擬考'] }                 // group 3: AND NOT
// ]
```

### 3.3 核心 SQL:動態組合 EXISTS 子句

```sql
-- 輸入:N 個 groups,每個 group 有 includeTagIds + excludeTagIds
-- 輸出:符合條件的公告 (含分頁 + 排序 + 標籤過濾受眾)

WITH include_match AS (
  -- 每個 group 檢查「公告是否具備 group 任一 include tag」
  SELECT
    at.announcement_id,
    g.group_index
  FROM announcement_tags at
  JOIN UNNEST($1::uuid[], $2::int[]) AS g(tag_id, group_index)
    ON at.tag_id = g.tag_id
  GROUP BY at.announcement_id, g.group_index
),
exclude_match AS (
  -- 排除掉「公告具備任一 exclude tag」的 group
  SELECT
    at.announcement_id,
    g.group_index
  FROM announcement_tags at
  JOIN UNNEST($3::uuid[], $4::int[]) AS g(tag_id, group_index)
    ON at.tag_id = g.tag_id
),
-- 找出滿足「所有 group 都有 include_match 且沒有 exclude_match」的公告
matched_announcements AS (
  SELECT announcement_id
  FROM include_match
  WHERE announcement_id NOT IN (SELECT announcement_id FROM exclude_match)
  GROUP BY announcement_id
  HAVING COUNT(DISTINCT group_index) = $5  -- $5 = groups 數量
)
SELECT
  a.id, a.title, a.content, a.publisher_id, a.publisher_dept,
  a.require_signature, a.signature_deadline, a.publish_at,
  a.created_at, a.updated_at,
  -- 同時撈出這則公告的所有 tag (前端顯示 chip)
  COALESCE(
    (SELECT json_agg(json_build_object('id', t.id, 'name', t.name, 'type', t.type, 'color', t.color))
     FROM announcement_tags at JOIN tags t ON t.id = at.tag_id
     WHERE at.announcement_id = a.id), '[]'::json
  ) AS tags
FROM announcements a
JOIN matched_announcements ma ON ma.announcement_id = a.id
WHERE a.deleted_at IS NULL
  AND a.status = 'published'
  -- 依使用者身分過濾 (受眾):
  -- 學生只看 [自己年級] OR [自己班級] OR [訂閱標籤] OR [公開]
  AND (
    a.visibility = 'public'
    OR EXISTS (
      SELECT 1 FROM announcement_tags at
      WHERE at.announcement_id = a.id
        AND at.tag_id = ANY($6::uuid[])  -- $6 = 該使用者的可見 tag id 陣列
    )
  )
ORDER BY a.publish_at DESC
LIMIT $7 OFFSET $8;  -- 分頁
```

### 3.4 參數綁定 (Node.js / Drizzle 端)

```typescript
// 給 engineering-lead 的型別提示
interface FilterQueryParams {
  // groups 攤平:每個 group 的 (tag_id, group_index) 配對
  includeTuples: Array<[tagId: string, groupIndex: number]>;
  excludeTuples: Array<[tagId: string, groupIndex: number]>;
  groupCount: number;
  userVisibleTagIds: string[];   // 該使用者的可見 tag (含年級/班級/角色/訂閱)
  limit: number;                 // 預設 20
  offset: number;                // 預設 0
}

// Drizzle 用 $queryRaw 跑上方 SQL,參數化查詢防 SQL injection
```

### 3.5 效能分析

- **公告 ≤ 10,000 則、標籤 ≤ 100 個** : 上述 query 在 Neon free tier (< 100ms) 通過。索引命中 (`idx_announcement_tags_tag_id`、`idx_announcements_publish_at`) 確保即使 N 翻 10 倍仍 < 500ms。
- **JOIN 數** : `announcement_tags` 是 bridge table,JOIN 開銷可控;UNNEST 把陣列展開成虛擬表,PostgreSQL planner 會合併到主查詢。
- **冷查詢風險** : 篩選條件組合多時,query plan 難以 cache。**解法** : 用 `pg_stat_statements` 觀察慢查詢,必要時加 materialized view 預計算「熱門篩選」(v2 議題)。
- **client-side 套用** : 標籤篩選 < 0.5 秒 (PRD §5.1) 必須靠 server round-trip,client-side 套用需要把全部公告先載入 (200 公告 × 5KB = 1MB,MVP 規模可接受但浪費流量);**採 server-side 為主、client-side caching 為輔**。

### 3.6 實體關係圖 (Mermaid)

```mermaid
erDiagram
    Department ||--o{ User : "歸屬"
    User ||--o{ Announcement : "發布"
    User ||--o{ SavedFilter : "儲存"
    User ||--o{ ReadReceipt : "已讀"
    User ||--o{ SignatureReceipt : "已簽"
    User ||--o{ AuditLog : "操作者"
    Announcement ||--o{ AnnouncementTag : "掛載"
    Tag ||--o{ AnnouncementTag : "被掛載"
    Announcement ||--o{ AnnouncementAttachment : "包含"
    Attachment ||--o{ AnnouncementAttachment : "被包含"
    Announcement ||--o{ ReadReceipt : "被讀"
    Announcement ||--o{ SignatureReceipt : "被簽"
    User ||--o{ Attachment : "上傳"
    
    Announcement {
        uuid id PK
        string title
        text content
        uuid publisher_id FK
        string publisher_dept FK
        enum status
        enum visibility
        bool require_signature
        timestamp signature_deadline
        timestamp publish_at
        timestamp expire_at
        timestamp deleted_at
    }
    Tag {
        uuid id PK
        enum type
        string name
        string description
        string color
        uuid created_by FK
        bool is_active
    }
    User {
        uuid id PK
        string email UK
        string password_hash
        string name
        enum role
        string department_code FK
        uuid grade_tag_id FK
        uuid class_tag_id FK
        jsonb role_tag_ids
        jsonb subscription_tag_ids
        bool must_change_password
        bool is_active
    }
    Attachment {
        uuid id PK
        string file_name
        string mime_type
        int size_bytes
        string sha256
        string r2_key
        uuid uploaded_by FK
        enum scan_status
    }
```

---

## 4. REST API 設計

> 風格: REST + JSON、動詞用 HTTP method 表達、路徑複數 (announcements 不是 announcement)、錯誤統一用 HTTP status + JSON body。
> 認證:除了登入 / 健康檢查外,全部需要 Bearer JWT (見 §5)。
> CSRF:瀏覽器 cookie 模式需要 CSRF token;純 Bearer (Authorization header) 模式則不需要。MVP 採 Bearer,CSRF 防護簡化。

### 4.1 認證 / 使用者 (Auth)

| Method | Path | 用途 | 權限 |
|--------|------|------|------|
| POST | /api/auth/login | email + 密碼登入,回傳 JWT | 公開 |
| POST | /api/auth/logout | 註銷 token (寫進黑名單或清 cookie) | 全部已登入 |
| POST | /api/auth/forgot-password | 忘記密碼,寄 email 重設連結 | 公開 |
| POST | /api/auth/reset-password | 用重設連結內 token 設定新密碼 | 公開 (持有 token) |
| POST | /api/auth/change-password | 已登入使用者改密碼 (含首次登入強制變更) | 全部已登入 |
| GET | /api/auth/me | 取得目前登入者資料 (含 role、department、可見 tag) | 全部已登入 |
| POST | /api/auth/push-subscribe | 訂閱 Web Push (VAPID) | 全部已登入 |
| DELETE | /api/auth/push-subscribe | 取消訂閱 Web Push | 全部已登入 |

### 4.2 公告 (Announcements) - 核心

| Method | Path | 用途 | 權限 |
|--------|------|------|------|
| GET | /api/announcements | 公告列表 (含篩選 + 分頁 + 排序),query 參數見 §4.2.1 | 全部已登入 |
| GET | /api/announcements/:id | 公告詳情 (含 tags + attachments + 自己的已讀 / 已簽狀態) | 全部已登入 |
| POST | /api/announcements | 建立公告 (含 tagIds + attachmentIds) | 處室承辦以上 (dept_officer / sysadmin) |
| PATCH | /api/announcements/:id | 更新公告 (改標題 / 內文 / 標籤 / 附件 / 簽收設定) | 原發布者 + sysadmin |
| DELETE | /api/announcements/:id | 軟刪除 (status → archived) | 原發布者 + sysadmin |
| POST | /api/announcements/:id/read | 標記已讀 (進入詳情頁時前端自動呼叫,去重) | 全部已登入 |
| POST | /api/announcements/:id/sign | 簽收 (requireSignature=true 才生效) | 全部已登入 |
| GET | /api/announcements/:id/receipts | 取得此公告的已讀 / 已簽名單 (含匯出 CSV 選項) | 原發布者 + sysadmin |

### 4.2.1 列表 query 參數

```
GET /api/announcements?groups=<base64 JSON>&page=1&limit=20&search=模擬考&sort=-publish_at

groups = base64([{tagIds:['uuid1','uuid2'], excludeTagIds:[]}, ...])  // §3.2 結構
page = 1 (預設) / limit = 20 (預設,可選 50, 100)
search = 全文搜尋關鍵字 (對 title + content 做 tsquery)
sort = -publish_at (新到舊) | publish_at (舊到新) | -created_at

回應:
{
  "data": [AnnouncementWithTags[]],
  "pagination": { "page": 1, "limit": 20, "total": 142, "hasMore": true }
}
```

### 4.3 標籤 (Tags)

| Method | Path | 用途 | 權限 |
|--------|------|------|------|
| GET | /api/tags | 取得所有啟用中的標籤 (依 type 分群),含每個 tag 的「被 N 則公告引用」計數 | 全部已登入 |
| GET | /api/tags/:id | 單一標籤詳情 | 全部已登入 |
| POST | /api/tags | 新增標籤 (選 type + 填 name + description + color) | 系統管理員 |
| PATCH | /api/tags/:id | 編輯標籤 (改 name / description / color) | 系統管理員 |
| DELETE | /api/tags/:id | 刪除標籤 (若有公告引用改為停用,前端顯示警告) | 系統管理員 |
| POST | /api/tags/:id/activate | 啟用 / 停用切換 (isActive toggle) | 系統管理員 |

### 4.4 附件 (Attachments)

| Method | Path | 用途 | 權限 |
|--------|------|------|------|
| POST | /api/attachments/upload | 階段 1 上傳檔案到 R2,回傳 attachmentId 跟臨時 URL (見 §6) | 處室承辦以上 |
| GET | /api/attachments/:id | 取得附件 metadata (含 scanStatus) | 全部已登入 (依公告受眾) |
| GET | /api/attachments/:id/download | 下載附件 (proxy 過後端,做權限檢查 + 寫稽核) | 公告受眾內 |
| DELETE | /api/attachments/:id | 刪除附件 (軟刪,30 天後由系統清) | 上傳者 + sysadmin |
| GET | /api/attachments/:id/scan-status | 查詢附件掃毒狀態 (前端 polling 用) | 上傳者 + sysadmin |

### 4.5 處室 / 使用者 / 角色 (Admin)

| Method | Path | 用途 | 權限 |
|--------|------|------|------|
| GET | /api/departments | 取得所有處室 (前端側邊欄用) | 全部已登入 |
| GET | /api/admin/users | 使用者列表 (含篩選 role / department / 啟用狀態) | 系統管理員 |
| POST | /api/admin/users | 新增使用者 (含密碼初始化、寄 email 通知) | 系統管理員 |
| PATCH | /api/admin/users/:id | 編輯使用者 (改 role / department / 標籤) | 系統管理員 |
| DELETE | /api/admin/users/:id | 停用使用者 (isActive=false,保留稽核) | 系統管理員 |
| POST | /api/admin/users/:id/reset-password | 系統管理員強制重設密碼 | 系統管理員 |
| GET | /api/admin/audit-logs | 稽核紀錄 (含篩選 actor / action / 時間範圍) | 系統管理員 |

### 4.6 個人化 (Me)

| Method | Path | 用途 | 權限 |
|--------|------|------|------|
| GET | /api/me/subscriptions | 取得我訂閱的標籤 | 全部已登入 |
| PUT | /api/me/subscriptions | 整批更新我的訂閱標籤 (前端複選後一次送) | 全部已登入 |
| GET | /api/me/attachments | 我下載過的附件列表 (含原始公告連結) | 全部已登入 |
| GET | /api/me/signatures | 我的簽收紀錄 (含公告標題、簽收時間) | 全部已登入 |
| GET | /api/me/filters | 我的常用篩選 | 全部已登入 |
| POST | /api/me/filters | 新增常用篩選 (含 name + queryJson) | 全部已登入 |
| PATCH | /api/me/filters/:id | 編輯常用篩選 | 全部已登入 |
| DELETE | /api/me/filters/:id | 刪除常用篩選 | 全部已登入 |

### 4.7 統一錯誤回應格式

```json
{
  "error": {
    "code": "ANNOUNCEMENT_NOT_FOUND",
    "message": "公告不存在或已被刪除",
    "details": {}  // 選填,例如 Zod 驗證錯誤的欄位
  }
}
```

HTTP status code 對照:
- 400 = 請求格式錯誤 (Zod validation fail)
- 401 = 未登入 / token 過期
- 403 = 權限不足
- 404 = 資源不存在
- 409 = 衝突 (例:email 已存在)
- 413 = 附件太大
- 422 = 業務邏輯錯誤 (例:公告至少要 1 個標籤)
- 429 = Rate limit
- 500 = 伺服器錯誤

---

## 5. Auth 設計

### 5.1 認證流程總覽

```
使用者登入
  ↓ POST /api/auth/login (email + password)
後端驗證 (bcrypt.compare)
  ↓ 成功
後端簽發 JWT (HS256, payload 見 §5.2)
  ↓ 回傳 { accessToken, refreshToken, user }
前端存 accessToken 到記憶體 (或 httpOnly cookie),refreshToken 存 httpOnly cookie
  ↓ 後續 API 請求
前端加 Authorization: Bearer <accessToken>
  ↓ 後端 middleware 驗證 (jose 套件)
業務邏輯執行
```

### 5.2 JWT Payload 設計

```typescript
interface JwtPayload {
  sub: string;                 // user.id
  email: string;
  role: 'sysadmin' | 'dept_officer' | 'teacher' | 'parent' | 'student' | 'guest';
  departmentCode: string | null;
  // 受眾標籤 (用於公告受眾過濾) - 從 user 計算出來 cache 在 token
  visibleTagIds: string[];     // [grade_tag_id, class_tag_id, ...role_tag_ids, ...subscription_tag_ids]
  iat: number;                 // issued at
  exp: number;                 // accessToken: 8 小時 (PRD §4.3.3) / refreshToken: 7 天
  jti: string;                 // unique id,黑名單用
}
```

### 5.3 密碼雜湊策略

- **演算法** : bcrypt (cost = 12,符合 PRD §5.2「salt 至少 16 byte」)
- **套件** : `bcryptjs` (pure JS,跟 Edge runtime 兼容) 或 `bcrypt` (原生,效能較好但需 native build)
- **選擇** : Node.js runtime (寫入 API) 用 `bcrypt`,Edge runtime (唯讀 API 不處理密碼) 不需要
- **範例** (給 engineering-lead 參考):
  ```typescript
  // 註冊 / 改密碼
  const passwordHash = await bcrypt.hash(plainPassword, 12);
  // 登入驗證
  const isValid = await bcrypt.compare(plainPassword, passwordHash);
  ```
- **首次登入強制變更** : 註冊時設 `mustChangePassword = true`,前端 middleware 看到就強制導到 `/change-password`,變更後設為 false
- **密碼強度** : 至少 8 字元 + 英文數字混用 (前端 Zod 驗證);不強制特殊字元 (NIST 800-63B 建議)
- **Rate limiting** : `/api/auth/login` 連續失敗 5 次鎖定 15 分鐘 (用 Vercel Edge Config 或 Upstash Redis)

### 5.4 Refresh Token 機制

- **accessToken 過期** (8 小時) : 前端用 refreshToken 換新 accessToken,使用者無感
- **refreshToken 過期** (7 天) : 重新登入
- **撤銷** : 提供 `/api/auth/logout` 把 jti 加入 Redis 黑名單,該 token 立即失效
- **rotation** : 每次 refresh 換新的 refreshToken,舊的加入黑名單 (防 token 盜用)

### 5.5 RBAC 權限檢查 (Middleware)

```typescript
// 給 engineering-lead 的介面,實作在 middleware.ts
interface AuthContext {
  user: User;
  jwtPayload: JwtPayload;
}

// 權限裝飾器風格
function requireRole(...allowed: User['role'][]) {
  return (ctx: AuthContext) => {
    if (!allowed.includes(ctx.user.role)) {
      throw new ForbiddenError(`需要 ${allowed.join(' 或 ')} 角色`);
    }
  };
}

// 處室歸屬檢查 (dept_officer 只能管自己的處室)
function requireSameDepartment(ctx: AuthContext, targetDeptCode: string) {
  if (ctx.user.role === 'dept_officer' && ctx.user.departmentCode !== targetDeptCode) {
    throw new ForbiddenError('只能管理自己處室的公告');
  }
}
```

### 5.6 跨處室閱讀權 (v1 簡化版)

- 預設:處室承辦只能讀 [自己處室] + [public] 公告
- 擴充:在 `User` 加 `crossDepartmentReadCodes: string[]` (JSONB),系統管理員可設定「教務主任可讀 [學務處]」
- v2 再做後台管理介面 (v1 暫用 SQL 直接改)

### 5.7 個資法遵循

- 刪除使用者:`DELETE /api/admin/users/:id` 採軟刪 (isActive=false),保留 1 年後由排程清空個資 (姓名、email 改為 `[已刪除使用者]`),但保留匿名化的已讀 / 已簽紀錄 (PRD §5.2)
- 資料可攜:`GET /api/me/export` 打包我發過的公告 + 簽收紀錄 JSON (個人資料保護法 §8 遵循)

---

## 6. 附件上傳流程

> 對標 PRD §4.4.3「兩階段上傳」(Cloud School 設計)。

### 6.1 流程圖

```
使用者選檔
  ↓ 前端檢查 size (≤ 50MB) + mime (白名單)
POST /api/attachments/upload (multipart/form-data)
  ↓ 後端檢查 auth + role (處室承辦以上)
  ↓ 後端產生 R2 presigned PUT URL (5 分鐘有效)
  ↓ 後端寫入 attachments table (status='pending', scanStatus='pending')
  ↓ 回傳 { attachmentId, uploadUrl, expiresAt }
前端 PUT 檔案到 R2 uploadUrl
  ↓ R2 收到後前端通知後端
POST /api/attachments/:id/finalize (告訴後端上傳完成)
  ↓ 後端觸發背景掃毒 (Cloudmersive API)
  ↓ 掃毒完成後更新 scanStatus (clean / infected)
  ↓ scanStatus='clean' 之前,附件「不可被綁定到公告」(前端 disabled)

(之後使用者到「新增公告」頁)
  ↓ 從「已上傳的附件」選擇 (GET /api/attachments?uploadedBy=me&notBoundTo=...)
POST /api/announcements (附帶 attachmentIds: [...])
  ↓ 後端寫入 announcement_attachments
  ↓ 公告發布後,附件可下載
```

### 6.2 兩階段的好處

- **附件可重用** : 同一個 PDF 報名表可在多則公告使用,不必重傳
- **預先上傳** : 小美可以「先上傳所有 PDF,明天再寫公告內容」
- **節省頻寬** : 上傳失敗可重試同一個 R2 URL,不需前端重傳整個檔案
- **掃毒隔離** : 附件不乾淨不污染公告,管理者可事後刪除

### 6.3 附件下載 (proxy 模式)

```
使用者點公告附件
  ↓ 前端 GET /api/attachments/:id/download
後端檢查:
  1. JWT 認證
  2. 該使用者是否符合公告受眾 (透過 announcement_tags + user.visibleTagIds)
  3. 公告未被軟刪除
  ↓ 通過
後端從 R2 GET 該檔案 (server-to-server,免費)
  ↓ 同時寫入 audit_logs (action='ATTACHMENT_DOWNLOAD')
  ↓ 回傳檔案串流給前端 (Content-Disposition: attachment)
```

- **為何不直接 R2 公開 URL** : 為了 (a) 存取控制、(b) 稽核、(c) v2-03 預留「時效 token」機制
- **為何不直接 R2 presigned URL** : 雖然 R2 提供 presigned URL (1 小時有效),但這等於把「存取控制」外包給 R2,稽核跟受眾檢查全斷;**採後端 proxy 統一控管**

### 6.4 附件大小 / 格式限制 (對應 PRD §4.4.1-2)

| 限制 | 值 | 實作位置 |
|------|------|----------|
| 單檔 size | 50 MB | 前端 input accept + size 檢查;後端 middleware 強制 |
| 單則公告附件總和 | 200 MB | 後端 POST /api/announcements 時 sum size 檢查 |
| 支援格式 | 見 PRD §4.4.1 16 種 | 前端 input accept + 後端 mime 白名單 |
| 排除格式 | exe, bat, sh, xlsm, docm (巨集) | 後端 mime 黑名單 |

### 6.5 附件掃毒整合

- **掃毒 API** : Cloudmersive Virus Scan API (每月 500 次免費,超量 $0.15/100 次)
- **時機** : 附件 finalize 後背景觸發,不等掃毒完成就回應前端 (status='pending')
- **前端體驗** : 上傳後顯示「掃毒中...」,前端輪詢 `/api/attachments/:id/scan-status`,完成後解除 disabled
- **掃毒失敗** : scanStatus='infected' → 附件從「可選用」清單移除 + email 通知上傳者 + 寫 audit log
- **v2 改本地 ClamAV** : 量大後自建 ClamAV daemon (省錢、掃描更嚴)

### 6.6 附件生命週期 (對應 PRD §4.4.7)

| 狀態 | 附件可下載 | 保留期限 |
|------|----------|----------|
| 公告 published | 是 | 永久 |
| 公告 archived (軟刪) | 是 (稽核用) | 30 天 |
| 公告永久刪除 (sysadmin 操作) | 否 | 連同附件一併刪 (R2 delete + DB soft delete) |
| 附件獨立軟刪 (上傳者刪) | 否 | 30 天 (R2 lifecycle rule) |

---

## 7. Vercel 環境變數清單

> 環境分層:Production / Preview / Development,每層可獨立設定。
> **敏感變數** (DB 密碼、API key) 一律標 `Sensitive`,Vercel 加密儲存。

### 7.1 必要環境變數 (Production 必設)

| 變數名 | 用途 | 範例值 | Sensitive |
|--------|------|--------|-----------|
| DATABASE_URL | Neon PostgreSQL 連線字串 | `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/school_bulletin?sslmode=require` | ✓ |
| JWT_SECRET | JWT 簽章密鑰 (至少 32 字元) | 隨機產生,例:`openssl rand -base64 32` | ✓ |
| JWT_REFRESH_SECRET | Refresh token 簽章密鑰 | 同上,跟 access 分開 | ✓ |
| R2_ACCOUNT_ID | Cloudflare R2 帳號 ID | `a1b2c3d4e5f6...` | ✗ |
| R2_ACCESS_KEY_ID | R2 API token access key | R2 控制台產生 | ✓ |
| R2_SECRET_ACCESS_KEY | R2 API token secret | R2 控制台產生 | ✓ |
| R2_BUCKET_NAME | R2 bucket 名 | `school-bulletin-prod` | ✗ |
| R2_PUBLIC_URL | R2 公開 CDN URL (圖片預覽用) | `https://pub-xxx.r2.dev` | ✗ |
| RESEND_API_KEY | Resend email 寄送 | `re_xxx` | ✓ |
| EMAIL_FROM | 寄件者地址 | `noreply@bulletin.school.edu.tw` | ✗ |
| VAPID_PUBLIC_KEY | Web Push 公鑰 | 產生自 `web-push generate-vapid-keys` | ✗ |
| VAPID_PRIVATE_KEY | Web Push 私鑰 | 同上 | ✓ |
| VAPID_SUBJECT | Web Push 寄件者 | `mailto:admin@school.edu.tw` | ✗ |
| CLOUDMERSIVE_API_KEY | 附件掃毒 API | `xxx` | ✓ |
| APP_URL | 本應用正式網址 | `https://bulletin.school.edu.tw` | ✗ |
| NODE_ENV | Node 環境 | `production` | ✗ |

### 7.2 選用環境變數 (視需要開啟)

| 變數名 | 用途 | 何時需要 |
|--------|------|----------|
| SENTRY_DSN | Sentry 錯誤追蹤 | 想接 Sentry 才設 |
| UPSTASH_REDIS_URL | Upstash Redis 連線 (rate limit、token 黑名單) | 上線後需要做 rate limit |
| LOG_LEVEL | 日誌等級 (debug/info/warn/error) | debug 模式 |
| CRON_SECRET | Vercel Cron 呼叫 API 的 secret | 設定 cron job 後必加 |

### 7.3 部署前 checklist (給 DevOps)

- [ ] Neon project 建立,主分支 `main` database
- [ ] Cloudflare R2 bucket 建立,設定 CORS 允許 `https://bulletin.school.edu.tw`
- [ ] Resend domain 驗證 (DNS SPF + DKIM)
- [ ] VAPID key pair 產生並填入
- [ ] Cloudmersive 帳號建立,API key 取得
- [ ] Sentry project 建立 (選用)
- [ ] Vercel project import,綁定 GitHub repo
- [ ] 環境變數逐項填入 (Production / Preview / Development)
- [ ] 第一個 commit push,確認 Preview deployment 成功
- [ ] 跑 `pnpm db:push` 初始化 schema
- [ ] 跑 `pnpm db:seed` 建立 6 個處室帳號
- [ ] 設定 custom domain + DNS
- [ ] 設定 Vercel Cron jobs (見 §8.4)

### 7.4 Vercel Cron Jobs 設定 (vercel.json)

```json
{
  "crons": [
    { "path": "/api/cron/cleanup-soft-deleted", "schedule": "0 2 * * *" },
    { "path": "/api/cron/verify-backup", "schedule": "0 3 * * *" },
    { "path": "/api/cron/purge-expired-audit", "schedule": "0 4 1 * *" }
  ]
}
```

用途:
- `cleanup-soft-deleted` : 每天 02:00 清理 30 天前軟刪除的附件 (R2 + DB)
- `verify-backup` : 每天 03:00 驗證 Neon auto backup 成功
- `purge-expired-audit` : 每月 1 號 04:00 清除超過 1 年的稽核紀錄 (個資法遵循)

---

## 8. 給 engineering-lead 的接力清單

> 本節是「照著蓋就會對」的施工指南,照順序執行就能在 1 小時內進入第一個 commit。

### 8.1 套件清單 (pnpm)

**核心框架**:
- `next@15` + `react@19` + `typescript@5` + `@types/node` + `@types/react`
- `tailwindcss` + `autoprefixer` + `postcss`
- `shadcn-ui` (用 CLI 初始化,挑需要的元件: button / dialog / form / table / tabs / select / chip / card / toast)

**後端 / 資料庫**:
- `drizzle-orm` + `drizzle-kit` (migrations)
- `@neondatabase/serverless` (Neon 連線)
- `bcrypt` + `@types/bcrypt`
- `jose` (JWT 簽章 / 驗證,Edge runtime 兼容)
- `zod` (request validation)

**工具 / 整合**:
- `react-hook-form` + `@hookform/resolvers` (前端表單)
- `@aws-sdk/client-s3` (R2,跟 S3 同一個 SDK)
- `web-push` + `@types/web-push` (Web Push 推播)
- `resend` (email)
- `react-day-picker` (日期選擇器,簽收截止日用)
- `date-fns` (時間處理,時區 Asia/Taipei)
- `lucide-react` (icon)

**測試 / 監控**:
- `vitest` + `@vitest/ui` (unit test)
- `@playwright/test` (E2E)
- `@sentry/nextjs` (選用,錯誤追蹤)

### 8.2 資料夾結構

```
school-bulletin/
├── app/                          # Next.js App Router
│   ├── (public)/                 # 未登入可見 (公開公告)
│   │   └── announcements/[id]/page.tsx
│   ├── (auth)/                   # 登入 / 註冊
│   │   ├── login/page.tsx
│   │   └── change-password/page.tsx
│   ├── (protected)/              # 已登入才可見
│   │   ├── announcements/
│   │   │   ├── list/page.tsx
│   │   │   ├── new/page.tsx
│   │   │   └── [id]/
│   │   │       ├── page.tsx
│   │   │       └── edit/page.tsx
│   │   ├── admin/
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── announcements/page.tsx
│   │   │   ├── users/page.tsx
│   │   │   ├── tags/page.tsx
│   │   │   └── audit/page.tsx
│   │   └── me/
│   │       ├── subscriptions/page.tsx
│   │       ├── attachments/page.tsx
│   │       ├── signatures/page.tsx
│   │       └── filters/page.tsx
│   ├── api/                      # Route Handlers
│   │   ├── auth/
│   │   ├── announcements/
│   │   ├── tags/
│   │   ├── attachments/
│   │   ├── admin/
│   │   ├── me/
│   │   └── cron/
│   ├── layout.tsx
│   └── globals.css
├── components/                   # React 元件 (shadcn-ui 客製化)
│   ├── ui/                       # shadcn-ui 自動產生
│   ├── announcement/
│   │   ├── AnnouncementCard.tsx
│   │   ├── TagChip.tsx
│   │   └── TagFilter.tsx          # 核心:標籤 OR/AND 篩選器
│   ├── attachment/
│   │   ├── AttachmentUploader.tsx
│   │   └── AttachmentList.tsx
│   └── layout/
│       ├── Sidebar.tsx
│       └── TopBar.tsx
├── lib/
│   ├── db/
│   │   ├── schema.ts              # Drizzle schema (對應 §2 interface)
│   │   ├── client.ts              # Neon 連線
│   │   ├── migrations/            # drizzle-kit 產生
│   │   └── seed.ts                # 6 個處室帳號
│   ├── auth/
│   │   ├── jwt.ts                 # sign / verify
│   │   ├── password.ts            # bcrypt hash / compare
│   │   └── middleware.ts          # 權限檢查
│   ├── api/
│   │   ├── announcements.ts       # 含 §3.3 SQL query
│   │   ├── tags.ts
│   │   └── attachments.ts
│   ├── r2.ts                      # R2 client (S3 SDK)
│   ├── email.ts                   # Resend wrapper
│   ├── push.ts                    # Web Push
│   └── validation/                # Zod schemas
├── public/
├── tests/
│   ├── unit/                      # Vitest
│   └── e2e/                       # Playwright
├── drizzle.config.ts
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── vercel.json
├── package.json
└── README.md
```

### 8.3 開發順序 (1 小時上手 → 1 週交付 MVP 雛形)

**第 1 小時 : 專案初始化**
1. `pnpm create next-app@latest school-bulletin --typescript --tailwind --app`
2. `pnpm add` 上面 §8.1 全部套件
3. `pnpm dlx shadcn@latest init`,挑 8 個常用元件
4. 設定 `tsconfig.json` 路徑 alias (`@/*`)
5. 建 `.env.local` (DATABASE_URL + JWT_SECRET + 其他 §7.1)
6. 設定 `drizzle.config.ts` + `lib/db/schema.ts` (從 §2 interface 翻成 Drizzle)
7. `pnpm db:push` 跑 schema
8. 寫 `lib/db/seed.ts` + `pnpm db:seed` 建立 6 個處室帳號
9. 開第一個 commit: `chore: scaffold project`

**第 1 天 : Auth + 公告 CRUD 基本**
1. 寫 `lib/auth/jwt.ts` + `lib/auth/password.ts`
2. 寫 `/api/auth/login` + `/api/auth/me`
3. 寫 `app/(auth)/login/page.tsx` (簡單 form)
4. 寫 `middleware.ts` (檢查 JWT、redirect)
5. 寫 `/api/announcements` (GET list、POST create)
6. 寫 `components/announcement/AnnouncementCard.tsx`
7. 寫 `app/(protected)/announcements/list/page.tsx`
8. 開 commit: `feat: auth + basic announcement CRUD`

**第 2-3 天 : 標籤系統 (核心)**
1. 寫 `/api/tags` 全部 CRUD
2. 寫 `components/announcement/TagFilter.tsx` (核心 UI,先做基本 OR + AND,MVP 簡化版)
3. 改 `/api/announcements` 支援 §3.3 SQL filter
4. 寫 `app/(protected)/admin/tags/page.tsx` (系統管理員後台)
5. E2E test:佐藤同學的 US-2.1 / US-2.2 / US-2.3
6. 開 commit: `feat: tag system with OR/AND filter`

**第 4-5 天 : 附件上傳 + 已讀 / 已簽**
1. 寫 `lib/r2.ts` (presigned URL generation)
2. 寫 `/api/attachments/upload` + `/api/attachments/:id/finalize`
3. 寫 `components/attachment/AttachmentUploader.tsx`
4. 寫 `/api/attachments/:id/download` (proxy 模式)
5. 串接 Cloudmersive 掃毒
6. 寫 `/api/announcements/:id/read` + `/api/announcements/:id/sign`
7. 寫 `/api/announcements/:id/receipts` (含 CSV 匯出)
8. 開 commit: `feat: attachments + read/sign tracking`

**第 6 天 : 個人化 + 訂閱**
1. 寫 `/api/me/subscriptions` + 對應 UI
2. 寫 `/api/me/filters` (常用篩選)
3. 寫 `/api/me/attachments` + `/api/me/signatures`
4. 開 commit: `feat: personal area`

**第 7 天 : 推播 + Email + E2E test + deploy**
1. 寫 Web Push 訂閱 / 寄送
2. 寫 Email 通知 (新公告、簽收提醒、忘記密碼)
3. Playwright E2E:3 個 Persona 各跑 1 個 happy path
4. Vercel 部署 Preview,跑完所有驗收
5. 開 commit: `feat: notifications + E2E tests`

### 8.4 第一個 commit 前必跑

```bash
pnpm install
pnpm typecheck       # tsc --noEmit
pnpm lint            # eslint
pnpm test            # vitest
pnpm build           # next build (production build 必須成功)
```

### 8.5 給 engineering-lead 的關鍵提醒

1. **永遠不要寫 raw SQL string concatenation** : 全部用 Drizzle 的 `eq()` `and()` `or()` `inArray()` 參數化查詢,或 `sql` template literal 帶參數 (見 §3.3 `$1` `$2` 寫法)
2. **API 全部過 Zod validation** : 每個 request body / query params 都用 Zod schema 驗證,失敗統一 400 + 詳細錯誤
3. **所有寫入操作寫 audit log** : 任何 POST / PATCH / DELETE 都寫 `audit_logs` table (PRD §5.2)
4. **前端不存 JWT 在 localStorage** : 用 httpOnly cookie 或記憶體,防 XSS 偷 token
5. **附件下載走後端 proxy** : 不要在前端直接 R2 公開 URL,見 §6.3
6. **時區統一 Asia/Taipei** : Drizzle 用 `timestamp with time zone`,前端用 `date-fns-tz` 顯示
7. **Vercel 部署前設 `output: 'standalone'`** : 加速 cold start
8. **不要在 Edge runtime 跑 bcrypt** : Edge 沒有原生 bcrypt,登入 API 改用 `runtime = 'nodejs'`

### 8.6 上線前必跑 (給 DevOps 接力)

- [ ] 6 個處室帳號 seed 完成 + 首次登入強制變更密碼驗證
- [ ] 50 MB 附件上傳成功 + 掃毒 clean + 下載成功
- [ ] 標籤 OR/AND 篩選跑 PRD §4.2.5 四種情境全綠
- [ ] 已讀 / 已簽雙軌制驗證 (高雄校園通風格)
- [ ] 推播訂閱 + 發送 + 點擊通知 (PWA 模式)
- [ ] Webhook / Vercel Cron 跑 cleanup / backup / audit purge
- [ ] Sentry 收到前端錯誤 (選用)
- [ ] Lighthouse 分數:Performance ≥ 80、Accessibility ≥ 90

### 8.7 架構決策待釐清 (請 default orchestrator 轉達使用者裁決)

> 這幾個我選了合理預設值,但使用者可能想改,列出請裁決:

1. **業主是否要求「校內機房自建」** ? 若是,MVP 架構要改 Docker Compose + 本地 PostgreSQL + 自建 R2 (MinIO)。預設採 Vercel 雲端託管 (開發快、便宜)。
2. **是否需要「訪客 (未登入) 可看公開公告」** ? 若是,前端要有「公開公告」路由,SEO 要做。預設 MVP 不開 (全校人員都有帳號,簡化)。
3. **附件掃毒用 Cloudmersive (託管) 還是 ClamAV (自建)** ? Cloudmersive 每月 500 次免費,超過收費;ClamAV 免費但要自建 daemon。預設 Cloudmersive,量大後改 ClamAV。
4. **推播機制** :MVP 用 Web Push (VAPID),但 iOS Safari 對 Web Push 支援不佳;若家長主要用 iPhone,可能要提早做 FCM/APNs。預設 MVP 先 Web Push,v3 再原生 APP。
5. **學校 SSO 整合時程** :若業主希望「跟校務系統單一登入」(避免重複密碼),MVP 就要預留 OAuth2 介接。預設 MVP 用本地帳號,SSO 留 v2。
