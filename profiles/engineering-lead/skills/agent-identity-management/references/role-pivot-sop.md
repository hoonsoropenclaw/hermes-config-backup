# 身份重塑 (Role Pivot) 完整指南

> 給未來遇到「**現有代理的核心職責要整個反轉**」任務時的快速參考。SKILL.md 的 pivot 段是精簡版、本檔是完整版。

## 什麼時候需要「重塑」而不是「重建新代理」?

**Pivot(重塑現有)**:
- 現有代理的基礎設施(API key / model / sessions 歷史)可重用
- 上下游依賴關係不變(只 pivot 該代理、不動其他代理)
- 名字**可**沿用或**可**換(看使用者決定)
- 工作量:中等(改 persona + 精瘦 skill + 同步下游)

**Rebuild(完全重建新代理)**:
- 現有代理的設定完全不適用
- 想保留舊代理的歷史(例:前任的 session log 要查)
- 上下游依賴關係要拆
- 工作量:大(從零建)

**合併(merge)**:
- 兩個代理的職責重疊度 > 70%、想整合成一個
- 詳見 SKILL.md「身份繼承」段的合併子情境

## Pivot 決策矩陣

| 維度 | 保留原樣(A) | 改局部(B) | 整個重建(C) |
|------|-------------|-----------|-------------|
| profile 名 | A | A(只在 persona 改) | C |
| wrapper | A | A | C |
| skill 庫 | A | B(精瘦 30-60 個) | C(從 default clone 重選) |
| persona.md | A(微調) | B(整段重寫 SOP) | C(從零寫) |
| SOUL.md | A | B(改語氣) | C(從零寫) |
| handoff 結構 | A | B(改 README + 範本) | C(從零建) |
| 下游代理 | A | B(同步引用) | C(下游另建) |

**If** pivot 範圍 < 3 個維度 **Then** 走 A/B(原地改,工作量小)
**If** pivot 範圍 ≥ 4 個維度 **Then** 走 C(整個重建,乾淨不混亂)

**若使用者偏好「乾淨」而非「省事」,一律走 C**(推薦)

## Pivot 前的 4 個驗證問題

動手前先自問:

1. **現有代理的「核心職責」要整個反轉嗎?**
   - 否:只是小調整(改 1-2 段)→ 用 persona 局部 patch
   - 是:進 Step 0 列 6 個決策點

2. **下游代理是否需要同步改?**
   - 否:本代理是 leaf(沒有接手代理)→ 跳過 Step 6 下游同步
   - 是:列出所有下游 + 每個下游要改的 4-5 個具體段

3. **skill 庫需要重選嗎?**
   - 否(新舊角色需要的 skill 高度重疊)→ 不用精瘦
   - 是:進 Step 3 精瘦 30-60 個

4. **現有 session 歷史有意義嗎?**
   - 有(未來可能要查過去的 session)→ 保留舊 profile 不刪,改用「封存」(加 `archive-` 前綴)
   - 無(測試專案、沒 session)→ 整個刪除舊 profile

## 4 種典型 pivot 情境(給未來案例對照)

### 情境 1:核心職責反轉(2026-06-10 案例)
- **前**:`market-strategist` (做市場分析、TAM/SAM/SOM、行銷定位)
- **後**:`consumer-researcher` (做消費者需求挖掘、標竿功能盤點)
- **pivot 範圍**:6 個維度全變 → 整個重建
- **下游同步**:product-planner(改 4 處 persona + 1 處 skill 內引用)

### 情境 2:角色細分(預期常見)
- **前**:`general-coder` (什麼程式都寫)
- **後**:`frontend-engineer` + `backend-engineer`(拆分)
- **pivot 範圍**:單一代理 → 兩個新代理
- **下游同步**:沒有下游(leaf 代理)

### 情境 3:加強專業度(預期常見)
- **前**:`writer` (一般寫作)
- **後**:`technical-writer` (技術文件、API doc、規格書)
- **pivot 範圍**:5 個維度變 → 整個重建
- **下游同步**:沒有下游(只跟 default 互動)

