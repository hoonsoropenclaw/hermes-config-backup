#!/usr/bin/env python3
"""
weather_bot.py — Telegram 機器人 (N100 Linux/headless-friendly)

功能
----
1. 接收 Telegram 文字訊息 → 解析為城市名 → 呼叫 OpenWeatherMap API → 回傳格式化結果
2. /start、/help、/health 內建指令
3. 結構化 JSONL 日誌（INFO/WARN/ERROR/DEBUG）
4. 預設安全:無 token → 啟動時拒絕；--check 模式只驗證設定不通報；--mock 模式:離線測試
5. 失敗分類:網路 / 5xx / 4xx / 解析失敗,使用者面向友善訊息 + 結構化錯誤日誌
6. Reconnect-friendly:PTB 22 自動處理 polling recovery

設計原則
--------
- DN:善用原生/現成方案   → python-telegram-bot 22.6(已存在 hermes venv)+ 標準 urllib + dataclasses
- DRY:預設安全 + 結構化日誌 + 自我驗證(從上次 task 學到)
- ROOT CAUSE:失敗時不只回 "失敗了",用 message 對應到具體補救動作
- 輸入清洗:去除控制字元、超長截斷、空訊息忽略、Unicode normalize

環境變數
--------
TELEGRAM_BOT_TOKEN     必填,BotFather 給的 token
OPENWEATHER_API_KEY    必填,https://openweathermap.org/api 申請免費 key
OWM_UNITS              選填,metric|imperial|standard,預設 metric
OWM_LANG               選填,zh_tw|zh_cn|en,預設 zh_tw
LOG_FILE               選填,JSONL 日誌路徑,預設 ~/weather-bot.jsonl
HTTP_TIMEOUT           選填,API 逾時秒數,預設 10

CLI
---
weather_bot.py              → 正式啟動 long-polling
weather_bot.py --check      → 驗證設定、log 路徑、網路可達性、weather API key 合法性,然後退出
weather_bot.py --mock       → 啟動 mock 模式,模擬天氣查詢(不呼叫 Telegram/OWM,純本機)
weather_bot.py --version
weather_bot.py --help

驗證
----
python3 -m py_compile weather_bot.py
python3 weather_bot.py --check --mock
python3 weather_bot.py --mock
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 第三方:python-telegram-bot 22.6(已裝在 hermes venv)
try:
    from telegram import Update
    from telegram.constants import ParseMode
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError as e:  # pragma: no cover
    TELEGRAM_AVAILABLE = False
    _TELEGRAM_IMPORT_ERR = repr(e)
# 保險:變數一定存在(若 try 成功也定義空字串,避免測試 mock 時 NameError)
if '_TELEGRAM_IMPORT_ERR' not in dir():
    _TELEGRAM_IMPORT_ERR = ""

# --------------- 常數 ---------------

VERSION = "1.0.0"
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_UNITS = "metric"
DEFAULT_LANG = "zh_tw"
DEFAULT_TIMEOUT = 10
MAX_CITY_LEN = 80
MAX_INPUT_LEN = 200
LOG_FIELD_ORDER = ["ts", "level", "event", "message", "ctx"]

# --------------- 結構化日誌 ---------------

class JsonLineLogger:
    """JSONL 日誌:每行一個事件,欄位順序固定,具備 stdout 跟 file 雙輸出。"""

    def __init__(self, log_path: Path | None, *, also_stderr: bool = True):
        self.log_path = log_path
        self.also_stderr = also_stderr
        self._fh = None
        if log_path is not None:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                self._fh = log_path.open("a", encoding="utf-8")
            except OSError as e:
                sys.stderr.write(f"[warn] failed to open log file {log_path}: {e}\n")
                self._fh = None

    def _emit(self, level: str, event: str, message: str, ctx: dict[str, Any] | None = None) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": level,
            "event": event,
            "message": message,
            "ctx": ctx or {},
        }
        line = json.dumps(record, ensure_ascii=False, sort_keys=False)
        if self._fh is not None:
            try:
                self._fh.write(line + "\n")
                self._fh.flush()
            except OSError:  # pragma: no cover
                pass
        if self.also_stderr:
            sys.stderr.write(line + "\n")

    def info(self, event: str, message: str, ctx: dict | None = None) -> None:
        self._emit("INFO", event, message, ctx)

    def warn(self, event: str, message: str, ctx: dict | None = None) -> None:
        self._emit("WARN", event, message, ctx)

    def error(self, event: str, message: str, ctx: dict | None = None) -> None:
        self._emit("ERROR", event, message, ctx)

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None


# --------------- 設定 ---------------

@dataclass(frozen=True)
class Settings:
    token: str = ""
    owm_key: str = ""
    units: str = DEFAULT_UNITS
    lang: str = DEFAULT_LANG
    timeout: float = DEFAULT_TIMEOUT
    log_path: Path | None = None
    mock: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        log_path_str = os.environ.get("LOG_FILE", "").strip()
        log_path = Path(log_path_str).expanduser() if log_path_str else None
        return cls(
            token=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
            owm_key=os.environ.get("OPENWEATHER_API_KEY", "").strip(),
            units=os.environ.get("OWM_UNITS", DEFAULT_UNITS).strip() or DEFAULT_UNITS,
            lang=os.environ.get("OWM_LANG", DEFAULT_LANG).strip() or DEFAULT_LANG,
            timeout=float(os.environ.get("HTTP_TIMEOUT", str(DEFAULT_TIMEOUT))),
            log_path=log_path,
        )


# --------------- 天氣 API ---------------

@dataclass
class WeatherResult:
    ok: bool
    city: str
    data: dict[str, Any] = field(default_factory=dict)
    error_kind: str = ""        # network | timeout | 4xx | 5xx | parse | empty
    error_detail: str = ""
    http_status: int = 0

    def to_user_text(self) -> str:
        """格式化成給 Telegram 看的訊息(plain text,避免 Markdown 衝突)。"""
        if not self.ok:
            return self._format_error()
        return self._format_weather()

    def _format_weather(self) -> str:
        d = self.data
        name = d.get("name") or self.city
        sys_ = d.get("sys", {}) or {}
        country = sys_.get("country", "")
        weather_list = d.get("weather", []) or []
        main = d.get("main", {}) or {}
        wind = d.get("wind", {}) or {}
        clouds = d.get("clouds", {}) or {}
        rain = d.get("rain", {}) or {}
        snow = d.get("snow", {}) or {}

        desc = weather_list[0]["description"] if weather_list else "（無描述）"
        icon = weather_list[0].get("icon", "") if weather_list else ""
        icon_emoji = _icon_to_emoji(icon)

        temp = main.get("temp")
        feels = main.get("feels_like")
        tmin = main.get("temp_min")
        tmax = main.get("temp_max")
        humidity = main.get("humidity")
        pressure = main.get("pressure")
        unit_symbol = _unit_symbol(self.units_here)

        lines = [
            f"{icon_emoji} {name}, {country}".strip(", "),
            f"目前天氣:{desc}",
        ]
        if temp is not None:
            lines.append(f"溫度:{temp}{unit_symbol}  (體感 {feels}{unit_symbol})")
        if tmin is not None and tmax is not None:
            lines.append(f"今日範圍:{tmin}{unit_symbol} ~ {tmax}{unit_symbol}")
        if humidity is not None:
            lines.append(f"濕度:{humidity}%")
        if pressure is not None:
            lines.append(f"氣壓:{pressure} hPa")
        if wind.get("speed") is not None:
            ws = wind["speed"]
            if self.units_here == "imperial":
                lines.append(f"風速:{ws} mph")
            elif self.units_here == "standard":
                lines.append(f"風速:{ws} m/s")
            else:
                lines.append(f"風速:{ws} m/s")
        if clouds.get("all") is not None:
            lines.append(f"雲量:{clouds['all']}%")
        if rain.get("1h"):
            lines.append(f"近 1 小時降雨:{rain['1h']} mm")
        if rain.get("3h"):
            lines.append(f"近 3 小時降雨:{rain['3h']} mm")
        if snow.get("1h"):
            lines.append(f"近 1 小時降雪:{snow['1h']} mm")
        if sys_.get("sunrise") and sys_.get("sunset"):
            lines.append(f"日出:{_fmt_ts(sys_['sunrise'])}  日落:{_fmt_ts(sys_['sunset'])}")
        return "\n".join(lines)

    def _format_error(self) -> str:
        """失敗訊息:說明 root cause + 補救建議,符合 Architect 原則。"""
        e = self.error_kind
        city = self.city or "（未提供）"
        if e == "empty":
            return f"請告訴我城市名稱,例如「台北市」「Tokyo」「New York」\n我收到的是空的。"
        if e == "invalid":
            return f"抱歉,我看不懂 '{city}' 是地名。請用中文或英文城市名試試。"
        if e == "network":
            return "目前連不上天氣服務,請檢查網路後再試。"
        if e == "timeout":
            return "天氣服務回應太慢(timeout),請稍後再試。"
        if e == "4xx":
            if self.http_status == 401:
                return "天氣 API key 驗證失敗(401),請聯絡管理員檢查 OPENWEATHER_API_KEY。"
            if self.http_status == 404:
                return f"找不到 '{city}' 的天氣資料,請換個寫法(例如「台中」改「Taichung」)。"
            if self.http_status == 429:
                return "天氣 API 達到速率限制(429),請稍後再試。"
            return f"天氣 API 拒絕請求(HTTP {self.http_status})。"
        if e == "5xx":
            return "天氣服務暫時不可用(5xx),請稍後再試。"
        if e == "parse":
            return "天氣服務回傳的資料格式異常,無法解析,請稍後再試。"
        return f"查詢失敗({e})。請稍後再試。"

    # 為了 WeatherService 補上 units 屬性
    units_here: str = DEFAULT_UNITS


class WeatherService:
    """OpenWeatherMap client,失敗分類為 root cause。"""

    def __init__(self, api_key: str, *, units: str, lang: str, timeout: float,
                 logger: JsonLineLogger, mock: bool = False):
        self.api_key = api_key
        self.units = units
        self.lang = lang
        self.timeout = timeout
        self.logger = logger
        self.mock = mock

    async def query(self, city: str) -> WeatherResult:
        city = (city or "").strip()
        if not city:
            return WeatherResult(ok=False, city=city, error_kind="empty")
        if not _is_probably_city(city):
            return WeatherResult(ok=False, city=city, error_kind="invalid")

        if self.mock:
            return self._mock_query(city)

        params = {
            "q": city,
            "appid": self.api_key,
            "units": self.units,
            "lang": self.lang,
        }
        url = f"{OWM_BASE_URL}?{urllib.parse.urlencode(params)}"
        started = time.monotonic()
        try:
            loop = asyncio.get_running_loop()
            data, status = await loop.run_in_executor(None, self._fetch, url)
        except urllib.error.HTTPError as e:
            elapsed = time.monotonic() - started
            body_snip = ""
            try:
                body = e.read()
                body_snip = body[:200].decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover
                pass
            kind = "5xx" if e.code >= 500 else "4xx"
            self.logger.error(
                "weather_api_http_error",
                f"OWM HTTP {e.code}",
                {"city": city, "status": e.code, "elapsed_ms": int(elapsed * 1000), "body": body_snip},
            )
            return WeatherResult(
                ok=False, city=city, error_kind=kind,
                error_detail=f"HTTP {e.code}", http_status=e.code,
            )
        except urllib.error.URLError as e:
            elapsed = time.monotonic() - started
            reason = getattr(e, "reason", None)
            is_timeout = isinstance(reason, (socket.timeout, TimeoutError))
            kind = "timeout" if is_timeout else "network"
            self.logger.error(
                "weather_api_url_error",
                f"OWM URL error ({kind})",
                {"city": city, "elapsed_ms": int(elapsed * 1000),
                 "reason": repr(reason)},
            )
            return WeatherResult(
                ok=False, city=city, error_kind=kind,
                error_detail=repr(reason),
            )
        except (TimeoutError, socket.timeout):
            elapsed = time.monotonic() - started
            self.logger.error(
                "weather_api_timeout",
                "OWM timeout",
                {"city": city, "elapsed_ms": int(elapsed * 1000)},
            )
            return WeatherResult(ok=False, city=city, error_kind="timeout")
        except Exception as e:  # pragma: no cover
            self.logger.error(
                "weather_api_unexpected",
                f"OWM unexpected: {e!r}",
                {"city": city},
            )
            return WeatherResult(
                ok=False, city=city, error_kind="network",
                error_detail=repr(e),
            )

        elapsed = time.monotonic() - started
        if status != 200:
            kind = "5xx" if status >= 500 else "4xx"
            self.logger.warn(
                "weather_api_non_200",
                f"OWM non-200 {status}",
                {"city": city, "status": status, "elapsed_ms": int(elapsed * 1000), "body": str(data)[:200]},
            )
            return WeatherResult(
                ok=False, city=city, error_kind=kind,
                error_detail=str(data)[:200], http_status=status,
            )

        if not isinstance(data, dict):
            self.logger.error(
                "weather_api_parse",
                "OWM returned non-dict",
                {"city": city, "type": type(data).__name__},
            )
            return WeatherResult(ok=False, city=city, error_kind="parse")

        self.logger.info(
            "weather_api_ok",
            "weather fetched",
            {"city": city, "status": status, "elapsed_ms": int(elapsed * 1000),
             "resolved": data.get("name"), "country": (data.get("sys") or {}).get("country")},
        )
        result = WeatherResult(ok=True, city=city, data=data)
        result.units_here = self.units
        return result

    def _fetch(self, url: str) -> tuple[Any, int]:
        """同步 HTTP fetch executor。回傳 (parsed_json, http_status)。"""
        req = urllib.request.Request(url, headers={"User-Agent": f"weather-bot/{VERSION}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read()
            status = resp.status
        try:
            return json.loads(raw.decode("utf-8")), status
        except (ValueError, UnicodeDecodeError):
            return raw[:500], status

    def _mock_query(self, city: str) -> WeatherResult:
        """Mock 模式:用 mock JSON fixture,本地 timeout 0.01s。"""
        fixture = {
            "name": city.title() if city.isascii() else city,
            "sys": {"country": "TW", "sunrise": 1700000000, "sunset": 1700040000},
            "weather": [{"id": 800, "main": "Clear", "description": "晴", "icon": "01d"}],
            "main": {
                "temp": 27.3, "feels_like": 29.1,
                "temp_min": 25.0, "temp_max": 30.0,
                "humidity": 65, "pressure": 1013,
            },
            "wind": {"speed": 3.2, "deg": 180},
            "clouds": {"all": 10},
        }
        result = WeatherResult(ok=True, city=city, data=fixture)
        result.units_here = self.units
        return result


# --------------- 工具 ---------------

_EMOJI_BY_ICON_PREFIX = {
    "01": "☀️", "02": "🌤️", "03": "🪨", "04": "☁️",
    "09": "🌧️", "10": "🌦️", "11": "⛈️", "13": "❄️", "50": "🌫️",
}


def _icon_to_emoji(icon: str) -> str:
    if not icon:
        return "🌡️"
    return _EMOJI_BY_ICON_PREFIX.get(icon[:2], "🌡️")


def _unit_symbol(units: str) -> str:
    return {"metric": "°C", "imperial": "°F", "standard": "K"}.get(units, "°C")


def _fmt_ts(epoch: int) -> str:
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%H:%M UTC")
    except (OSError, ValueError, OverflowError):
        return "?"


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE_RE = re.compile(r"\s+")
_BOT_TOKEN_FMT = re.compile(r"^[0-9]{6,12}:[A-Za-z0-9_-]{30,}$")




def sanitize_input(text: str, max_len: int = MAX_INPUT_LEN) -> str:
    """移除控制字元、collapse 空白、strip、超長截斷、Unicode normalize。"""
    if not text:
        return ""
    text = _CONTROL_RE.sub("", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


def _is_probably_city(text: str) -> bool:
    """啟發式:含字母/中日韓文字、長度 2-80、城市允許的標點。"""
    if not text or len(text) < 2 or len(text) > MAX_CITY_LEN:
        return False
    if not re.search(r"[A-Za-z\u4e00-\u9fff\u3040-\u30ff]", text):
        return False
    # 拒絕明顯是網址/指令/郵件的輸入
    if re.search(r"https?://|@|\.com|\.io|\.org|/", text):
        return False
    return True


def looks_like_bot_token(s: str) -> bool:
    return bool(s) and bool(_BOT_TOKEN_FMT.match(s))


# --------------- 檢查模式 ---------------

@dataclass
class CheckReport:
    env_token_ok: bool
    env_owm_ok: bool
    log_path: str
    log_writable: bool
    hermes_venv_python: str
    telegram_module: str
    network_ok: bool
    owm_api_ok: bool
    notes: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = ["weather_bot --check 報告", "=" * 40]
        lines.append(f"hermes venv python    : {self.hermes_venv_python}")
        lines.append(f"python-telegram-bot   : {self.telegram_module}")
        lines.append(f"TELEGRAM_BOT_TOKEN    : {'OK' if self.env_token_ok else 'MISSING'}")
        lines.append(f"OPENWEATHER_API_KEY   : {'OK' if self.env_owm_ok else 'MISSING'}")
        lines.append(f"LOG_FILE              : {self.log_path or '(default)'}")
        lines.append(f"LOG writable          : {'OK' if self.log_writable else 'NO'}")
        lines.append(f"Internet reachability : {'OK' if self.network_ok else 'NO'}")
        lines.append(f"OWM API key validity  : {'OK' if self.owm_api_ok else 'NO'}")
        if self.notes:
            lines.append("")
            lines.append("Notes:")
            for n in self.notes:
                lines.append(f"  - {n}")
        return "\n".join(lines)


def run_check(settings: Settings, logger: JsonLineLogger) -> CheckReport:
    notes: list[str] = []
    hermes_py = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python3")
    py_exists = os.path.exists(hermes_py)
    tg_module = "MISSING"
    if py_exists:
        import subprocess
        r = subprocess.run(
            [hermes_py, "-c", "import telegram; print(telegram.__version__)"],
            capture_output=True, text=True, timeout=10,
        )
        tg_module = r.stdout.strip() if r.returncode == 0 else f"ERROR: {r.stderr.strip()}"
    if not py_exists:
        notes.append("hermes venv python 不存在 — 請確認 ~/.hermes/hermes-agent/venv/")

    log_writable = True
    log_path = str(settings.log_path) if settings.log_path else ""
    if settings.log_path:
        try:
            settings.log_path.parent.mkdir(parents=True, exist_ok=True)
            with settings.log_path.open("a", encoding="utf-8") as fh:
                fh.write("")
            log_writable = True
        except OSError as e:
            log_writable = False
            notes.append(f"log 寫入失敗: {e}")

    network_ok = False
    try:
        socket.create_connection(("api.openweathermap.org", 443), timeout=5).close()
        network_ok = True
    except OSError as e:
        notes.append(f"無法連到 api.openweathermap.org: {e}")

    owm_api_ok = False
    if settings.owm_key and network_ok:
        try:
            url = f"{OWM_BASE_URL}?q=London&appid={urllib.parse.quote(settings.owm_key)}"
            req = urllib.request.Request(url, headers={"User-Agent": f"weather-bot/{VERSION}"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                status = resp.status
            owm_api_ok = (status == 200)
            if not owm_api_ok:
                notes.append(f"OWM 回 {status} (key 可能無效)")
        except urllib.error.HTTPError as e:
            notes.append(f"OWM HTTP {e.code} — key 可能無效")
        except Exception as e:
            notes.append(f"OWM 連線失敗: {e!r}")

    report = CheckReport(
        env_token_ok=bool(settings.token and looks_like_bot_token(settings.token)),
        env_owm_ok=bool(settings.owm_key),
        log_path=log_path,
        log_writable=log_writable,
        hermes_venv_python=hermes_py if py_exists else "MISSING",
        telegram_module=tg_module,
        network_ok=network_ok,
        owm_api_ok=owm_api_ok,
        notes=notes,
    )
    logger.info("check_complete", "check finished", report.__dict__)
    return report


# --------------- Bot 主流程 ---------------

def build_application(settings: Settings, weather: WeatherService, logger: JsonLineLogger):
    """組裝 PTB v22 Application。"""
    if not TELEGRAM_AVAILABLE:
        raise RuntimeError(f"python-telegram-bot 不可用: {_TELEGRAM_IMPORT_ERR}")
    app = Application.builder().token(settings.token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else None
        logger.info("cmd_start", "user sent /start", {"chat_id": chat_id})
        text = (
            "👋 我是 Weather Bot\n"
            "直接傳城市名給我,例如:\n"
            "  台北市\n  Tokyo\n  New York\n"
            "指令:\n"
            "  /help  說明\n  /health  自我檢查\n"
        )
        await update.message.reply_text(text)

    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else None
        logger.info("cmd_help", "user sent /help", {"chat_id": chat_id})
        text = (
            "Weather Bot 使用說明\n"
            "輸入地名(中文/英文) → 回傳目前天氣\n"
            "範例:台中 / Taichung / 渋谷区 / Singapore\n\n"
            "問題回報請聯絡管理員。"
        )
        await update.message.reply_text(text)

    async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else None
        logger.info("cmd_health", "user sent /health", {"chat_id": chat_id})
        rep = run_check(settings, logger)
        await update.message.reply_text(rep.to_text())

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        chat_id = update.effective_chat.id if update.effective_chat else None
        raw = sanitize_input(update.message.text)
        if not raw:
            return
        logger.info("user_query", "user sent city query",
                    {"chat_id": chat_id, "raw_len": len(raw)})
        result = await weather.query(raw)
        await update.message.reply_text(result.to_user_text())
        logger.info(
            "user_query_done",
            "weather reply sent",
            {"chat_id": chat_id, "ok": result.ok, "kind": result.error_kind or "ok"},
        )

    async def on_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        chat_id = update.effective_chat.id if update.effective_chat else None
        if update.message.text and not update.message.text.startswith("/"):
            return  # 已被 on_text 處理
        logger.info("unknown_command", "unknown command", {"chat_id": chat_id})
        await update.message.reply_text("不認識的指令,輸入 /help 看說明。")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(filters.COMMAND, on_unknown))
    return app


# --------------- 主程式 ---------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="weather_bot",
        description="Telegram 機器人:接收文字 → 查天氣 API 回傳",
    )
    p.add_argument("--check", action="store_true",
                   help="驗證設定與網路,然後退出")
    p.add_argument("--mock", action="store_true",
                   help="mock 模式:不連 Telegram/OWM,本機驗證流程")
    p.add_argument("--version", action="version", version=f"weather_bot {VERSION}")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env()
    if args.mock:
        settings = Settings(
            token=settings.token or "0:Mock-Mode-Token-Not-Validated",
            owm_key=settings.owm_key or "MOCK-OWM-KEY",
            units=settings.units,
            lang=settings.lang,
            timeout=settings.timeout,
            log_path=settings.log_path or Path.home() / "weather-bot.jsonl",
            mock=True,
        )

    logger = JsonLineLogger(settings.log_path)
    logger.info("boot", "weather_bot starting", {
        "version": VERSION,
        "mock": settings.mock,
        "check_mode": args.check,
        "telegram_available": TELEGRAM_AVAILABLE,
    })

    if not TELEGRAM_AVAILABLE:
        logger.error("telegram_missing", "python-telegram-bot 不可用", {"err": _TELEGRAM_IMPORT_ERR})
        sys.stderr.write(f"python-telegram-bot 不可用: {_TELEGRAM_IMPORT_ERR}\n")
        return 2

    if args.check:
        # mock 模式下,lenv 全空仍可驗證 telegram 模組與網路
        if settings.mock:
            report = run_check(settings, logger)
            print(report.to_text())
            print("\n[mock 模式]略過 token/api key 嚴格驗證")
            logger.close()
            return 0
        report = run_check(settings, logger)
        print(report.to_text())
        all_ok = (
            report.env_token_ok
            and report.env_owm_ok
            and report.log_writable
            and report.network_ok
            and report.owm_api_ok
        )
        logger.close()
        return 0 if all_ok else 1

    # 正式啟動前 sanity check
    if not settings.token:
        logger.error("missing_token", "TELEGRAM_BOT_TOKEN 未設定")
        sys.stderr.write("錯誤:TELEGRAM_BOT_TOKEN 未設定或為空。請看 --help 設定。\n")
        logger.close()
        return 2
    if not looks_like_bot_token(settings.token):
        logger.warn("token_format_suspicious", "token 格式不像 Telegram bot token",
                    {"token_head": settings.token[:12]})
        sys.stderr.write("[warn] TELEGRAM_BOT_TOKEN 格式不像正常的 bot token,繼續嘗試...\n")
    if not settings.owm_key and not settings.mock:
        logger.error("missing_owm_key", "OPENWEATHER_API_KEY 未設定")
        sys.stderr.write("錯誤:OPENWEATHER_API_KEY 未設定。如要 mock 測試請加 --mock。\n")
        logger.close()
        return 2

    weather = WeatherService(
        api_key=settings.owm_key,
        units=settings.units,
        lang=settings.lang,
        timeout=settings.timeout,
        logger=logger,
        mock=settings.mock,
    )

    try:
        app = build_application(settings, weather, logger)
    except Exception as e:
        logger.error("app_build_failed", f"build_application failed: {e!r}")
        sys.stderr.write(f"FATAL: build_application 失敗: {e!r}\n")
        logger.close()
        return 2

    logger.info("polling_start", "starting long-polling", {"mock": settings.mock})
    if settings.mock:
        # mock 模式完全離線:印出模擬問答互動,不起 Telegram polling
        logger.info("mock_session", "entering mock interrogation loop")
        print("[mock 模式]離線模擬(不打 Telegram/OWM)。")
        print("輸入城市名查詢(送出空行離開):")
        sys.stdout.flush()
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                city = sanitize_input(line)
                if not city:
                    print("(empty → 結束)")
                    break
                result = asyncio.run(weather.query(city))
                print("---")
                print(result.to_user_text())
                print("---")
                sys.stdout.flush()
        except KeyboardInterrupt:
            print("\n[mock] interrupted")
        logger.info("mock_session_done", "exit mock loop")
        logger.close()
        return 0
    try:
        app.run_polling(allowed_updates=["message"], drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("polling_keyboard_interrupt", "user interrupted")
    except Exception as e:
        logger.error("polling_crashed", f"run_polling crashed: {e!r}")
        sys.stderr.write(f"FATAL: run_polling 拋出: {e!r}\n")
        logger.close()
        return 1
    finally:
        logger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
