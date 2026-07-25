# 常駐 Profile 精瘦 SOP（Persistent Profile Lean SOP）

建立「跨 session 持續運作的常駐代理」時的完整步驟，源於 2026-06-09 建立 `market-strategist` + `product-planner` 兩個常駐代理的實戰。**取代舊的「agents/ + persistent-subagent skill」方案**（已於 2026-06-09 清除）。

## 何時使用

**觸發**（任一符合即載入）:

- 使用者說「建一個常駐子代理」「常駐策略代理」「常駐監控代理」「幫我做一個長期代理」
- `hermes profile create <name> --clone` 之後需要精瘦 skill 池
- 任何要在 `~/.hermes/profiles/<name>/` 下建獨立 persona + 專屬 skill 的任務
- 看到舊的 `~/.hermes/agents/*.yaml` 身份檔或 `persistent-subagent` skill → 改走本方案

## 核心觀念

**「常駐代理」≠「派遣 subagent」**:

| 概念 | 工具 | 用途 |
|---|---|---|
| **常駐代理** | `hermes profile` + tmux | 跨 session 持續運作、獨立 persona、獨立記憶、獨立 skill |
| **派遣 subagent** | `delegate_task` | 一次性背景任務、跟主 session 共用記憶 |

兩者完全不同，**不要再混用舊的「常駐 subagent」概念**（MEMORY.md「常駐子代理」L3 教訓）。

## 完整 8 步 SOP（2026-06-10 從 system-architect 建置擴充,加入 SOUL.md + handoff 範本 + 端到端驗證 3 步）

### Step 1 — 建立 profile（含最小目錄結構）

```bash
# 從 default clone 帶設定檔（會帶 197 個 skill，這時是「什麼都有」狀態）
hermes profile create <name> --clone \
  --description "一句話說明這個代理擅長什麼（給 kanban orchestrator 分流用）"
```

**驗證**:
- `hermes profile list` 看到新 profile
- `~/.hermes/profiles/<name>/` 出現完整結構（config.yaml / .env / SOUL.md / skills/）
- `~/.local/bin/<name>` wrapper 自動建立（`PATH` 需含 `~/.local/bin`）

**踩雷**:
- 預先建空的 `~/.hermes/profiles/<name>/` 目錄會讓 `hermes profile create` 撞名報錯 → 先 `rm -rf` 空的再建
- `--clone` 帶的 skill 數量跟 default 一樣多（**這不是 bug，是設計**），精瘦在 Step 4 做

### Step 2 — 寫 persona.md（最重要的一步）

放在 `~/.hermes/profiles/<name>/persona.md`，內容含：

1. **核心信念**（3-5 條，這個代理「在意什麼」）
2. **擅長方法論**（2-5 條專業領域術語）
3. **標準工作流程**（具體 5-7 步，含每步要產出什麼）
4. **交付物格式**（具體 Markdown 結構、章節命名）
5. **與上下游的 handoff**（如果有跨代理協作，明確寫出檔案路徑跟命令）
6. **禁止事項**（3-5 條，這個代理**不做**什麼）
7. **語言與風格**（預設語言、引用風格、不確定性標記）

**這是整個常駐代理的「靈魂」**——沒寫 persona = 這代理跟 default 沒兩樣。

**驗證**:
- 讀得出 3 個具體差異點（跟 default 比，這個代理做了什麼不同的事）
- 跨代理 handoff 段落指向具體檔案路徑

### Step 2.5 — 寫 SOUL.md（人格層、跟 persona.md 互補）**（2026-06-10 新增）**

放在 `~/.hermes/profiles/<name>/SOUL.md`，persona.md 是「這個代理做什麼」、SOUL.md 是「這個代理的語氣」。

**SOUL.md 範本**（5 段）:
1. **語氣特徵** — 3-5 個語氣形容詞 + 行為例（例:「看到 X 會主動停下來、派遣 worker」）
2. **與使用者的互動姿態** — 3-5 條互動原則（反問、報告、不打擾等）
3. **與上下游代理的關係** — 上下游定位 + 邊界 + 不搶對方工作的明確聲明
4. **與 default orchestrator 的關係** — 常駐子代理的標準姿態:不主動接任務、只接受派遣、完成後主動通知
5. **自我審查清單** — 5-10 條「每次任務結束前必跑」的驗證項
6. **哲學(為什麼這樣設計)** — 1-3 條 L3 抽象原則,未來 agent 看了能理解設計動機

