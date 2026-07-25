# 「哪些該備、哪些不該備」決策樹(詳細版)

## 完整判斷流程

```
[1] 這個路徑是 hermes 系統設計就在這的、hermes 程式碼有 hardcode 路徑嗎?
    ├─ 是 → 必備 (T1,除非是 secret 才進 T2)
    │       例: config.yaml(hermes_cli/main.py)、state.db、auth.json
    │       例: SOUL.md(agent/prompt_builder.py:1401)
    │       例: skills/(plugin loader 自動掃)
    │
    └─ 否 → [2]

[2] 這個路徑的內容可以從其他來源 rebuild 嗎?
    ├─ 是 → 不備
    │       例: hermes-agent/ (upstream clone、git pull 重建)
    │       例: image_cache/、audio_cache/ (hermes 重新生成)
    │       例: lsp/ (LSP server 自動下載)
    │       例: rag/ (索引可重建)
    │
    └─ 否 (內容是「使用者真實工作產出」或「無法重建的歷史」) → [3]

[3] 這個路徑的內容有多大?
    ├─ < 10MB  → 必備
    ├─ 10-100MB → 必備(若可重建成本高;若可重建則不備)
    ├─ 100MB-1GB → 評估「重建成本 vs 備份成本」
    │            預設:不備(state-snapshots/ 200MB 雖 < 1GB 但 pre-update 快照可重建)
    └─ > 1GB   → 不備(無條件)

[4] 這個路徑的內容含敏感資料嗎?
    ├─ 是 (API key、token、user data) → 必備 + Tier 2 GPG 加密
    │       例: .env、auth.json、state.db、secrets/、kanban.db (雖然是空殼但含 SQLite schema)
    │
    └─ 否 → [5]

[5] 這個路徑的內容是「使用者的真實工作產出」嗎?
    ├─ 是 (任務成果、設計文件、跨 session 記錄) → 必備
    │       例: handoff/ (跨 profile handoff)、reports/ (設計文件)、archive/ (永久歷史)
    │
    └─ 否 (純暫存 cache、screenshot、debug dump) → 不備
            例: browser_screenshots/、pastes/、sessions/request_dump_*.json
```

## 各路徑具體分類(2026-06-10 完整盤點)

### 必備(但 v4 漏備)

| 路徑 | 為什麼必備 | 大小 |
|------|----------|------|
| `~/.hermes/SOUL.md` | hermes 啟動時載入(persona) | 6KB |
| `~/.hermes/config/` | .hermes-user-key 必備(cron Tier 2) | 8KB |
| `~/.hermes/archive/` | 永久歷史(SOUL/TOOLS/config 備份) | 104KB |
| `~/.hermes/handoff/` | 跨 profile handoff 任務成果 | 700KB |
| `~/.hermes/reports/` | 設計文件、跨 session 價值 | 32KB |
| `~/.hermes/cache/youtube/` | YouTube 公開資料(路徑變動) | 1.5KB |
| `~/.hermes/cache/documents/` | documents cache(任務成果) | 4KB |
| `~/.hermes/logs/agent.log` | debug 價值(但 agent.log.1 排除) | 656KB |

### 不備(rebuildable)

| 路徑 | 為什麼不備 |
|------|----------|
| `~/.hermes/hermes-agent/` | upstream clone、git pull 重建 |
| `~/.hermes/hermes-backup-staging/` | 備份本體、不能備自己 |
| `~/.hermes/backups/` | 備份本體 |
| `~/.hermes/state-snapshots/` | 200M pre-update 快照、rebuild 容易 |
| `~/.hermes/state.db*` | hermes runtime 鎖定檔、Tier 2 GPG |
| `~/.hermes/projects/<x>/.git/` | rebuildable 專案、本身有 git remote |
| `~/.hermes/bin/tirith` | 二進位、可從 upstream 重建 |

### 不備(純暫存 / 空)

| 路徑 | 為什麼 |
|------|------|
| `audio_cache/ image_cache/ images/ pairing/ sandboxes/ hooks/ test_rclone_speed/` | 空目錄 |
| `browser_screenshots/` | 純截圖暫存 |
| `pastes/` | 剪貼簿暫存 |
| `lsp/` | LSP 暫存 |
| `rag/` | 索引可重建 |
| `sessions/` | request_dump 暫存、有敏感資料風險 |

### 走 Tier 2 GPG 加密備份(不進 Tier 1 公開)

| 路徑 | 說明 |
|------|------|
| `~/.hermes/.env` | API keys |
| `~/.hermes/auth.json` | OAuth tokens |
| `~/.hermes/state.db` | session store(可能含個人資料) |

## 變更日誌

- 2026-06-10: 初版,基於 v4 根目錄完整盤點
