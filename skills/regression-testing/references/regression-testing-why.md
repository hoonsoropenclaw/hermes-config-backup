# regression-testing Reference — 2026-06-13

## L3 Lesson: 為什麼需要 regression-testing 而不只是 e2e-minimum-checklist

**問題**: `e2e-minimum-checklist` 是靜態 pass/fail 健康檢查（"這 10 件事現在能不能做"），不知道"相較上次變更有沒有功能退化"。

**具體案例**: school-bulletin 06-11 棒 1 commit 了 AND 篩選功能，e2e-minimum-checklist 全綠，但 production 跑 AND 篩選時 `TypeError: Cannot read properties of undefined (reading 'length')` → 500。問題不是"篩選功能健不健康"，而是"這次變更（commit X）把原本正常的 AND 邏輯改壞了"。

**根本差異**:

| | e2e-minimum-checklist | regression-testing |
|--|---|---|
| 機制 | pass/fail | baseline snapshot vs current diff |
| 問的問題 | "這 10 件事能不能做？" | "這次變更破壞了什麼本來正常的功能？" |
| 捕捉的問題 | 某功能完全壞掉（500） | 功能退化（200 但邏輯錯誤） |

**正確串接**:

```
handoff-chain-acceptance-sop（PRD 4 步對照）
    ↓
e2e-minimum-checklist（10 項健康檢查）
    ↓
regression-testing（API snapshot diff）
    ↓
vercel deploy（或 revert）
```

## run_regression.sh 使用方式

```bash
# 第一次跑（自動建立 baseline）
bash ~/.hermes/scripts/run_regression.sh https://your-app.vercel.app

# 之後每次跑（自動比對）
bash ~/.hermes/scripts/run_regression.sh https://your-app.vercel.app

# 看 diff
diff /tmp/regression_baseline/... /tmp/regression_YYYYMMDD_HHMMSS/...
```

## 維護注意事項

- baseline 預設放 `/tmp/regression_baseline/`（tmpfs，會被清）
- 正式專案應在 `~/` 下建立專屬 baseline 目錄
- 要更新 baseline（確認這次變更是 intended change）：`cp /tmp/regression_current/* /tmp/regression_baseline/`
