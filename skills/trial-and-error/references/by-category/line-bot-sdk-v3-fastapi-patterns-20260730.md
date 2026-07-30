# LINE Bot SDK v3 + FastAPI 整合模式
**建立時間**：2026-07-30, Cycle 560
**Skill gap**：school-bulletin-system 的 LINE 通知模組缺乏 v3 SDK + FastAPI 整合 SOP
**驗證狀態**：✅ 理論研究（SDK docs + GitHub examples/fastapi-echo）

---

## 核心洞察

### 1. SDK 安裝與版本
```bash
pip install line-bot-sdk  # v3.25.0 (2026-07-07), Python >= 3.10
```
**v3 與 v2.x 完全不相容**——所有 import 路徑、類別名稱、API 呼叫方式全部改寫。

### 2. 三層 import 結構（v3）
```python
from linebot.v3 import WebhookHandler          # webhook 事件處理
from linebot.v3.exceptions import InvalidSignatureError  # 例外處理
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,  # API 呼叫
    ReplyMessageRequest, PushMessageRequest,  # 請求模型
    TextMessage, FlexMessage, FlexContainer   # 訊息模型
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent  # 事件模型
```

### 3. ApiClient Configuration Pattern（必須）
```python
configuration = Configuration(access_token='YOUR_CHANNEL_ACCESS_TOKEN')

# ✅ 正確：每次 API 呼叫都用 context manager
with ApiClient(configuration) as api_client:
    line_bot_api = MessagingApi(api_client)
    line_bot_api.reply_message(reply_token=..., messages=[...])

# ❌ 錯誤：把 ApiClient 當成全域單例
api_client = ApiClient(configuration)  # 連線未正確關閉
```

### 4. FastAPI Webhook 端點（官方 examples/fastapi-echo）
```python
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError

app = FastAPI()
handler = WebhookHandler('YOUR_CHANNEL_SECRET')

@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get('X-Line-Signature', '')
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
async def handle_message(event: MessageEvent):
    # FastAPI 可用 async handler
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"收到：{event.message.text}")]
            )
        )
```

### 5. Reply vs Push vs Multicast
| 方法 | 用途 | 場景 |
|------|------|------|
| `reply_message()` | 回覆使用者訊息 | 互動式回覆（需 reply_token） |
| `push_message()` | 主動推播給單一 user | 系統主動通知 |
| `multicast()` | 推播給多位 user | 學校公告（家長清單） |
| `broadcast()` | 推播給所有好友 | ⚠️ 不建議學校用（無分眾） |

```python
# Push（單一用戶）
line_bot_api.push_message(
    PushMessageRequest(to="Uxxx111", messages=[TextMessage(text="有新公告")])
)

# Multicast（多用戶清單，學校場景首選）
line_bot_api.multicast(
    to=["Uxxx111", "Uxxx222", "Uxxx333"],  # 從 DB 撈取
    messages=[TextMessage(text=f"📢 {title}\n{summary}")]
)
```

### 6. Flex Message（美觀卡片）
```python
bubble_json = """{
  "type": "bubble",
  "body": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {"type": "text", "text": "📢 公告標題", "weight": "bold", "size": "lg"},
      {"type": "text", "text": "公告內容摘要...", "wrap": true}
    ]
  },
  "footer": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {"type": "button", "action": {"type": "uri", "label": "查看全文", "uri": "https://..."}}
    ]
  }
}"""

line_bot_api.push_message(
    PushMessageRequest(
        to="Uxxx111",
        messages=[FlexMessage(
            alt_text="有新公告，點我看詳情",
            contents=FlexContainer.from_json(bubble_json)
        )]
    )
)
```

### 7. WebhookHandler vs WebhookParser
```python
# WebhookHandler（裝飾器，適合簡單場景）
handler = WebhookHandler('CHANNEL_SECRET')
@handler.add(MessageEvent, message=TextMessageContent)
def handle(event): ...

# WebhookParser（手動解析，適合 FastAPI async 或複雜分流）
parser = WebhookParser('CHANNEL_SECRET')
events = parser.parse(body, signature)
# 手動分發到不同 handler
```

### 8. 錯誤處理模式
```python
from linebot.v3.exceptions import InvalidSignatureError, LineBotApiError

try:
    handler.handle(body, signature)
except InvalidSignatureError:
    raise HTTPException(status_code=400, detail="Invalid signature")
except LineBotApiError as e:
    # rate limit (429) 或 quota exceeded
    print(f"LINE API Error: {e.status_code} {e.message}")
```

---

## If→Then 經驗

**If** 要在 FastAPI 中整合 LINE Bot SDK v3，**then** 必須遵守 `ApiClient(configuration)` context manager 模式，每次 API 呼叫都在 `with` 區塊內執行：

```python
# ✅ 正確
with ApiClient(configuration) as api_client:
    line_bot_api = MessagingApi(api_client)
    line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[...]))

# ❌ 錯誤：外層宣告變數，視為全域單例（v2 習慣）
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)  # v3 不支援這種用法
```

**Why**：v3 SDK 的 `ApiClient` 內部管理 HTTP 連線生命週期，context manager 確保每次請求後正確釋放資源。全域單例模式在 v3 中會導致連線未正確關閉。

---

## 驗證命令
```bash
# 確認 SDK 版本
python3 -c "import linebot; print(linebot.__version__)"

# 確認 FastAPI example 存在
python3 -c "from linebot.v3 import WebhookHandler; print('WebhookHandler OK')"

# 確認 Python 版本（需 >= 3.10）
python3 --version

# 本地測試（需 CHANNEL_ACCESS_TOKEN）
# 請勿在正式環境外洩 token
```

---

## 參考來源
- https://github.com/line/line-bot-sdk-python (v3.25.0, 2026-07-07)
- https://github.com/line/line-bot-sdk-python/blob/master/examples/fastapi-echo/
- https://developers.line.biz/en/docs/messaging-api/using-flex-messages/
- `school-bulletin-system/references/line-bot-messaging-v3-bulletin-notify-20260730.md`
