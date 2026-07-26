"""
logscan/scanner.py — 系統日誌掃描
=================================

支援兩種來源：
1. 檔案：/var/log/syslog, /var/log/kern.log, /var/log/auth.log
   - 增量讀取（用 state 裡的 offset）
   - 檔案 rotate 時（檔案大小縮回去）自動重置 offset
2. systemd journal（journalctl）：
   - 抓最近 1 小時的 ERR / WARNING 等級訊息
   - 透過 subprocess 執行（不引入 systemd python binding）

回傳結構：list[LogHit]
"""
from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from config import thresholds as T


@dataclass
class LogHit:
    source: str           # "syslog" / "kern.log" / "journalctl"
    line: str             # 原始一行
    level: str            # "warn" | "crit"
    matched_pattern: str  # 哪個 regex 命中
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# 檔案掃描
# ---------------------------------------------------------------------------
def scan_log_file(path: str, offset: int) -> tuple[list[LogHit], int]:
    """讀取 [offset, end] 範圍內的新行。

    處理：
    - 檔案不存在 → 跳過（不報錯）
    - 檔案 rotate（目前 size < offset）→ 重置 offset 為 0
    - 沒有新行 → 回空 list, offset 不變

    Return: (hits, new_offset)
    """
    p = Path(path)
    if not p.exists():
        return [], offset

    try:
        size = p.stat().st_size
        if size < offset:
            # 檔案比上次小（rotate 了）→ 從頭開始
            offset = 0

        with p.open("rb") as f:
            f.seek(offset)
            raw = f.read()
        new_offset = offset + len(raw)

        # 解碼（用 errors='replace' 避免二進位污染）
        text = raw.decode("utf-8", errors="replace")
        if not text:
            return [], new_offset

        hits = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            hits.extend(_classify_line(line, source=p.name))

        return hits, new_offset

    except PermissionError:
        # 沒讀權限（/var/log 群組 syslog）→ 跳過但不報錯
        return [], offset
    except OSError:
        return [], offset


def _classify_line(line: str, source: str) -> list[LogHit]:
    """單行分類：先看 ignore → crit → warn → 無。"""
    # 1. 忽略
    for pat in T.LOG_IGNORE_PATTERNS:
        if re.search(pat, line):
            return []

    hits: list[LogHit] = []

    # 2. crit 先（優先）
    for pat in T.CRITICAL_LOG_PATTERNS:
        if re.search(pat, line):
            hits.append(LogHit(
                source=source,
                line=line,
                level="crit",
                matched_pattern=pat,
            ))
            return hits   # 一行只記一次 crit

    # 3. warn
    for pat in T.WARN_LOG_PATTERNS:
        if re.search(pat, line):
            hits.append(LogHit(
                source=source,
                line=line,
                level="warn",
                matched_pattern=pat,
            ))
            return hits

    return []


# ---------------------------------------------------------------------------
# journalctl 掃描
# ---------------------------------------------------------------------------
def scan_journal(since: str = T.JOURNALCTL_TIME_RANGE,
                 boot: str = T.JOURNALCTL_BOOT_FLAG) -> list[LogHit]:
    """執行 journalctl -b --since='1 hour ago' -p err..alert --no-pager

    物件分類：err/crit/alert/emerg → crit，warning → warn
    """
    hits: list[LogHit] = []
    try:
        proc = subprocess.run(
            ["journalctl", boot, f"--since={since}",
             "-p", "err..alert", "--no-pager", "-q"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []  # 沒 journalctl 或逾時 → 跳過
    except Exception:
        return []

    if proc.returncode != 0 or not proc.stdout:
        return []

    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        classified = _classify_line(line, source="journalctl")
        hits.extend(classified)

    return hits


# ---------------------------------------------------------------------------
# 主進入點
# ---------------------------------------------------------------------------
def scan_all(state) -> tuple[list[LogHit], dict[str, int]]:
    """掃描所有日誌，回傳 (聚合 hits, 新的 offset map)。

    state: state.State 實例
    Return: (list[LogHit], dict[str, int])  ← 第二個元素傳給 state.set_offset()
    """
    all_hits: list[LogHit] = []
    new_offsets: dict[str, int] = {}

    for log_path in T.LOG_FILES_TO_MONITOR:
        offset = state.get_offset(log_path)
        hits, new_offset = scan_log_file(log_path, offset)
        all_hits.extend(hits)
        new_offsets[log_path] = new_offset

    # journalctl（不持久化 offset，每次都掃「最近 1 小時」）
    all_hits.extend(scan_journal())

    return all_hits, new_offsets
