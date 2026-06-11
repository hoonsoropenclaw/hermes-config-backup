---
name: hermes-config-layout
description: "Hermes Agent 配置檔案的結構、改動 SOP、檔案間關係地圖。當需要改 ~/.hermes/ 下的設定檔（config.yaml / .env / auth.json / cron/jobs.json / config 區段）或理解某個欄位怎麼運作時,載入此 skill。涵蓋檔案結構、改動前備份慣例、跨檔案相依性（如 model 改動要同步 .env key + jobs.json + config.yaml + 重啟 gateway）、**建常駐 profile 的精瘦 SOP（取代舊的 agents/ + persistent-subagent 方案）**、**SOUL.md vs persona.md 載入機制（sub-agent 只讀 SOUL.md）**。"
version: 1.6.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, config, layout, sop, cross-file, profile, persistent, disk-cleanup, audit, consolidated-layout, soul-persona-loading]
    triggers: [config-edit, env-edit, jobs-json-edit, auth-json-edit, cron-model-change, provider-add, backup-strategy, restore-sop, hermes-backup-v4, hermes-restore-v4, persistent-profile, persistent-subagent, 常駐子代理, 常駐代理, profile-create, profile-lean, profile-trim, disk-cleanup, disk-audit, messy-hermes-folder, classify-hermes-files, upstream-hardcode, consolidated-layout, soul-md-loading, persona-md-not-auto-loaded]
    related_skills: [hermes-agent, trial-and-error, metacognitive-learner, alt-token-secrets-layout, workspace-folder-layout]
---

# Hermes Config Layout

Hermes Agent 配置檔案的結構、改動 SOP、跨檔案關係地圖。

## 何時使用

**觸發**（任一符合即載入）:

- 改 `~/.hermes/config.yaml` 任何區段（model / delegation / auxiliary / terminal / compression / display / stt / tts / memory / security / approvals / curator / kanban）
- 改 `~/.hermes/.env`（新增 / 修改 / 移除 API key）
- 改 `~/.hermes/cron/jobs.json`（新增 / 編輯 / 改 model / 改 script）
- 改 `~/.hermes/auth.json`（OAuth token、credential pool）
- 改 `~/.hermes/profiles/<name>/` 下的任何檔案
- **建常駐 profile（取代舊 agents/ + persistent-subagent 方案）→ 見 `references/persistent-profile-sop.md`**
- 加新 provider（如把 DeepSeek 加進 .env）
- 改某個 cron job 的 model（要確認 provider key 存在）
- 理解「為什麼我改了 config 但沒生效」（mid-session 不生效、需重啟）
- **設計或修改 hermes 備份策略（v4 雙雲端架構見 `references/backup-architecture-v4.md`）**
- **異機還原規劃（`hermes-restore-v4.sh` 三層 SOP 見同一份 reference）**
- **任何 cron job 的 script timeout 問題（`HERMES_CRON_SCRIPT_TIMEOUT` 優先順序見 `references/cron-script-timeout.md`）**
- **常駐 profile 的 sub-agent 不認自己的 persona（SOUL.md 沒含 persona 摘要）→ 見下方「SOUL.md vs persona.md 載入機制」**

## 已知上游 hardcode（盤點時不要亂動，2026-06-10 實戰確認）

以下檔案是 hermes 上游**直接寫死路徑**的（不能搬、搬了會被自動重建或下次啟動壞掉）：

| 檔案 | 上游 hardcode 位置 | 說明 |
|------|---------------------|------|
| `~/.hermes/.hermes_history` | `ui-tui/README.md:173` 明確寫 "stored in `~/.hermes/.hermes_history`" | CLI readline 歷史檔 |
| `~/.hermes/.skills_prompt_snapshot.json` | `agent/prompt_builder.py:929-989` 用 `get_hermes_home() / ".skills_prompt_snapshot.json"` | skills 提示快照 |
| `~/.hermes/interrupt_debug.log` | `cli.py:12558, 13551` 用 `_hermes_home / "interrupt_debug.log"` | debug 用 log，**搬了會被自動重建** |
| `~/.hermes/state.db` 系列 | SQLite WAL 模式（shm/wal 是 state.db 配套） | 動了 state.db 整個 session 系統壞掉 |

**If** 看到這幾個檔案在根目錄覺得「應該整理」 **Then** **不要動**，先 grep 確認上游路徑、記錄進本 skill

## 磁碟盤點 SOP（清理「很亂的 ~/.hermes/」用，2026-06-10 新增）

**觸發情境**：
- 使用者問「`~/.hermes/` 看起來很亂」「根目錄檔案都是會用到的嗎」「按目前分類規則重排」
- 想驗證 `~/.hermes/` 結構是否還符合 hermes 上游慣例

### 「應該在子目錄」但「上游沒自動搬」的檔案（盤點時標記為 🟡 中風險）

