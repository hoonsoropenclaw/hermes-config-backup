---
name: backup-coverage-check
description: |
  每日自動驗證備份腳本的「同步清單完整性」——掃 ~/.hermes/ 跟 v4 同步清單比對，找出「該備但沒備」或「有備但本機不存在」的路徑變動。**任何備份系統的設計都應配套這個自動檢查**——避免「備份跑得很順、但其實漏了 6 個關鍵目錄」這種 silent failure。
  觸發:備份腳本改完、新加/移除同步路徑、使用者說「檢查備份有沒有漏」「為什麼 archive/ 沒被備份」時。
  3 層檢查:Layer 1 路徑比對(每天)、Layer 2 staging 同步驗證(每天)、Layer 3 GitHub 同步驗證(每週,不在 cron 每日範圍)。
---

# Backup Coverage Check — 備份同步清單完整性自動檢查

## 何時使用

**觸發**(任一符合即載入):

- 任何備份腳本設計/改完之後,驗證「我有沒有漏同步某個重要目錄」
- 使用者問「為什麼 X 沒被備份」「備份覆蓋率多少」「有什麼路徑變動沒被備份」
- 備份架構演進時(加新常駐目錄、改架構、cleanup 任務之後)
- 接手別人的備份系統、不確定覆蓋率

**Always-on 提醒**:本 skill 是「備份系統的 backup」——備份本身要可靠,**驗證備份有沒有漏**同樣要可靠。任何備份設計必配套本 skill 的 cron job。

## 核心觀念:備份 silent failure

**情境**(2026-06-10 真實事件):

- v4 備份腳本(v4.5,雙層 GPG 加密,看起來非常完善)只同步 7 個目錄 + 1 個檔
- 但 `~/.hermes/` 根目錄有 21 個檔案 + 13 個目錄(v4 完全沒碰)
- 其中 7 個關鍵目錄漏備:`archive/`、`config/`(含 .hermes-user-key 必備)、`handoff/`、`reports/`、`cache/youtube/`、`cache/documents/`、`logs/`
- **備份跑得很順、雙層加密驗證 PASS、Drive 也有檔案——但其實漏了 .hermes-user-key**(沒它 cron 跑 Tier 2 加密會壞)
- 使用者直到 2026-06-10 主動問「今天變動的檔案是否有漏備」才發現

**教訓**:
- 備份成功 ≠ 備份完整
- 雙層加密、USER_KEY 驗證、Drive push 成功——這些驗證「備份機制本身能跑」,但**不驗證「我備了所有該備的東西」**
- 路徑會隨時間演進(新加目錄、清理任務、profile 建立),但備份腳本不自動跟著演進

## 設計:3 層檢查

### Layer 1:路徑比對(每天跑,核心)

**目的**:找出「該備但 v4 沒備」或「v4 有備但本機不存在」的路徑變動

**輸入**:
- `~/.hermes/` 根目錄所有「目錄」跟「單檔」
- `INVENTORY.md` 的「v4 同步清單」段(單一真實來源)

**輸出**:
- PASS:清單完整,沒有漏
- WARN:有新路徑未列入清單(可能是漏備份、也可能是刻意跳過)
- FAIL:清單裡的目錄本機不存在(可能是備份腳本刪除了目標、或搬移了路徑)

**Script 設計**:見 `scripts/coverage_check.sh` template

### Layer 2:staging 同步驗證(每天跑,補 Layer 1 不足)

**目的**:比對 `~/.hermes/hermes-backup-staging/` 跟 `~/.hermes/` 同步狀態,找出「本機有但 staging 沒」(= 漏同步)

**輸入**:
- `~/.hermes/hermes-backup-staging/` 內容
- `~/.hermes/` 內容(透過 rsync `--dry-run` 或 `find` + 比對)

**輸出**:
- WARN:有本機檔案沒在 staging(可能是 v4 rsync 排除、可能是 staging 漏跑)

**注意**:Layer 1 + Layer 2 互補——Layer 1 抓「該備但沒列」、Layer 2 抓「有列但 staging 沒同步到」

### Layer 3:GitHub 同步驗證(每週跑,不在 cron 每日範圍)

**目的**:確認 staging 跟 GitHub 遠端一致

