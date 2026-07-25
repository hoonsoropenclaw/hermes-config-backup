# session_skill_logger.py argparse bug — 2026-06-20 D3 Exit

## 問題

`session_skill_logger.py --days 7 --write-log` 輸出 usage help 而非執行。

## 根因

原始程式碼邏輯：

```python
if args.session:           # ← early return
    ...
    return

if args.list_sessions:     # ← 搶走了 flow
    ...
    return

# --days 和 --write-log 的處理邏輯放在這裡
# 但當只有 --days（沒有 --session）時，走到 else → parser.print_help()
```

`--session` 有值時直接 return，導致 `--days` 的 branch 永遠無法抵達。

## 修復

新增 `elif args.platform or args.days:` branch，確保所有 flag combinations 都有處理邏輯。

```python
if args.session:
    ...
    return

elif args.platform or args.days:
    # 批次處理邏輯
    ...

parser.print_help()
```

## 預防

新增 argparse flag combination 前：
1. 實際測試**所有可能組合**（--session, --days, --write-log, --session --write-log, --days --write-log）
2. 確認 `if`/`elif`/`else` 的 mutually exclusive 邏輯覆蓋所有分支
3. 避免 early return 在 conditional blocks 之前，否則後面的 branch 永遠是 dead code
