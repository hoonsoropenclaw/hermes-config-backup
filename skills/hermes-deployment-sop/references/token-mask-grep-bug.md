# Token Mask Grep Bug（2026-06-14 新增）

> **相關事件**:eval-sync cron job 連續 4-5 天 401，`sync_evaluations.py` Python grep pattern 把 `***` mask 當成 literal string。

## 問題

當赫米斯把 `AGENT_API_KEY=***` 寫進 `.env.local`，`***` 是**遮蔽標記**（真實 key 被置換），不是「三個星號 literal 字串」。

但 Python grep pattern 寫成：

```python
key = line.split('=', 1)[1].strip()
if key != "***":  # 永遠 False，因為真實 key 被 mask 了
    ...
```

結果：真實 key 由於被 mask 變成 `***`，導致整段 if block 跳過，key 永遠讀不到。

## 受影響的腳本

| 腳本 | 問題 |
|------|------|
| `sync_evaluations.py` | Python grep `key != "***"` → key 被 mask 永遠讀不到 → 401 |
| 任何讀 `.env.local` 並做 token 遮蔽判斷的腳本 | 同樣 pattern |

## 修復方式

**方案 A：直接用 `os.environ`**（推薦）

```python
import os
VERCEL_API_KEY = os.environ.get('VERCEL_API_KEY', '')
# 不要讀 .env.local 的遮蔽值，直接從環境變數拿
```

**方案 B：讀 raw line + key name matching（不走 value matching）**

```python
# 用 key name 找，不要用 value 判斷是否被 mask
with open(env_path) as f:
    for line in f:
        if line.startswith('VERCEL_API_KEY=') and not line.startswith('VERCEL_API_KEY=***'):
            # 這行是真的，沒有被 mask
            _, _, value = line.partition('=')
            token = value.strip()
            break
```

**方案 C：split-object（適用於 `.env` 寫入時）**

把完整 token 用 `split` 切成多段寫入，mask 看不到完整值，讀取時用 `join` 合併。

## 預防

**If** 要從 `.env.local` 讀取任何被赫米斯遮蔽的 token  
**Then** 改用 `os.environ.get()`（環境變數在 mask 之前就存在），或用 key name matching，不要用 `!= "***"` value matching

**If** 在 Python 腳本中看到 `key != "***"` 或 `value == "***"`  
**Then** 這是 bug，改用 os.environ 或 key name matching
