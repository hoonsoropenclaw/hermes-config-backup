# MemPalace LLM Re-rank 技術參考

## 背景

MemPalace 本身不提供 LLM re-rank 機制。`mempalace_search` 的底層是純向量搜尋（ChromaDB）+ BM25 混合排序，無 LLM 介入。

拉斐爾（OpenClaw）在 2026-04-26 設計了三層搜尋架構，第三層是可選的 LLM re-rank。這是原創設計，不是 MemPalace 內建功能。

赫米斯移植了這個設計，但改為**自動觸發**（非可選），因為後設認知缺口掃描需要更高準確性。

## Benchmark 驗證結果（官方數據，2026-03）

來源：[mempalaceofficial.com](https://mempalaceofficial.com) + [GitHub benchmarks/](https://github.com/mempalace/mempalace/tree/main/benchmarks)

### LongMemEval（500 題）

| Mode | R@5 | LLM Required | Cost/query |
|------|-----|-------------|-----------|
| Raw ChromaDB（純向量） | **96.6%** | None | $0 |
| Hybrid v4 held-out 450（乾淨分數） | **98.4%** | None | $0 |
| Hybrid v4 + Haiku/Sonnet rerank | 100% | Optional | ~$0.001 |

> ⚠️ 100% 不作為官方數字發布：最後 0.6% 是針對 3 道錯題調整的（teaching to the test）。真實可引用數字 = **98.4% held-out**。

### LoCoMo（1,986 題）

| Mode | R@10 | LLM |
|------|------|-----|
| Hybrid v5（top-10，無 rerank） | 88.9% | None |
| Hybrid v5 + Sonnet rerank（top-50） | 100% | Required |

### Re-rank 模型驗證

MemPalace 官方測試過以下模型，均可達到 100% R@5：
- **Claude Haiku** ✅
- **Claude Sonnet** ✅
- **minimax-m2.7 via Ollama Cloud** ✅ — 與赫米斯當前模型相同

> 「The gap between raw and reranked is model-agnostic」—— re-rank 效果與模型無關，只要够強的閱讀理解能力即可。

## 赫米斯三層搜尋閾值

| 階段 | 工具 | 觸發條件 |
|------|------|----------|
| Phase 1 | session_search | 預設先執行 |
| Phase 2 | mempalace__mempalace_search | Phase 1 分數 < 0.3 或無結果 |
| Phase 3 | MiniMax LLM re-rank | Phase 2 分數 < 0.4 或結果數 > 10 |

## LLM Re-rank Prompt（可直接內嵌使用）

```
你是記憶檢索助手。請根據以下查詢和候選記憶，評估每條記憶的相關性並重新排序。

原始查詢：{query}

候選記憶：
{index}. [{source}] 相似度={score}
{text_preview}

請以 JSON 格式輸出：
{{"ranked": [{{"index": N, "reason": "為什麼相關", "new_score": 0-1}}]}}
只輸出 JSON，不要其他文字。
```

## 關鍵發現

1. **MemPalace MCP server 有 29 個工具**，不是只有 search
2. **mempalace_search 底層**：Drawer 向量搜尋（主floor）+ Closet 向量搜尋（boost信號）+ BM25 混合排序
3. **max_distance 參數**：預設 0（不過濾），設 0.3-1.0 可過濾低質量結果
4. **Hydration 机制**：對於有多個 drawer 的 source，會做 drawer-grep 擴展，取關鍵字最好的 chunk ± 1 鄰居

## 與拉斐爾的差异

- 拉斐爾：第三層是「選擇性」（可以送 LLM re-rank）
- 赫米斯：第三層是「自動備援」（分數 < 0.4 自動觸發）

赫米斯更積極是因為：
- 後設認知任務需要高召回
- session_search → mempalace → LLM 三層的額外成本可控
- 使用內建 MiniMax 模型，無額外 API 設定
