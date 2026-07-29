# Subagent Decision Transparency in Isolated Contexts

> **固化時間**: Cycle 559 (2026-07-29)
> **來源事件**: engineering-lead tyai-clone T1 (Cycle 548-549)

## 核心問題

`delegate_task` 的 subagent 在 isolated context 運行，main session 無法觀測其 intermediate decisions。隔離是工具約束、不可改變。**透明揭露是隔離架構下唯一的 trust 建立機制。**

## 驗證案例

### ✅ 合規案例（engineering-lead tyai-clone T1）
- 5 個技術實現決策：Next.js 16 而非 14、Tailwind 4 globals.css 而非 tailwind.config.ts、`zh-Hant` lang、navbar 下拉不展開、未 push remote
- 全部在回報末尾「⚠️ 透明揭露：不在 ticket 範圍的決策」區塊揭露
- main session 合規接收

### ❌ 不合規案例（school-bulletin 22）
- token 在 heredoc 直接暴露
- 未揭露、未等待指令
- → GH013

## If→Then 規則

### If→Then #1（揭露觸發條件）
> **If** subagent 在 isolated context 執行時，遇到 ticket/scope 未覆蓋的決策節點
> **Then** 在回報時主動列舉「⚠️ 透明揭露：不在 ticket 範圍的決策」區塊，格式：
> 1. **決策描述**（精確）
> 2. **理由**（為何這樣選）
> 3. **影響**（scope/DOD/後續 sprint）

### If→Then #2（main session 接收原則）
> **If** subagent 回報含「透明揭露」區塊
> **Then** 視為合規回報，除非揭露的決策直接破壞核心約束（安全/隱私/已知偏好）
> **原因**：subagent 有 scope 裁決權、main session 有最終核准權

### If→Then #3（決策 Priority Tier）
| Priority | 觸發條件 | 行為 |
|----------|---------|------|
| P0 安全 | token/secret/GH013 相關 | **從不自主決策**，立即回報 |
| P1 偏好 | 已知使用者偏好（格式/工具/路徑） | 依 trial-and-error 執行 |
| P2 技術 | 純技術實現選擇（框架版本/設定位置） | 自行裁決 + 透明揭露 |

## 與現有章節的關係

- **補充「Sub-Agent Handoff Contract Design」**：現有章節定義了 4 個 handoff 元素（task/context/constraints/output_format），但未覆蓋 subagent 執行中的 scope 外決策處理
- **補充「Integration-Fix SOP」**：Integration-Fix 是事後補救；透明揭露是事前預防
- **不衝突**：HARD TRIGGER 被動觸發（trial-and-error）仍有效，這是主動揭露的互補雙軌

## 驗證命令

```bash
# 確認 reference 存在
ls ~/.hermes/skills/agent-orchestration-multi-agent-optimize/references/subagent-decision-transparency-20260729.md
```
