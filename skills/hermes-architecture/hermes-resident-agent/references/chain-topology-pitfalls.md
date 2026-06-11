# Chain 拓樸設計的 5 個常見錯誤

> 2026-06-11 新增。從「@專案」鏈（`skill-language-exchange-platform`）的設計過程中沉澱。
> 涵蓋**拓樸**（誰接誰）、**命名**（@符號學習 vs @專案的混淆）、**規劃文件**（`_plan.md`）、**動態鏈 vs 預設鏈**。

這份是 `chain-automation.md` 的**設計原則補充**。chain-automation.md 講「怎麼用 bash wrapper 跑 chain」、本檔講「**怎麼設計一條 chain 才合理**」。

---

## 錯誤 1：把「skill 觸發標記」誤當成「handoff 鏈名」

### 觸發場景
使用者說「@學習」其實是指 `trial-and-error` skill 的 keyword（試誤學習的觸發標記），**不是鏈名**。
AI 如果不釐清、就會**主動延伸**成「@符號學習」這種不存在的鏈。

### 正確的命名模型
| 概念 | 命名空間 | 範例 |
|------|---------|------|
| **Skill 觸發標記** | skill 維度、`@<keyword>` 形式、定義在 `~/.hermes/skills/<skill>/SKILL.md` frontmatter | `@學習` (= `trial-and-error`)、`@profiling` |
| **Handoff 鏈名** | 專案維度、定義在 `~/.hermes/handoff/<project>/_plan.md` | `@專案` (= `skill-language-exchange-platform`) |
| **常駐代理名** | 角色維度、定義在 `~/.hermes/profiles/<name>/` | `consumer-researcher`、`test-engineer` |

**3 個概念不能混用**：
- 「**@學習是 skill 觸發、不是鏈**」 —— `trial-and-error` skill 的 frontmatter 寫了 `triggers: ['@學習']`，意思是「使用者打 @學習 時自動載入這個 skill」
- 「**@專案是鏈**」 —— 寫在 `_plan.md` 開頭、是這條鏈的名字
- **代理是 component、鏈是 composition** —— 一個代理（如 `consumer-researcher`）可參與多條鏈、但一條鏈的 `consumer-researcher` 階段只存在一次

### If-Then 規則
- **If** 使用者提 `@<keyword>`、且 keyword 在 `~/.hermes/skills/` 找得到對應 skill **Then** 這是 **skill 觸發、不是鏈**
- **If** 不確定「@X 是 skill 還是鏈」**Then** `grep -rn "triggers.*@X" ~/.hermes/skills/` 確認是 skill、還有 `ls ~/.hermes/handoff/*/ 2>/dev/null | grep -B1 "@X"` 確認是鏈
- **If** 沒驗證就延伸出「@<隨意名>鏈」**Then** 違反 trial-and-error 教的「不要憑印象答」、必被使用者抓包

### 真實案例
2026-06-11：使用者說「未來可能要建『反編譯/反組譯』代理」、AI 順手延伸出「@符號學習」鏈（寫進 `_chains/README.md`）。**使用者立刻糾正**：「沒有『@符號學習』這個鏈、我從來沒說過、是你延伸的」。

**教訓**：
- 聽到「@X」先確認是 skill 還是鏈
- 沒有使用者明確指示、**不要主動給鏈取名**
- 寫進文件前要核對至少 2 個來源（skill directory + handoff directory）

---

## 錯誤 2：把「主 session 召集」畫成「鏈內交付」

### 觸發場景
畫 5 階段鏈條圖時，常見錯誤是把所有代理都畫成「前一棒的交付物直接給後一棒」。但 `engineering-lead` 跟 `test-engineer` 往往是**主 session 召集**、不是 `system-architect` 派工。

### 正確的拓樸

**錯誤畫法**（我 2026-06-11 第一次畫的）：
```
consumer-researcher → product-planner → system-architect
    ↓                                       ↓
engineering-lead ←────── ←─────────────── test-engineer
```

