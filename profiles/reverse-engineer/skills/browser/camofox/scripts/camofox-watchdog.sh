#!/bin/bash
# Camofox Health Watchdog — checks every minute
# Restarts the container if browserConnected is false, with logging via logger

HEALTH=$(curl -s --max-time 5 http://localhost:9377/health 2>/dev/null)
if [ -z "$HEALTH" ]; then
  # API unreachable — container may be down or engine not responding
  logger -t camofox-watchdog "API unreachable, restarting container"
  docker restart camofox-browser
  exit
fi

if echo "$HEALTH" | grep -q '"browserConnected":false'; then
  logger -t camofox-watchdog "browserConnected=false, restarting camofox-browser"
  docker restart camofox-browser
fi