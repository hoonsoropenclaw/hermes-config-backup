# Supabase Migration 10 項完整性 Checklist

從 KV/Blob 切到 Supabase 必跑的驗證項。每項獨立可驗證、不可跳。

## Phase 1: Schema（動手前）

- [ ] **1. Schema SQL 在 Supabase dashboard 跑成功**
  ```sql
  SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name IN
      ('departments','users','tags','announcements','attachments')
    ORDER BY table_name;
  -- 預期 5 行
  ```

- [ ] **2. RLS 在 5 個表上都啟用**
  ```sql
  SELECT tablename, rowsecurity FROM pg_tables
    WHERE schemaname='public' AND tablename IN
      ('departments','users','tags','announcements','attachments');
  -- 預期 5 行全部 rowsecurity = true
  ```

- [ ] **3. Storage bucket `attachments` 建立、私有**
  - 到 Storage → 看 bucket 列表 → 看到 `attachments`
  - Bucket 設為 private（不走 public URL、後端 proxy 下載）

## Phase 2: 程式碼（commit 前）

- [ ] **4. 全域 grep 確認沒有 Vercel KV/Blob 殘留**
  ```bash
  cd <project>
  grep -rE "@vercel/(kv|blob)|HAS_BLOB|blobUrl|KV_REST|BLOB_READ" \
    --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" .
  # 預期: 0 match (除了 package.json 也清了)
  ```

- [ ] **5. `package.json` 移除 `@vercel/kv` `@vercel/blob`、加上 `@supabase/supabase-js`**
  ```bash
  grep -E "@vercel/(kv|blob)|@supabase" package.json
  # 預期: @supabase/supabase-js 在 dependencies、@vercel/(kv|blob) 沒有
  ```

- [ ] **6. `lib/db.ts` 改為 `getSupabaseAdmin()` + `HAS_SUPABASE`**
  ```bash
  grep -E "getSupabaseAdmin|HAS_SUPABASE" lib/db.ts | head -3
  # 預期: 2 行有 match
  ```

- [ ] **7. `lib/repository.ts` 用 Supabase client（不是 `kvGet` / `kvSet`）**
  ```bash
  grep -E "getSupabaseAdmin|kvGet" lib/repository.ts | head -3
  # 預期: getSupabaseAdmin 有 match、kvGet 沒有
  ```

## Phase 3: Vercel env（部署前）

- [ ] **8. Vercel 專案 env 有 3 個 Supabase、target 含三個 environment**
  ```python
  # 跑 env-migration-script.py 或 Vercel REST API
  GET /v9/projects/<id>
  # 預期 env 包含:
  #   SUPABASE_URL                 plain      production,preview,development
  #   SUPABASE_ANON_KEY            plain      production,preview,development
  #   SUPABASE_SERVICE_ROLE_KEY    encrypted  production,preview,development
  ```

- [ ] **9. 死的 KV/Blob env 已刪**
  ```python
  GET /v9/projects/<id>
  # 預期: 沒有 KV_REST_API_URL / KV_REST_API_TOKEN / BLOB_READ_WRITE_TOKEN
  ```

## Phase 4: Production 驗證（部署後必跑 5 步）

- [ ] **10. 五步 production 連線驗證全通**

```bash
PROD=https://<project>.vercel.app

# Step 1: seed 觸發（建 6 帳號 + N tags + N 公告）
curl -s "$PROD/api/seed-demo" | head -c 300
# 預期: {"ok":true,"report":{"users":6,"tags":N,"announcements":N}}

# Step 2: tags 真的讀得到
curl -s "$PROD/api/tags" | head -c 300
# 預期: {"data":[{...}]}  不是空陣列

# Step 3: 登入真的能用
curl -s -X POST "$PROD/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"teaching","password":"School@2026"}' | head -c 300
# 預期: {"data":{"id":"u_xxx","displayName":"教務處"}}
# 若 {"error":"INVALID_CREDENTIALS"} → seed 沒生效 → 重跑 step 1

# Step 4: 首頁不是 __next_error__
curl -s "$PROD/" | grep -c "__next_error__"
# 預期: 0

# Step 5: 公告列表真的讀得到
curl -s "$PROD/api/announcements?groups=%5B%5D" | head -c 300
# 預期: {"data":[...3 則示範...]}
```

**任何一項失敗 → 不要回報使用者「完成」、誠實標明哪層失敗**

## 沒跑完這 10 項 = migration 還沒成功

無論程式碼多漂亮、build 多綠燈 — production 行為不對 = 失敗。常見漏項：
- 漏 #4 grep → 殘留 `@vercel/blob` import 讓 build 報 `Module not found`
- 漏 #9 env 沒刪 → 雖然有 Supabase、但 Vercel KV 仍佔 env quota、且混淆 debug
- 漏 #10 step 1-5 → 5 個 API 看起來 200 但每個回空、storage dead token 又發生一次

## 完成後的 3 個建議動作

1. **刪掉 debug endpoints**（如果之前為了 debug 加了 `/api/test-kv` 等）— 寫進 commit message `chore: remove debug endpoints`
2. **加 Vercel env 變更到 INVENTORY**（如果有 INVENTORY.md）— 記錄 SUPABASE_* 跟 SESSION_SECRET 怎麼 rotate
3. **重設預設密碼**（`School@2026` 是 demo 用、上 production 前必改）
