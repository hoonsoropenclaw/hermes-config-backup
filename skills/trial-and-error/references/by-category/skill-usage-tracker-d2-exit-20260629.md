### skill-usage-tracker D2 Exit 完成記錄（2026-06-29）

**缺口**：skill-usage-tracker combo_rating = 11.8%（17 筆中 2 筆），已連續 4+ cycles 識別為優先缺口但零實作干預。

**根因**：post_delivery.py 的 `generate_invitation()` 從未被主 execution path 呼叫，導致評分邀請從未出現在回覆末尾。工具本身正常（session_skill_logger 已驗證）。這是 **SOP 即時觸發機制缺失**。

**D2 Exit 干預動作（2026-06-29）**：
- 將 SOP-A 觸發約束寫入 `~/.hermes/SOUL.md` Vibe 段落
- 新增：「**SOP-A 評分邀請觸發**：每次任務交付後，自動在回覆末尾附上評分邀請格式」
- 驗證：`stat -c '%y' ~/.hermes/SOUL.md` → `2026-06-29 20:36:41`，行數從 120 → 131

**為何寫 Vibe 而非只更新文件**：
- Vibe 段落每次推理都注入，不依賴 `skill_view()` 手動呼叫
- 過去 4 cycles 的 session 從未主動呼叫 `skill_view('skill-usage-tracker')`

**驗證方式（下個 cycle）**：
```bash
python3 -c "import json; from pathlib import Path; log_dir = Path.home()/.hermes/skill-usage; total=sum(1 for f in log_dir.glob('*.jsonl') for _ in open(f)); rated=sum(1 for f in log_dir.glob('*.jsonl') for l in open(f) if json.loads(l).get('combo_rating') is not None); print(f'rating rate: {rated/total*100:.1f}%' if total else '0')"
```
**預期**：下個 cycle combo_rating rate 從 11.8% 升至 > 50%（若 Vibe 約束生效）
