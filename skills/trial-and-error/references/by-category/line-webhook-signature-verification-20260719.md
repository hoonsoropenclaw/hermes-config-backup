### line-webhook-01 LINE Messaging API Webhook Signature Verification
**Created**: Cycle 522, 2026-07-19
**Type**: D3-learn (實作型)
**Validated by**: LINE Developers Docs + Hooklistener 2026 Webhook Trends + HMAC Best Practices
**Gap**: LINE Messaging API webhook security — signature verification was not deeply codified in Hermes skills

---

## 背景

**LINE Messaging API Webhook 安全機制**：
- LINE server → Hermes webhook endpoint（POST）
- LINE 在 HTTP header `X-LINE-Signature` 傳送 HMAC-SHA256 簽名
- 簽名 = `HMAC-SHA256(channel_secret, raw_request_body)`
- Hermes 必須用相同的演算法重新計算並比對，防止偽造

**2026 趨勢（Hooklistener 2026 Webhook Trends）**：
- RFC 9421 HTTP Message Signatures 逐漸成為標準
- 短期臨時 token（60-300 秒 TTL）成為新常態
- LINE 目前使用靜態 channel_secret，但包裝成通用介面將來易於遷移
- Timing-safe comparison 是標配（防止 timing attack）

**⚠️ 最常見錯誤**：
- 在驗證簽名前先 parse JSON → request body 被改變 → 簽名比對失敗
- 使用 `==` 而非 timing-safe comparison → timing attack 漏洞
- 把 channel_secret 寫死在 code 而非環境變數

---

## 核心原理

LINE 簽名驗證流程：
```
1. LINE Server 計算：HMAC-SHA256(channel_secret, raw_body) → signature_A
2. Hermes 接收：從 X-LINE-Signature header 取得 signature_B
3. Hermes 計算：HMAC-SHA256(channel_secret, 收到的 raw_body) → signature_C
4. 比對：signature_A == signature_B == signature_C（使用 timing-safe 比較）
```

**關鍵：raw_body 必須是未經處理的原始 bytes，不能是 parse 後的 JSON。**

---

## 實作：Python（FastAPI / Flask）

### Python — Timing-Safe 驗證

```python
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
import os

app = FastAPI()

LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]  # 放環境變數

async def verify_line_signature(request: Request) -> bytes:
    """驗證 LINE webhook 簽名，傳回 raw_body。"""
    # 1. 取 header（務必用 .raw bytes）
    signature = request.headers.get("X-LINE-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-LINE-Signature")

    # 2. 取 raw body（還沒被 parse 的原始 bytes）
    # FastAPI：request.body() 回傳 bytes
    # ⚠️ 絕對不能先 await request.json() 或 request.form()
    raw_body = await request.body()

    # 3. 計算 expected signature
    expected = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    # 4. Timing-safe comparison（防止 timing attack）
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return raw_body


@app.post("/webhook")
async def line_webhook(request: Request):
    raw_body = await verify_line_signature(request)

    # 5. 現在才 parse（驗證完才處理）
    import json
    events = json.loads(raw_body)

    for event in events.get("events", []):
        # 處理 event...
        pass

    return {"status": "ok"}
```

### Python — Flask 版本

```python
import hmac
import hashlib
import os
from flask import Flask, request, abort
import json

app = Flask(__name__)
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]

@app.route("/webhook", methods=["POST"])
def webhook():
    # 1. 取 header
    signature = request.headers.get("X-LINE-Signature")
    if not signature:
        abort(401, "Missing X-LINE-Signature")

    # 2. 取 raw body（request.get_data() 回傳 bytes）
    raw_body = request.get_data()

    # 3. 計算 expected
    expected = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    # 4. Timing-safe comparison
    if not hmac.compare_digest(expected, signature):
        abort(401, "Invalid signature")

    # 5. Parse
    events = json.loads(raw_body)
    return {"status": "ok"}
```

---

## If→Then 經驗固化

### If→Then #1（簽名驗證失敗的最常見原因）

**If** LINE webhook 一直回傳 401 Invalid signature，且確定 channel_secret 正確
**Then** 檢查是否在驗證前就先 parse 了 JSON — 必須先取 raw body 再驗證，最後才 parse

