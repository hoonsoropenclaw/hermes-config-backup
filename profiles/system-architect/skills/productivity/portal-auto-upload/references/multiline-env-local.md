# 多行 .env.local 陷阱詳細記錄

> 建立日期：2026-06-05
> 觸發 skill：portal-401-troubleshoot（v1.2.0）
> 關聯 cron 失敗：eval-sync

## 觸發情境

`eval-sync` cron 從 `sync_evaluations.py` 內呼叫 `get_api_key()` 讀 `/home/hoonsoropenclaw/hermes-portal/.env.local` 內的 `AGENT_API_KEY`，但送出的 API 請求持續回 401。

**使用者反應**：「但 `grep AGENT_API_KEY .env.local` 明明看得到正確的值啊？」

## 根因分析

`/home/hoonsoropenclaw/hermes-portal/.env.local` 內有**多行** `AGENT_API_KEY=*** (輸出 `grep -c` 顯示 2 行以上)。可能原因：
1. Vercel CLI 部署時，自動把 `.env.local` 的值上傳到 Vercel Dashboard 後，又把 Dashboard 的值同步回 `.env.local`（造成重複）
2. 之前手動 `echo "AGENT_API_KEY=xxx" >> .env.local` 追加，沒注意到已經有一行
3. Supabase migration 自動加入環境變數行

`sync_evaluations.py` 的 `get_api_key()`：
```python
result = subprocess.run(
    ["grep", "^AGENT_API_KEY=*** path"],
    capture_output=True, text=True
)
return result.stdout.strip().split("=", 1)[1]  # ← BUG
```

`grep` 會回傳所有匹配的行（不是只有第一個），`.split("=", 1)[1]` 取最後一個匹配的值。

## 驗證

```bash
$ grep -c "^AGENT_API_KEY=*** /home/hoonsoropenclaw/hermes-portal/.env.local
2
$ grep "^AGENT_API_KEY=*** /home/hoonsoropenclaw/hermes-portal/.env.local
AGENT_API_KEY=***
AGENT_API_KEY=***
```

## 修復方式

### 方案 A：用 `awk` 取代 `grep | cut`（推薦，script 端最簡）

```bash
API_KEY=*** -F= '/^AGENT_API_KEY=*** $2; exit}' /home/hoonsoropenclaw/hermes-portal/.env.local)
```

特性：`exit` 讓 awk 處理第一個匹配就停止。

### 方案 B：Python 用 `re.search` + MULTILINE flag

```python
import re
from pathlib import Path
content = Path("/home/hoonsoropenclaw/hermes-portal/.env.local").read_text()
match = re.search(r"^AGENT_API_KEY=*** content, re.MULTILINE)
api_key = match.group(1).strip() if match else None
```

### 方案 C：用 `dotenv` 或 `python-dotenv` 套件

```python
from dotenv import dotenv_values
config = dotenv_values("/home/hoonsoropenclaw/hermes-portal/.env.local")
api_key = config.get("AGENT_API_KEY")
```

特性：自動處理多行、跳過註解。但要安裝 `python-dotenv`（可能未在 hermes 環境中）。

### 方案 D：清掉 `.env.local` 的重複行

```bash
# 用 awk 內建去重（保留第一個出現）
awk -F= '!seen[$1]++' /home/hoonsoropenclaw/hermes-portal/.env.local > /tmp/env.tmp
mv /tmp/env.tmp /home/hoonsoropenclaw/hermes-portal/.env.local
```

## 永久性修復

無論選 A/B/C 哪個方案，**長期應把 .env.local 維持單行單 key**。建議：

1. 部署前先 `grep -c "^AGENT_API_KEY=*** 若 > 1 則報錯停止部署
2. 部署完成後再 grep 一次驗證
3. 寫進 CI/部署 SOP 作為 pre-deploy gate

## 教訓

> 任何「從 .env* 檔讀單一 key」的腳本，**永遠假設檔案可能含多行同名變數**，用「取第一個匹配」的工具（awk / re.MULTILINE / dotenv_values），不要用「回傳所有匹配」的工具（grep -c, cat, head -1）。

## 踩坑後的偵測訊號

如果你看到 cron job 失敗有 `HTTP 401`，且本機 `.env*` 檔**有**那個 key，但 curl 直接打 API 也 401——**先懷疑本地讀取有 bug，再懷疑 key 過期**。

驗證：手動跑那個讀取函式，印出實際送出的 key 的前 4 個字 + 長度，跟預期值比對。

```python
print(f"key starts: {api_key[:4]}... (len={len(api_key)})")
# 期望: key starts: hms_... (len=33)
# 若顯示: key starts: ... (len=0) → 抓到空字串 → 多行 bug 確認
```
