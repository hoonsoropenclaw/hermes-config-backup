# Multi-Agent Framework Selection Guide（2026-06 更新）

## 主流框架比較

| 框架 | 優勢 | 劣勢 | 生產採用 |
|------|------|------|---------|
| **LangGraph** | 狀態機 + debug 能力強，Postgres checkpointer | 學習曲線較陡 | Alice Labs 18+ deployments 第一名 |
| **CrewAI** | role-based，輸出豐富，直覺易上手 | 複雜流程支援較弱 | 第三名 |
| **AutoGen/AG2** | 研究級對話，微軟維護 | production 穩定性較低 | 第四名 |
| **Claude Agent SDK** | Anthropic 原生，生產級 | 綁定 Anthropic | 第二名 |
| **Semantic Kernel** | .NET stack，企業級 | 需 Microsoft 生態 | 第五名 |

## 選擇決策樹

```
If：需要生產級且重視調試能力
Then：LangGraph（狀態機 + checkpointer）
     參考：Alice Labs 18+ production deployments 第一名

If：需要快速建立 role-based agent crew 且重視輸出豐富度
Then：CrewAI（角色協作，輸出詳細）
     適合：研究報告、內容生成

If：需要 Anthropic-native 生產 agent（Claude Code 使用的框架）
Then：Claude Agent SDK

If：需要研究級對話式 agent 且不在意 production 穩定性
Then：AutoGen/AG2（微軟，v2 event-driven architecture）

If：.NET stack 且需企業級支援
Then：Semantic Kernel
```

## 赫米斯現有技能整合

- `agent-orchestrator`：已支援 skills 掃描和匹配，可考慮加入 framework 選擇決策樹
- `persistent-subagent`：依賴 delegation，framework 選擇應在 orchestration 層處理

## 外部驗證

- Alice Labs 生產部署排名（18+ deployments）：LangGraph > Claude Agent SDK > CrewAI > AutoGen > Semantic Kernel > LlamaIndex > Pydantic AI
- 來源：alice labs AI agent frameworks 2026 comparison

## If→Then 規則

```
If：需要 multi-agent workflow 且重視 production 穩定性
Then：選擇 LangGraph（state machine + Postgres checkpointer）

If：需要快速原型且輸出豐富
Then：選擇 CrewAI（role-based）

If：已有 Camofox 部署且只需要簡單的 browser automation
Then：不需要 multi-agent framework，直接用 Camofox API
```

## 補充：Browser Automation 與 Framework 的配合

nodriver/Camofox 等瀏覽器自動化工具可以作為 agent 的 tool，納入 LangGraph 或 CrewAI 的 workflow 中：

- LangGraph：`tool_calls` node 可以整合 nodriver
- CrewAI：`Tool` 裝飾器可以包裝 nodriver/camofox
- AutoGen：built-in browser tool 支援