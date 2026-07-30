### line-bot-02 LINE Bot Webhook Server 部署架構抉擇
**Created**: Cycle 561, 2026-07-30
**Type**: D3-learn (實作型)
**Validated by**: Phase 1 external核查（school-bulletin專案）、LINE Developers Docs
**Gap**: LINE Bot Messaging API webhook 需要公開可達的 HTTPS endpoint，但 Hermes 主機位於家庭網路 NAT 之後

---

## 背景

**學校公告系統 LINE Bot 整合現況**：
- `~/permanent-projects/school-bulletin/` — 無任何 LINE Bot 程式碼（0 Python LINE files, 0 LINE API routes）
- `school-bulletin-system/SKILL.md` — LINE Bot 整合計畫已識別但未實作
- `trial-and-error/by-category/line-bot-sdk-v3-fastapi-patterns-20260730.md` — SDK v3 模式已文檔化
- `trial-and-error/by-category/line-webhook-signature-verification-20260719.md` — 簽名驗證已文檔化

**缺口本質**：不是 LINE API 知識不足，而是**部署架構**——LINE Platform 必須能回呼 Hermes 主機，但家庭網路沒有公開 IP。

---

## Webhook Server 部署選項分析

### 選項 1：Cloudflare Tunnel（推薦）
```
LINE Platform → Cloudflare Tunnel → localhost:8000 webhook server
```
| 面向 | 評估 |
|------|------|
| 費用 | 免費（Cloudflare Tunnel 免費方案）|
| 穩定性 | ✅ 穩定，長期執行 |
| HTTPS | ✅ 自動 HTTPS，LINE 要求 |
| 設定難度 | 中（需要 Cloudflare 帳號 + tunnel daemon）|
| 啟動方式 | `cloudflared tunnel run --token <token>` |
| 斷線復原 | 需要 systemd service 或 supervisor |

**驗證命令**：
```bash
cloudflared --version  # 確認已安裝
cloudflared tunnel list  # 確認有可用 tunnel
```

### 選項 2：ngrok
```
LINE Platform → ngrok → localhost:8000 webhook server
```
| 面向 | 評估 |
|------|------|
| 費用 | 免費（3 個 concurrent tunnels）|
| 穩定性 | ⚠️ 免費版 IP 會變，重啟後 URL 需更新 LINE Console |
| HTTPS | ✅ 自動 HTTPS |
| 設定難度 | 低 |
| 生產不推薦 | URL 每次重啟都變，LINE Console 要手動更新 |

### 選項 3：Vercel Python 獨立服務
```
學校公告 Next.js (vercel) → Vercel Python function 處理 LINE webhook
```
| 面向 | 評估 |
|------|------|
| 費用 | 免費（Hobby 方案）|
| 整合性 | ✅ 與現有 Vercel 部署一致 |
| 穩定性 | ✅ Vercel 負責基礎設施 |
| 缺點 | 需要將 LINE Bot SDK Python 整合進 Vercel |

### 選項 4：Supabase Edge Functions + LINE Bot SDK
```
LINE Platform → Supabase Edge Functions → Supabase DB → 通知全校
```
| 面向 | 評估 |
|------|------|
| 費用 | 免費（Supabase 免費方案）|
| 穩定性 | ✅ Supabase 託管 |
| 缺點 | Edge Functions 是 JavaScript/TypeScript，LINE Bot SDK 是 Python |

---

## LINE Bot Webhook 整合的正確模式

