# Agentic RAG — Hermes Production State (2026-06-27)

Condensed from: `agentic-rag-upgrade-20260623.md` + `agentic-rag-routing-20260627.md`

## Hermes RAG Stack Capability

```
/usr/bin/python3.12 --version  # → 3.12.3 ✅
chroma 1.5.9 ✅  |  langchain 1.3.1 ✅
sentence_transformers ❌  |  faiss ❌  |  scikit-learn ❌
rank_bm25 ✅  |  torch ✅  |  numpy ✅
```

**Python env pitfall**: `python3` = Hermes venv 3.11 (no chromadb), `/usr/bin/python3.12` = system 3.12 (has chromadb).
**All RAG scripts must use `/usr/bin/python3.12`.**

## Accuracy Benchmarks

- Naive RAG (chunk→embed→top-K cosine→LLM): **44%** factual accuracy
- Production RAG (Hybrid + Reranking): **63%+**
- Gap: 19% absolute — matters for high-stakes HR policy queries

## Hermes-Ready RAG Upgrade Path

| Phase | What | Time |
|-------|------|------|
| Phase A | Hybrid Retrieval (BM25 + vector, RRF merge) | 1-2h |
| Phase B | Cross-encoder Reranking | 2-3h (needs external rerank API or Ollama upgrade) |
| Phase C | Self-RAG / CRAG loops | 5h+ (needs langchain upgrade) |

## Hermes Memory Tools

- `mempalace` MCP: semantic vector search (96.6% R@5, verified 2026-04-26)
- `session_search`: FTS5 over state.db messages — **polluted by cron output** (2026-06-13)
  - Workaround: direct state.db query for user sessions
- `agent-memory-systems` SKILL.md: full theory (CoALA, LangMem, chunking) + new query routing (2026-06-27)

## Query Routing Quick Reference

```
Query has specific entity names/dates?
  → Sparse (BM25)

Query is abstract ("similar", "like")?
  → Dense (vector)

Query has BOTH signals or is high-stakes?
  → Hybrid (RRF merge)

Query needs multi-step reasoning?
  → Decompose first, merge results

First result similarity < 0.3?
  → Switch strategy, don't retry same one
```

## If→Then Rules

- **If** user says "find" or "search" for a document AND has exact terms (法條/人名/日期)
  → **Then** use Hybrid Retrieval (BM25 + vector), not pure vector similarity
- **If** RAG script gives `ModuleNotFoundError: No module named 'chromadb'`
  → **Then** use `/usr/bin/python3.12` not `python3`
- **If** evaluating RAG quality
  → **Then** measure factual accuracy, not just "did it find a document"
  → **Then** Naive RAG baseline = 44%, Hybrid+Reranker = 63%+
- **If** same gap identified in consecutive cycles without SKILL.md update
  → **Then** D2 loop — patch existing SKILL.md, don't make new trial-and-error file
