#!/bin/bash
# N100 Autonomous Learning Manager
# Usage: ./manage_learning.sh [start|stop|stop-hard]

CRON_FILE="/tmp/current_cron"
CRON_JOB="/home/hoonsoropenclaw/.hermes/smart_heartbeat.py"

case "$1" in
    start)
        echo "[INFO] Unsealing smart_heartbeat.py..."
        crontab -l > $CRON_FILE
        sed -i "s|# \*/10 \* \* \* \* /usr/bin/python3 $CRON_JOB|\*/10 \* \* \* \* /usr/bin/python3 $CRON_JOB|g" $CRON_FILE
        crontab $CRON_FILE
        echo "[SUCCESS] Autonomous learning started."
        ;;
    stop)
        echo "[INFO] Sealing smart_heartbeat.py (Soft Stop)..."
        crontab -l > $CRON_FILE
        sed -i "s|^\*/10 \* \* \* \* /usr/bin/python3 $CRON_JOB|# \*/10 \* \* \* \* /usr/bin/python3 $CRON_JOB|g" $CRON_FILE
        crontab $CRON_FILE
        echo "[SUCCESS] Autonomous learning scheduled generation stopped. Existing sessions will finish gracefully."
        ;;
    stop-hard)
        echo "[INFO] Sealing smart_heartbeat.py and killing agents (Hard Stop)..."
        $0 stop
        echo "[INFO] Waiting 30 minutes for graceful shutdown buffer..."
        # The wait is managed by Antigravity schedule, so we kill immediately here.
        echo "[INFO] Killing active hermes_cli sessions..."
        pkill -f "hermes_cli.main gateway run"
        echo "[SUCCESS] All sessions terminated."
        ;;
    *)
        echo "Usage: $0 {start|stop|stop-hard}"
        exit 1
esac
