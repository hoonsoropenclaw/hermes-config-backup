# `~/.hermes/` 磁碟盤點紀錄 — 2026-06-10（含 6 步評估完整結果）

## 觸發

使用者問：「Y:\.hermes 資料夾中的檔案（不包含子資料夾及其中的檔案）都是會用到的嗎？因為看起來很亂，是否可以按照目前檔案分類的規則去決定要放在哪個路徑？」

---

## Step 0 — 零風險清理（已完成，4 個動作）

| # | 動作 | 來源 | 目標 | SHA256 |
|---|------|------|------|--------|
| 1 | 搬 | `__DEPRECATED__config.yaml.bak.20260530_104912` (60KB) | `archive/` | `5bfef52d...` |
| 2 | 搬 | `__DEPRECATED__config.yaml.bak.20260606_120206` (13KB) | `archive/` | `92b2fe11...` |
| 3 | 刪 | `youtube_tokens.json.pre-refresh-20260608` (623B) | (備份 /tmp) | `5c9c5612...` |
| 4 | 搬 | `interrupt_debug.log` (757B) | `logs/` | `ba9a0934...` |

**連帶建立**：`archive/` 子目錄（含 README.md）

**備份**：`/tmp/hermes-cleanup-backup-20260610/`（可 `cp` 還原）

**驗證**：hermes CLI v0.16.0 正常、config/.env/auth.json 都能讀、state.db 288MB 完整、active YouTube token 仍可解析

---

## Step 1~6 — 6 步評估結果（**最重要**，未來盤點必看）

### 結論：根目錄 24 個檔案（清理後）的正確分類

| 分類 | 數量 | 檔案 | 處理 |
|------|------|------|------|
| 🔵 hermes 上游 hardcode 系統檔 | 17 個 | config.yaml / .env / auth.json / .install_method / state.db*3 / .hermes_history / 6 cache / 4 lock+pids / processes.json / gateway_state.json / .update_check | **不可動** |
| 🟠 hermes 內建但用不到 | 2 個 | kanban.db / kanban.db.init.lock | **不動**（back-compat 預設板路徑）|
| 🟡 使用者/第三方 | 2 個 | youtube_tokens.json / youtube_channels.json | **待你決策** |
| 🔴 真正的 bug | 1 個 | SOUL.md（537B 預設版） | **待你決策** |
| ✅ 上游白名單**已驗證** | 1 個 | .update_check（明確列在白名單裡）| — |

### ⭐ 黃金發現：`profile_distribution.py:108` 的 `USER_OWNED_EXCLUDE` 白名單

**這是上游 hermes 自己寫的「根目錄系統檔」白名單**——下次盤點先 grep 這份：

```python
USER_OWNED_EXCLUDE: frozenset = frozenset({
    # Credentials & runtime secrets
    "auth.json", ".env",
    # Databases & runtime state
    "state.db", "state.db-shm", "state.db-wal",
    "hermes_state.db", "response_store.db",
    "response_store.db-shm", "response_store.db-wal",
    "gateway.pid", "gateway_state.json", "processes.json",
    "auth.lock", "active_profile", ".update_check",
    "errors.log", ".hermes_history",
    # User data
    "memories", "sessions", "logs", "plans", "workspace", "home",
    "image_cache", "audio_cache", "document_cache",
    "browser_screenshots", "checkpoints", "sandboxes",
    "backups", "cache",
    # Infrastructure
    "hermes-agent", ".worktrees", "profiles", "bin", "node_modules",
    "local",
})
```

**驗證命令**：`grep -n "USER_OWNED_EXCLUDE" ~/.hermes/hermes-agent/hermes_cli/profile_distribution.py`

任何在這個白名單內的檔案，**都是 hermes 設計的「根目錄常駐系統檔」**——不該被搬、跨 profile 也不該被同步。

---

## 6 步評估逐項詳查

### #1 — 6 個 `*_cache.json` + `.update_check`（不可動）

