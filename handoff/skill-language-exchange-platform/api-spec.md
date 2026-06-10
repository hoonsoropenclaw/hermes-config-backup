# [整合說明]

> 本檔由 system-architect v3_4_workers 模式產出,4 個 web-worker 平行完成於 2026-06-10 21:11,總耗時 8 分 8 秒。
>
> **整合過程**:
> - Worker A (容器圖) → 本檔 §1
> - Worker B (元件圖) → 本檔 §2
> - Worker C (資料庫) → 獨立 `database-schema.md`
> - Worker D (API 規格) → 獨立 `api-spec.md`
> - 對齊檢查:容器名 ↔ 元件名 ↔ 表名 ↔ API 端點,**全部對齊**(見 _plan.md 對齊契約)
>
> **5 個架構盲點的預設建議全部採用**:
> 1. 政府證件 → 30 分鐘硬刪 + 遮罩
> 2. 跨國匯率 → 固定 USD 錨點
> 3. 活體檢測 → 簡單眨眼 + 人工 review
> 4. 影片儲存 → Supabase Storage + Cloudflare
> 5. 12 歲學員 → MVP 不開放

---

## §1-§5 認證 + 共用規範 + 端點清單 + WebSocket(Worker D)

# §1 認證機制

## 1.1 雙 JWT 架構

| Token 類型 | 有效期 | 儲存位置 | 用途 |
|-----------|--------|----------|------|
| `access_token` | 15 分鐘 | Memory (JS) / Keychain | API 請求授權 |
| `refresh_token` | 30 天 | httpOnly Cookie (SameSite=Strict) | 刷新 access_token |

### 1.1.1 Access Token 規格

```json
// JWT Payload
{
  "sub": "uuid-v4",
  "user_id": "usr_abc123",
  "role": "user",
  "iat": 1718000000,
  "exp": 1718000900
}
```

- Algorithm: HS256
- Secret: 環境變數 `JWT_SECRET` (min 256 bits)
- Header 範例: `Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...`

### 1.1.2 Refresh Token 流程

```
┌──────────┐     POST /auth/refresh      ┌──────────┐
│  Client   │ ──────────────────────────→│   API    │
│           │                            │          │
│           │  ←─ 200 { access_token }   │          │
└──────────┘                            └──────────┘
     │                                        │
     │  httpOnly; Secure; SameSite=Strict     │
     │◄─────────────────────────────────────│
     │         Set-Cookie: refresh_token      │
```

- Refresh 時需帶上 `refresh_token` cookie (自動攜帶)
- 拒绝跨域 refresh (SameSite=Strict)
- 30 天未使用自動失效

## 1.2 認證端點

| 方法 | 路徑 | 認證 | 說明 |
|------|------|------|------|
| POST | /api/v1/auth/register | 無 | 註冊 |
| POST | /api/v1/auth/login | 無 | 登入 |
| POST | /api/v1/auth/refresh | 無 (cookie) | 刷新 access_token |
| POST | /api/v1/auth/logout | Bearer | 登出 |
| POST | /api/v1/auth/forgot-password | 無 | 寄密碼重設信 |

---

# §2 共用規範

## 2.1 API 版本控制

- 前綴: `/api/v1/`
- 未來 v2 時: `/api/v2/`，v1 維持 6 個月過渡期
- 破壞性變更**必須**新版本

## 2.2 分頁 (Cursor-Based)

```json
// Request
GET /api/v1/orders?cursor=eyJpZCI6MTIzfQ&limit=20

// Response
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTQzfQ",
    "prev_cursor": "eyJpZCI6MTEzfQ",
    "has_more": true,
    "total_count": 150
  }
}
```

- 預設 `limit`: 20，最大 100
- Cursor 為 Base64 編碼的 JSON `{"id": 123, "created_at": "..."}`
- 支援 `sort=created_at:desc` (預設)

## 2.3 排序

| 欄位 | 格式 | 範例 |
|------|------|------|
| 單一欄位 | `?sort=created_at:desc` | 最舊→最新 |
| 多欄位 | `?sort=status:asc,created_at:desc` | 先 status 再 created_at |
| 支援欄位 | id, created_at, updated_at, name, email | - |

## 2.4 篩選

```json
// Request
GET /api/v1/orders?status=completed&from=2024-01-01&to=2024-12-31

// Response
{
  "data": [...],
  "filters_applied": {
    "status": "completed",
    "date_range": { "from": "2024-01-01", "to": "2024-12-31" }
  }
}
```

- 日期格式: ISO 8601 (`YYYY-MM-DD`)
- 枚舉欄位: `status=pending|active|completed|cancelled`

## 2.5 限流 (Rate Limiting)

| 身份 | 限制 | 視窗 |
|------|------|------|
| 未認證 (IP) | 60 次/分 | 滑動視窗 |
| 已認證 (User) | 120 次/分 | 滑動視窗 |
| 敏感操作 | 10 次/分 | 固定視窗 |

敏感操作包含:
- `POST /auth/register`
- `POST /auth/login`
- `POST /orders` (建立預約)
- `POST /media/upload-id-card`

```json
// 超出限制回應 (429 Too Many Requests)
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "請求頻率過高，請稍後再試",
    "retry_after": 60
  }
}
```

- Header: `X-RateLimit-Limit: 60`, `X-RateLimit-Remaining: 0`, `Retry-After: 60`

## 2.6 統一回應格式

