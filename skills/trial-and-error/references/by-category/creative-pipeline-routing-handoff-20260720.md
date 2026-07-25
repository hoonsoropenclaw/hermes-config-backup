### creative-pipeline-03 Creative Pipeline Skill Routing Handoff（2026-07-20）

**Gap 症狀**：創意 pipeline 的各節點 SOP（DAG / 執行狀態 / 風格記憶 / 意圖鑒別 / 內容審核重構 / 多代理同步）均已存在，但**節點之間的 routing handoff 缺乏統一文檔**，導致創意請求進入 pipeline 時不知道某個節點該觸發哪個 SOP。

**外部研究**：explainx.ai Multi-Agent Orchestration Patterns 2026 — pipeline pattern 核心原則：「每個 agent 必須產生明確定義的輸出格式供下一個 agent 消費」。

---

## 創意 Pipeline 節點地圖

```
用戶創意請求
    │
    ▼
[意圖鑒別] ── 4-factor ambiguous trigger ──▶ Clarification Node (3-option)
    │                                        (agentic-rag-routing-20260627.md)
    ▼
[風格繼承] ── creative_brand_profiles/ ──▶ Style Memory Capture / Inheritance
    │                                        (creative-style-memory-20260719.md)
    ▼
[DAG 規劃] ── 6-type taxonomy ────────────▶ 畫出依賴圖
    │                                        (creative-pipeline-dag-20260713.md)
    ▼
[執行層] ──── mmx 6-type 工具鏈 ──────────▶ image/video/speech/music generate
    │                                        (mmx-cli image/video/speech/music)
    ▼
[內容審核] ── moderation_rejected ─────────▶ Semantic Replacement + Binary Search
    │                                        (image-moderation-reframing-20260709.md)
    ▼
[執行狀態] ── checkpoint 讀寫 ────────────▶ Checkpoint/Resume Logic
    │                                        (creative-pipeline-execution-state-20260719.md)
    ▼
用戶交付
```

---

## If→Then Handoff 規則

**If** 創意 pipeline 的某個 DAG node 需要執行，且該 node 輸出型別屬於 mmx 6-type taxonomy
**Then** 直接路由到 mmx-cli 工具鏈（image generate / video generate / speech synthesize / music generate）
**原因**：mmx 覆蓋全部 6 型別（text/image/video/speech/music/music-cover，Cycle 488-489 驗證），是創意工具鏈核心執行層

**If** 創意 pipeline 遇到 content moderation 阻擋（moderation_rejected）
**Then** 觸發 image-moderation-reframing SOP（semantic replacement table + binary search）
**原因**：creative-pipeline-execution-state-20260719.md 規則 1 定義了 handoff，但 routing layer 本身缺失

**If** 創意 pipeline 需要風格一致性（用戶提到「跟之前一樣」「再用那個風格」）
**Then** 先讀取 creative_brand_profiles/，若為空則從歷史對話重建 style 參數
**原因**：creative-style-memory SOP 定義了 capture/inheritance 機制，但 pipeline 執行前的主動讀取環節從未被調用（Cycle 524 確認 user_default.json 為空）

**If** 創意 pipeline 遇到模糊意圖（multi-type keywords / high-level goal / no 載體 / no 數量）
**Then** 觸發 agentic-rag-routing-20260627.md clarification node 3-option format
**原因**：4-factor ambiguous trigger（Cycle 499）和 clarification format 已經定義，但 pipeline 沒有整合這個 routing 節點

**If** 創意 pipeline 任務失敗後，用戶再次提到同一個 project
**Then** 讀取 ~/.hermes/creative_pipeline_checkpoints/<workflow_id>.json，按 creative-pipeline-execution-state-20260719.md 規則 3 resume 邏輯恢復
**原因**：checkpoint 格式和 resume 邏輯已經定義，但 checkpoint 目錄從未被創建過

---

## 驗證命令

```bash
# 確認 checkpoint 目錄存在（若不存在則創建）
ls -la ~/.hermes/creative_pipeline_checkpoints/ 2>/dev/null || echo "DIR_NOT_FOUND"

# 確認 creative_brand_profiles/ 有內容
ls -la ~/.hermes/skills/creative_brand_profiles/ 2>/dev/null || echo "PROFILES_DIR_NOT_FOUND"
```

---

**相關條目**：
- `creative-pipeline-dag-20260713.md` — DAG 框架基礎
- `creative-pipeline-execution-state-20260719.md` — Checkpoint/Resume 規則
- `creative-style-memory-20260719.md` — 風格記憶 capture/inheritance
- `agentic-rag-routing-20260627.md` — 意圖鑒別 + clarification node
- `image-moderation-reframing-20260709.md` — 內容審核 semantic replacement
