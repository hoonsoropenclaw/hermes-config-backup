# v4 EXCLUDE 規則

本文件說明**為什麼這些東西不進版控**。如果未來某個東西值得加、把它從 .gitignore 拿掉、commit 進來即可。

## 不備的東西 vs 原因

| 不備 | 為什麼 | 怎麼重建 |
|------|--------|----------|
| `hermes-agent/` (1.1 GB) | Python venv 巨大、可 `pip install` | `pip install hermes-agent` |
| `venv/`、`__pycache__/` | Python bytecode、rebuild 即可 | 自動生成 |
| `state.db` (179 MB) | 對話資料庫、rebuild 即可 | 對話歷史從 session log 重建 |
| `kanban.db` | 看板資料、不重要 | 重建 |
| `sessions/` (8.4 MB) | 對話 session、可從 git 推導 | 看 session DB |
| `logs/` (4.4 MB) | 系統 log、暫時性 | logrotate |
| `lsp/` (27 MB) | LSP server cache | 重啟 hermes 重生 |
| `bin/` (11.5 MB) | 二進位執行檔 | 從原始碼重編 |
| `browser_screenshots/` | 截圖、cache | 自動清 |
| `image_cache/`、`audio_cache/` | 媒體 cache | 自動清 |
| `models_dev_cache.json` | model metadata cache | 自動重抓 |
| `backups/` (671 MB) | 舊版備份 | 從 Drive 拉 |
| `hermes-backup-staging/` (39 MB) | 就是本 repo | 自己是 source of truth |
| `node_modules/` | Node.js 模組 | `npm install` |
| `.env`、`auth.json` | **secrets**、另外加密上 Drive | v4-P3 secrets 流程 |
| `*.gpg` | 加密檔（已加密的東西不該再被加密）| 從原檔加密重生 |
| `agentdb.rvf` (sparc 內) | binary vector store | 從記憶體 rebuild |

## 進版控 vs 不進版控的判斷原則

**進版控**：
- ✅ 純文字、可 diff、有意義
- ✅ 設定、SKILL、腳本、文件
- ✅ 即使丟失要重寫很花時間

**不進版控**：
- ❌ 二進位、cache、rebuild 可重生
- ❌ 體積 > 100 MB（GitHub LFS 限制）
- ❌ 含個人識別資訊（PIII）的二進位

## 為什麼 sparc 走 snapshot 而非 submodule

考慮過用 `git submodule` 引用 upstream `ruvnet/claude-flow`，但**最終選 snapshot**：

| 比較 | snapshot（採用） | submodule |
|------|------------------|-----------|
| 還原時網路需求 | `git clone` 一次 | 還要多步 `git submodule update` |
| 上游 API 變動風險 | 無（凍結） | 隨時被上游改壞 |
| repo 大小 | 78 MB（sparc 內含） | ~5 MB（不內含） |
| 更新方式 | 手動 `git pull` 後 re-backup | `git submodule update --remote` |
| 適合情境 | **備份**（凍結歷史） | **追蹤開發**（跟最新） |

→ 備份的本質是**凍結某個時間點的狀態**、不是追蹤 upstream，所以 snapshot 才是對的選擇。
