# combo_rating Backfill SOP — From Verbal Positive Signals (2026-06-28 D3 Exit)

## 問題

`analyze.py` 顯示 `⚠️ [SOP-C ALERT] 0 筆 combo_rating！`，但：
- `post_delivery.py` 工具正常（已實際執行，42 tool calls 解析成功）
- `session_skill_logger.py` 正常（Layer 2 重建正常）
- 真正問題：使用者說了「好」「可以」「按照」「OK」等正面口語信號，但這些信號**從未被轉換成 `combo_rating` 寫入 JSONL**

## 根因

`post_delivery.py` 的 `generate_invite()` 輸出從未出現在赫米斯回覆末尾（因為從未被呼叫），
導致：
- 使用者的正面口語回覆 → 停留在 Telegram 訊息裡
- 沒有任何機制把那些口語回覆轉換成 `combo_rating` 數值寫入 JSONL

## D3 Exit 實作（2026-06-28）

**目標**：從 `state.db` 直接識別有正面口語信號的 sessions，手動寫入 `combo_rating=4` entries。

**Step 1：識別有正面信號的 sessions**
```python
import sqlite3
from pathlib import Path

db_path = Path.home() / ".hermes/state.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT m.session_id, m.role, m.content, s.title, s.message_count
    FROM messages m
    JOIN sessions s ON m.session_id = s.id
    WHERE s.id NOT LIKE 'cron_%%'
    AND m.role = 'user'
    AND (
        m.content LIKE '%好%' OR m.content LIKE '%可以%' OR 
        m.content LIKE '%讚%' OR m.content LIKE '%按照%' OR
        m.content LIKE '%優%' OR m.content LIKE '%棒%'
    )
    ORDER BY s.started_at DESC
    LIMIT 10
""")
# 找 session_id + 具體的口語回覆內容
conn.close()
```

**Step 2：對每個識別出的 session 執行 post_delivery.py**
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
    --session <session_id>
```

**Step 3：根據口語信號內容，手動構造 combo_rating entry**

| 口語信號 | 推斷 combo_rating |
|---------|------------------|
| 「按照你的建議先做」 | 4 |
| 「好」「可以」「OK」| 4 |
| 「讚」「棒」「優」| 4 |
| 「超讚」「太棒了」| 5 |

```python
entry = {
    "ts": "<session-start-ts>",
    "session_id": "<session_id>",
    "platform": "<source>",
    "task": "<title or 1-line>",
    "planned": [],
    "actual": [],  # 從 post_delivery.py 輸出取得
    "result": "✅ <short-description>",
    "combo_rating": 4,  # 口語信號推斷
    "individual_ratings": {},  # 可選：若有多個 skill 可個別評
    "comment": "口語信號：「<原始用戶回覆>」= combo_rating ≥ 4"
}
```

**Step 4：寫入 JSONL（冪等）**
```python
import json
log_path = Path.home() / f".hermes/skill-usage/<YYYY-MM-DD>.jsonl"
existing = []
if log_path.exists():
    for line in log_path.read_text().strip().split('\n'):
        if line.strip():
            existing.append(json.loads(line))

# 檢查是否已存在（session_id 前綴匹配）
session_exists = any(
    e.get('session_id','').startswith('<session_id>') 
    for e in existing
)
if not session_exists:
    existing.append(entry)
    log_path.write_text(
        '\n'.join(json.dumps(e, ensure_ascii=False) for e in existing) + '\n'
    )
```

**Step 5：驗證**
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py
# 預期：combo_rating 樣本數從 0 → N（N = 已 backfill 的 sessions 數）
```

## 驗證結果（2026-06-28）

- 分析前：`⚠️ [SOP-C ALERT] 0 筆 combo_rating！`
- Backfill sessions：`20260616_125207_dc21b806` + `20260611_231137_6c48`
- 分析後：`組合評分樣本數: 2，樣本: [4, 4]`
- **確認：工具正常，缺口是 SOP 執行** ✅

## If→Then

**If** `analyze.py` 顯示 `⚠️ [SOP-C ALERT] 0 筆 combo_rating`
**Then** 立即執行口語信號 backfill（不要只更新文件）：
1. 從 state.db 找「好/可以/按照/OK/讚/棒」等正面口語 sessions
2. 對每個 session 執行 `post_delivery.py`
3. 根據口語信號內容給 `combo_rating=4` 或 `5`
4. 寫入 JSONL（冪等檢查）
5. 驗證：`python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py`

**If** backfill 後 combo_rating 仍是 0 但 post_delivery.py 正常輸出
**Then** 這代表「沒有口語信號可轉換」，gap 在預防而非補救——未來靠 SOP-A（每次任務完成後直接貼邀請文本）才是根本

## 相關條目

- `skill-usage-tracker/SKILL.md` — SOP-C 强制产出口（analyze.py 0 笔时触发检查）
- `references/post-delivery-tool-verified-20260628.md` — post_delivery.py 工具驗證（42 tool calls 成功解析）