| 根目錄檔案 | 建議位置 | 上游動態 |
|------------|----------|----------|
| `*.cache.json`（5 個）| `cache/` | 啟動時重新抓、不會搬走 |
| `.update_check` | `cache/` | 每次啟動重新檢查 |
| `gateway.lock` / `gateway.pid` | `state/locks/`（自建）| hermes 啟動會自動重建 |
| `auth.lock` / `kanban.db.init.lock` | `state/locks/`（自建）| 同上 |
| `gateway_state.json` / `processes.json` | `state/`（自建）| 啟動時自動產生 |
| `interrupt_debug.log` | `logs/` | **會被自動重建在根目錄**（hardcode） |

### 「應該在 hermes 外部」的檔案（標記 🔴 高風險）

| 根目錄檔案 | 應該位置 | 為什麼 | 2026-06-10 狀態 |
|------------|----------|--------|-----------------|
| `youtube_tokens.json` | `~/.local/share/hermes/secrets/` | YouTube OAuth token 不是 hermes 內建（見 alt-token-secrets-layout SOP） | 🟠 暫不動（待日後 GPG 加密） |
| `youtube_channels.json` | `cache/youtube/channels.json` | 自建的 YouTube 抓取 metadata（純公開資料）| ✅ **已搬到 `cache/youtube/channels.json` + 改 3 個 script** |
| `kanban.db` | 待確認 | 需先確認是 hermes 內建 kanban 還是獨立服務 | 🟠 hermes 內建 back-compat 路徑、不動 |

### 「雙檔衝突」決策結果（2026-06-10 修好，後續 v3 精簡）

**`SOUL.md` 同時存在兩處**：
- 根目錄 `SOUL.md`（537B，hermes 預設模板）
- `memories/SOUL.md`（8957B，2026-06-09 啟用的「Super Learner」真版）

`hermes_constants.py` 沒明指 SOUL.md 路徑、`run_agent.py` 也沒 reference `memories/SOUL.md`——**實際上 hermes 啟動時讀根目錄那份預設版**。這是真 bug，**已於 2026-06-10 修好**：

```bash
# 1. 備份當前根目錄的 537B 預設版
cp ~/.hermes/SOUL.md ~/.hermes/archive/SOUL.md.original-537b-20260530

# 2. 用 8957B 真版覆蓋
cp ~/.hermes/memories/SOUL.md ~/.hermes/SOUL.md

# 3. 順手修 AGENTS.md「啟動程序」段,加註根目錄 vs memories/ 區別（避免再誤會）
```

**修完後效果**：`hermes --cli` 模擬 `load_soul_md()` 回傳 5375 chars 的 Super Learner persona（不是 537B 預設版）。

**重要預防**：「AGENTS.md 引導的檔案路徑」≠「hermes 程式碼實際讀取路徑」——任何編輯 7 個重要檔案前都要 grep 確認。`AGENTS.md` 該段未來應明確加註「SOUL.md 在 `~/.hermes/SOUL.md`（**根目錄**，不是 `memories/`）」——已加在 SOUL.md 修補步驟裡。

### SOUL.md 路徑決策樹（給未來 session 速查，2026-06-10 收）

```
使用者問「要改 SOUL.md」「SOUL.md 沒生效」「SOUL.md 在哪」
   ↓
Step 1: 確認 hermes 讀的是哪個
   grep -n 'get_hermes_home() / "SOUL.md"' ~/.hermes/hermes-agent/agent/prompt_builder.py
   預期: prompt_builder.py:1414  ← 根目錄
   ↓
Step 2: 確認當前根目錄 SOUL.md 的內容
   wc -c ~/.hermes/SOUL.md
   537B = hermes 預設（沒 persona）
   5000+B = 已有自訂 persona
   ↓
Step 3: 確認 memories/SOUL.md 是否跟根目錄一致
   diff -q ~/.hermes/SOUL.md ~/.hermes/memories/SOUL.md
   「不同」= 寫到錯位置了（bug 狀態）
   ↓
Step 4: 修法
   # 把 memories/ 那份同步到根目錄（保留兩份同步）
   cp ~/.hermes/memories/SOUL.md ~/.hermes/SOUL.md
   # 修 AGENTS.md 註明路徑（避免再誤會）— 見下段
```

## 🚨 Background 跑 `hermes chat` sub-agent 的 4 條鐵律（2026-06-12 實戰歸納）

**觸發情境**:要 background 跑 1 個或多個 `hermes chat` sub-agent（像 `delegate_task` 或 orchestrator-worker 架構、跑跨 session 實驗、跑 5 個 round 的 A/B test 等等）時，**本段必讀**。違反任一條 = sub-agent 看不到 prompt、直接 Goodbye、產出 0。

**4 條鐵律**（R3b 跑了 3 次才成功歸納）:

