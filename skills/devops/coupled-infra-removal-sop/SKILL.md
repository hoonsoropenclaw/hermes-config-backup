---
name: coupled-infra-removal-sop
description: "Disaster-safe removal workflow for infrastructure the agent itself depends on. TRIGGER when user says 'remove/uninstall/delete X' and X is a service, tool, package, or runtime that this agent, its MCPs, or another production system consumes (custom CLI tool, MCP server, daemon, cron-driven service, OAuth-providing app). 4 phases: (1) 依賴盤點 — find every dependency and write it down, (2) 備份 + 路徑轉移 — mirror critical data to an external location and change script paths to read from there, (3) 健康驗證 — confirm the agent and downstream systems still run from the new location, (4) 規劃 — write a multi-option removal plan with risks and ask for user sign-off BEFORE any destructive step. Core principle: 不可逆動作前必須有可逆備份 + 驗證證據;沒有驗證證據不動手。"
version: 1.0.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [DevOps, Migration, Safety, SOP, Destructive, Uninstallation, Removal]
    related_skills: [trial-and-error, deployment-verification-sop, general-workflow, hermes-config-layout]
trigger:
  keywords:
    - 移除
    - 卸載
    - 反安裝
    - 清除
    - uninstall
    - remove
    - 砍掉
    - 刪除
    - 清掉
    - 不要了
  when_agent_depends_on_target: true
---

# Coupled Infrastructure Removal SOP

> **核心鐵律**: 不可逆動作前必須有可逆備份 + 驗證證據。沒有驗證證據不動手。
>
> 2026-06-08 從移除一個耦合度極高的 gateway/CLI agent（OpenClaw 3.8GB + 11 cron + 3 MCP + 1 OAuth flow + 1 status site 源頭）建立。使用者明確要求「先備份/轉移/驗證,再規劃」的 4 階段流程。

## 為什麼需要這個 SOP

**錯誤示範**（沒有這個 SOP 時的本能反應）:
- 使用者:「請把 X 移除」
- agent: `sudo npm uninstall -g X` → 然後發現 X 提供的 MCP、cron、token、config 全部一起被砍 → agent 自己或別的服務 crash

**正確示範**（套用這個 SOP）:
- agent 先**依賴盤點** → 發現 X 跟 11 個 cron、3 個 MCP、1 個 OAuth flow、1 個 status site 源頭耦合
- agent **誠實報告**這個耦合度、給 3 個風險分級方案
- 使用者選一個 → agent 才**備份/轉移/驗證** → **規劃** 移除動作（不再動手,要再次審核）

## 觸發條件（任一符合即觸發）

- 使用者說「移除 / 卸載 / 反安裝 / 清除 / uninstall / remove / 砍掉 / 清掉 X」**且**
- X 是 agent / 生產服務 正在依賴的東西（process 還在跑、config 還在讀、MCP 還在連、cron 還在用、token 是它發的）
- 涉及 service / daemon / CLI tool / MCP server / 套件層級的移除（不是單純的「刪一個檔案」）

**不要觸發**（不是這個 SOP 範圍）:
- 純刪檔案/資料夾（看 trial-and-error 的 `bash-defensive-patterns` 跟 backup SOP）
- 「幫我把 X 專案清掉」— 那是 git/GitHub 操作,不是 system infra
- 「幫我重新整理」— 沒有破壞性

## 4 階段流程

```
使用者要求移除 X
       │
       ▼
[Phase 1: 依賴盤點]  ← 任何其他動作前必跑
       │
       ▼
[Phase 2: 備份 + 路徑轉移]  ← 不刪任何東西
       │
       ▼
[Phase 3: 健康驗證]  ← 跑 10 項健康檢查
       │
       ▼
[Phase 4: 規劃]  ← 寫多方案 + 用戶簽核
       │
       ▼
（等使用者批准具體方案 → 才進實作）
```

### Phase 1: 依賴盤點（5-15 tool calls）

