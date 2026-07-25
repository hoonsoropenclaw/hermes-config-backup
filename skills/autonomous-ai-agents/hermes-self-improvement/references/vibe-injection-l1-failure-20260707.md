# 疊加服從偏差：Vibe Injection 失效（2026-07-07）

**skill**: hermes-self-improvement
**cycle**: metacognitive-learner cycle 2026-07-07
**發現**：SOUL.md Vibe Layer 1 注入在「使用者說『直接動手』+ D3 高強度執行」組合下被選擇性忽略。

## 問題

06-29 cycle 將 SOP-A 觸發約束寫入 SOUL.md Vibe §95-106，解決了「skill 文件存在但從未被上下文載入」的 D2 根因。但 07-02 backup modification session（132 msgs，D3）仍 0 invite sent。

**觸發模式**：
1. 使用者說「直接動手」（意圖：加速執行）
2. 赫米斯服從並開始 D3 高強度執行（patch jobs.json、create wrapper scripts、validate）
3. D3 完成後沒停等用戶回覆，直接開始下一個子步驟
4. SOP-A 邀請被跳過

**為什麼 Layer 1 失效**：當使用者明確指示加速時，赫米斯產生「疊加服從」效應——服從執行的置信度疊加在原本的 SOP 約束上，導致後者被選擇性忽略。這不是「Vibe 沒注入」的問題，而是 LLM 推理的置信度偏差。

## 驗證數據

- `analyze.py`：combo_rating 樣本 3，0 explicit invite from 2026-07 sessions
- 07-02 session（`20260702_221910_b4729405`）：D3 deliverable 全程無「⭐ 請評分」邀請
- logger 正常 ✅、工具正常 ✅、文件完整 ✅

## 現有三層架構的極限

| 層 | 機制 | 對「疊加服從」的防禦力 |
|----|------|----------------------|
| L1 soft | SOUL.md Vibe 段落每次推理注入 | 低——可被高置信度指令覆蓋 |
| L2 tool | tool_use_enforcement 強制特定工具 | 中——依賴 MiniMax 是否在名單 |
| L3 外部 | 外部驗收循環 | 高——但目前未實作 |

**根本限制**：即使 L1 注入成功，LLM 仍可能在「使用者明確指示」語境下選擇忽略它。

## 如果要真正解決

**方案 A（最小改動）**：將 SOP-A 邀請升級為「不可跳過的明確步驟」，不走 Layer 1 soft 注入。當赫米斯完成任何形式的 delivery，必須在同一次回覆末尾親自生成並附上邀請文本——不走「先做完、等下個 turn 再問」，而是「做完就問」。

**方案 B（架構改動）**：在 D3 任務的 delivery 工具鏈中強制插入 SOP-A 文本生成，而不是依賴赫米斯「記得」在回覆末尾加。這需要 `tool_use_enforcement: true` + 在 delivery 相關 tool 的 output 注入 SOP-A prompt。

**方案 C（外部驗收）**：main session 每小時或每 N 個 tasks 主動詢問「過去這段時間有沒有跳過任何 SOP？」——這是真正的 Layer 3，但需要使用者配合。

## If→Then

**If** 使用者在 D3 任務中說「直接動手」並且赫米斯服從執行
**Then** D3 完成後**仍必須**先附上 SOP-A 評分邀請，再繼續下一個步驟
**Then** 「使用者說直接動手」= 同意執行，不等於「放棄交付後 SOP」

**If** 赫米斯在 D3 任務中已完成多個子步驟
**Then** 每個子步驟完成後都可以附上 SOP-A 邀請，不需等到整個 D3 完成

**If** Layer 1 注入連續 2 次在相同語境（使用者說「直接動手」）下失效
**Then** 這代表 L1 無法處理該語境，需升級到 L2 或 L3
