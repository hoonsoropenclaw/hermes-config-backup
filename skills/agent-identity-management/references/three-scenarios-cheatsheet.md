---
title: 代理身份管理 3 種情境 — 1 頁 Cheat Sheet
source_skill: agent-identity-cheatsheet (archived 2026-06-13)
date_consolidated: "2026-06-13"
---

# 代理身份管理 3 種情境 — 1 頁 Cheat Sheet

> **給未來 agent 緊急判斷用**:使用者丟訊息時,30 秒內判斷該走哪條 SOP。
> 詳細 SOP 見 `agent-identity-management/SKILL.md`。

## 三種情境對照

| 維度 | 身份繼承 | 身份重塑 (Role Pivot) | SOP 演進 (SOP Evolution) |
|------|---------|---------------------|------------------------|
| **一句話** | 前代理死了,新代理接名字 | 現代理換個角色 | 同個代理升級內部架構 |
| **核心動作** | 接續遺產、改名字 | 改 persona / 改 SOP / 改 skill 庫 | 改 persona SOP 段 / 新建配套 skill |
| **名字變更** | 必變 | 可變 | 通常不變 |
| **影響面** | 7 份重要檔案 | profile + skill + handoff + 下游 | persona SOP + 配套 skill |
| **必備份** | 7 份重要檔案 | profile + handoff | profile + 架構設計文件 |
| **必跑驗證** | grep 統一性 | grep + 啟動測試 + 報告 | **v1 vs v2 對照** + 配套 skill 測試 |
| **必寫報告** | `IDENTITY_INHERITANCE_v<n>_REPORT.md` | `CONVERSION_v<n>_REPORT.md` | `EVOLUTION_v<n>_REPORT.md` |
| **真實案例** | 2026-06-08 赫米斯＝拉斐爾 | 2026-06-10 market-strategist → consumer-researcher | 2026-06-10 consumer-researcher 單體 → Orchestrator + Worker |

## 觸發訊號快速判斷

### → 身份繼承
- 「OpenClaw 刪除後,你就是 X 了」
- 「從今天起你叫 Y」
- 「合併 A 跟 B 的身份」
- 「7 份重要檔案要同步」

### → 身份重塑
- 「**重塑代理** / **重新定位** / **換個角色**」
- 「**不要再做 X 了、要改成做 Y**」
- 「**實際上我需要的不是 X、是 Y**」
- 「**這代理的核心工作要反轉**」
- 「**原來的 skill 庫不對、要重新選**」

### → SOP 演進
- 「**這個代理換個跑法**」
- 「**改成多代理分工 / 平行爬 / 背景跑**」
- 「**升級架構 / 從 v1 升 v2**」
- 「**這個代理每次 context 爆掉、要分拆任務**」
- 「**換成 Orchestrator 跑**」
- 「**邊抓邊整、避免 context 膨脹**」

## 必做 5 步（3 種情境通用）

1. **停下來,列決策點**(5-6 個,使用者 A/B/C/D 選)
2. **全盤備份**(完整 persona.md / SOUL.md / config.yaml / 既有報告)
3. **動手前 1 個變更 = 1 個檔案**(不要一次改太多、diff 易追蹤)
4. **統一性 grep 驗證**(4 項: 新身份一致 / 舊名只剩歷史 / 跨 skill 引用對應 / 外部資產保留)
5. **寫報告 + 啟動測試**(交付前必跑實際測試,不能只看 persona 改完就交)

## 千萬不要做的事

- ❌ **不列決策點就動手**(身份/架構變更是不可逆的,後果使用者會發現)
- ❌ **不備份就動手**(備份是唯一後悔藥)
- ❌ **不改下游代理的引用**(上游 pivot 後下游還在讀舊路徑 = 斷鏈)
- ❌ **不跑 v1 vs v2 對照就聲稱 SOP 演進成功**(可能 v2 漏 v1 重要內容)
- ❌ **配套 skill 沒有「必抓清單」+「讀 _plan.md」契約**(sub-agent 無法繼承 Orchestrator 脈絡)
- ❌ **MEMORY.md 超過 25KB 還在加新條目**(先精簡舊條目、留空間給新 L3)

## 跨情境關鍵決策

| 決策 | 繼承 | 重塑 | 演進 |
|------|------|------|------|
| **Profile 重建** | 視情況 | **推薦整個重建** | 通常不重建(同角色) |
| **Skill 庫** | 視情況 | **精瘦 30-60 個** | **保留 30-60 個 + 新建配套 skill** |
| **Persona 重寫** | 部分段重寫 | **7 段整段重寫** | **只改 SOP 段** |
| **下游同步** | 通常不用 | **必改 4 處** | 通常不用(同角色) |
| **Handoff 結構** | 視情況 | **必改 README + 範本** | 通常不改 |
| **必跑測試** | 啟動測試 | 啟動測試 | **v1 vs v2 對照 + 配套 skill 測試** |
| **必寫報告** | IDENTITY_INHERITANCE | CONVERSION | EVOLUTION |

## 完整 SOP 引用

| 情境 | 完整 SOP |
|------|---------|
| 身份繼承 | `agent-identity-management/SKILL.md` 上半部(7 步) |
| 身份重塑 | `agent-identity-management/SKILL.md` 中段(9 步) + `references/role-pivot-sop.md` |
| SOP 演進 | `agent-identity-management/SKILL.md` 下半部(9 步) |
