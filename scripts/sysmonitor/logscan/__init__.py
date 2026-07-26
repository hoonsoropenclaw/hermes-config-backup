"""
logscan — 系統日誌掃描子套件
"""
from .scanner import LogHit, scan_log_file, scan_journal, scan_all

__all__ = ["LogHit", "scan_log_file", "scan_journal", "scan_all"]