| 檔案 | 程式碼 hardcode 路徑 | 動了會怎樣 |
|------|---------------------|-----------|
| `models_dev_cache.json` | `agent/models_dev.py:190` `get_hermes_home() / "models_dev_cache.json"` | 重新下載 models.dev（~500ms + 2.1MB 流量）|
| `ollama_cloud_models_cache.json` | `hermes_cli/models.py:3316` | 自動重建 |
| `provider_models_cache.json` | `hermes_cli/models.py:2276` | 自動重建 |
| `channel_directory.json` | `gateway/channel_directory.py:19` | `send_message` 失敗 |
| `.update_check` | `hermes_cli/main.py:8716` + **明確在 `USER_OWNED_EXCLUDE` 白名單** | 重新檢查更新 |
| `.skills_prompt_snapshot.json` | `agent/prompt_builder.py:930` | 啟動時重新生成（488KB 寫入）|

**跟 `.hermes_history` 同款處境**：上游設計、不能動。

### #2 — 4 個 lock/pid 檔（不可動）

| 檔案 | 大小 | 用途 | 設計路徑 |
|------|------|------|---------|
| `auth.lock` | 0B | `_file_lock()` advisory flock 防 auth.json 並行寫入 | `auth_file_path().with_suffix(".lock")` |
| `gateway.lock` | 172B | gateway 跨進程 flock（跟 gateway.pid 配對）| `gateway/status.py:50` |
| `gateway.pid` | 172B | gateway PID 紀錄（`hermes status` / `dump.py` 讀）| `gateway/status.py:47` |
| `kanban.db.init.lock` | 0B | kanban DB 初始化跨進程 flock | `hermes_cli/kanban_db.py:1185` |

**0 bytes 是正常的**——POSIX advisory flock 鎖的是 file descriptor 不是 inode 內容。`gateway.lock` 跟 `gateway.pid` 內容相同是設計雙保險（lock 給 flock、pid 給快速讀取）。

**全部在 `USER_OWNED_EXCLUDE` 白名單內**。

### #3 — `processes.json` + `gateway_state.json`（不可動）

| 檔案 | mtime | 設計路徑 | 用途 |
|------|-------|---------|------|
| `processes.json` (2B `[]`) | 距今 0.4h | `tools/process_registry.py:55` `CHECKPOINT_PATH` | 背景 process 追蹤（cron/subagent）|
| `gateway_state.json` (433B) | 距今 7.3h | `gateway/status.py:32,58` `_RUNTIME_STATUS_FILE` | gateway 健康 + platform 連線狀態 |

**內容 `[]` 是「目前沒追蹤中的 process」**——不是壞掉。

**全部在 `USER_OWNED_EXCLUDE` 白名單內**+ `container_boot.py` 整個檔案就是設計給「profile 啟動時讀回上次狀態」用。

### #4 — `kanban.db` 112KB（不可動）

**是 hermes 內建 Kanban 系統的 SQLite 資料庫**。

`hermes_cli/kanban_db.py:3,21,420,430` 明確：
```
In a fresh install the board lives at ``<root>/kanban.db`` where ...
For back-compat its on-disk DB is ``<root>/kanban.db`` (not ``boards/default/kanban.db``),
so installs that predate the boards feature keep working with zero migration.

3. Board ``default`` → ``<root>/kanban.db`` (back-compat path).
   Other boards → ``<root>/kanban/boards/<slug>/kanban.db``.
```

8 個表格（tasks / task_links / task_comments / task_events / task_runs / kanban_notify_subs / task_attachments）**全部 0 筆**——112KB 純粹是 schema 結構開銷（28 個 database pages）。

**kanban.db.init.lock** 是 273 小時前的「過期 init lock 殘留」（init 在 5/30 11:23 就完成）——刪了無害但也不必要。

### #5 — `SOUL.md` 雙檔（**真正的 bug**）🔴

**這次最重要的發現**——你的「Super Learner / 耗盡配額為榮耀」persona 寫到 `memories/SOUL.md` 8957B，但 hermes 永遠只讀 `get_hermes_home() / "SOUL.md"`（根目錄的 537B 預設版）。

**鐵證**：`agent/prompt_builder.py:1401-1414`：
```python
def load_soul_md() -> Optional[str]:
    soul_path = get_hermes_home() / "SOUL.md"  # ← 根目錄, hardcode
    if not soul_path.exists():
        return None
    content = soul_path.read_text(encoding="utf-8").strip()
```