```json
// 成功
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}

// 錯誤
{
  "error": {
    "code": "NOT_FOUND",
    "message": "找不到資源",
    "details": { ... }
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

---

# §3 錯誤碼總表

## 3.1 4xx 用戶端錯誤

| HTTP 狀態 | 錯誤碼 | 說明 | 解決方式 |
|-----------|--------|------|----------|
| 400 | `INVALID_REQUEST` | 請求格式錯誤或參數驗證失敗 | 檢查請求 Body/Params |
| 401 | `UNAUTHORIZED` | 未提供或無效的 access_token | 重新登入或刷新 token |
| 401 | `TOKEN_EXPIRED` | access_token 過期 | 呼叫 POST /auth/refresh |
| 403 | `PERMISSION_DENIED` | 無權限執行此操作 | 檢查角色或所有權 |
| 404 | `NOT_FOUND` | 資源不存在 | 確認 ID/路徑正確 |
| 409 | `ALREADY_EXISTS` | 資源已存在 (如重複註冊) | 使用現有資源或更換資料 |
| 422 | `VALIDATION_ERROR` | 業務邏輯驗證失敗 | 檢查詳細錯誤訊息 |
| 429 | `RATE_LIMIT_EXCEEDED` | 請求頻率超出限制 | 等待後重試 |

## 3.2 5xx 伺服器錯誤

| HTTP 狀態 | 錯誤碼 | 說明 |
|-----------|--------|------|
| 500 | `INTERNAL_ERROR` | 伺服器內部錯誤 |
| 502 | `BAD_GATEWAY` | 上游服務無回應 |
| 503 | `SERVICE_UNAVAILABLE` | 服務暫時不可用 |
| 504 | `GATEWAY_TIMEOUT` | 上游服務逾時 |

## 3.3 錯誤回應範例

```json
// 401 TOKEN_EXPIRED
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "您的 access_token 已過期，請重新整理",
    "details": { "expired_at": "2024-01-01T12:15:00Z" }
  }
}

// 404 NOT_FOUND
{
  "error": {
    "code": "NOT_FOUND",
    "message": "找不到指定的課程預約",
    "details": { "order_id": "ord_xyz789" }
  }
}

// 422 VALIDATION_ERROR
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "請求參數驗證失敗",
    "details": {
      "fields": [
        { "field": "email", "error": "無效的 email 格式" },
        { "field": "points", "error": "點數不足，請先充值" }
      ]
    }
  }
}
```

---

# §4 端點清單

## 4.1 /auth/* — 認證相關 (5 個端點)

### 4.1.1 POST /api/v1/auth/register — 註冊

**認證**: 無

**請求**:
```json
{
  "email": "sako@example.com",
  "password": "SecurePass123!",
  "name": "佐藤健太郎",
  "locale": "zh-TW",
  "timezone": "Asia/Tokyo",
  "birthday": "1992-05-15",
  "gender": "male"
}
```

| 欄位 | 類型 | 必填 | 驗證 |
|------|------|------|------|
| email | string | 是 | 有效 email 格式 |
| password | string | 是 | 最少 8 字元，含大小寫+數字 |
| name | string | 是 | 2-50 字元 |
| locale | string | 是 | `zh-TW` 或 `en` |
| timezone | string | 是 | IANA timezone |
| birthday | string | 否 | ISO date |
| gender | string | 否 | `male` / `female` / `other` |

**回應 201**:
```json
{
  "data": {
    "user_id": "usr_a1b2c3",
    "email": "sako@example.com",
    "name": "佐藤健太郎",
    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
    "expires_in": 900
  },
  "meta": {
    "request_id": "req_register_001"
  }
}
```

**錯誤碼**: `INVALID_REQUEST`, `ALREADY_EXISTS`, `RATE_LIMIT_EXCEEDED`

---

### 4.1.2 POST /api/v1/auth/login — 登入

**認證**: 無

**請求**:
```json
{
  "email": "sako@example.com",
  "password": "SecurePass123!"
}
```

**回應 200**:
```json
{
  "data": {
    "user_id": "usr_a1b2c3",
    "email": "sako@example.com",
    "name": "佐藤健太郎",
    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
    "expires_in": 900,
    "refresh_token_set": true
  }
}
```

**錯誤碼**: `INVALID_REQUEST`, `UNAUTHORIZED`, `RATE_LIMIT_EXCEEDED`

---

### 4.1.3 POST /api/v1/auth/refresh — 刷新 Access Token

**認證**: 無 (使用 httpOnly Cookie)

**請求**: (自動攜帶 cookie)

**回應 200**:
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
    "expires_in": 900
  }
}
```

**錯誤碼**: `INVALID_REQUEST`, `UNAUTHORIZED`

---

### 4.1.4 POST /api/v1/auth/logout — 登出

**認證**: Bearer (access_token)

**請求**: (空 Body)

**回應 200**:
```json
{
  "data": {
    "message": "已成功登出"
  }
}
```

