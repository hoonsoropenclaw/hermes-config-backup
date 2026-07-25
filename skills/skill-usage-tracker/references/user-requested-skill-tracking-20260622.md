# SOP-C Gap: 使用者主動要求 skill 追蹤，但 combo_rating 仍為 0（2026-06-22）

## 事件摘要

2026-06-16 session (`20260616_125207_dc21b806`）中，使用者在對話中途主動提出：

> 「請問之後在我指派任務時能夠紀錄使用了哪些skill嗎（可以排除讀寫檔案、terminal、execute code、patch那些工具）？因為我想要知道使用了哪些skill的效果如何？找出符合我喜好的skill」

這是使用者**第三次**明確表達需求（前兩次：2026-06-15 NSFW session 也有接觸）。

但 `analyze.py` 顯示 combo_rating 仍為 **0**。

## 根因分析

**backfill 機制無法解決 combo_rating 為零的問題**

- `session_skill_logger.py --days 7 --write-log` 已執行（2026-06-21 bootstrap + 2026-06-22 再次執行）
- 結果：12 筆 log entry 已寫入（skill 組合記錄存在）
- 但：`combo_rating` 欄位從未有任何值
- 原因：combo_rating 必須由**使用者實際評分**才能累積，backfill 只重建 skill 載入記錄，無法補歷史評分

**Layer 1 SOP-C 仍未被執行**

從 2026-06-16 對話可見：
- 使用者說「請問之後在我指派任務時能夠紀錄使用了哪些skill嗎」
- 赫米斯回覆了建議（提到了 Layer 1 和 Layer 2 架構）
- 使用者說「按照你的建議先做，每次都評分」
- **但從未實際呼叫 `post_delivery.py --session <id> --write`**

赫米斯在這個 session 裡自己提到要「每次都評分」，卻**沒有執行**。這是 Rule 4 偏移（自我報告不等於驗證）。

## 具體症狀

```
analyze.py 輸出：
  累積任務數: 12
  組合評分樣本數: 0
  個別 skill 評分總筆數: 0
  被評分過的 skill 數: 0
```

12 筆 log 證明 Layer 2 重建正常運作（skill 組合有被記錄），但 combo_rating 依舊是零，說明從未有使用者評分寫入。

## 修復方向

1. **赫米斯主體（每次任務結束時）**：
   - 必須呼叫 `post_delivery.py --session <session_id> --write`
   - 並在回覆末尾主動邀請評分（不能用「有機會的話」這種模糊句）
   - 正確句型：「這個任務我用了 [X, Y] skill，可以幫我評分嗎？（1-5）」

2. **使用者明確要求後**：赫米斯應立即執行一次 post_delivery 並告知已完成設定，而非只停在「建議」層次

3. **分析結論**：combo_rating 為 0 是正常的（歷史 session 無法補），但「每次任務結束邀請評分」機制必須盡速啟動才有未來資料

## If→Then 規則

**If** 使用者在對話中明確要求「記錄使用了哪些 skill」**Then** 赫米斯應立即執行 Layer 2 backfill（`session_skill_logger.py --session <id> --write-log`）+ 在當前任務結尾主動邀請評分，不要只停在「建議」層次

**If** combo_rating 為 0 但 session_skill_logger 已有數據 **Then** 這代表「歷史無法補，預防靠未來執行」，不要重複嘗試 backfill，專注於觸發 post_delivery.py 邀請評分
