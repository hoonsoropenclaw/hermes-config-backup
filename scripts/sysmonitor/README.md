# sysmonitor — Linux 系統監控腳本

> 2026-07-27 建立的 v1.0 監控腳本，部署在 N100 (hoonsoropenclaw@100.88.38.80) 主機。

## 監控什麼

- **資源**：CPU、RAM、磁碟（所有真實 mountpoint，自動過濾 snap/docker 唯讀層）、load avg、zombie process
- **日誌**：增量掃描 `/var/log/{syslog, kern.log, auth.log}`，加上 `journalctl -p err..alert --since='1 hour ago'`
- **關鍵字**：OOM / segfault / kernel panic / systemd exit-code / authentication failure / disk full / 服務重啟循環

## 怎麼通知

- `console` (stderr) — 預設
- `log` — 寫到 `logs/alert.log`
- `telegram` — **選用**，需要 `SYSMONITOR_TG_BOT_TOKEN` + `SYSMONITOR_TG_CHAT_ID` 環境變數

降級設計：沒 token 不會掛掉。

## 抑制規則（避免 alert storm）

- 同樣 fingerprint 冷卻 15 分鐘
- 同一天最多 20 條
- 連續 3 個 crit 周期 → 訊息加 `[ESCALATED ×N]` 標記

## 檔案位置

```
/home/hoonsoropenclaw/.hermes/scripts/sysmonitor/
├── sysmonitor.py              ← 主入口
├── metrics.py                 ← 資源採樣
├── alert.py                   ← 多頻道通知
├── logscan/                   ← 日誌掃描子套件
│   ├── __init__.py
│   └── scanner.py
├── state/state.py             ← 持久化（offsets + fingerprints）
├── config/thresholds.py       ← 全部閾值常數
├── reports/                   ← 每次跑一份 JSON
├── logs/alert.log             ← 已發送的 alert
└── state/state.json           ← 持久化狀態
```

## 使用

```bash
# 跑一次（cron 模式）
python3 /home/hoonsoropenclaw/.hermes/scripts/sysmonitor/sysmonitor.py --once

# 測試用 — 不發 alert
python3 .../sysmonitor.py --dry-run --once

# 開發用 — 60 秒循環
python3 .../sysmonitor.py --loop 60
```

## 部署（cron）

```cron
# 每分鐘跑一次
* * * * * /usr/bin/python3 /home/hoonsoropenclaw/.hermes/scripts/sysmonitor/sysmonitor.py --once >> /home/hoonsoropenclaw/.hermes/scripts/sysmonitor/logs/cron.log 2>&1
```

## 部署（systemd timer）

可選；用 timer 可以看上次跑了多久（cron 不會）。

```bash
sudo cp deployment/systemd/sysmonitor.service /etc/systemd/system/
sudo cp deployment/systemd/sysmonitor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sysmonitor.timer
sudo systemctl list-timers sysmonitor.timer
```

## 啟用 Telegram

```bash
export SYSMONITOR_TG_BOT_TOKEN='123456:ABC-DEF...'
export SYSMONITOR_TG_CHAT_ID='-1001234567890'

# 然後在 config/thresholds.py 把 ALERT_CHANNELS 加入 'telegram'
```

## 故障排查

- 沒報警？  檢查 `state/state.json` 裡 `alerts_sent_today` 有沒有達 20、清 cooldown 也清 `alert_fingerprints`
- 重複告警？  fingerprint 規則是 `key:level:YYYY-MM-DD:HH` — 一小時內同 key+level 抑制
- 看不到真實 mountpoint？  `psutil.disk_partitions()` 預設只回真實分割區；如果 `lsblk` 有但這沒看到，加 `all=True`
- 沒讀 `/var/log/syslog` 權限？  把使用者加入 `adm` 群組：`sudo usermod -aG adm $USER`

## 設計原則

1. **零硬體依賴** — 標準庫 + psutil。沒有第三方雲端 SDK、不引入 GitHub API、不發 webhook。
2. **降級優先** — 任何 sub-process / 通知失敗都不能讓監控自己掛掉。
3. **持久化增量** — 不重複告警、不吃掉 rotate 後的新行。
4. **可離線閱讀** — `reports/YYYYMMDD_HHMMSS.json` 是 human-readable、有自檢 snapshot、能 grep。
5. **零 mock** — 報告「捕獲 N 條」就是「真的從 syslog 讀到 N 條」，沒有合成數據。
