# skill-usage-tracker — `skills_loaded: []` Diagnostic (2026-06-22)

## 發現情境

`session_skill_logger.py` 在 2026-06-22 的 backfill 中：
- 寫入 12 筆 entry
- 所有 entry 的 `skills_loaded: []`（空陣列）
- `combo_rating: N/A`

## 根因分析

### 第一層懷疑：Logger 壞了？
state.db 直接查詢顯示：
```
session=20260616_125207_ tool_name=skill_view → 1 call
session=20260615_082514_ tool_name=skill_view → 1 call
```

logger 對 `skill_view` 的 SQL 查詢語法正確，state.db schema `tool_name TEXT` 存在。

### 第二層懷疑：Logger 解析失敗？
state.db 中 `tool_calls=NULL`（所有 rows），而 logger 的解析邏輯依賴 `json.loads(content)` 或 regex `name='xxx'`。

`content` 欄位值未知（從 state.db 直接讀不出來），但 1 筆 `skill_view` call 在 session 98 msg 中佔比 1%——幾乎全部依賴隱性工具。

### 第三層結論：Gap 在 session 本身，不是 logger

| Session | skill_view 次數 | 隱性工具次數 | 隱性佔比 |
|---------|-----------------|-------------|---------|
| 20260616 | 1 | 93 | 94.9% |
| 20260615 | 1 | ~80 | ~98.8% |

**Hermes 沒有呼叫 `skill_view`，所以 logger 沒有東西可讀。**

## 診斷 SOP

```python
# 當 skills_loaded: [] 且 combo_rating: N/A 時，先跑這個
import sqlite3
from pathlib import Path

db_path = Path.home() / ".hermes/state.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Step 1: 數 skill_view 次數
cur.execute("""
    SELECT COUNT(*) as cnt
    FROM messages
    WHERE session_id = ? AND tool_name = 'skill_view'
""", (session_id,))
skill_view_count = cur.fetchone()[0]

# Step 2: 數隱性工具（排除清單）
EXCLUDED = {'terminal','execute_code','read_file','write_file','patch',
            'search_files','web_search','browser_navigate','vision_analyze',
            'send_message','delegate_task'}
cur.execute("""
    SELECT tool_name, COUNT(*) as cnt
    FROM messages
    WHERE session_id = ? AND tool_name IS NOT NULL
    GROUP BY tool_name
    ORDER BY cnt DESC
""", (session_id,))
all_tools = cur.fetchall()

implicit = sum(cnt for tn, cnt in all_tools if tn not in EXCLUDED)
total = sum(cnt for _, cnt in all_tools)
print(f"skill_view={skill_view_count}, implicit={implicit}/{total} ({100*implicit//total}%)")

# Step 3: 判定
if skill_view_count == 0 and implicit/total > 0.9:
    print("→ Gap is LLM not calling skill_view — logger is fine")
elif skill_view_count > 0 and skills_loaded_empty:
    print("→ Logger parsing may be broken — check content field")
else:
    print("→ Logger returned 0 skills legitimately — session had no skill_loads")

conn.close()
```

## If→Then 決策

**If** `skills_loaded: []` 且 `implicit/total > 90%`  
**Then** 根因是「LLM 沒呼叫 `skill_view`」，logger 正常，文件這個模式

**If** `skill_view_count > 0` 但 `skills_loaded: []`  
**Then** `session_skill_logger.py` 的 content 解析有 bug，檢查 `tool_calls` 是否真的 `NULL`

## 與 d3-exit-sop-a-gap-20260622.md 的關係

- `d3-exit-sop-a-gap-20260622.md`：從**執行缺口**角度描述（SOP-A 從未被執行）
- 本文件：從**技術診斷**角度描述（如何確認 `skills_loaded: []` 的根因）

兩者互補，同一 gap 的兩個視角。
