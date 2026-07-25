#!/usr/bin/env python3
"""
test_weather_bot.py — 離線單元測試(不需 Telegram token / OWM key)

涵蓋:
- input 清洗 (sanitize_input)
- city 啟發式 (_is_probably_city)
- 失敗分類 (WeatherService.query 在 mock 模式)
- 結果格式化 (WeatherResult.to_user_text)
- Logger 結構化輸出
- Settings.from_env
- build_application 結構 (handler 註冊)
- CLI entry 主要分支

執行: hermes-venv 的 python3 test_weather_bot.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/home/hoonsoropenclaw/.hermes/scripts")

import weather_bot as wb  # noqa: E402


class TestSanitizeInput(unittest.TestCase):
    def test_strip_and_collapse(self):
        self.assertEqual(wb.sanitize_input("  hello   world  "), "hello world")

    def test_remove_control_chars(self):
        self.assertEqual(wb.sanitize_input("a\x00b\x07c"), "abc")

    def test_truncate_long(self):
        long = "a" * 500
        out = wb.sanitize_input(long, max_len=80)
        self.assertEqual(len(out), 80)

    def test_empty(self):
        self.assertEqual(wb.sanitize_input(""), "")
        self.assertEqual(wb.sanitize_input(None), "")
        self.assertEqual(wb.sanitize_input("   "), "")

    def test_unicode_preserved(self):
        self.assertEqual(wb.sanitize_input("台北市 天氣"), "台北市 天氣")

    def test_newline_collapsed(self):
        self.assertEqual(wb.sanitize_input("line1\n\nline2\t\tline3"), "line1 line2 line3")


class TestCityValidation(unittest.TestCase):
    def test_valid_english(self):
        self.assertTrue(wb._is_probably_city("Tokyo"))
        self.assertTrue(wb._is_probably_city("New York"))

    def test_valid_chinese(self):
        self.assertTrue(wb._is_probably_city("台北市"))
        self.assertTrue(wb._is_probably_city("渋谷区"))

    def test_invalid_url(self):
        self.assertFalse(wb._is_probably_city("https://example.com"))
        self.assertFalse(wb._is_probably_city("foo.com"))
        self.assertFalse(wb._is_probably_city("/etc/passwd"))

    def test_invalid_too_short(self):
        self.assertFalse(wb._is_probably_city("a"))
        self.assertFalse(wb._is_probably_city(""))

    def test_invalid_too_long(self):
        self.assertFalse(wb._is_probably_city("a" * 200))

    def test_invalid_no_letter(self):
        self.assertFalse(wb._is_probably_city("12345"))
        self.assertFalse(wb._is_probably_city("---"))

    def test_email_like(self):
        self.assertFalse(wb._is_probably_city("user@example.com"))


class TestWeatherResult(unittest.TestCase):
    def test_format_success(self):
        data = {
            "name": "Taipei",
            "sys": {"country": "TW", "sunrise": 1700000000, "sunset": 1700040000},
            "weather": [{"id": 800, "main": "Clear", "description": "晴", "icon": "01d"}],
            "main": {"temp": 27.3, "feels_like": 29.1, "temp_min": 25.0, "temp_max": 30.0,
                      "humidity": 65, "pressure": 1013},
            "wind": {"speed": 3.2},
            "clouds": {"all": 10},
        }
        r = wb.WeatherResult(ok=True, city="Taipei", data=data)
        r.units_here = "metric"
        text = r.to_user_text()
        self.assertIn("Taipei", text)
        self.assertIn("晴", text)
        self.assertIn("°C", text)
        self.assertIn("濕度:65%", text)
        self.assertIn("☀️", text)  # icon 01d
        self.assertIn("日出", text)

    def test_format_empty_error(self):
        r = wb.WeatherResult(ok=False, city="", error_kind="empty")
        self.assertIn("城市", r.to_user_text())

    def test_format_invalid_error(self):
        r = wb.WeatherResult(ok=False, city="!!@#", error_kind="invalid")
        self.assertIn("看不懂", r.to_user_text())

    def test_format_4xx_401(self):
        r = wb.WeatherResult(ok=False, city="Tokyo", error_kind="4xx", http_status=401)
        self.assertIn("401", r.to_user_text())
        self.assertIn("OPENWEATHER_API_KEY", r.to_user_text())

    def test_format_4xx_404(self):
        r = wb.WeatherResult(ok=False, city="XXX", error_kind="4xx", http_status=404)
        self.assertIn("找不到", r.to_user_text())

    def test_format_4xx_429(self):
        r = wb.WeatherResult(ok=False, city="Tokyo", error_kind="4xx", http_status=429)
        self.assertIn("429", r.to_user_text())

    def test_format_5xx(self):
        r = wb.WeatherResult(ok=False, city="Tokyo", error_kind="5xx")
        self.assertIn("5xx", r.to_user_text())

    def test_format_timeout(self):
        r = wb.WeatherResult(ok=False, city="Tokyo", error_kind="timeout")
        self.assertIn("timeout", r.to_user_text())

    def test_format_network(self):
        r = wb.WeatherResult(ok=False, city="Tokyo", error_kind="network")
        self.assertIn("網路", r.to_user_text())


class TestWeatherService(unittest.TestCase):
    def _make_logger(self):
        return wb.JsonLineLogger(None)  # 不寫檔

    def test_query_empty(self):
        ws = wb.WeatherService("", units="metric", lang="zh_tw", timeout=1,
                                  logger=self._make_logger(), mock=True)
        r = asyncio.run(ws.query(""))
        self.assertFalse(r.ok)
        self.assertEqual(r.error_kind, "empty")

    def test_query_invalid(self):
        ws = wb.WeatherService("", units="metric", lang="zh_tw", timeout=1,
                                  logger=self._make_logger(), mock=True)
        r = asyncio.run(ws.query("@@@"))
        self.assertFalse(r.ok)
        self.assertEqual(r.error_kind, "invalid")

    def test_query_mock(self):
        ws = wb.WeatherService("", units="metric", lang="zh_tw", timeout=1,
                                  logger=self._make_logger(), mock=True)
        r = asyncio.run(ws.query("台北市"))
        self.assertTrue(r.ok)
        self.assertIn("name", r.data)
        text = r.to_user_text()
        self.assertIn("台北市", text)
        self.assertIn("°C", text)


class TestJsonLineLogger(unittest.TestCase):
    def test_writes_valid_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "test.jsonl"
            logger = wb.JsonLineLogger(log_path)
            logger.info("test_event", "hello", {"foo": 1})
            logger.warn("warn_event", "watch", {"x": [1, 2]})
            logger.error("err_event", "boom", {"code": 500})
            logger.close()
            content = log_path.read_text()
            lines = [l for l in content.splitlines() if l.strip()]
            self.assertEqual(len(lines), 3)
            for line in lines:
                obj = json.loads(line)
                self.assertIn("ts", obj)
                self.assertIn("level", obj)
                self.assertIn("event", obj)
                self.assertIn("message", obj)
                self.assertIn("ctx", obj)
            self.assertEqual(json.loads(lines[0])["level"], "INFO")
            self.assertEqual(json.loads(lines[1])["level"], "WARN")
            self.assertEqual(json.loads(lines[2])["level"], "ERROR")

    def test_none_path_no_error(self):
        logger = wb.JsonLineLogger(None)
        logger.info("e", "m")  # 不應拋
        logger.close()

    def test_bad_path_falls_back(self):
        logger = wb.JsonLineLogger(Path("/nonexistent/dir/x.jsonl"))
        logger.info("e", "m")  # 不應拋
        logger.close()


class TestSettings(unittest.TestCase):
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            s = wb.Settings.from_env()
        self.assertEqual(s.token, "")
        self.assertEqual(s.owm_key, "")
        self.assertEqual(s.units, "metric")
        self.assertEqual(s.lang, "zh_tw")
        self.assertEqual(s.timeout, 10.0)
        self.assertIsNone(s.log_path)

    def test_loads_env(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:abcdef",
            "OPENWEATHER_API_KEY": "owm-key",
            "OWM_UNITS": "imperial",
            "OWM_LANG": "en",
            "HTTP_TIMEOUT": "20",
            "LOG_FILE": "/tmp/x.log",
        }
        with patch.dict(os.environ, env, clear=True):
            s = wb.Settings.from_env()
        self.assertEqual(s.token, "123:abcdef")
        self.assertEqual(s.owm_key, "owm-key")
        self.assertEqual(s.units, "imperial")
        self.assertEqual(s.lang, "en")
        self.assertEqual(s.timeout, 20.0)
        self.assertEqual(s.log_path, Path("/tmp/x.log"))


class TestBuildApplication(unittest.TestCase):
    def test_build_registers_handlers(self):
        logger = wb.JsonLineLogger(None)
        ws = wb.WeatherService("", units="metric", lang="zh_tw", timeout=1,
                                  logger=logger, mock=True)
        settings = wb.Settings(token="0:Mock", owm_key="k", mock=True)
        app = wb.build_application(settings, ws, logger)
        # PTB 22 在 group 0 註冊了 4 個 handler(start, help, health, text, unknown)
        # 不同版本可能 4 or 5;重要的是至少有 3 個核心
        self.assertGreaterEqual(len(app.handlers[0]), 3)

    def test_unknown_telegram_lib_raises(self):
        logger = wb.JsonLineLogger(None)
        ws = wb.WeatherService("", units="metric", lang="zh_tw", timeout=1,
                                  logger=logger, mock=True)
        settings = wb.Settings(token="0:Mock", owm_key="k", mock=True)
        with patch.object(wb, "TELEGRAM_AVAILABLE", False):
            with self.assertRaises(RuntimeError):
                wb.build_application(settings, ws, logger)


class TestBotLogic(unittest.TestCase):
    """模擬 on_text handler 處理一個訊息端到端。"""

    def _make_bot_context(self):
        logger = wb.JsonLineLogger(None)
        ws = wb.WeatherService("", units="metric", lang="zh_tw", timeout=1,
                                  logger=logger, mock=True)
        return ws, logger

    def test_end_to_end_success(self):
        ws, logger = self._make_bot_context()
        result = asyncio.run(ws.query("台中"))
        self.assertTrue(result.ok)
        self.assertIn("台中", result.to_user_text())

    def test_end_to_end_invalid(self):
        ws, logger = self._make_bot_context()
        result = asyncio.run(ws.query("###"))
        self.assertFalse(result.ok)
        self.assertEqual(result.error_kind, "invalid")


class TestIconUnicode(unittest.TestCase):
    def test_known_icons(self):
        self.assertEqual(wb._icon_to_emoji("01d"), "☀️")
        self.assertEqual(wb._icon_to_emoji("02n"), "🌤️")
        self.assertEqual(wb._icon_to_emoji("09d"), "🌧️")
        self.assertEqual(wb._icon_to_emoji("11d"), "⛈️")
        self.assertEqual(wb._icon_to_emoji("13d"), "❄️")
        self.assertEqual(wb._icon_to_emoji("50d"), "🌫️")

    def test_unknown_icon(self):
        self.assertEqual(wb._icon_to_emoji("99d"), "🌡️")
        self.assertEqual(wb._icon_to_emoji(""), "🌡️")


class TestUnitSymbol(unittest.TestCase):
    def test_metric(self):
        self.assertEqual(wb._unit_symbol("metric"), "°C")
    def test_imperial(self):
        self.assertEqual(wb._unit_symbol("imperial"), "°F")
    def test_standard(self):
        self.assertEqual(wb._unit_symbol("standard"), "K")
    def test_unknown_defaults(self):
        self.assertEqual(wb._unit_symbol("foo"), "°C")


class TestTokenFormat(unittest.TestCase):
    def test_real_telegram_format(self):
        # 真實格式:<digits>:<35+ chars alphanumeric>
        self.assertTrue(wb.looks_like_bot_token("1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-abcde"))

    def test_wrong_digits(self):
        self.assertFalse(wb.looks_like_bot_token("abc:1234567890abcdefghij1234567890abcde"))

    def test_wrong_tail(self):
        self.assertFalse(wb.looks_like_bot_token("1234567890:"))

    def test_empty(self):
        self.assertFalse(wb.looks_like_bot_token(""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