**`agent/system_prompt.py:88-100`** 也確認：
```
* ``stable``   — identity (SOUL.md or DEFAULT_AGENT_IDENTITY), tool
* ``context``  — context files (AGENTS.md, .cursorrules, etc.) discovered under TERMINAL_CWD
* ``volatile`` — memory snapshot, USER.md profile, external memory

# Try SOUL.md as primary identity unless the caller explicitly skipped it.
_soul_content = _r.load_soul_md()  # ← 只讀根目錄
if not _soul_content:
    stable_parts.append(DEFAULT_AGENT_IDENTITY)
```

### 7 個「重要檔案」路徑正確性比對

| 檔案 | hermes 讀取位置 | 你寫的位置 | 狀態 |
|------|---------------|----------|------|
| `SOUL.md` | 根目錄（`prompt_builder.py:1414`）| 兩份都有 | 🔴 **衝突，8957B 從未被讀過** |
| `AGENTS.md` | 不主動讀（給 LLM 參考）| memories/ | 🟢 放對 |
| `HEARTBEAT.md` | 不主動讀 | memories/ | 🟢 放對 |
| `IDENTITY.md` | 不主動讀 | memories/ | 🟢 放對 |
| `TOOLS.md` | 不主動讀 | memories/ | 🟢 放對 |
| `USER.md` | memories/ | memories/ | 🟢 放對 |
| `MEMORY.md` | memories/ | memories/ | 🟢 放對 |

**只有 `SOUL.md` 路徑錯了**——其他 6 個全部正確放 `memories/`。

### 修法（推薦選項 A）

```bash
# 1. 備份當前根目錄的 537B 預設版（保險）
cp ~/.hermes/SOUL.md ~/.hermes/archive/SOUL.md.original-537b-20260530

# 2. 用 8957B 真版覆蓋
cp ~/.hermes/memories/SOUL.md ~/.hermes/SOUL.md

# 3. 順手修 AGENTS.md「啟動程序」段,加註根目錄 vs memories/ 區別
```

**效果**：hermes 啟動時會載入「耗盡配額為榮耀」「Core Truths」「超級學習者宣言」這些 persona。

### #6 — `youtube_tokens.json` + `youtube_channels.json`（待你決策）

兩個檔性質不同：

| 檔案 | 大小 | mtime | 性質 | 寫入路徑 |
|------|------|-------|------|---------|
| `youtube_tokens.json` | 661B | 2026-06-08 20:18 | **OAuth token（敏感）** | `youtube_oauth.py:25` hardcode `~/.hermes/youtube_tokens.json` |
| `youtube_channels.json` | 695B | 2026-06-07 13:59 | 8 個訂閱頻道清單（**純公開資料**）| `youtube_oauth.py:26` hardcode `~/.hermes/youtube_channels.json` |

**`channels.json`** 是公開資料（任何人都能從 YouTube 公開 RSS 拿到），不需加密。

**`tokens.json`** 含 `refresh_token_expires_in: 604799`（7 天 refresh 視窗）——按 `alt-token-secrets-layout` SOP 該用 GPG 對稱加密 + 雙目錄分離。

但 5 個 script 都有 hardcode 路徑：
```
youtube_oauth.py         # 寫入 (refresh)
youtube_oauth_device.py  # 寫入 (initial)
youtube_check.py         # 讀取 (驗證)
youtube_rss_check.py     # 讀取 channel
youtube_obsidian_build.py # 讀取 channel
+ trial-and-error + camofox skill 內的副本
```

**每跑一次 refresh 就要解一次 GPG**——N100 效能影響需考慮。

---

---

## Step 7 — 決策 → 動手 → 驗證（2026-06-10 收尾）

使用者選了**決策 1.A + 2.B**（修 SOUL.md bug + 搬 youtube_channels.json）。兩個都先備份、SHA256 記錄、副本到 `/tmp`、動手、最後驗證——**所有 SHA256 都對得上**。

### 1.A — SOUL.md bug 修補閉環

