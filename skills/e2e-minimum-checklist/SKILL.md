---
name: e2e-minimum-checklist
description: "任何 web app 部署「前」必跑的 E2E 10 項 minimum checklist — 補 deploy-preflight-safelist 的 E2E 段為獨立 skill。觸發:任何 Next.js / Express / FastAPI / Rails / 任何 web app 部署前、棒 N 結束前、production URL 上線前。使用者說「E2E」「end-to-end」「部署前測試」「production ready」時強制觸發。核心原則:「happy path 不夠、error path 必跑」、「單一角色不夠、多角色交叉測」、「單一 env 不夠、本機 + production 都要測」。"
version: 1.0.0
author: Hermes Agent (auto-saved, 2026-06-11 school-bulletin production 5 bug 慘案歸納)
license: MIT
platforms: [linux, macos]
---

# E2E Minimum Checklist (End-to-End Minimum Checklist)

> 任何 web app 部署**前**必跑 10 項 minimum。**全部綠**才准 deploy。
> 2026-06-11 從 school-bulletin production 5 bug 慘案歸納（POST 沒擋、編刪未驗、session 沒過期、簽收 UI 沒說明、AND 篩選 500）。

## 觸發條件（任一符合即觸發）

- 任何 web app（Next.js / Express / FastAPI / Rails / Django / 任何 SSR 框架）部署前
- 棒 N 結束、要進棒 N+1 之前
- production URL 上線前
- 使用者說「可以 deploy 了」「production ready」「上 production」

**自我檢查**：這個 web app 有 user-facing 功能？（是 → 走 SOP；否 → 不用）

---

## 10 項 Minimum（必跑、全綠才 deploy）

### 1. 訪客（無 cookie）能載首頁

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://<prod-url>/
# 預期: HTTP 200
```

**為什麼必跑**：未登入狀態 = 80% 真實訪客、首頁 404 或 500 全部人看不到

### 2. 登入 flow: login 200 → /api/auth/me 200 → cookie 正確

```bash
# Login + 抓 cookie
curl -s -X POST https://<prod-url>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<test-user>","password":"<test-pwd>"}' \
  -c /tmp/cookie.txt

# 預期: HTTP 200 + 看到 user 物件

# /api/auth/me 帶 cookie
curl -s https://<prod-url>/api/auth/me -b /tmp/cookie.txt
# 預期: HTTP 200 + 看到同樣 user
```

**為什麼必跑**：登入是入口、入口壞 = 全部功能不可用。**尤其要驗 cookie 能帶到下一個 request**（學校專案慘案：login 200 但 cookie 沒保住、me 500）。

### 3. happy path: 處室 POST 201 → GET 看到 → PATCH 200 → DELETE 204

```bash
# POST 新增
POST_ID=$(curl -s -X POST https://<prod-url>/api/<resource> \
  -H "Content-Type: application/json" \
  -b /tmp/cookie.txt \
  -d '{"title":"E2E 測試","content":"內容","department":"academic"}' | jq -r '.data.id')

# 預期: 201, 有 ID

# GET 看到
curl -s https://<prod-url>/api/<resource>/$POST_ID -b /tmp/cookie.txt
# 預期: 200, 看到剛才 POST 的內容

# PATCH 修改
curl -s -X PATCH https://<prod-url>/api/<resource>/$POST_ID \
  -H "Content-Type: application/json" \
  -b /tmp/cookie.txt \
  -d '{"title":"E2E 修改後"}'
# 預期: 200

# DELETE 刪除
curl -s -X DELETE https://<prod-url>/api/<resource>/$POST_ID -b /tmp/cookie.txt
# 預期: 204
```

**為什麼必跑**：CRUD 是基本、其中一個壞 = 整個資源管理不可用。**尤其 DELETE 204 容易漏**（Next.js 預設 DELETE route 回 Response.json() 不是 204、會變 200 但 body 為空、仍是 bug）。

### 4. error path A: 受眾 / 非授權角色 POST 403

```bash
# 用另一個 role (非 POST 授權) 帳號
curl -s -X POST https://<prod-url>/api/<resource> \
  -H "Content-Type: application/json" \
  -b /tmp/cookie_audience.txt \
  -d '{"title":"受眾測試","content":"內容"}'
