# skill-usage-tracker D3 Exit — SOP-A Gap Confirmed (2026-06-22)

## 事件摘要

2026-06-22 metacognitive-learner cycle 確認：`skill-usage-tracker` SKILL.md v1.6（2026-06-18 建立）在建立後的 4 天內：

- **0 筆 combo_rating 真實 entry**
- **SOP-A 從未在任何真實 user session 被執行**
- 使用者 06-16 明確要求「記錄並評價技能效果」，但赫米斯從未附上評分邀請

## 根因

**LRU cache 錯覺**: SKILL.md 是「推理時刻的額外上下文」，不是「觸發鉤子（hook）」。LLM 每次推理都是獨立的——定義了 SOP 不等於會自動執行。

## 驗證命令

```bash
# 確認 06-16 session 的 tool 分佈（已確認：94.9% 隱性工具）
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
    --session 20260616_125207_dc21b806

# 確認 skill-usage log 有 task 記錄但 0 評分
python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py --min-ratings 1
```

## 產出

1. **L3 lesson** 寫入 `trial-and-error/references/by-category/hermes-internal.md`（見上方新條目）
2. **口頭補救**: 這個 cycle 通過 cron-to-telegram 回應了 06-16 session 的補評邀請
3. **Layer 2.5 評估**: `automated-sop-validation` 目前只檢查「技術輸出格式」，不檢查「SOP-A 執行與否」。這是 future improvement。

## 狀態

- `skill-usage-tracker/SKILL.md` v1.6 ✅ 已建立（mtime 2026-06-18）
- `skill-usage-tracker/scripts/post_delivery.py` ✅ 已建立（mtime 2026-06-21）
- `skill-usage-tracker/scripts/analyze.py` ✅ 存在
- **SOP-A 執行率**: 0/9 任務（定義了但從未執行）
- **Layer 1 服從性**: 0/9（赫米斯從未自覺觸發）

## 下一步

若使用者回覆了這個補評邀請，立即執行：
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
    --session 20260616_125207_dc21b806 --write \
    --rating <N> --comment "<user reply>"
```