**為什麼需要這層**（2026-06-10 驗證）:
- `product-planner` 沒寫自訂 SOUL.md,結果代理開新 session 用的是 hermes-agent 預設語氣,**不夠嚴謹**
- `system-architect` 寫了自訂 SOUL.md,LLM 開 session 自動套用「技術翻譯者」風格,跟 persona 內的 SOP 段互補
- **persona.md = 業務邏輯、SOUL.md = 語氣** — 兩者要對應,但不能重複(避免膨脹)

**如果使用者不指定,預設要寫**(跟其他兩個代理對齊) — 不要假設 hermes 預設就夠好。

### Step 3 — 建立專屬 skill（如果需要）

```bash
mkdir -p ~/.hermes/profiles/<name>/skills/<skill-name>/references
```

每個專屬 skill 含：
- `SKILL.md`：YAML frontmatter（name / description / version / tags）+ 觸發情境 + 標準流程 + 必用工具 + 自我審查
- `references/*.md`：補充文件（檢核表、範本、領域知識）

**驗證**:
- `hermes -p <name> skills list` 看到專屬 skill 且 status = enabled

**多 skill 場景(2026-06-10 驗證)**:
- 主 SKILL 放「6 步 SOP + 交付物格式」(給主 session 載入)
- 配套 SKILL 放「v2 模式的 worker template」(只給 Orchestrator 派遣時用,例:architect-web-worker-template)
- 兩個 SKILL 透過 persona.md 互相引用,**不要把 v2 模板塞進主 SKILL** — 那會讓主 session context 爆掉

**跨 profile 寫入的 soft-guard**(2026-06-10 親身踩到,第 3 次撞到):
從 `default` profile 寫進新 profile 的 `skills/` 會被擋:
```
Cross-profile write blocked by soft guard:
  <file> belongs to Hermes profile '<other>', but the agent is running under profile 'default'.
  To bypass this guard after explicit user direction, retry with cross_profile=True.
```

**修法**:`write_file(path=..., cross_profile=True)`(或 `patch(cross_profile=True)`)
**前提**:使用者已明確指示「動工」或「建好」,這就是 explicit user direction
**警告**:**不要**為了省事預設 `cross_profile=True` 開著 — 會繞過所有 profile 邊界
**驗證**:寫完用 `hermes -p <target> skills list` 看是否 enabled(不同 profile 看到的 skills/ 不一樣)

### Step 4 — 精瘦 skill 池（最常被忽略的關鍵步驟）

`--clone` 帶來 100+ skill，會污染 context、讓代理身份混淆。**必須精瘦到 30-60 個**。

#### 4a — `opt-out --remove` 刪 bundled skill

```bash
hermes -p <name> skills opt-out --remove --yes
```

**效果**:
- 寫入 `~/.hermes/profiles/<name>/.no-bundled-skills` marker（以後 hermes update 不會再 seed 進來）
- 自動刪除 ~65 個 bundled skill（user-edited / hub / local **不刪**，所以專屬 skill 一定保得住）
- 從 ~197 → ~50 個

**驗證**:
- `~/.hermes/profiles/<name>/.no-bundled-skills` 存在
- `hermes -p <name> skills list` 數字大幅下降

**踩雷**:
- 沒加 `--remove` → 只加 marker，現有 skill 一個都沒刪
- 不加 `--yes` → 會卡在互動式確認

#### 4b — 用 Python 讀磁碟真實清單 + 設計白名單 + 批次刪

**`hermes skills list` 的數字會騙人**（CLI 把每個 skill 的子目錄都當 enabled 算）→ **以磁碟 `ls` 為準**。

```python
import os, shutil

PROFILE_DIR = os.path.expanduser("~/.hermes/profiles/<name>/skills")
all_skills = set(os.listdir(PROFILE_DIR)) - {".hub", ".bundled_manifest", ".curator_backups"}

# 白名單（共同 + 專屬）
COMMON_KEEP = {"general-workflow", "user-collaboration-style", "trial-and-error", ...}
KEEP = COMMON_KEEP | {"<自己專屬的 skill>", ...}

# 必保留保險（雙重檢查）
MUST_KEEP = {"<自己專屬>", "general-workflow", "trial-and-error"}

to_remove = sorted(all_skills - KEEP)
for name in to_remove:
    if name in MUST_KEEP:
        print(f"  ✗ REFUSE: {name}")
        continue
    path = os.path.join(PROFILE_DIR, name)
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path):
        os.remove(path)
```

