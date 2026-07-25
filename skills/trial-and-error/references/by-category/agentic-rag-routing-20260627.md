# Agentic RAG Query Routing — 赫米斯技能缺口 (2026-06-27)

## 識別時機
2026-06-27 metacognitive-learner cycle。Phase 1 缺口掃描發現：
- Hermes 有 `agent-memory-systems` skill（理論框架：CoALA、MemGPT、LangMem、chunking strategies）
- Hermes 有 `mempalace` MCP（向量語意搜尋，96.6% R@5）
- **缺口**：無 query routing / retrieval strategy selection 決策框架
- 使用者最近討論 AI 圖片生成、學校公告、面試排程、Hr文件自動化

## 理論軌（基於 agent-memory-systems skill 內容 + RAG 研究現況）

### 三種主流檢索策略

| 策略 | 適用場景 | 原理 |
|------|---------|------|
| **Dense (向量語意)** | 語義相似、非關鍵字匹配 | embedding model 映射到語意向量空間 |
| **Sparse (BM25/關鍵字)** | 精確術語、專有名詞、型號 | 傳統資檢索，統計詞頻 |
| **Hybrid (RRF 融合)** | 混合需求、兩種信號都重要 | Reciprocal Rank Fusion 合併排名 |

### Query Decomposition（查詢分解）

複雜問題需要分解為多個子查詢：
```
原始問題：「這個月的面試候選人有多少來自師大附中？」
→ 子查詢1：「師大附中 2026面試候選人」
→ 子查詢2：「2026年6月 面試記錄」
→ 子查詢3：「各高中 候選人來源統計」
```

### Reranking（重新排序）

第一階段召回（高 recall）→ 第二階段重新排序（高 precision）：
- **Cross-encoder reranking**：比 embedding cosine 更精確但更慢
- **RRF (Reciprocal Rank Fusion)**：多策略結果融合，無需訓練

## 工具軌
無外部 web search 可用（Ollama + Tavily 均失敗），跳過。

---

# 創意內容請求路由（Cycle 487 — 2026-07-12）

## 識別背景

Cycle 486 metadata 標記「下一個 D3 gap：creative request routing framework」。
赫米斯有多个创意 skills 但缺乏统一的请求路由决策树。

## 理論軌

### 創意內容意圖分類（Creative Intent Taxonomy）

基於 intent classification 原理（MLPills #109, 2026），將創意請求分為 5 類：

| 意圖類型 | 用戶關鍵信號 | 建議工具 |
|---------|------------|---------|
| **圖像生成** | 「生成一張圖」、「畫一個」、「給我看看...的樣子」 | mmx-cli image |
| **影片生成** | 「做一個影片」、「生成短片」、「animation」 | mmx-cli video |
| **漫畫/連續圖敘事** | 「漫畫」、「comic strip」、「分鏡」 | baoyu-comic 或 mmx-cli image（靜態 panel） |
| **資訊圖表** | 「資訊圖」、「infographic」、「視覺化數據」 | baoyu-infographic 或 mmx-cli image（靜態圖） |
| **語音/音頻** | 「語音合成」、「配音」、「文字轉語音」 | mmx-cli speech |
| **音樂生成** | 「生成音樂」、「做一首歌曲」、「背景音樂」 | mmx-cli music |

### 請求複雜度維度

| 維度 | 簡單（直接生成） | 複雜（需策劃） |
|------|---------------|--------------|
| 單一輸出 | 1 張圖、1 個影片 | 故事板、多段影片 |
| 組合輸出 | 單一工具滿足 | image→video→speech 鏈 |

### 關鍵原則

**意圖分類先行**：在選擇工具之前，先判斷用戶想要的創意輸出類型。
赫米斯 mmx-cli 覆蓋 4/6 類型（圖像、影片、音頻、音樂），漫畫和資訊圖需要 image_gen tool（靜態替代可用 mmx-cli image）。

## If→Then 固化規則

**If** 用戶要求創意視覺內容但未指定格式
**Then** 先做意圖分類：問「想要靜態圖、影片、漫畫、還是資訊圖？」
**Why** 避免工具選擇錯誤導致浪費額度的 retry 迴圈

**If** 用戶要求漫畫/資訊圖但 image_gen tool 不可用
**Then** 評估是否可用 mmx-cli image 替代（如：靜態 comic panel 可用 image 生成）
**Why** N100 上 baoyu-comic/baoyu-infographic 依賴的 image_generate tool 不存在，但漫畫單格靜態圖可用 mmx-cli 替代

