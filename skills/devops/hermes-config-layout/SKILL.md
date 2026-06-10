---
name: hermes-config-layout
description: "Hermes Agent 配置檔案的結構、改動 SOP、檔案間關係地圖。當需要改 ~/.hermes/ 下的設定檔（config.yaml / .env / auth.json / cron/jobs.json / config 區段）或理解某個欄位怎麼運作時,載入此 skill。涵蓋檔案結構、改動前備份慣例、跨檔案相依性（如 model 改動要同步 .env key + jobs.json + config.yaml + 重啟 gateway）、**建常駐 profile 的精瘦 SOP（取代舊的 agents/ + persistent-subagent 方案）**。"
version: 1.3.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, config, layout, sop, cross-file, profile, persistent]
    triggers: [config-edit, env-edit, jobs-json-edit, auth-json-edit, cron-model-change, provider-add, backup-strategy, restore-sop, hermes-backup-v4, hermes-restore-v4, persistent-profile, persistent-subagent, 常駐子代理, 常駐代理, profile-create, profile-lean, profile-trim]
    related_skills: [hermes-agent, trial-and-error, metacognitive-learner, alt-token-secrets-layout]
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

**不備份的後果**: 改錯時沒有 rollback 點，要重建設定。

## 與其他 skill 的關係

- **hermes-agent** (bundled, 不可編) —— 給高階 CLI 指令、providers 清單、slash commands 速查
- **trial-and-error/references/execution-sop.md** —— 4 個 SOP（cron / .env / config / 分流）的細節
- **alt-token-secrets-layout** —— GPG 雙目錄加密的 SOP（屬於 secrets-and-env 的子集）
- **metacognitive-learner** —— 監控 cron job 健康、識別 SOP 違規
- **`references/persistent-profile-sop.md`** —— 建常駐 profile 的精瘦 SOP（profile 精瘦、opt-out --remove、白名單設計、5 個必跑驗證）

## 維護

- **patch > create**: 任何 session 發現配置結構有變（hermes 版本更新、新 provider 加入），patch 本 skill
- **不要複製 SKILL.md 整份到 references/**: 這份是結構速查,詳細 SOP 在 trial-and-error
- **3 個月掃一次**: 確認檔案路徑還適用（hermes 改版可能會改 ~/.hermes 結構）
