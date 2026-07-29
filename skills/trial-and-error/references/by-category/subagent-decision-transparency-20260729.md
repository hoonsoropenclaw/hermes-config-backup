# Subagent 決策透明揭露原則（2026-07-29 固化）

## 來源事件
- **Cycle 548-549**：engineering-lead 執行 tyai-clone T1 ticket 時，自主做了 5 個超出 ticket 範圍的決策（Next.js 16 而非 14、Tailwind 4 globals.css 而非 tailwind.config.ts、zh-Hant lang、navbar 下拉不展開、未 push remote）
- **透明揭露機制**：engineering-lead 在回報末尾主動列舉「不在 ticket 範圍的決策」區塊
- **效果**：即使有 5 個自主決策，因有透明揭露，main session 能在第一時間知道範圍偏移、避免事後爭議

## 為何重要
- **協作契約偏移**：赫米斯架構中 subagent（engineering-lead）在 isolated context 運行，main session 無法即時監控其決策
- **Rule 12 自作主張**：subagent 本身不等於自作主張——關鍵在於「揭露」而非「不行動」
- **透明度彌補隔離性**：subagent 隔離是工具約束、無法改變；透明揭露是唯一能在此約束下維持 trust 的手段

## 核心 If→Then

### If→Then #1（subagent 決策揭露觸發條件）
> **If** subagent 在 isolated context 執行時，遇到 ticket/scope 未覆蓋的決策節點
> **Then** 在回報時主動列舉「⚠️ 透明揭露：不在 ticket 範圍的決策」區塊，格式為：
> 1. **決策描述**（精確、不可模糊）
> 2. **理由**（為何這樣選）
> 3. **影響**（對 scope/DOD/後續 sprint 的影響）
> **原因**：隔離環境下 main session 無法觀測 intermediate decisions，透明揭露是唯一 trust 建立機制

### If→Then #2（main session 如何接收 subagent 透明揭露）
> **If** subagent 回報中出現「透明揭露」區塊
> **Then** main session 視為「合規回報」而非「需要修正的信號」——除非揭露的決策直接破壞了核心約束（安全/隱私/已知偏好）
> **原因**：subagent 有 scope 裁決權、main session 有最終核准權；兩者不是上下屬、是協作合約的兩個角色

### If→Then #3（subagent 自主判斷的底線）
> **If** 觸發條件涉及安全邊界（token 暴露、GH013、secret scan）→ **從不自主決策**、立即回報等待指令
> **If** 觸發條件涉及使用者已知偏好（格式/工具/路徑）→ 依 trial-and-error 已知偏好執行
> **If** 觸發條件純屬技術實現選擇（框架版本、色票位置）→ 自行裁決 + 透明揭露
> **原因**：安全/隱私 > 已知偏好 > 技術實現；三層 priority 決定何時揭露、何時等待

## 與既有 SOP 的關係
- **不衝突**：trial-and-error 的「HARD TRIGGER 被動觸發」仍有效；此 SOP 補充 subagent 主動揭露場景
- **與 brandkit D3 差異**：brandkit 的 data-without-consumption 是「Skill 未消費已存在的 data」；此 SOP 是「subagent 在隔離環境下超出 ticket 的決策」

## 驗證案例
- ✅ engineering-lead T1：5 個技術實現決策，全部揭露，main session 合規接收
- ❌ school-bulletin 22 事件：token 在 heredoc 直接暴露（未揭露、未等待）、導致 GH013
