# skill-usage-tracker D2→D3 Exit — 口語回饋自動推斷落地（2026-06-21）

**cycle**: metacognitive-learner cycle 2026-06-21
**問題**：連續 2 個 cycle（06-20、06-21）識別了「skill-usage-tracker 評分從未執行」，但只記錄不實作。

## 根因

- 使用者 2026-06-16 明確要求「每次任務完成後評分」
- 132 個非 cron session 中，標準評分邀請格式（⭐ + 請評分）發送次數 = **0**
- `analyze.py` 的口語回饋 auto-parse（Weak Reward）在 v1.4 SKILL.md 文件裡有 If→Then 規則，但 **script 從未實作 `parse_weak_reward()`**
- 累積 6 筆重構 entry（Layer 2 正常），但 0 筆 combo_rating（Layer 3 失效）

## D3 Exit 本次執行（2026-06-21）

1. **SKILL.md v1.5**：新增「口語回饋自動轉換規則」段落 + 更新 If→Then（說明 Layer 2 只重建 skill 載入、不主動收集偏好）
2. **analyze.py**：新增 `parse_weak_reward()` 函數 + 在 `load_entries()` 中自動呼叫（in-place，不修改 log 檔案）
3. **驗證**：`python3 scripts/analyze.py` → 6 筆 entry 中口語關鍵字 auto-parse 產生 combo_rating，報告可正常產出偏好清單

## 實作後驗證命令

```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py
# 預期：combo_rating 樣本數 > 0（含自動推斷）
# 預期：報告末尾顯示 🔁 標記（weak reward inferred）
```

## VARS Paper 參考（理論強化）

**arXiv:2603.20939 — User Preference Modeling for Conversational LLM Agents**
- 核心發現：從「弱監督信號」（口語關鍵字）自動推斷偏好，不需要每次填表
- 關鍵機制：`Dual-Vector User State` = Long-term vector（跨 session） + Short-term vector（session 內）
- 赫米斯落地簡化版：keyword matching ("好"→4, "不行"→2, "普通"→3)
- 不需要 embedding model 或 reranker，Python regex 即可做到

## If→Then（防止下次再掉進同一陷阱）

**If** 發現同一個 gap 已經連續 2 個 cycle 被識別為「優先缺口」
**Then** 第 3 個 cycle **必須**升級到 D3，具體動作：
  1. 直接修改程式碼（script / SKILL.md），不要 research paper
  2. research paper 的發現如果不能在 5 分鐘內總結成「可以做什麼」，就跳過

**If** 口語 auto-parse 的 keyword set 不夠用
**Then** 先查 log 檔案（`~/.hermes/skill-usage/*.jsonl`）裡 comment 欄位的實際內容，再擴充關鍵字集合，不要猜
