# Nullglob + set -e: When Glob Matches Zero Files

## 問題

**症狀**：
```bash
#!/usr/bin/env bash
set -euo pipefail

files=(~/logs/*.log)           # glob expands to 0 files → becomes: files=(~/logs/)
latest=$(ls -t "${files[@]}" | head -1)  # ls with no args → exit 1
# Script dies with "exit code 1" or "exit code 2"
```

手動執行可能成功（因為剛好有檔案），但 cron 執行時失敗（因為排程時間剛好沒檔案）。

## 根因

`shopt -s nullglob`（預設關閉）：
- **Off**：pattern 匹配 0 檔 → 展開成 literally `~/logs/*.log`（不會變空）
- **On**：pattern 匹配 0 檔 → 整個 pattern 消失（變成 0 個 arguments）

多數 shell script 預設 `nullglob` 關閉，所以 `ls *.log` 無匹配時變成 `ls *.log`（不變），導致 `ls: cannot access '*.log': No such file or directory` → exit 1。

## 修復

```bash
#!/usr/bin/env bash
set -euo pipefail

shopt -s nullglob          # ADD THIS before any glob
logs_dir="$HOME/logs"
today_logs="$logs_dir/$(date +%Y-%m-%d)_"*".log"
latest=$(ls -t $today_logs 2>/dev/null | head -1 || true)
shopt -u nullglob          # restore after

if [[ -z "$latest" ]]; then
    echo "No logs found for today"
fi
```

## 為何加 `|| true`

即使加了 nullglob，在 subshell 內 `ls -t ""` 仍可能返回 exit 1。加 `|| true` 確保 pipefail 不會在這行中斷。

## 預防 Checklist

任何 `set -euo pipefail` script 有以下任一組合，必須加 nullglob：
- [ ] `ls *.md`
- [ ] `files=(*.log)`
- [ ] `for f in ~/path/*; do`
- [ ] `cp ~/dir/*.txt ~/backup/`

## 相關

- `cron-job-health-monitor` — 實際案例：v4-daily-summary hermes-backup-daily-summary.sh
- `hermes-internal.md` — cron script bug 修復記錄