# Layer 2.5 Validator Integration Pattern

**日期**: 2026-05-31
**問題**: `automated-sop-validation` 引擎已實作，但從未被呼叫——validator 存在卻是裝飾。

---

## 整合模式

### 發現經過

Cron job `metacognitive-learner-24h` 的 `skills` 陣列包含 `"session_search"`（MCP 工具），導致連續 13+ 次執行時 skills 載入失敗但無阻斷。`automated-sop-validation` 的 `sop_validator.py` 已完整實作（AgentContract SDK + FallbackValidator 雙軌），卻從無任何消費端呼叫它。

### 正確整合方式

**原則**: 不要依賴 cron/job 系統的 post-hook（目前無此機制），由學習者自己在交付前呼叫驗證。

在 `metacognitive-learner` SKILL.md Phase 4.5 中新增：

```bash
python3 ~/.hermes/skills/productivity/automated-sop-validation/scripts/sop_validator.py \
  --check-delivery <task_type> --json -- < <(cat <<'EOF'
[完整輸出內容]
EOF
)
```

### 實測命令

```bash
cd ~/.hermes/skills/productivity/automated-sop-validation

# 從 stdin 讀取輸出（支援 heredoc）
echo '## 學習摘要...' | python3 scripts/sop_validator.py \
  --check-delivery metacognitive-learner --json -

# 從檔案讀取
python3 scripts/sop_validator.py \
  --check-delivery metacognitive-learner --json - < output.txt
```

### FallbackValidator vs AgentContract SDK

| 層面 | AgentContract SDK | FallbackValidator |
|------|-----------------|-------------------|
| YAML 載入 | `Contract.from_yaml()` 有相容性問題 | `yaml.safe_load()` 正常 |
| Pattern 比對 | 原生支援 | `re.search` |
| Required Element | 原生支援 | 子字串比對（`in`） |
| 目前狀態 | 無法載入 ❌ | 正常運作 ✅ |

AgentContract SDK 的 `from_yaml` 在 v0.2.0 有破壞性變更，已確認 `/tmp/ac-env` venv 中的 FallbackValidator 完全可用。AgentContract SDK 整合改列「長期研究」而非「待實作」。

### Cron Job skills 陣列維護

`~/.hermes/cron/jobs.json` 中的 `skills` 陣列：只放「存在且穩定」的 skill。MCP 工具（如 `session_search`）應視為可選依賴而非必要項目。

---

## If→Then 經驗

**If** 需要為一個已實作但未整合的工具關閉閉環
**Then** 在使用該工具的 skill 中新增 Phase 4.5 自我驗收步驟，不要等待系統鉤子

**If** cron job 的 skills 陣列包含已連續失敗的 MCP 工具
**Then** 直接從 skills 陣列移除——它會一直 skip 且不阻斷，長期忽略真正問題

**If** AgentContract SDK 的 `from_yaml` 載入失敗
**Then** 使用 FallbackValidator（純 Python regex）作為備援，繼續正常運作
