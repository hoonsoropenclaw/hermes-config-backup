# Camofox Watchdog 部署完整 SOP（2026-06-06 實測）

## 問題背景

Camofox 的瀏覽器引擎（camoufox process）可能單獨崩潰，而 Docker container 和 API server 繼續運行。`browserConnected: false` 但 `docker ps` 顯示 container 還在跑。這種斷線是**靜默的**——所有自動化任務失敗但沒有錯誤訊息。

`camofox-watchdog.sh` 腳本存在於 `~/.hermes/skills/browser/camofox/scripts/`，但：
1. 從未部署到 crontab
2. skill 目錄是 `drwx------` (0700)，root cron 無法進入執行

## 完整部署步驟

### Step 1：準備自包含腳本（解決 0700 權限問題）

skill 目錄 `~/.hermes/skills/browser/camofox/scripts/` 是 0700，root cron 無法執行。將腳本複製到 `/tmp/`：

```bash
# 複製並確保可執行
cp ~/.hermes/skills/browser/camofox/scripts/camofox-watchdog.sh /tmp/camofox-watchdog.sh
chmod +x /tmp/camofox-watchdog.sh

# 重寫為自包含版本（不依賴 hermes 路徑）
cat > /tmp/camofox-watchdog.sh << 'WATCHDOG'
#!/bin/bash
HEALTH=$(curl -s --max-time 5 http://localhost:9377/health 2>/dev/null)
if [ -z "$HEALTH" ]; then
  echo "[$(date)] API unreachable, restarting camofox-browser" >> /tmp/camofox-watchdog.log
  docker restart camofox-browser >> /tmp/camofox-watchdog.log 2>&1
  exit
fi

if echo "$HEALTH" | grep -q '"browserConnected":false'; then
  echo "[$(date)] browserConnected=false, restarting camofox-browser" >> /tmp/camofox-watchdog.log
  docker restart camofox-browser >> /tmp/camofox-watchdog.log 2>&1
fi
WATCHDOG
chmod +x /tmp/camofox-watchdog.sh
```

### Step 2：驗證腳本可執行

```bash
/bin/bash /tmp/camofox-watchdog.sh && echo "exit: $?"
# 預期：exit: 0（瀏覽器健康時無需重啟）
cat /tmp/camofox-watchdog.log  # 檢查日誌
```

### Step 3：部署到 crontab（每分鐘檢查）

```bash
(crontab -l 2>/dev/null | grep -v camofox-watchdog; \
  echo "* * * * * /tmp/camofox-watchdog.sh >> /tmp/camofox-watchdog.log 2>&1") | crontab -
```

### Step 4：驗證 crontab 部署

```bash
crontab -l | grep camofox
# 預期：* * * * * /tmp/camofox-watchdog.sh >> /tmp/camofox-watchdog.log 2>&1
```

### Step 5：驗證瀏覽器引擎連線

```bash
curl -s http://localhost:9377/health | python3 -m json.tool
# 預期：{"browserConnected": true, "browserRunning": true, "ok": true}
```

## 技術細節

### 為什麼 skill 目錄是 0700？
`~/.hermes/` 目錄整體是 `drwx------` (700)，保護所有赫米斯設定檔、secrets、memory。副作用是 root cron 無法進入 `.hermes` 子目錄。

### 為什麼複製到 /tmp/？
`/tmp/` 是 `1777`（world-writable + sticky），root 和任何用戶都可以執行。但日誌也寫到 `/tmp/camofox-watchdog.log`，所以整個 watchdog 體系都在 `/tmp/` 自包含。

### 為什麼不用其他路徑？
- `/usr/local/bin/` → 需要 sudo 權限才能寫入
- `/home/hoonsoropenclaw/` → root 無法讀取（home 是 0700）
- `/tmp/` → 唯一不需要特殊權限且 root 可執行的位置

### 驗證方式選擇
- `curl -s http://localhost:9377/health` — 最快（5 秒超時）
- `docker ps | grep camofox` — 確認 container 活著，但不區分 API server 和瀏覽器引擎
- `docker restart camofox-browser` — 重啟後需等 10 秒讓瀏覽器引擎啟動

## 日誌位置

- Watchdog 執行日誌：`/tmp/camofox-watchdog.log`
- Docker container logs：`docker logs camofox-browser`

## 恢復後驗證清單

1. ✅ `curl -s http://localhost:9377/health` → `browserConnected: true`
2. ✅ `crontab -l | grep camofox` → cron entry 存在
3. ✅ `/bin/bash /tmp/camofox-watchdog.sh` → exit 0（瀏覽器健康，無需重啟）
4. ✅ 等 2 分鐘後再看 `/tmp/camofox-watchdog.log` 確認 cron 有在執行

## 已知限制

- watchdog 每分鐘執行一次，最大斷線時間為 60 秒（cron 分鐘精度）
- 如果 Docker daemon 也掛了（罕見），watchdog 無法重啟 container
- 如果 N100 重啟，需要重新部署 cron（watchdog 不會自動重跑）