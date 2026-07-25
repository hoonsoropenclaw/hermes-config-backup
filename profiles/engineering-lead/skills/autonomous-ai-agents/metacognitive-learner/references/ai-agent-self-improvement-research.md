# AI Agent Self-Improvement Research — Condensed

**更新日期**: 2026-06-08
**來源**: arXiv papers + ICML/NeurIPS 2025 + Yohei Nakajima synthesis

---

## SOP-Agent (arXiv:2501.09316, Jan 2025)

### 核心發現
- 將 SOP 表示為**決策圖（decision graph）**：節點 = 候選動作，邊 = IF/ALWAYS 條件
- 使用 GPT-4 tool call interface 在**單次查詢**中生成所有必要 function calls（DFS 策略）
- 實驗結果：data cleaning 100% 成功率，ALFWorld 88.8%（超越 AutoGPT 66.2%）

### 對赫米斯的啟發
- SOP 可轉換為可執行規則，適合 Layer 2.5 自動化驗收
- 決策圖方式比純文字 SOP 更機器可讀

---

## CRITIC (ICLR 2024)

### 核心發現
- **LLM 無法仅靠自身進行可靠的自我驗證**
- 外部工具互動是 self-correct 的關鍵
- 移除搜索 API 後，CRITIC 改善微弱甚至退化

### 對赫米斯的啟發
- 驗證必須是**外部觸發**，不能依賴 agent 自己判斷
- Layer 2.5 必須是獨立的檢查步驟，不是 agent 輸出的一部分

---

## Agent Behavioral Contracts (arXiv:2602.22302, Feb 2026)

### 核心發現
- 四元件框架：**P**reconditions、**I**nvariants、**G**uarantees、**R**ecovery
- 數學證明 Drift Bounds Theorem：當 γ > α 時，drift 有上限 D* = α/γ
- 1980 sessions 實驗：檢測到 5.2–6.8 個 soft violations（baseline 完全漏掉）
- 實作：`AgentAssert` (agentassert.com) + `AgentContract` (GitHub agentcontract/spec)

### 對赫米斯的啟發
- `.contract.yaml` 格式是 Layer 2.5 的具體實作方向
- R (Recovery) 機制是閉環關鍵

---

## AgentContract 開放規範

### 規格
- GitHub: `agentcontract/spec` — Apache 2.0
- Python/TS/Rust 參考實作
- `.contract.yaml` 格式社群 contract 庫

### 合約格式範例
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

## TICK (arXiv:2410.03608)

### 核心發現
- LLM 生成 instruction-specific checklist 來評估 LLM 輸出
- 完全自動化的可重複 SOP 合規檢查

### 對赫米斯的啟發
- 可與 SOP-Agent 決策圖結合，自動生成驗收檢查清單

---

## 三層服從架構

| 層級 | 機制 | 穩定性 | 赫米斯狀態（2026-06-04 更新）|
|------|------|--------|------------|
| Layer 1 | SOP 寫在技能文件裡 | 低 | ✅ 80+ SOP |
| Layer 2 | `tool_use_enforcement: true` | 中 | ✅ 已設定 |
| Layer 2.5 | 自動化對照 SOP 檢查 | 高 | ✅ 已實作（automated-sop-validation）|
| Layer 3 | 外部基準/自動化測試 | 高 | ❌ 缺失 |

### 更新：2026-06-04（Layer 2.5 已實作）
- 引擎：`skills/productivity/automated-sop-validation/scripts/sop_validator.py`
- 合約：`skills/productivity/automated-sop-validation/contracts/hermes-default.contract.yaml`
- FallbackValidator：純 Python regex 實作（agentcontract SDK 載入失敗時備援）

**核心原則**: 增加外部強制約束（Layer 2/3）而非只改善 skill 文件內容（Layer 1）。

---

## 新增：ICML 2025 — Truly Self-Improving Agents Require Intrinsic Metacognitive Learning

**來源**: Liu & van der Schaar, ICML 2025 Position Paper Track
**URL**: https://openreview.net/forum?id=4KhDd0Ozqe

### 核心論點
- 現有 agent 的 self-improvement 多是 **extrinsic**（固定、人類設計的反饋迴圈），無法擴展和適應新環境
- **Intrinsic metacognitive learning**：agent 主動評估、反思、調整自己的學習過程
- 三元件框架：**metacognitive knowledge**（自我評估能力）、**metacognitive planning**（決定學什麼+怎麼學）、**metacognitive evaluation**（反思學習經驗改善未來學習）

### 對赫米斯的直接影響
- 赫米斯的 `metacognitive-learner` 是 **extrinsic 迴圈**（固定每 2 小時喚醒、執行固定流程）——符合現狀
- 真正的 intrinsic 能力：赫米斯能否**根據過往學習成效動態調整下一個 cycle 的學習策略**？
- 缺口：當前沒有「根據學習成效調整學習方向」的機制

### 三層服從架構更新

