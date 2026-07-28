# logwatcher

Linux 系統日誌與資源監控腳本（純 bash + python3，零外部依賴）。

## 功能

| 檢查 | 觸發 | 預設閾值 |
|------|------|---------|
| `disk` | mount 容量超限 | 80/90/95% |
| `inode` | inode 用量超限 | 70/85/93% |
| `memory` | (Total - Available)/Total | 75/88/95% |
| `swap` | swap 使用率 | 30/60/85% |
| `load` | loadavg1 / nproc | 1.5x/2.5x/4.0x |
| `logs` | kernel/auth/service pattern 命中 | 1/10/3 (10min 內) |

## 使用

```bash
./logwatcher.sh                      # 完整一次
./logwatcher.sh --self-test          # 內建單元測試
./logwatcher.sh --check disk         # 跑單一 check
./logwatcher.sh --dry-run            # 不寫檔不打 webhook
./logwatcher.sh --quiet              # 抑制 stderr
./logwatcher.sh --config /path.yaml  # 用自訂 config
./logwatcher.sh --report             # 只生報告
./logwatcher.sh --help               # 說明
```

Exit codes：`0` clean / `2` 有 alert / `1` 致命錯誤 / 其他 參數錯。

## 排程

- cron：`*/5 * * * * /home/hoonsoropenclaw/.hermes/scripts/logwatcher/logwatcher.sh`
- systemd：見 `systemd/logwatcher.{service,timer}`

## 通知

| 通道 | 啟用方式 |
|------|---------|
| alerts.log | 永遠啟用，固定寫入 `reports/alerts.log` |
| stderr | 預設啟用，cron/systemd 會接到 |
| Webhook | `config.yaml` 設 `notification.webhook_url` |
| Telegram | 設環境變數 `TG_BOT_TOKEN` + `TG_CHAT_ID` |

冷卻機制：同 `(check, target, level)` 在 `cooldown_minutes` 內只發一次（預設 30 分鐘），避免 log bomb。

## 檔案佈局

```
logwatcher/
├── logwatcher.sh         # 主腳本
├── config.yaml           # 配置檔
├── run.sh                # 整合測試
├── systemd/
│   ├── logwatcher.service
│   └── logwatcher.timer
├── cron/
│   └── logwatcher.cron
├── reports/              # 每次跑的快照 + alerts.log
├── state/                # 冷卻 stamp
└── locks/                # 並發鎖
```

## 故障排除

```bash
# 1. self-test
./logwatcher.sh --self-test

# 2. 確認 yaml 解析
./logwatcher.sh --check disk --dry-run

# 3. 清 stale lock
rm -f locks/watcher.lock

# 4. 確認 journalctl 讀得到
journalctl --since "-10 min" --no-pager | head
```

## 設計原則

1. **零外部依賴** — bash + python3 stdlib + 標準 linux util
2. **YAML > 環境變數** — 結構化、註解、範例齊
3. **冷卻避免 log bomb** — 同 alert 30 分鐘內只發一次
4. **鎖定避免重疊** — 10 分鐘 stale lock
5. **Self-test 不需 root** — 任何時候都能驗證
6. **graceful degradation** — journalctl 失敗 → syslog fallback

## 變更

- v1.0 (2026-07-28)：初版 — 6 個 check，3 級警告，4 種通知
