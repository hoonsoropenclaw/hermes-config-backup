# Chain Automation — 多代理串接自動化 SOP

> 2026-06-10 新增。從 `market-strategist` + `product-planner` 雙棒 chain 實戰中沉澱。

## 問題背景

建立 `market-strategist` + `product-planner` 兩個常駐代理後，每次需要**手動**執行串接：
```bash
hermes -p market-strategist chat -q "..." --cli
# 然後自己從 ~/.hermes/handoff/<slug>/market-research.md 撈報告
hermes -p product-planner chat -q "..."
```

沒有自動化觸發機制。赫米斯的 profile 只是被動等待 CLI 指令，不會在上一棒完成後自動啟動下一棒。

## 解法：Chain Wrapper Script

用 bash wrapper script 實現 chain 自動化。原則：**每棒是獨立 CLI call**，靠 handoff 檔案作為結構化合約。

### 標準模板

```bash
#!/usr/bin/env bash
# chain_runner.sh — 多代理鏈自動化 wrapper
set -euo pipefail

PROJECT_SLUG="${1:?用法: $0 <project-slug>}"
HANDOFF_DIR="$HOME/.hermes/handoff/$PROJECT_SLUG"

# 前置：確保 handoff 目錄存在
mkdir -p "$HANDOFF_DIR"

echo ">> [1/3] market-strategist: 執行市場調研..."
hermes -p market-strategist chat \
  -q "執行 market-research，交付到 $HANDOFF_DIR/market-research.md" \
  --cli --no-input

# 驗證上一棒產出存在再繼續
if ! test -f "$HANDOFF_DIR/market-research.md"; then
  echo "ERROR: market-research.md 未產生，chain 中斷" >&2
  exit 1
fi

echo ">> [2/3] product-planner: 讀取市場報告，產出 PRD..."
hermes -p product-planner chat \
  -q "從 $HANDOFF_DIR/market-research.md 讀取市場報告，產出 prd 到 $HANDOFF_DIR/prd.md" \
  --cli --no-input

if ! test -f "$HANDOFF_DIR/prd.md"; then
  echo "ERROR: prd.md 未產生，chain 中斷" >&2
  exit 1
fi

echo ">> [3/3] 驗收最終產出..."
ls -la "$HANDOFF_DIR/"
echo "Chain 完成"
```

### 加入第三棒（工程代理）

在 wrapper 中新增一段即可，原則不變：

```bash
# 假設第三棒是 coding-agent（工程代理）
if [ -n "${3:-}" ]; then
  AGENT3="${3}"
  echo ">> [3/3] $AGENT3: 讀取 PRD，啟動實作..."
  hermes -p "$AGENT3" chat \
    -q "從 $HANDOFF_DIR/prd.md 讀取 PRD，執行實作" \
    --cli --no-input
fi
```

### 擴展 N 棒 chain

把 wrapper 改成讀取 `chain_config.json`：
```json
[
  {"agent": "market-strategist", "input": "使用者需求", "output": "market-research.md"},
  {"agent": "product-planner",    "input": "market-research.md", "output": "prd.md"},
  {"agent": "coding-agent",       "input": "prd.md", "output": null}
]
```

## 核心設計原則

| 原則 | 說明 |
|------|------|
| **Handoff 檔案作為合約** | 每棒的輸出檔名固定，下一棒才知道去哪讀 |
| **驗證後再繼續** | `test -f <output>` 才觸發下一棒，避免 chain 斷裂 |
| **`set -e`** | 任何一棒失敗就中斷，不繼續執行爛攤子 |
| **`--cli --no-input`** | 批次模式，不需要 stdin 互動 |
| **kebab-case slug** | `school-website`、`freelancer-tax-tool` |

## 已知限制

1. **同步阻塞**：wrapper 會等每棒完成（LLM call 耗時），不適合需要平行執行的場景
2. **無失敗重試**：chain 中斷後需手動重啟，未來可加 `--retry N` 參數
3. **Handoff 檔案無鎖**：多個 wrapper 同時跑同一 slug 會打架（加 `flock` 或用 slug+timestamp）

## 與 `agent-orchestrator` skill 的分工

- `agent-orchestrator`：default profile 內的 skill 自動匹配 + 排序（單一 session 內）
- `hermes-resident-agent + chain-automation`：跨 profile 的多代理 pipeline（多 session 持續）

**不要**用 `agent-orchestrator` 處理跨 profile chain——它的 `scan_registry` 和 `match_skills` 是針對 default profile 的 skills，不是針對其他 profiles 的 CLI wrapper。

## 驗證方式

```bash
# 1. 建立測試 slug
SLUG="test-chain-$(date +%Y%m%d%H%M%S)"
mkdir -p ~/.hermes/handoff/$SLUG

# 2. 跑 2 棒測試
bash chain_runner.sh "$SLUG"

# 3. 檢查產出
ls -la ~/.hermes/handoff/$SLUG/
test -f ~/.hermes/handoff/$SLUG/market-research.md && echo "棒1 OK"
test -f ~/.hermes/handoff/$SLUG/prd.md && echo "棒2 OK"

# 4. 清理測試資料
rm -rf ~/.hermes/handoff/$SLUG
```