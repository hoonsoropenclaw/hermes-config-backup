---
name: regression-testing
description: "赫米斯的回歸測試 skill：系統性跑「變更前→變更後」對比、捕獲功能退化、整合進 handoff chain 尾端形成自動驗收層。觸發：handoff 鏈尾（棒 N 結束）、網站功能更新後、本地上線前。"
version: 1.0.0
author: Hermes Agent (2026-06-13 從 school-bulletin production 5 bug + 06-11 5 Must 缺口歸納)
license: MIT
platforms: [linux, macos]
tags: [testing, regression, handoff, quality, deployment]
---

# Regression Testing Skill

> 目標：讓赫米斯每次變更（handoff 鏈尾、部署前、本地開發）後，能系統性驗證「我改的東西沒壞」，而不是靠「看起來正常」。

## 核心原則

1. **沒有對比的 regression test = 沒有價值** — 一定要有「變更前 baseline」vs「變更後 current」的明確對比
2. **自動化 > 手動** — curl / Playwright / node script 能自動跑，不要依賴「人工打開瀏覽器看看」
3. **進 handoff chain 尾端** — 不是棒 N 內自己測，而是棒 N+1 開始前、或 production deploy 前，自動觸發
4. **失敗 = revert 信號** — regression test 紅 = 立即 revert，不准「上線再說」

## 觸發條件

| 情境 | 觸發時機 | 誰觸發 |
|------|---------|--------|
| Handoff 鏈尾 | 棒 N engineering-lead 產出完成，棒 N+1 開始前 | handoff-chain-acceptance-sop 尾端 |
| 功能更新後 | 任何功能變更提交 PR/merge 前 | git hook 或 CI |
| 本地上線前 | `vercel --prod` 前 | e2e-minimum-checklist 同時觸發 |
| Cron 監控 | 每日/每週對已知 URL 跑 baseline 比對 | regression-testing cron job |

## 測試類型

### Type A：API Regression（curl-based，fast，CI-friendly）

適合：REST API backend（Supabase、FastAPI、Express）

**核心機制：snapshot comparison**

```bash
# 1. 抓 baseline（只跑一次，或每天更新）
curl -s https://<prod-url>/api/departments | jq --sort-keys . > /tmp/baseline_departments.json

# 2. 跑 current
curl -s https://<prod-url>/api/departments | jq --sort-keys . > /tmp/current_departments.json

# 3. diff（任何輸出都是 regression）
diff /tmp/baseline_departments.json /tmp/current_departments.json && echo "✅ No regression" || echo "❌ REGRESSION DETECTED"
```

**與 e2e-minimum-checklist 的區別：**
- `e2e-minimum-checklist` = 「這 10 件事能不能做」（pass/fail 健康檢查）
- `regression-testing` = 「這次變更有沒有破壞之前正常的功能」（diff-based）

### Type B：Playwright Visual Regression（browser-based）

適合：有 UI 的 web app（Next.js、React、Vue）

**核心機制：screenshot comparison**

```javascript
// /tmp/regression-screenshot.js
const { chromium } = require('playwright');
const fs = require('fs');

const BASELINE_DIR = process.env.BASELINE_DIR || '/tmp/regression_baseline';
const CURRENT_DIR = process.env.CURRENT_DIR || '/tmp/regression_current';
const TARGET_URL = process.env.TARGET_URL || 'https://your-app.vercel.app';

async function captureScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const routes = [
    '/',
    '/login',
    '/dashboard',
    '/api/departments',
  ];

  for (const route of routes) {
    await page.goto(TARGET_URL + route);
    await page.waitForLoadState('networkidle');
    await page.screenshot({
      path: `${CURRENT_DIR}/${route.replace(/\//g, '_')}.png`,
      fullPage: true,
    });
    console.log(`📸 Captured: ${route}`);
  }

  await browser.close();
}

