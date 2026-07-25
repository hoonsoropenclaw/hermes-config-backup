# Cron Fix Cross-Verification SOP

## 問題由來
2026-06-09 cycle 發現：`hermes-config-backup-daily` timeout，trial-and-error 已記錄「timeout_seconds 600→3600」，但 jobs.json 查詢顯示仍是 600。文件說了要改，但根本沒改。

## 根本原因
Phase 1.5 只做「狀態檢查」（cron list 看 error/not error），沒有交叉驗證「trial-and-error 記錄的修復方案 vs jobs.json 實際值」。導致「修復記錄了 = 修復完成了」的錯誤假設。

## 正確的 Phase 1.5 交叉驗證流程

```
當 Phase 1.5 發現 cron job error 時：
1. 讀 last_error，了解錯誤類型
2. 搜尋 trial-and-error / MEMORY.md 是否有該問題的修復記錄
3. 若有修復記錄 → 立即用指令驗證 jobs.json 的實際值是否已改
   - 例：grep "timeout_seconds" ~/.hermes/cron/jobs.json
   - 若值不是記錄中的建議值 → 本次 cycle 必須完成修復
4. 若無修復記錄 → 識別為新缺口，走 Phase 2-3
```

## 驗證指令庫

```bash
# 查 jobs.json 的 timeout_seconds（任何 job）
python3 -c "
import json
with open('/home/hoonsoropenclaw/.hermes/cron/jobs.json') as f:
    jobs = json.load(f)['jobs']
for j in jobs:
    ts = j.get('timeout_seconds', 'NOT SET')
    if ts != 'NOT SET' and int(ts) < 3600:
        print(f\"LOW TIMEOUT: {j['name']} (id: {j['id']}) → {ts}s\")
"

# 查特定 job 的所有關鍵欄位
jq '.jobs[] | select(.id=="65f2dc3583d5")' ~/.hermes/cron/jobs.json

# 驗證 rclone crypt remote 可達性（快速檢查）
rclone lsl crypt_hermes:hermes-backup/v3/current/ --config ~/documents/rclone.conf | head -3
```

## jobs.json 常見需要交叉驗證的欄位

| 欄位 | 正常值 | 警告值 |
|------|--------|--------|
| timeout_seconds | 3600+ | < 600 |
| script | 檔名（不含路徑） | 含路徑 `/home/...` |
| prompt | null（no_agent） | 非 null 字串 |
| no_agent | true | false |
| enabled | true | false |

## 2026-06-09 緊急修復清單

- [ ] `hermes-config-backup-daily` (id: 65f2dc3583d5): timeout_seconds 600→3600
- [ ] 驗證：`python3 -c "import json; j=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json')); print([x for x in j['jobs'] if x['id']=='65f2dc3583d5'][0].get('timeout_seconds'))"`