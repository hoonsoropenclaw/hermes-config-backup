# ⚠️ Minimax 配額耗盡緊急處理程序

## 偵測條件
當隔離 session 執行任務時，如果 Minimax 模型回傳以下錯誤：
- `usage limit exceeded`
- `Token Plan Plus (4500/4500 used)`
- `rate_limit`

## 立即行動（在隔離 session 中）

### ✅ 第一步：保存當前工作狀態
將以下資訊寫入 `~/.openclaw/workspace/evolution/quota_saves/`：
```json
{
  "saved_at": "<當前時間 (台灣)>",
  "task_name": "<當前任務名稱>",
  "reason": "Minimax quota exhausted",
  "current_step": "<已完成到哪一步>",
  "notes_completed": "<已產出的檔案列表>",
  "next_step": "<恢復後要繼續做的事>"
}
```

### ✅ 第二步：寫入日誌
在 `~/.openclaw/workspace/logs/` 寫入中斷日誌。

### ❌ 禁止做的事
- **不要**使用 deepseek-chat 或其他付費模型**繼續學習**
- **不要**嘗試重新執行任務
- **不要**使用 API 呼叫額外服務

### ⏸️ 中斷後行為
1. 保存狀態後直接停止
2. 訊息會透過 delivery 機制發送回 Telegram（chatId: 8209753986）

## 恢復流程（Minimax 配額恢復後）
1. 配額約每 5 小時重置一次
2. 從 `quota_saves/` 讀取保存的狀態
3. 從中斷處繼續執行

## 自動化支援
主 session 會自動檢查隔離 session 的錯誤日誌，若發現配額耗盡錯誤：
1. ✅ 產生工作狀態保存
2. ✅ 發送 Telegram 通知
3. ❌ 不切換到 deepseek-chat 繼續學習