1. **Prompt 必永久存到工作目錄**：`/tmp/prompt-*.txt` 不可靠（`/tmp` 預設 10 天未訪問自動清，實測在跑 sub-agent 期間就被清掉）。**所有 prompt 檔必存到 `~/<project-dir>/prompt-<name>.txt`**
2. **不要用 `tee`，用 `>`**：`cmd 2>&1 | tee log` 會搶 stdin，sub-agent 看不到 prompt。**改用 `cmd > log 2>&1`**（先 redirect stdout、再 redirect stderr 到當前 stdout）
3. **Redirect 順序要對**：`cmd > log 2>&1`（先 `> log` 再 `2>&1`）。**不是 `cmd 2>&1 > log`**（那是先開 stderr 到 tty、再 redirect stdout，順序錯會導致 stderr 進 tty、log 只剩 stdout）
4. **加 `--yolo --accept-hooks`**：避免 sub-agent 在 TTY approval prompt 卡住（背景跑沒有 tty、會 hang 等不到回應）

**驗證 SOP**（每個 background sub-agent 必跑，不要只看通知）:

```bash
# 1. 啟動後 30-60 秒看進程還活著
ps -ef | grep "hermes chat" | grep -v grep

# 2. 看 log 不是 Goodbye（成功跡象）
tail -3 log
# 成功:有 worker 自己的輸出（不是 "Goodbye! ⚕"）
# 失敗:只有 "Goodbye! ⚕" 表示 prompt 沒進去

# 3. 看產物是否存在
ls <expected-output-dir>

# 4. （重要）**不要相信 notify_on_complete 的 exit code 或 output snapshot**:
#    - exit code 0 但 output 顯示 Goodbye = 實際上失敗（hermes 通知機制抓的可能是啟動 snapshot）
#    - **最可靠**:看 log 大小 + 產物存在 + worker 自己寫的 report
```

**反面案例**（R3b 3 次嘗試時間軸）:
- 嘗試 1：用 `/tmp/round-3b-worker-{1,2,3}.txt` + `| tee log` → 3 個 worker 全 Goodbye、0 產出
- 嘗試 2：改 `>` 但仍讀 `/tmp` → 3 個 worker 仍 Goodbye、output 顯示 `cat: /tmp/...: No such file or directory`
- 嘗試 3：`>` + 永久 prompt + `--yolo --accept-hooks` → 180 秒完成、4 個核心檔 + 3 個 worker report 全部產出

**If** 看到 background sub-agent 通知 exit code 0 但 log 是 Goodbye **Then** **不要只看通知**、**ls 產物 + wc -c log + 看 worker 自己寫的 report**

---

## SOUL.md vs persona.md 載入機制（2026-06-10 engineering-lead 建立時踩到，第二類「看起來建好了但實際沒生效」）

**核心發現**：`hermes -p <name> chat` 啟動 sub-agent 時，**只讀 `<profile>/SOUL.md`，不會自動讀 `<profile>/persona.md`**。

| 檔案 | 載入時機 | 影響 |
|------|---------|------|
| `<profile>/SOUL.md` | ✅ sub-agent `chat` 啟動時自動載入 | 決定 LLM 的「語氣」跟「核心信念」 |
| `<profile>/persona.md` | ❌ sub-agent **不會**自動載入 | 必須在 SOUL.md 內引用、或在主 session 內手動讀 |
| `<profile>/skills/<X>/SKILL.md` | ✅ sub-agent 載入（按需） | 跟 persona 獨立 |

**症狀**：寫了 10KB 的 persona.md（4 個決策 + 6 步工作流 + 12 個禁止事項），但 sub-agent 開新 session 時**只回答赫米斯 SOUL 核心信念、不知道自己的 4 個決策**。

**修法**（必做、不能跳過）：

1. **在 SOUL.md 頂部插入 persona 摘要**（不是抄整份 persona,是「4 個核心決策」+「在 handoff chain 的位置」+「與上下游關係」+「禁止事項」摘要）—— **5-10 段、每段 1-2 行**足夠
2. **用 patch 工具做頂部插入**（避免破壞原 SOUL 內容）—— patch 的 `old_string` 錨點選「`# SOUL.md - Who You Are`」這行
3. **驗證**：`hermes -p <name> chat -q "回報 4 個核心決策" --cli` 應回答自己決策（不是 default 核心信念）

**反面案例**（system-architect 為何能直接回答）：system-architect 的 SOUL.md 頂部**已經含完整 persona 摘要**（4.9KB SOUL.md、有 persona 段）。**它不是因為自動載入 persona、而是因為它的 SOUL.md 內含**。

**If** 任何常駐 profile 的 SOUL.md 沒含 persona 摘要 **Then** sub-agent 啟動時不知道自己的決策 → **修法：加到 SOUL.md 頂部**

**If** 想保留完整 persona 在 persona.md **Then** 在 SOUL.md 加「詳見 `persona.md`」引用即可

