# eval-sync 雙重故障（2026-06-08）

## 問題描述

`eval-sync` cron job 失敗，錯誤：
```
ERROR: AGENT_API_KEY not found in hermes-portal/.env.local
```

實際：`.env.local` 有 `AGENT_API_KEY=***`（3 字元 placeholder，不是真實 key）。

## 故障鏈（兩個獨立 bug）

### Bug 1：Python startswith() 語法錯誤

`sync_evaluations.py` 第 32 行（0-indexed 31）：
```python
# 錯誤（❌）— 缺少 ) 關閉第一個 startswith：
if line.startswith("AGENT_API_KEY=*** or line.startswith("export AGENT_API_KEY=*** 正確（✅）：
if line.startswith("AGENT_API_KEY=*** or line.startswith("export AGENT_API_KEY=***")
```

Python 把「or line.startswith("export...」視為同一個字串參數的延續，因為缺少 `)` 關閉第一個 `startswith(`。結果：`SyntaxError: unterminated string literal (detected at line 32, column 99)`。

**受影響**：`get_api_key()` 返回 `None` → script 在第 96 行 `sys.exit(1)`。

---

### Bug 2：Vercel env pull 把 AGENT_API_KEY mask 成 `***`

**症狀**：`.env.local` 有 `AGENT_API_KEY=***`（3 字元），長度 < 10。

**根因**：`vercel env pull .env.local` 會把所有環境變數的**實際值**以 `***` 遮蔽。這是**不可逆的遮蔽**。

**後果**：即使 Bug 1 修復，`get_api_key()` 會讀到 `***`（3 字元 placeholder），嘗試用它當 Bearer token → `401 Unauthorized`。

**再生修復**：
1. 到 Vercel Dashboard → Settings → Environment Variables → 找到 `AGENT_API_KEY` → 刪除
2. 重新 `Add` 一個新值（用 `openssl rand -hex 32` 生成）
3. **不要用 `vercel env pull`**（會再次 mask）— 直接在 Vercel Dashboard 寫入
4. 手動更新 `~/.hermes/.env` 或 `hermes-portal/.env.local` 寫入新 key

**預防**：
- **永遠不要對 `AGENT_API_KEY` 使用 `vercel env pull`**
- 若 key 被 mask → 必須在 Vercel Dashboard 重建，無法從本地恢復

---

## 驗證

```bash
# 1. 檢查 Python 語法
python3 -m py_compile ~/.hermes/scripts/sync_evaluations.py
# 預期：無輸出（exit 0）

# 2. 檢查 key 長度（真實 key 約 40+ chars，masked 是 3 chars "***"）
grep AGENT_API_KEY ~/.hermes/.env ~/.hermes/permanent-projects/hermes-portal/.env.local 2>/dev/null
# 預期：長度 > 20

# 3. 實際執行
python3 ~/.hermes/scripts/sync_evaluations.py
# 預期：exit 0 + "取得 N 筆評價"
```

---

## 修復記事

- **2026-06-08 06:xx**：嘗試用 sed、Python byte editing、restore from backup 修復，全部失敗
- 備份檔也有同樣 bug（sibling subagent 之前的修復不完整）
- 修復嘗試花費 45+ 分鐘，導致 Phase 1-3 完全沒執行
- 修復後更糟：byte-level 插入位置算錯，`)` 跑到 `or` 前面，變成 `startswith("AGENT_API_KEY=*** )or...`

**結論**：`sync_evaluations.py` 需要從源頭重建（main session 介入）。