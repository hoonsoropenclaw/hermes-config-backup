# Agentic Retriever Paradigm — 2026 Research Update

## 研究背景

2026-07-10 metacognitive-learner Phase 3 研究。傳統 RAG 正面臨典範轉移，「agent-as-retriever」模式在編碼 agent 領域超越純向量搜尋。

---

## 核心發現

### Agent-as-Retriever vs Traditional RAG

| 維度 | 傳統 RAG | Agent-as-Retriever |
|------|---------|-------------------|
| 資料處理 | 預先 embedding → 存向量 | 維持輕量識別符（檔案路徑、查詢）→ 執行期動態載入 |
| 檢索方式 | 單次 top-k 向量查詢 | 迭代式、可自我修正的 tool calls |
| 新鮮度 | 索引延遲（stale index） | 檔案系統讀取 = 當前狀態（100ms 內） |
| 安全風險 | 索引需額外存储 = 額外 liability | 檔案系統 ACL 即可 |
| 可靠性 | 元件多 = 失敗點多 | 組件少 = 失敗點少 |

### Anthropic 的發現（Claude Code）

Claude Code 移除向量搜尋後，Boris Cherny：「打敗了所有方案，遠遠落後」（beat everything. By a lot）。Anthropic multi-agent 研究系統：比單一 Opus 4 **提升 90.2%**。

### 關鍵論文

- **AAAI 2026 / Amazon Science**: Keyword Search faithfulness **94.5%** vs vector RAG 86%。FinanceBench：agentic search 30.40% vs RAG 24.24%。
- **Search-R1** (RL-trained retrieval, Qwen2.5-7B): 相比 RAG baseline **+24% relative improvement**。
- **SWE-bench 進化**: 2023 RAG 1.96% → 2024 SWE-agent 12.47% → 2026 agentic systems **80%+**。

---

## 四種 Agent-as-Retriever 架構

### 1. Pure Agentic（Claude Code, Devin）
- 無持久索引
- 工具：`Glob`（檔案路徑匹配）、`Grep`（regex 內容搜尋）、`Read`、`Bash`、`Explore` subagent
- 控制迴圈：`plan → glob/grep → read → refine → repeat → compact → answer`

### 2. Hybrid Lexical + Semantic（Cursor, Sourcegraph Amp）
- 即時 Grep 處理精確符號
- 語意搜尋處理概念性查詢
- **+12.5% accuracy** 來自兩者結合

### 3. Structural / AST-Aware（Cline, Probe, ast-grep）
三層架構：
```
Tier 1: ripgrep 內容搜尋（輸出上限）
Tier 2: fzf fuzzy 檔案/資料夾評分
Tier 3: tree-sitter AST 擷取
```
Probe: 「一次 Probe call 捕獲其他工具 10+ agentic loops 的內容」

### 4. Specialized Retrieval Models
- Windsurf SWE-grep: 8 parallel calls × 4 turns = **10× faster**
- Chroma Context-1: 20M context window

---

## Claude Code 的五層壓縮管線

當接近 200K token 上限時：
1. **Budget reduction** — 移除最不相關內容
2. **Snip** — 移除多餘 tool call 輸出
3. **Microcompact** — 摘要個別長訊息
4. **Context collapse** — 折疊舊 turns 為較短摘要
5. **Auto-compact** — 最終摘要（再也塞不進時）

---

## Hermes 的啟示

**現有架構**：mempalace MCP（向量語意搜尋，96.6% R@5）+ `agent-memory-systems` skill（有查詢路由框架）。

**缺口**：缺乏明確的 **agentic retrieval 模式**。純向量搜尋在編碼任務落後 agent-as-retriever 模式。

**升級方向**（非緊急缺口）：
1. 將 mempalace MCP 視為「工具」而非「背景索引」
2. 針對複雜查詢（多跳、統計、比較），先做 query decomposition 再決定策略
3. 考慮 `Glob`+`Grep`+`Read` 的 just-in-time 模式替代部分预索引向量查詢

**現有 trial-and-error 已有**：2026-06-27 的 `agentic-rag-routing-20260627.md` 已記錄查詢路由決策框架。

---

## If→Then

- **If** 任務是程式碼理解、架構分析、依賴追蹤，**Then** 優先使用 `Glob`/`Grep`（just-in-time），不要默认预索引向量
- **If** 向量搜尋第一次 R@ < 0.3，**Then** 切換關鍵字或 just-in-time 讀取，不要重跑同一失敗策略
- **If** 使用者提出「比較X和Y」、「統計」、「列出N個」，**Then** 先 query decomposition 再 hybrid RRF 融合
