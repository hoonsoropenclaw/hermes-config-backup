# Hermes Backup Coverage Pattern — v4 同步清單 + 路徑變動自動化

_2026-06-10 從「今天變動的檔案是否漏備份」任務收的設計模式。_

## 這個 reference 解決什麼問題

`hermes-backup-v4.sh` 走 v4.5（2026-06-10 完整化）——但 v4.5 **只同步 7 個目錄 + 1 個單檔**，**沒列舉「使用者工作區會新增哪些目錄/檔案」**。當使用者在 `~/.hermes/` 根目錄新增 `archive/` `config/` `cache/youtube/` 等目錄時，**v4 腳本不會自動同步**——這就是「今天變動的檔案是否漏備」任務發現的真 bug。

**本 reference 記錄**：
1. v4.6 同步清單擴充設計（從 8 個 → 14 個目標）
2. 「單一真實來源」模式（`INVENTORY.md` 同步 v4 腳本跟 coverage check script）
3. `hermes-backup-coverage-check.sh` 的 3 層檢查邏輯
4. 為何這個設計是**不變的**（即使 v4 升 v5、v6）

## v4.6 同步清單（從 8 個擴充到 14 個目標）

### 原有 v4.5 同步的（8 個）

| 類型 | 目標 |
|------|------|
| 單檔 | `config.yaml` |
| 目錄 | `agents/`, `memories/`, `scripts/`, `cron/`, `docs/`, `profiles/`, `skills/` |

### v4.6 新增的（6 個）

| 類型 | 目標 | 為什麼要備 |
|------|------|----------|
| 單檔 | `SOUL.md` | 核心人格檔（修 SOUL.md bug 後主版在根目錄，不是 `memories/SOUL.md`）|
| 目錄 | `archive/` | 永久棄用備份（SOUL.md.original-537b 等）|
| 目錄 | `config/` | **.hermes-user-key 必備**（cron 跑 Tier 2 加密要靠它，丟了備份鏈失效）|
| 目錄 | `handoff/` | 跨 profile handoff pipeline 產出 |
| 目錄 | `reports/` | subagent 設計文件 |
| 目錄 | `cache/youtube/` | YouTube 公開資料快取 |
| 目錄 | `cache/documents/` | documents cache |
| 目錄 | `logs/` | agent.log 主檔、debug 價值（排除 `*.log.1` 等大檔）|

### 設計上**不備份**的（11 個）

| 目標 | 為什麼 |
|------|--------|
| `hermes-agent/` | upstream clone、git pull 可重建 |
| `hermes-backup-staging/` | 備份本體、不能備份自己 |
| `backups/` | 備份本體、不能備份自己 |
| `state.db` 系列 | hermes runtime 鎖定、Tier 2 GPG 加密 |
| `kanban.db` | 空殼、可重 init |
| `audio_cache/`, `image_cache/`, `images/`, `pairing/`, `sandboxes/`, `hooks/`, `test_rclone_speed/` | 空目錄 |
| `browser_screenshots/`, `pastes/`, `rag/` | rebuildable 暫存/索引 |
| `sessions/` | request_dump 暫存、有敏感資料風險 |
| `state-snapshots/` | 太大（200M）、rebuild 容易 |
| `projects/`, `bin/` | 有 .git 的 rebuildable 專案 / tirith 二進位 |

## 「單一真實來源」模式（避免 rsync 段散落腳本）

**問題**：v4.5 的同步清單是「散落在 9 個 `if [[ -d ... ]] rsync ...` 段裡」、沒有集中管理。問「v4 到底備份了哪些」只能 grep 才知道——**這是維護噩夢**。

**v4.6 解法**：

