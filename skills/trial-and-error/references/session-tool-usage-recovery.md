# Session Tool Usage Recovery — 從 state.db 反推「那次 session 用了哪些 skill」(2026-06-16 驗證)

## 何時需要

使用者問「之前那次任務你用了哪些 skill」「你之前做 X 的時候實際跑了什麼」——而 `session_search` FTS5 結果**污染、被截斷、或 context compaction 把對話壓掉**時,需要更精確的「事實級」答覆。

**觸發條件**:
- 使用者問「之前那次用了哪些 skill / 工具」
- session_search 撈到的結果**看起來不對**、太雜、太少、或被 cron 紀錄污染
- 對話 context 已被 compaction 壓縮,看不到「當時載入了哪些 skill」
- 需要「驗證」某次任務的 tool 使用模式(避免「自我報告 ≠ 驗證」陷阱)

## 直接查 state.db 的 4 步

state.db 路徑:`~/.hermes/state.db`(SQLite,FTS5 索引)

### Step 1: 找出目標 session 的 ID

```python
import sqlite3, time
from datetime import datetime
from pathlib import Path

conn = sqlite3.connect(str(Path.home() / ".hermes" / "state.db"))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 把目標日期轉成 timestamp(state.db started_at 是 REAL 秒)
ts_start = time.mktime(time.strptime("2026-06-11 00:00:00", "%Y-%m-%d %H:%M:%S"))
ts_end = ts_start + 86400

cur.execute("""
    SELECT id, started_at, source, model, title, message_count
    FROM sessions
    WHERE id NOT LIKE 'cron_%%'
      AND started_at >= ? AND started_at < ?
    ORDER BY started_at ASC
""", (ts_start, ts_end))
for r in cur.fetchall():
    print(f"{r['id']} | {r['source']} | {r['model']} | msgs={r['message_count']} | {r['title']}")
```

**判定**:用 `title` LIKE 或 `message_count` 大小定位目標。`source` 是 `telegram` / `cli` / `cron`,排除 `cron` 才能找到 user 主對話。

### Step 2: 統計 tool_name 使用頻率

```python
from collections import Counter
cur.execute("""
    SELECT tool_name FROM messages
    WHERE session_id = ? AND tool_name IS NOT NULL
""", (sid,))
counter = Counter(r['tool_name'] for r in cur.fetchall())
for tool, n in counter.most_common():
    print(f"  {tool}: {n}")
```

**判讀**:
- `terminal` / `execute_code` 大量 → 主要靠 shell 跑命令、Python 寫腳本
- `skill_view` 數字小(常 1-3)→ 主 session 載入的 skill 不多(因為**載入本身不寫進 messages**)
- `write_file` + `patch` + `read_file` → 直接改 source code
- `clarify` 出現 → 雖然 user 說「不用問」、但中間還是有問

### Step 3: 撈開頭 + 中段 + 結尾各 10 條訊息

```python
cur.execute("""
    SELECT id, role, timestamp, tool_name, substr(content, 1, 500) as preview
    FROM messages WHERE session_id = ?
    ORDER BY timestamp ASC LIMIT 25
""", (sid,))
```

**為什麼要開頭**:
- 第一條 user 訊息 = 觸發 keyword(`^專案` / `@skill` / 直接描述)
- 第一條 assistant 訊息 = 通常會說「先用 X skill 撈...」(直接證據)

**為什麼要結尾**:
- 使用者 feedback 與 skill 補教訓通常在結尾(2026-06-11 那次結尾就建了 2 個新 skill)

### Step 4: 從 user 訊息全文反推 skill 名稱

```sql
-- 找 assistant 訊息裡提到 skill 名稱的位置
SELECT id, content FROM messages
WHERE session_id = ?
  AND role = 'assistant'
  AND (content LIKE '%skill_view%' OR content LIKE '%先用 %skill%')
```

## 已知限制

1. **skill 載入本身不寫進 messages 表**——只能從「assistant 明說要載入哪個 skill」反推
2. **delegate_task 產出的 child session 寫進 sessions 表(parent_session_id)**——但 terminal background 跑的 worker **不寫**
3. **context compaction 會把對話開頭壓縮**——前 N 條訊息內容被改成 `[CONTEXT COMPACTION — REFERENCE ONLY]`,失去「那時載入了什麼 skill」的細節
4. **MEMORY 跟 state.db 可能不一致**——MEMORY 寫「跑了 handoff chain」、state.db 顯示無 children。**以 state.db 為準**(它是事實,MEMORY 是摘要)

## 教訓(2026-06-16)

> 2026-06-16 使用者問「之前在設計學校佈告欄網站時用了哪些技能」,session_search 撈到的全是 metacognitive-learner cron 提到 school-bulletin 的片段(被 FTS5 污染),撈不到 2026-06-11 那次 user 主對話。**改查 state.db 直接撈 sessions 表 → 找到 `20260611_140758_6e5934c5`(244 條訊息,「學校公告系統建置」)→ 統計 tool_name 發現 skill_view 只有 2 次** → **真正能 100% 確認的只有 1 個 skill(trial-and-error)**,其他(nextjs、supabase-migration 等)MEMORY 推測可能有但無法證實。

**If** 使用者問「之前那次用了哪些 skill」
**Then** 不要直接從 MEMORY 答(可能記錯或過時)
**Then** 先試 session_search,被污染時改查 state.db
**Then** 誠實告知「state.db 能確認到 N 個 skill,其他是推測,無法 100% 驗證」

**驗證方式**:
```bash
ls -la ~/.hermes/state.db  # 確認存在
python3 -c "import sqlite3; conn=sqlite3.connect('/home/hoonsoropenclaw/.hermes/state.db'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM sessions'); print(f'sessions: {cur.fetchone()[0]}')"
```