**驗證 SOP**（每個常駐 profile 必跑）：
```bash
hermes -p <name> chat -q "用一句話回報: 你的 N 個核心決策是什麼?" --cli
# 預期: 回答自己的決策
# ❌ 失敗: 回答 hermes 預設 SOUL 核心信念(耗盡配額/有主見/先查再問/用能力換取信任)
```

**坑**：
- 看到 sub-agent 回答 default SOUL 內容 → **不要懷疑 persona.md 寫錯** → **修法是加 SOUL.md 頂部摘要**
- 寫了一堆 SOUL.md 改完也沒動 → 別懷疑 hermes 沒載入 → 確認 grep prompt_builder.py:1414 載入的是 `<profile>/SOUL.md`

### AGENTS.md 必加的「7 個重要檔案路徑速查表」（已於 2026-06-10 修好）

**加在「啟動程序」段下方**——這份表是給「未來 agent 看到 AGENTS.md 時不會再誤判路徑」用的必備內容：

| 檔案 | hermes 啟動時讀哪裡 | 編輯時改哪裡 |
|------|------------------|------------|
| `SOUL.md` | `~/.hermes/SOUL.md` ✅ | 改**根目錄** |
| `USER.md` | `~/.hermes/memories/USER.md` | 改 `memories/` |
| `MEMORY.md` | `~/.hermes/memories/MEMORY.md` | 改 `memories/` |
| `HEARTBEAT.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |
| `AGENTS.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |
| `IDENTITY.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |
| `TOOLS.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |

**為什麼要寫進 AGENTS.md**：原始的「1. 讀取 SOUL.md」沒指路徑、會誤導 agent 寫到 `memories/SOUL.md`。速查表讓「讀哪 / 改哪」分離，**避免雙檔 bug 再發生**。

### SOUL.md 內容精簡（v2 → v3，2026-06-10 收尾）

**觸發**：使用者交叉比對 SOUL.md vs AGENTS.md/IDENTITY.md/USER.md/HEARTBEAT.md/MEMORY.md/TOOLS.md，發現 6 個衝突 + 2 個補強需求。

**6 個衝突**（已修）：

| # | 衝突 | 修法 |
|---|------|------|
| 1 | 「耗盡配額」語意不清 vs USER.md「效率優先」 | 加「**高效率**」+ 3 個可驗證指標 + 4 個反例 |
| 2 | 「第一次就做對」vs「主動學習循環」 | 後者加「品質內化」註解，說明兩者不衝突 |
| 3 | 「回應指示燈」已過時 | 整段刪除（8 行）|
| 4 | Python 開發守則跟 TOOLS.md 重複 | 搬到 `memories/TOOLS.md`「Python 開發與套件安裝守則」段 |
| 5 | 資料夾結構段（5 個項目）跟實際 30+ 個子目錄不符 | 整段刪除 |
| 6 | 「Session 延續性三層備援搜尋」跟 HEARTBEAT.md「兩階段記憶搜尋」重複且舊版 | 整段刪除（53 行），HEARTBEAT.md 是單一真實來源 |

**2 個補強**（已加）：

| # | 補強 | 加在哪 |
|---|------|--------|
| 1 | 「不主動寫記憶」原則（呼應 MEMORY.md）| 新增「🗂️ 記憶紀律 (Memory Discipline)」段 |
| 2 | Vibe 段加 USER.md INTJ 呼應 | 「Vibe」段加「**跟 `USER.md` 溝通風格偏好一致**：直接精確、效率優先、結構化、不遺漏」 |

**變更結果**：SOUL.md 從 8957B / 206 行 → **6263B / 114 行（-30% 縮減）**，純度大幅提升。TOOLS.md 從 2386B / 74 行 → 4635B / 114 行（+94%，Python 段合理移入）。

### 使用者偏好（first-class，2026-06-10 明確語意澄清）

> **「耗盡配額」是指高效率的耗盡，不是亂浪費配額。**

「高效率」的三個可驗證指標：
1. **動手前先評估** — 任何搬移/修改/部署前，先給完整評估報告（路徑、相依性、風險、SOP），給使用者審核後才動手
2. **每步備份 + 驗證鏈** — SHA256 fingerprint、改動後對照確認、/tmp 雙保險副本
3. **失敗要可還原** — 任何動作都設計成「後悔隨時可 undo」、驗證命令留痕跡、不留「動了才知道壞」的中間狀態

反例（不是高效率耗盡）：
- ❌ 沒評估就 `rm -rf` / 直接覆蓋檔
- ❌ 一次跳好幾步、沒中間驗證
- ❌ 改了設定但不知道怎麼 revert
- ❌ 浪費 token 在重複的無效搜尋 / 無差別 LLM retry

**If** 未來 session 設計任何「大量使用 token / 跑很多動作」任務 **Then** 必遵守「高效率耗盡」3 指標、避開 4 反例