### FastAPI Webhook Handler（完整可用的模式）
```python
from fastapi import FastAPI, Request, HTTPException, Header
import hmac
import hashlib
import json
from contextlib import asynccontextmanager

LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]

# 注意：LINE 要求 raw body，FastAPI 需要特別處理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 紀錄 webhook 已就緒
    print("LINE Bot webhook server started")
    yield
    # Shutdown
    print("LINE Bot webhook server stopped")

app = FastAPI(lifespan=lifespan)

async def verify_line_signature(body: bytes, signature: str) -> bool:
    """LINE X-LINE-Signature 驗證（HMAC-SHA256 + timing-safe）"""
    expected = hmac.new(
        LINE_CHANNEL_SECRET.encode(),
        body,
        hashlib.sha256
    ).digest()
    return hmac.compare_digest(expected, signature.encode())

@app.post("/webhook/line")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None, alias="x-line-signature")
):
    # ⚠️ 必須取 raw body（LINE 驗證要求字元完全一致）
    body = await request.body()
    
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-LINE-Signature")
    
    if not await verify_line_signature(body, x_line_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # 現在可以安全地 parse JSON
    events = json.loads(body)
    
    for event in events.get("events", []):
        if event["type"] == "message":
            user_id = event["source"]["userId"]
            # ... 處理訊息
    
    return {"status": "ok"}
```

### 觸發通知時（FastAPI route handler 中）：
```python
from linebot import ApiClient, Configuration, MessagingApi, PushMessageRequest, TextMessage

@app.post("/api/announcements")
async def create_announcement(...):
    # ... 建立公告 logic ...
    
    # 觸發 LINE 通知（使用 multicast 而非 broadcast）
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        # 查詢所有家長/師生的 LINE user_id
        user_ids = await db.fetch(
            "SELECT line_user_id FROM user_role_assignments "
            "WHERE role IN ('parent', 'student') AND line_user_id IS NOT NULL"
        )
        if user_ids:
            line_bot_api.multicast(
                [u["line_user_id"] for u in user_ids],
                [TextMessage(text=f"📢 新公告：{title}\n{summary}")]
            )
    
    return {"id": announcement_id}
```

---

## If→Then 規則

**If** 要將 LINE Bot 整合進學校公告系統但主機沒有公開 IP，**then** 選擇 Cloudflare Tunnel 方案（穩定、長期執行），不要用 ngrok 免費版（URL 每次變更），因為 LINE Console 的 Webhook URL 需要手動更新：

```bash
# Cloudflare Tunnel 啟動（一次性設定）
cloudflared tunnel run --token <YOUR_TUNNEL_TOKEN>

# 驗證 tunnel 狀態
cloudflared tunnel list
curl https://<tunnel-subdomain>.trycloudflare.com/health

# LINE Console webhook URL 設定為：
# https://<tunnel-subdomain>.trycloudflare.com/webhook/line
```

**If** LINE webhook 驗證失敗（401），**then** 首先確認是否在 `request.body()` 之前就先做了 `json.loads()`——LINE 要求 raw body 字元完全一致才能驗證簽名：

```python
# ❌ 錯誤：先 parse 再驗證（body 被改變）
body_json = json.loads(await request.body())  # body 字元改變了
events = body_json["events"]

# ✅ 正確：先取 raw body 驗證，再 parse
body = await request.body()  # 先取 raw bytes
verify_signature(body, x_line_signature)  # 用原始 body 驗證
events = json.loads(body)  # 驗證通過後再 parse
```

---

## 驗證命令

```bash
# 1. 確認 FastAPI 可以啟動
cd ~/permanent-projects/school-bulletin
python3 -c "from fastapi import FastAPI; print('FastAPI OK')"

# 2. 確認 line-bot-sdk v3 安裝
python3 -c "from linebot import ApiClient, Configuration, MessagingApi; print('linebot v3 OK')"

# 3. 驗證 Cloudflare Tunnel 可達性（設定後）
curl -s https://<tunnel-subdomain>.trycloudflare.com/health

# 4. 驗證 LINE SDK v3 可正確處理 context manager
python3 -c "
from linebot import ApiClient, Configuration, MessagingApi
config = Configuration(access_token='test_token')
with ApiClient(config) as client:
    api = MessagingApi(client)
    print('context manager works')
"
```

---

## 資源連結

- LINE Messaging API Webhook：https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature
- Cloudflare Tunnel 免費方案：https://dash.cloudflare.com/
- line-bot-sdk v3（pip）：`pip install line-bot-sdk>=3.0.0`