### 情境 4:換技術領域(罕見)
- **前**:`python-coder` (Python only)
- **後**:`typescript-coder` (TypeScript only)
- **pivot 範圍**:3 個維度變 → 走 B(原地改)
- **下游同步**:沒有下游

## Keep-list 範本(給不同 pivot 場景)

### 場景 A:從「市場分析」pivot 到「消費者研究」

```text
# === 核心方法論(7) ===
anthropic-customer-research         # 客戶/消費者研究方法論
anthropic-account-research          # 帳號/客群研究
anthropic-competitive-brief         # 競品/標竿簡報
anthropic-competitive-intelligence  # 競品/標竿情報
anthropic-knowledge-synthesis       # 多源研究綜合
anthropic-synthesize-research       # 學術/質性研究綜合
anthropic-search-strategy           # 多源搜尋策略

# === 搜尋與爬取(5) ===
anthropic-search
web_search
scrapling
agent-browser
browser

# === 資料探勘與分析(5) ===
anthropic-explore-data
anthropic-analyze
anthropic-metrics-review
anthropic-statistical-analysis
anthropic-validate-data

# === 視覺化(3) ===
anthropic-data-visualization
anthropic-create-viz
anthropic-build-dashboard

# === 寫作/文件/簡報(6) ===
minimax-docx
minimax-pdf
minimax-xlsx
pptx-generator
docx
xlsx
pdf

# === 研究(2) ===
research
anthropic-scientific-problem-selection

# === 規劃(2) ===
anthropic-product-brainstorming
anthropic-write-spec

# === Hermes 基礎設施(7) ===
trial-and-error
user-collaboration-style
workspace-folder-layout
general-workflow
anti-panic-protocol
connection-resilience
new-conversation

# === 視覺(1) ===
vision-analysis
```
**總計 41 個 skill**(market-strategist 原本 53 個、砍 12 個,主要是 9 個跟市場分析/fintech 相關的 skill)

### 場景 B:從「general-coder」pivot 到「frontend-engineer」

```text
# === 核心方法論(5) ===
anthropic-product-brainstorming
anthropic-write-spec
antislop                    # 避免 AI-slop UI
anti-slop-design            # 避免 AI-slop 設計
design-taste-frontend       # 前端設計品味

# === 前端框架專屬(8) ===
lb-nextjs16-skill           # Next.js 16 文件
gsap-core                   # GSAP 動畫核心
gsap-frameworks             # GSAP 框架整合
gsap-react                  # GSAP + React
gsap-scrolltrigger          # GSAP 滾動觸發
gsap-timeline               # GSAP 時間軸
gsap-performance            # GSAP 效能優化
gsap-plugins                # GSAP 插件

# === UI / 設計系統(4) ===
ant_design_skill            # Ant Design
antigravity-design-expert   # 高互動 UI
minimalist-ui               # 極簡編輯風
soft-design                 # 高端視覺設計

# === 3D / Shader(2) ===
3d-web-experience           # Three.js
shader-dev                  # GLSL shader

# === 工具(3) ===
creative                    # 創意工具集
playwright-skill            # E2E 測試
scrapling                   # 自適應爬蟲

# === Hermes 基礎設施(7) ===
trial-and-error
user-collaboration-style
workspace-folder-layout
general-workflow
anti-panic-protocol
connection-resilience
new-conversation
```
**總計 30 個 skill**

### 場景 C:從「writer」pivot 到「technical-writer」

```text
# === 核心方法論(6) ===
anthropic-write-spec
anthropic-knowledge-synthesis
anthropic-synthesize-research
anthropic-search
anthropic-search-strategy
web_search

# === 文件/簡報(6) ===
minimax-docx
minimax-pdf
minimax-xlsx
pptx-generator
docx
pdf

# === 程式理解(2) ===
scrapling                   # 程式碼範例爬取
scrapling                   # 程式碼搜索
anthropic-explore-data

# === Hermes 基礎設施(7) ===
trial-and-error
user-collaboration-style
workspace-folder-layout
general-workflow
anti-panic-protocol
connection-resilience
new-conversation
```
**總計 22 個 skill**

