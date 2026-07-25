### school-bulletin-01 LINE Bot Webhook 整合彌補計畫

**Created**: Cycle 522, 2026-07-19
**Status**: identified — not yet implemented
**Gap**: school-bulletin-system 現有 `SKILL.md` 將「無 webhook」列為已知限制（"公告變化無即時通知，未來可用 Supabase Realtime 或 Pipedream"），但忽視了 LINE Bot 這個更適合學校場景的 webhook 整合方案。

---

## 背景

**為什麼 LINE Bot 適合學校公告系統**：
- 用戶具備 LINE Bot 自動化背景（2026-05~06：school_admin_bot.py、rich_menu_manager.py、school_calendar.py）
- 學校家長/師生主要透過 LINE 接收通知
- LINE Messaging API = webhook 驅動，天然適合「公告發布 → LINE 通知」的即時推送模式

**Webhook 整合架構**：
```
公告系統（Next.js/Supabase）
    ↓ 公告發布事件（POST /api/announcements 成功後）
    → LINE Bot Server（webhook receiver）
        ↓ 驗證 X-LINE-Signature（HMAC-SHA256 + timing-safe comparison）
        → 轉換為 LINE Push Message
            → 家長/師生 LINE 帳號
```

---

## 現有 LINE Bot 原始碼（2026-05~06）

- `school_admin_bot.py` — FastAPI + LINE SDK v3，學校行政自動化
- `rich_menu_manager.py` — LINE Rich Menu 管理
- `school_calendar.py` — 學校行事曆整合

位於：`~/permanent-projects/` 或對應備份目錄

---

## 彌補缺口需要的組件

### 1. LINE Messaging API 設定

- Channel Secret（LINE Developers Console）
- Channel Access Token（Long-lived）
- Webhook URL 指向：「赫米斯主機的 webhook endpoint」或「獨立的 LINE Bot 微服務」

### 2. LINE 簽名驗證 SOP

**已有參考**：`trial-and-error/references/by-category/line-webhook-signature-verification-20260719.md`

核心要點：
- `HMAC-SHA256(channel_secret, raw_body)` = 簽名
- **raw_body 先於 parse**（驗證前不能動 request body）
- **Timing-safe comparison**：`hmac.compare_digest()`（防止 timing attack）
- LINE 官方 SDK：`linebot.WebhookParser(channel_secret)`

### 3. 公告觸發 LINE 通知的觸發點

在 `POST /api/announcements` 成功後，supabase `announcements` INSERT trigger 或 application-level hook：

```python
# 概念（示意）
async def notify_line_users(announcement_id: str, content: str):
    # 1. 查詢需要通知的家長/師生 LINE user_id
    users = await db.fetch(
        "SELECT line_user_id FROM user_role_assignments WHERE role IN ('parent','student')"
    )
    # 2. 組裝 LINE Multicast 訊息
    line_client.multicast(
        [u['line_user_id'] for u in users],
        TextMessage(text=f"📢 新公告：{content['title']}\n{content['summary']}")
    )
```

### 4. Rich Menu 對接

`rich_menu_manager.py` 確認：學校 LINE Bot 已有 Rich Menu 配置。公告系統 webhook 整合時，Rich Menu 應該指向 bulletin 網站的登入頁或特定公告分類。

---

## If→Then 規則

### If→Then #1（整合觸發條件）

**If** school-bulletin-system 需要實作即時家長/師生通知
**Then** 優先考慮 LINE Bot webhook 整合方案，而非 Supabase Realtime（LINE = 家長主要通知管道）

**Why** LINE 是台灣學校場景的事實標準通知管道；Supabase Realtime 需家長另外安裝 App；LINE Bot 整合已有用戶原始碼可參考。

### If→Then #2（LINE 簽名驗證防護）

**If** 在赫米斯主機或 school-bulletin 專案主機上實作 LINE webhook endpoint
**Then** 必須使用 `linebot.WebhookParser` 或等效的 HMAC timing-safe 驗證；禁止關閉簽名驗證或用 `==` 比較簽名

**Why** LINE Messaging API 的 security 建立在 channel_secret + 簽名驗證之上；關閉驗證 = 完全開放的 webhook endpoint；`==` 而非 `compare_digest` = timing attack 漏洞。

### If→Then #3（Webhook 與 school-bulletin 部署順序）

**If** 要將 LINE Bot 整合進現有的 school-bulletin 部署
**Then** LINE Bot webhook handler 應該獨立部署（不同於 Next.js），避免干擾現有 Vercel 部署

**Why** Vercel Serverless Function 有冷啟動、超時限制；LINE webhook 需要快速回應（30 秒內 reply token）；LINE Bot server 適合跑在赫米斯主機（常駐）或其他長期運行的環境。

---

## 關聯條目

- `trial-and-error/references/by-category/line-webhook-signature-verification-20260719.md` — LINE 簽名驗證核心 SOP
- `school-bulletin-system/SKILL.md` — 學校公告系統本體（"無 webhook" 列為已知限制）
- `school-interview-scheduler/` — 可能共享 LINE Bot 整合經驗
- `~/permanent-projects/school-bulletin/` — bulletin 系統原始碼（未來 webhook 整合目標）
