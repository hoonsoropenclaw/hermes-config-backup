# Camofox Watchdog Cron Deployment (2026-06-09)

## 問題
`camofox-watchdog.sh` 存在於 `~/.hermes/skills/browser/camofox/scripts/` 但從未進 crontab。

原因：
- Skill 目錄權限 `0700`（`drwx------`）
- Root cron 無法讀取 hoonsoropenclaw 用戶的 0700 skill 目錄

## 修復步驟

```bash
# 1. 複製到 /tmp/（用戶可讀的路徑）
cp ~/.hermes/skills/browser/camofox/scripts/camofox-watchdog.sh /tmp/camofox-watchdog.sh

# 2. 確保可執行
chmod 755 /tmp/camofox-watchdog.sh

# 3. 部署到 crontab
(crontab -l 2>/dev/null | grep -v camofox-watchdog; echo "* * * * * /tmp/camofox-watchdog.sh >> /tmp/camofox-watchdog.log 2>&1") | crontab -

# 4. 驗證
crontab -l | grep camofox
```

## 驗證命令

```bash
# 確認 crontab entry
crontab -l | grep camofox

# 確認 script 可執行
ls -la /tmp/camofox-watchdog.sh

# 確認 watchdog 正在運行
ps aux | grep camofox-watchdog | grep -v grep

# 確認 camofox 狀態
curl -s --max-time 3 http://localhost:9377/health
```

## If→Then 規則

**If** 需要部署一個來自 skill 目錄的 watchdog/service script
**Then** 複製到 `/tmp/`（用戶可讀），chmod 755，再加入 crontab
**Then** 不要直接用 skill 目錄內的路徑（root cron 無法讀取 0700 目錄）

**If** script 權限是 0700 且 crontab 不會執行
**Then** 這是 skill 目錄權限問題，複製到 /tmp/ 繞過