**驗證**:
- `ls ~/.hermes/profiles/<name>/skills/ | wc -l` 剩 30-60 個
- 必保留 5 個 skill 全部還在
- 主代理（default）的 `~/.hermes/skills/` 數字**不變**

**白名單設計原則**:
- 共同保留（任何代理都需要）：`general-workflow` / `user-collaboration-style` / `trial-and-error` / `workspace-folder-layout` / `anti-panic-protocol` / `python-*` / `web_search` / `agent-browser` / `browser` / 輸出格式（`minimax-docx` / `pdf` / `xlsx` / `pptx-generator` / `beautiful-mermaid` / `diagram-generator`）
- 專屬保留：依 persona.md 內的「必用工具」清單挑
- 刪除原則：**任何「這個代理不會用到的」就刪**——不要「先留著以防萬一」

### Step 5 — 驗證整體

**5 個必跑檢查**:

```bash
# 1. 專屬 skill 還在
ls -la ~/.hermes/profiles/<name>/skills/<self-skill>/SKILL.md

# 2. persona.md 存在且有實質內容
wc -l ~/.hermes/profiles/<name>/persona.md
# 應該 > 50 行

# 3. opt-out marker 寫入
ls ~/.hermes/profiles/<name>/.no-bundled-skills

# 4. 精瘦後 skill 數量合理
ls ~/.hermes/profiles/<name>/skills/ | wc -l
# 應該 30-60 個

# 5. 主代理（default）沒被影響
ls ~/.hermes/skills/ | wc -l
# 應該跟之前一樣（196 左右）
```

**冒煙測試**:
```bash
hermes -p <name> skills list 2>&1 | grep <self-skill>
# 應該看到 status: enabled

hermes -p <name> chat
# 開新 session 確認 persona 生效（開場會引用 persona 內容）
```

## 備份策略要點

常駐 profile 的備份要特別注意：

- **每個 profile 自己的 `skills/` 是獨立的**——備份時要包含所有 `~/.hermes/profiles/<name>/` 目錄
- **`.no-bundled-skills` marker 一定要備**——重灌後少了 marker，hermes update 會把所有 bundled skill 又塞回來
- **`persona.md` 一定要備**——沒了 persona 整個代理就空殼
- **不要備** `~/.hermes/agents/`（舊方案，已於 2026-06-09 清除）

見 `hermes-config-layout/references/backup-architecture-v4.md` 內的「profile 目錄清單」段。

### Step 5.5 — 建立 handoff 範本(2026-06-10 新增,給有上下游的代理用)

**適用情境**:這個代理要接 handoff(讀上游的產出)或要交棒給下游代理。

**動作**:
```bash
mkdir -p ~/.hermes/handoff/_template/<this-agent-deliverable>/
# 建 3-5 份 .template.md 範本(給未來每個專案 clone 使用)
```

**範本要含**:
- 章節結構(用 `##` / `###` 標好層級,代理人複製後填空)
- 「1 小時上手 checklist」(給下游代理驗收的介面保證)
- 自我審查清單(交付前必跑)
- 複雜度判斷(S/M/L 三級 → 產幾份文件)
- Mermaid 圖模板(架構類代理)或 API 規格範本(後端類代理)

**現有範例**:`~/.hermes/handoff/_template/architecture/`(2026-06-10 建 system-architect 時的 5 份範本 + README)

### Step 5.7 — 端到端真實跑驗證(2026-06-10 新增,INTJ 必跑)

**為什麼需要這步**:寫完 persona + SOUL + skill + 精瘦後,**外觀上看起來建好了**,但使用者(INTJ)期待「真的跑了一次才算交付」,不是「看起來能用」。