- 清除 httpOnly refresh_token cookie
- 呼叫後 access_token 失效

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`

---

### 4.1.5 POST /api/v1/auth/forgot-password — 忘記密碼

**認證**: 無

**請求**:
```json
{
  "email": "sako@example.com"
}
```

**回應 200**:
```json
{
  "data": {
    "message": "若該帳號存在，密碼重設連結已寄送至 email"
  }
}
```

- 寄送含時效性 token (15 分鐘) 的 email
- 防止帳號枚舉攻擊，回應訊息固定

**錯誤碼**: `INVALID_REQUEST`, `RATE_LIMIT_EXCEEDED`

---

## 4.2 /users/* — 使用者相關 (4 個端點)

### 4.2.1 GET /api/v1/users/me — 取得本人資料

**認證**: Bearer

**回應 200**:
```json
{
  "data": {
    "user_id": "usr_a1b2c3",
    "email": "sako@example.com",
    "name": "佐藤健太郎",
    "avatar_url": "https://cdn.example.com/avatars/usr_a1b2c3.jpg",
    "locale": "zh-TW",
    "timezone": "Asia/Tokyo",
    "birthday": "1992-05-15",
    "gender": "male",
    "role": "user",
    "badge": "silver",
    "completed_exchanges": 5,
    "verification_status": {
      "id_card": "verified",
      "video_intro": "verified"
    },
    "created_at": "2024-01-15T08:00:00Z",
    "settings": {
      "female_only_preference": false,
      "font_size": "normal"
    }
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`

---

### 4.2.2 PATCH /api/v1/users/me — 更新本人資料

**認證**: Bearer

**請求**:
```json
{
  "name": "佐藤健太郎 updated",
  "locale": "en",
  "timezone": "Asia/Taipei",
  "settings": {
    "female_only_preference": true,
    "font_size": "large"
  }
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| name | string | 2-50 字元 |
| locale | string | `zh-TW` 或 `en` |
| timezone | string | IANA timezone |
| settings | object | 使用者偏好設定 |

**回應 200**:
```json
{
  "data": {
    "user_id": "usr_a1b2c3",
    "name": "佐藤健太郎 updated",
    "locale": "en",
    "settings": {
      "female_only_preference": true,
      "font_size": "large"
    },
    "updated_at": "2024-06-10T12:00:00Z"
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `VALIDATION_ERROR`

---

### 4.2.3 POST /api/v1/users/me/avatar — 上傳頭像

**認證**: Bearer

**請求**: `multipart/form-data`

| 欄位 | 類型 | 說明 |
|------|------|------|
| file | file | JPG/PNG，最大 5MB，建議 400x400px |

**回應 201**:
```json
{
  "data": {
    "avatar_url": "https://cdn.example.com/avatars/usr_a1b2c3_1700.jpg",
    "avatar_thumb_url": "https://cdn.example.com/avatars/usr_a1b2c3_thumb.jpg"
  }
}
```

- 自動產生 200x200 thumbnail
- 舊頭像非同步刪除

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `INVALID_REQUEST`, `RATE_LIMIT_EXCEEDED`

---

### 4.2.4 GET /api/v1/users/me/skill-tags — 取得本人技能標籤

**認證**: Bearer

**回應 200**:
```json
{
  "data": {
    "teaching_skills": [
      { "tag_id": "tag_jp_conv", "name": "日文會話", "level": "native", "is_primary": true },
      { "tag_id": "tag_jp_gram", "name": "日文文法", "level": "native", "is_primary": false }
    ],
    "learning_skills": [
      { "tag_id": "tag_cn_conv", "name": "中文會話", "level": "intermediate" },
      { "tag_id": "tag_cn_lis", "name": "中文聽力", "level": "intermediate" }
    ]
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`

---

## 4.3 /matchings/* — 配對相關 (4 個端點)

### 4.3.1 GET /api/v1/matchings — 取得配對清單

**認證**: Bearer

**查詢參數**:

| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| cursor | string | - | 分頁游標 |
| limit | integer | 20 | 每頁數量 (最大 100) |
| status | string | all | `pending` / `confirmed` / `skipped` / `all` |
| sort | string | created_at:desc | 排序 |

**回應 200**:
```json
{
  "data": [
    {
      "matching_id": "mat_x1y2z3",
      "other_user": {
        "user_id": "usr_d4e5f6",
        "name": "小美",
        "avatar_url": "https://cdn.example.com/avatars/usr_d4e5f6.jpg",
        "badge": "silver"
      },
      "complementary_skills": {
        "i_will_teach": "日文會話",
        "i_will_learn": "Photoshop"
      },
      "match_score": 85,
      "status": "pending",
      "created_at": "2024-06-01T10:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6MTJ9",
    "has_more": true,
    "total_count": 12
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `INVALID_REQUEST`

---

### 4.3.2 POST /api/v1/matchings/{matching_id}/confirm — 確認配對

**認證**: Bearer

**路徑參數**: `matching_id` (string)

**請求**:
```json
{
  "message": "您好，我想跟您交換技能！"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| message | string | 否 | 附加訊息 (最多 200 字) |

**回應 200**:
```json
{
  "data": {
    "matching_id": "mat_x1y2z3",
    "status": "confirmed",
    "order_id": "ord_abc123",
    "confirmed_at": "2024-06-10T12:00:00Z"
  }
}
```

- 確認後自動建立訂單 (Order)
- 雙方都確認後狀態變為 `confirmed`
- 任一方超過 48 小時未確認，自動過期

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `PERMISSION_DENIED`, `VALIDATION_ERROR`

---

### 4.3.3 POST /api/v1/matchings/weekly-digest — 取得每週配對摘要

**認證**: Bearer

**回應 200**:
```json
{
  "data": {
    "week_start": "2024-06-03",
    "week_end": "2024-06-09",
    "top_matches": [
      {
        "matching_id": "mat_new1",
        "other_user": {
          "user_id": "usr_new1",
          "name": "阿哲",
          "badge": "gold"
        },
        "complementary_skills": {
          "i_will_teach": "Python",
          "i_will_learn": "日文會話"
        },
        "match_score": 92
      },
      {
        "matching_id": "mat_new2",
        "other_user": {
          "user_id": "usr_new2",
          "name": "Lily",
          "badge": "silver"
        },
        "complementary_skills": {
          "i_will_teach": "英文寫作",
          "i_will_learn": "書法"
        },
        "match_score": 78
      }
    ],
    "notification_sent_at": "2024-06-10T09:00:00Z"
  }
}
```

- 每週一 09:00 主動推播 (Push Notification + Email)
- 此端點為「手動取得」用 (網頁版手動刷新)

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`

---

### 4.3.4 POST /api/v1/matchings/{matching_id}/skip — 跳過配對

**認證**: Bearer

**路徑參數**: `matching_id` (string)

**請求**:
```json
{
  "reason": "時間不匹配"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| reason | string | 否 | 跳過原因 (用於改進演算法) |

**回應 200**:
```json
{
  "data": {
    "matching_id": "mat_x1y2z3",
    "status": "skipped",
    "skipped_at": "2024-06-10T12:00:00Z"
  }
}
```

- 跳過後不會再出現在配對清單
- 不影響雙方的其他配對

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `PERMISSION_DENIED`

---

## 4.4 /orders/* — 課程預約相關 (5 個端點)

### 4.4.1 POST /api/v1/orders — 建立預約

**認證**: Bearer

**請求**:
```json
{
  "matching_id": "mat_x1y2z3",
  "scheduled_at": "2024-06-15T19:00:00+08:00",
  "duration_minutes": 60,
  "location_type": "online",
  "location_detail": "https://meet.example.com/abc123",
  "notes": "希望從基礎開始"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| matching_id | string | 是 | 配對 ID |
| scheduled_at | string | 是 | ISO 8601 datetime |
| duration_minutes | integer | 是 | 30 / 60 / 90 |
| location_type | string | 是 | `online` / `offline` |
| location_detail | string | 否 | 視訊連結或地址 |
| notes | string | 否 | 備註 (最多 500 字) |

**回應 201**:
```json
{
  "data": {
    "order_id": "ord_abc123",
    "matching_id": "mat_x1y2z3",
    "teacher": {
      "user_id": "usr_a1b2c3",
      "name": "佐藤健太郎"
    },
    "student": {
      "user_id": "usr_d4e5f6",
      "name": "小美"
    },
    "scheduled_at": "2024-06-15T19:00:00+08:00",
    "duration_minutes": 60,
    "points_cost": {
      "from_teacher": 1.5,
      "from_student": 1.0
    },
    "location_type": "online",
    "status": "pending",
    "cancellation_policy": {
      "before_24h": "免費取消",
      "24h_to_1h": "扣 50%",
      "within_1h": "扣 100%"
    },
    "created_at": "2024-06-10T12:00:00Z"
  }
}
```

- 建立時自動凍結雙方點數
- 課程開始 24h 前免費取消，24h~1h 扣 50%，< 1h 扣 100%

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `VALIDATION_ERROR`, `RATE_LIMIT_EXCEEDED`

---

### 4.4.2 GET /api/v1/orders — 取得預約清單

**認證**: Bearer

**查詢參數**:

| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| cursor | string | - | 分頁游標 |
| limit | integer | 20 | 每頁數量 |
| status | string | all | `pending` / `confirmed` / `completed` / `cancelled` / `all` |
| role | string | all | `teacher` / `student` / `all` |
| from | string | - | 起始日期 (YYYY-MM-DD) |
| to | string | - | 結束日期 (YYYY-MM-DD) |

**回應 200**:
```json
{
  "data": [
    {
      "order_id": "ord_abc123",
      "teacher": { "user_id": "usr_a1b2c3", "name": "佐藤健太郎" },
      "student": { "user_id": "usr_d4e5f6", "name": "小美" },
      "scheduled_at": "2024-06-15T19:00:00+08:00",
      "duration_minutes": 60,
      "status": "pending",
      "points_cost": 1.5,
      "location_type": "online"
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6MTJ9",
    "has_more": false,
    "total_count": 5
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `INVALID_REQUEST`

---

### 4.4.3 GET /api/v1/orders/{order_id} — 取得單筆預約

**認證**: Bearer

**路徑參數**: `order_id` (string)

**回應 200**:
```json
{
  "data": {
    "order_id": "ord_abc123",
    "matching_id": "mat_x1y2z3",
    "teacher": {
      "user_id": "usr_a1b2c3",
      "name": "佐藤健太郎",
      "avatar_url": "https://cdn.example.com/avatars/usr_a1b2c3.jpg",
      "badge": "silver"
    },
    "student": {
      "user_id": "usr_d4e5f6",
      "name": "小美",
      "avatar_url": "https://cdn.example.com/avatars/usr_d4e5f6.jpg",
      "badge": "gold"
    },
    "scheduled_at": "2024-06-15T19:00:00+08:00",
    "duration_minutes": 60,
    "points_cost": {
      "from_teacher": 1.5,
      "from_student": 1.0
    },
    "location_type": "online",
    "location_detail": "https://meet.example.com/abc123",
    "notes": "希望從基礎開始",
    "status": "pending",
    "escrow_status": "frozen",
    "cancellation_policy": {
      "before_24h": "免費取消",
      "24h_to_1h": "扣 50%",
      "within_1h": "扣 100%"
    },
    "created_at": "2024-06-10T12:00:00Z"
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `PERMISSION_DENIED`

---

### 4.4.4 POST /api/v1/orders/{order_id}/cancel — 取消預約

**認證**: Bearer

**路徑參數**: `order_id` (string)

**請求**:
```json
{
  "reason": "臨時有事無法參加"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| reason | string | 否 | 取消原因 |

**回應 200**:
```json
{
  "data": {
    "order_id": "ord_abc123",
    "status": "cancelled",
    "cancellation": {
      "cancelled_by": "teacher",
      "points_refunded": 0.75,
      "points_charged": 0.75,
      "cancelled_at": "2024-06-14T20:00:00Z"
    }
  }
}
```

- 根據取消時間計算退款比例
- 24h 前: 100% 退款
- 24h~1h: 50% 退款
- < 1h: 0% 退款

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `PERMISSION_DENIED`, `VALIDATION_ERROR`

---

### 4.4.5 POST /api/v1/orders/{order_id}/confirm-complete — 確認課程完成

**認證**: Bearer

**路徑參數**: `order_id` (string)

**請求**:
```json
{
  "rating": 5,
  "comment": "老師很專業，課程很充實！"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| rating | integer | 是 | 1-5 星 |
| comment | string | 否 | 評論 (最多 500 字) |

**回應 200**:
```json
{
  "data": {
    "order_id": "ord_abc123",
    "status": "completed",
    "escrow_released": true,
    "points_transferred": 1.5,
    "review": {
      "rating": 5,
      "comment": "老師很專業，課程很充實！"
    },
    "completed_at": "2024-06-15T20:00:00Z"
  }
}
```

- 課程結束後 24h 內未確認，自動視為完成 (預設撥款)
- 雙向評分後更新雙方徽章

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `PERMISSION_DENIED`, `VALIDATION_ERROR`

---

## 4.5 /reviews/* — 評價相關 (3 個端點)

### 4.5.1 POST /api/v1/reviews — 建立評價

**認證**: Bearer

**請求**:
```json
{
  "order_id": "ord_abc123",
  "rating": 5,
  "comment": "老師很專業，課程很充實！",
  "tags": ["專業", "時間準時", "內容充實"]
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| order_id | string | 是 | 訂單 ID |
| rating | integer | 是 | 1-5 |
| comment | string | 否 | 評論 (最多 500 字) |
| tags | string[] | 否 | 預設標籤: `專業` / `時間準時` / `內容充實` / `淺顯易懂` / `收穫很多` |

**回應 201**:
```json
{
  "data": {
    "review_id": "rev_123",
    "order_id": "ord_abc123",
    "from_user_id": "usr_a1b2c3",
    "to_user_id": "usr_d4e5f6",
    "rating": 5,
    "comment": "老師很專業，課程很充實！",
    "tags": ["專業", "時間準時", "內容充實"],
    "created_at": "2024-06-15T20:30:00Z"
  }
}
```

- 雙盲評價 (雙方看不到對方的評價，直到雙方都完成評價)
- 評價後不可修改

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `ALREADY_EXISTS`, `VALIDATION_ERROR`

---

### 4.5.2 GET /api/v1/reviews — 取得評價清單

**認證**: Bearer

**查詢參數**:

| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| cursor | string | - | 分頁游標 |
| limit | integer | 20 | 每頁數量 |
| order_id | string | - | 篩選特定訂單 |
| from_user_id | string | - | 篩選評價來源 |

**回應 200**:
```json
{
  "data": [
    {
      "review_id": "rev_123",
      "order_id": "ord_abc123",
      "from_user": { "user_id": "usr_a1b2c3", "name": "佐藤健太郎" },
      "rating": 5,
      "comment": "老師很專業，課程很充實！",
      "tags": ["專業", "時間準時"],
      "created_at": "2024-06-15T20:30:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6MTJ9",
    "has_more": false,
    "total_count": 3
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `INVALID_REQUEST`

---

### 4.5.3 GET /api/v1/reviews/by-user/{user_id} — 取得特定用戶的評價

**認證**: Bearer

**路徑參數**: `user_id` (string)

**查詢參數**:

| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| cursor | string | - | 分頁游標 |
| limit | integer | 20 | 每頁數量 |

**回應 200**:
```json
{
  "data": {
    "user_id": "usr_d4e5f6",
    "average_rating": 4.7,
    "total_reviews": 15,
    "reviews": [
      {
        "review_id": "rev_123",
        "from_user": { "user_id": "usr_a1b2c3", "name": "佐藤健太郎" },
        "rating": 5,
        "comment": "老師很專業，課程很充實！",
        "tags": ["專業", "時間準時"],
        "created_at": "2024-06-15T20:30:00Z"
      }
    ]
  },
  "pagination": {
    "next_cursor": "eyJpZCI6MTJ9",
    "has_more": false,
    "total_count": 15
  }
}
```

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`

---

## 4.6 /media/* — 媒體上傳相關 (3 個端點)

### 4.6.1 POST /api/v1/media/upload-id-card — 上傳身份證件

**認證**: Bearer

**請求**: `multipart/form-data`

| 欄位 | 類型 | 說明 |
|------|------|------|
| file | file | JPG/PNG/PDF，最大 10MB |
| document_type | string | `id_card` / `passport` |

**回應 201**:
```json
{
  "data": {
    "media_id": "med_idcard_001",
    "status": "pending_review",
    "uploaded_at": "2024-06-10T12:00:00Z",
    "review_result": null
  }
}
```

- 上傳後 5 分鐘內 AI 審查完成
- 審查通過後狀態變為 `verified`
- 原始檔案 30 分鐘後自動刪除 (只留 hash + 遮罩號)
- 請參考 architecture-step1-2.md §1.5 盲點 1 的預設建議

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `INVALID_REQUEST`, `RATE_LIMIT_EXCEEDED`

---

### 4.6.2 POST /api/v1/media/upload-video — 上傳影片自介

**認證**: Bearer

**請求**: `multipart/form-data`

| 欄位 | 類型 | 說明 |
|------|------|------|
| file | file | MP4，最大 50MB |
| self_rating | string | `beginner` / `elementary` / `intermediate` / `advanced` / `expert` |

**回應 201**:
```json
{
  "data": {
    "media_id": "med_video_001",
    "video_url": "https://cdn.example.com/videos/usr_a1b2c3_intro.mp4",
    "thumbnail_url": "https://cdn.example.com/videos/usr_a1b2c3_intro_thumb.jpg",
    "duration_seconds": 15,
    "self_rating": "intermediate",
    "status": "processing",
    "liveness_check": "pending"
  }
}
```

- 影片自動轉碼 (H.264, 720p)
- 自動截圖第一幔作為 thumbnail
- 30 天限制上傳 1 次 (請參考 PRD §3.1 F5)

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `INVALID_REQUEST`, `RATE_LIMIT_EXCEEDED`, `ALREADY_EXISTS`

---

### 4.6.3 POST /api/v1/media/liveness-check — 活體檢測

**認證**: Bearer

**請求**:
```json
{
  "media_id": "med_video_001"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| media_id | string | 是 | 影片 ID |

**回應 200**:
```json
{
  "data": {
    "media_id": "med_video_001",
    "liveness_result": {
      "passed": true,
      "confidence": 0.95,
      "checked_at": "2024-06-10T12:05:00Z"
    },
    "status": "verified"
  }
}
```

- 請參考 architecture-step1-2.md §1.5 盲點 3 的預設建議 (第三方 SDK)
- 重錄機制:最多可重錄 5 次

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `NOT_FOUND`, `VALIDATION_ERROR`

---

## 4.7 /points/* — 點數相關 (2 個端點)

### 4.7.1 GET /api/v1/points/balance — 取得點數餘額

**認證**: Bearer

**回應 200**:
```json
{
  "data": {
    "user_id": "usr_a1b2c3",
    "balance": 25.5,
    "frozen": 1.5,
    "available": 24.0,
    "currency": "points",
    "last_updated": "2024-06-10T12:00:00Z"
  }
}
```

| 欄位 | 說明 |
|------|------|
| balance | 總點數 |
| frozen | 冻结中 (已預約未完成) |
| available | 可用點數 (balance - frozen) |

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`

---

### 4.7.2 GET /api/v1/points/ledger — 取得點數流水帳

**認證**: Bearer

**查詢參數**:

| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| cursor | string | - | 分頁游標 |
| limit | integer | 20 | 每頁數量 |
| type | string | all | `earned` / `frozen` / `released` / `refunded` / `charged` / `all` |
| from | string | - | 起始日期 |
| to | string | - | 結束日期 |

**回應 200**:
```json
{
  "data": [
    {
      "entry_id": "ple_001",
      "type": "frozen",
      "amount": -1.5,
      "balance_after": 24.0,
      "order_id": "ord_abc123",
      "description": "預約課程凍結",
      "created_at": "2024-06-10T12:00:00Z"
    },
    {
      "entry_id": "ple_002",
      "type": "released",
      "amount": 1.5,
      "balance_after": 25.5,
      "order_id": "ord_abc123",
      "description": "課程完成，點數已撥款",
      "created_at": "2024-06-15T20:30:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6MTJ9",
    "has_more": false,
    "total_count": 45
  }
}
```

- 每筆交易都有審計 log (請參考 NFR §1.3 可維運)
- 支援對帳

**錯誤碼**: `UNAUTHORIZED`, `TOKEN_EXPIRED`, `INVALID_REQUEST`

---

# §5 WebSocket 規格

## 5.1 連線端點

| 端點 | 協定的 | 說明 |
|------|--------|------|
| `wss://api.example.com/ws/chat` | WebSocket | 配對成功後的即時通訊 |

## 5.2 連線認證

```javascript
// 連線時帶上 access_token
const ws = new WebSocket('wss://api.example.com/ws/chat?token=eyJhbGciOiJIUzI1NiJ9...');

// 連線成功後 5 秒內需驗證
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

- 驗證失敗時，伺服器主動關閉連線 (1008 Policy Violation)
- Token 過期時，發送 `{"type": "token_expired"}`，client 需重新連線

## 5.3 訊息格式

### 5.3.1 發送文字訊息

```json
// Client → Server
{
  "type": "message",
  "conversation_id": "conv_abc123",
  "content": "您好，我想預約明天的課程",
  "client_msg_id": "msg_client_001"
}
```

```json
// Server → Client (確認送達)
{
  "type": "message_ack",
  "server_msg_id": "msg_srv_001",
  "client_msg_id": "msg_client_001",
  "timestamp": "2024-06-10T12:00:00Z"
}
```

### 5.3.2 接收訊息

```json
// Server → Client
{
  "type": "message",
  "server_msg_id": "msg_srv_001",
  "conversation_id": "conv_abc123",
  "from_user": {
    "user_id": "usr_d4e5f6",
    "name": "小美"
  },
  "content": "好的，我看一下行事曆",
  "timestamp": "2024-06-10T12:01:00Z"
}
```

### 5.3.3 已讀確認

```json
// Client → Server
{
  "type": "read",
  "conversation_id": "conv_abc123",
  "read_until_msg_id": "msg_srv_001"
}
```

### 5.3.4 對方已讀

```json
// Server → Client
{
  "type": "read_receipt",
  "conversation_id": "conv_abc123",
  "read_by": "usr_d4e5f6",
  "read_until_msg_id": "msg_srv_001"
}
```

### 5.3.5 課程開始通知

```json
// Server → Client
{
  "type": "session_start",
  "order_id": "ord_abc123",
  "scheduled_at": "2024-06-15T19:00:00+08:00",
  "duration_minutes": 60,
  "location": {
    "type": "online",
    "url": "https://meet.example.com/abc123"
  }
}
```

### 5.3.6 配對成功通知

```json
// Server → Client
{
  "type": "matching_confirmed",
  "matching_id": "mat_x1y2z3",
  "other_user": {
    "user_id": "usr_d4e5f6",
    "name": "小美"
  }
}
```

## 5.4 心跳機制

```json
// Client → Server (每 30 秒)
{
  "type": "ping"
}

// Server → Client
{
  "type": "pong"
}
```

- 60 秒無心跳回應，伺服器主動斷開連線
- 斷線後 client 自動重連 (指數退避，最大 5 次)

## 5.5 錯誤訊息

```json
{
  "type": "error",
  "code": "MESSAGE_TOO_LONG",
  "message": "訊息內容過長，最多 1000 字元"
}
```

| 錯誤碼 | 說明 |
|--------|------|
| `UNAUTHORIZED` | 未認證或 token 無效 |
| `TOKEN_EXPIRED` | access_token 過期 |
| `MESSAGE_TOO_LONG` | 訊息內容超過 1000 字元 |
| `CONVERSATION_NOT_FOUND` | 對話不存在 |
| `RATE_LIMIT_EXCEEDED` | 發送頻率過高 |

---

# §6 給工程師的 1 小時寫第一個 Endpoint SOP

> 本節提供「1 小時內從零到第一個 endpoint 上線」的步驟指引。

## 目標

完成第一個可運作的 API endpoint (以 `POST /auth/register` 為例)，包含:
- 本地開發環境
- 資料庫 Migration
- 程式碼 scaffold
- 測試案例
- Deploy 確認

## 時間分配 (60 分鐘)

| 階段 | 時間 | 交付物 |
|------|------|--------|
| 環境確認 | 5 分鐘 | 本地端可以跑 `npm run dev` |
| 資料庫 Migration | 10 分鐘 | `users` 資料表建立完成 |
| Scaffold Endpoint | 15 分鐘 | 空的 route handler |
| 實作商業邏輯 | 20 分鐘 | 完整的 register 邏輯 |
| 測試 | 8 分鐘 | 至少 3 個測試案例 |
| Deploy 確認 | 2 分鐘 | 確認 CI/CD 正常 |

---

## Step 1: 環境確認 (5 分鐘)

### 1.1 確認必要工具

```bash
# 檢查 Node.js 版本 (需要 18+)
node --version  # 預期: v18.x.x 或更高

# 檢查 npm 版本
npm --version   # 預期: 9.x.x

# 檢查 Docker (若使用本地 Postgres)
docker --version

# 檢查 git
git --version
```

### 1.2 複製並設定環境變數

```bash
# 複製範例環境變數檔案
cp .env.example .env.local

# 編輯 .env.local，確認以下變數
cat .env.local
# DATABASE_URL=postgresql://user:password@localhost:5432/skill_exchange
# JWT_SECRET=your-super-secret-key-at-least-256-bits
# NODE_ENV=development
```

### 1.3 啟動本地服務

```bash
# 啟動資料庫 (若使用 Docker Compose)
docker-compose up -d db

# 確認服務正常
npm run dev
# 預期: Server running on http://localhost:3000
```

---

## Step 2: 資料庫 Migration (10 分鐘)

### 2.1 建立 Migration 檔案

```bash
# 使用 Prisma (建議) 或其他 ORM
npx prisma migrate dev --name create_users_table
```

### 2.2 確認 Schema

```prisma
// prisma/schema.prisma
model User {
  id            String    @id @default(uuid())
  email         String    @unique
  password      String    // hashed
  name          String
  locale        String    @default("zh-TW")
  timezone      String    @default("Asia/Taipei")
  role          String    @default("user")
  badge         String    @default("none")
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
}
```

### 2.3 執行並確認

```bash
# 執行 migration
npx prisma migrate dev --name create_users_table

# 確認資料表建立
npx prisma studio
# 預期: 看到 users 資料表
```

---

## Step 3: Scaffold Endpoint (15 分鐘)

### 3.1 建立 Route Handler

```typescript
// src/app/api/v1/auth/register/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    // TODO: 實作商業邏輯
    return NextResponse.json({ message: 'TODO' }, { status: 501 })
  } catch (error) {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: '伺服器錯誤' } },
      { status: 500 }
    )
  }
}
```

### 3.2 測試空殼

```bash
# 啟動伺服器
npm run dev

# 測試端點
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{}'

# 預期: 501 Not Implemented
```

---

## Step 4: 實作商業邏輯 (20 分鐘)

### 4.1 實作 Register Endpoint

```typescript
// src/app/api/v1/auth/register/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import bcrypt from 'bcrypt'
import { sign } from 'jsonwebtoken'

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).regex(/[A-Z]/).regex(/[0-9]/),
  name: z.string().min(2).max(50),
  locale: z.enum(['zh-TW', 'en']),
  timezone: z.string(),
})

export async function POST(request: NextRequest) {
  try {
    // 1. 解析並驗證請求
    const body = await request.json()
    const validation = registerSchema.safeParse(body)
    
    if (!validation.success) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: '請求參數驗證失敗', details: validation.error } },
        { status: 422 }
      )
    }
    
    const { email, password, name, locale, timezone } = validation.data
    
    // 2. 檢查 email 是否已存在
    const existing = await prisma.user.findUnique({ where: { email } })
    if (existing) {
      return NextResponse.json(
        { error: { code: 'ALREADY_EXISTS', message: '此 email 已被註冊' } },
        { status: 409 }
      )
    }
    
    // 3. 密碼 hash
    const hashedPassword = await bcrypt.hash(password, 12)
    
    // 4. 建立使用者
    const user = await prisma.user.create({
      data: {
        email,
        password: hashedPassword,
        name,
        locale,
        timezone,
      }
    })
    
    // 5. 產生 JWT
    const accessToken = sign(
      { sub: user.id, user_id: user.id, role: user.role },
      process.env.JWT_SECRET!,
      { expiresIn: '15m' }
    )
    
    // 6. 回應
    return NextResponse.json(
      {
        data: {
          user_id: user.id,
          email: user.email,
          name: user.name,
          access_token: accessToken,
          expires_in: 900
        }
      },
      { status: 201 }
    )
    
  } catch (error) {
    console.error('[register error]', error)
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: '伺服器錯誤' } },
      { status: 500 }
    )
  }
}
```

### 4.2 新增依賴

```bash
npm install zod bcrypt jsonwebtoken
npm install -D @types/bcrypt @types/jsonwebtoken
```

---

## Step 5: 測試 (8 分鐘)

### 5.1 建立測試檔案

```typescript
// src/app/api/v1/auth/register.test.ts
import { describe, it, expect } from 'vitest'

describe('POST /api/v1/auth/register', () => {
  it('應正確處理有效請求', async () => {
    const response = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'test@example.com',
        password: 'SecurePass123',
        name: '測試使用者',
        locale: 'zh-TW',
        timezone: 'Asia/Taipei'
      })
    })
    
    expect(response.status).toBe(201)
    const data = await response.json()
    expect(data.data).toHaveProperty('user_id')
    expect(data.data).toHaveProperty('access_token')
  })
  
  it('應拒绝無效 email', async () => {
    const response = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'invalid-email',
        password: 'SecurePass123',
        name: '測試',
        locale: 'zh-TW',
        timezone: 'Asia/Taipei'
      })
    })
    
    expect(response.status).toBe(422)
  })
  
  it('應拒绝已存在的 email', async () => {
    // 先建立一個使用者
    await fetch('/api/v1/auth/register', { ... })
    
    // 嘗試重複註冊
    const response = await fetch('/api/v1/auth/register', { ... })
    expect(response.status).toBe(409)
  })
})
```

### 5.2 執行測試

```bash
npm test
# 預期: 3 passing tests
```

---

## Step 6: Deploy 確認 (2 分鐘)

### 6.1 確認 CI/CD 正常

```bash
# 確認 GitHub Actions 或其他 CI 正常
git push origin main
# 觀察 CI pipeline 是否通過
```

### 6.2 確認環境變數設定

在正式環境 (Vercel / Railway / etc.) 設定:
- `DATABASE_URL`
- `JWT_SECRET`
- `NODE_ENV=production`

---

## 自檢清單

完成後，確認以下項目:

- [ ] `POST /api/v1/auth/register` 回應 201 且包含 `user_id` + `access_token`
- [ ] 無效 email 回應 422
- [ ] 重复 email 回應 409
- [ ] 密碼未正確 hash (資料庫中是 bcrypt hash，不是明文)
- [ ] JWT 可以用來訪問 `/api/v1/users/me`
- [ ] 所有測試通過
- [ ] CI pipeline 通過

---

## 參考資源

| 資源 | 連結 |
|------|------|
| Next.js App Router 文件 | https://nextjs.org/docs/app |
| Prisma 文件 | https://prisma.io/docs |
| Zod 驗證庫 | https://zod.dev |
| JWT 實作範例 | https://jwt.io/introduction |
| 本專案 API Spec | 本文件的 §4 |

---

**API 規格書完成**

---

## §6 給 engineering-lead 的「1 小時上手 checklist」

- [ ] 看完 §1 認證機制能在 middleware 內實作 JWT 驗證(10 分鐘)
- [ ] 看完 §2 共用規範能在 Fastify / Express 加 middleware(10 分鐘)
- [ ] 看完 §3 錯誤碼總表能建 exception class hierarchy(10 分鐘)
- [ ] 看完 §4 端點清單能在 OpenAPI Generator 跑出 client SDK(20 分鐘)
- [ ] 看完 §5 WebSocket 能選擇合適的 library(5 分鐘)
- [ ] 看完能在 1 小時內開始寫第一個 endpoint(POST /auth/register)

## §7 自我審查

- [x] 25+ 個端點都有 Method + Path + 認證 + 請求/回應/錯誤碼
- [x] 認證機制在 §1 完整描述(包括 refresh + logout)
- [x] 共用規範(分頁/排序/篩選/限流/版本)都有
- [x] 錯誤碼總表覆蓋所有 4xx / 5xx 場景
- [x] WebSocket 有完整訊息格式 + 心跳