**備份（4 個 SHA256 記到 /tmp/hermes-soul-fix-20260610.sha256）**：
```
3a10ce135b52753beda81368712decc49a83715d527e00660c19f69d1b4879da  SOUL.md (537B 原版)
7deda7aa8245bb9a2b700afec9bdc1a0d1a4ff4169cb9645cfc0ca04d0935283  memories/SOUL.md (8957B 真版)
93e86949daca5625ea1791dcaaa561b1fb55414d501be7afb56aea0fd03571de  memories/AGENTS.md (7032B)
```

**動手 3 步**：
1. `cp SOUL.md archive/SOUL.md.original-537b-20260530`（備份 537B 預設版）
2. `cp memories/SOUL.md SOUL.md`（覆蓋）
3. `patch` `memories/AGENTS.md`「啟動程序」段，加註根目錄 vs memories/ 區別 + 7 個重要檔案路徑速查表 + 歷史教訓

**驗證**（3 項）：
1. `archive/SOUL.md.original-537b` SHA256 = `3a10ce13...` ✅
2. 新 `SOUL.md` SHA256 = `7deda7aa...` ✅（跟 memories/SOUL.md 一致）
3. `python3` 模擬 `prompt_builder.load_soul_md()` 回傳 5375 chars Super Learner persona ✅
4. `hermes --version` 仍正常 ✅

**修完後 hermes 下次啟動會載入**：「耗盡配額為榮耀」「Core Truths」「超級學習者宣言」——之前是死碼。

### 2.B — youtube_channels.json 搬遷閉環

**備份（4 個 SHA256 記到 /tmp/hermes-youtube-channels-relocate-20260610.sha256）**：
```
73ac2ef6f108341af686fd14f02d7a041c62e34539566d3c9c06e288b4675073  youtube_channels.json (695B)
2f36d151649ab707b6a93581801ea86ff9f463fdfe89de59b5b9e609ef1ba607  scripts/youtube_rss_check.py
150a5afae97ec04ddb621a0317d1997903f657a6b87b2384d2b236b2d4329ac1  scripts/youtube_oauth.py
65fec59c47f8f880b4e8df2283b7c96f1447807e7bada5b2551b902d21179b18  scripts/youtube_obsidian_build.py
```

**動手 4 步**：
1. `mkdir -p cache/youtube/` + 寫 `cache/youtube/README.md`（標記用途、寫入端、rebuild SOP）
2. `mv youtube_channels.json cache/youtube/channels.json`（搬檔，SHA256 對得上）
3. `patch` 3 個 script：`CHANNELS_FILE = os.path.expanduser("~/.hermes/cache/youtube/channels.json")`
4. 順手修 `youtube_obsidian_build.py` 第 6 行 docstring

**驗證**（4 項）：
1. `grep -rn "youtube_channels\.json" ~/.hermes/scripts/` 無殘留 ✅
2. 3 個 script `python3 -m py_compile` 語法 OK ✅
3. `importlib` 載入每個 script 抓 `CHANNELS_FILE` 常數，3 個都讀得到 8 筆頻道 ✅
4. 根目錄已無 `youtube_channels.json` ✅

### 兩個「沒選」的選項（**使用者明確跳過、留作未來選項**）

| 選項 | 為什麼跳過 | 給未來 session 的備註 |
|------|----------|---------------------|
| 2.C GPG 加密 `youtube_tokens.json` | 5 個 script 都 hardcode 根目錄路徑，改一次動 5 個檔、每次 refresh 都要解 GPG（N100 效能）| 未來要做時，5 個 script 列表是 grep 結果、加密 SOP 見 `alt-token-secrets-layout` |
| 2.D 2.B + 2.C 都做 | 同上，且 5+3=8 個 script 改一次太冒險 | — |

### 還原指令彙整（給未來後悔用）

