---
name: school-bulletin-system
description: "學校公告系統建置與維運 skill。當用戶提到「建立學校公告系統」「校園公告」「處室各自發布公告」「公告標籤篩選」「家長師生分流看公告」「學校網站」時啟用。核心功能：Next.js 15 + Supabase (PostgreSQL) 公告系統，含 RBAC 權限矩陣（6 角色 × 4 權限）、標籤 OR/AND 篩選、簽收回條。部署於 Vercel。"
version: 1.1.0
author: Hermes Agent (metacognitive-learner)
platforms: [linux]
metadata:
  hermes:
    tags: [school, bulletin, announcement, vercel, nextjs, supabase, rbac, taiwan]
    triggers: [學校公告, 公告系統, 校園公告, 處室發布, 標籤篩選, 家長分流]
    user_type: school HR / IT admin (high school)
---

# School Bulletin System — 學校公告系統建置與維運

## 系統概覽

```
URL: https://school-bulletin.vercel.app
原始碼: ~/permanent-projects/school-bulletin/
建置時間: 2026-06-11
架構: Next.js 15 (App Router) + Supabase (PostgreSQL 16) + Vercel
```

**PRD 完成度**: 8/9（M-08 推播通知 v1 不做）

## 技術棧

| 層 | 技術 | 備註 |
|----|------|------|
| 前端框架 | Next.js 15 (App Router) + React 19 | TypeScript 5.7 |
| 樣式 | Tailwind CSS 3.4 | |
| Rich Text 編輯器 | Tiptap 3 | |
| 後端 | Next.js Route Handlers (Node.js runtime) | |
| 資料庫 | Supabase (PostgreSQL 16) | Project ID: `isyttbeketzmepcanaoc` |
| 附件儲存 | Supabase Storage | |
| 認證 | HMAC + bcryptjs（自製，8 小時 session cookie）| |
| 部署 | Vercel | git push → auto deploy |

## 權限矩陣（C 方案 v4，最終定案）

**設計聖經**: `登入後能看到的 >= 未登入`

### 角色與閱讀權限（v4：所有人看全部公告）

| 角色 | username | 閱讀範圍 | 發布/編輯/刪除 |
|------|----------|---------|----------------|
| sysadmin | `principal` | 全部 | ✅ |
| dept_officer | `teaching`, `student`, `general`, `counseling`, `accounting`, `info` | 全部 | ✅ |
| teacher | `teacher_lin` | 全部 | ❌ |
| parent | `parent_chen` | 全部 | ❌ |
| student | `student_wang` | 全部 | ❌ |

> **v4 核心洞察**：在「內部公告」機制建立之前，受眾帳號（teacher/parent/student）不應被 audience 過濾。否則登入 = 看更少 = 登入動機消失。詳見 `references/design-evolution.md`。

### 發布權限（POST/PATCH/DELETE）

**只有 `sysadmin` 和 `dept_officer` 可以發布/編輯/刪除**。其餘角色帳號 POST 公告 → 403。

```
if (me.role !== 'dept_officer' && me.role !== 'sysadmin') {
  return NextResponse.json({ error: '權限不足' }, { status: 403 })
}
```

## 標籤系統

標籤類型（`tags` 表 `type` 欄位）：
- `grade` — 年級標籤
- `class` — 班級標籤
- `department` — 處室標籤
- `activity` — 活動標籤
- `role` — 角色標籤（用於 audience 分流）
- `custom` — 自訂標籤

### 篩選邏輯（OR/AND）

前端支援 `OR` 和 `AND` 邏輯混合篩選。API 接受 base64url 編碼的 filter payload：

```
GET /api/announcements?groups=<base64url({"groups": ["tag1", "tag2"], "op": "or"})>
```

OR: 符合任一標籤即可；AND: 需同時符合所有標籤。

**Idempotent 設計**：`tagIds` 和 `tags` 兩種格式都接受，雙向容錯。

## 簽收回條

