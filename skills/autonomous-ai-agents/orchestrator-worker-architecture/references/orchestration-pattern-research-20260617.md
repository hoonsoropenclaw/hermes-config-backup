# Multi-Agent Orchestration Research Summary（2026-06-17）

> 本檔案濃縮本次 research cycle 的關鍵發現，供日後決策參考，不重複 upstream 文件。

## 四大 Orchestration Primitives（Augment Code）

| Primitives | 赫米斯對應 | 備註 |
|-----------|-----------|------|
| Task Decomposition | `delegate_task(tasks=[...])` / `orchestrator-worker-architecture` | |
| Routing | `hermes chat -q` 派遣 / profile 隔離 | |
| State | `_plan.md` + `_raw/` + `_summary.md` / `memorial palace` | |
| Recovery | `hermes cron` watchdog / `anti-panic-protocol` | |

## 三種主要拓撲（Vellum）

| Pattern | 赫米斯實作 | Best For |
|---------|-----------|---------|
| **Supervisor**（中心化）| `delegate_task` 預設模式 | Hub-and-Spoke，集中控制 |
| **Hierarchical**（階層式）| `orchestrator-worker-architecture` | 流水線：研究→整理→結論 |
| **Peer-to-Peer**（對等）| 赫米斯**不原生支持**（需 shared file 模擬）| 2-4 個 agent 固定協作 |

## 框架對比（Alice Labs 2026，18+ 生產部署）

| 排名 | 框架 | 赫米斯對應 | 適合場景 |
|------|------|-----------|---------|
| #1 | LangGraph | N/A | 生產控制、複雜狀態流 |
| #2 | Claude Agent SDK | 赫米斯（Anthropic-native）| Anthropic-native 生產 agent |
| #3 | CrewAI | N/A | 角色驅動多代理 |
| #4 | AutoGen/AG2 | N/A | 研究風格對話 agent |

**赫米斯定位**: 類似 Claude Agent SDK，但更側重**多平台 gateway**（Telegram/Discord/Slack）與**cron 驅動的時間軸自主化**。

## Token 代價研究（Anthropic 內部）

- Multi-agent token 消耗是 chat 的 **~15x**
- 主要原因：重複的 context（每個 agent 都要帶完整的 shared assumption）
- 赫米斯額外代價：process/transport 隔離的 session init overhead（~5-10s/次）

## 協作失敗率（AutoGen/CrewAI/LangGraph 統計）

- **36.94%** 的失敗來自 coordination（通訊/路由/狀態不一致）
- 這印證了赫米斯 Phase 1.5 cron 健康掃描的重要性——coordination drift 是隱性 failure mode

## Framework 選擇決策

| 若你注重 | 選 LangGraph |
|----------|-------------|
| Anthropic-native 生產 | Claude Agent SDK / 赫米斯 |
| 團隊速度（快速原型）| CrewAI |
| 研究風格對話 | AutoGen/AG2 |

## 赫米斯相較於通用框架的獨特優勢

1. **`hermes cron` = 原生 scheduler**：其他框架需要自己實作
2. **`profiles` = process 級隔離**：其他框架是 thread 級
3. **`kanban` = 原生視覺化任務板**：其他框架需額外整合

## Hermes Orchestration Decision Tree 依據

上方 Decision Tree 的 Step 1-5 依據：
- Step 1（Topology）：Vellum 三種 pattern × 赫米斯原語映射
- Step 2（Context Isolation）：Anthropic 15x token 研究 + 赫米斯 session init overhead 測量
- Step 3（State）：赫米斯具備的 state 機制盤點
- Step 4（Recovery）：赫米斯現有 `anti-panic-protocol` + `cron` watchdog 覆蓋
- Step 5（Special Cases）：赫米斯架構限制（P2P 不原生支持）

## Sources

- [Vellum: Multi-Agent Systems Building with Context Engineering](https://www.vellum.ai/blog/multi-agent-systems-building-with-context-engineering)
- [Augment Code: Multi-Agent Orchestration Architecture Guide](https://www.augmentcode.com/guides/multi-agent-orchestration-architecture-guide)
- [Alice Labs: Best AI Agent Frameworks 2026](https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026)
- [LangGraph vs CrewAI vs AutoGen 2026](https://pub.towardsai.net/langgraph-vs-crewai-vs-autogen-which-ai-agent-framework-should-your-enterprise-use-in-2026-3a9ebb407b09)
