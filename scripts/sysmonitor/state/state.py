"""
state.py — 持久化監控狀態
========================

負責兩件事：
1. 追蹤每個 log 檔的讀過 offset（支援增量掃描、不重複告警）
2. 記錄 alert fingerprint 的最後發送時間（cooldown 抑制）

儲存格式：JSON，atomic write（先寫 .tmp 再 rename）。
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

# 預設狀態目錄（腳本啟動時可覆寫）
DEFAULT_STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_FILE = DEFAULT_STATE_DIR / "state.json"


class State:
    """簡單的 key/value 持久化層。

    schema:
    {
        "log_offsets": {
            "/var/log/syslog": 12345678,   # 已讀過的 byte offset
            "/var/log/kern.log": 9012,
        },
        "alert_fingerprints": {
            "cpu_crit:2026-07-27:01-02": 1722000000.0,  # last_sent epoch
        },
        "consecutive_crit": {
            "cpu_crit": 3,   # 連續 crit 計數
        },
        "alerts_sent_today": {
            "2026-07-27": 5,  # 當日 alert 數量
        },
    }
    """

    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def _load(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return self._empty()
        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # 確保必要 key 都在
            for key in ("log_offsets", "alert_fingerprints", "consecutive_crit", "alerts_sent_today"):
                data.setdefault(key, {})
            return data
        except (json.JSONDecodeError, OSError):
            # 壞檔 → 重新開始（不要讓監控自己掛掉）
            return self._empty()

    def _empty(self) -> dict[str, Any]:
        return {
            "log_offsets": {},
            "alert_fingerprints": {},
            "consecutive_crit": {},
            "alerts_sent_today": {},
        }

    def save(self) -> None:
        """atomic write：先寫 .tmp 再 rename，避免半寫狀態。"""
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".state.", suffix=".tmp", dir=self.state_file.parent
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.state_file)
        except Exception:
            # 失敗時清掉 .tmp
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    # log offsets
    # ------------------------------------------------------------------
    def get_offset(self, log_path: str) -> int:
        return int(self._data["log_offsets"].get(log_path, 0))

    def set_offset(self, log_path: str, offset: int) -> None:
        self._data["log_offsets"][log_path] = int(offset)

    # ------------------------------------------------------------------
    # alert fingerprints
    # ------------------------------------------------------------------
    def can_send(self, fingerprint: str, cooldown_sec: int) -> bool:
        """檢查該 fingerprint 是否在 cooldown 內。"""
        last = self._data["alert_fingerprints"].get(fingerprint)
        if last is None:
            return True
        return (time.time() - float(last)) >= cooldown_sec

    def mark_sent(self, fingerprint: str) -> None:
        self._data["alert_fingerprints"][fingerprint] = time.time()

    # ------------------------------------------------------------------
    # consecutive crit counter
    # ------------------------------------------------------------------
    def bump_crit(self, key: str, increment: int = 1) -> int:
        v = int(self._data["consecutive_crit"].get(key, 0)) + increment
        self._data["consecutive_crit"][key] = v
        return v

    def reset_crit(self, key: str) -> None:
        self._data["consecutive_crit"][key] = 0

    def get_crit(self, key: str) -> int:
        return int(self._data["consecutive_crit"].get(key, 0))

    # ------------------------------------------------------------------
    # daily alert counter
    # ------------------------------------------------------------------
    def incr_today(self, today: str) -> int:
        v = int(self._data["alerts_sent_today"].get(today, 0)) + 1
        self._data["alerts_sent_today"][today] = v
        return v

    def today_count(self, today: str) -> int:
        return int(self._data["alerts_sent_today"].get(today, 0))
