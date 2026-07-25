#!/bin/bash
# API 消耗追蹤腳本
# 用法: ./increment_api_calls.sh <數量>

AMOUNT=${1:-0}
COUNTER_FILE="/home/hoonsoropenclaw/.hermes/evolution/api_counter.txt"

# 讀取當前數值
if [ -f "$COUNTER_FILE" ]; then
    CURRENT=$(cat "$COUNTER_FILE")
else
    CURRENT=0
fi

# 累加
NEW_TOTAL=$((CURRENT + AMOUNT))

# 寫回
echo "$NEW_TOTAL" > "$COUNTER_FILE"

# 顯示結果
echo "API 消耗: +${AMOUNT}"
echo "總計: ${NEW_TOTAL}"
echo "時間: $(date '+%Y-%m-%d %H:%M:%S')"