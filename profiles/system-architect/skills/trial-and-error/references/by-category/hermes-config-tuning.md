# hermes-config-tuning（赫米斯配置調校試誤）

赫米斯自己（不是人）做配置調校時踩過的坑、驗證過的捷徑。
Sub-agent 派工、cron 排程、tier routing 相關的設定問題都收這裡。

---

## 配置調校三層決策（2026-06-06 確立）

赫米斯接到「優化 LLM token 消耗」任務時的標準動作順序：

### Layer 1：先看 cron jobs 健康度（不消耗 LLM）
- `hermes cron list` 找出 LLM-driven 的 job
- 預設假設：所有 cron job 沒指定 model → 繼承主 session 設定
- **If** LLM-driven cron > 1 個 **Then** 改用「per-job model override」

### Layer 2：全域 delegation.model 設便宜 model（單一動作）
- `hermes config set delegation.model MiniMax-M2.7`（或對應 cheap tier model）
- 所有 `delegate_task` 不指定 model 的 sub-agent 自動走便宜路徑
- 預估省 30-50% tokens，sub-agent 工作品質不打折

### Layer 3：tier router skill 給赫米斯主 session 自己看（半自動）
- 寫一份「任務難度 → model」對照表 skill（見 `hermes-tier-router`）
- 赫米斯在 dispatch sub-agent **前**讀 skill、自己決定要不要明確帶 `model=` 參數
- **重要限制**：赫米斯架構不支援「sub-agent 不指定 model 時自動依難度選」——這層繼承邏輯是 hermes 核心寫死的
- 實作是「我每次 dispatch 前跑一次決策」，不是「不指定就自動」

---

## Sub-agent 預設 model 繼承機制

**事實**（2026-06-06 驗證）：
- `delegate_task` 不帶 `model` 參數時，sub-agent 繼承 `delegation.model` 全域設定
- 驗證指令：跑一個 sub-agent 跑 "hello world" → 4.95 秒完成、model 顯示 `MiniMax-M2.7`
- **沒有**「不指定 model → 自動依任務難度切」這個機制
- 真要做自動切，必須在主 session dispatch 前明確帶 `model=` 參數

## Model 智力基準（用於 tier router 決策）

### 主用榜：Artificial Analysis Intelligence Index v4.0
- URL: https://artificialanalysis.ai/
- 包含 10 個 benchmark 複合指數（GDPval-AA、𝜏²-Bench、Terminal-Bench Hard、SciCode、AA-LCR、AA-Omniscience、IFBench、Humanity's Last Exam、GPQA Diamond、CritPt）
- 532 個 models 評比、持續更新
- **If** 給 LLM 做智力排序依據 **Then** 引用這個榜的分數

### 輔助榜：LLM-Stats Leaderboard
- URL: https://llm-stats.com
- 302+ models、複合分數（intelligence + speed + price）
- 適合看「成本/品質比」最佳解

### 持續更新機制
- 這兩個榜都不是 API 化、可程式查詢的
- 赫米斯可定期用 `web_search` 抓最新榜、寫回 `hermes-tier-router` skill 內的「當前快照」
- **If** 對 tier 決策的智力排序有疑問 **Then** 重新跑 `web_search` 查最新榜

## 已知 model 智力排序（2026-06-06 快照）

| 排名 | Model | Provider | Intelligence Index | 用途 |
|------|-------|----------|-------------------|------|
| 1 | Claude Opus 4.8 | Anthropic | 67.9 | frontier reasoning |
| 2 | GPT-5.5 | OpenAI | 62.9 | frontier general |
| 3 | Claude Opus 4.7 | Anthropic | 60.5 | frontier reasoning |
| 4 | GPT-5.4 | OpenAI | 59.9 | general |
| 5 | Gemini 3.5 Flash | Google | 59.4 | 速度+品質 |
| 6 | **MiniMax M3** | minimax | ~56 (SWE-Bench Pro 59%) | **premium tier** |
| 7 | **MiniMax M2.7** | minimax | 較低 (SWE-Bench Pro 56.2%) | **standard tier** |
| 8 | **DeepSeek V3.2 (Reasoning)** | DeepSeek | composite 比 M2.7 高 6-8 分 | **cheap but strong reasoning** |
| 9 | Kimi K2.6 | Moonshot | 57.3 (open weights) | open weights 高分 |
| 10 | Qwen3.7 Max | Alibaba | 56.4 | 高 CP 值 |