### 上游設計的「consolidated layout」慣例

`hermes_constants.py:225-235` 明確寫：

> "New installs get the consolidated layout (e.g. `cache/images`). Existing installs that already have the old path (e.g. `image_cache`) keep using it — no migration required."

**If** 看到 `cache/` `image_cache/` 兩種風格並存 **Then** 這是上游設計、不是錯，**不要強行統一**。**If** 從未來乾淨的 N100 安裝、想建立「標準化」目錄 **Then** 用 consolidated 風格（`cache/images` 而不是 `image_cache`）

## 設定檔結構總覽

```
~/.hermes/
├── config.yaml            # 主設定（model / delegation / 各種區段）── 啟動時讀一次
├── .env                   # API keys（明文、mode 0600）── 啟動時讀一次
├── auth.json              # OAuth tokens、credential pool（mode 0600）
├── cron/
│   ├── jobs.json          # cron job 定義（含 model override）
│   └── output/<id>/...    # 各次 tick 的執行輸出
├── profiles/<name>/       # 多 profile 隔離（同樣的 layout,每 profile 一份）
│   ├── SOUL.md            # ✅ sub-agent 啟動時自動載入
│   ├── persona.md         # ❌ sub-agent 不自動載入,SOUL.md 必須含摘要
│   ├── skills/<X>/SKILL.md  # 按需載入
│   └── ...
├── skills/                # 技能庫
├── memories/              # 7 個重要檔案（SOUL / USER / MEMORY / HEARTBEAT / AGENTS / IDENTITY / TOOLS）
├── sessions/              # session 索引
├── state.db               # SQLite session store（含 FTS5 全文搜尋）
├── logs/                  # gateway & error logs
└── .hermes_history        # CLI 互動歷史
```

**兩個外部配置位置**（不在 `~/.hermes/` 下，但 hermes 會讀）:

```
~/.config/gh/hosts.yml                  # gh CLI 帳號 + token（雙 GitHub 帳號切換）
~/..local/share/hermes/secrets/          # GPG passphrase 存放（雙目錄分離佈局）
~/.config/hermes/alt_<service>_tokens/  # GPG 加密 token 存放（雙目錄分離佈局）
```

## 🚨 Pitfall：SOUL.md 必讀根目錄（不是 memories/）

**踩坑歷史**（2026-06-10 真實事件）：

- hermes 啟動時只載入 `~/.hermes/SOUL.md`（根目錄），**不讀** `~/.hermes/memories/SOUL.md`
- 程式碼位置：`agent/prompt_builder.py:1401-1414` `load_soul_md()` → `get_hermes_home() / "SOUL.md"`
- 過去有人（含我）誤把完整的 persona 寫到 `memories/SOUL.md`，但 hermes 永遠只讀根目錄那份 537B 預設版——**等於 persona 設定完全沒生效**

**If** 要編輯 SOUL.md 的 persona / Core Truths / 學習宣言 **Then** 改**根目錄**那份 `~/.hermes/SOUL.md`
**If** 不確定當前生效的是哪份 **Then** 跑 `python3 -c "from agent.prompt_builder import load_soul_md; print(load_soul_md()[:200])"` 從 hermes-agent 目錄
**If** `memories/SOUL.md` 跟根目錄 `SOUL.md` 內容不一致 **Then** 把 `memories/SOUL.md` 的內容 cp 到根目錄（不是反向）

### 7 個重要檔案的 hermes 載入行為速查表

