# session_skill_logger.py --write-log 重複寫入 Bug（2026-06-20）

## 問題

`session_skill_logger.py --write-log` 每次呼叫都會 append 新 entry，沒有 dedup 機制。

**實測**：對同一 session（06-15）執行兩次 `--write-log`，導致 `~/.hermes/skill-usage/2026-06-20.jsonl` 出現 2 個 identical entry。

**觸發條件**：`--write-log` 在同一 session 上被呼叫兩次（metacognitive-learner 重建歷史 session 時可能重複呼叫）。

---

## 解法

在 append 之前檢查該 session 是否已存在於今日 log（見下方 If→Then）。

---

## If→Then

**If** `session_skill_logger.py --write-log` 輸出包含同一 session_id 重複 entry
**Then** 手動刪除 `~/.hermes/skill-usage/<date>.jsonl` 內的重複行，或下次呼叫前先 grep 確認

**If** 需要對同一 session 多次查詢（調試用）
**Then** 使用 `--json` 直接輸出到 stdout，不要用 `--write-log`

---

## 預防

下次更新 `session_skill_logger.py` 時，確保 `--write-log` 有 dedup 檢查。

**相關條目**：
- `references/auto-trigger-gap.md` — Layer 1 自覺觸發失效的根因
- `references/layer2-coverage-gap.md` — Layer 2 覆蓋盲區