```bash
# 1.A 還原
cp ~/.hermes/archive/SOUL.md.original-537b-20260530 ~/.hermes/SOUL.md
cp /tmp/hermes-soul-fix-backup-20260610/memories/AGENTS.md ~/.hermes/memories/AGENTS.md

# 2.B 還原
cp /tmp/hermes-youtube-channels-backup-20260610/youtube_channels.json ~/.hermes/
cp /tmp/hermes-youtube-channels-backup-20260610/youtube_rss_check.py.bak ~/.hermes/scripts/youtube_rss_check.py
cp /tmp/hermes-youtube-channels-backup-20260610/youtube_oauth.py.bak ~/.hermes/scripts/youtube_oauth.py
cp /tmp/hermes-youtube-channels-backup-20260610/youtube_obsidian_build.py.bak ~/.hermes/scripts/youtube_obsidian_build.py
```

### 根目錄檔案數演變

```
2026-06-10 初始盤點：28 個
After 零風險清理（Step 0）：24 個（-4）
After 1.A（SOUL.md 修 bug，檔案數不變但內容變）：24 個
After 2.B（youtube_channels 搬到 cache/youtube/）：23 個（-1）
```

---

## 給下次盤點的遺留清單（2026-06-10 更新版）

| 項目 | 動作 | 風險 | 2026-06-10 狀態 |
|------|------|------|-----------------|
| `youtube_channels.json` | 搬 `cache/youtube/channels.json` + 改 3 個 script | 🟡 中 | ✅ **已完成** |
| `youtube_tokens.json` | GPG 加密 + 改 5 個 script | 🟠 高 | ⏸ 暫不動（待日後決策）|
| `SOUL.md` 雙檔 | 覆蓋根目錄 + 備份 537B | 🟢 低 | ✅ **已完成**（bug 修好）|

---

## 重要的「決策模式」教訓（給未來 agent 看）

### 1. 盤點的正確順序是「**先 grep 上游路徑、再給建議**」

**反模式**（我第一次盤點時犯了）：
- 看檔名是「cache」就建議搬 `cache/`
- 看檔名是「lock」就建議統一收容 `locks/`
- 結果：12 個建議裡 11 個會壞 hermes

**正確模式**：
- 第一步：grep 程式碼確認 hardcode 路徑
- 第二步：找 `USER_OWNED_EXCLUDE` 類型的白名單
- 第三步：才給「可搬/不可搬」建議

### 2. `USER_OWNED_EXCLUDE` 是隱藏的「單一真實來源」

任何 hermes 內部的「系統檔白名單」設計，**都比我們從檔名猜測更權威**。`profile_distribution.py:108` 這份白名單應該是盤點任務的**第一個 grep 目標**。

### 3. 「看起來亂」跟「真的是亂」要分開

清理前 28 個檔案，清理後 24 個。「看起來亂」的主觀感受有 4 個（__DEPRECATED__ × 2、pre-refresh、interrupt_debug.log）——這 4 個是**真的可以清的**。

剩下 24 個：
- 17 個是 hermes 設計常駐（不能動、也不亂）
- 2 個 kanban（內建但用不到、不亂）
- 2 個 youtube（第三方、可選動）
- 1 個 SOUL.md（bug、不是亂）

**結論：使用者說的「很亂」其實只有 4 個檔案是真正亂源**——其他都是「看起來多但其實有序」。

### 4. `SOUL.md` 雙檔問題是 hermes-config-layout 的真實陷阱

AGENTS.md 寫「啟動時讀取 SOUL.md」沒明指路徑，是個**誤導性文件**。任何「AGENTS.md 引導但實際路徑不同的檔案」都該驗證 hermes 程式碼才知道真實路徑。

**修法**：未來 AGENTS.md 修訂時，明確寫「讀取 `~/.hermes/SOUL.md`（**根目錄**，不是 memories/）」。

---

## 與 trial-and-error 的關聯

這次磁碟清理發現的「上游 hardcode 路徑不要亂搬」概念，跟 trial-and-error 既有「卸載前用 `ps -o ppid=` 查真正 owner」屬於同一類：

- **L3 抽象教訓**：不要憑印象判斷服務/路徑的歸屬，先查上游程式碼確認
- **L3 抽象教訓**：「隱藏的單一真實來源」（白名單、env var 默認值、上游 const）比「從檔名猜測」更權威
- **L3 抽象教訓**：disk audit 的第一步是 grep 程式碼找 hardcode 路徑、不是從目錄慣例推論