**Key 觀察**：
- M3 vs M2.7 差 3 分 SWE-Bench Pro（59% vs 56.2%），但 context 從 200K 升到 1M
- DeepSeek V3.2 Reasoning 在 reasoning 類任務贏 M2.7，但在 coding agentic 任務未必
- M2.7 在 composite 智力榜比 M3 低 6-8 分 → tier 區分有效

## 改 `metacognitive-learner-24h` cron model（M3 → M2.7）

**症狀**: 每 120 分鐘的後設認知 cycle 一直用 M3（繼承主 session），太貴
**根因**: cron job 沒指定 model → 繼承主 session 預設
**解法**: 編輯 `~/.hermes/cron/jobs.json`，對 LLM-driven job 加 `model` 跟 `provider` 欄位
**備份**: 改動前先 `cp jobs.json jobs.json.bak.<timestamp>`
**驗證**: `grep -B 1 -A 8 'metacognitive-learner-24h' jobs.json` 確認 `model` 跟 `provider` 寫入
**預估效益**: 省 30-50% tokens、cycle 品質不打折（SOP 服從是格式問題不是智商問題）

**注意**:
- 改 jobs.json 是手動操作，**不**走 `hermes cron edit`（那個 CLI 對 no_agent jobs 有 bug）
- 5 個 no_agent script jobs 不用改（零 token 消耗）

## DeepSeek provider 接入（2026-06-06 完成）

**症狀**: 想把 deepseek-v3.2 加進 tier router 當 cheap tier
**根因**: 預設 .env 沒有 `DEEPSEEK_API_KEY`
**解法**:
1. 申請 DeepSeek API key（https://platform.deepseek.com）
2. 寫進 `~/.hermes/.env`：
   ```
   DEEPSEEK_API_KEY=***   DEEPSEEK_BASE_URL=https://api.deepseek.com
   ```
3. 測試：`hermes chat -q "ping" --provider deepseek --model deepseek-chat`
4. 成功（6 秒回 pong）後可在 `delegate_task(goal=..., model="deepseek-chat", provider="deepseek")` 用

**Hermes 內建 deepseek provider**:
- provider 字串: `deepseek`
- model 字串: `deepseek-chat`（對應 DeepSeek V3 chat model）
- 不需 custom base_url 設定，用 .env 的 `DEEPSEEK_BASE_URL` 就夠

---

## Rule 11：v3 限制催生 v4 雙雲端（2026-06-07 確立）

- Drive API 配額 840K/分鐘對 1 萬+ 小檔不友善（v3 半成品）
- GitHub 走 git protocol、沒有 Drive 配額問題
- 雙雲端分工：GitHub 管文字、小檔；Drive 管加密大檔、secrets
- 異機還原時間從 58 分鐘（v2 tar.gz）→ 5 分鐘（v4 Tier 1）

## Rule 12：`rclone purge remote:` 會刪整個 remote root、不是清垃圾桶（2026-06-07 親身踩到）

**症狀**：想清 Drive 垃圾桶、跑 `rclone purge crypt_hermes:` → **整個 Drive remote 內所有東西都移到垃圾桶**（不是只有垃圾桶的東西）

**根因**：
- `rclone purge <path>` = 永久刪 `<path>` 及其所有子目錄
- 對 crypt remote 來說、purge root = purge 整個 wrapper 後面的東西
- 「垃圾桶」是 Drive 特性、不是 rclone 操作
- 正確清垃圾桶：`rclone delete remote: --drive-trashed-only --drive-use-trash=false` 或直接用 Google Drive UI

**If** 想清 Drive 垃圾桶 **Then** 永遠用 `--drive-trashed-only` + `--drive-use-trash=false`、或 Drive UI
**Then 不要** 用 `rclone purge remote:`（會砍整個 root）
**Then 不要** 假設 `purge` = 「清垃圾桶」（這是兩個完全不同的操作）

**預防**：
- 任何 rclone 危險操作前先 `rclone ls remote:path` 看會影響什麼
- 對重要 remote 先設個測試子目錄試跑

