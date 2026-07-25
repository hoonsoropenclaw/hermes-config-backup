#!/usr/bin/env python3
"""
赫米斯 Credential 拓撲地圖 (Credential Topology Map)
============================================
自動生成並維護赫米斯所有 API tokens 的：來源 → 消費者映射。

使用方式：
    python3 ~/.hermes/scripts/credential_topology_map.py

每個 cron job 或 script 只應從 ~/.hermes/.env 讀取 credential，
嚴禁 hardcode 或從多個路徑游擊式讀取。

2026-06-13 生成 | 由 metacognitive-learner cycle 建立
"""

from pathlib import Path
import re

HERMES_ENV = Path("/home/hoonsoropenclaw/.hermes/.env")
PORTAL_ENV = Path("/home/hoonsoropenclaw/permanent-projects/hermes-portal/.env.local")
SCRIPTS_DIR = Path("/home/hoonsoropenclaw/.hermes/scripts")

# ============================================================================
# CREDENTIAL 來源（Source of Truth）
# ============================================================================
# 所有 credential 都應在 ~/.hermes/.env 中，嚴禁放在其他位置。
# 若某個 script 需要從多個路徑讀取同一 credential（如 sync_evaluations.py），
# 代表該 script 有「credential 游擊式讀取」問題，需要重構。
#
# 2026-06-13 現況：
# - AGENT_API_KEY: 在 ~/.hermes/.env（真實值）+ hermes-portal/.env.local（mask 值 "***"）
#   → sync_evaluations.py 會同時讀兩個位置，但 .env.local 的 "***" 是 Vercel env pull 的 mask，導致 401
# - VERCEL_API_TOKEN: 在 ~/.hermes/.env
#   → sync_md_files.py, sync_scheduler.py, run_skill_stats.sh, skill-usage-daily-v3 cron 使用
# - TELEGRAM_BOT_TOKEN: 在 ~/.hermes/.env
#   → api_quota_monitor.sh, system_monitor.sh, watchdog.sh 使用
# - GITHUB_TOKEN: 在 ~/.hermes/.env（masked = "***"）
#   → v4-backup-tier1/2, hermes-backup-v4.sh 使用（透過 git remote URL 認證）
# - MINIMAX_API_KEY: 在 ~/.hermes/.env（masked = "***"）
#   → Hermes Agent 本體使用（hermes-gateway）
# - DEEPSEEK_API_KEY: 在 ~/.hermes/.env
#   → 可用於 API 呼叫
# - OLLAMA_WEB_SEARCH_API_KEY: 在 ~/.hermes/.env
#   → Ollama Web Search
# - TAVILY_API_KEY: 在 ~/.hermes/.env
#   → Web search 備援

# ============================================================================
# CONSUMER 腳本對照表（消費者）
# ============================================================================
# 格式：TOKEN_NAME -> [(script_name, usage_context), ...]

CREDENTIAL_CONSUMERS = {
    "AGENT_API_KEY": [
        ("sync_evaluations.py", "HERMES_PORTAL_API_KEY — 讀取 hermes-portal 評價資料"),
        ("eval-sync (cron)", "同上（scheduler-sync 所屬的 cron job）"),
    ],
    "VERCEL_API_TOKEN": [
        ("sync_md_files.py", "部署 hermes-status-site 到 Vercel"),
        ("sync_scheduler.py", "部署 scheduler 相關網站"),
        ("run_skill_stats.sh", "部署 skill stats 到 Vercel"),
        ("skill-usage-daily-v3 (cron)", "部署 skill stats 網站"),
    ],
    "TELEGRAM_BOT_TOKEN": [
        ("api_quota_monitor.sh", "當配額不足時發送 Telegram 警告"),
        ("system_monitor.sh", "系統健康狀態通知"),
        ("watchdog.sh", "服務 watchdog 通知"),
        ("hermes-gateway (main)", "Telegram DM 接入"),
    ],
    "GITHUB_TOKEN": [
        ("v4-backup-tier1-daily (cron)", "git push hermes-backup-staging"),
        ("v4-backup-tier2-daily (cron)", "git push hermes-backup-staging"),
        ("hermes-backup-v4.sh", "git push hermes-config-backup"),
        ("hermes-backup-daily-summary.sh", "git push hermes-backup-staging"),
        ("verify-recovery-chain.sh", "驗證還原鏈"),
        # SSH 認證（git remote URL 是 git@github.com:...，不走 HTTPS）
    ],
    "MINIMAX_API_KEY": [
        ("hermes-gateway (main)", "默認 LLM provider"),
    ],
    "DEEPSEEK_API_KEY": [
        ("hermes-gateway (可選)", "備援 LLM provider"),
    ],
    "OLLAMA_WEB_SEARCH_API_KEY": [
        ("hermes-gateway (web_search)", "Ollama Web Search 主軌"),
    ],
    "TAVILY_API_KEY": [
        ("hermes-gateway (web_search)", "Web Search 備軌（OLLAMA_WEB_SEARCH_API_KEY 失敗時）"),
    ],
}

# ============================================================================
# 已知問題（Known Issues）
# ============================================================================
ISSUES = """
1. sync_evaluations.py 同時讀 hermes-portal/.env.local 和 ~/.hermes/.env
   → .env.local 中的 AGENT_API_KEY 是 "***" mask（Vercel env pull 機制）
   → 導致 eval-sync cron job 出現 401 Unauthorized
   → 正確做法：永遠只從 ~/.hermes/.env 讀取
"""

def generate_report():
    lines = []
    lines.append("=" * 70)
    lines.append("赫米斯 Credential 拓撲地圖")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Source of Truth: {HERMES_ENV}")
    lines.append(f"Secondary:       {PORTAL_ENV}")
    lines.append("")
    
    for token, consumers in sorted(CREDENTIAL_CONSUMERS.items()):
        lines.append(f"\n{token}")
        lines.append("-" * 50)
        for script, purpose in consumers:
            lines.append(f"  → {script}")
            lines.append(f"    用途: {purpose}")
    
    lines.append("\n" + "=" * 70)
    lines.append("已知問題")
    lines.append("=" * 70)
    lines.append(ISSUES)
    
    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_report())