**輸入**:
- `git -C hermes-backup-staging log` vs `git -C hermes-backup-staging status`
- `git fetch` 對比 origin/main SHA

**輸出**:
- FAIL:有 commit 沒 push、push 卡住、remote 拒絕(見 `agent-system-backup` §10.6、§10.7)

## 設計原則

### 1. 不自動修,只警告

**不要**寫「發現漏備 → 自動加 rsync 段到備份腳本」這種自動修邏輯。理由:

- 自動修可能誤刪誤搬(USER.md 寫「INTJ、效率優先、要求完整」,自動修風險高)
- 「該不該備」的判斷需要 context(看到 200M state-snapshots 不該備、但 archive/ 該備——這需要對系統的理解,不是 grep 能做的)
- 腳本只負責「找漏 + 通知」,修補決策留給人或下次 session 處理
- 跟 MEMORY.md 規範「不主動寫記憶、要明確指示才做」一致

### 2. INVENTORY.md 當 single source of truth

**任何備份系統都該有**一份「同步清單」文件,放在 `INVENTORY.md` 裡:

```markdown
## v4 同步清單

### 目錄
- agents/ — 用戶身份代理配置
- memories/ — 7 個重要檔案
- ...

### 單檔
- config.yaml — 主設定
- SOUL.md — 根目錄主版(不是 memories/)
- ...

### 排除
- hermes-agent/ — upstream clone,可 git pull 重建
- state.db* — hermes runtime 鎖定檔,Tier 2 加密備份
- ...
```

**好處**:
- 備份腳本跟 coverage check 都從 `INVENTORY.md` 讀清單,改清單不用改兩個地方
- 未來 AI 接手時一眼看到「這個備份系統覆蓋哪些路徑」
- coverage check 跟清單對照、找出偏差

### 3. 通知策略

- **PASS**:不通知(避免噪音)
- **WARN**:寫到 `~/.hermes/logs/backup-coverage-warn.log`、每週累積一次通知(避免每天 spamm)
- **FAIL**:立刻 local notify(重要錯誤、不能等)

### 4. 排程避開備份 cron

- v4 備份通常跑凌晨 3 點(見 `agent-system-backup` §6)
- coverage check 排凌晨 4 點(避開、確保備份已完成)

## 實作 SOP

### Step 1:在 `INVENTORY.md` 建立「v4 同步清單」段

如果備份腳本還沒用 INVENTORY.md,先建清單(從腳本 grep 出 rsync 跟 cp 段、列出「目錄」「單檔」「排除」三類)。

### Step 2:寫 coverage check script

放在 `~/.hermes/scripts/hermes-backup-coverage-check.sh`(hermes cron 預設從這找),內含:
- 讀 `INVENTORY.md` 解析清單
- `find ~/.hermes/ -maxdepth 1` 掃根目錄
- 對照、輸出 PASS/WARN/FAIL
- 寫 log 跟必要時通知

### Step 3:加 symlink 到 scripts/(hermes cron 規範)

```bash
ln -sf ~/.hermes/skills/backup-coverage-check/scripts/coverage_check.sh \
       ~/.hermes/scripts/hermes-backup-coverage-check.sh
```

### Step 4:加 cron job

```json
{
  "id": "<uuid>",
  "name": "hermes-backup-coverage-check",
  "prompt": null,
  "script": "hermes-backup-coverage-check.sh",
  "no_agent": true,
  "schedule": {"kind": "cron", "expr": "0 4 * * *", "display": "0 4 * * *"},
  "enabled": true,
  "deliver": "local"
}
```

### Step 5:跑一次驗證

```bash
bash ~/.hermes/scripts/hermes-backup-coverage-check.sh
# 預期: 輸出 3 層結果、寫 log、依通知策略處理
```

### Step 6:驗證 cron job 排程

```bash
hermes cron list 2>&1 | grep -A 8 "name: hermes-backup-coverage-check"
# 預期: next_run 是明天 4 點、last_status 為 ok
```

## 「哪些該備、哪些不該備」決策樹

備份設計時遇到「X 目錄該不該備份」時的判斷:

