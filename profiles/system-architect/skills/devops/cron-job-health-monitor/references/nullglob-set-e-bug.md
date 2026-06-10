# Nullglob + set -e Bug in cron Scripts

## 問題（2026-06-10 發現）

**症狀**：
```
last_error: Script exited with code 2
# 但手動執行: bash script.sh → EXIT 0（成功）
```

`exit code 2` 是 `set -euo pipefail` + `pipefail` 的組合效果。

**觸發程式碼**：
```bash
#!/usr/bin/env bash
set -euo pipefail

today_log="$CRON_OUTPUT/$job_id/${TODAY}_"*".md"   # glob expands to 0 files
latest=$(ls -t $today_log 2>/dev/null | head -1)   # ls with no args → exit 1
# pipefail → script exits with code 1 from ls
```

**實際發生的情況**：
1. `shopt -s nullglob` 是預設**關閉**的
2. Pattern 匹配 0 個檔案時，`ls *.md` 擴展成 `ls`（無參數）
3. `ls`（無參數）寫到 stderr: `ls: cannot access '*.md': No such file or directory` → exit 1
4. `head -1` 收到 empty stdin → exit 1
5. Pipeline exit code = last command (`head -1`) = 1
6. `set -e` + `pipefail` → script exits with code 1

**赫米斯受影響的 script**：`hermes-backup-daily-summary.sh`（v4-daily-summary cron job）

**為何手動執行成功**：
- 當天有 log 檔時，`ls -t *.md` 匹配到 1+ 檔案，正常執行
- 只有在「pattern 匹配 0 檔」時才觸發 bug

**修復方式**：
```bash
shopt -s nullglob    # 0 match 時返回空字串，不報錯
today_log="$CRON_OUTPUT/$job_id/${TODAY}_"*".md"
latest=$(ls -t $today_log 2>/dev/null | head -1 || true)  # 加 || true 防萬一
shopt -u nullglob    # 事後還原
```

**驗證**：
```bash
# 觸發 bug（今天非週日）：
bash ~/.hermes/scripts/hermes-backup-daily-summary.sh
# 修復前：EXIT 2
# 修復後：EXIT 0

# 測試 nullglob 本身：
shopt -s nullglob; ls /tmp/nonexistent*.md 2>/dev/null; echo "exit=$?"; shopt -u nullglob
# exit=0（空字串，無錯誤）
```

## If→Then

**If** `set -euo pipefail` 腳本在 glob 匹配 0 檔時無故退出（exit code 2）、但手動執行成功（exit 0），**Then** 根因是 `ls *.md` 無匹配時返回 exit 1，pipefail 捕獲導致中斷，解法是加 `shopt -s nullglob`。

## 預防

任何 cron script 有 `set -euo pipefail` + glob + `ls` + `head` 的組合，必須默認加 `shopt -s nullglob`：
```bash
set -euo pipefail
shopt -s nullglob   # ADD THIS before any glob expansion
```

## 相關條目

- `hermes-internal.md` — cron script bug 修復記錄
- `bash-defensive-patterns.md` — nullglob 模式