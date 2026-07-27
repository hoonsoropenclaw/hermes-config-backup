# syswatch — Linux 系統日誌與資源監控

自動監控 CPU / Memory / Disk / Load / I/O wait 等資源,以及 `auth.log` (SSH 暴力破解)、`syslog` (OOM / segfault / 磁碟 I/O error / kernel panic),超過閾值時輸出 alerts。

## 設計目標

- **stdlib-only** — 無第三方依賴 (Python 3.10+)
- **可離線執行** — 不依賴 systemd / Prometheus / 任何 daemon
- **多輸出通道** — console + JSON report (每日輪替) + JSONL log + syslog (logger)
- **自動 fallback** — `/var/log/syswatch` 寫不進去 → 改用 `~/.local/share/syswatch/log`
- **冷卻機制** — `urgent_flag` 存在期間不重複發 CRITICAL 警報

## 檔案

| 檔案 | 用途 |
|------|------|
| `syswatch.py` | 主腳本 (CLI + library) |
| `config.json` | 預設配置 (含所有閾值) |
| `test_syswatch.py` | Smoke test (7 個 threshold 場景) |
| `syswatch-run.sh` | Cron / systemd timer 用的 wrapper |

## 使用方式

```bash
# 單次掃描、印人類可讀 + 寫 report
python3 syswatch.py

# 印 JSON only (給其他工具 ingest)
python3 syswatch.py --json-only

# 持續 loop,每 60 秒一次
python3 syswatch.py --loop 60

# 不要寫檔,只 console
python3 syswatch.py --dry-run

# 用自訂 config
python3 syswatch.py --config /etc/syswatch/myconfig.json

# 寫一份預設 config 到指定路徑
python3 syswatch.py --init-config /home/hoonsoropenclaw/.hermes/scripts/syswatch/prod.json

# 跑 smoke test
python3 test_syswatch.py
```

## 監控項目

### 資源
- CPU busy % (1 秒 dual-sample,讀 `/proc/stat`)
- I/O wait %
- Load average (1/5/15) per CPU
- Memory used % (MemAvailable)
- Swap used %
- Disk used % — 監控 `monitored_mounts` + 自動走訪 `/proc/mounts` 排除 tmpfs / proc / sysfs 等
- 0 byte 偽檔案系統 (`securityfs`, `efivarfs`, `bpf`) 自動排除

### 日誌
- `auth.log` (15 min / 60 min 滑動窗口)
  - `Failed password` — Top 5 攻擊 IP + Top 5 被嘗試 username
  - `Invalid user` — Top 5 IP + username
  - `Accepted` / session opened / closed
- `syslog` (60 min 滑動窗口)
  - `OOM kill` — ≥3 次 → `EMERGENCY`, ≥1 次 → `CRITICAL`
  - `segfault` — WARN ≥3 / CRITICAL ≥10
  - I/O error / EXT4-fs error — WARN ≥2 / CRITICAL ≥5
  - Kernel panic — 任何一次 = `EMERGENCY`

## Severity 模型

| 等級 | 觸發條件 | 動作 |
|------|---------|------|
| INFO | 預設 | 寫 report, console 印 ℹ️ |
| WARN | 閾值 warn 級別觸發 | 同上 + `logger -t syswatch` |
| CRITICAL | 閾值 critical 級別觸發 | 同上 + 寫 urgent flag (冷卻期內不重複) |
| EMERGENCY | OOM ≥3 / kernel panic | 同上 |

Exit code: `0` = OK, `1` = CRITICAL/EMERGENCY, `2` = 腳本錯誤。

## Cron 整合

```cron
# /etc/cron.d/syswatch
*/5 * * * * hoonsoropenclaw /home/hoonsoropenclaw/.hermes/scripts/syswatch/syswatch-run.sh
```

或 Hermes cron (`~/.hermes/cron/jobs.json`):

```json
{
  "name": "syswatch-every-5min",
  "schedule": "*/5 * * * *",
  "command": "bash /home/hoonsoropenclaw/.hermes/scripts/syswatch/syswatch-run.sh",
  "enabled": true
}
```

## 輸出位置

| 通道 | 預設路徑 |
|------|---------|
| Console | stdout (受 `--console` 控制) |
| JSON report | `/var/log/syswatch/syswatch-report-YYYYMMDD-HHMMSS.json` (或 fallback) |
| JSONL log | `/var/log/syswatch/syswatch.log` (追加) |
| Urgent flag | `/var/run/syswatch.urgent` (或 `/tmp/syswatch.urgent` fallback) |
| Wrapper log | `~/.local/share/syswatch/log/wrapper.log` (append) |

## 閾值覆寫範例

把 `/etc/syswatch/config.json` 蓋掉 warn / critical 級別,適合針對特定硬體調校:

```json
{
  "thresholds": {
    "cpu_percent_warn": 70,
    "cpu_percent_critical": 90,
    "memory_percent_warn": 75,
    "memory_percent_critical": 90,
    "disk_percent_warn": 70,
    "disk_percent_critical": 85
  }
}
```

## 設計取捨

1. **為何 stdlib-only** — N100 環境不想裝 `requests` / `psutil` 等第三方依賴,降低部署摩擦
2. **為何每日 JSON report + JSONL log** — JSONL 易 grep / 餵 jq;每日 report 適合做 trend 分析
3. **為何雙輸出目錄** — 給 root 跑的 cron 用 `/var/log/syswatch`;給 user cron 自動 fallback 到 home
4. **為何 cooldown 而非 rate-limit** — 同樣 CRITICAL 連發 10 次 vs 1 次通知差很多;cooldown 預設 10 分鐘
5. **為何 dmesg 不直接讀** — 預設 `/dev/kmsg` 需要 root;`dmesg` 指令需要 `CONFIG_SECURITY_DMESG_RESTRICT` 沒設。改用 syslog 內的 kernel line 較可靠

## 已知限制

- 不會自動 rotate JSONL `syswatch.log` (只 rotate 每日 JSON report)
- OOM 判斷仰賴 syslog 內的 "Killed process" 字串;若 distro 用 cgroup v2 OOM killer (輸出在 cgroup 通知),會漏掉
- 一次掃描 log 檔整個讀進記憶體,在 5GB+ 大 log 環境會 OOM。建議先用 `logrotate` 控管日誌大小
- `dmesg --since` 沒實際呼叫 (預設走 syslog 內 kernel line);若使用者堅持需要 dmesg,可加 `--use-dmesg` flag