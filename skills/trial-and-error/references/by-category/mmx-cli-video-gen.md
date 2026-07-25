
---

### mmx-cli video generate 參數錯誤（2026-06-27）
**症狀**: `mmx video generate --help` 顯示正確參數（`--first-frame`、`--subject-image`、`--last-frame`），但 SKILL.md 紀錄的是錯誤參數（`--input`、`--duration`、`--fps`）。用戶或赫米斯照 SKILL.md 操作會得到 `Error: Flag --input requires a value`。

**根因**: SKILL.md v1.1.0 撰寫時未實際執行 `mmx video generate --help` 驗證，是從網路資料推斷的。實際 CLI 行為（v1.0.16）與文件不符。

**解法**: 
1. 執行 `mmx video generate --help`（stderr 輸出）取得真實參數
2. 發現 T2V/I2V/SEF/S2V 四種模式（舊文件只提及 I2V）
3. 發現 `--async`/`--no-wait`/`--poll-interval`/`--callback-url` 等 agent/CI 模式專用參數
4. 建立參數更正區塊，標記舊錯誤

**預防**: 所有 CLI skill 文件寫入前，**必須**實際執行 `mmx <command> --help` 驗證，不可只靠網路資料推斷

**驗證命令**: 
```bash
mmx video generate --help 2>&1 | grep -E "first-frame|last-frame|subject-image|no-wait|async"
```

**If→Then**: **If** mmx CLI 文件記載的參數與實際行為不符 **Then** 執行 `mmx <subcommand> --help 2>&1` 交叉驗證，以 CLI 實際輸出為準
