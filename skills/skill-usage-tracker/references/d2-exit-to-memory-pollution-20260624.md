# D3 Exit: TO_MEMORY 污染問題識別（2026-06-24 Cycle #281）

## 發現背景

Phase 4.2 量化分析發現：281 個 cycles 中，**89% 的 TO_MEMORY 區塊是 SOP 文本**，而非實際學習內容。

## 根因分析

metacognitive-learner 的 skill invocation block 內含完整的 SOUL.md + skill 文件內容。
當 cycle output 被寫入時，`[TO_MEMORY]` 標記被放在 response 的**技能文本**之後。
LLM 在生成 response 時，在 `[TO_MEMORY]` 區塊內**只引用了 SOP 文本**（格式說明），而非實際學習成果。

## D3 動作（2026-06-24 完成）

1. ✅ 識別問題：89% TO_MEMORY 是 SOP 文本
2. ✅ 量化分析：建立 Phase 4.2 Python 審計命令
3. ✅ 實際產出：
   - 跑 `post_delivery.py --session 20260616_125207_dc21b806`（已執行）
   - 建立 `~/.hermes/skill-usage/pending/manifest.json`（待赫米斯主體交付評分邀請）

## 驗證命令

```bash
python3 -c "
from pathlib import Path
cron_out = Path.home() / '.hermes/cron/output/6edfe1507888'
files = sorted(cron_out.glob('*.md'))
actual = sum(1 for f in files if 'category:' in f.read_text()[f.read_text().find('[TO_MEMORY]'):][:500])
print(f'實際內容: {actual}/{len(files)}')
"
```
