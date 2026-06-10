# Cheap Model 5 分鐘 Quickstart

> 用途：用戶說「我想試試便宜 model」時，照著做就對了

---

## 步驟 1：確認當前設定（30 秒）

```bash
# 看主 session model
hermes config show | grep -A 1 "◆ Model"

# 看 delegation 設定（sub-agent 用什麼）
hermes config show | grep -A 1 delegation

# 看 .env 裡的 key
grep -E "MINIMAX|DEEPSEEK|ANTHROPIC" ~/.hermes/.env | sed -E 's/=.{8,}$/=<redacted>/'
```

**預期看到**：
- 主 session model: `MiniMax-M3`（旗艦）
- delegation: 空（子代理繼承主 session）
- `.env` 有 `MINIMAX_API_KEY` + `MINIMAX_BASE_URL`

---

## 步驟 2：選路徑（看任務本質）

| 如果你的任務... | 用這條路徑 |
|----------------|----------|
| 固定時間跑、不需要 AI | **路徑 A**：`no_agent=True` |
| 對話中臨時派出去的子代理 | **路徑 B**：`delegation.model` |
| 特定 cron job 需要 AI 介入 | **路徑 C**：cron job 自帶 `model` |

---

## 步驟 3A（路徑 A）：把 cron 改成 no_agent=True 跑 script

**為什麼**：零 LLM token 消耗，100% 省

```bash
# 1. 確認現有 cron job 設定
hermes cron list

# 2. 把任務寫成獨立 .sh 腳本
mkdir -p ~/.hermes/scripts/
cat > ~/.hermes/scripts/run_my_task.sh <<'EOF'
#!/bin/bash
# 你的任務：撈 RSS、查硬碟、跑 curl、查 log
# 不需要 LLM，直接 shell 處理
echo "$(date): 任務執行中..."
# ... 你的命令 ...
EOF
chmod +x ~/.hermes/scripts/run_my_task.sh

# 3. 改 jobs.json：手動編輯（不要用 hermes cron edit --script，會觸發 bug）
# 將 script 欄位改為：
#   "script": "run_my_task.sh"
#   "no_agent": true
#   "prompt": null

# 4. 驗證
bash ~/.hermes/scripts/run_my_task.sh
hermes cron list
```

**詳細 bug 與修法**：見 `~/.hermes/skills/devops/cron-job-health-monitor/SKILL.md` 與 metacognitive-learner skill 的 `hermes cron edit --script` bug 段落。

---

## 步驟 3B（路徑 B）：設定 delegation.model 給所有 sub-agent

**為什麼**：影響 `delegate_task` 派出去的所有子代理，一次設定全部

```bash
# 設定 cheap model 給 sub-agent
hermes config set delegation.model MiniMax-M2.7
hermes config set delegation.provider minimax

# 驗證
hermes config show | grep -A 1 delegation
# 應該看到：
# delegation:
#   model: MiniMax-M2.7
#   provider: minimax
```

**效果**：
- 主 session 仍用 M3
- 所有 `delegate_task` 派出去的子代理用 M2.7
- 預期節省 50-60%（依任務複雜度）

**注意**：
- 主 session 不能中途切換（要切必須 /reset）
- delegation 設定改完**不需要重啟 hermes**（config 動態讀取）

---

## 步驟 3C（路徑 C）：特定 cron job 帶 model 參數

**為什麼**：只影響該 cron job，其他不受影響

```bash
# 建立新 cron job 帶 model
hermes cron create \
  --name "rss-summary" \
  --schedule "0 9 * * *" \
  --prompt "總結昨天的 RSS 摘要，列前 5 條" \
  --model MiniMax-M2.7

# 或編輯現有（注意：hermes cron edit 有 bug，建議直接改 jobs.json）
```

---

## 步驟 4：監控效果

```bash
# 跑一段時間後看 token 用量
ls -lh ~/.hermes/logs/agent.log

# 對比 cheap tier vs 旗艦的 token 消耗
grep "tokens" ~/.hermes/logs/agent.log | tail -50
```

---

## 完整驗證 checklist

- [ ] `hermes config show` 顯示 delegation 已設為 M2.7
- [ ] 一個 cron job 跑成功，last_status = ok
- [ ] 24 小時後看 token 消耗對比
- [ ] 沒有 workflow compliance 問題（任務都正常完成）

---

## 退回（發現 cheap tier 效果不好）

```bash
# 退回設定
hermes config set delegation.model ""  # 空字串 = 繼承主 session
hermes config set delegation.provider ""

# 驗證
hermes config show | grep -A 1 delegation
# 應該看到：
# delegation:
#   model: ''
#   provider: ''
```

**If** 退回後還是問題
**Then** 該任務可能需要 M3/Opus，**不應該**硬切 cheap tier。
