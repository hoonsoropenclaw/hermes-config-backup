# Multi-Agent Cascade Failure Defense Patterns
> **研究來源**: arXiv 2603.04474v2 (From Spark to Fire) + LangGraph GitHub #7303 + LangGraph production guides
> **閱讀日期**: 2026-07-30
> ** Relevance**: orchestrator-worker-architecture 的 cascade failure gap（Cycle 563 識別）

## 核心威脅模型

### 三種內生漏洞（From Spark to Fire, 2026）

| 漏洞 | 機制 | 證據 |
|------|------|------|
| **V1: Cascade Amplification** | 多鄰居曝光 compound 而非 cancel 錯誤 | 6 framework 中 5 個達到 100% 最终感染率 |
| **V2: Topological Fragility** | Hub 節點有最大譜影響力 | Hub injection: LangGraph 100%, Leaf injection: 9.7% — 差距 10.31× |
| **V3: Consensus Inertia** | 修正成本隨 workflow 進展增加 | 延遲修正衝突累積的 dependency chain |

### 量化傷害

```
Framework  | Hub injection | Leaf injection | Impact Factor
-----------|-------------|---------------|---------------
LangGraph  |   100.0%    |     9.7%      |    10.31×
CrewAI     |   100.0%    |    15.9%      |     6.29×
AutoGen    |   100.0%    |    100.0%     |     1.00×  (mesh 無 hub)
CAMEL      |   100.0%    |    100.0%     |     1.00×
```

### 共識腐蝕攻擊 Pipeline（3步）

1. **Seed Construction**: 建構與任務格式相容的 atomic falsehood
2. **Credibility Packaging**: 權威框架（"per company policy"）或恐懼/不確定性（"emergency CVE patch"）
3. **Injection Placement**: Gray-box 攻擊瞄準高影響力節點（hub agents）

---

## 防禦模式（Governance Layer）

### Pattern 1: Hub Verifier Gating

```
[Worker A] ──┐
[Worker B] ──┼──▶ [HUB AGENT] ──▶ [VERIFIER NODE] ──▶ [下一階段]
[Worker C] ──┘         ▲
                       │ conditional edge
                  trust_score < threshold?
                       │
                 ──▶ [HUMAN REVIEW]
```

**LangGraph 實作**:
```python
from langgraph.checkpoint.memory import MemorySaver

# Trust-gated conditional edge
def should_continue(state: AgentState) -> str:
    trust_score = state.get("verifier_trust_score", 1.0)
    if trust_score < 0.7:
        return "human_review"  # interrupt + persist state
    return "continue"

# Graph with governance node
graph = StateGraph(AgentState)
graph.add_node("verifier", verifier_node)
graph.add_edge("hub_agent", "verifier")
graph.add_conditional_edges(
    "verifier",
    should_continue,
    {"human_review": "human_review_node", "continue": "next_phase"}
)
```

### Pattern 2: Phase Gate with Decay

在共識慣性最強的位置（workflow 中期）插入獨立的事實核查節點：

```
Phase 1 (Plan) → Phase 2 (Execute) → [PHASE GATE: Fact-check] → Phase 3 (Synthesis)
                                         │
                                    失敗閾值?
                                         ├─▶ 重試 (max 3)
                                         └─▶ Escalate to human
```

**關鍵**: Phase Gate 必須在 hub agent廣播之前拦截，不能在共識形成後才補救。

### Pattern 3: Source Provenance Tracking

追蹤每個資訊來源的 agent，防止污染鏈：
```python
@dataclass
class VerifiedClaim:
    content: str
    source_agent: str
    confidence: float
    verification_status: Literal["unverified", "passed", "failed"]
    propagated_from: Optional[List[str]] = None  # 追蹤污染路徑
```

---

## 實作選擇框架對照

| 框架 | Cascade 安全性 | 治理支援 | 2026 狀態 |
|------|--------------|---------|----------|
| LangGraph | ⚠️ Star=100% Hub | `langgraph-trust` (MSFT) | Active |
| CrewAI | ⚠️ Star=100% Hub | 原生無，需自建 | Active |
| OpenAI Agents SDK | 較佳（原生的） | 平台整合 | Active |
| AutoGen | ⚠️ Mesh=100% | 維護模式 | Maintenance-only |

**選擇結論**: 新專案用 **OpenAI Agents SDK** 或在 **LangGraph + langgraph-trust** 上建立治理節點。避免純 Star topology 的自由協作（anti-pattern）。

---

## If→Then 經驗

- **If** 任務使用 `delegate_task(tasks=[...])` 派遣 3+ 個平行 workers，且產出為需要彙總的結果（研究、分析、非單一事實），**Then** 必須在彙整前執行 cascade failure 防禦檢查：驗證每個 worker 輸出獨立於其他 worker、未受 hub 節點傳播的 false consensus 污染，並在 `_summary.md` 中明確標記衝突點而非假設達成一致——因為 2026 年 "From Spark to Fire" 證實 LangGraph/CrewAI/AutoGen 在 hub injection 攻擊下均會達到接近 100% 的最終感染率。

- **If** 任務需要多個 agent 在最外層「自由協作」（free mesh P2P），**Then** 重新設計為 supervisor 模式：協作作為受控的 subroutine 放在 supervisor 內部，而非作為頂層架構——2026 年生產驗證確認自由協作在外部層級是 anti-pattern。

- **If** 在 LangGraph 中建構 multi-agent workflow，**Then** 將 `verifier` 節點視為第一公民（first-class citizen），每個 hub agent 後串聯一個事實核查節點，並用 `interrupt()` 對高風險輸出（刪除/發送/花費）實現 human-in-the-loop——這樣等於在架構層級內建了 "From Spark to Fire" 攻擊的防御線。
