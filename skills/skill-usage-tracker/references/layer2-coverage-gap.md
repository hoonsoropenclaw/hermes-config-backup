# Layer 2 覆蓋盲區：為何「2 個 SKILL.md」不等於「只做了 2 件事」

**日期**：2026-06-20
**驗證者**：metacognitive-learner cycle

---

## 問題

使用者問：「之前做學校公告系統時用了哪些技能？」
`session_skill_logger.py` 回覆：「2 個 SKILL.md — `mmx-cli` + `school-bulletin-system`」

這看起來很少，但實際上這個 session（244 messages）的工作量涵蓋了：
- Next.js 15 架構决策
- Supabase PostgreSQL schema 設計
- Vercel 部署流程
- RBAC 權限矩陣設計
- **這些都没有獨立 SKILL.md 定義**

同樣的問題出現在 06-16 圖片生成 session：
- `session_skill_logger.py` 顯示 2 個 SKILL.md（`mmx-cli` + `school-bulletin-system`）
- 但 `messages.tool_name` 分佈顯示：大量 `execute_code:11 + vision_analyze:10 + terminal:7` — 代表隠性工作量（Prompt Engineering 推理、content filter 對抗、多輪試错）

---

## 根因

**Layer 2 追蹤的是「SKILL.md 被呼叫的次數」，不是「完成任務所需的知識廣度」**

Hermes 的 SKILL.md 是任務級別的封裝（一個公告系統、一個 hr workflow），但任務內的**推理、决策、Prompt Engineering** 這些「活的知識應用」沒有封裝成 SKILL.md，所以 `skill_view` 永遠看不見它們。

---

## 為何這不是 bug

「模型内部推理」本來就没有 SKILL.md：
- 06-16 的 comic vs line art 風格稳定性差異 → 是模型能力知識，不是「工具使用」
- 06-16 的 `image-01` content filter 行為 → 是試错得來的 Pattern，不是「有文件的流程」
- 這些知識目前以 trial-and-error 條目存在，不算「技能」

---

## 實用應對

當使用者問「用了哪些技能」時：

```python
# 步驟 1：取得 SKILL.md 清單
skills = session_skill_logger.py --session <id>

# 步驟 2：取得工具呼叫分佈（工作量代理指標）
import sqlite3
cur.execute("""
    SELECT tool_name, COUNT(*) as cnt
    FROM messages WHERE session_id = ?
    AND tool_name IS NOT NULL
    GROUP BY tool_name ORDER BY cnt DESC
""", (session_id,))

# 步驟 3：誠實告知覆蓋範圍
```

| 層次 | 可追蹤？ | 如何呈現 |
|------|---------|---------|
| 有 SKILL.md 的技能 | ✅ Layer 2 完美覆蓋 | `mmx-cli`、`school-bulletin-system` |
| 架構决策（没有 SKILL.md） | ❌ 看不見 | 從 `execute_code`/`write_file` 次数推估 |
| Prompt Engineering 知識 | ❌ 看不見 | 從 `vision_analyze`/`execute_code` 次数推估 |
| 工具使用熟練度 | ✅ 可從 tool_name 推估 | `terminal`/`execute_code` 次數多 = 大量 shell/Python 工作 |

---

## If→Then

**If** 使用者問「這個任務用了哪些技能」且 `session_skill_logger` 只顯示 1-2 個 SKILL.md
**Then** 誠實說明「SKILL.md 載入覆蓋不到 Prompt Engineering 推理和架構决策」，並用工具分佈補充工作量描述

**If** 使用者追問「那具體用了什麼知識」
**Then** 從 `messages.tool_name` 分佈推估（如大量 `vision_analyze` = 模型在視覺確認），並說明「隐性知識目前以 trial-and-error 條目存在，沒有封裝成 SKILL.md」