```
Q1. 這個目錄是 hermes 系統設計就在這的、程式碼有 hardcode 路徑嗎?
   → 是 → 必備(失敗重建成本高,例如 config/, archive/)
   → 否 → Q2

Q2. 這個目錄的內容可以從其他來源 rebuild 嗎?
   → 是 → 不備(例如 hermes-agent/ 從 upstream 重建、image_cache/ 重新生成)
   → 否 → Q3

Q3. 這個目錄的內容有多大、會撐大備份嗎?
   → < 100MB → 必備
   → 100MB-1GB → 評估「重建成本 vs 備份成本」
   → > 1GB → 通常不備(state-snapshots/ 200MB 雖 < 1GB 但 pre-update 快照可重建)

Q4. 這個目錄的內容含敏感資料嗎?
   → 是(API key、token、user data)→ 必備 + 走 Tier 2 GPG 加密
   → 否 → 走 Tier 1 GitHub 公開

Q5. 這個目錄的內容是「使用者的真實工作產出」嗎?
   → 是(handoff/、reports/、projects/ 任務成果)→ 必備
   → 否(純暫存 cache、screenshot、debug dump)→ 不備
```

## 已知陷阱

### 陷阱 1:SOUL.md 路徑陷阱

**見 `hermes-config-layout` SKILL §「Pitfall:SOUL.md 必讀根目錄」**——備份腳本常誤把 SOUL.md 備份到 `memories/`,但 hermes 載入的是根目錄的版本。coverage check 必須掃根目錄**跟** memories/,且警告「兩份內容不一致」。

### 陷阱 2:.env / auth.json / state.db 走 Tier 2 不走 Tier 1

coverage check 不要把這些檔案列入「Tier 1 漏備」警告——它們走 Tier 2 GPG 加密,本來就不在 Tier 1 範圍。

### 陷阱 3:config/ 子目錄

v4 設計沒同步 `config/` 目錄,但裡面有 `.hermes-user-key`(cron Tier 2 加密必備)。**coverage check 必須把 `config/` 列為「必備但 v4 漏備」**——這是 2026-06-10 真實事件。

### 陷阱 4:staging 跟本機「本來就該有差異」

`hermes-backup-staging/` 是備份 staging 區,本來就會跟本機有差異(它已經篩選過了)。coverage check 比對時要理解「staging 內容 ⊆ 本機內容」是正常的,反過來才不正常。

### 陷阱 5:備份本體的備份

`hermes-backup-staging/` 跟 `backups/` 內是備份本體,**不能備份自己**(會無限遞迴、撐爆 Drive)。coverage check 必須把這兩個目錄列為「永遠排除」,不要誤判為「該備但沒備」。

## 修改影響對照表

| If 改這個 | Then 必同步改 |
|---|---|
| 備份腳本(hermes-backup-v4.sh) | `INVENTORY.md`「v4 同步清單」段 + coverage check script + `agent-system-backup` SKILL §14 |
| `INVENTORY.md`「v4 同步清單」 | coverage check script 自動生效(因為它從 INVENTORY.md 讀)、備份腳本(若還 hardcode 要改成 grep INVENTORY.md) |
| 任何新增/移除 `~/.hermes/` 子目錄 | 跑一次 coverage check 看是否觸發 WARN(若是 → 決定補進清單或加排除) |
| coverage check script | `agent-system-backup` SKILL §10.5.2 提到的「讀 INVENTORY.md 設計」不變,但實作細節會跟著改 |
| cron job 排程 | `agent-system-backup` SKILL §6 + `cron-job-health-monitor` 提到的新 job |

## 與其他 skill 的關係

- `agent-system-backup` — 上游備份系統,本 skill 是它的驗證層
- `workspace-folder-layout` — 工作區分類 SOP,coverage check 對照用的「哪些該備」決策從這延伸
- `hermes-config-layout` — SOUL.md 路徑陷阱在本 skill 引用
- `cron-job-health-monitor` — coverage check 本身是個 cron job,失敗時用這個 skill 診斷
- `coupled-infra-removal-sop` — 卸載/清理前必先看「這個目錄還活著嗎」,跟 coverage check 互補

## 支援檔

- `scripts/coverage_check.sh` — Layer 1 + Layer 2 檢查 script template
- `references/decision-tree.md` — 詳細的「哪些該備」決策樹
- `references/notifications.md` — WARN/FAIL 通知策略
