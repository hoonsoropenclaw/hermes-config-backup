# syshealth_monitor.py

Linux 系統健康檢查 + 閾值告警腳本（stdlib-only）。

## 特色

- **5 個獨立檢查器** — CPU / RAM / Disk / Journal errors / Zombie processes
- **stdlib-only** — 不依賴 `psutil` / `requests` / `yaml` 等第三方（用 `subprocess` + regex）
- **可調閾值** — 預設合理, YAML 可覆寫
- **SNR 精簡輸出** — `--brief` 給 cron/Telegram, 預設寫詳細 JSON log
- **退出碼** — 0=OK / 1=warn / 2=crit（或 error）
- **不動紅區** — 不寫 `/etc`、不動 cron、不動 systemd

## 安裝

已經就緒，無需安裝：

```bash
ls ~/.hermes/scripts/syshealth/syshealth_monitor.py
```

## 使用

```bash
# 跑全部 5 個檢查 + 寫詳細 log 到 ~/.hermes/logs/syshealth/
python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py

# 一行輸出（Telegram / cron 友好）
python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py --brief

# 只跑單一檢查
python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py --check cpu
python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py --check journal

# 不寫 log, 只檢查（debug 用）
python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py --dry-run

# 顯示預設閾值（複製到 ~/.hermes/config/syshealth.yaml 改）
python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py --show-default-config
```

## 輸出格式

### `--brief`（cron / Telegram）

```
✅ syshealth OK — 5 checks pass, 0 skipped
```
```
❌ syshealth ALERT — 1 crit, 0 err, 0 warn | journal=236 err entries in last 1h (headroom=+216 vs crit)
```

### 預設（debug / 詳細 log）

```
== syshealth_monitor.py v1.0.0 — 2026-07-28T04:22:08 ==
  [OK  ] cpu      load1=0.42 (0.10/core, nproc=4)
  [OK  ] ram      RAM 7.6% (2420/31806MB), swap 6.3% (514/8191MB)
  [OK  ] disk     /=47.0%
  [CRIT] journal  236 err entries in last 1h (headroom=+216 vs crit)
  [OK  ] zombies  0 zombie process(es)

log: ~/.hermes/logs/syshealth/syshealth-20260727T202208Z.log
```

### JSON log（每檔完整資料）

每個 log 檔含 5 個檢查器的 `name / level / message / value / detail`，後續可寫 dashboard / 趨勢分析。

## 客製閾值

```bash
# 1. 看預設值
python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py --show-default-config

# 2. 複製範例
cp ~/.hermes/scripts/syshealth/syshealth.yaml.example \
   ~/.hermes/config/syshealth.yaml

# 3. 編輯 ~/.hermes/config/syshealth.yaml，改 warn/crit 即可
```

腳本會自動 merge：你只列了想覆寫的 key，其他仍用預設。

## 退出碼（cron 友善）

- `0` — 全綠
- `1` — 有 warn
- `2` — 有 crit / error（建議 cron 發 Telegram 通知）
- `130` — KeyboardInterrupt

## 接 cron job（手動設定）

⚠️ **本腳本不會自動註冊 cron job**（避免 fake authority 越權）。要排程請手動：

```bash
crontab -e
# 加一行：
*/15 * * * * python3 ~/.hermes/scripts/syshealth/syshealth_monitor.py --brief || echo "syshealth ALERT rc=$?" | /usr/bin/notify-send
```

## 設計決策

| 決策 | 原因 |
|------|------|
| stdlib-only | 對齊 Cycle 538 stdlib-first SOP；不污染 Python venv；可在任何容器即時跑 |
| `~/.hermes/scripts/syshealth/` | 永久路徑（避免 `/tmp` 被清），跟其他監控腳本同層 |
| `~/.hermes/logs/syshealth/` log dir | 跟 hermes 主 log 生態一致，不混在 `/var/log` |
| 預設閾值偏寬鬆 | 適合 4-core 24GB RAM 迷你機；高規格機可調更嚴 |
| 不自動註冊 cron | fake authority 不應該自動改排程；使用者手動控制 |
| YAML 解析不用 PyYAML | 犧牲複雜度換零依賴；只支援兩層 + 數字/bool |
| 退出碼 0/1/2 | cron 與 systemd service 通用；不靠 log 解析 |

## L3 教訓應用

來自 trial-and-error：

- 教訓 36（stdlib-first 生產工具）: 完全用 `urllib`/`subprocess`/`dataclass`
- 教訓 25（永久路徑）: 腳本放 `~/.hermes/scripts/syshealth/`，不放 `/tmp`
- 教訓 22（mkdir -p 順序）: 寫檔前先建目錄
- SNR 管理（hermes-internal §輸出噪聲比）: `--brief` 模式 + 詳細 log 分流
- 教訓 22（sub-agent 整合成本）: 單一檔案 + 單一概念，不分散多檔
- 紅區攔截: 不寫 `/etc`、不動 `cron/jobs.json`、不碰 systemd unit