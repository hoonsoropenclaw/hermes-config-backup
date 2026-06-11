---
name: supabase-integration
description: 整合 Supabase 到 Vercel 部署的 Next.js / Node 專案的完整 SOP。涵蓋拿到兩把 key (anon + service_role)、SQL schema 設計、RLS 政策、JS SDK 整合、Vercel env 設定。觸發情境:使用者說「用 Supabase」「Supabase DB」「Postgres 雲端」「Supabase auth」「auth 用 supabase」時立即載入。
---

# Supabase 整合 SOP

> 給 N100 headless 環境 + Vercel 部署使用。涵蓋「拿到 key → 建 schema → 改 code → 部署」端到端流程。

## 何時使用

**觸發情境**（任一符合即觸發）:
- 使用者說「用 Supabase」「改用 Supabase」「把 DB 換成 Supabase」「我要 Supabase auth」
- 任何 Postgres / Auth / Storage 雲端整合任務
- Vercel KV / Vercel Postgres 連線失敗、考慮改用 Supabase
- 專案需要 RLS (Row Level Security) 控管前端直接查表

---

## 1. 兩把 Key 的角色分工

| Key | 用途 | 能不能放前端 / Vercel env | 能不能跑 DDL |
|---|---|---|---|
| **`anon` `public`** | 前端 / 公開 API、**受 RLS 政策控管** | ✅ 可以 | ❌ 不能 |
| **`service_role` `secret`** | 繞過 RLS、**等同 DB superuser** | ❌ **絕對不行**（只放 serverless function 環境變數、不進 `NEXT_PUBLIC_*`） | ✅ 能跑 SQL（透過 PostgREST 或管理 API） |

**關鍵安全模型**: anon key 即使被外人拿到、沒有登入 session 也只能做 RLS「允許」的事。
**service_role key 一旦洩漏 = 完整 DB 權限、砍資料都沒人擋**。

---

## 2. 拿到 Key 流程（給使用者看的 SOP）

1. 開 https://supabase.com/dashboard → 登入（GitHub OAuth 最快）
2. 點 **New Project**:
   - Name: `<project-name>`
   - Database Password: **記下來**（不會再顯示）
   - Region: **Singapore (ap-southeast-1)** 對台灣最近
   - Plan: **Free** 夠用
   - 點 Create → 等 ~90 秒
3. 建好後進去 **Settings → API**，複製:
   - `Project URL`（長得像 `https://abcdefg.supabase.co`）
   - `Project API keys` 區的 **`anon` `public`** key
4. **不要**複製 `service_role` 給赫米斯貼進任何檔（除非確定走「赫米斯跑 SQL 建表」路線、用完即丟）

---

## 3. 建資料表的兩個路徑

### 路徑 A：使用者自己貼 SQL 到 SQL Editor（推薦、最安全）

赫米斯把完整 SQL 寫成檔、印到對話給使用者、附單一 URL 連結:
- 印 `https://supabase.com/dashboard/project/<ref>/sql/new`
- 跑完請使用者回報 `SELECT` 結果（確認 5 個表都建好）

**好處**: service_role 不用過赫米斯手。

### 路徑 B：使用者給 service_role（赫米斯自己跑）

- 赫米斯用 Python `urllib.request` 直接打 REST API
- 驗證 SR 有效: `GET /rest/v1/<table>` → 應回 404 (table 還沒建) 而非 401
- 寫 SQL 到 `/tmp/schema.sql`、呼叫 `pg8000` 或 `psycopg2` 連 DB 跑 DDL
- **寫完不保留 token、用過即清**（見 step 4）

**警告**: **Supabase REST API 不能跑 DDL**（`POST /rest/v1/rpc/` 只支援 `CREATE FUNCTION`）。要走 DDL 必須:
- `psql` + connection string（從 Settings → Database → Connection string → URI 拿）
- 或 Python `psycopg2` + connection string

---

## 4. service_role 處理守則

