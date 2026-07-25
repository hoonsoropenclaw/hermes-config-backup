# Cron Error Message Shows Wrong Script Name — `prompt: ""` Bug (2026-06-08)

## Pattern

**症狀**: `hermes cron list` 顯示 error，但 error message 中的 script 路徑/名稱與 jobs.json 中實際的 `script` 欄位值不符。

**實際案例**:
- Job `hermes-config-backup-daily` (id: `65f2dc3583d5`)
- jobs.json 中 `script: "backup_hermes_v3.sh"` ✅ 正確
- `prompt: ""`（空字串）❌ — 空字串不是 `null`
- cron error message 顯示舊 script: `Script timed out after 120s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes.sh` ❌
- 實際存在的 script 是 `backup_hermes_v3.sh`（19976 bytes）而非 `backup_hermes.sh`（18988 bytes）

## 根因

Scheduler 的 `_run_job_script()` 對 no_agent jobs 讀取 `prompt` 作為 script path（不是 `script` 欄位）。

當 `prompt` 是**空字串** `""`（JSON string type）而非 `null` 時：
- `prompt: null` → Scheduler 走 `script` 欄位 ✅
- `prompt: ""` → Scheduler 可能對空字串做 fallback，使用了某個 legacy/compiled-in script path ❌

所以 jobs.json 中 `script: "backup_hermes_v3.sh"` 是正確的，但從未被讀取。

## 正確修復（2026-06-08 驗證通過）

直接編輯 jobs.json：
1. 將 `prompt` 改為 `null`（**不是空字串** `""`）
2. 確認 `script` 為正確檔名（如 `backup_hermes_v3.sh`）
3. 確認 `no_agent: true`
4. 加入 `timeout_seconds: 600`（120s 不夠大檔備份）

**注意**：不能用 `hermes cron edit --script` 修復——那個命令對 no_agent jobs 本身就會把值寫入錯誤的欄位。

## 驗證命令

```bash
# 確認 jobs.json 中實際的值
python3 -c "
import json
jobs = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))['jobs']
for j in jobs:
    if j['id'] == '65f2dc3583d5':
        print('script:', repr(j.get('script')))
        print('prompt:', repr(j.get('prompt')))  # 要要是 null，不是 ''
        print('no_agent:', j.get('no_agent'))
        print('timeout_seconds:', j.get('timeout_seconds', 'not set'))
"

# 確認實際存在的 script 檔案
ls -la /home/hoonsoropenclaw/.hermes/scripts/backup_hermes*.sh
```

## 鑑別診斷流程

**If** error message 顯示的 script 路徑與 jobs.json 的 `script` 欄位不符
**Then** 檢查 `prompt` 欄位值——這幾乎一定是 `prompt` 殘留問題

| `prompt` 值 | Scheduler 行為 |
|------------|--------------|
| `null` | 讀 `script` 欄位 ✅ |
| `""`（空字串）| fallback 到 legacy path ❌ |
| 非空字串 | 讀 `prompt` 作為 script path（`hermes cron edit --script` bug）|

**If** `prompt` 是 `""`（空字串）
**Then** 立即改為 `null`

**If** error message 是 `#!/bin/bash` 開頭
**Then** `prompt` 殘留了完整的 script content，變成 path 被 Scheduler 當路徑讀

## 預防

每次建立或修改 no_agent cron job 後，手動驗證：
```bash
JOB_ID="<id>"
python3 -c "
import json
jobs = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))['jobs']
j = [x for x in jobs if x['id'] == '$JOB_ID'][0]
script = j.get('script')
prompt = j.get('prompt')
print('script:', repr(script))
print('prompt:', repr(prompt))  # 要是 null
"
ls -la ~/.hermes/scripts/$script
```

## 相關條目

- [[hermes-internal#cron jobs JSON fix: backup_hermes.sh vs backup_hermes_v3.sh script name mismatch (2026-06-08)]]
- [[hermes-internal#hermes cron edit --script 對 no_agent jobs 的 Bug]]