**If** 用戶要求多段式創意內容（storyboard + video + 語音）
**Then** 使用 image→video(I2V)→speech 三步鏈（Cycle 485 已驗證）
**Why** 成功率 80%（vs blind generation 40%），成本從 $5/clip 降至 $1.5/clip

**If** 怀疑用户意图但时间有限
**Then** 优先选择 mmx-cli（圖像/影片/語音一體，N100 驗證可用），而非触发未知依赖的 skill
**Why** mmx-cli 1.0.16 在 N100 上已驗證（`npx -y mmx-cli --version` 可運行），其他 creative skills 有未滿足的依賴

## 現有資源盤點
- `~/.hermes/skills/agent-memory-systems/SKILL.md`：理論框架完整（CoALA、LangMem、MemGPT、chunking patterns）
- `mempalace` MCP：提供 semantic search 但無 routing logic
- 無 standalone query routing skill

## Gap 等級評估
- **D2 整合型**：識別缺口、提出整合方案
- 原因：agent-memory-systems 理論足夠，但缺「什麼情況用什麼策略」的決策框架
- 不需要新建 skill，在 agent-memory-systems 現有文件上追加 query routing 段落即可

## If→Then 經驗
**If** 使用者提問涉及多個實體的比較或需要匯總 **Then** 自動觸發 query decomposition，將問題分解為多個子查詢再合併結果

**If** 檢索結果明顯不相關（相似度低）**Then** 切換檢索策略（semantic → keyword 或反向），不要重複失敗的策略

**If** 檢索需要精確關鍵字匹配（人名、日期、機構名）**Then** 使用 sparse/BM25 策略而非純語意向量

## 建議修改現有 skill
在 `agent-memory-systems/SKILL.md` 追加以下章節：
1. Query Classification Signals（何時用哪種策略）
2. Query Decomposition patterns（多跳問題處理）
3. Hybrid Search with RRF（多策略融合）
4. Reranking patterns（cross-encoder vs RRF）

---

---

## 創意意圖模糊時的決策邊界（Cycle 499 深化 — 2026-07-16）

### 問題：何時應停下來問用戶，而非直接執行

Cycle 487 確認了 6-type taxonomy，但未定義「何時應澄清」的觸發邊界。直接執行模糊創意請求會導致：
- 執行了錯誤的類型（image vs video vs pipeline）
- 需要重跑（浪費 API 配額）
- 用戶最終說「不是我要的」

### 4-Factor 模糊觸發條件

當創意請求滿足以下任一條件，**先停、先問**，不要直接執行：

| 因子 | 觸發信號 | 例子 |
|------|---------|------|
| **Multi-type keywords** | 請求同時出現多個 6-type 關鍵詞 | 「做一個影片+配音」「圖片生成然後變成影片」 |
| **High-level goal** | 請求包含「宣傳/動畫/作品集/項目」等高層次目標詞 | 「做一個宣傳影片」「幫我做一個項目展示」 |
| **No 載體 specified** | 未指定載體（image/video/speech/music） | 「做一個好看的」（沒有「圖」或「影片」） |
| **No 數量 specified** | 未指定數量 | 「一些圖片」（不是「5張圖」）|

### Clarification Node 格式（3-Option Choice）

觸發模糊條件時，輸出以下格式：

```
你在找的是？

A. 單一類型 — 直接生成一個 [圖/影片/語音/音樂]
   適用於：已有明確想法，不需要看中間過程

B. Pipeline（多步驟）— 先做 [X]，再做 [Y]，最後 [Z]
   適用於：需要角色一致性、需要有音樂配合影片等複雜需求

C. 還需要多一點資訊才能決定
   適用於：還在構思階段、不確定要什麼
```

### Clarification 後的 Pipeline 識別

當用戶選擇 B（pipeline）時，立即輸出階段規劃：

```
這個 [project name] 需要以下步驟：

Step 1. [工具] — [產出描述]（預計 [時間/配額]）
Step 2. [工具] — [產出描述]（預計 [時間/配額]）
...

確認開始執行嗎？
```

**Diagrid durable execution 原則**：pipeline 規劃先於執行——確認後才開始消耗配額。

### 與 Cycle 492-494 的關係

- **Cycle 492**：「多步如何串聯」（DAG 框架）
- **Cycle 494**：「某節點失敗時如何處理」（fault tolerance）
- **Cycle 499**：「何時應停下來問」（disambiguation 邊界）

三個階段構成完整的創意 pipeline 決策鏈：意圖分類 → DAG 規劃 → 執行/容錯

---

**建立時間**: 2026-06-27
**更新**: 2026-07-16 (Cycle 499 — disambiguation 邊界深化)
**Cycle**: metacognitive-learner-24h · Jul 16
