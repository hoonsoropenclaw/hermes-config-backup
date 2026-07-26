"""
alert.py — 多頻道告警
====================

支援：
1. console — 印到 stderr
2. log — 寫到 logs/alert.log
3. telegram — 透過 Bot API（如果有 env var）

降級設計：telegram 沒 token 就跳過，不報錯。
冷卻：state.fingerprint + cooldown 控制。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from config import thresholds as T
from state.state import State

# ============================================================================
# 顏色（terminal 才有效）
# ============================================================================
class _C:
    RESET = "\033[0m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def _c(text: str, color: str) -> str:
    if not sys.stderr.isatty():
        return text
    return f"{color}{text}{_C.RESET}"


# ============================================================================
# 格式化
# ============================================================================
def _fmt_finding(f: dict[str, Any]) -> str:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lvl = f["level"].upper()
    icon = {"CRIT": "🚨", "WARN": "⚠️ "}.get(lvl, "·")
    return (
        f"{icon} [{lvl}] {ts}  {f['message']}\n"
        f"   key={f['key']}  value={f['value']}  threshold={f['threshold']}"
    )


def _fmt_loghit(h: dict[str, Any]) -> str:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lvl = h["level"].upper()
    icon = {"CRIT": "🚨", "WARN": "⚠️ "}.get(lvl, "·")
    line = h["line"]
    if len(line) > 220:
        line = line[:217] + "..."
    return (
        f"{icon} [{lvl}] {ts}  src={h['source']}\n"
        f"   {line}"
    )


# ============================================================================
# 頻道實作
# ============================================================================
def _send_console(items: list[dict[str, Any]], channel: str) -> None:
    """印到 stderr（不用 stdout——避免被 pipe 吃掉）。"""
    for f in items:
        if f["kind"] == "finding":
            line = _fmt_finding(f)
        else:
            line = _fmt_loghit(f)
        # CRIT 用紅、WARN 用黃
        color = _C.RED if f["level"] == "crit" else _C.YELLOW
        print(_c(line, color), file=sys.stderr)


def _send_logfile(items: list[dict[str, Any]], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        for it in items:
            if it["kind"] == "finding":
                f.write(_fmt_finding(it) + "\n")
            else:
                f.write(_fmt_loghit(it) + "\n")
            f.write("\n")


def _send_telegram(items: list[dict[str, Any]], bot_token: str, chat_id: str) -> bool:
    """發送到 Telegram。回傳是否成功。"""
    # 訊息上限 4096，組一條就夠
    lines = [f"🔔 *sysmonitor alert* — {len(items)} item(s)"]
    for it in items[:30]:  # 最多 30 則
        if it["kind"] == "finding":
            lines.append(f"• *{it['level'].upper()}* {it['message']}")
        else:
            truncated = it["line"][:200]
            lines.append(f"• *{it['level'].upper()}* `{it['source']}`: {truncated}")
    body = "\n".join(lines)

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": body,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return bool(data.get("ok"))
    except Exception as e:
        # 任何錯都不丟出去（避免監控自己掛掉）
        print(_c(f"[alert] telegram send failed: {e}", _C.DIM), file=sys.stderr)
        return False


# ============================================================================
# 決定是否送出（cooldown + 每日上限 + 連續 crit 升級）
# ============================================================================
def _should_send(fingerprint: str, state: State, today: str) -> bool:
    if state.today_count(today) >= T.MAX_ALERTS_PER_DAY:
        return False
    if not state.can_send(fingerprint, T.ALERT_COOLDOWN_SECONDS):
        return False
    return True


# ============================================================================
# 公開 API
# ============================================================================
def dispatch(findings: list, log_hits: list, state: State) -> dict[str, int]:
    """送出 findings + log_hits。

    Return: dict 統計 {channel: count}
    """
    # 統一格式
    items: list[dict[str, Any]] = []
    for f in findings:
        items.append({
            "kind": "finding",
            "key": f.key,
            "level": f.level,
            "value": f.value,
            "threshold": f.threshold,
            "message": f.message,
        })
    for h in log_hits:
        items.append({
            "kind": "loghit",
            "level": h.level,
            "source": h.source,
            "line": h.line,
        })

    if not items:
        return {ch: 0 for ch in T.ALERT_CHANNELS}

    # 過濾：cooldown + 每日上限
    today = dt.date.today().isoformat()
    to_send: list[dict[str, Any]] = []
    for it in items:
        if it["kind"] == "finding":
            fp = f"{it['key']}:{it['level']}:{dt.datetime.now().strftime('%Y-%m-%d:%H')}"
        else:
            # log hit 用 source + 第一句話的 hash 當 fingerprint
            line_sig = (it["line"][:80]).strip()
            fp = f"log:{it['source']}:{it['level']}:{line_sig}"
        if _should_send(fp, state, today):
            to_send.append(it)
            state.mark_sent(fp)
            state.incr_today(today)

    if not to_send:
        return {ch: 0 for ch in T.ALERT_CHANNELS}

    stats: dict[str, int] = {}

    # 1. console
    if "console" in T.ALERT_CHANNELS:
        _send_console(to_send, "console")
        stats["console"] = len(to_send)

    # 2. log
    log_path = Path(__file__).resolve().parent / "logs" / "alert.log"
    if "log" in T.ALERT_CHANNELS:
        _send_logfile(to_send, log_path)
        stats["log"] = len(to_send)

    # 3. telegram（有 token 才送）
    if "telegram" in T.ALERT_CHANNELS:
        bot = os.environ.get(T.ENV_TELEGRAM_BOT_TOKEN)
        chat = os.environ.get(T.ENV_TELEGRAM_CHAT_ID)
        if bot and chat:
            if _send_telegram(to_send, bot, chat):
                stats["telegram"] = len(to_send)
        else:
            stats["telegram"] = 0

    return stats


def print_summary(findings: list, log_hits: list, stats: dict[str, int],
                  self_check: dict[str, Any], state: State) -> None:
    """每次循環結尾的健全報告（即使沒 alarm 也印）。"""
    print(_c("\n──── sysmonitor cycle summary ────", _C.CYAN + _C.BOLD), file=sys.stderr)
    sc = self_check
    print(
        f"  CPU={sc['cpu_percent']:.1f}%  "
        f"MEM={sc['mem']['percent']:.1f}%({sc['mem']['used_gb']}G/{sc['mem']['total_gb']}G)  "
        f"LOAD={sc['load_avg_1']:.2f}  "
        f"ZOMBIE={sc['zombie_count']}  "
        f"PROC={sc['process_count']}",
        file=sys.stderr,
    )
    for d in sc["disks"]:
        flag = "  " if d["percent"] < T.DISK_PERCENT_WARN else (_c("⚠", _C.YELLOW) if d["percent"] < T.DISK_PERCENT_CRIT else _c("🚨", _C.RED))
        print(f"  {flag} disk {d['mountpoint']:<20} {d['percent']:.1f}% ({d['used_gb']}G/{d['total_gb']}G, {d['fstype']})", file=sys.stderr)

    n_find = len(findings)
    n_log = len(log_hits)
    print(f"  findings: {n_find}  log_hits: {n_log}  dispatched: {stats}", file=sys.stderr)
    today = dt.date.today().isoformat()
    print(f"  state: alerts_today={state.today_count(today)} (cooldown={T.ALERT_COOLDOWN_SECONDS}s)", file=sys.stderr)
    print(_c("─────────────────────────────────", _C.CYAN), file=sys.stderr)