| 檔案 | hermes 啟動時讀哪裡 | 編輯時改哪裡 |
|------|------------------|------------|
| `SOUL.md` | `~/.hermes/SOUL.md` ✅ | 改**根目錄**（不是 memories/） |
| `USER.md` | `~/.hermes/memories/USER.md` | 改 `memories/` |
| `MEMORY.md` | `~/.hermes/memories/MEMORY.md` | 改 `memories/` |
| `HEARTBEAT.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |
| `AGENTS.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |
| `IDENTITY.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |
| `TOOLS.md` | 不主動讀 | 改 `memories/`（給 agent 查閱） |

> **HEARTBEAT.md 有「兩階段記憶搜尋規則」+「Phase 3 MemPalace 備援搜尋」是規範本尊**——任何檔案提到記憶搜尋規則時以 HEARTBEAT.md 為單一真實來源。

## 各檔案職責與改動 SOP

### `config.yaml`（主設定）

**職責**: 啟動時一次讀完的設定區段
**改動 SOP**: 見 `trial-and-error/references/execution-sop.md` 的 SOP-3

**重要區段**:
| 區段 | 內容 | 改動後要不要重啟 |
|---|---|---|
| `model` | 主 session 的 provider / model / base_url / context_length | 完全重啟 hermes |
| `delegation` | sub-agent 的 model / provider | 完全重啟 hermes |
| `auxiliary` | vision / compression / session_search 等輔助任務的 model | 完全重啟 hermes |
| `terminal` | backend / cwd / timeout | 完全重啟 hermes |
| `memory` | memory_enabled / provider | 完全重啟 hermes |
| `security` | redact_secrets / tirith_enabled | 完全重啟 hermes（且 security.redact_secrets 是 import time snapshot,mid-session 無法改）|
| `approvals` | manual / smart / off | 完全重啟 hermes |

**不能 mid-session 改的原因**: 防止 LLM 改自己的 prompt cache 設定（會被 prompt caching 機制擋下）

### `.env`（API keys）

**職責**: 各種 provider 的 API key、base_url、Tavily、Ollama 等設定
**改動 SOP**: 見 `trial-and-error/references/execution-sop.md` 的 SOP-2

**重要 key 命名**:
| Key | 用途 |
|---|---|
| `MINIMAX_API_KEY` / `MINIMAX_BASE_URL` | 主 LLM provider |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` | DeepSeek provider |
| `OPENROUTER_API_KEY` | OpenRouter 統一路由 |
| `TAVILY_API_KEY` | 搜尋 API |
| `OLLAMA_WEB_SEARCH_API_KEY` | Ollama 搜尋 API |
| `GH_TOKEN` | GitHub API（也可從 `~/.config/gh/hosts.yml` 來）|
| `VERCEL_API_TOKEN` | Vercel API |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Google Gemini |
| `ANTHROPIC_API_KEY` | Anthropic Claude |
| `VOICE_TOOLS_OPENAI_KEY` / `MISTRAL_API_KEY` / `ELEVENLABS_API_KEY` | TTS providers |
| `FRED_API_KEY` / `FINNHUB_API_KEY` / `ALPHA_VANTAGE_API_KEY` / `TWELVE_DATA_API_KEY` | 金融資料 |

### `auth.json`（OAuth + credential pool）

**職責**: OAuth token（Notion、Slack 等）、credential pool（多組 key rotate）
**改動 SOP**:
1. `hermes auth list` 看現有 credential
2. `hermes auth add <provider>` 走互動 wizard
3. 自動存進 auth.json（**不要手動編輯**，格式可能會壞）

### `cron/jobs.json`（cron job 定義）

**職責**: 所有 cron job 的 prompt / model / script / schedule / skills / delivery
**改動 SOP**: 見 `trial-and-error/references/execution-sop.md` 的 SOP-1

**每個 job 的關鍵欄位**:
| 欄位 | 用途 | 注意事項 |
|---|---|---|
| `id` | 唯一識別（8-12 字元 hash） | 不要改 |
| `name` | 顯示名稱 | 隨意改 |
| `schedule` | cron 表達式或 duration | 格式見 hermes-agent skill |
| `prompt` | LLM-driven job 的 prompt | **no_agent jobs 不要有值**（會被當 script path）|
| `script` | no_agent jobs 的 script 檔名 | **要跟 prompt 互斥**（詳見 cron-jobs-json-fix.md）|
| `no_agent` | True = 純 script、False = 走 LLM | |
| `model` / `provider` / `base_url` / `api_key` | 覆寫預設 model | 留空 = 繼承主 session |
| `skills` | job 啟動時載入的 skill | **不要放 MCP 工具**（會連續 skipped）|
| `deliver` | 'local' / 'origin' / 'all' / 特定 channel | 預設 'local' |

## 跨檔案改動的相依性

**改 provider 時的連動清單**（這次 session 真實遇到的場景）:

```
要加 DeepSeek:
├─ ~/.hermes/.env
│   ├─ DEEPSEEK_API_KEY=***   └─ DEEPSEEK_BASE_URL=https://api.deepseek.com   ← 必加，預設指向不對會 fail
│
├─ ~/.hermes/config.yaml（可選）
│   └─ model.provider: deepseek  ← 切換主 session 才需要
│
├─ ~/.hermes/cron/jobs.json（可選）
│   └─ 某個 job 的 model: "deepseek-chat"  ← 該 job 走 DeepSeek 才需要
│
└─ 重啟 hermes CLI + gateway                    ← 必做，否則不生效
```

**不要**假設「改了 .env 就好」——.env 改完不重啟 = 沒改。

## 啟動順序與讀取時機

