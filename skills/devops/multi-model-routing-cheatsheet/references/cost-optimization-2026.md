# 2026 年 LLM 模型路由成本優化研究彙整

> 抓取時間：2026-06-06
> 用途：當用戶問「怎麼省 tokens」時的權威背書

---

## 來源 1：Infralovers 2026-02-19「Sonnet 4.6 vs Opus 4.6 實測」

**實驗設計**：
- 9-agent multi-agent 架構（technology researcher、content creator、KB query、channel routing）
- 測試單一 agent（Technology Researcher）
- Baseline = Opus 4.6、Treatment = Sonnet 4.6
- n=18（3 rounds × 3 parallel agents × 2 treatments）

**實測數據（Opus n=9）**：
- Avg Total Tokens: 7,501,012
- Avg API Calls: 120.7
- Avg Tool Uses: 94.3
- Avg Duration: 462s
- Avg Projects Evaluated: 9.0

**實測數據（Sonnet n=8, 排除 1 outlier）**：
- Avg Total Tokens: 4,843,462（**-35.4%**）
- Avg API Calls: 90.0（-25.4%）
- Avg Tool Uses: 72.3（-23.4%）
- Avg Duration: 408s（-11.6%）
- Avg Projects Evaluated: 6.3（-30.5%）

**成本對比**：
| Component | Opus 4.6 | Sonnet 4.6 | Factor |
|-----------|----------|------------|--------|
| Input Tokens | $5.00/MTok | $3.00/MTok | 0.60x |
| Output Tokens | $25.00/MTok | $15.00/MTok | 0.60x |
| Cache Read (5min) | $0.50/MTok | $0.30/MTok | 0.60x |
| Cache Create | $6.25/MTok | $3.75/MTok | 0.60x |

**結論**：
- 0.60（價格）× 0.65（token 量）= **0.39 成本係數** → **61% 成本下降**
- 保守實測：**~57% per-run 成本下降**
- Workflow compliance：**100%（7 步全跑，零 step-skip）**
- 品質 trade-off：少 30% 研究廣度（少評估 30% 專案）

**Benchmark 對比**（Sonnet 4.6 vs Opus 4.6）：
| Benchmark | Sonnet 4.6 | Opus 4.6 | Winner |
|-----------|------------|----------|--------|
| MCP-Atlas (Tool Use) | **61.3%** | 59.5% | **Sonnet** |
| SWE-bench Verified (Coding) | 79.6% | 80.8% | Opus（marginal） |
| Finance Agent / Vals AI | **63.3%** | 60.1% | **Sonnet** |
| GDPval-AA (Knowledge Work) | **1633 Elo** | 1606 Elo | **Sonnet** |
| ARC-AGI-2 (Novel Reasoning) | 58.3% | 68.8% | Opus |

**Key insight**: For the first time, a mid-tier model beats a prior-generation flagship in multiple agentic benchmarks.

**原文出處**：https://www.infralovers.com/blog/2026-02-19-ki-agenten-modell-optimierung

---

## 來源 2：duet.so 2026「Claude Opus vs Sonnet vs Haiku Routing Guide」

**💸 失控帳單案例**（真實事件）：

| 事件 | 費用 | 來源 |
|------|------|------|
| 23 subagents × 3 天 code-quality 專案 | **$47,000** | Verdent |
| 49 subagents × TypeScript checks | $8,000-$15,000 | Verdent |
| Claude Code 整晚 looping | $6,000 | MakeUseOf |
| 開發者 8 個月 API | $15,000（vs Max $800） | Build to Launch |
| **Uber**：2026 AI coding 預算 4 個月燒光 | $150-$2,000/engineer/月 | Fortune |

Uber COO 稱為「head-exploding moment」，Microsoft 直接取消大部分 Claude Code licenses。

**三個 Tier 的價格與定位**：

### Haiku — Fast, Cheap Workhorse
- $0.25/M input、$1.25/M output
- **60x 便宜於 Opus**
- Commit message、boilerplate、formatting、Q&A、regex、string ops

### Sonnet — Daily Driver
- $3/M input、$15/M output
- **5x 便宜於 Opus**，品質 gap 比想像小
- 70-80% 日常開發工作
- Landing page、API route、test、refactor、content、standard code review
- **應該是 default，不是 Opus**

### Opus — Heavy Hitter
- $15/M input、$75/M output
- 架構設計、complex multi-file debug、database migration、security audit、framework upgrade

**原文出處**：https://duet.so/guides/claude-opus-vs-sonnet-model-routing

---

## 來源 3：Augment Code「Best AI Model for Coding Agents in 2026」

**Static routing** vs Dynamic routing 對比：
- Claude sub-agents API 的 `model` 欄位接受 `sonnet` / `opus` / `haiku` 別名、完整 model ID、或 `inherit` 鏡像 parent session
- 案例：Sonnet 4.6 作為 implementor 在 multi-file tasks 完成更快（smart context use）

**角色對應**：
- Coordinator: Opus 4.6 for Planning
- Implementor: Sonnet 4.6 for Code Generation

**原文出處**：https://www.augmentcode.com/guides/ai-model-routing-guide

---

## 套用到赫米斯的結論

| 場景 | 推薦 model | 理由 |
|------|----------|------|
| cron 簡單任務（丟訊息、查 log） | **no LLM**（`no_agent=True`） | 100% 節省 |
| cron 簡單 AI 任務（RSS 摘要、單純 Q&A） | MiniMax-M2.1 / M2.5 | cheap tier |
| cron 標準 AI 任務（總結、分析） | MiniMax-M2.7 | daily driver |
| cron 複雜 AI 任務（多步推理） | MiniMax-M3 | 旗艦 |
| sub-agent 簡單子任務 | delegation.model = MiniMax-M2.7 | 套外部實測 57% 節省 |
| sub-agent 標準任務 | delegation.model = MiniMax-M2.7 | 同上 |
| sub-agent 複雜任務 | 用主 session M3，不走 delegation | 避免 cheap 化 |

**重要警告**：Infralovers 實驗 trade-off 是「少 30% 研究廣度」。如果用戶任務的價值在「廣度」（例如要找齊所有候選專案），不要切 cheap tier——切了反而省不到。

---

## 反面教材

❌ 用 Opus 跑 commit message → 60x 成本、零品質提升
❌ 23 subagents 全部 default Opus → $47,000 帳單
❌ Claude Code 整晚 looping → $6,000
❌ 不看任務本質，盲目升級到最強 model

---

## 預期常見追問

**Q**: 我的任務是 X，應該用哪個 model？
**A**: 先看 3-tier 矩陣（簡單/標準/複雜），再看是否有 image/video 需求（M3 限定）

**Q**: 主 session 在對話中能切換 model 嗎？
**A**: 不能。要切換必須 /reset 或新 session

**Q**: 我用 MiniMax 一組 key，能同時用 M3 和 M2.7 嗎？
**A**: 能。同一 key 同一 base_url 就能切換 model id，不需要多 provider 配置

**Q**: deepseek / claude 能一起用嗎？
**A**: 能，但需要 3 組不同 key（multi-provider 場景），sub-agent / cron job 可平行跨 provider
