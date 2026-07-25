# delegate_task Failure Modes（CAMEL Inception Prompting）

> Source: CAMEL (NeurIPS 2023, arXiv:2303.17760) + Hermes Issue #375
> 2026-06-16 新增

## 4 個常見 Sub-Agent Delegation 失敗模式

CAMEL 研究發現 LLM agent 互相 delegation 時，4 種失敗模式系統性發生，直接對應 Hermes `delegate_task` 可觀察的症狀：

| 失敗模式 | 定義 | Hermes 中可觀察症狀 |
|---|---|---|
| **Role-Flipping** | sub-agent 停止執行任務，開始像 parent 一樣問問題或提建議 | sub-agent 回「我建議你...」「你需要我專注哪部分？」「我應該先做什麼？」 |
| **Instruction Echoing** | sub-agent 只複述任務內容，不實際執行，摘要看起來做了但 0 tool calls | 摘要豐富但 `grep` 找不到任何 `terminal(`、`read_file(`、`browser_` 等實際 tool call |
| **Flake Replies** | sub-agent 給模糊、不確定的回覆 | 「可能還好」「需要進一步調查」「初步看起來沒有大問題」等於沒給 |
| **Infinite Loops** | sub-agent 重複同樣的錯誤嘗試直到 iteration 耗盡 | 同一個 SyntaxError 修了 10 次還失敗，`last_error` 顯示反覆相同錯誤 |

## CAMEL Inception Prompting 解法

CAMEL 在 sub-agent prompt 中注入 3 個約束組件來預防：

### 1. Role Constraint（角色約束）
明確聲明 sub-agent 的身份邊界：
```
你是獨立的 task-executor。
你的角色是 <具體職責>，不是 <排除的行為>。
你沒有 clarification 的對象——遇到不確定的假設，直接做合理預設值。
```

### 2. No-Question 約束
禁止 sub-agent 提問，有假設直接做：
```
不要問問題。
遇到不明確的地方，根據以下假設執行：
- <假設 1>
- <假述 2>
如果關鍵資訊缺失，預設 <合理預設值> 並繼續執行。
```

### 3. 終結性約束
明確结束條件，防止重複：
```
完成後，直接輸出結構化摘要：
## 完成的工作
## 發現的問題（如有）
## 檔案修改（如有）
不要解釋過程、不要呼應 prompt、不要說「我建議」。
```

## Hermes delegate_task 現狀（Issue #375）

`delegate_tool.py` 的 `_build_child_system_prompt()` 目前**缺少**這 3 個組件，是為何 Flake Replies 和 Role-Flipping 在 Hermes sub-agent 中常見的原因。

**受影响的情境**：
- `engineering-lead` 派遣 sub-agent 到 `round-3b-parallel-m3` 的 Todo App 開發
- `consumer-researcher` 的 web-worker 派遣
- 任何 `delegate_task(tasks=[...])` 的 batch 模式

## If→Then 規則

**If** sub-agent 回覆出現「我建議...」「專注哪部分」「應該先問」等 Role-Flipping 症狀
**Then** 在下次 `context` 中強制加入 No-Question 約束 + 終結性格式，示例如：
```
你是獨立的 task-executor。遇到不確定的地方直接假設，不要提問。
完成後只輸出：## 完成的任務 / ## 發現的問題（無則寫「無」）/ ## 修改的檔案（無則寫「無」）。
```

**If** sub-agent 摘要豐富但實際 tool calls = 0（Instruction Echoing）
**Then** 這代表 context 中的 task 定義太抽象，**必須提供具體檔案路徑 + 預期 action sequence**

**If** 需要建立新的 delegation workflow
**Then** 參考本文件 + `orchestrator-worker-architecture` SKILL.md 的完整架構，不要重複造輪

## 與 orchestrator-worker-architecture 的關係

現有 skill 已有完整的架構原則（context 隔離、worker 只整理事實、Summarizer 必讀 _plan.md）。本文檔補充的是：**當 sub-agent 回覆出現 4 種 failure mode 時，如何在 prompt 層修復**。

兩個檔案協作：
- `orchestrator-worker-architecture` → 架構層設計
- `delegate-task-failure-modes.md` → prompt 層 failure 預防

## 參考

- CAMEL: arXiv:2303.17760 (NeurIPS 2023)
- Hermes Issue #375: Inception Prompting for delegation hardening
