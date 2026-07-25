# D3 Exit Record: SOP-A/B/C + post_delivery.py（2026-06-21）

**Cycle**: metacognitive-learner, 2026-06-21 10:00
**Trigger**: D2 loop trap — `skill-usage-tracker` 06-18 建立，06-21 前從未執行一次「交付後 SOP」，導致 combo_rating = 0 連續 6 天。

## Root Cause

**Layer 2 `session_skill_logger` 只追蹤 `skill_view`（SKILL.md 載入），不追蹤隱性工具。**

驗證：對 `20260616_125207_dc21b806` 直接查 state.db：

| Tool | Count | SKILL.md？ |
|------|-------|-----------|
| execute_code | 11x | 隱性 |
| vision_analyze | 10x | 隱性 |
| terminal | 7x | 隱性 |
| session_search | 4x | 隱性 |
| write_file | 2x | 隱性 |
| **skill_view** | **2x** | **顯性（唯一被追蹤的）** |
| SKILL.md 涵蓋率 | — | **~10%** |

結論：`session_skill_logger` 的「2 個 SKILL.md」只反映 10% 的實際工作量，其餘 90% 藏在隱性工具 domain。

## What Was Built

1. **`scripts/post_delivery.py`**（新建，7,728 bytes，mtime 2026-06-21 10:01:25）
   - 從 state.db 完整查詢 `messages.tool_name` 分佈（顯性 + 隱性）
   - 計算隱性技能強度（HIGH: ≥3 domains ≥3x / MEDIUM / LOW）
   - 生成含隱性 domain 的「標準評分邀請格式」
   - 支援 `--write --rating N --comment` 直接寫入 log

2. **SKILL.md v1.6.0 新增章節**：
   - SOP-A：任務交付後 SOP（Step 1: post_delivery.py → Step 2: 附上邀請 → Step 3: 寫入 log）
   - SOP-B：「已建立但未激活」skill 審計流程
   - SOP-C：analyze.py 0 筆 combo_rating 時強制警告

3. **`analyze.py` 更新**：新增 SOP-C alert block

## Verification

```bash
python3 -m py_compile ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py
# ✅ syntax OK

python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
  --session 20260616_125207_dc21b806
# ✅ 輸出：隱性技能強度: HIGH
# ✅ 輸出：execute_code 11x + vision_analyze 10x + terminal 7x

python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py
# ✅ 輸出：⚠️ [SOP-C ALERT] 0 筆 combo_rating！

ls -la ~/.hermes/skills/skill-usage-tracker/scripts/
# ✅ 3 scripts，post_delivery.py mtime 2026-06-21 10:01:25
```

## Key Lesson

建立 skill ≠ skill 會被自動使用。沒有「激活確認」等於不知道 skill 是否在工作。

SOP-B 的存在是為了消滅「建立了一個 skill，然後它默默空轉 6 天」這種情況。