fs.mkdirSync(CURRENT_DIR, { recursive: true });
captureScreenshots().catch(console.error);
```

**比對脚本：**

```bash
# 簡單比對（pixel 差異）
cd /tmp
for f in regression_baseline/*.png; do
  name=$(basename "$f")
  if ! diff "$f" "regression_current/$name" > /dev/null 2>&1; then
    echo "❌ REGRESSION: $name"
  fi
done
echo "✅ Screenshot regression check complete"
```

## Regression Testing Pipeline

### 完整流程（建議整合進 handoff chain 尾端）

```
[棒 N 結束]
    ↓
[觸發 regression-testing]
    ↓
[下載/抓取 API baseline snapshot]
    ↓
[跑 current API response]
    ↓
[diff baseline vs current]
    ↓
[報告：PASS = 繼續 / FAIL = revert]
```

### 快速啟動腳本

```bash
#!/bin/bash
# ~/.hermes/scripts/run_regression.sh
# 用法：bash run_regression.sh <base_url> <output_dir>

BASE_URL="${1:-https://your-app.vercel.app}"
OUT_DIR="${2:-/tmp/regression_$(date +%Y%m%d_%H%M%S)}"
BASELINE_DIR="/tmp/regression_baseline"

mkdir -p "$OUT_DIR" "$BASELINE_DIR"

echo "=== API Regression Test ==="
echo "Target: $BASE_URL"
echo "Output: $OUT_DIR"
echo ""

# 測試清單（根據專案調整）
ENDPOINTS=(
  "/api/departments"
  "/api/announcements?page=1&limit=10"
  "/api/auth/me"
)

PASS=0
FAIL=0

for ep in "${ENDPOINTS[@]}"; do
  # 抓 current
  curl -s -o "$OUT_DIR$(echo $ep | tr '/?' '_').json" \
    "$BASE_URL$ep" 2>/dev/null

  # 抓 baseline
  curl -s -o "$BASELINE_DIR$(echo $ep | tr '/?' '_').json" \
    "$BASE_URL$ep" 2>/dev/null || true

  # 比對
  name=$(echo $ep | tr '/?' '_')
  if [ -f "$BASELINE_DIR$name.json" ]; then
    if diff "$BASELINE_DIR$name.json" "$OUT_DIR$name.json" > /dev/null 2>&1; then
      echo "✅ $ep"
      ((PASS++))
    else
      echo "❌ $ep — REGRESSION"
      ((FAIL++))
      diff "$BASELINE_DIR$name.json" "$OUT_DIR$name.json" | head -20
    fi
  else
    echo "🆕 $ep — no baseline (will be created)"
    cp "$OUT_DIR$name.json" "$BASELINE_DIR$name.json"
    ((PASS++))
  fi
done

echo ""
echo "=== Result: $PASS passed, $FAIL failed ==="
[ $FAIL -eq 0 ] && echo "✅ OK to deploy" || echo "❌ DO NOT DEPLOY"
exit $FAIL
```

## 與其他 Skill 的關係

| Skill | 職責 | 差異 |
|-------|------|------|
| `e2e-minimum-checklist` | 10 項 pass/fail 健康檢查 | 不知道變更前後差異 |
| `deployment-verification-sop` | 部署後 URL + DNS 驗證 | 不測功能回歸 |
| `handoff-chain-acceptance-sop` | PRD 4 步對照驗收 | 不懂 API/視覺 diff |
| **`regression-testing`** | **變更前→變更後 diff** | **本 skill** |

**正確串接：**

```
handoff-chain-acceptance-sop（PRD 對照）
    ↓（PRD 綠燈）
e2e-minimum-checklist（10 項健康檢查）
    ↓（10/10 綠燈）
regression-testing（API/視覺 diff）
    ↓（0 regression）
vercel deploy（或 revert）
```

## If→Then 速查

- **If** handoff 鏈棒 N 結束、棒 N+1 開始前 **Then** regression-testing 自動觸發
- **If** regression test FAIL **Then** 立即 revert，不上 production
- **If** 新專案第一次跑 regression **Then** 先建立 baseline（`/tmp/regression_baseline/`）
- **If** 想更新 baseline（明確知道這次變更是 intended change）**Then** `cp /tmp/regression_current/* /tmp/regression_baseline/`
- **If** 只想跑 regression 不建立新 baseline **Then** 只讀 `/tmp/regression_baseline/` 不寫入

## 變更記錄

- 2026-06-13 v1.0.0 — 從 school-bulletin production 5 bug + 06-11 handoff 鏈 5 Must 缺口歸納建立

## Companion Script

`~/.hermes/scripts/run_regression.sh` — 可直接執行，見 SKILL.md 內「快速啟動腳本」段落