**正確畫法**（使用者糾正後）：
```
consumer-researcher (56) → product-planner (64) → system-architect (102)
                                                    ↓
                            ← engineering-lead (88) ← test-engineer (38) ←── 主 session 召集
```

**差別**：
- 錯誤版：`test-engineer` 是 `system-architect` 派工（意謂 `system-architect` 寫完 architecture.md 就觸發 test）
- 正確版：`test-engineer` 由**主 session 召集**（意謂主 session 看完 sprint-report.md 才決定要不要觸發 test）

### 判斷規則
| 場景 | 鏈內交付？ | 主 session 召集？ |
|------|----------|------------------|
| 資料流（A 的 output 直接是 B 的 input）| ✅ 鏈內 | ❌ |
| 決策流（需要根據 A 的 output 決定要不要觸發 B）| ❌ | ✅ 主 session |
| 例：sprint-report 完了要不要跑 test？取決於 sprint 通過率 | ❌ | ✅ 主 session 決定 |
| 例：test 完了要不要觸發 bug 修復？取決於 bug 嚴重度 | ❌ | ✅ 主 session 決定 |
| 例：consumer-needs 直接餵給 product-planner | ✅ 鏈內 | ❌ |

### If-Then 規則
- **If** 階段 B 的觸發條件是「階段 A 的 output 滿足某條件」**Then** B 是主 session 召集
- **If** 階段 B 一定會跑（不管 A 結果如何）**Then** B 是鏈內交付
- **If** 畫鏈條圖時不確定 **Then** 預設畫成「主 session 召集」、加 `←── 主 session 召集` 標記

---

## 錯誤 3：跳過 stage 但沒寫 skip reason

### 觸發場景
動態鏈（5 階段不全跑）時，常見錯誤是 `_plan.md` 寫了 stage 1、2、4、5、但 stage 3（system-architect）沒寫就直接跳過。**未來 audit 不知道為什麼跳**。

### 正確寫法
`_plan.md` 必有 `## Skipped Stages` 段（即使沒跳過也要寫 `無`）：

```markdown
## Skipped Stages
- (無、5 階段全跑)
```

或真的跳過時：

```markdown
## Skipped Stages
- Stage 3 (system-architect): 跳過理由 = 教學內容不需複雜架構、單頁 SPA 就夠
  - 由誰補？: 改由 product-planner 直接在 prd.md 加 "技術選型" 段
```

### If-Then 規則
- **If** 動態鏈跳過某 stage **Then** `_plan.md` 必有 `## Skipped Stages` 段列理由
- **If** 跳過是因為「交給其他 stage 補」**Then** 必寫「由誰補」（避免未來找無主孤兒）
- **If** 完全跳過沒寫理由 **Then** 未來 audit 會誤判為「忘了跑」

---

## 錯誤 4：用「預設鏈」當實際鏈

### 觸發場景
default orchestrator dispatch 代理時、預設跑 5 階段標準鏈。但**不是每個 project 都該走滿 5 階段**。

### 預設鏈 vs 實際鏈
| 預設鏈 | 實際鏈（由 `_plan.md` 決定）|
|--------|--------------------------|
| 固定 5 階段 | 1-N 階段、視 project 而定 |
| consumer → product → architect → engineer → test | 跳過、插入、重組都 OK |

**規則**：**預設鏈只是起點、`_plan.md` 才是實際鏈**。

### 動態鏈的 3 種合法模式
1. **跳過**（Skipped）—— 寫進 `## Skipped Stages`、補交付物佔位檔（如 `architecture-skipped.md: "N/A"`）
2. **插入**（Inserted）—— 在 `_plan.md` 加新 stage（如「在 arch 跟 eng 之間插一個 design-review 階段」）
3. **平行**（Parallel，未來）—— 用 `delegate_task` 平行跑多棒、目前 `chain-automation.md` 不支援

### If-Then 規則
- **If** dispatch 第一個代理前 **Then** 必先寫 `_plan.md`（見錯誤 5）
- **If** `_plan.md` 寫「走預設鏈」**Then** 5 階段全跑、不準動態跳
- **If** `_plan.md` 寫「動態鏈」**Then** 跳過/插入的 stage 都要交代

