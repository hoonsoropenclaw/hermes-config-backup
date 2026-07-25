#!/bin/bash
# School Bulletin System Health Watchdog — checks every minute
# Restarts monitoring if production URL returns non-200
#
# IMPORTANT: Check the ROOT URL, not /api/health (which does not exist).
# Previous version used CHECK_PATH="/api/health" and produced false 404 errors.
#
# Deployed to crontab: * * * * * /tmp/school-bulletin-watchdog.sh >> /tmp/school-bulletin-watchdog.log 2>&1

SCHOOL_BULLETIN_URL="https://school-bulletin.vercel.app"
# CHECK_PATH must be empty — /api/health does NOT exist on this deployment
CHECK_PATH=""
MAX_RETRIES=2

check_bulletin() {
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${SCHOOL_BULLETIN_URL}${CHECK_PATH}" 2>/dev/null)
    echo "$status"
}

main() {
    local status
    status=$(check_bulletin)

    if [ "$status" = "200" ]; then
        exit 0
    fi

    # Retry once after 5 seconds
    sleep 5
    status=$(check_bulletin)

    if [ "$status" = "200" ]; then
        exit 0
    fi

    # Both checks failed — log and alert
    logger -t school-bulletin-watchdog "FAILED: HTTP ${status} from ${SCHOOL_BULLETIN_URL}${CHECK_PATH} (retried)"
    echo "$(date '+%Y-%m-%d %H:%M:%S') school-bulletin-watchdog: HTTP ${status} from ${SCHOOL_BULLETIN_URL}${CHECK_PATH}" >> /tmp/school-bulletin-watchdog.log
    exit 1
}

main
