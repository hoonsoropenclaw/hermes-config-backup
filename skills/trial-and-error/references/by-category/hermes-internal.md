# Hermes 內部架構 / 工具鏈 / SOP 試誤條目

> 集中收容：cron / gateway / profile / config / AGENTS.md / keyword 觸發 / 備份等內部工具鏈的 L2 試誤條目
> 寫法：問題情境 + 失敗原因 + 正確做法 + 驗證命令

---

## 2026-06-11（最新）

### jobs.json 欄位污染：no_agent cron job 的 `prompt` 欄位被錯誤寫入 script+args

**症狀**：
- `v4-backup-tier2-daily` (20d2173d8c97) 報 `Script not found: /home/hoonsoropenclaw/.hermes/scripts/hermes-backup-v4.sh --tier2 --upload-tier2`
- `hermes-config-backup-daily` (65f2dc3583d5) 報 `Script timed out after 3600s: /home/hoonsoropenclaw/.hermes/scripts/backup_hermes_v3.sh`（明明 jobs.json script 是 `hermes-backup-v4.sh`）

**根因**：`hermes cron edit --script <id> 'script.sh --args'` 對 `no_agent=True` 的 script-only jobs 有 bug：
- `--script` 參數值會被寫入 `prompt` 欄位，而非 `script` 欄位
- Scheduler 的 `_run_job_script()` 對 no_agent jobs 讀取 `prompt` 作為 script path
- 結果：Scheduler 把 `prompt` 的「`hermes-backup-v4.sh --tier2 --upload-tier2`」整個字串當成 script path，嘗試執行 `/home/.../hermes-backup-v4.sh --tier2 --upload-tier2`（含空白+args），檔案不存在

**觸發時機**：
- `hermes cron edit --script <id> '...'` 對 `no_agent: true` 的 job
- `hermes cron create --script 'script.sh --args'` 對 no_agent job（不給 `--no-agent` flag 時預設）

**正確做法**：

1. **不要用 `hermes cron edit --script`** 對 no_agent jobs 帶 args — 有 bug
2. 改用**直接編輯 jobs.json**：
   - 將 `prompt` 設為 `null`（不是空字串 `""`）
   - 將 `script` 設為單純檔名（如 `hermes-backup-v4.sh`，不含路徑和 args）
   - 若需要傳 args，寫一個 thin wrapper script 或讓 script 內部讀環境變數

```bash
# 修復 jobs.json 的正確方式
python3 - <<'EOF'
import json
with open('/home/hoonsoropenclaw/.hermes/cron/jobs.json') as f:
    d = json.load(f)
for j in d['jobs']:
    if j['id'] == '<target-id>':
        # 將 prompt 設為 null（不是 ""）
        j['prompt'] = None
        # script 只留檔名，不要含 args
        j['script'] = 'hermes-backup-v4.sh'
        j['no_agent'] = True
        print(f"Fixed {j['name']}: prompt={j['prompt']}, script={j['script']}")
with open('/home/hoonsoropenclaw/.hermes/cron/jobs.json', 'w') as f:
    json.dump(d, f, indent=2)
EOF
```

**驗證命令**：
```bash
# 確認 prompt 是 null（不是空字串）
python3 -c "import json; d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json')); [print(j['id'], j['name'], 'prompt=', repr(j.get('prompt')), 'ctx=', repr(j.get('context_from'))) for j in d['jobs'] if j.get('no_agent')]"
# prompt 應為 None，不是 "" 或任何其他值

# 確認 script 只含檔名不含路徑
python3 -c "import json; d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json')); [print(j['name'], 'script=', j.get('script')) for j in d['jobs'] if j.get('script')]"
# script 應為 "hermes-backup-v4.sh" 不是 "/home/.../hermes-backup-v4.sh"
```

**If→Then**：
- **If** cron job 報 `Script not found: /home/.../script.sh --args` **Then** 檢查 jobs.json 的 `prompt` 欄位是否被汙染，設為 `null`
- **If** `hermes cron edit --script` 的 last_error 顯示 script path 含 args **Then** 不要繼續用 edit，手動改 jobs.json
- **If** 要傳 args 給 no_agent cron script **Then** 在 v4.sh 內部做 `if [[ "$1" == "--tier2" ]]` 條件分支，不要透過 cron 的 prompt 傳

---

### jobs.json `context_from: []` 空陣列可能導致 Scheduler 行為異常

**症狀**：
- `v4-backup-tier1-daily` (108ce8cabdfc) 的 `context_from` 是 `[]`（空陣列），不是 `null`
- `v4-backup-tier2-daily` (20d2173d8c97) 修復前也是 `context_from: []`

**根因**：某些 `hermes cron create/edit` 操作會把空陣列 `[]` 寫入 `context_from`，而不是預期的 `null`

**正確做法**：
```python
# jobs.json 內 context_from 必須是 null，不是 []
if j.get('context_from') == []:
    j['context_from'] = None
```

**驗證**：
```bash
python3 -c "import json; d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json')); [print(j['name'], 'context_from=', repr(j.get('context_from'))) for j in d['jobs']]"
# 所有 no_agent script jobs 的 context_from 應為 None
```

---

### coverage check 新增覆蓋檔案時需同步改兩處

**症狀**：
- `hermes-backup-coverage-check.sh` 報 `ROOT_SINGLE_FILES` 漏掉 `.skills_prompt_snapshot.json`
- 但 v4.sh 內已加 `".skills_prompt_snapshot.json"` 到 `ROOT_SINGLE_FILES` array

**根因**：coverage check 比對「本機根目錄檔案」vs「v4.sh ROOT_SINGLE_FILES array」，但 INVENTORY.md（單一真實來源）沒同步更新，導致 coverage check 一直報 warning

**正確做法**（兩處都要改）：
1. `hermes-backup-v4.sh` 的 `ROOT_SINGLE_FILES` array 加新檔
2. `~/.hermes/docs/INVENTORY.md` 的「同步的單檔」表格加新檔

```bash
# 驗證 coverage check 是否 PASS
bash ~/.hermes/scripts/hermes-backup-coverage-check.sh
# 預期：✅ PASS  備份覆蓋率完整
```

**If→Then**：
- **If** coverage check 報 `ROOT_SINGLE_FILES` 漏掉新檔 **Then** 同時改 v4.sh ROOT_SINGLE_FILES + INVENTORY.md 同步清單，缺一不可
- **If** 要新增 v4 同步的根目錄單檔 **Then** 這兩處都改 + 記錄進 INVENTORY.md 變更記錄表

---

## 2026-06-10（之前，完整條目見 SKILL.md 上方滾動區）