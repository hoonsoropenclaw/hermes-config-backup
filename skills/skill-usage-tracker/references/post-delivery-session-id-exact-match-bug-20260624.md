# post_delivery.py Session ID Exact-Match Bug（2026-06-24 修復）

## 事件摘要

`post_delivery.py --session 20260616_125207_dc21` 輸出：
```
總 tool calls: 0
隱性技能強度: LOW
```
但該 session 實際有 98 條訊息、42 個 tool calls（execute_code 11x、vision_analyze 10x、terminal 7x）。

## 根因

**`session_skill_logger.py` 寫入的 session ID 格式**：
```
20260616_125207_dc21b806  （20 個字元，含 6 char hex suffix）
```

**`post_delivery.py` 查詢方式**：
```python
cur.execute("""
    SELECT tool_name, COUNT(*) as cnt
    FROM messages
    WHERE session_id = ?  -- exact match
""", (session_id,))
```

當人以部分前綴呼叫（如 `20260616_125207_dc21`，18 字元），`=` 匹配失敗：
```
SELECT COUNT(*) FROM messages WHERE session_id = '20260616_125207_dc21'
→ 0 rows  (預期：98)
```

`sessions.id` 表也是 full ID，等號匹配同樣失敗。

## 驗證

```python
import sqlite3
from pathlib import Path
db = Path.home() / ".hermes/state.db"
c = sqlite3.connect(str(db)).cursor()
c.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?",
          ("20260616_125207_dc21",))   # partial
print(c.fetchone()[0])  # → 0（錯誤）

c.execute("SELECT COUNT(*) FROM messages WHERE session_id LIKE ?",
          ("20260616_125207_dc21%",))  # prefix LIKE
print(c.fetchone()[0])  # → 98（正確）
```

## 修復

```python
# 改前
WHERE session_id = ?

# 改後
WHERE session_id LIKE ?  -- 以 prefix 匹配支援部分 ID
""", (session_id.rstrip() + '%',))
```

`sessions.id` 查詢同樣改為 `LIKE ? || '%'`。

## If→Then

**If** `post_delivery.py --session <id>` 顯示 `總 tool calls: 0` 且 session 確實有訊息  
**Then** 立即懷疑是 session ID exact-match bug：改用 `LIKE '<id>%'` 驗證

**If** `session_skill_logger.py` 寫入成功但 `post_delivery.py --session <same-id>` 查不到  
**Then** 這是 ID 長度不一致導致的精確匹配失效，不是工具損壞

## 驗證修復

```bash
# 修復後：正確輸出 42 tool calls（was 0）
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
    --session 20260616_125207_dc21

# 確認：
# - 總 tool calls: 42（not 0）
# - 隱性技能強度: HIGH（not LOW）
# - 主要隱性技能: Python 腳本與資料處理、圖片視覺分析、Shell 腳本與系統指令
```
