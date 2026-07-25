# Hermes Cron Bug 調查記錄（2026-06-04）

## 問題症狀
三個 no_agent cron jobs 連續失敗 4-5 天，錯誤訊息：
```
Script not found: /home/hoonsoropenclaw/.hermes/scripts/#!/bin/bash
python3 /home/hoonsoropenclaw/.hermes/scripts/sync_scheduler.py
```

## 根本原因
`hermes cron edit <id> --script '...'` 對 `no_agent=True` jobs 的 bug：
- `--script` 參數值寫入 `prompt` 欄位（而非 `script` 欄位）
- Scheduler 對 no_agent jobs 讀取 `prompt` 作為 script path 執行
- 導致 `#!/bin/bash\ncd /home/hoonsoropenclaw && bash ...` 被當作路徑

## 修復矩陣

| Job ID | job 名稱 | prompt → null | script 欄位 | no_agent |
|--------|----------|--------------|-------------|----------|
| 06ee7e5e4022 | scheduler-sync | ✅ | sync_scheduler.py | true |
| 591838105a4b | eval-sync | ✅ | sync_evaluations.py | true |
| d99463f25a91 | skill-usage-daily-v3 | ✅ | run_skill_stats.sh | true |

## 驗證結果

直接執行測試（已通過）：
- `scheduler-sync`：✅ exit=0，正常輸出 + git push
- `eval-sync`：✅ exit=1（401 是 API key 不同步，非 cron bug）
- `skill-usage-daily-v3`：✅ exit=0，成功部署網站

## jobs.json 結構參考

正確的 no_agent job 結構：
```json
{
  "id": "06ee7e5e4022",
  "name": "scheduler-sync",
  "prompt": null,
  "script": "sync_scheduler.py",
  "no_agent": true,
  "schedule": {"kind": "cron", "expr": "0 0 * * *"}
}
```

錯誤的結構（prompt 被誤設）：
```json
{
  "prompt": "#!/bin/bash\ncd /home/hoonsoropenclaw && bash scripts/portal_upload_check.sh 2>&1",
  "script": "python3 /home/hoonsoropenclaw/.hermes/scripts/sync_scheduler.py",
  "no_agent": true
}
```

## 關鍵代碼位置

- `_run_job_script()`：`cron/scheduler.py` line ~870-950
- no_agent 處理：`cron/scheduler.py` line 1239：`if job.get("no_agent")`
- `_run_job_script()` 讀取：`script_path = job.get("script")` line 1340
- 但 `prompt` 在 line 1364 被當作 prompt 構建，而非 script

## 診斷命令

```bash
# 看 jobs.json 中 prompt vs script 欄位
cat ~/.hermes/cron/jobs.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for j in data['jobs']:
    print(f\"{j['name']}: prompt={repr(j.get('prompt','NULL'))[:60]} script={repr(j.get('script','NULL'))[:60]}\")
"

# 看最近錯誤
hermes cron list

# 直接測試腳本
python3 ~/.hermes/scripts/sync_scheduler.py
python3 ~/.hermes/scripts/sync_evaluations.py
cd /home/hoonsoropenclaw && bash .hermes/scripts/run_skill_stats.sh
```

## 外部參考

- [Hermes Cron Internals](https://hermes-agent.nousresearch.com/docs/developer-guide/cron-internals)
- [Script-Only Cron Jobs](https://hermes-agent.nousresearch.com/docs/guides/cron-script-only)
- [cron/scheduler.py](https://github.com/NousResearch/hermes-agent/blob/main/cron/scheduler.py)