# 預期: 403 + 帶 error message (不是 200 也不是 500)
```

**為什麼必跑**：權限矩陣是最常被遺忘的、API 沒擋 = 任何人都能新增資料。**學校專案慘案**：role=teacher/parent/student 的受眾帳號能 POST 公告。

### 5. error path B: 未登入 PATCH 401

```bash
# 不帶 cookie PATCH
curl -s -X PATCH https://<prod-url>/api/<resource>/$POST_ID \
  -H "Content-Type: application/json" \
  -d '{"title":"未登入修改"}'
# 預期: 401 (或 redirect to /login)
```

**為什麼必跑**：未登入保護是最基本的安全設計、API 沒擋 = 任何人都能改別人的資料。

### 6. error path C: 過期 cookie → 401 或 redirect to login

```bash
# 把 cookie 改成過期的
sed -i 's/sb_session=.*/sb_session=expired/' /tmp/cookie.txt
curl -s -X PATCH https://<prod-url>/api/<resource>/$POST_ID \
  -H "Content-Type: application/json" \
  -b /tmp/cookie.txt \
  -d '{"title":"過期 cookie 測試"}'
# 預期: 401 或 redirect to /login?reason=session_expired
```

**為什麼必跑**：session 過期處理是常見 bug、API 沒擋 = 過期 cookie 還能改資料、UX 不知道為什麼失敗。**學校專案慘案**：過期 cookie 還能 POST、UI 沒提示。

### 7. AND/OR 篩選 200 + 結果正確

```bash
# 篩選 with 2 個 tag, AND 邏輯
curl -s "https://<prod-url>/api/<resource>?tagIds=tag1,tag2&logic=and" -b /tmp/cookie.txt | jq '.data | length'
# 預期: 結果都是同時有 tag1 和 tag2 的

# 同一組, OR 邏輯
curl -s "https://<prod-url>/api/<resource>?tagIds=tag1,tag2&logic=or" -b /tmp/cookie.txt | jq '.data | length'
# 預期: 結果是有 tag1 或 tag2 的,數量 >= AND 的數量
```

**為什麼必跑**：篩選邏輯是最容易寫錯的、**尤其 AND 邏輯的交集**。**學校專案慘案**：AND 篩選 500 `TypeError: Cannot read properties of undefined (reading 'length')`。

### 8. 簽收 / 確認 / 狀態變更 API 201

```bash
# POST 簽收
curl -s -X POST https://<prod-url>/api/<resource>/$POST_ID/sign \
  -H "Content-Type: application/json" \
  -b /tmp/cookie.txt \
  -d '{}'
# 預期: 201 + 看到簽收記錄
```

**為什麼必跑**：狀態變更 API 容易因為 schema 不對、unique constraint、外鍵失敗而 500。

### 9. 簽收 idempotent（重複簽 200 不是 201）

```bash
# 同一個簽收 API 跑兩次
curl -s -X POST https://<prod-url>/api/<resource>/$POST_ID/sign \
  -H "Content-Type: application/json" \
  -b /tmp/cookie.txt \
  -d '{}' -w "\nHTTP %{http_code}\n"
# 第一次: 預期 201
curl -s -X POST https://<prod-url>/api/<resource>/$POST_ID/sign \
  -H "Content-Type: application/json" \
  -b /tmp/cookie.txt \
  -d '{}' -w "\nHTTP %{http_code}\n"
# 第二次: 預期 200 (idempotent) 或 409 (conflict),不是 201
```

**為什麼必跑**：idempotency 是 API 設計基本、容易在「重複請求」時出錯。**學校專案慘案**：第二次簽收 500 unique constraint。

### 10. 至少 1 個檔案上傳 + 下載

```bash
# 上傳
curl -s -X POST https://<prod-url>/api/attachments/upload \
  -b /tmp/cookie.txt \
  -F "file=@/tmp/test.pdf"
# 預期: 201 + 拿到 file ID

# 下載
curl -s -o /tmp/downloaded.pdf -w "HTTP %{http_code}, size %{size_download}\n" \
  https://<prod-url>/api/attachments/$FILE_ID/download -b /tmp/cookie.txt