```
┌─────────────────────────────────┐
│  ~/.hermes/docs/INVENTORY.md    │ ← 單一真實來源
│  - 同步清單（14 個目標）         │
│  - 排除清單（11 個類別）         │
│  - 改檔對照表（改 X 必同步改 Y）  │
└──────────┬──────────────────────┘
           │ 被引用
   ┌───────┴────────┐
   ▼                ▼
hermes-backup-    hermes-backup-
v4.sh             coverage-check.sh
(用 if 段、if 段)   (用 grep 解析 if 段)
```

**`INVENTORY.md` 必含 3 段**：
1. **v4 同步清單**（14 個目標、每個標註為什麼備）
2. **改檔對照表**（改 v4 腳本必同步改 INVENTORY + SKILL §14.1）
3. **變更記錄**（每次擴充記日期 + 理由）

**改 v4 同步清單的 SOP**：
1. 改 `hermes-backup-v4.sh` 加 if 段
2. 改 `INVENTORY.md` 加對應表格行
3. 跑 `bash scripts/hermes-backup-coverage-check.sh` 確認沒出 warning
4. 跑 `bash -n scripts/hermes-backup-v4.sh` 確認 syntax

## hermes-backup-coverage-check.sh 設計（每日 04:00 跑，cron id 651713da919d）

**3 層檢查邏輯**：

### Layer A：本機有、v4 沒列（建議加）

```
對每個本機根目錄的目錄/單檔:
  if 不在 EXCLUDE 清單:
    if 不在 v4 預期清單:
      警告: 本機有 X、v4 沒列、建議加 INVENTORY
```

### Layer B：v4 有列、本機不存在（可能剛搬走）

```
對 v4 預期清單每個目標:
  if 本機不存在:
    標註: ℹ️ v4 預期要備 X 但本機不存在
```

### Layer C：staging vs 本機 SHA256 對比

```
檢查 staging 內的 config.yaml, SOUL.md 跟本機 SHA256 是否一致
檢查 staging 內 archive/, config/, handoff/, reports/ 4 個新增目錄是否存在
```

### EXCLUDE 清單設計（避免誤報）

3 個 EXCLUDE 清單：
- `EXCLUDE_DIRS`（19 個 rebuildable/空目錄/備份本體）
- `EXCLUDE_CACHE_SUBDIRS`（2 個 rebuildable）
- `EXCLUDE_ROOT_FILES`（17 個 Tier 2 加密/hermes runtime 鎖定/快取/rebuildable）

**沒有這 3 個清單會誤報 25 個 warning**（把「Tier 2 加密的 .env」「hermes 內建快取」都當成「漏備」）。

### 輸出格式

```
✅ PASS  備份覆蓋率完整（X 個目錄 + Y 個根目錄檔案都有覆蓋）
⚠️  WARN  備份覆蓋率不完整（N 個 warning）
   建議修法：
     1. 看哪些本機新路徑 v4 沒列
     2. 編輯 INVENTORY.md 加進『v4 同步清單』
     3. 編輯 hermes-backup-v4.sh 加 rsync 段
❌ FAIL  備份完整性檢查失敗（N 個 error, M 個 warning）
```

### Exit code 設計

- 0 = PASS（cron 視為成功、不通知）
- 1 = WARN（cron 視為「非完全成功」、local 通知一次）
- 2 = FAIL（cron 視為錯誤、立刻通知）

## 為何這個設計是「不變的」

即使 v4 升 v5、v6，**模式不變**：

1. **`INVENTORY.md` 當 single source of truth**——v4 腳本跟 coverage check 都讀它，不會「改了腳本忘了改 check」
2. **每日自動掃描路徑變動**——使用者新增目錄時不需記得「v4 有沒有備」，系統會主動警告
3. **3 個 EXCLUDE 清單跟「hermes 上游設計」綁定**——`profile_distribution.py:108` 的 `USER_OWNED_EXCLUDE` 白名單 + `hermes_constants.py:225` 的 consolidated layout，這些是上游固定設計