`signature_receipts` 表。同一使用者對同一公告 sign → idempotent（再次 sign 回 200 alreadySigned）。

3 個 API：
- `POST /api/signatures/:announcementId` — 簽收
- `GET /api/signatures/:announcementId` — 查詢誰簽了
- `GET /api/signatures` — 查自己的簽收記錄

## 附件上傳

使用 Supabase Storage（不在 Vercel Blob）。

Upload API: `POST /api/attachments/upload`
Download: `GET /api/attachments/:filename`

## 初始化流程

### 1. 安裝依賴

```bash
cd ~/permanent-projects/school-bulletin
npm install
```

### 2. 環境變數

```bash
cp .env.example .env.local
# 編輯 .env.local，填入：
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=eyJxxx  （Service Role key，非 anon key）
# SESSION_SECRET=<隨機 32 字元>
```

### 3. 初始化資料庫

在 Supabase SQL Editor 執行 `supabase/schema.sql`（冪等，可重跑）。

### 4. 種子資料

```bash
npm run seed
# 或觸發 API: GET /api/seed-demo
```

### 5. 開發

```bash
npm run dev
```

## Vercel 部署 SOP

### 部署觸發

```bash
cd ~/permanent-projects/school-bulletin
git add . && git commit -m "fix: ..."
git push origin main
# Vercel 自動偵測 → 觸發 deploy
```

### 環境變數（Vercel Dashboard）

在 Vercel project settings 設定以下 environment variables（Production + Preview + Development）：

| 變數名 | 用途 | 備註 |
|--------|------|------|
| `SUPABASE_URL` | PostgreSQL 連線 | |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin 操作（繞過 RLS） | **不可暴露到 client** |
| `SESSION_SECRET` | HMAC session 簽章 | 隨機 32 字元 |
| `NEXT_PUBLIC_APP_URL` | Production URL | |

### ⚠️ AGENT_API_KEY Mask Bug

`vercel env pull` 會將 `.env` 中的 `AGENT_API_KEY=***` 視為真實值下載，導致應用程式拿到 `***` 作為 API key。

**If** `vercel env pull` 後 `.env.local` 出現 `AGENT_API_KEY=***` 或很短的字串
**Then** 手動編輯 `.env.local`，從 `~/.hermes/.env` 取真實 key 填入（`grep AGENT_API_KEY ~/.hermes/.env`）

### 驗證 Production

```bash
# 1. 確認 deploy 狀態
curl -s https://school-bulletin.vercel.app/api/announcements | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✅ {len(d)} 公告')"

# 2. 登入測試（demo 帳號）
# principal / School@2026 → sysadmin
# teaching / School@2026 → dept_officer
```

## 資料庫 schema 核心表

```
announcements          — 公告主表
tags                  — 標籤（含 type: grade/class/department/activity/role/custom）
user_role_assignments — 使用者 ←→ 角色標籤（用於 audience 命中）
signature_receipts    — 簽收回條
attachments           — 附件（中繼資料）
```

## 維運命令

```bash
# 看即時 logs
vercel logs school-bulletin

# 資料庫直接查（Supabase dashboard 或 psql）
# Project ID: isyttbeketzmepcanaoc

# 重跑 seed（重建 demo 資料）
npm run seed
```

## ⚠️ 實作狀態警告

本 skill **有 SKILL.md 且 scripts/ 目錄已建立**（2026-06-18）。

**實作狀態（2026-06-23 更新）**：
- ✅ `scripts/deploy.sh` — Vercel git push 部署 + polling 等待
- ✅ `scripts/supabase_migrate.sql` — DB schema（從 handoff 複製，174 行）
- ✅ `scripts/school-bulletin-watchdog.sh` — 健康監控（2026-06-21 修復 `/api/health` 404 bug）
- ✅ `scripts/seed.sh` — demo 資料初始化 wrapper（2026-06-23 建立，驗證 exit 0）
- ⬜ `scripts/seed.ts` idempotency bug — tags INSERT 缺 `ON CONFLICT DO NOTHING`，導致 re-run 時 `duplicate key`；屬於專案原始碼 bug，不影響 wrapper 功能