**目的**: 找出 X 跟哪些東西耦合。**不動任何檔案**,只讀。

**必查清單**:

| 類別 | 必查命令 |
|------|----------|
| 進程 | `ps aux \| grep -iE 'X\|X-相關'` |
| systemd | `systemctl --user list-units --all \| grep -iE 'X'`、找 `~/.config/systemd/user/X*` |
| cron | `crontab -l`、找 `/etc/cron.d/X*` |
| 套件 | `npm list -g`、`pip list`、`dpkg -l \| grep X` |
| 設定檔 | `find ~ /etc -name '*X*' 2>/dev/null` |
| 資料目錄 | `ls -la ~/X ~/X-data ~/.X ~/.config/X 2>/dev/null` |
| 符號連結 | `readlink -f $(which X)` 找出 X 真正的 source path |
| 環境變數 | `env \| grep -iE 'X\|X_TOKEN\|X_KEY'` |
| 對外通訊 | `ss -tlnp` 看 X 在監聽哪些 port |
| Agent 自己 | 查 `~/.hermes/config.yaml` MCP 區段、查 `mcp_servers` 設定 |

**產出**: 一份依賴清單,**包含每個依賴的位置、大小、影響範圍**。

**給使用者的回報結構**:
```
X 佔據的全貌（已驗證事實）

A. 套件本體
- <path> （大小, 內容）
B. systemd 服務
- <service> （狀態: active/inactive）
C. cron jobs
- N 條全部指向 <path>...
D. 資料目錄
- <dir>（大小, 結構）
E. Agent 跟 X 的耦合
- MCP 設定、MEMORY 記錄、bash hook
F. X 自帶的反安裝機制
- <uninstall 指令>（--dry-run 試過）
```

### Phase 2: 備份 + 路徑轉移（10-30 tool calls）

**原則**:
1. **先建外部目錄**（`~/backups/X-migration-<date>/` 跟 `~/shared-infra/`）
2. **純複製不移動**（用 `cp -p` / `rsync -a` / `tar czf`）
3. **驗證 byte-level 一致**（`md5sum` 或 `diff -rq`）
4. **改路徑先評估技術限制**（見下方 Pitfall）

**必做的備份**:
| 物件 | 備份方式 | 目的地 |
|------|----------|--------|
| 設定檔（含所有備份版本）| `cp -p` 全部 | 兩個地方各一份 |
| systemd units | `cp -p` | backups 內 |
| crontab | `crontab -l > backup.txt` | backups 內 |
| bashrc.d 腳本 | `cp -p <name>.original` | 保留原版以利回滾 |
| 資料庫 | `rsync -a` + md5 驗證 | shared-infra 內 |
| OAuth token / API key | `cp -p` mode 600 保留 | shared-infra/secrets/ |
| 執行期輸出（如 dashboard 引擎）| `tar czf` | backups 內 |
| **現有 token 重新驗證** | 輕量 API 測 | N/A |

**OAuth/API token 特別處理**（2026-06-08 從 youtube_tokens.json 學到）:
- 若有兩份並存,**用 refresh_token 實測**決定哪份是 master
- access_token 過期不代表 refresh_token 過期
- 兩份 refresh_token 都失敗 → 需要重新跑 OAuth
- 修好後**先備份舊檔**（`<name>.pre-refresh-<date>`）再寫新

**「路徑轉移」的技術限制**（必看 Pitfall）

並非所有東西都能改路徑。要先讀 source code 找 `os.path.expanduser` / `Path.home()` / 寫死路徑的字串。

| 類型 | 可改路徑? | 怎麼做 |
|------|----------|--------|
| 純資料檔（JSON / SQLite）| ✅ | `cp` 或 `rsync` 即可 |
| CLI 工具（讀 config）| 部分 | 看 config 是寫死還是可 env var 覆蓋 |
| Python 套件（`~/.local/lib/.../foo/`）| ❌（除非改 source）| 寫死的 `os.path.expanduser("~")` 沒救 |
| systemd service | ✅ | 改 `ExecStart` 跟 `Environment=` 行 |
| cron jobs | ✅ | 直接 `crontab -e` 改路徑 |
| bashrc.d 腳本 | ✅ | 直接改 |

