# LINE Bot 整合狀態追蹤

**Created**: Cycle 563, 2026-07-30
**Status**: blocked — 等待 `cloudflared` 安裝

---

## 外部核查結果（Cycle 563）

```bash
# 1. cloudflared 安裝狀態
$ cloudflared --version
NOT_INSTALLED  ← Hermes 主機未安装 Cloudflare Tunnel

# 2. school-bulletin LINE 程式碼
$ ls ~/permanent-projects/school-bulletin/*line*.py
0 檔案

$ ls ~/permanent-projects/school-bulletin/app/api/ | grep line
0 routes
```

---

## 現有文件資產

| 文件 | 狀態 | 說明 |
|------|------|------|
| `references/line-bot-messaging-v3-bulleline-notify-20260730.md` | ✅ 文檔化 | SDK v3 multicast + Flex Message 模式 |
| `references/line-bot-webhook-integration-20260719.md` | ✅ 文檔化 | webhook 整合架構（FastAPI + LINE Bot） |
| `trial-and-error/.../line-bot-sdk-v3-fastapi-patterns-20260730.md` | ✅ 文檔化 | SDK v3 context manager 模式 |
| `trial-and-error/.../line-bot-webhook-server-deployment-20260730.md` | ✅ 文檔化 | Cloudflare Tunnel 部署抉擇 + 完整程式碼 |
| `trial-and-error/.../line-webhook-signature-verification-20260719.md` | ✅ 文檔化 | HMAC-SHA256 + timing-safe 驗證 SOP |

---

## 部署路徑（已確認）

```
LINE Platform → HTTPS webhook → Cloudflare Tunnel → localhost:8000 (FastAPI)
```

**首選方案**：Cloudflare Tunnel（穩定、長期執行，適合家庭 NAT 環境）

---

## 下一步行動（按順序）

1. **安裝 cloudflared**（blocking item）
   ```bash
   # 確認 tunnel token 是否存在
   grep -r "CLOUDFLARE_TUNNEL" ~/.hermes/.env 2>/dev/null | head -1
   # 若無，从 Cloudflare Zero Trust Dashboard 建立 tunnel 並取得 token
   ```

2. **驗證 tunnel 可達**
   ```bash
   cloudflared tunnel run --token <TOKEN> &
   sleep 5
   curl https://<tunnel-subdomain>.trycloudflare.com/health
   ```

3. **將 webhook server 程式碼寫入專案**
   - 程式碼藍圖已見 `trial-and-error/.../line-bot-webhook-server-deployment-20260730.md` line 81-133
   - 目標路徑：`~/permanent-projects/school-bulletin/app/api/line/webhook.py`
   - 或獨立部署至 `~/permanent-projects/line-bot-server/`

4. **設定 LINE Console Webhook URL**
   - 指向 `https://<tunnel-subdomain>.trycloudflare.com/webhook/line`
   - 關閉 LINE Console 的「使用 Webhook」靈活 JSON 模式（若啟用）

---

## LINE Bot 整合觸發點

在 `POST /api/announcements` 成功後，application-level hook：

```python
# 示意（尚未實作）
async def notify_line_users(announcement_id: str, title: str, summary: str):
    users = await db.fetch(
        "SELECT line_user_id FROM user_role_assignments "
        "WHERE role IN ('parent','student') AND line_user_id IS NOT NULL"
    )
    if users:
        line_bot_api.multicast(
            [u["line_user_id"] for u in users],
            [TextMessage(text=f"📢 新公告：{title}\n{summary}")]
        )
```

---

## DB Schema 需確認的欄位

`user_role_assignments` 表需要確認有 `line_user_id` 欄位：
```sql
-- 檢查
SELECT column_name FROM information_schema.columns
WHERE table_name = 'user_role_assignments' AND column_name LIKE '%line%';
```

若無此欄位，需新增 migration：
```sql
ALTER TABLE user_role_assignments ADD COLUMN line_user_id TEXT;
```

---

## If→Then 捷徑

**If** 要推進 LINE Bot 整合但不确定从哪一步开始
**Then** 先跑 `cloudflared --version` — 若 NOT_INSTALLED，先解決安裝問題，否則 webhook 無法連通

**If** cloudflared 已安裝但 tunnel 無法連線
**Then** 檢查 `cloudflared tunnel list` 和 `cloudflared tunnel run --token <T>` 的輸出日誌