---

## 錯誤 5：dispatch 第一個代理才補 `_plan.md`

### 觸發場景
default orchestrator 有時會「先觸發代理、再回頭補 plan」。這違反 chain 設計意圖 —— plan 應該是 dispatch **前**的決策文件、不是 dispatch **後**的記錄文件。

### 正確順序
```bash
# 1. 先建 handoff 目錄
mkdir -p ~/.hermes/handoff/<new-slug>/

# 2. 先寫 _plan.md（決定鏈條）
cat > ~/.hermes/handoff/<new-slug>/_plan.md <<'EOF'
# <new-slug> Handoff Plan
## Chain Definition
- 階段 1: <agent> → <filename>
...
EOF

# 3. 才觸發第一階段代理
hermes -p <agent> chat -q "..." --cli
```

### If-Then 規則
- **If** 接到一個 handoff 任務 **Then** **先**寫 `_plan.md`、`後` dispatch
- **If** 已經 dispatch 了才想到要寫 plan **Then** 中止代理、重來（除非代理剛啟動還沒動）
- **If** 不知道要寫什麼 plan **Then** 載入 `~/.hermes/handoff/_chains/EXAMPLE-at-project.md` 跟 SCHEMA.md 範本

---

## 真實案例彙整（2026-06-11 session）

| 案例 | 錯誤類型 | 修正動作 |
|------|---------|---------|
| 寫出「@符號學習」這個不存在的鏈 | 錯誤 1：命名混淆 | 全部改回「@專案」、加註「@學習≠鏈」 |
| 鏈條圖畫成「arch 直接派 test」 | 錯誤 2：拓樸錯誤 | 改畫「主 session 召集」、加箭頭標記 |
| README 沒列「目前唯一真實鏈」盤點 | 錯誤 4：預設鏈 vs 實際鏈 | 加「真實鏈盤點段」、明確標「只有 1 條」 |
| 寫了 SCHEMA 但沒 reference 範例 | （非錯誤、是配套）| 預備建 `EXAMPLE-at-project.md`（待建）|

---

## 驗證命令（chain 拓樸設計完跑一次）

```bash
# 1. plan 存在
ls ~/.hermes/handoff/<slug>/_plan.md

# 2. plan 內的代理都建好
grep -oP '階段 \d+: \K[a-z-]+' ~/.hermes/handoff/<slug>/_plan.md | while read agent; do
  hermes profile list | grep -q "^$agent " && echo "✅ $agent" || echo "❌ $agent MISSING"
done

# 3. plan 內的鏈名有沒有跟現有 skill 撞名
PLAN_NAME=$(grep -m1 "^# " ~/.hermes/handoff/<slug>/_plan.md | awk '{print $2}')
if grep -rq "triggers.*$PLAN_NAME\|name: $PLAN_NAME" ~/.hermes/skills/ 2>/dev/null; then
  echo "⚠️ $PLAN_NAME 跟現有 skill 撞名、確認這是鏈不是 skill"
fi

# 4. Skipped Stages 段有寫
grep -A3 "## Skipped Stages" ~/.hermes/handoff/<slug>/_plan.md

# 5. 主 session 召集的階段有標記
grep "主 session 召集" ~/.hermes/handoff/<slug>/_plan.md
```

---

## 跟 `chain-automation.md` 的分工

| | `chain-automation.md` | `chain-topology-pitfalls.md`（本檔）|
|---|----------------------|-------------------------------------|
| **焦點** | 技術：bash wrapper 怎麼寫 | 設計：鏈條拓樸怎麼設計才合理 |
| **時間** | dispatch 後執行 | dispatch 前規劃 |
| **角色** | 給「跑 chain」的人看 | 給「設計 chain」的人看 |
| **解決的問題** | 「wrapper 怎麼寫才不斷」 | 「鏈條怎麼設計才不踩坑」 |

**兩個檔案是互補的**：先看本檔設計好拓樸、再看 chain-automation.md 寫 wrapper 跑。
