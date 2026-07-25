# Agentic RAG Upgrade — 從 Naive RAG 到生產級 RAG（2026-06-23 學習）

## 學習背景

通過 state.db 直接查最近 user sessions，識別出 AI 圖片生成（06-16, 98 msgs）、學校公告系統建置（06-11, 244 msgs）等主題。`local-rag-system` skill（v1.1, 2026-06-07）只實作了 **naive RAG**（44% 準確率），落後於 2026 年 Agentic RAG 生產標準（63%+）。

---

## 1. Naive RAG 的準確率上限

**數據來源**：Atlan.com 引用 CRAG Benchmark 2024
- **Naive RAG**（固定四步：chunk → embed → top-K cosine → LLM）：**44%** 事實準確率
- **SOTA RAG**（含 advanced techniques）：**63%**
- **差距**：19% absolute accuracy gap = 幾乎一半的錯誤率改善

**If** 要在 HR 政策查詢（學校人事）等高精確度場景使用 RAG
**Then** naive RAG 不够——需要升級到 Hybrid Retrieval + Reranking 組合

---

## 2. 生產級 RAG 五大必要技術（按實作複雜度排序）

### T1 — 立即可升級（低複雜度，高 impact）

| 技術 | 做什麼 | 為什麼有效 |
|------|--------|-----------|
| **Hybrid Retrieval** | dense vector + sparse BM25，RRF merge | 處理 embedding 抓不到精確術語（人名、法條編號）|
| **Contextual Retrieval** | LLM 在 chunk 前加文件級語境 | 減少 67% retrieval failure（Anthropic 2024）|
| **Cross-Encoder Reranking** | 第二 pass 直接評分 (query, doc) | 提升 NDCG/MRR，bi-encoder initial retrieval 後必做 |

### T2 — 需要框架支援（中複雜度）

| 技術 | 做什麼 | 赫米斯現況 |
|------|--------|-----------|
| **Self-RAG**（ICLR 2024 Oral）| LLM 自己判斷何時要 retrieve + reflection tokens | 需要升級 langchain 至新版 |
| **CRAG**（Corrective RAG）| Evaluator 評估文件品質，差則 fallback 網路搜尋 | 高風險 domain（法律、醫療）必備 |
| **Adaptive RAG** | Classifier 路由到 no/single/multi-step retrieval | 生產環境標配 |

### T3 — 高複雜度新架構

| 技術 | 什麼場景需要 |
|------|------------|
| **GraphRAG**（Microsoft）| 多跳關係查詢（如：找「所有與這個政策相關的執行細則」）|
| **RAPTOR** | 長文件跨章節推理（+20% on QuALITY benchmark）|

---

## 3. 赫米斯當前 RAG 棧的實際能力

```bash
/usr/bin/python3.12 --version  # → 3.12.3 ✅
chroma 1.5.9 ✅  |  langchain 1.3.1 ✅
sentence_transformers ❌  |  faiss ❌  |  scikit-learn ❌
rank_bm25 ✅  |  torch ✅  |  numpy ✅
```

**Python 3.12 的 venv 陷阱**（已在 local-rag-system SKILL.md 記錄）：
- `python3` = Hermes venv 的 3.11（沒有 chromadb）
- `/usr/bin/python3.12` = 系統 Python 3.12（有 chromadb, langchain）
- **所有 RAG 腳本都必須用 `/usr/bin/python3.12` 執行**

**可用組件**：
- ✅ ChromaDB（PersistentClient）
- ✅ LangChain（RecursiveCharacterTextSplitter, text splitters）
- ✅ Ollama embeddings（`herald/dmeta-embedding-zh`）
- ✅ rank_bm25（馬上可以做 Hybrid Retrieval 的 sparse 層）
- ✅ Ollama qwen2.5:1.5b（LLM engine）

---

## 4. 立即可實作的升級路徑

### Phase A（1-2 小時）：Hybrid Retrieval

```python
# 概念：同時 query ChromaDB（dense）+ BM25（sparse），RRF merge
# 赫米斯已有：rank_bm25, ChromaDB, Ollama embeddings

# Step 1: 在 add_document() 時同時存原始文字（供 BM25 建立索引）
# Step 2: query 時：
#   dense_results = chroma.query(embedding, top_k)
#   sparse_results = bm25.search(query, top_k)
#   merged = rrf_merge(dense_results, sparse_results, k=60)
# Step 3: 輸出 merged ranking
```

### Phase B（2-3 小時）：加 Reranking

- 安裝 `sentence-transformers` 或使用 Cohere Rerank API
- Ollama 現在不支援 rerank endpoint（需要外部服務）
- **替代方案**：用 `mmx-cli` 跑一個簡單的 relevance scoring prompt

### Phase C（长期）：加 Self-RAG / CRAG

- 需要 langchain 版本升級
- 複雜度較高，建議有明確 HR use case 需求時再投入

---

## 5. HR 場景的 RAG Upgrade 優先順序

學校人事主管的使用模式：
1. **政策查詢**（「這個法條怎麼說」）→ T1 Hybrid Retrieval 馬上改善
2. **表單/辦法搜尋**（關鍵字精確匹配）→ BM25 對這類場景特別有效
3. **複雜法條關係**（「這個辦法參考哪個法規」）→ GraphRAG 長期目標

**If** 使用者明確說「學校人事政策查詢」或「法條搜尋」
**Then** 優先升級到 Hybrid Retrieval（BM25 + vector）
**Then** 不要只用 naive vector similarity

---

## 6. If→Then 經驗固化

**If→Then 1（Agentic RAG 判斷）**：
- **If**：使用者在 HR/學校/政策場景說「找」或「查」文件
- **Then**：先確認 naive RAG（pure vector similarity）是否足夠
- **Then**：若涉及精確術語（法條編號、人名、文件名稱）→ 必須加 Hybrid Retrieval（BM25 + RRF）

**If→Then 2（Python 環境陷阱）**：
- **If**：跑 RAG 腳本遇到 `ModuleNotFoundError: No module named 'chromadb'`
- **Then**：立郎確認——`python3` vs `/usr/bin/python3.12` 環境不同
- **Then**：所有 RAG 指令都用 `/usr/bin/python3.12` 執行，不要用 `python3`

**If→Then 3（RAG 準確率評估）**：
- **If**：要評估 RAG 系統好壞
- **Then**：不要只看「有沒有找到文件」——要看事實準確率
- **Then**：Naive RAG 基準線 44%，有 Hybrid+Reranker 可到 63%+

**If→Then 4（Reranking 必要性）**：
- **If**：bi-encoder retrieval 結果看似合理但順序不對
- **Then**：cross-encoder reranking 是標準解，不需要換 embedding 模型
- **Then**：但要記得 reranking 是額外延遲 cost（需要做 latency vs accuracy 權衡）

---

## 7. 對 `local-rag-system` skill 的建議

現有 SKILL.md 缺失的 5 個關鍵主題：
1. **Hybrid Retrieval 流程**（當前只有純 vector）
2. **BM25 安裝與整合**（`pip install rank-bm25`）
3. **Query routing**（什麼時候用 dense vs sparse vs hybrid）
4. **Chunking strategy 優化**（contextual retrieval 的前置條件）
5. **Self-RAG / CRAG 概念介紹**（讓使用者知道長期升級方向）

**預估實作時間**：
- Phase A（Hybrid Retrieval）：1-2 小時
- Phase B（Reranking）：2-3 小時
- Phase C（Agentic RAG loop）：5+ 小時

**建議**：先從 Phase A 開始，針對學校人事文件建立專屬 collection，驗證 BM25+vector hybrid 效果。
