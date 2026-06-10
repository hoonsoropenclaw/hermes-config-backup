# INVENTORY.md - 備份架構清單

_2026-06-10 建立——作為 `hermes-backup-v4.sh` 跟 `hermes-backup-coverage-check.sh` 的**單一真實來源 (single source of truth)**。_

任何「v4 同步哪些路徑」的問題都以此檔為準。改 v4 腳本或 check script 時，**必同步改本檔**。

---

## 📦 v4 備份同步清單（v4.6 起, 2026-06-10 補強）

### Tier 1（公開推到 GitHub, v4 腳本直接 rsync）

#### 同步的目錄（7 個原有 + 6 個新增, 共 13 個）

| 路徑 | 排除規則 | 為什麼備份 |
|------|---------|-----------|
| `agents/` | `__DEPRECATED__*` | 常駐 agent 身份檔（v4.2 起）|
| `memories/` | `*.bak.*` `*.lock` `*.clean.*` `__DEPRECATED__*` | 7 個重要檔案 + 學習素材 |
| `scripts/` | `*.bak` `*.pyc` `__DEPRECATED__*` | 輔助腳本（含 hermes-backup-v4.sh）|
| `cron/` | `*.bak` `*.bak.*` `output/` `__DEPRECATED__*` | cron jobs.json 排程配置 |
| `docs/` | `__DEPRECATED__*` | 4 份還原說明檔 + 設計文件 |
| `profiles/` | `*.bak.*` `*.lock` `*.clean.*` `.curator_backups/` `.archive/` `.hub/` `.usage.json` `.bundled_manifest` `.curator_state` `__pycache__/` `*.pyc` `venv/` `state.db` `state.db-shm` `state.db-wal` `*.tar.gz` `*.tar` `*.zip` `*.7z` `models_dev_cache.json` `home/` `logs/` `__DEPRECATED__*` | 常駐子代理整套配置（v4.2）|
| `skills/` | (見 §3 完整排除) | 自建技能庫 |
| **`archive/`** ✨ | `__DEPRECATED__*`（內含） | 永久棄用備份（SOUL.md.original-537b 等）|
| **`config/`** ✨ | `.hermes-user-key` 模式 600 保留 | USER_KEY 環境變數檔（cron 跑 Tier 2 必備）|
| **`handoff/`** ✨ | `__DEPRECATED__*` | 跨 profile handoff pipeline 產出 |
| **`reports/`** ✨ | `__DEPRECATED__*` | 設計文件 |
| **`cache/youtube/`** ✨ | `__DEPRECATED__*` | YouTube 公開資料快取 |
| **`cache/documents/`** ✨ | `__DEPRECATED__*` | documents 快取 |
| **`logs/`** ✨ | `*.log.1` `*.log.2` `*.gz` `backup_*.log` | agent.log 主檔、debug 價值（排除大檔）|

#### 同步的單檔（1 個原有 + 1 個新增, 共 2 個）

| 檔案 | 為什麼備份 |
|------|----------|
| `config.yaml` | hermes 主設定 |
| **`SOUL.md`** ✨ | 核心人格檔（根目錄版本、修 SOUL bug 後主版在這）|

#### 排除的目錄（設計上不備份, 11 個）

| 路徑 | 為什麼排除 |
|------|----------|
| `hermes-agent/` | upstream clone、git pull 可重建 |
| `hermes-backup-staging/` | 備份本體、不能備份自己 |
| `backups/` | 備份本體、不能備份自己 |
| `state.db` / `state.db-shm` / `state.db-wal` | hermes runtime 鎖定檔、Tier 2 GPG 加密 |
| `kanban.db` | 空殼、可重 init |
| `audio_cache/` `image_cache/` `images/` `pairing/` `sandboxes/` `hooks/` `test_rclone_speed/` | 空目錄或純暫存 |
| `browser_screenshots/` | 純截圖暫存 |
| `lsp/` `pastes/` `rag/` | rebuildable 暫存/索引 |
| `sessions/` | request_dump 暫存、有敏感資料風險 |
| `state-snapshots/` | 太大（200M）、rebuild 容易 |
| `projects/` `bin/` | 有 .git 的專案 / tirith 二進位、rebuild 容易 |

### Tier 2（私人, GPG 加密推 Drive）

走 `hermes-secrets-encrypt.sh`（不歸本 INVENTORY 管）：
- `.env` — API keys
- `auth.json` — OAuth tokens
- `state.db` (197MB) — session store

### Tier 2b（私人, USER_KEY 加密）

- `.hermes/config/.hermes-user-key` — USER_KEY 環境變數檔

---

## 🔄 變更記錄

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-06-10 | v4.6 | 新增 INVENTORY.md 同步清單（從 v4.5 升 v4.6 補強覆蓋率）|
| 2026-06-10 | v4.6 | 加 6 個 rsync 段：archive/ config/ handoff/ reports/ cache/youtube/ cache/documents/ logs/ |
| 2026-06-10 | v4.6 | 加 1 個根目錄單檔：SOUL.md |
| 2026-06-10 | v4.6 | 新建 `hermes-backup-coverage-check.sh`（每日 04:00 跑路徑覆蓋率檢查，cron id: 651713da919d）|
| 2026-06-10 | v4.5 | (歷史) 雙層 GPG 加密設計 |

---

## 📋 改檔對照表（給未來 AI 必看）

### 改 `hermes-backup-v4.sh` 同步清單時

**必同步修改**：
1. `~/.hermes/docs/INVENTORY.md`（本檔 §「v4 同步清單」）
2. `~/.hermes/skills/agent-system-backup/SKILL.md` §3 完整版 INVENTORY
3. `~/.hermes/skills/agent-system-backup/references/v4-rsync-exclude-recipes.md`（如有 rsync 排除規則變動）

### 改 `hermes-backup-coverage-check.sh` 時

**必同步修改**：
1. `~/.hermes/docs/INVENTORY.md`（本檔「v4 同步清單」段）
2. `~/.hermes/skills/agent-system-backup/SKILL.md` §16 Scripts 段

### 改 GPG / USER_KEY / Tier 2 設計時

**必同步修改**：
1. `hermes-secrets-encrypt.sh`
2. `hermes-restore-v4.sh`
3. `~/.hermes/docs/DRIVE-RESTORE.md` §B
4. `~/.hermes/skills/agent-system-backup/SKILL.md` §10.2.1

---

_Last updated: 2026-06-10_
