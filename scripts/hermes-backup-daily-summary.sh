#!/usr/bin/env bash
# hermes-backup-daily-summary.sh
# v4.1 每日備份摘要（22:00 跑、彙整當日 3 個 v4-* jobs、送到 Telegram）
#
# 設計：
#   - v4-backup-tier1-daily (02:00)、v4-backup-tier2-daily (02:30)、v4-restore-verify-weekly (週日 04:00)
#     三個都加 wakeAgent: false gate（成功時 silent、不直接送 Telegram）
#   - 本腳本（22:00 跑）讀取三個 v4-* jobs 的最後一次 log、彙整送 Telegram

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
CRON_OUTPUT="$HERMES_HOME/cron/output"
JOBS_JSON="$HERMES_HOME/cron/jobs.json"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%SZ)
TODAY=$(date +%Y-%m-%d)

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# 收集 v4-* job 的結果
declare -a SUMMARY_LINES
SUMMARY_LINES+=("📦 Hermes 備份每日摘要 ($TODAY)")
SUMMARY_LINES+=("")

# 對 3 個 v4-* job 收集
for job_name in v4-backup-tier1-daily v4-backup-tier2-daily v4-restore-verify-weekly; do
  # 從 jobs.json 找 job_id
  job_id=$(python3 -c "
import json
with open('$JOBS_JSON') as f:
    data = json.load(f)
for j in data.get('jobs', []):
    if j.get('name') == '$job_name':
        print(j.get('id', '?'))
        break
")
  if [[ -z "$job_id" ]]; then
    SUMMARY_LINES+=("• $job_name: ❌ not configured")
    continue
  fi

  # 找最新 log（nullglob 防止 ls *.md 匹配 0 檔時失敗觸發 set -e）
    shopt -s nullglob
    today_log="$CRON_OUTPUT/$job_id/${TODAY}_"*".md"
    latest=$(ls -t $today_log 2>/dev/null | head -1 || true)
    shopt -u nullglob

  if [[ -z "$latest" ]] || [[ ! -f "$latest" ]]; then
    # 週日才有 verify、不是週日就標 N/A
    if [[ "$job_name" == "v4-restore-verify-weekly" ]] && [[ $(date +%u) != 7 ]]; then
      SUMMARY_LINES+=("• $job_name: ⏭  N/A today (週日才跑)")
    else
      SUMMARY_LINES+=("• $job_name: ⚠️  找不到 log（$CRON_OUTPUT/$job_id/）")
    fi
    continue
  fi

  # 從 log 抽出狀態
  if grep -qE "GH013|GH001|destination not found|Failed to|Failed |error:|ERROR" "$latest" 2>/dev/null; then
    SUMMARY_LINES+=("• $job_name: ❌ FAILED")
    SUMMARY_LINES+=("  log: $latest")
  else
    SUMMARY_LINES+=("• $job_name: ✅ success")
    # 抓關鍵指標
    file_count=$(grep -oE "[0-9]+ files? changed" "$latest" 2>/dev/null | head -1 || true)
    push_result=$(grep "GitHub push" "$latest" 2>/dev/null | head -1 | sed 's/\x1b\[[0-9;]*m//g' || true)
    if [[ -n "$file_count" ]]; then
      SUMMARY_LINES+=("  → $file_count")
    fi
    if [[ -n "$push_result" ]]; then
      SUMMARY_LINES+=("  → $push_result")
    fi
  fi
  SUMMARY_LINES+=("")
done

# Drive 額外資訊（Tier 2 用）
SUMMARY_LINES+=("📊 Drive 狀態")
LATEST_BUNDLE=$(rclone lsf hoonsorasus:hermes-backup/secrets/ --config $HOME/documents/rclone.conf 2>/dev/null | grep "secrets-bundle-.*\.tar\.gpg$" | sort -r | head -1)
if [[ -n "$LATEST_BUNDLE" ]]; then
  SUMMARY_LINES+=("• 最新 Drive bundle: $LATEST_BUNDLE")
  BUNDLE_SIZE=$(rclone ls hoonsorasus:hermes-backup/secrets/$LATEST_BUNDLE --config $HOME/documents/rclone.conf 2>/dev/null | awk '{print $1}')
  SUMMARY_LINES+=("• Bundle 大小: $(( BUNDLE_SIZE / 1024 / 1024 )) MB")
else
  SUMMARY_LINES+=("• ⚠️  Drive 上找不到 secrets bundle")
fi
SUMMARY_LINES+=("")

# Drive 垃圾桶警告（如果有東西）
TRASH_SIZE=$(rclone about hoonsorasus: --config $HOME/documents/rclone.conf 2>/dev/null | grep Trashed | awk '{print $2, $3}')
SUMMARY_LINES+=("🗑️  Drive 垃圾桶: $TRASH_SIZE")
SUMMARY_LINES+=("")

SUMMARY_LINES+=("完整 backup script: $HERMES_HOME/scripts/hermes-backup-v4.sh")
SUMMARY_LINES+=("完整 SOP: https://github.com/hoonsoropenclaw/hermes-config-backup/blob/main/docs/RESTORE-V4.md")

# 把彙整印到 stdout（hermes cron 會送給 deliver target）
# 用 for loop 取代 printf '%s\n' "${arr[@]}" — printf 在 array 含特殊字元時可能不印
for line in "${SUMMARY_LINES[@]}"; do
  echo "$line"
done
