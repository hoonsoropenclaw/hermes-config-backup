---

### 代理鏈串接：market-strategist → product-planner 自動化（2026-06-10）

**症狀**：建立了 `market-strategist` + `product-planner` 兩個常駐代理，但每次需要手動執行串接——從 `~/.hermes/handoff/<slug>/market-research.md` 讀取報告再手動觸發下一棒，無法自動化。

**根因**：赫米斯的 profile 只是被動等待 CLI 指令，沒有「pipeline 觸發器」機制——上一棒完成後不會自動啟動下一棒。

**解法**：用 bash wrapper script 實現 chain 自動化：
```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT_SLUG="${1:?用法: $0 <project-slug>}"
HANDOFF_DIR="$HOME/.hermes/handoff/$PROJECT_SLUG"
mkdir -p "$HANDOFF_DIR"

hermes -p market-strategist chat -q "執行 market-research，交付到 $HANDOFF_DIR/market-research.md" --cli --no-input
test -f "$HANDOFF_DIR/market-research.md" || { echo "ERROR: market-research.md 未產生" >&2; exit 1; }

hermes -p product-planner chat -q "從 $HANDOFF_DIR/market-research.md 讀取並產出 prd" --cli --no-input
test -f "$HANDOFF_DIR/prd.md" || { echo "ERROR: prd.md 未產生" >&2; exit 1; }

ls -la "$HANDOFF_DIR/"
```

**預防**：
- handoff 目錄在 chain 開始前要先 `mkdir -p`
- 每棒完成後要驗證檔案存在（`test -f`）再觸發下一棒
- 任何一棒失敗時 `set -e` 會中斷 chain，不執行爛攤子
- 要擴展第三棒（工程代理）時，在 wrapper 中新增 `hermes -p <agent> chat ...` 即可，原則不變

**If→Then**：
- **If** 要串接多個常駐代理形成 chain **Then** 用 bash wrapper script + `hermes -p <profile> chat --cli --no-input` 模式
- **If** 要擴展 chain（加第三棒工程代理）**Then** 在 wrapper 中新增一行即可，不用改 SOP

**相關條目**：`[[profile-handoff-observations-2026-06-10#觀察 1：常駐代理 sandbox HOME 隔離導致絕對路徑可能繞路]]`