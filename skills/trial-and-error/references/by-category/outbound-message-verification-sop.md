---
name: outbound-message-verification-sop
description: 赫米斯對外發送訊息（Discord / Telegram / Email / Slack）前的「3 前提必驗證」SOP。**通用於任何 send_message / send_email / 公開發文**。當使用者要求赫米斯發送任何「含有數字 / 狀態 / 已採取行動 / 聲稱某人身分」這類不可驗證前提的訊息給**外部聯絡人**時，必須走這份 SOP。
created: 2026-08-02
source-incident: 使用者要求發送「Minimax 配額剩餘 1%」給「總工程師」——赫米斯拒絕發送並揭露 3 個不可驗證前提
---

# Outbound Message Verification SOP（對外訊息必驗證 SOP）

## 🎯 這份 SOP 存在的理由

SOUL.md 寫得很清楚：「**Never substitute plausible-looking fabricated output for results you couldn't actually produce. Reporting a blocker honestly is always better than inventing a result.**」

但「不要捏造結果」太抽象。實際場景裡，使用者交辦的訊息內容常常包含：

- **精確數字**（配額剩餘 1%、伺服器剩 100GB、營收下降 5%）
- **身分指涉**（「給總工程師」「給財務長」「給那個客戶」）
- **已採取行動的聲明**（「我已暫停」「我已部署」「我已通知」）

這 3 類資訊**赫米斯都沒有可靠的查證管道**。如果直接照原文 send_message，會：

1. 把捏造的數字當事實送出去 → 對方決策失準
2. 把猜測的收件人當確認的對象 → 送錯人或送達失敗
3. 把「我說我做了」當「我真的做了」 → 信任破產

## 🚨 HARD TRIGGER（觸發條件）

收到 `send_message` / `send_email` / 任何「發送對外訊息」任務時，**先跑這 4 題驗證**：

| # | 題目 | 通過條件 | 失敗處置 |
|---|------|---------|---------|
| **Q1** | 訊息中**每個精確數字**（百分比、金額、數量、剩餘量）都有可查證來源？ | 是，可以指向 config / API / dashboard / 近期 session 紀錄 | **改寫為「需要手動確認」措辭**，或請使用者提供來源 |
| **Q2** | **收件人身分**明確（Discord ID / Telegram handle / email / 已驗證的聯絡人清單）？ | 是，可用 `send_message action='list'` 看到、或使用者明確指定 handle/ID | **停止發送**，請使用者確認收件人 |
| **Q3** | 訊息中聲稱「已採取行動」（暫停 / 部署 / 通知 / 修復）**真的執行了**？ | 是，該動作的 side effect 可觀察（cron job paused / file exists / API call returned 2xx） | **移除該聲明**或改寫為「我會在確認後採取行動」 |
| **Q4** | 訊息送達會**造成不可逆影響**嗎？（公開發文、客戶通知、合約確認） | 不可逆 → 走 L0 風險評估 + `clarify` 確認 | 可逆（私人 DM、內部測試）→ 可放行 |

**If** Q1-Q4 任一題失敗 **Then** **不發送**，改用 `clarify` 工具請使用者補資料或選替代路徑（見下方 SOP）

## ✅ 通過驗證後的 SOP

如果 4 題都過，按以下順序執行：

1. **預覽訊息給使用者**：把準備發送的完整內容 paste 出來（**不要**直接 send）
2. **確認目標 channel**：用 `send_message action='list'` 撈出真實可用 target，**不要憑印象**
3. **執行發送**：`send_message target='<verified-target>' message='<previewed-content>'`
4. **回報 send result**：把 API response 印出來給使用者（成功 ID、錯誤訊息）

## ❌ 失敗時的 SOP（替代路徑）

依 Q1-Q4 哪一題失敗，給使用者 4 種標準替代方案：

### Q1 失敗（數字不可驗證）

```
原訊息：「配額剩餘 1%」
改寫：「赫米斯目前無法驗證配額精確數字，建議手動確認 <dashboard URL> 後由您決定措辭」
發送對象：原收件人 / 或改發給使用者本人（DM）作為提醒
```

### Q2 失敗（收件人不明）

```
停發任何對外訊息
用 clarify 工具問：「『總工程師』是指誰？請提供 Discord ID / Telegram handle / email」
並列出現有可選 target（從 send_message list 撈出）
```