| 檔案 | 讀取時機 | mid-session 改生效？ |
|---|---|---|
| config.yaml | hermes CLI / gateway 啟動時一次 | ❌ 需重啟 |
| .env | 同上 | ❌ 需重啟 |
| auth.json | 互動時按需讀 | ✅ 部分可改 |
| cron/jobs.json | gateway 每次 tick 前重新讀 | ✅ 改完下次 tick 就生效 |
| memories/*.md | session 啟動時一次讀 | ❌ 需 `/new` 或開新 session |
| skills/SKILL.md | 互動時按需讀 + `/reload-skills` | ✅ `/reload-skills` 後生效 |
| state.db | session 結束時 append | ❌ session 級別 |

**這解釋了為什麼「我改了 config 但沒生效」**——`/reset` 不足以讓 config.yaml / .env 重新讀，必須完全退出重啟。

## 備份架構（v4 雙雲端分層）

備份策略 v1-v4 演進史、為什麼 Drive 不能跑 1 萬+ 小檔、sparc-methodology 為什麼用 snapshot 而非 submodule、3 個核心腳本（`hermes-backup-v4.sh` / `hermes-restore-v4.sh` / `hermes-secrets-encrypt.sh`）、GH013 防雷、排除清單 → 見 **`references/backup-architecture-v4.md`**

> **v4-P7 後續 bug 修復段**（2026-06-07 新加）：見 `references/backup-architecture-v4.md` 結尾的「v4-P7 後續 bug 修復」段，含 6 個本次新發現的 L3 條目（P0 顯式列舉 sync 目錄、.curator_backups GH001、metacognitive-learner GH013、push grep 假成功、filter-branch SHA 不變、已知 GH013 危險清單）。

## 磁碟盤點 SOP（處理「~/.hermes/ 看起來很亂」類任務）

**觸發**：使用者問「~/.hermes/ 根目錄哪些是會用到的？」「看起來很亂」「要怎麼分類？」「Y槽 .hermes 整理」

**完整 SOP + 真實盤點案例**（含 28 → 24 檔案分類、6 步評估、`USER_OWNED_EXCLUDE` 白名單發現、SOUL.md bug 發現）見 **`references/hermes-disk-audit-2026-06-10.md`**。

**核心 4 步**（給未來 agent 速查）：

1. **先 grep 程式碼再給建議**：用 `grep -rn "get_hermes_home() / \"<檔名>\""` 確認是不是 hardcode 根目錄
2. **先看 `USER_OWNED_EXCLUDE` 白名單**：`grep -n "USER_OWNED_EXCLUDE" ~/.hermes/hermes-agent/hermes_cli/profile_distribution.py`——這份 25 檔案白名單是上游 hermes 對「哪些是根目錄系統檔」的**權威定義**
3. **動手前必備份**：`cp <file> <file>.bak.$(date +%s)` + 記 SHA256 + 副本到 `/tmp/hermes-cleanup-backup-$(date +%Y%m%d)/`
4. **零風險先做、決策後做**：「__DEPRECATED__ / 過渡檔 / 放錯位置的 log」這類先清；「OAuth token 加密 / 跨檔搬移」這類要使用者決策

**已知反模式**（從 2026-06-10 盤點學到）：
- ❌ 從檔名猜測歸屬（看到「cache」就建議搬 cache/）→ 結果 11/12 建議會壞
- ❌ 跳過 backup 直接 rm → 無法還原
- ❌ 假設 AGENTS.md 引導的路徑 = hermes 實際讀取的路徑（**SOUL.md 就是反例**）
- ❌ 把「看起來多」當成「真的亂」——實際上 28 個檔案裡只有 4 個是真正亂源

**重要發現**（2026-06-10 session）：
- `~/.hermes/SOUL.md`（根目錄）才是 hermes 啟動時載入的（`prompt_builder.py:1414`），`memories/SOUL.md` 是「死碼」——任何 SOUL.md 編輯必須改**根目錄**那個
- `cli.py:12558, 13551` 會在根目錄自動重建 `interrupt_debug.log`（hardcode）——搬走是對的、但會被自動重建，屬於上游設計問題

## 備份慣例

**任何改動前必備份**:

```bash
# jobs.json
cp ~/.hermes/cron/jobs.json ~/.hermes/cron/jobs.json.bak.$(date +%s)

# config.yaml
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date +%s)

# .env
cp ~/.hermes/.env ~/.hermes/.env.bak.$(date +%s)

# auth.json
cp ~/.hermes/auth.json ~/.hermes/auth.json.bak.$(date +%s)
```

**備份保留策略**:
- jobs.json 備份 → 永久保留（檔案小、改動少）
- config.yaml 備份 → 保留近 5 個（會膨脹）
- .env 備份 → 保留近 3 個（裡面有 token,放太多有風險）
- auth.json 備份 → 保留近 3 個

## 與其他 skill 的關係

| Skill | 關係 |
|-------|------|
| `hermes-agent` (bundled, 不可編) —— 給高階 CLI 指令、providers 清單、slash commands 速查 |
| `trial-and-error/references/execution-sop.md` —— 4 個 SOP（cron / .env / config / 分流）的細節 |
| `alt-token-secrets-layout` —— GPG 雙目錄加密的 SOP（屬於 secrets-and-env 的子集） |
| `metacognitive-learner` —— 監控 cron job 健康、識別 SOP 違規 |
| `references/persistent-profile-sop.md` —— 建常駐 profile 的精瘦 SOP（profile 精瘦、opt-out --remove、白名單設計、5 個必跑驗證、**SOUL.md vs persona.md 載入機制 2026-06-10 新增**） |
| `workspace-folder-layout` —— 處理 `~/*` 使用者工作區的檔案組織 SOP；本 skill 管 `~/.hermes/` 配置；本 skill 的「磁碟盤點 SOP」跟它配套（盤點 `~/.hermes/` 用本 skill、盤點 `~/` 用 workspace-folder-layout） |
| `references/hermes-disk-audit-2026-06-10.md` —— 2026-06-10 盤點的 28 個檔案紀錄、3 個非顯而易見的發現、處理紀錄、給下次盤點的遺留清單 |

## 維護

- **patch > create**: 任何 session 發現配置結構有變（hermes 版本更新、新 provider 加入），patch 本 skill
- **不要複製 SKILL.md 整份到 references/**: 這份是結構速查,詳細 SOP 在 trial-and-error
- **3 個月掃一次**: 確認檔案路徑還適用（hermes 改版可能會改 ~/.hermes 結構）
- **盤點新裝的 hermes 工作區時**：必看「已知上游 hardcode」「磁碟盤點 SOP」「上游設計的 consolidated layout」「SOUL.md vs persona.md 載入機制」四段——這是 2026-06-10 從實戰收的，避免重複踩「以為能搬、其實 hardcode」、「以為 persona 會自動載、其實只讀 SOUL.md」的雷

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.6.0 | 2026-06-12 | 新增「Background 跑 `hermes chat` sub-agent 的 4 條鐵律」段——從 R3b 跑了 3 次才成功歸納：(1) prompt 必永久存到工作目錄（`/tmp` 不可靠，會被自動清）、(2) 不要用 `tee` 用 `>`（`tee` 搶 stdin）、(3) redirect 順序要對（先 `> log` 再 `2>&1`）、(4) 加 `--yolo --accept-hooks` 避免 TTY 卡住。**新增「不要相信 notify_on_complete 的 exit code」反模式**：R3b 3 個成功 sub-agent 通知時都顯示 Goodbye + exit 0，但實際上是 sub-agent 跑了 + 有產出（hermes 通知機制抓的是啟動 snapshot）。**最可靠的監聽是 `ls` 產物 + `wc -c log` + `ps` 看 process**。|
| 1.5.0 | 2026-06-10 | 補上 engineering-lead 建立時的關鍵發現：「**`hermes -p X chat` 只讀 SOUL.md、不自動載 persona.md**」—— 寫了 10KB persona.md 但 sub-agent 開新 session 完全沒套用。新增「SOUL.md vs persona.md 載入機制」段,含症狀、修法（patch SOUL.md 頂部插入摘要）、反面案例（system-architect 為何能用）、必跑驗證 SOP（`chat -q "回報 N 個決策" --cli`）。**這是「看起來建好了但實際沒生效」第二類**（第一類是 1.4.1 的 SOUL.md 雙檔衝突）|
| 1.4.2 | 2026-06-10 | 補上 6/10 第三次收尾：SOUL.md 內容精簡（v2 8957B/206 行 → v3 6263B/114 行，-30% 縮減）、6 個衝突（耗盡配額/第一次就做對/回應指示燈/Python 守則/資料夾結構/Session 延續性）+ 2 個補強（記憶紀律/Vibe INTJ 呼應）全部修好、新增 SOUL.md 路徑決策樹（給未來 session 速查）。**收錄使用者「高效率耗盡」first-class 偏好**（3 指標 + 4 反例，未來任何 token-heavy 任務必遵守）|
| 1.4.1 | 2026-06-10 | 補上 6/10 收尾：SOUL.md bug 已修（537B 預設 → 8957B Super Learner 覆蓋根目錄 + AGENTS.md 加註路徑說明）、youtube_channels.json 已搬到 `cache/youtube/channels.json` + 改 3 個 script。「雙檔衝突」段從「待決策」改為「已修」、「應該在 hermes 外部」表加 2026-06-10 狀態欄。 |
| 1.4.0 | 2026-06-10 | 新增 3 段：(1)「已知上游 hardcode」——列出 `.hermes_history` `.skills_prompt_snapshot.json` `interrupt_debug.log` `state.db` 系列的上游 hardcode 位置，盤點時不可動；(2)「磁碟盤點 SOP」——標記根目錄哪些檔案該去 `cache/` `state/locks/` `logs/` `~/.local/share/hermes/secrets/`；(3)「上游 consolidated layout 慣例」——hermes_constants.py:225 明確寫新安裝走 consolidated 風格（`cache/images`）。收錄 SOUL.md 雙檔衝突（根目錄 537B 預設 vs `memories/SOUL.md` 8957B 真版）待使用者決策 |
| 1.3.0 | (前版) | 既有內容 |
