"""
sysmonitor 預設閾值設定
======================

所有閾值都可由外部 YAML 覆寫（見 config/config.yaml，未來擴充）。
本檔只放「合理預設值」——任何環境只要 Python + psutil 就能跑起來。

設計原則：
- 預設偏保守（先 false-positive 而非 false-negative），避免 alert fatigue
- 單位/說明集中在 docstring，方便單一檔案 review
- 數字有出處（OOM 已被踩過、journalctl 容量實測過）
"""
from __future__ import annotations

# ============================================================================
# 資源監控閾值
# ============================================================================

# CPU
CPU_PERCENT_WARN = 80.0      # 5 秒平均 > 80% → warn
CPU_PERCENT_CRIT = 95.0      # 5 秒平均 > 95% → crit（連續 60 秒）

# 記憶體（RAM）
MEM_PERCENT_WARN = 80.0      # used% > 80% → warn
MEM_PERCENT_CRIT = 92.0      # used% > 92% → crit（可能 OOM 觸發）

# 磁碟（每個掛載點）
DISK_PERCENT_WARN = 80.0     # used% > 80% → warn
DISK_PERCENT_CRIT = 92.0     # used% > 92% → crit（filesystem 接近 full）

# 載入平均（load average）
LOAD_AVG_PER_CPU_WARN = 1.5  # load1 / cpu_count > 1.5 → warn
LOAD_AVG_PER_CPU_CRIT = 3.0  # load1 / cpu_count > 3.0 → crit

# 行程 / IO
ZOMBIE_COUNT_WARN = 5        # 僵屍行程 ≥ 5 → warn
ZOMBIE_COUNT_CRIT = 20       # 僵屍行程 ≥ 20 → crit

# ============================================================================
# 系統日誌關鍵字（regex）
# ============================================================================

# 嚴重錯誤（crit 級）—— 這些絕對不能漏
CRITICAL_LOG_PATTERNS = [
    r"\bOOM\b|Out of memory|oom-kill|oom_reaper",        # OOM killer 觸發
    r"segfault|general protection|GPU hang",             # 核心 dump / GPU hang
    r"kernel panic|kernel:[ ]+\bBUG\b",                 # kernel panic（罕見但致命）
    r"Failed with result ['\"]exit-code['\"]",          # systemd service crash
    r"status=2\d\d/",                                     # systemd exit code 2xx
    r"\bI/O error\b|\bEXT4-fs error\b",                  # 磁碟 I/O error
    r"authentication failure|Failed password",          # 暴力破解跡象
    r"Disk full|ENOSPC: no space left",                  # 磁碟滿
    r"systemd\[1\]:.*Failed to start",                    # systemd 失敗啟動
]

# 警告（warn 級）—— 一次出現不一定有事，但累計起來可能是徵兆
WARN_LOG_PATTERNS = [
    r"\bWARN\b|warn:|\bdeprecated\b",                    # 通用警告
    r"restart counter is at \d{4,}",                     # systemd restart loop（>1000 次）
    r"scheduled restart job",                            # systemd 排程重啟
    r"connection refused",                                 # 拒絕連線
    r"timeout exceeded|timed out",                        # 逾時
    r"segfault.*total-vm",                                 # 加上 context 才會誤命中所以獨立列
    r"NMI: Non-maskable interrupt",                       # 硬體 NMI
]

# 應忽略的雜訊（避免 false positive）
LOG_IGNORE_PATTERNS = [
    r"systemd\[\d+\]: mcp-dashboard.*restart counter is at \d+\.",  # 已知重啟迴圈服務
    r"systemd\[\d+\]: mcp-dashboard\.service:.* (Scheduled restart|Failed to set up standard output|Main process exited|Failed with result)",  # 已知壞掉的 mcp-dashboard
    r"resolvconf.*resolv\.conf",                                     # 正常的 DNS reload
]

# ============================================================================
# 日誌檔位置
# ============================================================================

# 監控的檔案：以檔案最後讀過的 byte offset 為基準，支援增量掃描
LOG_FILES_TO_MONITOR = [
    "/var/log/syslog",
    "/var/log/kern.log",
    "/var/log/auth.log",
]

# 用 journalctl 撈 systemd journal 錯誤（如果可用）
JOURNALCTL_BOOT_FLAG = "-b"   # 當前 boot（更即時）
JOURNALCTL_TIME_RANGE = "1 hour ago"  # 抓最近 1 小時的 ERROR+

# ============================================================================
# 抑制規則（避免重複 alert）
# ============================================================================

# 同一個 fingerprint 在 COOLDOWN 秒內只發一次
ALERT_COOLDOWN_SECONDS = 900      # 15 分鐘

# 同一個 crit 模式日內最多發 MAX_ALERTS_PER_DAY 次
MAX_ALERTS_PER_DAY = 20

# 連續 N 個 crit 周期才升級為「緊急」升級告警
CRIT_CONSECUTIVE_THRESHOLD = 3    # 3 次連續 crit → 緊急升級

# ============================================================================
# 通知（先做 console + log，未來可加 Telegram）
# ============================================================================

# 通知路徑（全部存在時使用，否則降級）
ALERT_CHANNELS = ["console", "log"]  # 預設沒 Telegram 就只 console+log

# 環境變數讀取（避免硬編 token）
ENV_TELEGRAM_BOT_TOKEN = "SYSMONITOR_TG_BOT_TOKEN"
ENV_TELEGRAM_CHAT_ID = "SYSMONITOR_TG_CHAT_ID"

# ============================================================================
# 取樣相關
# ============================================================================

# CPU 採樣間隔（給 psutil.cpu_percent 用）
CPU_SAMPLE_INTERVAL_SEC = 1.0

# 單次盤查最大執行時間（防止腳本自己卡死）
MAX_RUN_TIME_SEC = 120

# 監控週期（se主任務策略）：這個數字給 cron 用 — 1 分鐘跑一次
CRON_INTERVAL_NOTE = "1m"