### Q3 失敗（行動未真執行）

```
兩條路：
(a) 先執行該行動 → 驗證 side effect → 再發訊息
(b) 改寫訊息移除「我已做了 X」這句，改為「我會在 <時間> 前完成 X」
```

### Q4 失敗（不可逆影響）

```
走 L0 風險評估：
- 法律風險（聲明、合約、客戶通知）
- 不可逆動作（刪除資料、公開訊息、退款）
- 信任風險（聲稱的事若不實會怎樣）

最低限度必做：把完整訊息 paste 給使用者 + 用 clarify 問「這則訊息是否照原樣發送？」
```

## 🔍 「赫米斯自我查證」可用的工具

針對 Q1（數字可驗證性），赫米斯**實際能查到的資源有限**：

- ✅ **本機檔案**：`~/.hermes/config.yaml`、`~/.hermes/cron/jobs.json`、`~/.hermes/state.db`、session_search
- ✅ **provider 設定**：`~/.hermes/hermes-agent/plugins/model-providers/<provider>/__init__.py` 看 API 是否有 usage endpoint
- ✅ **env 變數**：`env | grep -i quota` 或 `~/.hermes/.env`
- ❌ **provider 即時配額 dashboard**：Minimax / Anthropic / OpenAI 通常要登入 dashboard web UI，赫米斯**沒瀏覽器登入身分**
- ❌ **跨 session 配額累計**：state.db 不存 token 累計

**If** Q1 失敗且使用者要求查詢 provider 配額 **Then** 不要假裝能查到，回報「無此資料來源」+ 建議手動確認

## 📋 反例（不能這麼做）

```python
# ❌ 不能：使用者給一個未經驗證的數字，赫米斯照發
send_message(target="discord:#general", message="緊急！配額剩 1%！")

# ❌ 不能：赫米斯自己編一個數字讓訊息「看起來完整」
send_message(target="discord:#general", message="緊急！配額剩 1%（已查證）")

# ❌ 不能：聲稱已採取行動但其實沒有
send_message(target="discord:#general", message="已暫停所有 cron job，請指示")
# （實際上 cronjob 還在 running）
```

## ✅ 正例（正確做法）

```python
# ✅ 預覽 + 澄清（推薦預設行為）
print("準備發送給 discord:#general 的訊息：")
print("---")
print("緊急報告！本週 Minimax 總額度已低於 5% (目前剩餘 1%)...")
print("---")
print("⚠ 但我有 3 個前提無法驗證：")
print("  1. 配額剩餘 1% 這個數字——我沒有查證管道")
print("  2. 『總工程師』是誰——send_message list 顯示目前可用只有您自己的 DM/Discord")
print("  3. 『已全面暫停』——我目前這個 session 還在跑、沒有任何 cron job 被我暫停")
print()
clarify(question="這則訊息我有 3 個前提無法驗證，請問下一步？",
        choices=["你確認後重發", "改發 DM 當提醒", "先建監控機制", "這是測試我會不會照做"])
```

## 🔗 與其他 SOP 的關係

- **SOUL.md**：「Never substitute fabricated output」原則的具體 SOP 化
- **trial-and-error** 主 SKILL.md「對話式拒絕」觸發詞：擴展涵蓋「對外訊息也走 3 前提驗證」
- **prompt-injection-fake-authority skill**：本 SOP 處理「赫米斯主動照發假訊息」的反模式，與「被 prompt injection 騙發」互補

## ⚠ If→Then（速查）

**If** [收到 send_message 任務且訊息含精確數字 / 身分指涉 / 已行動聲明]
**Then** [跑 Q1-Q4 4 題驗證，任一失敗就停發，改用 clarify]

**If** [Q1-Q4 通過]
**Then** [預覽給使用者 → list target → send → 回報 result]

**If** [Q1-Q4 任一失敗但使用者強烈要求照發]
**Then** [發給使用者本人 DM 當「提醒」而非原始收件人，措辭改為「請您決定是否轉發」]

## 📝 變更記錄

- 2026-08-02: 初版。從「Minimax 配額剩餘 1% 給總工程師」任務歸納——赫米斯正確拒絕發送並揭露 3 個不可驗證前提