**If** 需要緊急執行 bulletin 系統相關操作
**Then** 使用 `scripts/deploy.sh` 或直接操作 `~/permanent-projects/school-bulletin/` 的原始碼

**If** watchdog log 報告 `HTTP 404 from .../api/health` 但網站本身正常
**Then** 這是 `CHECK_PATH="/api/health"` 設定錯誤，見 `references/watchdog-404-fix-20260621.md`

**If** watchdog 行為異常（log 出現 404 但網站正常）且 `/tmp/school-bulletin-watchdog.sh` 的 mtime 早於 skill scripts 目錄中的版本
**Then** 這是「部署版本與 skill scripts 原始版**不同步**」問題——skill scripts 修復 bug 後，crontab 指向的 `/tmp/` 工作副本未同步更新
**Then** 立即執行同步修復：
```bash
cp ~/.hermes/skills/school-bulletin-system/scripts/school-bulletin-watchdog.sh /tmp/school-bulletin-watchdog.sh
bash /tmp/school-bulletin-watchdog.sh  # 驗證 exit 0
```
**預防**：任何 `school-bulletin-watchdog.sh` 的原始碼變更後，必須同步到 crontab 指向的 `/tmp/` 路徑，並重新驗證 exit 0。

## If→Then 規則

**If** 用戶說「建立學校公告系統」「幫我做一個處室可以發公告的網站」
**Then** 使用本 skill，但注意：需先建立 `scripts/` 下的執行檔（見上方實作缺口）

**If** 用戶說「誰可以發布公告」「家長能看到什麼」
**Then** 說明 C 方案 v4：sysadmin + dept_officer 可發布，所有登入者看全部公告

**If** 用戶說「公告被家長/學生看到，但家長/學生不該看到」
**Then** 這是 v4 設計——在內部公告機制完成前，所有人都看全部。未來加 `audience_type: 'internal'` 欄位後可分流

**If** 部署後看到 401/403 或認證失效
**Then** 檢查 `SESSION_SECRET` 是否一致（新部署 `SESSION_SECRET` 不一致會導致所有 session 失效）

**If** `vercel env pull` 後附帶了 `AGENT_API_KEY=***`
**Then** 這是 Vercel CLI 的 mask bug，手動用真實 key 替換

## 已知限制

1. **M-08 推播通知 v1 不做**：需要 VAPID 金鑰設定，超出 initial handoff 範圍
2. **無「內部公告」機制**：v4 簡化為「全部可見」，未來加 `audience_type` 欄位可還原受眾分流
3. **無 webhook**：公告變化無即時通知，未來可用 Supabase Realtime 或 Pipedream
4. **Session 8 小時**：HMAC session 有時限，長期不操作需重新登入
5. **LINE Bot webhook 整合（進行中）**：見 `references/line-bot-webhook-integration-20260719.md` — 將「無 webhook」改為「LINE Bot 即時通知」

## 參考檔案

- `~/permanent-projects/school-bulletin/docs/DESIGN_DECISIONS.md` — 設計決策 audit trail（含 v1→v4 演進）
- `~/permanent-projects/school-bulletin/deliverable_audit.md` — 完整交付驗收報告
- `~/permanent-projects/school-bulletin/README.md` — 技術文件
- `skills/trial-and-error/references/by-category/audience-permission-logic.md` — C 方案 v4 受眾邏輯鐵律（任何改 audience 前必讀）
- `references/watchdog-404-fix-20260621.md` — watchdog `/api/health` 404 假性失敗修復（2026-06-21）
- `references/line-bot-webhook-integration-20260719.md` — LINE Bot webhook 整合彌補計畫（填補「無 webhook」已知限制）
- `references/seed-sh-d3-exit-20260623.md` — seed.sh wrapper D3 exit 完整紀錄（三坑：路徑推導/.env 雙引號/tsx 不讀 .env.local）