## Rule 13：Drive 對「加密大檔」不友善、明文 Drive + client-side GPG 才是對的（2026-06-07 實測）

**症狀**：
- 想用 `rclone crypt` 把 88MB 加密檔推到 Drive
- 跑了 18+ 分鐘、Transferring 顯示 100%、但 Drive 上實際沒寫入
- 嘗試 3 次（rclone copy、rclone copyto）、全部失敗或卡住

**根因**：
- rclone crypt 是 stream-encrypt + 上傳、對 88MB 單一大檔在 Drive 上會：
  - 整檔下載到本地暫存 → 整檔加密 → 分 chunk upload
  - 過程中任何一步失敗要重來整個
  - Drive API 對 88MB 加密單檔的「單一大檔 upload」配額會 throttle
- 實測：rclone crypt 88MB = 18 分鐘失敗 3 次、rclone copy 明文 88MB = 1 分 46 秒成功

**正確做法**：
1. **明文 Drive**（用 `drive:` backend、不用 crypt wrapper）直接傳 `.gpg` 檔案
2. **client-side GPG 加密**（在本地用 gpg 命令加密好、Drive 上看到的就是 .gpg）
3. Drive 只負責儲存、加密在本地完成

```bash
# 正確 workflow
gpg --batch --yes --pinentry-mode loopback \
  --passphrase-file /path/to/passphrase \
  --symmetric --cipher-algo AES256 \
  --s2k-mode 3 --s2k-count 65011792 \
  --output secrets.tar.gpg secrets.tar

# Drive 用明文（rclone copy 1m46s for 88MB）
rclone copy secrets.tar.gpg drive:hermes-backup/secrets/ --progress
```

**If** 想備份 secrets 到 Drive **Then** 用明文 Drive + client-side GPG、**不要**用 rclone crypt layer
**Then** Drive 上看到的是 .gpg 檔、不能用 Drive UI 直接看內容（要 client 解密）
**Then** 加密 + 上傳兩步分離、可以各自 retry

**If→Then 對比表**：

| 方案 | 88MB 加密 | 88MB 明文 | 1 萬小檔 |
|------|----------|----------|---------|
| rclone crypt + Drive | 18 分（失敗）| 不適用 | 必爆 throttle |
| rclone copy 明文 Drive + 預先加密 | 1 分 46 秒 | 秒傳 | 必爆 |
| 兩者結合（建議） | ✅ | ✅ | ⚠️（避免）|

## Rule 14：hermes cron 對 no_agent script 不帶參數、必須用 wrapper script（2026-06-07 確認）

**症狀**：想把 `hermes-restore-v4.sh tier1 --target /tmp/verify` 加進 cron 跑、hermes cron 寫進 jobs.json `script: "hermes-restore-v4.sh"` → 跑的時候 tier1 沒拿到 --target 引數、直接 exit 1

**根因**：
- hermes cron 對 `no_agent: true` jobs 只呼叫 `script` 欄位的純檔名（從 `$HERMES_HOME/scripts/` 解析）
- **不**帶任何參數
- 想要參數必須寫一個 wrapper script（包在 `~/.hermes/scripts/` 內、帶正確參數）

**正確做法**：
```bash
# 寫 ~/.hermes/scripts/hermes-restore-verify.sh
#!/usr/bin/env bash
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
TARGET="/tmp/hermes-restore-verify-$$"
exec "$HERMES_HOME/scripts/hermes-restore-v4.sh" tier1 --target "$TARGET"
```

jobs.json 內：
```json
{
  "name": "v4-restore-verify-weekly",
  "script": "hermes-restore-verify.sh",  // ← 用 wrapper、不要直接用 hermes-restore-v4.sh
  "no_agent": true,
  "schedule": {"kind": "cron", "expr": "0 4 * * 0"}
}
```

**If** cron 跑需要參數的 script **Then** 寫 wrapper script
**Then 不要** 在 jobs.json `script` 欄位直接放帶參數的指令（hermes 不支援）
**Then** 從 `hermes-agent/cron/scheduler.py:_run_job_script` 可看到只支援純 script 執行

---

## 相關 skills

- `hermes-tier-router`（赫米斯自用 tier 決策表）
- `trial-and-error/hermes-internal`（Hermes 內部試誤）