**做法**:
```bash
# 1. 找一個真實的現有 handoff 專案(用既有 PRD)
# 2. 設定 timeout 600s(10 分鐘); 預期跑 4-5 分鐘
# 3. 用 --cli non-interactive 模式
hermes -p <name> chat -q "<明確的子任務 prompt>" --cli
# 4. 驗證產出檔案存在 + 內容合理
ls -la ~/.hermes/handoff/<project-slug>/<expected-file>.md
wc -lc <expected-file>.md
```

**prompt 設計關鍵**(2026-06-10 驗證):
- **給明確的子任務範圍** — 不要說「跑個完整流程」(會跑 30+ 分鐘),改說「跑 Step 1-2 產出架構盲點 + 系統脈絡圖」
- **明確告知「把產出寫到 handoff 目錄」** — `--cli` 模式**沒有** `send_message` 工具,代理會誤以為可以通知 default,實際寫到檔案才是可靠的
- **明確告知「完成後只輸出完成訊息 + 檔案路徑」** — 不要讓代理試著 send_message

**驗證**:
- `ls -la <expected-file>.md` → 檔案存在
- `wc -lc <expected-file>.md` → 至少 5KB 才有實質內容
- `head -50` 讀開頭 → 確認 persona 內的語氣跟 SOP 都被套用
- 必含「給下游的 1 小時上手 checklist」段(per persona 自我審查)

**常見失敗**:
- ❌ 跑 30+ 分鐘(沒設 timeout)→ 600s 後被砍,半成品浪費
- ❌ 代理假裝完成但沒寫檔(把結果印到 stdout)→ orchestrator 撈不到
- ❌ 代理試著用 `send_message` 通知 default → CLI 模式沒這個工具,失敗但假裝 OK

**If** 端到端驗證失敗 **Then** 修 persona/SOUL 對應段(例:加明確的「不要 send_message,只寫檔」),重跑驗證

## 常見錯誤（pitfalls）

❌ **只建 profile 不寫 persona** → 這代理跟 default 沒兩樣，等於沒建

❌ **用 `hermes profile create` 不加 `--clone`** → 全新空 profile，沒有 config.yaml / .env / SOUL.md，要手動補

❌ **用 `hermes profile create --no-skills`** → 連 197 個 skill 都不帶，但你仍要 opt-out --remove 才能確保未來不會 seed 回來

❌ **看到 `hermes skills list` 數字就直接相信** → 那是「子目錄也算 enabled」的數字，跟磁碟 ls 不一致

❌ **精瘦完沒驗證 default 沒被影響** → 刪錯可能會把 default 的 skill 也掃掉

❌ **寫了 persona.md 卻忘了把白名單同步** → 代理跑起來還是用 default 的 skill 池，身份混淆

❌ **用舊的 `~/.hermes/agents/*.yaml` 身份檔** → 2026-06-09 已清除，新方案一律走 profile

❌ **沒寫 SOUL.md 依賴 hermes 預設語氣** → 預設是「友善但通用」,不夠嚴謹;每個常駐代理都應該有自訂 SOUL(2026-06-10 新增 pitfall)

❌ **沒建 handoff 範本** → 未來這個代理接任務時不知道交付物的具體 Markdown 結構(2026-06-10 新增 pitfall)

❌ **沒做端到端真實跑驗證就交付「建好可用」狀態** → INTJ 使用者期待「真的跑了才算交付」,不是「看起來能用」(2026-06-10 新增 pitfall)

## 與其他 skill 的關係

- **hermes-config-layout** (本 skill) —— 觸發入口，profile 結構 + 改動 SOP
- **trial-and-error/references/execution-sop.md SOP-4** —— L3 教訓分流（本 SOP 屬於 SOP-5 候選，可考慮補入）
- **MEMORY.md「常駐子代理 = profile + tmux」L3 教訓** —— 抽象決策原則，本檔是具體步驟

## 維護

- **2026-06-09 初版**：源於市場策略代理 + 產品規劃代理建立實戰
- **2026-06-10 從 5 步擴充到 8 步** — 新增 Step 2.5 (SOUL.md)、Step 5.5 (handoff 範本)、Step 5.7 (端到端真實跑驗證);新增 4 條 pitfall(沒寫 SOUL、沒建 handoff 範本、沒做端到端驗證、跨 profile soft-guard)
- **若 hermes 加新 skill 種類或 opt-out 行為改變** → patch 本檔
- **若發現更好的白名單設計模式** → patch 並加新範例
