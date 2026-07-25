#!/usr/bin/env python3
"""
Cron Job 健康掃描器

執行：python3 ~/.hermes/skills/devops/cron-job-health-monitor/scripts/check_cron_health.py
輸出：結構化報告（job name / 錯誤類型 / 嚴重度 / 建議修復）

觸發：
- metacognitive-learner Phase 1.5（每次啟動）
- 手動診斷 cron 失敗
- 排程（例如每天 09:00）做 health check
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime


JOBS_JSON = Path("/home/hoonsoropenclaw/.hermes/cron/jobs.json")


# 錯誤分類決策樹
ERROR_PATTERNS = [
    {
        "id": "A_AUTH_401",
        "pattern": re.compile(r"HTTP Error 401|Unauthorized|X-Agent-Key", re.IGNORECASE),
        "category": "認證/授權失敗",
        "severity": "HIGH",
        "fix_hint": "見 portal-401-troubleshoot skill (Step 5.5 多行 .env.local 陷阱、Step 6 Vercel rebuild)",
        "skill": "portal-401-troubleshoot",
    },
    {
        "id": "B_GH013_SECRET_LEAK",
        "pattern": re.compile(r"GH013|Repository rule violations|secret|Push cannot contain"),
        "category": "Secret leak (push 到公開 GitHub)",
        "severity": "CRITICAL",
        "fix_hint": "立即暫停 cron + 見 alt-token-secrets-layout/references/cron-secret-leak-scrub.md",
        "skill": "alt-token-secrets-layout",
    },
    {
        "id": "C_CRON_EDIT_SCRIPT_BUG",
        "pattern": re.compile(r"#!/bin/bash|Script not found.*hermes/scripts/#!"),
        "category": "hermes cron edit --script bug",
        "severity": "MEDIUM",
        "fix_hint": "見 metacognitive-learner skill (cron edit --script bug 段落)，手動編輯 jobs.json",
        "skill": "metacognitive-learner",
    },
    {
        "id": "D_SCRIPT_NOT_FOUND",
        "pattern": re.compile(r"Script not found", re.IGNORECASE),
        "category": "Script path 錯誤",
        "severity": "MEDIUM",
        "fix_hint": "確認 script 欄位為純檔名（無路徑），編輯 jobs.json 修正",
        "skill": "hermes-self-improvement",
    },
    {
        "id": "E_TIMEOUT_TRANSIENT",
        "pattern": re.compile(r"timed out|Connection refused|Connection reset|URLError"),
        "category": "暫時性網路/服務問題",
        "severity": "LOW",
        "fix_hint": "標記 transient，24h 後重試。連續 3 天同類錯誤升級",
        "skill": None,
    },
    {
        "id": "F_GENERIC_EXIT_1",
        "pattern": re.compile(r"Script exited with code 1", re.IGNORECASE),
        "category": "Script 執行失敗（待細查）",
        "severity": "MEDIUM",
        "fix_hint": "讀 last_error 完整 stdout+stderr 找對應 skill",
        "skill": None,
    },
]


def load_jobs():
    if not JOBS_JSON.exists():
        print(f"ERROR: jobs.json not found at {JOBS_JSON}", file=sys.stderr)
        sys.exit(1)
    return json.loads(JOBS_JSON.read_text())


def classify_error(last_error: str):
    """回傳 (pattern_id, category, severity, fix_hint, skill) 或 None"""
    if not last_error:
        return None
    for p in ERROR_PATTERNS:
        if p["pattern"].search(last_error):
            return p
    return {
        "id": "Z_UNKNOWN",
        "pattern": None,
        "category": "未知錯誤",
        "severity": "MEDIUM",
        "fix_hint": "手動讀 last_error + stdout/stderr 全文",
        "skill": None,
    }


def main():
    data = load_jobs()
    jobs = data.get("jobs", [])

    failed = []
    for job in jobs:
        if job.get("last_status") != "error":
            continue

        classification = classify_error(job.get("last_error", ""))
        failed.append(
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "last_run": job.get("last_run_at"),
                "last_error_preview": (job.get("last_error") or "")[:150],
                "classification": classification,
            }
        )

    # 報告
    report = {
        "scan_time": datetime.now().isoformat(),
        "total_jobs": len(jobs),
        "failed_jobs": len(failed),
        "critical_count": sum(1 for f in failed if f["classification"]["severity"] == "CRITICAL"),
        "high_count": sum(1 for f in failed if f["classification"]["severity"] == "HIGH"),
        "failed": failed,
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    # 若有 critical，回傳 exit code 2（讓排程觸發 alert）
    if report["critical_count"] > 0:
        sys.exit(2)
    elif report["high_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
