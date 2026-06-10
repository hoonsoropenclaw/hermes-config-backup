# 赫米斯全狀態備份 SOP（2026-06-06 確立）

跨機器還原赫米斯全部設定的標準 SOP，含 3 個目標：本地 tar.gz、rclone 加密上傳 Google Drive、GitHub 公開 repo 推送。

## 為什麼需要這個

赫米斯的設定散佈在 6 個地方（config.yaml、cron/jobs.json、memories/*.md、skills/、scripts/、kanban.db），還有 12 個 API key 在 .env。異機還原時**手動重來一次會花 4-8 小時**且容易漏。備份 SOP 目標：

- 30 秒決定備份目標、3 分鐘內完成單次備份
- 自動 redact 已知洩漏 token（2026-06-05 GH013 事件教訓）
- 異機還原時跑一個 .sh 就能還原 80%、其餘 20% 是 .env 申請 + 外部 skills 重裝

## 備份架構（決策已定，不要改）

```
3 個目標:
├── 本地: ~/.hermes/backups/hermes_backup_<YYYYMMDD_HHMMSS>.tar.gz
├── Google Drive: rclone crypt_hermes:hermes_backup_<YYYYMMDD_HHMMSS>/
└── GitHub: hoonsoropenclaw/hermes-config-backup (PUBLIC)
```

3 個目標互補：
- 本地：最快、最近 7 天隨時可拿
- Google Drive：加密、跨機器、即使 N100 整台掛了也能從雲端還原
- GitHub：公開版（不含 .env）、任何人都能 clone、版本控制天然支援

## 備份內容分層（依你的環境）

**進備份**（重點）：
- `config.yaml`、`cron/jobs.json`、`.env` 範本（key 全部 *** 化）
- 7 個核心 MD（USER/MEMORY/SOUL/AGENTS/IDENTITY/HEARTBEAT/TOOLS）
- 6 個自建 skill：metacognitive-learner、persistent-subagent、hermes-agent、hermes-tier-router、trial-and-error、alt-token-secrets-layout
- 全部 Python/Shell scripts
- `kanban.db`
- `INSTALLED_MANIFEST.md`（列所有外部 skill 安裝來源）

**不進備份**（明確排除）：
- `.env`（12 個明文 API key）
- `hermes-agent/`（1.1 GB 源碼，重新 install）
- `state.db`（169 MB session store）
- `sparc-methodology/`（103 MB 外部 skill）
- `venv/`、`cache/`、`logs/`、`lsp/`、`bin/`（衍生）
- `sessions/`（state.db 附屬）
- `models_dev_cache.json`（可重新生成）
- GPG 加密 token 目錄（`~/.config/hermes/alt_gh_tokens/`、`~/.local/share/hermes/secrets/`）

## Secret 掃描：4 道防線（不可省任何一道）

| 階段 | 工具 | 攔截對象 |
|---|---|---|
| 複製到 staging 後 | `perl` regex in-place replace | 任何 `vcp_/ghp_/sk-/hms_/gho_/glpat-` 開頭 20+ 字元 |
| 打包 tar 前 | `grep -rE` | 上述 regex 沒抓到的邊角 |
| 解 tar 後再掃 | `tar -xz \| grep` | 打包後又跑進去 |
| commit 前 | `grep -rE` | 確保 GitHub 推送前 100% 乾淨 |

**核心 regex**（直接 copy）：
```bash
SECRET_REGEX='(vcp_|ghp_|sk-|hms_|gho_|glpat-)[A-Za-z0-9_-]{20,}'
```

**為什麼要 4 道**：2026-06-05 sync_md_files.py 漏抓 vcp_ token 推到 GitHub、觸發 GH013 push protection 失敗 4+ 天。單一掃描**一定會漏**（檔案格式、編碼、編譯後的二進位都可能藏 token）。

## 已知坑（2026-06-06 真實踩過）

1. **Bash array key 用 `]` 結尾會 syntax error**
   - 寫法：`["vcp_***REDACTED***]` ← 這個 `]` 沒對應 `[` 開頭，bash 直接報 `unexpected EOF`
   - 修法：不要維護 REDACT_MAP 陣列，直接用萬用 regex

2. **gh repo create 預設是 private 不是 public**
   - 第一次跑 `gh repo create --public` 失敗 → fallback 到 `git init` → push 上去仍是 private
   - 修法：建完 repo 後立刻 `gh repo edit --visibility public` 確認

3. **hermes cron edit --script 對 no_agent jobs 有 bug**
   - 不要用 `hermes cron create --script`，手動編輯 jobs.json（prompt 設 null、script 設檔名）

4. **rsync / gh 等工具沒預裝會讓 script 中途失敗**
   - 在 script 開頭預檢 `for tool in rclone git python3 tar rsync gh; do command -v $tool || exit 1; done`

5. **tar 內含真實 token 的事件教訓檔**（最危險的）
   - 3 個 trial-and-error references 檔案內**記錄了真實 vcp_ token 當案例**
   - 這些檔案**必須備份**（是 L3 教訓），但 token 字串**必須 redact**
   - 解法：先複製、再用 perl 全檔 in-place replace、最後 grep 驗證

## 異機還原前必做

1. **關掉舊主機的 hermes-gateway**：`pkill -f hermes-gateway`
2. **Telegram session 一次只能掛一台機器**，別同時開兩台
3. **rclone config 必須另外保留**（不在備份範圍）—— 這是設計權衡，避免加密密鑰外洩

## 還原後必做

1. 從 .env 範本看需要哪些 API key，去各平台申請
2. 用 INSTALLED_MANIFEST.md 重裝外部 skills
3. 從舊機器拷貝 GPG 加密目錄到新機器對應位置
4. `hermes gateway run` 啟動、Telegram 測試
5. `hermes cron list` 確認 7 個 jobs 都有
6. 跑 `backup_hermes.sh` 一次，沒報錯就代表還原完成

## If→Then 規則

- **If** 接到任務「赫米斯備份」**Then** 參考本 SOP，不要從零設計
- **If** 備份 script 報「secret pattern」**Then** 不要繞過掃描，先看是 trial-and-error 教訓檔漏 redact、修 regex
- **If** 還原後 Telegram bot 沒回應 **Then** 99% 是兩台機器 gateway 同時搶，先 pkill 舊主機
- **If** state.db 不見了 **Then** 這是設計的，重要對話已在 trial-and-error 跟 MEMORY.md 結構化
- **If** deepseek 沒接上 **Then** 已知問題，hermes 內建沒 deepseek provider，見 hermes-tier-router skill

## 參考檔案

- `~/.hermes/scripts/backup_hermes.sh` — 12 KB 備份主腳本
- `~/.hermes/scripts/restore_hermes.sh` — 7.6 KB 異機還原腳本
- `~/.hermes/docs/RESTORE.md` — 5.9 KB 完整還原 SOP
- `metacognitive-learner/references/provider-verify-pitfalls.md` — Provider 設定陷阱（備份系統本身也用了 4 道 secret 掃描）

## 跨分類關聯

- 6/5 GH013 事件 → [[hermes-internal#2026-06-05 sync 腳本把 vcp_ token 推到公開 GitHub]]
- Bash array 語法坑 → [[hermes-internal#bash array key 含 ] 會 syntax error]]
- gh repo 預設 private → [[hermes-internal#gh repo create 預設是 private 不是 public]]
- MEMORY.md 清理後搬家 → [[hermes-internal#技能 L3 抽象教訓分流決策樹]]