**If** Python 套件寫死 `~/.X` base path **Then** 不能用「改路徑」完全解耦,只能:
- (a) 用 symlink `~/.X → ~/shared-infra/X/`（但砍目標時會把 symlink 一起砍）
- (b) 用 env var 覆蓋**部分**路徑（如 `MEMPALACE_PALACE_PATH`）
- (c) 接受「設定檔在原位、資料在別處」的不對稱狀態

**必做**: 給使用者一份**誠實**的「哪些能改、哪些不能改」清單,**不要假裝能改不能改的東西**。

### Phase 3: 健康驗證（10-20 tool calls）

**絕對必跑**的 10 項驗證,全部寫進規劃文件 §6 驗證清單,**10/10 全綠才進 Phase 4**。

```bash
# 1. 目標服務還在跑（移除前狀態基準）
systemctl --user is-active <X>.service  # 預期 active

# 2. 相關 timer / 排程還在跑
systemctl --user is-active <X>.timer  # 預期 active

# 3. 關鍵進程還在跑
ps -p <PID> -o cmd  # 預期顯示完整指令

# 4-5. Agent 用的工具仍能 work
# （直接呼叫一個 MCP 工具 / 跑一個搜尋指令）
# 預期: 至少 1 個結果 / 預期資料數量

# 6. HTTP 健康端點還在回
curl -s --max-time 5 http://localhost:<port>/health  # 預期 200

# 7. bashrc.d 改路徑後啟動無報錯
bash ~/.bashrc.d/<X>_check.sh  # 預期 0 輸出、marker 寫入

# 8. 部署源頭（若有）仍在
ls <deploy-source>/.git/config  # 預期 exists

# 9. 部署源頭 git log 仍正常
cd <deploy-source> && git log -1 --format='%h %s'  # 預期有 commit

# 10. 備份與轉移目錄大小合理
du -sh <backup-root> <shared-infra-root>  # 預期都有內容
```

**If** 任一項不過 **Then** Phase 2 沒做好、回去補完才能進 Phase 4。

**If** 涉及「資料移到 shared-infra、用 env var 啟動新 MCP」**Then** 額外跑:
```bash
<ENV_VAR>=<new-path> python3 -c "<import-and-test>"
# 預期: 從新路徑能讀到資料、搜尋有結果
```

### Phase 4: 規劃（5-10 tool calls 寫文件）

**不要直接給指令碼**。**寫一份**規劃文件,包含:

1. **§1 已完成備份轉移**（貼路徑、大小、md5、權限）
2. **§2 技術限制**（誠實列出做不到的、symlink/env var workaround）
3. **§3 多方案**（A 不可逆 / B 半可逆 / C 最保險,各列動作清單 + 風險 + 預估時間）
4. **§4 推薦順序**
5. **§5 未來清理**（跟本次無關但順便發現的）
6. **§6 驗證清單**（Phase 3 跑完貼輸出,**全部打勾**）
7. **§7 動手前的最終確認**（使用者勾完才能進 §3）

**最少要給 3 個方案**（不可逆/半可逆/最保險）讓使用者選。**不要假設使用者會選最激進的**。

**必含的「不要動的東西」清單**:
- 哪個目錄刻意不刪（保護使用者資產）
- 哪個服務刻意不停（避免 cascade failure）
- 哪個 token 刻意不刷（避免觸發 re-auth 流程）
- 哪個 config 刻意不改（避免重啟時炸掉）

## 4 個常見的「假裝能做到」陷阱

### 陷阱 1: 假裝能改 Python 套件寫死的路徑