**If** 拿到 service_role key **Then**:
1. **只放環境變數傳遞、不寫進任何檔案**
2. 寫進 `/tmp/<project>.env` 跑用、用完 `shred -u /tmp/<project>.env` 或 `rm -f`
3. **不要** 寫進 `~/.hermes/.env`、**不要** 寫進 `MEMORY.md`、**不要** 在對話明文重複貼
4. 部署上線時 **service_role 也不進 Vercel env**（只用 anon）

**驗證**:
```bash
# 確認 service_role 沒留在任何位置
grep -r "service_role" ~/.hermes/ ~/.bashrc /tmp/*.env 2>/dev/null | grep -v node_modules
# 應回空（或只有 code 內 `apikey: process.env.SUPABASE_SERVICE_ROLE_KEY` 之類的引用、不是明文 token）
```

---

## 5. Vercel Env 設定

```python
# 透過 Vercel REST API (從 ~/.hermes/.env 讀 VERCEL_API_TOKEN)
POST /v10/projects/<id>/env
{
  "key": "NEXT_PUBLIC_SUPABASE_URL",
  "value": "https://xxxxx.supabase.co",
  "type": "encrypted",
  "target": ["production", "preview", "development"]
}
POST /v10/projects/<id>/env
{
  "key": "NEXT_PUBLIC_SUPABASE_ANON_KEY",
  "value": "eyJhbG...<anon JWT>",
  "type": "encrypted",
  "target": ["production", "preview", "development"]
}
```

**必加 3 個 target**: production + preview + development（漏 preview 會導致 git push preview 部署讀不到 env 噴 500）。

---

## 6. Next.js JS SDK 整合

```bash
npm install @supabase/supabase-js
```

**前端 client (lib/supabase-client.ts)**:
```typescript
import { createBrowserClient } from '@supabase/ssr';

export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

**Server client (lib/supabase-server.ts)** — Next.js App Router:
```typescript
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (toSet) => { for (const { name, value, options } of toSet) cookieStore.set(name, value, options); }
      }
    }
  );
}
```

**RLS 透過 anon key 自動生效** — SELECT 只能拿到 RLS 政策允許的列。

---

## 7. 常見坑

| 症狀 | 根因 | 修法 |
|------|------|------|
| `Invalid API key` 用 anon 打 | anon key 被遮罩截斷 / 複製時少字 | 重到 dashboard 重新複製完整 JWT |
| `Could not find the table 'public.X'` | 沒跑 SQL 建表 | 跑 Schema Editor 或 SQL Editor |
| `permission denied for table X` | RLS 政策擋住 | 進 dashboard → Authentication → Policies 加 policy |
| `401` 在 serverless function | env 變數沒設或只設 production target | 改用 `target: ["production", "preview", "development"]` |
| `next/image` 顯示 Supabase Storage 圖片 403 | bucket 是 private | bucket 改 public 或用 signed URL |

---

## If→Then 速查

- **If** 使用者說「用 Supabase」 **Then** 載入此 skill + 給「拿到 key 流程」4 步 SOP
- **If** 拿到 anon key 但缺 service_role **Then** 走「路徑 A」（SQL 給使用者貼到 SQL Editor）
- **If** 拿到 service_role **Then** 只放 env、用過即清、不寫進任何檔
- **If** 部署 Vercel 後 Supabase 連線 500 **Then** 檢查 env target 是否含 production + preview + development 三個
- **If** anon key 從前端 query 一直回空陣列 **Then** 檢查 RLS 政策（`USING` clause 條件太嚴）
- **If** 整合到一半使用者又說「改用 Vercel KV」**Then** 不衝突、可同時存在、KV 做 cache、Supabase 做 source of truth
- **If** 需要 migration 工具 **Then** 用 `supabase db diff` / `supabase db push` CLI 跑 migration、不要手動貼 SQL

## 交叉參考

- `~/.hermes/skills/trial-and-error/references/by-category/secrets-and-env.md` — token 存放原則
- `~/.hermes/skills/trial-and-error/references/by-category/vercel-deployment.md` — Vercel env 設定 3 個 target
- `~/.hermes/skills/trial-and-error/references/sops/keyword-triggers-sop.md` — 觸發「用 Supabase」等 keyword 後的 SOP
