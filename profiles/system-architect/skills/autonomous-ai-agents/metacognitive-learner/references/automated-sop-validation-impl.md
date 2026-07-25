# automated-sop-validation 實作記錄

**日期**：2026-05-31
**起因**：metacognitive-learner Phase 3 學習時發現 `automated-sop-validation` 只有理論文件，無實際程式碼
**結果**：已實作 Layer 2.5 驗收引擎

---

## 實作結構

```
skills/productivity/automated-sop-validation/
├── SKILL.md                          # 技能定義（已更新實作狀態）
├── scripts/
│   └── sop_validator.py              # 核心驗證引擎
└── contracts/
    ├── hermes-default.contract.yaml  # 預設合約
    └── metacognitive-learner.contract.yaml  # 學習交付專用合約
```

---

## 引擎設計

### 雙軌模式
- **主軌**：AgentContract v0.2.0 SDK（標準化驗證框架）
- **備援**：FallbackValidator（純 Python regex，agentcontract 未安裝時仍可運作）

### FallbackValidator 實作
- 使用 `yaml.safe_load` 載入合約
- 正規表示式比對 `must_not` 中的 pattern
- 簡單子字串比對 `must` 中的 `required_element`
-觸發時機：AgentContract SDK載入失敗（`from_yaml` 方法相容性問題）

### 驗證函式
```python
SOPValidator(contract_path).validate(output, task_type)
SOPValidator().validate_delivery(output, task_type)  # 自動載入任務合約
```

### Hermes 特定規則（`_check_hermes_rules`）
- 禁止揭露 system prompt（SOUL.md/MEMORY.md）
- 警告缺少 `[TO_MEMORY]` 區塊

---

## 合約格式（AgentContract spec v0.1.0）

```yaml
agent: <name>
version: "1.0"
requires: [] # 前置條件
invariant: [] # 持續規則
limits: {}          # 定量限制
must_not: []        # 禁止（pattern + on_violation）
must: []            # 必要元素（required_element + on_violation）
assert: []          # 斷言（type: pattern/schema/llm/latency/cost）
ensures: []         # 後置條件
on_violation: {}    # 違規處理
severity: critical
```

---

## 測試結果

|測試 | 輸入 | 預期 | 實際 |
|------|------|------|------|
| 無違規模 | "正常文字" | ✅ PASS | ✅ PASS |
| SSN 洩漏 | "SSN: 123-45-6789" | ❌ FAIL | ❌ FAIL |
| 信用卡洩漏 | "Card: 1234-5678-9012-3456" | ❌ FAIL | ❌ FAIL |
| 結構化輸出 | "## 學習摘要 + [TO_MEMORY]" | ✅ PASS | ✅ PASS |
| 學習交付 | 含4 個必要元素 | ✅ PASS | ✅ PASS |

---

## 安裝依賴

```bash
# 建立 venv
cd /tmp && uv venv ac-env
source ac-env/bin/activate
uv pip install agentcontract PyYAML
```

---

## 已知限制

1. AgentContract SDK 的 `from_yaml` 有相容性問題，已用 FallbackValidator 繞過
2. Layer 3（外部基準測試）未實作
3. Cron 鉤子整合未實作

---

## 擴展方向

1. 為每個 skill 建立對應的 `.contract.yaml`
2. 在 cron job 中串接驗證（`metacognitive-learner` 完成後 → `sop_validator.py --check-delivery`）
3. 整合 Layer 3：對可自動化測試的 skill（如 code、browser）建立實際測試案例
