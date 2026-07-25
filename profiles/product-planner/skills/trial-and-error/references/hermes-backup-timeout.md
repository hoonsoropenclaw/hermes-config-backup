# hermes-config-backup-daily timeout fix

## 發現時間
2026-06-08

## 問題描述
`hermes-config-backup-daily` cron job 使用 `backup_hermes.sh`（v2），該腳本產出兩個大 tar.gz（PUBLIC + FULL），加上 rclone crypt 上傳 694 MB，120 秒 timeout 不夠用，導致 Script timed out。

## 修復
切換 cron job 的 script 從 `backup_hermes.sh`（v2）改為 `backup_hermes_v3.sh`（v3）：

**v2 問題**：產 694 MB tar.gz → rclone crypt 上傳超慢（191 KiB/s、需 58 分鐘）
**v3 解法**：用 rclone sync 直接同步目錄架構，不打包tar.gz，timeout 內可完成

jobs.json 修改：
```json
{
  "id": "65f2dc3583d5",
  "name": "hermes-config-backup-daily",
  "script": "backup_hermes_v3.sh",  // 從 backup_hermes.sh 改為 backup_hermes_v3.sh
  "no_agent": true
}
```

## 驗證
確認 jobs.json 中 backup script 已改為 v3：
```bash
python3 -c "import json; d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json')); print([j['script'] for j in d['jobs'] if j['id']=='65f2dc3583d5'])"
# ['backup_hermes_v3.sh']
```

## 預防
設計 cron script 時，假設 timeout 為 120s。設計架構時避免單一 script 產生/上傳超大檔案（> 100 MB），改用 rclone sync 增量同步。