**如果未來 hermes 改版改了根目錄慣例**（例如把 `state.db` 搬到 `state/state.db`）：
- `hermes-backup-coverage-check.sh` 會自動偵測（本機 vs v4 預期清單比對）
- 出 WARN → 使用者決策
- 改 `INVENTORY.md` + 改 v4 腳本 + 改 EXCLUDE 清單（3 個檔案同步更新）

## 跨 skill 引用

- **`hermes-config-layout`** —— `~/.hermes/` 整體結構 + 磁碟盤點 SOP（互補）
- **`workspace-folder-layout`** —— `~/` 工作區的檔案組織 SOP（不一樣的 class）
- **`alt-token-secrets-layout`** —— GPG 加密 token SOP（Tier 2 加密的內容）
- **`trial-and-error/references/by-category/hermes-backup-strategy.md`** —— 設計演進史

## 設計踩坑（2026-06-10 實際經驗）

### 坑 1：第一版只 warning 不動手 → 噪音太多被忽略

最初版只 Layer A 比對，**沒加 EXCLUDE**——結果 25 個 warning（包含 .env、auth.json、state.db 等本來就不該備份的），變成純噪音。

**修法**：3 個 EXCLUDE 清單（19+2+17 = 38 個排除項），讓 warning 只剩「真的漏備」。

### 坑 2：`patch` tool 連 3 次失敗後沒換策略

第三次失敗時，patch 工具直接給 `_hint`：
> "(1) re-read the file fresh to verify current content, (2) use a longer / more unique old_string with surrounding context lines, or (3) use write_file to replace the entire file if the targeted region is hard to anchor."

**教訓**：patch 工具失敗 2 次以上 → 立即換策略（用更長 context、用 `execute_code` 確認精確字串、別再死磕相同參數）。

### 坑 3：寫 INVENTORY 時只寫「v4 同步清單」、沒寫「改檔對照表」

第一版只列「v4 同步哪些目錄」，**沒寫「改 X 必同步改 Y」**——下次有人改 v4 腳本會忘了同步 INVENTORY。

**修法**：加「改檔對照表」段——這是 §14 修改影響對照表原則（從備份 v4.5 完整化歸納）的一次實踐。

### 坑 4：coverage check 跑出 4 個「staging 落後」warning → 看起來像 bug

跑完 script 出 4 個 warning（archive/、config/、handoff/、reports/ 還沒在 staging 內）——實際是「v4 還沒跑過、所以 staging 沒這幾個目錄」。

**修法**：在 Layer C 加「staging 內應該存在但不在」邏輯，**4 個 warning 才是合理預期**。下次 v4 跑完後會自動消失。

## 對未來 AI 的提示

**If** 你被指派「`~/.hermes/` 看起來很亂，請檢查備份是否完整」**Then** 必走這個流程：

1. 載入 `agent-system-backup` skill
2. 看本 reference 了解 v4 同步清單架構
3. 跑 `bash ~/.hermes/scripts/hermes-backup-coverage-check.sh` 看現況
4. 跑 `grep -rn "get_hermes_home() /" ~/.hermes/hermes-agent/` 找上游 hardcode 的檔案（不要動它們）
5. 跑 `grep -n "USER_OWNED_EXCLUDE" ~/.hermes/hermes-agent/hermes_cli/profile_distribution.py` 看白名單
6. 給使用者評估報告（必含 4 段：總覽圖、決策依據、風險分級、預設計畫）
7. **分批執行**、每批獨立備份 + 驗證
8. 動完跑 coverage check 確認 0 個 warning

**不要**：
- ❌ 從檔名猜測歸屬（看到「cache」就建議搬 cache/）——實際 11/12 會是錯的
- ❌ 跳過 backup 直接 rm
- ❌ 假設「AGENTS.md 引導的路徑 = hermes 實際讀取的路徑」——SOUL.md 就是反例
- ❌ 把「看起來多」當成「真的亂」——28 個檔案只有 4 個是真正亂源
