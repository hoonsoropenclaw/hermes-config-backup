# linux_ops_monitor.py

Linux 系統日誌與資源監控腳本。

## 一句話用途
掃描 systemd journal + 系統資源（CPU/RAM/Disk/Load/IO）+ systemd unit 健康，
超過閾值時輸出告警到本地 alert log 與 stdout，退出碼反映 severity。

## 安裝與使用

### 1) 單次跑
```bash
python3 ~/.hermes/scripts/linux_ops_monitor.py --once
# 退出碼：0=ok, 1=warn, 2=critical, 3=腳本錯誤
```

### 2) 乾跑（不寫 state/alert log）
```bash
python3 ~/.hermes/scripts/linux_ops_monitor.py --once --dry-run
```

### 3) JSON 輸出（給外部整合）
```bash
python3 ~/.hermes/scripts/linux_ops_monitor.py --json
```

### 4) 背景常駐（推薦 daemon 模式）
```bash
python3 ~/.hermes/scripts/linux_ops_monitor.py --daemon --interval 300
```

### 5) cron 模式（推薦用 wrapper）
```cron
*/5 * * * * /home/hoonsoropenclaw/.hermes/scripts/run-linux-ops-monitor.sh
```

### 6) 驗證腳本可發 alert（測試環境用）
```bash
python3 ~/.hermes/scripts/linux_ops_monitor.py --once --test
# 強制觸發所有 alert 路徑（閾值歸 0、cooldown=0）
```

## 退出碼對照
| code | 意義      | cron 動作                |
|------|----------|-------------------------|
| 0    | OK       | 忽略                    |
| 1    | WARN     | mail 通知（可選）        |
| 2    | CRITICAL | 強烈通知 / onfailure=    |
| 3    | 腳本錯誤  | 自己 debug（看 log）     |

## 檔案佈局
- `~/.hermes/scripts/linux_ops_monitor.py` — 主腳本（單檔、無外部依賴）
- `~/.hermes/scripts/run-linux-ops-monitor.sh` — cron 用的薄殼 wrapper
- `~/.hermes/logs/linux_ops_monitor_alerts.log` — 告警事件 log（JSONL append）
- `~/.hermes/logs/linux_ops_monitor_cron.log` — cron 跑的 stdout/stderr 副本
- `~/.hermes/state/linux_ops_monitor_state.json` — 去重 state（cooldown tracker）

## 設定檔（可選）
預設 config 已內建。給自訂：
```json
{
  "thresholds": {
    "cpu_pct": 85.0,
    "mem_pct": 85.0,
    "disk_pct": 80.0,
    "load_per_cpu": 1.5
  },
  "journal": {
    "since": "30m",
    "priority": "warning",
    "max_err_count": 30
  },
  "units": {
    "critical": ["ssh.service", "cron.service"],
    "watched": ["rsyslog.service"]
  }
}
```
然後：
```bash
python3 ~/.hermes/scripts/linux_ops_monitor.py --once --config /path/to/cfg.json
```

## 設計原則
1. **無第三方依賴**：只用 stdlib（`subprocess`/`re`/`json`/...）
2. **fail-soft**：任何 sub-check 失敗不讓整個腳本崩潰
3. **去重**：同個 alert key 在 cooldown 內只發一次（避免 journalctl 每次掃到都洗版）
4. **退出碼語意化**：0/1/2/3 對應 severity，可直接接 cron / systemd `OnFailure=`
5. **不外呼**：腳本只寫本地檔 + stdout；不發 email / webhook（讓 Hermes / 外部去讀 alert log 再決定怎麼通知）

## 已知限制
- journal 在容器 / 無 journald 環境會回 OK + 一行解釋（不算嚴重）
- CPU 短取樣（2s）易誤判，預設不升 critical；只有 iowait 高才 critical
- 沒做趨勢分析（要 history 才知道「越來越高」），目前只看當下瞬間值
