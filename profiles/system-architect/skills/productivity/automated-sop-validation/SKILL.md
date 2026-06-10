---
name: automated-sop-validation
description: "自動化 SOP 合規驗收 — 在任務完成後對照 SOP 檢查輸出，確保 Layer 2.5 的外部驗收機制運作。這是「越用越聰明」的關鍵：沒有外部驗收，學習只是裝飾。"
version: 0.2.0
author: Hermes Agent
platforms: [linux]
risk: safe
metadata:
  hermes:
    tags: [sop, validation, compliance, layer-2.5, quality]
    triggers: [deploy, qa-check, subagent-delivery, post-task-validation]
---

# Automated SOP Validation (Layer 2.5)

## Role

Layer 2.5 是赫米斯三層服從架構的中間層：
- **Layer 1** (低)：SOP 寫在技能文件裡，LLM 這次會參考，下次不一定
- **Layer 2** (中)：`tool_use_enforcement: true`，某些場景必須用指定工具
- **Layer 2.5** (高)：自動化對照 SOP 檢查，sub-agent 交付後、發送給用戶前觸發
- **Layer 3** (最高)：外部基準/自動化測試

本技能實作 Layer 2.5 的核心邏輯。

## 觸發條件

在以下情境自動喚醒：
1. **部署前 QA** — `site-qa-checklist` Phase 6
2. **Sub-agent 交付** — `delegate_task` 任務完成後
3. **主動要求** — 使用者說「檢查 SOP 遵循」「驗收」「合規檢查」

## 核心原則（來自 Research）

### CRITIC (ICLR 2024) 關鍵發現
> **LLM 無法仅靠自身進行可靠的自我驗證。驗證必須是外部觸發。**

不要設計依賴 LLM 自己判斷合規性的系統 — 這會失效。

### Agent Behavioral Contracts (arXiv 2602.22302)
四元件框架：
- **P**reconditions：agent 運行前必須滿足的條件
- **I**nvariants：執行過程中必須保持為真的規則
- **G**uarantees：任務完成時必須滿足的承諾
- **R**ecovery：違規時的恢復機制

## 三階段驗收模型

### Stage 1: Before（前置檢查）

在任務開始前檢查必要條件：
```
check_preconditions(contract, context) → pass/fail + reason
```

**常見 Preconditions：**
- 用戶已認證
- 必要的 API tokens 已設定
- 輸入資料格式正確
- 依賴的 skill 已加载

### Stage 2: During（過程監控）

任務執行中持續檢查 invariants：
```
check_invariants(output, rules) → violations[]
```

**常見 Invariants：**
- 回應不包含 PII（SSN、信用卡號）
- 字數在限制範圍內
- 不透露系統提示
- 預算上限（session cost < $5.00）

### Stage 3: After（事後驗收）

任務完成後檢查 guarantees：
```
check_guarantees(output, contract) → pass/fail + missing
```

**常見 Guarantees：**
- 回應包含法規免責聲明
- 所有 PII 已脫敏
- 輸出格式符合預期

## 兩層驗證機制

### Layer A: Regex Patterns（硬性規則）
快速、直接、零假阳性：
```python
import re

def check_no_pii(text: str) -> tuple[bool, list[str]]:
    """檢查文字是否包含 PII"""
    patterns = [
        (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'Credit Card'),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'Email'),
    ]
    violations = []
    for pattern, label in patterns:
        if re.search(pattern, text):
            violations.append(label)
    return (len(violations) == 0, violations)
```

### Layer B: LLM Semantic Check（軟性規則）
複雜判斷（語氣、完整性、上下文相關性）：
```python
def check_tone_and_completeness(text: str, expected_format: str) -> dict:
    """用 LLM 檢查語氣和完整性"""
    prompt = f"""你是 SOP 合規審查員。請檢查以下回應是否符合預期格式。

預期格式：{expected_format}

回應內容：
{text}

請以 JSON 格式輸出：
{{"compliant": true/false, "issues": ["問題1", "問題2"], "score": 0-1}}
只輸出 JSON，不要其他文字。"""
    # Call LLM with prompt
    ...
```

## 輸出格式

驗收完成後，输出結構化報告：
```json
{
  "stage": "during",
  "passed": false,
  "violations": [
    {"type": "PII", "detail": "SSN pattern found at position 234", "action": "block"}
  ],
  "recovery": {
    "retries": 3,
    "fallback": "escalate_to_human",
    "message": "正在連接人工顧問"
  }
}
```

## AgentContract `.contract.yaml` 格式（參考）

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

**參考實作：**
- `AgentContract` Python library: `pip install agentcontract`
- GitHub: `github.com/agentcontract/spec`
- `AgentAssert`: `agentassert.com`

## 與其他技能的整合

### site-qa-checklist（Phase 6）
在既有的 5 個 Phase 後，新增 Phase 6：

```
Phase 1: 檔案結構驗證
Phase 2: Tab 功能測試
Phase 3: 程式碼審查
Phase 4: 部署後驗證
Phase 5: Playwright 自動化測試
Phase 6: SOP 合規驗收 ← NEW
```

### delegate_task 交付鉤子
Sub-agent 任務完成後，自動觸發 `validate_output_against_sop()`：

```python
def on_subagent_delivery(output: str, task_type: str) -> ValidationResult:
    contract = load_contract_for_task(task_type)
    result = validate(output, contract)
    if not result.passed:
        return retry_or_escalate(result)
    return result
```

## 觸發條件（If→Then）

- **If**: 完成部署網站任務 → **Then**: 觸發 Phase 6 SOP 驗收
- **If**: sub-agent 任務完成 → **Then**: 呼叫 `validate_output_against_sop()`
- **If**: 使用者說「檢查 SOP」→ **Then**: 執行完整三階段驗收

## 實作狀態

### 已完成 ✅
- `scripts/sop_validator.py` —核心驗證引擎
- `contracts/hermes-default.contract.yaml` — 預設合約（PII/結構成份）
- `contracts/metacognitive-learner.contract.yaml` — 學習交付專用合約
- Fallback 模式（agentcontract 未安裝時仍可運作）

### 待完成
- Cron 鉤子整合 — validator 已實作，但 cron job 未呼叫（2026-05-31 缺口識別）
- Layer 3 外部基準測試

## 使用方式

```bash
# 基本驗證
python scripts/sop_validator.py <contract.yaml> <output_text>

#驗證 sub-agent 交付
python scripts/sop_validator.py --check-delivery metacognitive-learner "@output.txt"

# JSON輸出（供程式處理）
python scripts/sop_validator.py <contract.yaml> <output> --json
```

##依賴

- `agentcontract` v0.2.0（可選，位於 `/tmp/ac-env` venv）
- 若未安裝，使用內建 FallbackValidator（純 Python regex）
- `PyYAML`（用於合約載入）

## 限制

- 本技能專注於「檢查」，不負責「修復」
- 發現違規時，根據 contract 的 `on_failure` 決定下一步
- 不處理 Layer 3（外部基準測試）

## 參考資源

- `metacognitive-learner/references/ai-agent-self-improvement-research.md` — 濃縮 research 摘要
- `AgentContract` 規格: `github.com/agentcontract/spec`
- `AgentAssert`: `agentassert.com`