# Fan-Out/Fan-In 結果彙整研究

**來源**: Beam AI Blog, April 2026 | **閱讀日期**: 2026-06-14

## 核心問題

多 agent 平行執行後，誰的結果優先？如何合併衝突？如何檢測部分失敗？

## 已知失敗模式

| 失敗模式 | 說明 | 發生條件 |
| --- | --- | --- |
| API rate limits | 15 concurrent agents × 150 req/sec → 超出集體限速 | 15+ workers |
| Race conditions on shared state | N agents = N(N-1)/2 潛在衝突 | 5 agents = 10 conflicts; 10 agents = 45 |
| Aggregation hallucination | LLM synthesis 把衝突當共識 | 多視角分析任務（如 sentiment vs fundamentals） |

## 專家建議

1. **明確衝突 resolution 機制**——不要「summarize results」，要「列出所有觀點 + 標記衝突」
2. **投票或加權合併**——對於可量化的任務，用投票而非 LLM synthesis
3. **結果優先順序在派遣前就定義**——不在彙整時才發現誰說的算

## 來源

- Beam AI: 6 Multi-Agent Orchestration Patterns for Production (2026)
- Unblocked: Scale Parallel AI Agents Without Losing Quality (2026)
- arXiv 2507.08944: Optimizing Sequential Multi-Step Tasks with Parallel LLM Agents