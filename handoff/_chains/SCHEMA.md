# Handoff Chain Schema（鏈條結構定義）

> 一條「合法 handoff 鏈」必須滿足什麼條件、怎麼描述、怎麼驗證。
> 給 default orchestrator + 未來 AI 看。

---

## 鏈的最小定義

一條 handoff 鏈 = **1 個 project** 走過 **N 個代理**、產出 **N 個交付物**、每個代理收到上個代理的交付物作輸入。

最少 1 個代理（純架構評估）、最多無限（理論上、實務 5-7 個最常見）。

---

## 鏈的 4 個必要元素

| 元素 | 必填？ | 說明 | 範例（@專案）|
|------|-------|------|--------------|
| **project-slug** | ✅ 必填 | kebab-case、`~/.hermes/handoff/<slug>/` 目錄名 | `skill-language-exchange-platform` |
| **chain stages** | ✅ 必填 | 至少 1 個 stage、每個 stage 標明代理 + 交付物 | stage 1: consumer-researcher → consumer-needs-research.md |
| **skip reasons** | ⚠️ 跳過階段才填 | 為什麼這個 stage 不需要 | （@專案沒跳過、5 階段全跑）|
| **trigger mode** | ✅ 必填 | `sequential`（串接）/ `parallel`（平行）| sequential |

---

## stage 的標準格式

每個 stage 在 `_plan.md` 內的寫法：

```markdown
- 階段 N: <agent-name> → 交付物: <filename>
  - 輸入: <上個 stage 的交付物檔名>（第一階段可省略）
  - 觸發命令: <agent-name> chat -q "<給這個 stage 的 prompt>" --cli
  - 預期產出大小: <byte 估計>
  - 預期時間: <分鐘估計>
```

---

## 合法鏈的 6 條硬規則

### 規則 1: 輸入來自上個 stage
**每個 stage（除了第一個）必須有「輸入」欄位、引用前個 stage 的交付物檔名**。
原因：避免「無中生有」—— 每個代理都要有上個代理的產出才能開始。

### 規則 2: 交付物檔名在 `_template/` 內有對應範本
**5 階段標準鏈的交付物**（consumer-needs-research / prd / architecture / sprint-report / qa-signoff）在 `~/.hermes/handoff/_template/` 都有 `.template.md` 範本。如果某個 stage 的交付物**沒對應範本**、代表這是**新交付物類型**、要先建範本。

### 規則 3: 代理存在於 `hermes profile list`
**每個 stage 寫的 `<agent-name>` 必須是已建立的 profile**。`hermes profile list` 查得到、且有 `~/.local/bin/<agent-name>` wrapper。

```bash
# 驗證命令
hermes profile list | grep <agent-name>
ls ~/.local/bin/<agent-name>
```

### 規則 4: `_plan.md` 在 dispatch 第一個代理前寫完
**default orchestrator 必須在觸發第一階段代理前** 寫好 `_plan.md`。不允許「先 dispatch、再補 plan」（失去 chain 規劃意義）。

### 規則 5: `_handoff-log.md` 每 stage append 一行
**每個 stage 完成的當下** append 一行（不是最後才回頭補）。格式：

```
| <ISO timestamp> | <agent-name> | <filename> | <ok/error> | <duration> | <session_id> | <notes> |
```

### 規則 6: 跳過的 stage 必須有 skip reason
**如果某 stage 在 plan 寫了但實際不跑**（中途決策改變），要在 `_plan.md` 加 `## Skipped Stages` 段、記錄原因。不允許「默默跳過」。

---

## 鏈的 3 種型態

### 型態 A: 5 階段標準鏈（消費者驅動）
**起點**：使用者有「想做的東西」但需求模糊
**完整流程**：
```
consumer-researcher → product-planner → system-architect → engineering-lead → test-engineer
```
**交付物**：`consumer-needs-research.md` → `prd.md` → `architecture.md` → `sprint-report.md` → `qa-signoff.md`
**目前唯一真實鏈**：`skill-language-exchange-platform`（@專案）

### 型態 B: 重構/接手既有 codebase（程式碼驅動）
**起點**：使用者有「既有 .exe / .class / legacy code」、要重構或翻譯
**規劃中**：
```
decompiler-agent (2026-Q3 規劃) → refactor-architect → engineering-lead → test-engineer
```
**跳過**：consumer-researcher / product-planner（沒有新需求、接手的是既有 code）
**交付物**：`decompile-report.md` → `refactor-plan.md` → `sprint-report.md` → `qa-signoff.md`
**目前狀態**：**未建**（decompiler-agent 還沒建、refactor-architect 也還沒建）

### 型態 C: 純評估鏈（單一代理）
**起點**：使用者只要「看個架構 / 評個 PRD / 跑個 audit」
**流程**：只跑 1 個代理、產出 1 份報告
**範例**：
- 只跑 system-architect：`architecture-review.md`
- 只跑 product-planner：`prd-critique.md`
- 只跑 test-engineer：`bug-audit.md`

---

## 鏈條 vs 交付物模板 的對應

| 鏈型態 | stage 1 | stage 2 | stage 3 | stage 4 | stage 5 |
|--------|---------|---------|---------|---------|---------|
| A. 5 階段標準鏈 | consumer-needs-research | prd | architecture | sprint-report | qa-signoff |
| B. 重構鏈 | decompile-report | refactor-plan | (略) | sprint-report | qa-signoff |
| C. 純評估 | architecture-review | - | - | - | - |

**每個交付物檔名必須在 `_template/` 內有對應 `.template.md`、或在 `_chains/EXAMPLE-*.md` 有完整結構描述**。

---

## 驗證鏈條合法的命令

```bash
# 1. plan 存在
ls ~/.hermes/handoff/<slug>/_plan.md

# 2. plan 內引用的代理都建好
grep -oP '階段 \d+: \K[a-z-]+' ~/.hermes/handoff/<slug>/_plan.md | while read agent; do
  hermes profile list | grep -q "^$agent " && echo "✅ $agent" || echo "❌ $agent MISSING"
done

# 3. log 內每個 stage 都有記錄
wc -l ~/.hermes/handoff/<slug>/_handoff-log.md

# 4. 交付物都存在
for f in $(grep -oP '交付物: \K\S+' ~/.hermes/handoff/<slug>/_plan.md); do
  [ -f ~/.hermes/handoff/<slug>/$f ] && echo "✅ $f" || echo "❌ $f MISSING"
done
```

---

## 鏈條演進規則

未來想擴展 / 修改鏈時，**改這 3 個地方**：

1. **新增鏈型態** → 寫到本 SCHEMA.md §型態段
2. **新增交付物範本** → 寫到 `_template/<新交付物>.template.md`、並在本 SCHEMA.md 對應鏈型態的表格補一行
3. **新增代理** → `hermes profile create <new-agent> --clone` + 精瘦 + wrapper + persona，**不用動 SCHEMA**（代理是 component、鏈是 composition）

**不該改的**：本 SCHEMA.md §硬規則段（規則 1-6 是合約、不能因個案改）