**情境**: 某個套件 `config.py` 寫死 `Path(os.path.expanduser("~/.X"))`,預設 base path 不可改。
**錯誤做法**: 把 config.json 內某個 path 改成 `/shared-infra/...`,假裝這就是「路徑轉移」。
**後果**: 啟動時讀得到 config（部分路徑 env var 覆蓋 OK）但其他附屬檔（locks/、registry、wals）仍然寫到 `~/.X` —— 資料分裂。
**正確做法**: 誠實說「只能用 env var 覆蓋一部分、其餘路徑仍然寫死」,讓使用者決定要不要接受這個限制。

### 陷阱 2: 用「access_token 過期」判定 token 死亡

**情境**: OAuth token 兩份並存,access_token 1 小時後過期是正常。
**錯誤做法**: 看到 401 就以為 refresh_token 也死了。
**正確做法**: 用 `grant_type=refresh_token` POST 到 token endpoint,**refresh_token 過不過期才是真的死/活**。

### 陷阱 3: 用「mtime 較新」判定 master

**情境**: 同樣的 token / config 兩份並存,`A/` 那份 mtime 較新。
**錯誤做法**: 直接假設新的是 master。
**正確做法**: 用實際 API 測試（輕量 endpoint 如 `channels.list?mine=true&maxResults=1` 或 `<resource>.get` 1 quota unit）。`mtime` 只能當線索,不是證據。

### 陷阱 4: 「砍 cron 就好、保留資料」= 假可逆

**情境**: 移除服務時只 `crontab -r`、保留資料目錄。
**錯誤做法**: 認為這樣「半可逆」、可以 `setup` 救回。
**後果**: N 條 cron 在刪掉後、資料目錄內的執行期引擎、subagent、identity 等子目錄**已無守護進程在同步**,資料會開始 stale。
**正確做法**: 要嘛全留（方案 C）,要嘛真的卸載（方案 A/B）。不要做「半吊子卸載」。

## If→Then 速查

- **If** 使用者要移除「正在被 agent 依賴」的服務 **Then** 必走這個 SOP,不要直接下 `uninstall` 指令
- **If** Phase 1 盤點發現耦合度 > 5 個層面 **Then** 給使用者 3+ 方案而不是 1 個,等他選
- **If** 涉及 Python 套件寫死 `~/.X` 路徑 **Then** 不要假裝能「改路徑」,誠實標示限制
- **If** 兩份並存的 token / config / 資料 **Then** 用「輕量 API probe」決定 master,不是用 mtime / 檔名
- **If** Phase 3 驗證沒跑完或沒全綠 **Then** 不進 Phase 4,回去補 Phase 2
- **If** Phase 4 規劃文件沒給至少 3 個風險分級方案 **Then** 補上
- **If** 規劃文件沒經使用者批准 **Then** 不執行 §3 任何動作

## 與其他 skill 的關係

| 技能 | 何時優先載入 |
|------|-------------|
| `trial-and-error` | 觸發詞命中時**先載入**（必走 SOP §0 強制載入） |
| `deployment-verification-sop` | Phase 3 健康驗證時,參考它的 4 步驗證法 |
| `general-workflow` | 大型工作流的進度追蹤、回報格式、🟢/🔴 指示燈 |
| `hermes-config-layout` | 改 `~/.hermes/config.yaml` MCP 區段時 |
| `hermes-config-tuning` | cron jobs 改路徑時（避免 wakeAgent gate 影響 silent/not） |

**分工**:
- `trial-and-error` 處理**個別雷點**（症狀導向、給修法）
- 本 skill 處理**整套破壞性作業流程**（4 階段 + 多方案 + 驗證）
- `deployment-verification-sop` 處理**部署後**驗證（curl + DNS + browser）
- `general-workflow` 處理**任務分派 + 回報**（指示燈、進度追蹤）

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-06-08 | 從 OpenClaw 移除計畫建立。4 階段流程 + 4 個常見陷阱 + If→Then 速查 |
