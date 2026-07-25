# AgentAssert / Agent Behavioral Contracts

**日期**: 2026-06-02
**來源**: arXiv:2602.22302, github.com/qualixar/agentassert-abc

---

## 核心概念

AgentAssert 是 Agent Behavioral Contracts (ABC) 的runtime enforcement 實現，將 Design-by-Contract 原則引入 AI agents。

**6 Pillars**:
1. Formal Behavioral Contracts — YAML-based specification
2. Runtime Enforcement — mathematical guarantees at execution time
3. Session Drift Detection — JSD-based behavioral tracking
4. SPRT Statistical Certification — Sequential Probability Ratio Testing
5. Compositional Guarantees — multi-agent pipeline safety proofs
6. Hard/Soft Constraint Separation — critical vs. advisory rules

---

## 關鍵論文發現

### (p,δ,k)-Satisfaction
契約合規的概率概念，考慮 LLM 非確定性和恢復机制。

### Drift Bounds Theorem
contracts with recovery rate γ > α (γ = 恢復率, α = 自然漂移率)
→ behavioral drift bounded to **D* = α/γ** in expectation

### 實驗結果
- 293 scenarios across 12 domains, **100% pass rate**
- Contracted agents detect **5.2–6.8 soft violations per session** that uncontracted baselines miss entirely (p<0.0001, Cohen's d=6.7–33.8)
- Hard constraint compliance: **88–100%**
- Behavioral drift bounded to **D* < 0.27** across extended sessions
- Recovery for frontier models: **100%**, across all models: **17–100%**
- Overhead: **<10ms per action**

### Live LLM Benchmark (10-16 turn e-commerce sessions)
| Model | Hard Violations | Soft Violations | Mean Drift |
|-------|-----------------|-----------------|------------|
| GPT-5.3 | 0 | 11 | 0.034 |
| Claude Sonnet 4.6 | 4 | 0 | 0.020 |
| Mistral-Large-3 | 5 | 0 | 0.025 |

**Key Finding**: AgentAssert catches violations that traditional guardrails miss because it tracks behavioral drift over **entire sessions**, not just individual outputs.

---

## 安裝

```bash
pip install agentassert-abc[all]
```

Dependencies:
- `yaml` — ruamel.yaml for YAML parsing
- `math` — scipy, numpy for drift detection
- `llm` — LiteLLM for recovery re-prompting
- `otel` — OpenTelemetry metric export

---

## 框架整合

| Framework | Integration Type |
|-----------|-----------------|
| LangGraph | Node Interception |
| CrewAI | Task Guardrails |
| OpenAI Agents SDK | Output Guardrails |

---

## YAML Contract 範例

```yaml
agent: financial-advisor
version: "1.0"

before:
  - user must be authenticated
  - compliance status must be approved

during:
  - responses must not contain SSN patterns
  - responses must not contain credit card numbers
  - session cost must stay under $5.00
severity: critical
action: block

after:
  - response must include regulatory disclaimer
  - all PII references must be redacted
on_failure:
  retries: 3
  fallback: escalate_to_human
  message: "Connecting you with a human advisor."
```

---

## 與赫米斯的關係

- **赫米斯的 Layer 2.5** (automated-sop-validation) 類似 AgentAssert 的 pre-condition/during rules
- **赫米斯的 Layer 3** 外部基準可以參考 AgentContract-Bench 的 200+ scenarios
- **差距**: 赫米斯目前沒有 JSD-based session drift detection 和 SPRT statistical certification

---

## If→Then 經驗

**If** 需要為 AI agent 定義形式化行為契約
**Then** 使用 AgentAssert YAML 格式，區分 Hard（action: block）vs Soft（action: warn）

**If** 要追蹤 agent 長期行為漂移
**Then** 實作 session-level JSD drift detection，而非只檢查單次輸出

---

## 參考連結

- Paper: https://arxiv.org/abs/2602.22302
- GitHub: https://github.com/qualixar/agentassert-abc
- Website: https://agentassert.com