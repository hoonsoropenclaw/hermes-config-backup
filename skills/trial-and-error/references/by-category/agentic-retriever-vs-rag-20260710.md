# Agentic Retrieval vs Vector RAG — 赫米斯技能更新 (2026-07-10)

## 來源

2026-07-10 metacognitive-learner Phase 3 research。根據 AAAI 2026 / Amazon Science 論文與 Anthropic Claude Code 案例，更新 `agent-memory-systems` skill。

## 識別時機

Phase 3 研究發現：agent-as-retriever 典範正在編碼 agent 領域取代傳統 RAG。赫米斯現有 `mempalace` 向量搜尋架構落後於新範式。

## 理論軌

- Anthropic Claude Code 移除向量搜尋 → 打敗 RAG「遠遠落後」（Boris Cherny）
- Anthropic multi-agent: 比單一 Opus 4 **提升 90.2%**
- Amazon Science / AAAI 2026: keyword search faithfulness **94.5%** vs vector RAG 86%
- SWE-bench: 2023 RAG 1.96% → 2026 agentic systems **80%+**
- Search-R1 (RL-trained retrieval): +24% relative improvement over RAG

## 更新的 skill

`agent-memory-systems` SKILL.md 新增：
- `references/agentic-retriever-paradigm-20260710.md`（新檔案）
- Query routing section 新增 agentic retrieval 何時使用說明
- If→Then 新增「code/architecture/tracing → 優先 Glob/Grep」規則

## 緊急性

非緊急缺口。現有 mempalace 架構對學校 Hr 文件、公告系統等非程式碼任務仍然適用。agent-as-retriever 升級為未來優化方向。
