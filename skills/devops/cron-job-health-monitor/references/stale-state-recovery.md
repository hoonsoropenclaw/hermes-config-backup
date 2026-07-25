# Stale last_status Recovery SOP

> 2026-06-11 從 cron-job-health-monitor 觀察歸納的 `last_status` 解耦問題
> 對應 SKILL.md「類型 J：Stale last_error 排除 SOP」段

## 為什麼這是個獨立檔

`last_status` 跟 jobs.json 修復狀態**完全解耦**——這是赫米斯 24/7 監控裡最容易誤判的陷阱。看到 `last_status: error` 直覺反應是「又壞了、要修」，但 80% 情況是「之前修對了、只是 last_status 還沒被 cron tick 翻」。

獨立這個檔是因為：
- **這是 class-level knowledge**（任何 cron 修復 workflow 都該先排除 stale state）
- **不是 1 個 session 的小事**（過去 3 個 cycle 我們反覆觸發緊急修復、浪費 30+ 分鐘）
- **要可重複執行**（未來 cycle 一定會再遇到）

## 完整排除流程（4 步）

### Step 1：手動跑 script 驗證邏輯

```bash
# 從 / 模擬 cron 的無 cwd 環境
cd / && python3 /home/hoonsoropenclaw/.hermes/scripts/<script_name>.py
# 或
cd / && bash /home/hoonsoropenclaw/.hermes/scripts/<script_name>.sh

# 紀錄 exit code
echo "exit: $?"
```

**判斷**：
- exit 0 → 進入 Step 2
- exit 1 → 這是真實 bug、走 SKILL.md A-I 決策樹

### Step 2：交叉驗證 jobs.json

```bash
python3 -c "
import json
d = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name') == '<job_name>':
        print('id:', j.get('id'))
        print('script:', j.get('script'))
        print('prompt:', j.get('prompt'))
        print('timeout_seconds:', j.get('timeout_seconds'))
        print('no_agent:', j.get('no_agent'))
        print('last_error:', j.get('last_error'))
"
```

**判斷**：
- `prompt` 為 `null` + `script` 為純檔名 + `no_agent: true` + timeout 合理 → jobs.json 已修對
- 如果有 trial-and-error 建議值（ex: `timeout_seconds: 3600`）→ 比對 jobs.json 當前值是否一致

**全部一致 → 這是 stale state、不是新 bug**（進入 Step 3）

### Step 3：強迫 cron 翻 last_status

```bash
# 1. 立即 schedule 到下一個 tick
hermes cron run <job_name>

# 2. 等 30-60 秒讓 scheduler tick
sleep 30

# 3. 驗證 last_status 翻成 ok
python3 -c "
import json
d = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name') == '<job_name>':
        print('last_status:', j.get('last_status'))
        print('last_run_at:', j.get('last_run_at'))
        print('last_error:', j.get('last_error'))
"

# 4. 看 cron output dir
ls -lat /home/hoonsoropenclaw/.hermes/cron/output/<job_id>/
```

**判斷**：
- `last_status: ok` + `last_error: (none)` + `last_run_at` 是剛剛 → 修復完成
- `last_status: error` + 新 `last_error` → 有新問題、看錯誤訊息重來

### Step 4：若仍失敗（hermes cron run 也沒翻）

1. 確認 `hermes-gateway` 在 active：
   ```bash
   systemctl status hermes-gateway --no-pager 2>&1 | grep "Active:"
   ```
2. 確認 `mark_job_run()` 真的會跑（看 scheduler.py line 2129）：
   ```bash
   grep -n "mark_job_run\|deliver_content" /home/hoonsoropenclaw/.hermes/hermes-agent/cron/scheduler.py
   ```
3. 確認 jobs.json 沒被任何 process 鎖住：
   ```bash
   lsof /home/hoonsoropenclaw/.hermes/cron/jobs.json
   ```

## 為什麼「等 cron 自然排程」是反模式

- cron 排程頻率：backup job 大多 daily（02:00/03:00/04:00）
- 從「修對 jobs.json」到「last_status 自動翻成 ok」**最長 24 小時延遲**
- 24 小時內 metacognitive-learner 會觸發 12 次（每 2 小時一次）、每次都看到 stale error → **12 個 cycle 重複誤判**
- 立即 `hermes cron run` + `hermes cron tick` → 30 秒內翻完

## 觀察記錄（2026-06-11 9:00~11:53 連續 3 cycle）

| Cycle | 看到的 last_error | 真實狀態 | 浪費時間 |
|-------|------------------|----------|----------|
| 09:00 | `Script exited with code 1` (rsync mkdir) | jobs.json 06:53 已修、v4.sh 07:12 已加 mkdir | 15 min（手動跑 + 驗證） |
| 09:30 | 同上 | 同上 | 5 min（已知道路徑） |
| 10:50 | 同上 | 同上 | 10 min（再次驗證） |
| 11:53 | 還 stale | **直接 `hermes cron run` + `hermes cron tick` 一鍵翻成 ok** | 1 min |

**教訓**：3 個 cycle 浪費了 30+ 分鐘做手動驗證、其實只需 1 個 `hermes cron run` 指令就能翻。

## 「強迫翻轉」的兩種使用時機

1. **jobs.json 已被手動修對**（上面描述的場景）
2. **想驗證修復後 cron 真的能跑**（不需要等明天 02:00）

兩者都用同樣的指令（`hermes cron run` + `hermes cron tick`）。

## 相關條目

- SKILL.md「類型 J」段：本檔的摘要版
- SKILL.md「驗證修復成功」段：通用 cron 修復驗證 SOP
- `metacognitive-learner` Phase 1.5 段：cron health 掃描的觸發場景
- `trial-and-error/references/by-category/hermes-internal.md`「`last_status` 跟 jobs.json 修復狀態完全解耦」條目：今天 session 的歸納