# 預期: 200 + 下載下來的檔案大小 > 0
```

**為什麼必跑**：檔案上傳/下載是最常壞的功能（路徑、權限、CDN、storage bucket）、容易在上 production 才發現。**至少有 1 個檔案 = 確認整個 storage pipeline 通了**。

---

## 多角色測試（棒 N 結束額外必跑）

如果 web app 有角色矩陣（dept_officer / sysadmin / 受眾）：

```
[ ] 每個 role 至少 1 個帳號跑完 10 項 minimum
[ ] 受眾 role POST 必 403
[ ] 處室 role POST 必 201
[ ] 跨 role 看到資料的 scope 正確（處室互通 vs 處室隔離）
```

**慘案**：學校專案 v1 設計教務處只看到教務處的、違反直覺、整個 v1 推翻重做。**多 role 交叉測試能早期 catch 設計問題**。

---

## 多環境測試（棒 N 結束額外必跑）

```
[ ] 本機 E2E 10 項全綠
[ ] production E2E 10 項全綠 (deployment URL)
[ ] 本機 vs production 結果一致 (尤其 DB schema 是不是真的同步)
```

**慘案**：學校專案棒 1 寫 SQL 進 git、但沒真跑進 Supabase、本機看起來 OK、production 5 個 bug。**多環境交叉測試能 catch 棒 1 慘案**。

---

## 跑完 E2E 怎麼回報

```markdown
### E2E 10 項結果
| 項目 | 本機 | production |
|------|------|-----------|
| 1. 訪客首頁 200 | ✅ | ✅ |
| 2. 登入 flow | ✅ | ✅ |
| 3. happy path CRUD | ✅ | ✅ |
| 4. 受眾 POST 403 | ✅ | ✅ |
| 5. 未登入 PATCH 401 | ✅ | ✅ |
| 6. 過期 cookie 401 | ✅ | ✅ |
| 7. AND/OR 篩選 | ✅ | ✅ |
| 8. 簽收 API 201 | ✅ | ✅ |
| 9. 簽收 idempotent | ✅ | ✅ |
| 10. 檔案上傳下載 | ✅ | ✅ |
```

**任何一項不綠 → 停下來 fix、不准 deploy**。

---

## If→Then 速查

- **If** 棒 N 結束準備進棒 N+1 **Then** 必跑這 10 項 + 多角色 + 多環境
- **If** production E2E 有任何紅 **Then** revert 到上一個綠的 commit、不在 production debug
- **If** 受眾 POST 200（應該 403）**Then** API 沒擋、整個權限矩陣壞了、不准 deploy
- **If** AND 篩選 500 **Then** schema 對不上 / 沒容錯、棒 1 DDL 必跑驗證（見 deploy-preflight-safelist 原則 2）
- **If** 過期 cookie 200 **Then** session 過期處理壞了、整個 auth 流程要重做
- **If** production vs 本機結果不一致 **Then** DB schema 不同步、棒 1 DDL 沒真跑

---

## 與其他 skill 的關係

- **本 skill 是 deploy-preflight-safelist 原則 3（E2E 必跑 happy + error path）的展開**、更詳細 + 可直接複製貼上
- 部署**後**驗證（DNS / headless browser / 4 步）見 `deployment-verification-sop`
- 棒 1 race / 棒 N 間 handoff 細節見 `handoff-chain-timeout-sop.md`
- **⚠️ 重要串接**：`e2e-minimum-checklist` 是「這 10 件事現在能不能做」（靜態 pass/fail 健康檢查），**不**知道「相較上次變更有沒有功能退化」。正確串接順序：

  ```
  handoff-chain-acceptance-sop（PRD 4 步對照）
      ↓
  e2e-minimum-checklist（10 項健康檢查）← 本 skill
      ↓
  regression-testing（API snapshot diff）  ← 必接在這裡
      ↓
  vercel deploy（或 revert）
  ```

  **沒有 regression-testing 的問題**：10/10 綠但 AND 篩選從正確變 500（功能退化）不會被 catch。學校專案 06-11 的 5 Must 只有 55% 實作率，正是兩層都缺的情況。

---

## 變更記錄

- 2026-06-11 v1.0.0 — 從 school-bulletin production 5 bug 慘案歸納建立。10 項 minimum + 多角色測試 + 多環境測試 + 回報格式
- 2026-06-13 — 新增「與 regression-testing 的串接關係」，彌補本 skill 只有靜態 pass/fail 無 diff 的缺口
