# eval-sync grep pattern bug

## 發現時間
2026-06-08 (本 cycle)

## 問題描述
sync_evaluations.py 的 `get_api_key()` 函數使用 `startswith("AGENT_API_KEY=***")` 來匹配 AGENT_API_KEY 行，但 `***` 是**字面字元**而非萬用字元，導致當 .env.local 中的 key 被 mask 為 `AGENT_API_KEY=***` 時，Python 的 `line.split("=", 1)[1].strip()` 取出 `***`（三個星號字元），非空值被當成有效 key 返回，但 `***` 不是真實 API key。

正確做法：`.env.local` 中 `AGENT_API_KEY=***` 表示 Vercel 的 env pull 對敏感值做了遮罩（實際 key 在 Vercel server-side），此檔案無法用於客戶端認證。應該從 `~/.hermes/.env` 取真實 key。

## 修復
```python
# Before (broken):
if line.startswith("AGENT_API_KEY=*** or line.startswith("export AGENT_API_KEY=***):
    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if key:
        return key

# After (fixed):
if line.startswith("AGENT_API_KEY="):
    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if key and key != "***":  # Skip redaction markers
        return key
```

## 驗證
```bash
cd /home/hoonsoropenclaw && python3 .hermes/scripts/sync_evaluations.py
# 輸出：[2026-06-08 11:56:44] ===== 評價同步開始 =====
#       [2026-06-08 11:56:47] 取得 1 筆評價（不再是 AGENT_API_KEY not found）
```

## 預防
Python grep pattern（如 `line.startswith("***")`）中的 `***` 是字面字元，不是 shell glob 的萬用字元。任何檢查字串是否為 redaction marker 的邏輯，應使用明確比對 `!= "***"` 而非信賴字元長度或 prefix matching。