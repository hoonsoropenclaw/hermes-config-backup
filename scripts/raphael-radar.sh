#!/usr/bin/env bash
# Hermes no-agent 排程（每晚 21:30，在新知雷達 20:00 傳來 items.json 之後）：
#   同步核准結果 → 雷達匯入 → 規則初篩 → M3 評分與技能卡 → 建學習提案單
# 正常情況不輸出（空輸出 = 不推 Telegram）；新提案的通知由派工網站的輪詢器負責。
# 只有某一步失敗時才印一行摘要。完整紀錄在 state/radar/logs/<日期>.log。
# 由 install-hermes.sh（或手動）複製到 ~/.hermes/scripts/raphael-radar.sh 後排程。
cd "/home/hoonsoropenclaw/raphael-harness" || exit 0
[ -f .venv/bin/activate ] && source .venv/bin/activate
mkdir -p state/radar/logs
LOG="state/radar/logs/$(date +%F).log"
fail=""
for step in "proposal sync-inbox" "radar ingest" "radar filter" "radar score" "radar propose"; do
  # shellcheck disable=SC2086
  out=$(python -m harness $step 2>&1)
  rc=$?
  { echo "== $(date '+%F %T') $step（結束碼 $rc）"; echo "$out"; } >> "$LOG"
  if [ $rc -ne 0 ] || printf '%s' "$out" | grep -q '"ok": false'; then
    fail="$fail「$step」"
  fi
done
if [ -n "$fail" ]; then
  echo "[拉斐爾] 新知學習流程有步驟失敗：$fail，詳見 ~/raphael-harness/$LOG"
fi
exit 0