## 上下游同步的 4 個必改段

下游代理有 4 個段必改(其他 95% 不用動):

```bash
# 1. 核心介紹
"你是一個專門把「<舊交付物名>」轉成「<新交付物名>」的<下游角色>。"

# 2. 核心信念(讀取來源段)
"承接 <上游舊名> 的假設" → "承接 <上游新名> 的假設"

# 3. Step 1 讀取路徑
"從 ~/.hermes/handoff/<slug>/<舊交付物>.md 讀..."

# 4. 交付物版本標頭
"承接自:<舊交付物>-<slug>.md  接手給:<下一棒>"
```

下游的 skill 庫內引用也要對應:
```bash
# 找下游 skill 內所有「<舊名>」引用
grep -rn "<上游舊名>" ~/.hermes/profiles/<下游>/skills/
# 對應改成 <上游新名>
```

## 統一性 grep 的 4 個必跑項

```bash
# 1. 新 profile 內不該出現舊名(業務邏輯層,允許歷史脈絡段)
grep -rn "<上游舊名>" ~/.hermes/profiles/<上游新名>/ 2>&1

# 2. handoff 範本 + README 不該出現舊名
grep -rn "<上游舊名>" ~/.hermes/handoff/_template/ ~/.hermes/handoff/README.md 2>&1

# 3. 下游代理的 persona + skill 內引用應已對應
grep -rn "<上游舊名>" ~/.hermes/profiles/<下游>/ 2>&1 | grep -v "歷史\|history\|update\|2026-"

# 4. trial-and-error 跨 profile 引用
grep -rn "<上游舊名>" ~/.hermes/skills/trial-and-error/ 2>&1
```

**第 4 個特別注意**:`trial-and-error/SKILL.md` 跟 `references/` 是 default profile 持有,被所有 profile 共享。如果在 trial-and-error 內更新了對 pivot 代理的描述(例:`profile-slimming-sop.md` 內的範例從「市場策略代理」改成「消費者需求代理」),**用跨 profile 寫入**(`patch(cross_profile=True)` 或 `write_file(cross_profile=True)`)。

## 跨 profile 寫入的 4 個安全檢查

`cross_profile=True` 是繞過 soft-guard,動手前必跑:

1. **確認使用者明確指示**：「全照建議走」OK、「自己看著辦」不 OK
2. **確認改動有正當理由**：例:pivot 上游 → 下游必須對應(必要)
3. **確認改動範圍**：只改必要 1-2 個檔、不要清空整個 skill
4. **改完必驗證**:`grep` 對應下游 profile、確認新名生效

## 報告交付 checklist

寫 `CONVERSION_v<n>_REPORT.md` 時對照這 8 段必含:

- [ ] 6 項決策落實表(對照 Step 0 提的 6 個)
- [ ] 各步驟執行情況(每步一行、標 ✅ 或 ❌)
- [ ] 統一性 grep 4 項輸出
- [ ] 意外發現(3-5 條 L2 教訓)
- [ ] 刻意保留決策(避免無謂改動風險)
- [ ] 未做的項目(避免後續「為什麼沒做」疑問)
- [ ] 給 default orchestrator 的快速參考
- [ ] 驗證命令(給未來週期性檢查用)

## 跟身份繼承(本 SKILL.md 上半部)的對照

| 維度 | 身份繼承 | 身份重塑 |
|------|---------|---------|
| 觸發 | 前代理死了/卸載 | 現代理要 pivot |
| 影響面 | 7 份重要檔案 + 跨 skill | profile + skill 庫 + handoff + 下游 |
| 必跑步驟 | 7 步 | 9 步 |
| 必用工具 | grep / 統一性驗證 | grep + `hermes profile create --clone` + 精瘦 + PTY |
| 必改下游 | 通常不用(代理死了) | 必改 4 處 |
| 風險 | 過度改名 | 過度保留舊 skill + 下游斷鏈 |
| 報告 | `IDENTITY_INHERITANCE_v<n>_REPORT.md` | `CONVERSION_v<n>_REPORT.md` |