| 層級 | 機制 | 赫米斯狀態 |
|------|------|------------|
| Layer 1 | SOP 寫在技能文件裡 | ✅ 80+ SOP |
| Layer 2 | `tool_use_enforcement: true` | ✅ 已設定 |
| Layer 2.5 | 自動化對照 SOP 檢查 | ✅ 已實作 |
| Layer 3 | 外部基準/自動化測試 | ❌ 缺失 |
| **Layer 3.5（新增）** | **Intrinsic metacognitive planning**（根據學習成效動態調整策略） | ❌ 完全缺失 |

---

## 新增：NeurIPS 2025 Synthesis — Better Ways to Build Self-Improving AI Agents

**來源**: Yohei Nakajima, NeurIPS 2025 Synthesis
**URL**: https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents

### 三個「真正自我改進」的判定條件
1. Agent **改變自己的行為**（不只是抽樣多個輸出）
2. 改變由 **agent 自己經驗/回饋/生成數據** 驅動（非人類標籤）
3. 機制 **整合进 agent 迴圈**（非一次性離線微調）

### 六大機制摘要

#### 1. Self-Reflection & In-Loop Feedback（Reflexion, Self-Refine）
- Reflexion: HumanEval 80% → 91%（GPT-4 baseline）
- 限制：改進是 ephemeral 的（重啟後消失），除非持久化到 skill library

#### 2. Self-Generated Data & Auto-Curricula（最接近赫米斯的方向）
- Self-Challenging Agents: RL on self-generated tasks，LLaMA-3.1-8B 在 M³ToolEval/TauBench 效能**翻倍**
- Self-Generated In-Context Examples: ALFWorld 73% → 89%（有時 73% → 93%）
- **關鍵設計挑戰**：Signal quality — label/reward 從哪來？如何過濾 bad self-labels？

#### 3. Self-Adapting Models（SEAL 等）
- SEAL: model generates self-edit instructions → fine-tuning examples， factual QA 33.5% → 47%

#### 4. Self-Improving Code Agents（最強，因为 code 可執行+tests 便宜）
- **STO (Self-Taught Optimizer)**: 迭代改進自己的 code，发现 beam search、simulated annealing、genetic algorithm autonomously
- **SICA**: Agent 直接編輯自己的 agent script，17-53% 性能提升
- **Voyager**: skill library 持久化成功軌跡供 reuse
- **關鍵模式**：skills/strategies 表示為**可執行 artifact（code）**，給 agent 修改能力

#### 5. SICA — Self-Improving Coding Agent（對赫米斯最有參考價值）
- 核心：Evaluate → if unsatisfactory → self-edit phase → re-evaluate → keep changes that improve metrics
- 赫米斯的 trial-and-error skill 是類似「skill library」機制，但缺少 **自我修改** 能力（只能追加，不能重寫既有條目）

#### 6. Voyager — Persistent Skill Library
- 成功 skills 存進 skill library，reuse 在未來任務
- **赫米斯已實作**：trial-and-error = persistent skill library

### 赫米斯的具體缺口

| 機制 | 赫米斯狀態 | 缺口 |
|------|------------|------|
| Skill library（成功軌跡持久化） | ✅ trial-and-error skill | — |
| Self-generated curriculum（根據缺口生成學習任務） | ❌ 沒有 | Phase 2 優先排序是固定的（基於簡單打分，無自我生成） |
| Self-edit phase（根據驗效結果修改技能） | ❌ 只能追加不能重寫 | trial-and-error 條目只增不修，舊條目錯誤會永遠留存 |
| External validation（修復後外部驗證） | ⚠️ partial（Phase 4.5 SOP validator） | 只驗格式，不驗實際效果 |
| Metacognitive planning（根據成效動態調整） | ❌ 完全缺失 | 每個 cycle 都用相同流程，不根據過往成效調整 |

### 下一個改進方向

**If** 要讓赫米斯的「自主學習」真正有效
**Then** 需要在 trial-and-error 機制上增加「自我修改」能力：
1. 允許 agent 根據驗證結果**修訂**現有條目（不只是追加）
2. 根據條目使用頻率/成功率**排序**學習優先級
3. 引入類似 SICA 的「evaluate → self-edit → re-evaluate」閉環

### Reflexion（Stanford Shinn et al.）
- **核心發現**：agents with verbal self-reflection 達成 91% pass@1 on HumanEval（GPT-4 baseline 80%）
- **關鍵**：self-improvement 有效不是因為「自己反省」，而是「有 rubric 可對照」
- **數據**：58.3% → 78.2% 準確率提升（在有 external validation 的條件下）

⚠️ **沒有外部驗收的 self-improvement 是裝飾**。automated-sop-validation 是正確方向。

---

## 驗證要點

- If: 發現 SOP 服從性不足 → 先檢查是否有外部驗收機制
- If: 要實作 Layer 2.5 → 參考 SOP-Agent 決策圖 + AgentContract 格式
- If: LLM 輸出需要驗證 → 外部觸發，不能依賴 LLM 自己