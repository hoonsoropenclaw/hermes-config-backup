# [專案名稱] API 規格(範本)

> **這是 system-architect 代理的交付物範本**。完整方法論見 `~/.hermes/profiles/system-architect/skills/system-architecture/SKILL.md` Step 6。
> 複製這個檔、把 `[...]` 佔位符替換成實際內容,完成後存到 `~/.hermes/handoff/<project-slug>/api-spec.md`。

---

建立日期:YYYY-MM-DD
負責代理:system-architect
API 風格:RESTful
API 根路徑:`https://api.example.com/api/v1`
認證:JWT (Bearer Token)

---

## §1 認證機制

### Access Token
- **格式**:JWT (HS256)
- **有效期**:15 分鐘
- **儲存(前端)**:記憶體(不可 localStorage 防 XSS)
- **Header**:`Authorization: Bearer <access_token>`

### Refresh Token
- **格式**:隨機 256-bit 字串(儲存 hash 在 sessions 表)
- **有效期**:30 天
- **儲存(前端)**:httpOnly Secure SameSite=Strict cookie
- **使用**:POST `/auth/refresh` 換新 access_token

### 認證流程
```
1. POST /auth/login → 回 access_token + Set-Cookie refresh_token
2. 前端每次 request → Header 加 access_token
3. access_token 過期 → POST /auth/refresh(cookie 自動帶)→ 拿新 access_token
4. refresh_token 也過期 → 重新登入
```

---

## §2 共用規範

### 2.1 分頁

**Cursor-based**(推薦,用於無限滾動):
```
GET /api/v1/orders?cursor=eyJpZCI6MTIzfQ&limit=20

Response:
{
  "data": [...],
  "next_cursor": "eyJpZCI6MTQzfQ",
  "has_more": true
}
```

**Offset-based**(用於後台管理):
```
GET /api/v1/admin/orders?page=1&page_size=20

Response:
{
  "data": [...],
  "total": 1234,
  "page": 1,
  "page_size": 20,
  "total_pages": 62
}
```

### 2.2 排序
```
GET /api/v1/products?sort=created_at_desc  # 或 _asc
```

### 2.3 篩選
```
GET /api/v1/products?status=active&min_price=100&max_price=500
```

### 2.4 限流

每個 IP:
- 60 requests / 分鐘(一般 API)
- 10 requests / 分鐘(認證 API: login, register, refresh)
- 5 requests / 分鐘(密碼重設 email)

**超過限流** → 回 429 Too Many Requests + `Retry-After: <seconds>` header

### 2.5 版本控制
- URL path:`/api/v1/...`、`/api/v2/...`
- Breaking change 才升 v2、additive 改進留在 v1
- 舊版本維護 6 個月 + 3 個月重疊期

### 2.6 錯誤回應格式

**所有 4xx / 5xx 都用這個結構**:
```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "使用者不存在",
    "details": {
      "user_id": "uuid"
    }
  }
}
```

---

## §3 錯誤碼總表

### 4xx — Client Error

| HTTP | code | 說明 |
|------|------|------|
| 400 | INVALID_REQUEST | 請求參數錯誤 |
| 400 | VALIDATION_ERROR | 欄位驗證失敗 |
| 401 | UNAUTHENTICATED | 缺少 access token |
| 401 | TOKEN_EXPIRED | access token 過期(用 refresh) |
| 401 | TOKEN_INVALID | access token 格式錯或被撤銷 |
| 403 | PERMISSION_DENIED | 權限不足 |
| 404 | NOT_FOUND | 資源不存在 |
| 409 | ALREADY_EXISTS | 資源已存在(例:email 重複) |
| 409 | CONFLICT | 狀態衝突(例:取消已出貨訂單) |
| 422 | BUSINESS_RULE_VIOLATED | 業務規則違反 |
| 429 | RATE_LIMIT_EXCEEDED | 超過限流 |

### 5xx — Server Error

| HTTP | code | 說明 |
|------|------|------|
| 500 | INTERNAL_ERROR | 未預期錯誤 |
| 502 | UPSTREAM_ERROR | 外部服務失敗 |
| 503 | SERVICE_UNAVAILABLE | 維護中或過載 |
| 504 | UPSTREAM_TIMEOUT | 外部服務 timeout |

---

## §4 端點清單

### 4.1 Auth(認證)

#### POST /api/v1/auth/register
**用途**:使用者註冊
**認證**:無
**限流**:10 / 小時 / IP

**請求**:
```json
{
  "email": "user@example.com",
  "password": "StrongP@ss123",
  "name": "王小明"
}
```

**回應 201**:
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "王小明",
    "created_at": "2026-06-10T12:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
+ `Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=2592000`

**錯誤**:
- 400 VALIDATION_ERROR(password 強度不足)
- 409 ALREADY_EXISTS(email 已被註冊)
- 429 RATE_LIMIT_EXCEEDED

#### POST /api/v1/auth/login
[同上結構]

