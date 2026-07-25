# delegate_task model 參數不生效 — 已確認 Bug 記錄（2026-06-06）

## Bug 狀態

| 項目 | 內容 |
|------|------|
| **嚴重程度** | 高（影響所有 sub-agent tier routing） |
| **類型** | `delegate_tool.py` schema 缺少 `model` 欄位，參數被靜默忽略 |
| **影響版本** | 所有 hermes-agent 版本（截至 2026-06-06） |

## 受影響的 GitHub Issues

- **#17685** — `delegate_task: per-task model override is silently ignored`：完整忽略，`model` 欄位從未被提取
- **#35409** — `Add profile/model override parameter to delegate_task`：schema 根本沒有 `model` 欄位
- **#11999** — `delegate_task` always runs subagents on the parent session's model
- **#12440** — Sub-agent model configuration is ignored，導致 context window 錯誤

## 根因分析

`hermes-agent/tools/delegate_tool.py` 第 2438-2463 行的 `DELEGATE_TASK_SCHEMA` 任務屬性：

```python
# 只有：goal, context, toolsets, acp_command, acp_args, role
# 沒有 model！
```

當 `delegate_task(goal=..., model="MiniMax-M3")` 被呼叫時：
1. `model` 參數傳入 schema
2. schema 驗證時找不到 `model` 欄位（未定義）
3. 該參數被靜默丟棄，`model` 變成 `None`
4. dispatcher 發現 `model is None` → fallback 到 parent session model

## Workaround（目前無解）

**沒有乾淨的繞過方式**。所有嘗試都失敗：
- `delegate_task(goal=..., model="X", provider="Y")` → model 被忽略
- 改 `config.yaml` 的 `delegation.model` → 只對「不指定 model」的 sub-agent 有效
- 在 sub-agent 內部執行 `hermes chat --provider X` → 不是真的 sub-agent，是另一層呼叫

唯一「可行」但破壞性的方式：派 premium task 前全域改 `delegation.model`，派完改回。但這樣無法同時跑 standard + premium 並行。

## 對 hermes-tier-router 的影響

- **standard tier**：`delegation.model = MiniMax-M2.7` 全域預設 → ✅ 有效（不指定就會走）
- **premium tier**：`delegate_task(..., model="MiniMax-M3")` → ❌ 完全不生效，永遠走 M2.7

hermes-tier-router skill 目前價值：**僅 standard tier 有效**。

## 驗證方式（2026-06-06 實測）

```bash
# 派 sub-agent 指定 deepseek-chat，觀察輸出仍是 MiniMax-M2.7
# 耗時：27s/31s/134s（三個全部走同一 model）
```

## 何時再查

- 追蹤 #17685 的 fix 版本發布
- 或自己 patch `delegate_tool.py` 加 `model` 到 schema + 提取 + 傳遞

## 相關檔案

- `hermes-tier-router/SKILL.md` — 路由決策表（含目前限制說明）
- `trial-and-error/references/by-category/hermes-config-tuning.md` — L3 試誤完整記錄
- `metacognitive-learner/references/provider-verify-pitfalls.md` — 驗證陷阱