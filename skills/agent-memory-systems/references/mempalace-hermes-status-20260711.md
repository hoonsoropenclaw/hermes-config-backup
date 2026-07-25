# MemPalace × Hermes Integration Status (2026-07-11)

## 拓撲位置

| 組件 | 路徑 | 備註 |
|------|------|------|
| MemPalace DB | `~/.mempalace/palace/` | 不同於 `~/.hermes/` |
| MemPalace MCP | `mcp_mempalace_*` tools | 全工具已啟用 |
| Hermes state.db | `~/.hermes/state.db` | session 歷史 |
| HERMES MEMORY.md | `~/.hermes/MEMORY.md` | ~16.9 KB |

## MemPalace 規模（2026-07-11）

- **276 drawers** across 8 wings, 16 rooms
- Wings: `wing_raphael`(178), `mempalace_palace`(76), `learning_system`(8), `hermes`(8), `wing_拉斐爾`(3), `projects`(1), `raphael`(1), `evolution`(1)
- 主要房間：`diary`(182), `general`(76), `if-then`(5), `if_then_experiences`(5), `mmx-image-gen`(1)
- Protocol: `mempalace__mempalace_protocol`（AAA級壓縮格式）

## Phase 1 搜尋優先順序（缺口確認）

**現況**：
- `session_search` FTS5：被 cron 輸出污染 → 改用 state.db 直接查詢
- `mempalace_search`：作為 fallback，分數閾值 0.4
- LLM re-rank：最終備援，分數閾值 0.6

**缺口**：`mempalace_search` 是 fallback，不是 Phase 1 primary。
但 MemPalace 有 276 drawers 涵蓋 episodic（對話經驗）和 procedural（if-then 經驗），
適合作為 Phase 1 的 primary 知識庫。

**修正方向（不緊急）**：
- Phase 1 三層搜尋應改為：MemPalace primary → session_search secondary → LLM re-rank tertiary
- 這樣可以繞過 FTS5 cron 污染問題

## If→Then

```
If [metacognitive-learner Phase 1 缺口掃描]
Then [先用 state.db 直接查詢（繞過 FTS5 cron 污染），
      再用 mempalace_search（276 drawers, 8 wings），
      最後才 LLM re-rank]
原因：MemPalace 已有豐富的 episodic + procedural 記憶，
     且 MCP 工具已啟用。session_search 是輔助。

If [查詢使用者偏好或穩定事實]
Then [查 HERMES MEMORY.md（16.9 KB，結構化），
      而非 MemPalace（memorial 用途）]
原因：MEMORY.md 是使用者偏好的正規記錄位置

If [查詢編碼任務、架構追蹤、檔案依賴]
Then [使用 Glob/Grep/Read 的 agentic retrieval，
      而非 mempalace_search]
原因：2026 研究確認 agent-as-retriever 優於 vector RAG
```
