# skill-usage-tracker combo_rating D2 迴圈陷阱（2026-06-25 確認）

## 狀態：已識別 D2（第 3+ cycle），尚未 D3 exit

## 缺口確認時間線

| Date | Cycle | 動作 | 結果 |
|------|-------|------|------|
| 2026-06-16 | ? | 使用者明確要求 skill 追蹤 + 評分 | 僅停在「建議層次」，未執行 |
| 2026-06-18 | D1 | 建立 SKILL.md v1.0.0 | 建檔完成，但從未執行一次 SOP-A |
| 2026-06-20 | D2 | 建立 Layer 2 session_skill_logger | 重建正常，但 combo_rating = 0 |
| 2026-06-21 | D3? | 建立 SOP-A/B/C + post_delivery.py | D3 exit，但 combo_rating 仍是 0 |
| 2026-06-22 | D2 | 第三次識別 combo_rating = 0 | 又停在記錄，未實際邀請評分 |
| 2026-06-24 | D2 | 修 post_delivery.py session ID bug | 修完仍是 0 筆真實評分 |
| **2026-06-25** | **D2** | **第四次識別 combo_rating = 0** | **仍是口頭記錄，未 D3 exit** |

## 驗證數據（2026-06-25 18:55 UTC+8）

```bash
$ wc -l ~/.hermes/skill-usage/*.jsonl
1 /home/hoonsoropenclaw/.hermes/skill-usage/2026-06-18.jsonl
5 /home/hoonsoropenclaw/.hermes/skill-usage/2026-06-20.jsonl
3 /home/hoonsoropenclaw/.hermes/skill-usage/2026-06-21.jsonl
3 /home/hoonsoropenclaw/.hermes/skill-usage/2026-06-22.jsonl
3 /home/hoonsoropenclaw/.hermes/skill-usage/2026-06-24.jsonl
15 total

$ python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py
⚠️  [SOP-C ALERT] 0 筆 combo_rating！
```

**combo_rating 覆蓋率：0/15 = 0%**

## 根因

SOP-A 的「標準評分邀請格式」**從未出現在任何一次赫米斯回覆的末尾**。

`post_delivery.py` 有完整 `generate_invite()` 實作，但：
1. Layer 1 主動記錄從未觸發（依賴自覺，失效）
2. Layer 2 session_skill_logger 只重建 skill 清單，**不產生邀請文本**
3. `generate_invite()` 從未被 main execution path 主動呼叫
4. sub-agent 回覆 = 終點，`pending/` 無人讀取（已確認架構空轉）

## IJCAI 2025 Research 確認

Human rating = **External Feedback 最高價值信號**（Agentic Reward Modeling，arXiv 2502.19328）。`skill-usage-tracker` 的 0% combo_rating = 完全浪費了這個信號。

## 下一步（D3 Exit required）

**不能再 research 了**。必須在下一個接觸使用者的機會中：
1. 在回覆末尾附上 `python3 post_delivery.py --session <id>` 的**實際輸出**
2. 使用者回覆任何星星或數字後立即寫入 `~/.hermes/skill-usage/<today>.jsonl`

**驗證命令**：
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py
# 預期：combo_rating 覆蓋率 > 0%
```