**為什麼**：LINE 文件特別強調「do not modify the request body before verifying the signature」。FastAPI/Flask 的 `.json()` 和 `.form()` 會改變 request stream 指標位置，導致 HMAC 計算的 body 與 LINE 發出的不一致。

**驗證方法**：
```bash
# 直接用 curl 測試（必須有正確的 X-LINE-Signature）
curl -X POST https://your-domain.com/webhook \
  -H "X-LINE-Signature: <your_signature>" \
  -H "Content-Type: application/json" \
  -d '{"events":[]}' \
  -v 2>&1 | grep -E "< HTTP|{"
```

### If→Then #2（Timing Attack 防護）

**If** 在實作 webhook 簽名驗證時，發現自己用了 `==` 或 `!=` 比較簽名字串
**Then** 立刻換成 `hmac.compare_digest()` — Python 內建 timing-safe comparison

**為什麼**：一般 `==` 在比對到第一個不同字元時就回傳 False，攻擊者可利用時間差推測正確的簽名。`hmac.compare_digest()` 不管字元對不對都比對完整長度，時間相同。2026 年所有 webhook 框架（Stripe/Twilio/LINE）都要求 timing-safe comparison。

```python
# ❌ 錯誤：會被 timing attack
if calculated_signature == received_signature:
    pass

# ✅ 正確：timing-safe
if hmac.compare_digest(calculated_signature, received_signature):
    pass
```

### If→Then #3（Webhook 可靠性 — Reply Token 只用一次）

**If** 收到 LINE webhook event 且需要回覆用戶
**Then** 用 reply token（只能在 30 秒內用一次）回覆，然後立即忽略或存入佇列

**為什麼**：LINE 的 reply token 是一次性（single-use），過期時間 30 秒。如果同時收到多個相同 reply token 的 webhook（LINE 會 retry），只能用第一個，其他的 reply 會失敗。

```python
# 正確流程：
# 1. 驗證簽名（上面已完成）
# 2. 如果需要回覆，立刻 reply，然後不要再 reply 同一個 token
# 3. 其他處理（非同步）：存入 DB / 推入佇列 / 交給後續 worker
```

### If→Then #4（Webhook Secret 放在環境變數）

**If** 看到 channel_secret 被寫在程式碼中（`LINE_CHANNEL_SECRET = "xxx123..."`）
**Then** 立即改為 `os.environ["LINE_CHANNEL_SECRET"]` 或 `os.getenv("LINE_CHANNEL_SECRET")`

**為什麼**：Secret 寫在 code = 任何有原始碼存取權的人都能看到。放在環境變數，部署時注入，生產環境隔離。Cron job 的 GH013 教訓（secret leak）也確認：token 必須與 code 分離。

---

## 驗證命令

```bash
# 驗證 LINE SDK signature 計算（用已知 secret + body）
python3 -c "
import hmac, hashlib, json
secret = 'test_secret'
body = json.dumps({'events': []}).encode()
expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
print(f'Expected: {expected}')
print(f'Algorithm: HMAC-SHA256')
print(f'Input: secret={secret}, body={body}')
"

# 驗證 Timing-safe comparison（測試 compare_digest 行為）
python3 -c "
import hmac, hashlib, time

# 模擬 timing attack 情境
secret = 'mysecret'
payloads = ['aaaaaa', 'aaaab', 'aaaac', secret]

def unsafe_compare(a, b):
    return a == b

def safe_compare(a, b):
    return hmac.compare_digest(a, b)

print('Timing-safe vs unsafe comparison:')
for p in payloads:
    start = time.perf_counter()
    result = hmac.compare_digest(p, 'aaaaba')  # 接近但不對
    t1 = time.perf_counter() - start
    
    start = time.perf_counter()
    result2 = (p == 'aaaaba')  # unsafe
    t2 = time.perf_counter() - start
    
    print(f'  compare_digest: {t1*1000:.4f}ms, ==: {t2*1000:.4f}ms')
"
```

---

## 關聯條目

- `school-bulletin-system/SKILL.md` — 學校公告系統（可能有 LINE Bot 整合需求）
- `school-interview-scheduler/` — LINE Bot 面試排程 workflow
- `ai-image-safety-school-20260620.md` — 學校場景的內容安全
- Hooklistener 2026 Webhook Trends（外部資源）— RFC 9421、短期 token、post-quantum readiness
