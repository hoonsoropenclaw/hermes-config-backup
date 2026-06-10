# 赫米斯異機還原 SOP

> **寫於 2026-06-06**，赫米斯全狀態備份 repo 的官方還原手冊。
> 適用於：新裝機、災難復原、機器移轉。

## 0. 環境需求

新機器必須有：

- [ ] Linux 主機（與原機同 OS family，推薦 Ubuntu 24.04）
- [ ] Python 3.11+
- [ ] `rclone` 安裝：`sudo apt install rclone` 或 `brew install rclone`
- [ ] `git`、`gh` CLI
- [ ] 已 `gh auth login`（GitHub 帳號 `hoonsoropenclaw`）
- [ ] rclone config 檔在 `~/documents/rclone.conf`（**這份必須另外保留**）

## 1. 三條還原路徑（選一條）

### 路徑 A：從本地 tar.gz 還原（最快）
```bash
# 把備份 tar.gz 放到新機器上
scp old_machine:~/.hermes/backups/hermes_backup_<timestamp>.tar.gz ~/
bash ~/hermes_backup_*.tar.gz  # 還原
bash ~/restore_hermes.sh ~/hermes_backup_*.tar.gz
```

### 路徑 B：從 Google Drive 加密備份還原（推薦）
```bash
# 1. 把 rclone config 放到新機器
scp old_machine:~/documents/rclone.conf ~/documents/
chmod 600 ~/documents/rclone.conf

# 2. 跑 restore（自動找最新備份）
bash restore_hermes.sh
```

### 路徑 C：從 GitHub 公開 repo 還原（最慢但最方便）
```bash
git clone https://github.com/hoonsoropenclaw/hermes-config-backup.git
bash hermes-config-backup/scripts/restore_hermes.sh
```

## 2. 還原後必做的 7 件事

### 2.1 重新申請 API keys（**最重要**）
看 `~/.hermes/.env` 範本（restore 會自動建好），列了需要哪些 key：
- MINIMAX_API_KEY
- DEEPSEEK_API_KEY
- OPENAI_API_KEY
- ALPHA_VANTAGE_API_KEY
- FRED_API_KEY
- FINNHUB_API_KEY
- TWELVE_DATA_API_KEY
- TAVILY_API_KEY
- OLLAMA_WEB_SEARCH_API_KEY
- TELEGRAM_BOT_TOKEN
- （其他從 env-template 看）

去各平台申請，寫進 `~/.hermes/.env`（mode 0600）

### 2.2 重裝外部 skills
看 `~/.hermes/skills/INSTALLED_MANIFEST.md` 列出所有外部 skill 來源。
範例：
```bash
hermes skills install https://github.com/anthropics/knowledge-work-plugins
hermes skills install https://github.com/Leonxlnx/taste-skill
# 依 INSTALLED_MANIFEST.md 跑
```

### 2.3 還原 GPG 加密的備用 token
備用 GitHub PAT 走 GPG 加密儲存，**沒在 backup 範圍**。
從舊機器拷貝：
```bash
scp -r old_machine:~/.config/hermes/alt_gh_tokens ~/~/.config/hermes/
scp -r old_machine:~/.local/share/hermes/secrets ~/~/.local/share/hermes/
```
新機器要：
```bash
# 1. 確認 GPG 已裝、gpg-agent 跑得起來
gpg --list-secret-keys

# 2. 測試解密能跑
echo "<passphrase>" | gpg --batch --passphrase-fd 0 --decrypt ~/.config/hermes/alt_gh_tokens/hoonsor.gpg
```

### 2.4 安裝 hermes-agent 源碼
restore 腳本會**自動跑** hermes install 指令。
如果失敗，手動跑：
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### 2.5 啟動 hermes-gateway
**⚠️ 重要：先確認舊主機的 gateway 已關閉**
```bash
# 舊主機上
pkill -f hermes-gateway
systemctl --user stop hermes-gateway  # 如果用 systemd
```

新主機上：
```bash
hermes gateway run
# 或背景跑
hermes gateway install
hermes gateway start
```

### 2.6 Telegram session 測試
從 Telegram 給你的 bot 發一則訊息，看有沒有回應。
- 有回應 → 還原成功
- 沒回應 → 看 `~/.hermes/logs/gateway.log`

### 2.7 跑 cron job 健康檢查
```bash
hermes cron list --all
# 應該看到 6 個 jobs（4 個 no-agent script + 2 個 LLM-driven）

# 跑一個 LLM-driven job 確認
hermes cron run metacognitive-learner-24h
# 或
hermes cron run 6edfe1507888
```

## 3. 常見問題

### Q1：還原後 Telegram bot 沒回應？
**A**：99% 是兩台機器 gateway 同時在搶。檢查：
```bash
# 舊主機
ps aux | grep hermes-gateway | grep -v grep
# 看到就 kill
pkill -f hermes-gateway
```

### Q2：deepseek 沒接上？
**A**：hermes-agent 內建沒 deepseek provider。本機會 fallback 到 minimax。
詳細處理見 `~/.hermes/skills/trial-and-error/references/by-category/hermes-config-tuning.md`。

### Q3：某些 skill 找不到？
**A**：看 `INSTALLED_MANIFEST.md`，重裝對應外部 skill。restore 腳本只還原自建的 6 個 skill：
- metacognitive-learner
- persistent-subagent
- hermes-agent
- hermes-tier-router
- trial-and-error
- alt-token-secrets-layout

外部 skill（sparc-methodology、anthropic-*、taste-skill 等）**不會**自動還原。

### Q4：state.db（169 MB session store）不見了？
**A**：這是設計的，不備份。state.db 是 session 累積，異機還原後從零開始。
**重要對話已結構化在 trial-and-error skill 跟 MEMORY.md**，不會真的丟失。

### Q5：MEMORY.md 內容比預期少？
**A**：可能看到的是 2026-06-06 清理後版本（6 KB）。
完整歷史可用 `session_search` 撈，或從備份機器的 `~/.hermes/memories/MEMORY.md.bak.*` 找回。

### Q6：怎麼驗證整個備份循環是健康的？
**A**：跑一次 `backup_hermes.sh` 確認：
- 本地 tar.gz 產出
- Google Drive 上有對應資料夾（檔名是亂碼 = 加密生效）
- GitHub repo commit 推送
- 沒看到「❌ ABORT: secret pattern」

## 4. 還原驗證清單（建議跑完逐項打勾）

- [ ] `hermes --version` 顯示版本
- [ ] `hermes config` 顯示 model = MiniMax-M3、provider = minimax
- [ ] `ls ~/.hermes/memories/` 有 7 個 MD
- [ ] `hermes cron list` 有 6 個 jobs
- [ ] `ls ~/.hermes/skills/trial-and-error/references/by-category/` 有 8 個分類檔
- [ ] `cat ~/.hermes/.env` 有 API keys（要手動填）
- [ ] Telegram bot 從訊息有回應
- [ ] 跑一次 `backup_hermes.sh` 沒報錯
- [ ] 從備份 repo 看 commit log 有今天的紀錄

## 5. 緊急聯絡

備份/還原有問題：
1. 看 `~/.hermes/logs/backup_<timestamp>.log`
2. 看 trial-and-error `hermes-config-tuning.md` 跟 `hermes-internal.md`
3. 赫米斯主 session 還在的話直接問
