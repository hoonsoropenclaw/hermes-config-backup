#!/usr/bin/env bash
# v4 backup --brief --tier1 的 cron wrapper
# 詳見 hermes-backup-v4.sh 說明
# 為什麼要這個 wrapper:hermes cron 的 script 欄位把整段當路徑找、不支援 flags
# 解法:每個 flag 組合包成獨立 script
exec /home/hoonsoropenclaw/.hermes/scripts/hermes-backup-v4.sh --brief --tier1