#### POST /api/v1/auth/refresh
**用途**:用 refresh_token 換新 access_token
**認證**:refresh_token cookie(自動帶)
**請求**:無 body
**回應 200**:`{ "access_token": "..." }` + 新 Set-Cookie
**錯誤**:401 TOKEN_INVALID / TOKEN_EXPIRED

#### POST /api/v1/auth/logout
**用途**:撤銷當前 refresh_token
**認證**:需 access_token
**回應 204**:無 body

### 4.2 Users(使用者)

#### GET /api/v1/users/me
**認證**:需
**回應 200**:
```json
{
  "id": "...",
  "email": "...",
  "name": "...",
  "avatar_url": "...",
  "skill_tags": [
    { "tag": "Python", "level": "expert" },
    { "tag": "日文", "level": "intermediate" }
  ]
}
```

#### PATCH /api/v1/users/me
**認證**:需
**請求**:`{ "name": "新名字", "avatar_url": "https://..." }`(部分欄位)
**回應 200**:更新後的 user

### 4.3 Orders(訂單)

#### POST /api/v1/orders
**認證**:需
**請求**:
```json
{
  "items": [
    { "product_id": "uuid", "quantity": 2 }
  ],
  "shipping_address": {
    "name": "王小明",
    "phone": "+886912345678",
    "address": "台北市信義區..."
  }
}
```
**回應 201**:
```json
{
  "id": "uuid",
  "status": "pending",
  "total_amount": 1200.00,
  "currency": "TWD",
  "payment_url": "https://checkout.stripe.com/...",
  "created_at": "..."
}
```

#### GET /api/v1/orders
**認證**:需
**Query**:`?cursor=...&limit=20&status=paid`
**回應 200**:見 §2.1 cursor-based 格式

#### GET /api/v1/orders/{id}
**認證**:需(只能看自己的訂單)
**回應 200**:訂單完整資料
**錯誤**:404 NOT_FOUND / 403 PERMISSION_DENIED(別人的訂單)

#### POST /api/v1/orders/{id}/cancel
**認證**:需
**回應 200**:訂單狀態變 `cancelled`
**錯誤**:409 CONFLICT(已出貨無法取消)

### 4.4 Payments(付款)

#### POST /api/v1/payments/webhook
**用途**:Stripe Webhook 接收
**認證**:Stripe Signature header 驗證
**冪等性**:用 `provider_transaction_id` 去重
**處理**:更新 `payments` 跟 `orders` 狀態 → 觸發 `order.paid` event → background worker 寄 email

### 4.5 Reviews(評價)

#### POST /api/v1/products/{id}/reviews
**認證**:需
**請求**:`{ "rating": 5, "content": "..." }`
**回應 201**:`{ "id": "...", "rating": 5, ... }`
**限制**:每個使用者對同一商品只能評一次

#### GET /api/v1/products/{id}/reviews
**認證**:無
**Query**:`?cursor=...&limit=20&sort=created_at_desc`
**回應 200**:cursor 格式

---

## §5 WebSocket / SSE(若需要即時通訊)

### 5.1 連線

```
WSS /api/v1/ws/chat?token=<access_token>
```

- 連線時 query 帶 access_token
- 服務端驗證後升級 WebSocket
- 斷線自動 reconnect、指數退避

### 5.2 訊息格式

**客戶端送**:
```json
{
  "type": "send_message",
  "to_user_id": "uuid",
  "content": "你好"
}
```

**服務端推**:
```json
{
  "type": "new_message",
  "from_user_id": "uuid",
  "content": "你好",
  "timestamp": "2026-06-10T12:00:00Z"
}
```

### 5.3 心跳

每 30 秒客戶端送 `{"type": "ping"}`,服務端回 `{"type": "pong"}`。90 秒無心跳 → 自動斷線。

---

## §6 給 engineering-lead 的「1 小時上手 checklist」

- [ ] 看完 §1 認證機制能在 middleware 內實作 JWT 驗證
- [ ] 看完 §2 共用規範能在 FastAPI / Express 加 middleware
- [ ] 看完 §3 錯誤碼總表能建 exception class hierarchy
- [ ] 看完 §4 端點清單能在 OpenAPI Generator 跑出 client SDK
- [ ] 看完 §5 WebSocket(若需要)能選擇合適的 library(Socket.IO / websockets)
- [ ] 看完能在 1 小時內開始寫第一個 endpoint

---

## §7 自我審查(交付前必跑)

- [ ] 每個端點都有 Method + Path + 認證 + 請求/回應/錯誤碼?
- [ ] 認證機制在 §1 完整描述(包括 refresh + logout)?
- [ ] 共用規範(分頁/排序/篩選/限流/版本)都有?
- [ ] 錯誤碼總表覆蓋所有 4xx / 5xx 場景?
- [ ] WebSocket(若有)有完整訊息格式 + 心跳?
- [ ] §6 checklist 完整、可執行?

---

**版本**:v0.1 (初稿)
