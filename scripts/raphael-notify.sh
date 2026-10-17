#!/usr/bin/env bash
# Hermes no-agent 通知：有新的「需要使用者決定」提案才輸出（空輸出 = 不通知）。
# 由 install-hermes.sh 複製到 ~/.hermes/scripts/raphael-notify.sh 後排程。
cd "/home/hoonsoropenclaw/raphael-harness" || exit 0
[ -f .venv/bin/activate ] && source .venv/bin/activate
# 先同步網站上的核准/取消/提醒，再輸出 raphael-notify；輸出不可混進通知內容
python -m harness proposal sync-inbox >/dev/null 2>&1 || true
python -m harness proposal notify
