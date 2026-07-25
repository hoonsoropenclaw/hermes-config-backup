# School Bulletin System Watchdog — D3 Exit Record (cycle 061)

## 發現經過

- **cycle 060 (2026-06-18)**：設計了 `/tmp/school-bulletin-watchdog.sh`，但**從未部署至 crontab**
- **cycle 061 (2026-06-20)**：Phase 1.5 發現 `crontab -l | grep school-bulletin` 返回空，確認 script 缺失

## 根因

cycle 060 識別了 gap 並建立了 script 檔案，但：
1. 部署指令（`crontab -l | ... | crontab -`）從未執行
2. Phase 1.5 只檢查「script 存在否」，沒有同時確認 crontab entry

## 教訓

**If→Then**：建立 watchdog script 後，**必須立即確認 crontab entry 存在**，兩步一起跑。

## 2026-06-20 D3 Exit 內容

**Script**：`/tmp/school-bulletin-watchdog.sh`（mtime 2026-06-20）
```bash
#!/bin/bash
SCHOOL_BULLETIN_URL="https://school-bulletin.vercel.app"
CHECK_PATH=""   # 根路徑已足夠，/api/health 返回 404
# 重試邏輯：第一次失敗後等 5 秒再試，第二次也失敗才 log
```

**部署+驗證**：
```bash
chmod +x /tmp/school-bulletin-watchdog.sh
(crontab -l 2>/dev/null | grep -v "school-bulletin-watchdog"; \
  echo "* * * * * /tmp/school-bulletin-watchdog.sh >> /tmp/school-bulletin-watchdog.log 2>&1") | crontab -
# 驗證
crontab -l | grep school-bulletin
bash /tmp/school-bulletin-watchdog.sh && echo "EXIT:0"
curl -s -o /dev/null -w "%{http_code}" https://school-bulletin.vercel.app
```

## 驗證結果

- crontab entry：✅ 存在
- watchdog exit 0：✅
- production URL HTTP 200：✅
