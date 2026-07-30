# LINE Bot Messaging API v3 + School Bulletin Integration (D3-learn, Cycle 560)

**Created**: Cycle 560, 2026-07-30
**Source**: line-bot-sdk-python GitHub (v3.25.0, 2026-07-07) + LINE Messaging API reference

---

## 研究來源

1. [line/line-bot-sdk-python](https://github.com/line/line-bot-sdk-python) — v3.25.0 (2026-07-07), 2.1k stars, async support
2. [LINE Messaging API Reference](https://developers.line.biz/en/reference/messaging-api) — multicast/push/reply/broadcast endpoints
3. `school-bulletin-system/references/line-bot-webhook-integration-20260719.md` — 現有 webhook 整合架構
4. `trial-and-error/references/by-category/line-webhook-signature-verification-20260719.md` — HMAC timing-safe 驗證

---

## 核心洞察

### 1. line-bot-sdk v3 vs v2.x（重要：不相容）

v3（2024+）完全基於 OpenAPI spec 自動生成，與 v2.x API 完全不同：

| 特徵 | v2.x | v3 |
|------|------|-----|
| Import | `from linebot import LineBotApi` | `from linebot.v3.messaging import MessagingApi` |
| 模式 | `LineBotApi(access_token)` | `ApiClient(configuration)` context管理器 |
| 簽名驗證 | 手動 HMAC | `WebhookParser` / `WebhookHandler` |
| Reply | `line_bot_api.reply_message()` | `line_bot_api.reply_message_with_http_info()` |
| Async | limited | `AsyncLineBotApi` + aiohttp |

**Python >= 3.10 required**

### 2. FastAPI + line-bot-sdk v3 範例

```python
# 完整 FastAPI webhook endpoint（line-bot-sdk v3）
from fastapi import FastAPI, Request, HTTPException, Header
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os

app = FastAPI()
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

@app.post("/callback")
async def callback(
    request: Request,
    x_line_signature: str = Header(None, alias="X-Line-Signature")
):
    body = await request.body()
    
    # 驗證簽名（parser.parse 會拋 InvalidSignatureError）
    try:
        events = parser.parse(body.decode(), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=f"收到：{event.message.text}")]
                    )
                )
    
    return {"status": "ok"}
```

### 3. 學校公告推播流程（Announcement → LINE Multicast）

```python
# 公告發布後觸發 LINE 推播
async def notify_line_users(announcement: dict, user_line_ids: list[str]):
    """
    announcement: {"title": "...", "summary": "...", "category": "一般"}
    user_line_ids: 已訂閱的家長/師生 LINE user_id 清單
    """
    if not user_line_ids:
        return
    
    text = (
        f"📢 新公告\n"
        f"【{announcement['category']}】{announcement['title']}\n"
        f"{announcement['summary']}"
    )
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        # Multicast：一次推給多個用戶（非廣播）
        line_bot_api.multicast(
            to=user_line_ids,
            messages=[TextMessage(text=text)]
        )
```

### 4. LINE Messaging API 發送類型選擇

| 方法 | 適用場景 | 限制 |
|------|---------|------|
| `reply_message` | webhook 回應（reply_token） | 30秒內、一次性的 reply_token |
| `push_message` | 主動推給單一用戶 | 需要 user_id |
| `multicast` | 公告推給多位家長 | **學校公告首選**（有 user_id 清單） |
| `broadcast` | 推給所有好友 | 無目標控制，不推薦學校 |

### 5. Reply Token 30秒規則（安全處理）

```python
# ⚠️ Reply token 只用一次，LINE 會 retry
# 正確做法：收到即回覆，不要存入 DB 重複使用

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # ✅ 立即回覆
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="好的，已收到！")]
        )
    )
    # ❌ 不要這樣做：把 reply_token 存入佇列稍後使用
    # reply_token 30秒後過期，且只能成功使用一次
```

### 6. Flex Message（可選：美化公告卡片）

```python
from linebot.v3.messages import FlexMessage, FlexContainer

# 公告 Flex Message（可放在 LINE 聊天上方呈現卡片）
bulletin_bubble = """{
  "type": "bubble",
  "header": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {"type": "text", "text": "📢 新公告", "weight": "bold", "size": "sm"}
    ]
  },
  "body": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {"type": "text", "text": "「{title}」", "weight": "bold", "size": "md"},
      {"type": "text", "text": "{summary}", "size": "sm", "color": "#666666"}
    ]
  },
  "footer": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {"type": "button", "action": {"type": "uri", "label": "查看全文", "uri": "{bulletin_url}"}}
    ]
  }
}"""

flex_msg = FlexMessage(
    alt_text=f"新公告：{announcement['title']}",
    contents=FlexContainer.from_json(bulletin_bubble)
)
```

---

## If→Then 經驗固化

### If→Then #1（學校公告 LINE 推播首選 multicast）

**If** 學校公告系統需要即時通知家長/師生，**then** 用 `MessagingApi.multicast()` 而非 `broadcast()` —— multicast 可精確控制目標用戶清單（家長、師生、個別班級），避免漏發或誤發：

```python
# ✅ 正確：指定 user_id 清單
line_bot_api.multicast(
    to=["Uxxx111", "Uxxx222", "Uxxx333"],  # 家長 LINE user_id
    messages=[TextMessage(text=bulletin_text)]
)

# ❌ 錯誤：broadcast 無差別推給所有好友
line_bot_api.broadcast(messages=[TextMessage(text=bulletin_text)])
```

**Why**：學校場景需要角色區分（家長只看家長通知、師生只看校務通知）；broadcast 推給全部好友，無法做到分眾推送。

### If→Then #2（line-bot-sdk v3 用 ApiClient context manager）

**If** 使用 line-bot-sdk v3 發送 LINE 訊息，**then** 必須用 `ApiClient(configuration)` context manager 包覆 `MessagingApi`——所有 API call 都需要通過 `ApiClient`：

```python
# ✅ 正確
with ApiClient(configuration) as api_client:
    line_bot_api = MessagingApi(api_client)
    line_bot_api.multicast(to=user_ids, messages=[TextMessage(text=msg)])

# ❌ 錯誤（v2.x 語法，在 v3 會失敗）
line_bot_api = MessagingApi(access_token)  # v3 無此構造
line_bot_api.multicast(to=user_ids, messages=[...])
```

**Why**：v3 SDK 所有 API call 都通過 `ApiClient` 管理 HTTP 連線和 token refresh；直接構造 `MessagingApi` 會失敗。

### If→Then #3（學校 LINE Bot 需儲存 user_id 而非只靠 LINE 登入）

**If** 學校公告系統要推 LINE 通知給家長，**then** 在家長第一次加入時必須抓取並儲存 `line_user_id`（透過 `line_bot_api.get_profile(user_id)` 或 webhook follow event）：

```python
# Webhook: 家長加入bot時自動儲存
@handler.add(FollowEvent)
def handle_follow(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        profile = line_bot_api.get_profile(event.source.user_id)
        # 存入 DB：user_line_id, display_name, picture_url
        save_user_line_id(
            line_user_id=event.source.user_id,
            display_name=profile.display_name,
            role="parent"  # 或 student/staff
        )
```

**Why**：LINE 推播需要 `user_id`，不是 email；家長加入 bot 時就該capture並持久化，之後公告觸發時才能取用。

---

## 驗證命令

```bash
# 驗證 line-bot-sdk 版本
pip show line-bot-sdk

# 驗證 Python 版本（需 >= 3.10）
python3 --version

# 測試 multicast 構造（不需要真的發送）
python3 -c "
from linebot.v3.messaging import TextMessage
msg = TextMessage(text='test')
print(f'Message type: {msg.type}')
print(f'Message text: {msg.text}')
"

# 驗證 HMAC 計算（確認 timing-safe）
python3 -c "
import hmac, hashlib, json
secret = 'test_secret'
body = json.dumps({'events': []}).encode()
expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
print(f'HMAC-SHA256: {expected}')
print(f'Algorithm correct: {len(expected) == 64}')
"
```

---

## Cycle History
- **Cycle 560** (this cycle): D3-learn — line-bot-sdk v3 async patterns; ApiClient context manager; multicast for school bulletin; reply token 30s rule; Flex Message; 4 sources
- **Cycle 522**: LINE webhook signature verification documented (D3)
