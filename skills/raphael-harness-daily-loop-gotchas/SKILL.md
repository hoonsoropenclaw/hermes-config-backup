---
name: raphael-harness-daily-loop-gotchas
description: Raphael Harness 每日循環中 journal/SOP/卡片系統的隱藏欄位與欄位驗證規則（card ID 前綴、sop apply 旗標、journal learned[] 校驗、stale_takeover 接續模式）。給 cron 場景下的 Hermes Agent。
version: 0.1.0
author: Raphael
license: MIT
metadata:
  hermes:
    tags: [Learning, Harness, Pitfalls]
    parent_skill: autonomous-learning
---

# Raphael Harness Daily-Loop Gotchas（2026-10-07 補）

補 autonomous-learning-raphael-harness-pitfalls 沒寫到的細節。

## journal save 會校驗卡片 ID

`learned[]` 與 `reviewed[].id` 必須是 `state/knowledge/cards/` 裡真實存在的檔名（去掉 `.json`）。自己編的 ID 會被擋下：

```json
{"ok": false, "errors": ["learned 中的卡片不存在：<fake-id>（先用 card add）"]}
```

**取得真實 ID**：
```bash
python -m harness card list | python -c "import json,sys; [print(c['id']) for c in json.load(sys.stdin)]"
```

## ID 前綴是「domain-id 取前 ~17 字元」

Harness 把 `domain_id + '--' + topic` 截斷到 ~17 字元當 card 檔名：

- `office-automation--排程與錯誤通知` → 實檔 `office-automatio--排程與錯誤通知.json`
- `office-automation--openpyxl-與-pandas-處理-excel` → `office-automatio--openpyxl-與-pandas-處理-excel.json`
- `admin-documents--公文結構-主旨-說明-辦法` → `admin-documents--公文結構-主旨-說明-辦法.json`（剛好沒截）
- `admin-presentation--金字塔原理-結論先行` → `admin-presentati--金字塔原理-結論先行.json`

寫 journal 前先 `card list` 對齊一次，不要憑印象寫 domain 前綴。

## sop apply 必須用旗標，不能用 positional

```bash
# ✅ 對
python -m harness sop apply --type code --id <pid> --part minor

# ❌ 錯（argparse 拒絕：unrecognized arguments: <pid>）
python -m harness sop apply <pid>
```

`sop propose` 一樣要旗標：`--type code -i /tmp/prop.json`。

## cron 從斷點接續的 stale_takeover

cron 被前次中斷後，下次 `run start` 會回傳 `ok:true` + `takeover.previous_run` + 完整 `completed_steps[]`。**直接從 `next_step` 繼續**，不要重跑已完成的步驟。`evaluate` 之後的 `journal save` 仍會覆蓋同一天的 journal 檔（原子寫入，安全）。

## journal 的 `time_spent_minutes` 欄位

`templates/journal.example.json` 有這個欄位、`journal save` 也接受。建議實際填，幫助後續校準 `plan.budget.max_minutes` 是否合理。