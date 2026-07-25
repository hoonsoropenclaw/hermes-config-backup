# VMAO: Verified Multi-Agent Orchestration Framework

> **來源**: [arXiv 2603.11445v2](https://arxiv.org/html/2603.11445v2)  
> **閱讀日期**: 2026-06-16  
> ** Relevance**: 為 `orchestrator-worker-architecture` Phase 6 的「整合後端到端驗證」提供 research-backed 依據

## 核心貢獻

VMAO（Verified Multi-Agent Orchestration）提出 **Plan→Execute→Verify→Replan→Synthesize** 五階段循環，關鍵創新是 **orchestration-level verification**——驗證發生在所有 agent 完成後、synthesis 前，而非每個 agent 各自驗證。

## 量化效果

| 指標 | Single-Agent | Static Pipeline | VMAO (Verify後) |
| --- | --- | --- | --- |
| 完整性 (1-5) | 3.1 | 3.5 | **4.2** (+35%) |
| 來源品質 (1-5) | 2.6 | 3.2 | **4.1** (+58%) |
| 平均 Tokens | 100K | 350K | 850K |
| 平均時間 (s) | 165 | 420 | 900 |

> **教訓**: 多了 900s（15 分鐘）的 verification 代價，換來 +35% 完整性提升。若不做 verification，完整性感率下降 35%——對關鍵任務來說，這個代價值得。

## 三層 Agent 組織（與赫米斯對應）

| Tier | VMAO Agent | 赫米斯對應 |
| --- | --- | --- |
| **Tier 1** | Data Gathering (RAG, Web Search, Financial, Competitor) | Web-worker (Phase 2) |
| **Tier 2** | Analysis (Analysis, Reasoning, Raw Data) | Summarizer-worker (Phase 4) |
| **Tier 3** | Output (Document, Visualization) | Orchestrator 最終整合 (Phase 5) |

## Verification 機制

### Verification 輸出格式

每個 sub-question 結果經 verifier 產生：
- **Status**: complete / partial / incomplete
- **Completeness score**: 0-1
- **Missing aspects**: 列出未覆蓋部分
- **Contradictions**: 列出矛盾點
- **Recommendation**: accept / retry / escalate

### Configurable Stop Conditions

| 條件 | 閾值 | 理由 |
| --- | --- | --- |
| Ready for Synthesis | 80% complete | 足以回答核心問題 |
| High Confidence | 75% conf + 50% complete | 高可靠性但部分覆蓋 |
| Diminishing Returns | <5% improvement | 繼續迭代邊際效益太低 |
| Token Budget | 1M tokens | 硬性成本上限 |
| Max Iterations | 3 | 防止無限迴圈 |

## 對赫米斯的啟發

### 為何赫米斯需要 Phase 6

赫米斯現有 `fan-in-aggregation-sop.md` 處理 **結果彙整層級** 的驗證（檔案存在、非空、無衝突標記）。但 **整合後** 的驗證——多個 worker 產出的程式碼是否真的可以一起運行——這個層級 **完全缺失**。

VMAO 明確指出：synthesis 前必須有 verification step。赫米斯的 Phase 5 相當於 synthesis，Phase 6 相當於 VMAO 的 Verify。

### Phase 6 與 VMAO Verify 的差異

| 維度 | VMAO Verify | 赫米斯 Phase 6 |
| --- | --- | --- |
| 手段 | LLM-based verifier（對答案打分） | 實際建置（`npm run build` / `pytest`） |
| 目標 | 答案完整性 | **程式碼可運行性** |
| 觸發條件 | 所有 sub-question 完成 | 工程實作任務（程式碼產出） |

> **赫米斯特殊點**: VMAO 處理的是「複雜查詢回答」，驗證手段是 LLM 打分。赫米斯處理的工程實作任務，驗證手段是**實際建置/測試**——這比 LLM 打分更客觀、更可靠。

## 關鍵引用

> "VMAO improves answer completeness from 3.1 to 4.2 and source quality from 2.6 to 4.1 (1–5 scale) compared to a single-agent baseline, demonstrating that **orchestration-level verification is an effective mechanism for multi-agent quality assurance**."

> "The key contributions are: (1) dependency-aware parallel execution over a DAG of sub-questions with automatic context propagation, (2) **verification-driven adaptive replanning that uses an LLM-based verifier as an orchestration-level coordination signal**, and (3) configurable stop conditions that balance answer quality against resource usage."
