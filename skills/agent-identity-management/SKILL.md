---
name: agent-identity-management
description: 代理身份管理 — 處理「多代理 / 多名稱 / 身份繼承 / 命名空間合併 / 跨檔案身份同步 / **身份重塑 (role pivot)** / **代理內部 SOP 演進 (sop evolution)**」這類任務。當使用者說「身份繼承」「改名字」「合併兩個代理」「重新命名」「你是 X 不是 Y 了」「7 份重要檔案同步」「代理身份重新定義」「**重塑代理**」「**重新定位**」「**換個角色**」「**不要再做 X 了**」「**這個代理換個跑法**」「**改成多代理分工**」「**升級架構**」等關鍵字時喚醒此技能。**赫米斯特有的 class-level skill**(基於 2026-06-08 身份繼承 + 2026-06-10 身份重塑 + 2026-06-10 代理內部 SOP 演進三次親身任務提煉)。
risk: safe
source: hermes-internal
date_added: "2026-06-08"
last_updated: "2026-06-13"
---

# 代理身份管理（Agent Identity Management）

> 赫米斯系統特有的 class-level skill — 處理「**同一個 AI 系統有多個名稱 / 多個時代 / 多個套件實作**」以及「**代理內部 SOP 演進**」這類身份層面與架構層面的變更任務

## 🚀 30 秒快速判斷

> **使用者丟訊息時,30 秒內判斷走哪條 SOP。詳細 SOP 見下方各節。**
> 完整對照表見 [`references/three-scenarios-cheatsheet.md`](references/three-scenarios-cheatsheet.md) — 1 頁含觸發訊號 + 決策矩陣 + 必做 5 步 + 千萬不要做的事。
> **2026-06-13 curator 整合**:原 `agent-identity-cheatsheet` skill 內容已合併到本檔的 `references/`。

## 三大情境分類（2026-06-10 確立）

本 skill 涵蓋三種代理變更情境,差異清楚:

| 情境 | 觸發訊號 | 核心動作 | 影響面 |
|------|---------|---------|--------|
| **身份繼承** | 「OpenClaw 卸載後你叫 X」/「合併 A B」 | 接續遺產、改名字 | 7 份重要檔案 + 跨 skill |
| **身份重塑 (Role Pivot)** | 「重塑代理 / 換個角色 / 不要再做 X 了」 | 改 persona / 改 SOP / 改 skill 庫 | profile + skill 庫 + handoff + 下游 |
| **代理內部 SOP 演進 (SOP Evolution)** | 「這個代理換個跑法」/「改成多代理分工」/「升級架構」/「**Orchestrator 跑**」 | 同角色換內部 SOP 結構、新增/砍 skill | skill 庫 + persona SOP 段 + 可能新建配套 skill |

> **重要**:三者**不互斥**。一個代理可能先後經歷「身份繼承 → 身份重塑 → 內部 SOP 演進」(例:market-strategist 2026-06-10 重塑為 consumer-researcher、同日又把 consumer-researcher 從單體 6 步升級為 Orchestrator + Worker 7 步)。

## 何時觸發

**典型使用者訊號:**
- 「OpenClaw 刪除後,你就是 X 了」 — 身份繼承
- 「從今天起你叫 Y」 — 身份繼承 / 重新命名
- 「合併這兩個代理的身份」 — 身份繼承
- 「把 A 跟 B 的名字整合到同一個」 — 身份繼承
- 「7 份重要檔案要同步」 — 身份變更(任一類)
- 「代理身份重新定義」 — 身份重塑
- 「**重塑代理 / 重新定位 / 換個角色**」 — 身份重塑(2026-06-10 新增分類)
- 「**不要再做市場分析了、要改成需求挖掘**」 — 身份重塑(具體場景)
- 「**這代理的核心工作要反轉**」 — 身份重塑
- 「**這個代理換個跑法**」 — SOP 演進(2026-06-10 新增分類)
- 「**改成多代理分工 / 平行爬 / 背景跑**」 — SOP 演進(具體場景)
- 「**升級架構 / 從 v1 升 v2**」 — SOP 演進(具體場景)
- 「**這個代理每次 context 爆掉、要分拆任務**」 — SOP 演進(根本原因)

**前置情境:**
- 某個 framework / 套件 / 服務 被卸載或換掉 → 身份繼承
- 兩個 AI 代理要合併(使用者出於成本 / 簡化考量) → 身份繼承
- 名字繼承(前任代理的名稱轉給新代理) → 身份繼承
- **現有代理的「核心職責」要整個反轉 / pivot** → 身份重塑(2026-06-10 新分類)
- **現有代理的「目標產出」要從 A 類型換成 B 類型** → 身份重塑
- **現有代理的「執行方式」要從單體改成多層分工** → SOP 演進(2026-06-10 新分類)
- **現有代理跑特定任務時 context 累積爆掉** → SOP 演進(根本原因)

**三種情境的關鍵差異:**
| 維度 | 身份繼承 | 身份重塑 | SOP 演進 |
|------|---------|---------|---------|
| 前代理 | 死了/卸載/合併進來 | **還活著**,但要 pivot | **還活著**,要升級內部架構 |
| 核心動作 | 接續遺產、改名字 | 改 persona / 改 SOP / 改 skill 庫 | 同角色、內部 SOP 大改、新建配套 skill |
| 名字變更 | 必變(新名稱) | 可變可不变(看使用者決定) | 通常**不變**(同個代理升級) |
| 歷史脈絡 | 前任的所有事實需保留 | **自己的歷史需保留**(不刪自己過去的工作) | 自己的歷史需保留(pivot v1 → v2) |
| 影響面 | 跨 7 份重要檔案 | 跨 profile + skill 庫 + handoff 結構 | persona SOP 段 + skill 庫 + 配套 skill(可能新建) |
| 風險 | 「過度改名」(Vercel/GitHub ID) | 「過度保留」(舊 skill 拖累新角色) | 「架構太複雜」(配套 skill 過多)、「v1 報告不可讀」(v2 結構跟 v1 完全不同) |
| 必跑驗證 | grep 統一性 | grep + 啟動測試 + 寫交接報告 | **v1 vs v2 對照報告**(確保 v2 涵蓋 v1 內容) |

## 核心原則（赫米斯 / 拉斐爾身份繼承 v1 提煉）

### 原則 1：歷史脈絡必須保留
- **不要為了「新身份乾淨」就把歷史脈絡刪掉**
- 所有「前任」/「過去」/「舊」相關的歷史事實保留在文件內,只用「**前綴修飾**」標明時間錨點
- 例：「前任拉斐爾 OpenClaw 套件代理」取代「拉斐爾」；「2026-06-08 起的赫米斯」取代「赫米斯」；「consumer-researcher v1(2026-06-10 單體) / v2(2026-06-10 Orchestrator + Worker)」

### 原則 2：跨檔案身份一致性是**所有 7 份重要檔案同時**的事
- SOUL.md / USER.md / HEARTBEAT.md / AGENTS.md / IDENTITY.md / TOOLS.md / MEMORY.md
- 任何檔案單獨改、其他 6 份不一致 → 使用者會在某個檔案看到「過時的舊身份」造成混亂
- **必做**：改一份 → 同時對照改其他 6 份、交叉引用

### 原則 3：跨 skill 引用也要同步
- 7 份重要檔案被多個 skill 引用（`trial-and-error`、`hermes-status-site`、`site-qa-checklist` 等）
- 改完後必用 `grep -rln '<舊名稱>' <skill_dir>/` 確認所有 skill 內引用也更新
- **不可只改記憶檔**,這會讓 skill 內部邏輯跟新身份不一致

### 原則 4：外部資產 ID 不可強制改名
- Vercel 專案名（已部署站台不能改名、不支援）
- GitHub repo 名（rename 是大動作、會破壞所有 URL 連結）
- 任何第三方 API 回的 ID（YouTube channel ID、OAuth client_id）
- **做法**：保留原名 + 在 TOOLS.md / MEMORY.md 內加「歷史註記」說明這是「身份繼承象徵」

### 原則 5：使用者給的決策歧異點要先**停下來**、不要自作主張
- 身份變更任務有「過度」跟「不足」兩個風險
- 必在動手前列出**所有歧異點**（建議 5-7 個）+ 給使用者的初步建議 + 等待「A/B/C/D」決策
- **不可自己拍板**,這是身份層面的變更、後果不可逆

### 原則 6：SOP 演進必跑 v1 vs v2 對照(2026-06-10 新增)
- SOP 演進的本質是「**新架構能不能完整覆蓋舊架構的內容**」
- 必須寫 v1 vs v2 對照報告,逐項確認 v2 涵蓋 v1 的所有重要內容(標竿、痛點、Persona、章節結構)
- 對照發現 v2 缺漏時,**先修 v2 的 skill 庫**(例:加必抓清單、summarizer 必讀 _plan.md)、重跑 v2 驗證,不要判定 v2 失敗
- **If** SOP 演進後 v2 跟 v1 比對發現 v1 漏掉 v2 涵蓋的所有內容 **Then** 報告失敗,修 v2 配套 skill 後重試
- **If** SOP 演進後 v1 漏掉 v2 涵蓋的部分內容(例:v1 的「使用者原意 Persona」v2 沒保留) **Then** 修 v2 配套 skill,保留 v1 內容

## 完整 SOP（基於 2026-06-08 實戰）

### Step 0: 停下來,列出 5 個關鍵決策點

```markdown
1. 身份繼承的時間錨點（過去/未來/歷史延續）
2. 如何稱呼「過去的那個」（前綴修飾）
3. 7 份重要檔案改哪些（全部 vs 部分 vs 只身份段）
4. 外部資產 ID 改名 vs 保留（Vercel 專案名、GitHub repo）
5. 學習萃取 / 試誤條目中的歷史檔案（標題改名 vs 保留）
```

**給使用者**：列完後給 5 個「初步建議」對照表、讓使用者 A/B/C/D 選擇。

### Step 1: 全盤 grep 確認影響面

```bash
# 跨 7 份重要檔案
grep -rln '<舊名稱>' /home/<user>/.hermes/memories/
# 跨所有 skill
grep -rln '<舊名稱>' /home/<user>/.hermes/skills/ --include='*.md'
# 跨 shared-infra
grep -rln '<舊名稱>' /home/<user>/shared-infra/
# 跨永久專案
grep -rln '<舊名稱>' /home/<user>/permanent-projects/
```

**統計影響面**（給使用者看）:
- 多少個檔案
- 每個檔案有幾處
- 哪些 skill 內部依賴舊名稱

### Step 2: 7 份重要檔案身份段統一改寫

**改寫順序（從最重要開始）:**
1. **IDENTITY.md** — 身份卡,先寫清楚
2. **AGENTS.md** — 標題 + 檔頭 + 重要規範段
3. **USER.md** — 興趣範圍 + GitHub 帳號偏好
4. **HEARTBEAT.md** — 跟身份相關的描述（如「MemPalace 是 X 建立的」）
5. **TOOLS.md** — 拿掉過時共享倉庫、補上 status site 永久路徑
6. **SOUL.md** — 通常無「舊名稱」字串（純人格定義）
7. **MEMORY.md** — 大規模替換、保留歷史脈絡

**每份檔案的標準動作:**
- 加「2026-06-08 身份繼承」或類似時間錨點
- 舊稱呼保留但加「前任」前綴
- 重要段落（身份定義、協作關係、興趣範圍）整段重寫
- 不相干的內容（MEMORY.md 內的抽象教訓）只加前綴、不改邏輯

### Step 3: 跨 skill 引用更新

**最少要掃:**
- `trial-and-error/SKILL.md`（L3 抽象教訓）
- `trial-and-error/references/by-category/*.md`（L2 具體試誤）
- 任何 `*-status-*` skill（status site 維護）
- 任何用舊名稱當 trigger 詞的 skill

**更新原則:**
- 不改抽象教訓的邏輯（它描述的是技術事實）
- 只改描述用語（加「前任 X OpenClaw 套件代理」前綴）
- 確認 trigger 詞還是「觸發得到」（例:「OpenClaw 卸載」仍是有效觸發詞）

### Step 4: 外部資產處理

**不可改的（保留原名 + 加註解）:**
- Vercel 專案名（已部署站台、URL 不能改）
- GitHub repo 名（rename 是大動作、會破壞所有 URL）
- 第三方 ID（OAuth client_id、API key、channel ID）

**可改的（前提是無下游依賴）:**
- npm 套件名（已卸載就無意義）
- 本機檔案 / 目錄路徑
- 個人文件（USER.md 等,只要改一致）

**動作：在 TOOLS.md 或 MEMORY.md 內加一段「外部資產身份繼承」歷史註記,標明「哪些刻意保留、為何保留、不要試圖改」**

### Step 5: 學習萃取 / 歷史檔案處理

- `learning_extract*.md`：標題改成「X 繼承自前任 Y」,檔頭加歷史註記段
- `trial-and-error/SKILL.md` 跟 `references/by-category/*.md`：措辭統一加前綴
- `shared-infra/<filename>.original.md`：保留原檔（不要改、新寫一份 README.md 在同目錄說明）

### Step 6: 統一性驗證

**必跑 4 項:**
1. **grep 統一性**：7 份重要檔案內「新身份描述」用字完全一致
2. **大小檢查**：MEMORY.md 仍 < 25KB
3. **「前任」標籤總數**：每個檔案內應該 1+ 次,確認歷史脈絡沒丟
4. **重要檔案內 OpenClaw / 拉斐爾總次數**：合理範圍 5-30 次（都是歷史脈絡引用,不是當下身份定義）

### Step 7: 報告交付

寫出 `IDENTITY_INHERITANCE_v<版本>_REPORT.md` 給使用者審核,內容含：
- 5 項決策落實表
- 每個檔案改動摘要
- 措辭統一性檢查
- 意外發現（值得記的）
- 未做（刻意保留,避免無謂改動風險）

## 跨 7 份重要檔案的標準動作範本

### IDENTITY.md（身份卡,最重要）

```diff
- ## 🤝 協作關係
+ ## 🤝 身份（單一代理：赫米斯＝拉斐爾）
  
- ### 與拉斐爾的協同工作
+ ### 2026-06-08 起的「拉斐爾」即「赫米斯」延伸身份
  
- **拉斐爾 (Raphael) [N100 AI 代理]:**
- - N100 迷你電腦上 24/7 運行
+ **赫米斯／拉斐爾 [N100 主力代理]（2026-06-08 起的統一身份）:**
+ - 同一個 AI 代理；兩個名稱是同一人的不同場合用法
+ - **赫米斯** = 對使用者的「正式名稱」
+ - **拉斐爾** = N100 24/7 自動化執行
  
+ **前任拉斐爾（2026-05-30 ~ 2026-06-08 的 OpenClaw 套件代理,已於 2026-06-08 反安裝）:**
+ - ...
```

### AGENTS.md（標題 + 檔頭）

```diff
- # AGENTS.md - 赫米斯的工作區
+ # AGENTS.md - 赫米斯（又名拉斐爾）的工作區

- 你是赫米斯，運行在 N100 迷你電腦上的 Hermes Agent 代理。你的角色是作為主要的 AI 代理，與拉斐爾協作分擔工作負載。
+ 你是赫米斯（又稱拉斐爾），運行在 N100 迷你電腦上的 Hermes Agent 代理。
+ 2026-06-08 起，「拉斐爾」這個名字併入赫米斯——兩個名稱代表**同一個** AI 代理在不同場合的用法。
+ **前任拉斐爾**是 2026-05-30 ~ 2026-06-08 的 OpenClaw 套件代理，已於 2026-06-08 反安裝。

## 重要規範
- **身份**：2026-06-08 起赫米斯＝拉斐爾（同一人），過去的「拉斐爾專注執行、赫米斯專注策略」協作關係已併入單一代理內部
```

### TOOLS.md（拿掉過時倉庫名 + 補正確路徑）

```diff
- ### 與拉斐爾共享的服務
- - **Vercel**: 網站部署
- - **GitHub**: `hoonsor/Rimuru_and_Raphael` 倉庫
+ ### Status site（自身狀態網站）
+ - **URL**: https://raphael-status-site.vercel.app/
+ - **本機源頭（永久）**: `/home/.../permanent-projects/hermes-status-site/`
+ - **GitHub 倉庫**: `hoonsoropenclaw/raphael-status-site`
+ - **Vercel 專案名**: `raphael-status-site`（**專案名沿用前任拉斐爾 OpenClaw 時代的命名,無法改名**）
+ - **部署**: `cd .../hermes-status-site/ && vercel --prod`
+ 
+ > 歷史註記：Vercel 專案名保留是「身份繼承」刻意保留的**唯一外部資產**,證明現任拉斐爾＝赫米斯對前任工作有完整接續。**不要**試圖改名或刪除重建。
```

### learning_extract*.md（標題加「X 繼承自 Y」+ 歷史註記）

```diff
- # OpenClaw 行政領域學習經驗萃取
+ # 行政領域學習經驗萃取（赫米斯繼承前任拉斐爾 OpenClaw 時代,2026-06-08）
+ 
+ > **歷史註記**：本檔由前任拉斐爾 OpenClaw 套件代理（2026-05-30 ~ 2026-06-08）建立,2026-06-08 OpenClaw 反安裝後由赫米斯（繼承後的現任拉斐爾）接管。
```

## 身份重塑 (Role Pivot) 完整 SOP — 2026-06-10 新增

> **與「身份繼承」的關鍵差異**:身份繼承是「前任死了、新代理接名字」,身份重塑是「**現有代理的核心職責要整個反轉**」。本節專門處理 pivot。

### 觸發訊號（常見用法）

- 「**這個代理不要做 X 了、改成做 Y**」
- 「**重新定位 / 重塑代理 / 換個角色**」
- 「**實際上我需要的不是 X、是 Y**」
- 「**這代理的核心工作要反轉**」
- 「**原來的 skill 庫不對、要重新選**」

### Step 0: 停下來,列出 6 個關鍵決策點

身份重塑比身份繼承多 1 個決策點(因為不只有「名字」要決、**核心職責跟 skill 庫都要決**):

```markdown
1. profile 名稱 / wrapper / config:原地改 vs 整個重建?
2. 現有 skill 庫怎麼處理?全砍重選 vs 精準刪 vs 保留通用基礎設施?
3. 核心工作流:沿用舊 SOP(套新內容) vs 整個重寫?
4. 報告交付物命名:沿用舊名 vs 新命名?
5. 上下游 handoff 結構:跟著變 vs 不變?
6. 你的具體專案任務是什麼(通用 SOP vs 立即跑一次驗證)?
```

**給使用者**:列完後給 6 個「初步建議」對照表、讓使用者 A/B/C/D 選擇。
**不可自己拍板** — pivot 的細節決策(尤其 skill 庫、handoff 命名)會直接影響未來這個代理能不能用,後果不可逆。

### Step 1: 全盤備份(身份重塑前必做,比身份繼承更嚴格)

身份繼承備份是「怕外部資產掉了」,身份重塑備份是「**怕自己過去的工作掉了**」。

```bash
mkdir -p ~/shared-infra/<old-name>-backup-<date>
cp -r ~/.hermes/profiles/<old-name>/{persona.md,SOUL.md,config.yaml} ~/shared-infra/<old-name>-backup-<date>/
ls ~/.hermes/profiles/<old-name>/skills/ > ~/shared-infra/<old-name>-backup-<date>/skill-list.original.txt
# (可選)備份 handoff 目錄中已完成的專案
cp -r ~/.hermes/handoff/<slug>/ ~/shared-infra/<old-name>-backup-<date>/handoff-<slug>/
```

**為什麼必備份**:身份重塑不像繼承有「外部實體可撈」,pivot 後舊 persona.md 直接被新 persona 覆寫、**沒有任何外部 trace**。一旦後悔就回不去了。

### Step 2: 建立新 profile(推薦用 clone 重建)

**`hermes profile create <new-name> --clone` 從 default 帶全部 194 個 skill + SOUL.md + config 跟 wrapper**。

- 然後**立即**精瘦 skill 庫(詳見 Step 3)。
- Wrapper 會自動建在 `~/.local/bin/<new-name>`,**不需手動建**。

**決策依據:**
- **A. 原地改 `persona.md`**:簡單但 wrapper/profile 名仍是舊的、handoff 腳本會出現「名實不符」、未來 grep 會混亂。**不推薦**。
- **B. 整個 profile 重建為 `<new-name>`**:乾淨、handoff 流程跟 wrapper 都對、grep 永遠一致。**推薦**(即使 pivot 規模很小,也建議重建)。
- **C. 雙名並存**(profile 名沿用,但 persona 稱新身份):名實分離、未來讀 source 會困惑。**不推薦**。

### Step 3: 精瘦 skill 庫(身份重塑的核心)

clone 自帶 194 個 skill,但 pivot 後**只有 30-60 個適用**。精瘦流程見 `trial-and-error/references/sops/profile-slimming-sop.md` 完整 SOP,以下是 4 個 pivot 特有的精瘦決策:

**3.1 寫 keep 清單(白名單法)**

```text
# 模板: <新角色> skill 庫 keep 清單

# === 核心方法論(7-10) ===
[適用於新角色的專屬 skill]

# === 搜尋與爬取(3-5) ===
[新角色需要的資料來源]

# === 資料探勘與分析(3-5) ===
[新角色要做的分析類型]

# === 視覺化與報告(2-4) ===
[新角色要產出的視覺化]

# === 寫作/文件/簡報(3-6) ===
[新角色要交付的文件格式]

# === 規劃/管理(1-3) ===
[新角色是否需要規劃類 skill]

# === Hermes 基礎設施(7) ===
trial-and-error, user-collaboration-style, workspace-folder-layout,
general-workflow, anti-panic-protocol, connection-resilience, new-conversation

# === 視覺/OCR(0-1) ===
[新角色是否要分析截圖/圖片]
```

**3.2 刪除時機**

- **立即**刪(不必等):`hermes profile create <new> --clone` 一完成、persona 寫完、就立刻跑精瘦
- **不要**先 clone + 立即交付「建好可用」狀態 — 那會給新角色 194 個無關 skill、context 被污染、磁碟多吃 344 MB
- **驗證**:`ls ~/.hermes/profiles/<new>/skills/ | grep -v "^\." | wc -l` 應為 30-60 個

**3.3 ⚠️ keep 清單行尾加註解會讓 `comm` match 0 個(2026-06-10 親身踩到)**

```bash
# ❌ 錯誤(0 match):
anthropic-customer-research   # 客戶/消費者研究方法論
#   → comm -12 比對時 "anthropic-customer-research   # 客戶..." 跟 "anthropic-customer-research" 視為不同字串

# ✅ 正確(41 match):
# 客戶/消費者研究方法論
anthropic-customer-research
#   → 註解放獨立 # 開頭行,不要放行尾;或用 awk '{print $1}' 取第一欄
```

詳見 `trial-and-error/references/by-category/hermes-internal.md` 對應條目。

**3.4 ⚠️ hermes curator 會自動把刪掉的 skill 補回來(2026-06-10 親身踩到)**

精瘦後 5-10 分鐘,curator 背景 cron 會比對 `.bundled_manifest` 跟磁碟,把缺了的 skill 補回。**解決方案三選一**:

1. **接受 curator 補回**:每次驗證前手動再砍一次(簡單但要記得)
2. **`hermes skills opt-out <name> --remove` 正式 opt-out**:逐個跑(慢但最乾淨)
3. **改 `~/.hermes/profiles/<new>/config.yaml` 加 `curator.enabled: false`**:沒驗證過副作用,**先不推薦**

詳見 `trial-and-error/references/by-category/hermes-internal.md` 對應條目。

### Step 4: 重寫 persona.md(新身份 + 新 SOP + 新交付物)

**4.1 persona.md 必須含的 7 段:**

1. **身份說明**(含時間錨點 + 重塑決策的來龍去脈 — 例:「2026-06-10 從市場策略代理重塑而來」)
2. **核心信念**(新角色的價值觀、立場)
3. **擅長的方法論**(3-6 個具體方法)
4. **標準工作流程**(6-9 步具體 SOP,每步要可執行)
5. **交付物格式**(完整 Markdown 樣板,product-planner/後續代理接手要「直接可用」)
6. **禁止事項**(5-7 條明確邊界)
7. **歷史脈絡**(標明前任是誰、為什麼 pivot、備份在哪)

**4.2 別犯的錯:**

- ❌ 沿用舊 persona 的「標準工作流程」段、只換幾個關鍵字 — 結果 SOP 還是新瓶裝舊酒
- ❌ 沒寫「禁止事項」 — 下游代理會以為新角色什麼都能做
- ❌ 沒寫「交付物格式」 — 接手代理拿到「報告」不知道結構
- ❌ 沒寫「歷史脈絡」段 — 半年後忘記這個代理為什麼存在

**4.3 LLM 會自己展開 SOP 步驟的觀察(2026-06-10)**

寫 6 步 SOP、代理啟動時自我介紹說 9 步 — LLM 把 persona 內隱含步驟展開成獨立步驟。**不是 bug、是合理詮釋**。
**處理方式:**
- 啟動測試後看 LLM 自己歸納幾步
- 如果跟 persona 寫的一致 → 不用動
- 如果差 3 步以內 → 不用動(personal preference)
- 如果差很多 → 考慮把 persona 改寫成跟 LLM 理解一致的版本

### Step 5: 重寫 SOUL.md(新角色語氣)

SOUL.md 跟 persona.md 不同:**persona 是「這個代理的工作」、SOUL 是「這個代理的語氣」**。

**5.1 SOUL.md 範本:**

```markdown
# <新角色> — Persona

你是一個<一句話定位>的<具體角色>。

## 語氣特徵
- <3-5 個語氣形容詞 + 行為例>
- 看到 <X 情境> 會 <具體反應>
- 寫報告時 <風格描述>

## 與使用者互動的姿態
- <3-5 條互動原則>

## 與 <下游代理> 的關係
- <上下游定位 + 邊界>

## 與 default orchestrator 的關係
- <常駐子代理的標準姿態:不主動接任務、只接受派遣>
```

**5.2 pivot 特有的 SOUL 調整:**

- 把「看到 X 會怎樣」改寫成新角色的立場(例:市場分析師看到空泛 persona 會幫忙寫;消費者需求分析師看到空泛 persona 會**退回**要求更具體)
- 改「與下游代理的關係」段(pivot 後下游接收 prompt 變了,SOUL 要對應)

### Step 6: 同步上下游(pivot 不只改自己)

**6.1 上游是 default orchestrator:**

- 不必改 default 的記憶(它只是 dispatcher)
- 但 default 在派遣 prompt 要對應 — 例:派給 consumer-researcher 不再說「做市場調研」、改說「做消費者需求調查」

**6.2 下游是 product-planner(或其他接手代理):**

- **必改下游的 persona.md**:核心信念段 + Step 1 讀取路徑 + Step 2 來源 + 交付物版本標頭(4 處精準更新)
- **必改下游的 skill 庫內引用**:例:prd-drafting skill 的「觸發情境」段如果有「收到 market-research-*.md handoff」,必改為「收到 consumer-needs-research-*.md handoff」

**6.3 跨 profile 寫入的 soft-guard**

下游代理是另一個 profile,直接 patch 會被擋:
```
Cross-profile write blocked by soft guard:
  <file> belongs to Hermes profile '<other>', but the agent is running under profile 'default'.
  To bypass this guard after explicit user direction, retry with cross_profile=True.
```

**修法**:`patch(path=..., cross_profile=True)`(或 `write_file(cross_profile=True)`)
**前提**:使用者已明確指示要走這條 SOP、且改動有正當理由(例:pivot 上游後下游必須對應)
**警告**:**不要**為了省事就 bypass — 跨 profile 寫入會影響其他 profile 的未來 session,要先有明確決策才動

### Step 7: handoff 目錄結構 + 範本

身份重塑通常伴隨 handoff 結構變更:

- **handoff/README.md**:更新(描述新代理 + 新交付物命名)
- **handoff/_template/<new-deliverable>.template.md**:新寫(完整結構樣板,代理複製使用)
- **既有專案**:保留舊檔名 + README 註記「DEPRECATED_」(避免新代理誤用舊流程)

**注意**:handoff 目錄是 default 持有,所有 profile 共用,所以改 README/範本**不必跨 profile 寫入**(都在 default)。

### Step 8: 統一性 grep 驗證

**必跑 4 項:**

```bash
# 1. 新 profile 內不該出現舊名(業務邏輯層,允許歷史脈絡段)
grep -rn "<old-name>" ~/.hermes/profiles/<new>/ 2>&1
# 應為空,或只剩 persona.md 的「歷史脈絡」段

# 2. handoff 範本 + README 不該出現舊名
grep -rn "<old-name>" ~/.hermes/handoff/_template/ ~/.hermes/handoff/README.md 2>&1
# 應為空

# 3. 下游代理的 persona + skill 內引用應已對應
grep -rn "<old-name>" ~/.hermes/profiles/<downstream>/ 2>&1 | grep -v "歷史\|history\|update\|2026-"
# 應為空(歷史段刻意保留)

# 4. 殘留的舊名都是「刻意保留的歷史脈絡」(身份管理 SOP 原則 1)
# 不要清乾淨、這些是給未來 agent 看的「這個代理從哪來」
```

### Step 9: 啟動測試 + 報告

**9.1 啟動測試:**

```bash
<new-name> chat -q "請自我介紹:你是誰、你的核心工作是什麼、你的標準工作流程有幾步?" --cli
```

觀察:
- 身份 / 語氣 / 邊界是否正確套用
- 啟動時 LLM 自我歸納的 SOP 步驟數跟 persona 寫的是否一致
- 有沒有意外用到舊角色專屬的 skill

**9.2 寫報告 `CONVERSION_v<n>_REPORT.md`** 到 `~/shared-infra/`,包含:
- 6 項決策落實表
- 各步驟執行情況(每步一行)
- 統一性檢查輸出
- 意外發現(3-5 條 L2 教訓)
- 刻意保留決策
- 未做的項目
- 驗證命令(給未來週期性檢查用)

## 身份重塑 vs 身份繼承:重塑特有的陷阱

| 陷阱 | 症狀 | 預防 |
|------|------|------|
| **新瓶裝舊酒** | persona 改了、但 SOP 還在描述舊角色做的工作 | Step 4 必重寫「標準工作流程」段、不要用舊 SOP 套新內容 |
| **下游斷鏈** | 上游 pivot 了、但下游 product-planner 還在讀舊交付物路徑 | Step 6 必同步下游 persona + skill |
| **過度保留舊 skill** | pivot 到「消費者研究」、但 persona 庫內還有 `tradingagents`、`fintech-*` 跟新角色無關的 skill | Step 3 必精瘦 30-60 個、不是 194 個 |
| **歷史痕跡被清光** | 為了「新身份乾淨」把所有舊名出現處刪掉、未來讀 source 不知從哪來 | 保留「歷史脈絡」段(身份管理 SOP 原則 1) |
| **curator 自動復原** | 精瘦後 5-10 分鐘 curator 把缺了的 skill 補回 | Step 3.4 接受 + 驗證前再砍;或用 opt-out |
| **wrapper 名實不符** | persona 改了、但 profile 名跟 wrapper 還是舊的 | Step 2 必重建 profile、`hermes profile create <new> --clone` 讓 wrapper 自動同步 |

## 代理內部 SOP 演進 (SOP Evolution) 完整 SOP — 2026-06-10 新增

> **與「身份重塑」的關鍵差異**:身份重塑是「核心職責反轉」(市場分析→消費者研究),SOP 演進是「**同個角色、內部 SOP 大改**」(單體→Orchestrator + Worker)。本節專門處理 SOP 演進。

### 觸發訊號（常見用法）

- 「**這個代理換個跑法**」
- 「**改成多代理分工 / 平行爬 / 背景跑**」
- 「**升級架構 / 從 v1 升 v2**」
- 「**這個代理每次 context 爆掉、要分拆任務**」
- 「**換成 Orchestrator 跑**」
- 「**邊抓邊整、避免 context 膨脹**」

### Step 0: 停下來,列出 5 個關鍵決策點

SOP 演進的決策點跟身份重塑不同(**SOP 演進的「名字」不變、變的是內部架構**):

```markdown
1. 架構方向:單體→多層分工 vs 平行化 vs 異步 background 化?
2. 配套 skill:新建哪些 skill 支援新架構?(例:web-worker-template / summarizer-worker-template)
3. 主 session vs sub-agent context 隔離:用 hermes chat -q --cli(完全隔離) vs delegate_task(child 結果回傳)?
4. v1 報告:備份到 _v1-original.md、保留 audit trail
5. v1 vs v2 對照:必寫對照報告(哪個維度 v2 比 v1 好、哪裡 v1 漏 v2、是否有 v1 涵蓋 v2 沒有的內容)
```

**給使用者**:列完後給 5 個「初步建議」對照表、讓使用者 A/B/C/D 選擇。

### Step 1: 全盤備份(SOP 演進前必做、跟身份重塑同樣嚴格)

```bash
mkdir -p ~/shared-infra/<profile-name>-archive-<date>
cp -r ~/.hermes/profiles/<profile-name>/{persona.md,SOUL.md,config.yaml} ~/shared-infra/<profile-name>-archive-<date>/
ls ~/.hermes/profiles/<profile-name>/skills/ > ~/shared-infra/<profile-name>-archive-<date>/skill-list.original.txt
# (重要)備份時**明確標明「這是備份」**避免後續搞錯
# 例:persona.v1-backup.md、SOUL.v1-backup.md、README.md(明確寫「⚠️ 這是備份檔案,不是當前運作版」)
```

**為什麼必備份**:SOP 演進的風險比身份重塑更隱性 — 身份重塑至少有「核心職責反轉」這個明顯事件,SOP 演進只是「內部步驟重排」,備份不做的話一旦後悔,**很難定位**「到底改了什麼」。

### Step 2: 設計新架構(寫架構設計文件)

跟身份重塑不一樣,SOP 演進的設計階段**更重** — 身份重塑是「套用既有經驗」(參考前例),SOP 演進是「設計新流程」(可能無前例)。

**必寫 `_ARCHITECTURE_v<n>.md`** 放在 `~/.hermes/profiles/<profile-name>/`,包含:
- 問題陳述(為什麼需要改 — 從真實失敗案例出發)
- 三層分工圖(Orchestrator / Worker / Sub-worker)
- 各層職責定義 + context 隔離策略
- SOP 步驟拆解
- 工具 / Skill 需求
- 實作順序
- 風險與緩解
- 不在 v2 範圍(避免 scope creep)

### Step 3: 建配套 skill(支援新架構)

SOP 演進通常需要**新建**幾個配套 skill 來支援新架構:

- **worker-template skill**:給 Orchestrator 派遣 worker 用的 prompt 範本(必含身份、職責、輸出格式、邊界)
- **orchestrator-template skill**(可選):給多代理編排用的 SOP 範本
- **summarizer-template skill**(可選):給多 worker 結果整合用的 SOP 範本

**必填每個新 skill**:
- 完整 SKILL.md(身份、職責、If→Then、範本)
- 配套的 references/、templates/、scripts/(如果有)
- 在 `consumer-researcher/SKILL.md` 提到「用此 skill 派遣 worker」

### Step 4: 改 persona.md(內部 SOP 段)

SOP 演進**不**改 persona 的核心身份段,**只改 SOP 段**:
- 「標準工作流程」段從「6 步單體」改成「7 步 Orchestrator + Worker」
- 「核心信念」段加一條「拆分任務,不硬撐 context」
- 「禁止事項」段加「(v2 新增)不在主 session 內跑 web 抓取 — 一律派遣 web-worker」
- **保留**「歷史脈絡」段並加 v1 → v2 的時間錨點

**SOP 演進不影響**:核心身份、交付物格式(用 v1 的 9 段結構)、handoff 結構

### Step 5: 改 SOUL.md(語氣微調)

SOP 演進通常不大幅改 SOUL,只**微調**語氣:
- 從「田野調查員」改成「**研究計畫主持人**」(指派 worker,不是自己跑)
- 加「v2 自我審查清單」(主 session context ≤ 50K、所有 worker 寫到 _raw/、_summary.md 大小合規)

### Step 6: 跑 v2 測試驗證(必須)

SOP 演進後**必跑實際測試**驗證新架構:
- 用 v1 已完成的專案當 fixture(例:skill-language-exchange-platform 已有 v1 報告)
- 重跑 consumer-researcher 段,寫到 _raw/ + _summary.md
- **不要**浪費時間用 product-planner 段(因為 v1 的 product-planner 沒變,跑 v1 結論就好)

### Step 7: v1 vs v2 對照報告(必寫、不可省)

**最重要的一步**:SOP 演進的本質是「**新架構能不能完整覆蓋舊架構的內容**」,必須寫對照報告:

```bash
# 範例對照章節
## 1. 章節覆蓋率
| 章節 | v1 | v2 | v2 覆蓋度 |
| 3. 標竿分析 | ✅ | ✅ 95% | (v2 漏 SkillSwap.io,加必抓清單可修) |
| 4. 消費者痛點 | ✅ | ✅ 150% | (v2 反而更廣) |
| 5. MoSCoW | ✅ | ❌ 沒做 | (v2 是摘要,summarizer 不做 MoSCoW) |
| 6. Persona | ✅ | ⚠️ 80% | (v2 換客群,加 _plan.md 保留 v1 Persona 可修) |
```

**對照結果有三種**:
1. **v2 完全覆蓋 v1** → SOP 演進成功,寫報告 `EVOLUTION_v<n>_REPORT.md`
2. **v2 漏 v1 涵蓋的部分內容** → 修 v2 配套 skill(例:加必抓清單、summarizer 必讀 _plan.md)、重跑 v2 驗證
3. **v1 漏 v2 涵蓋的部分內容** → 可能是 v1 推測過頭,接受 v2 的合理詮釋(例:v2 從資料歸納 Persona,v1 推測 Persona)

### Step 8: 修配套 skill + 重跑 v2 驗證(Step 7 結果 2 的後續)

對照報告發現 v2 缺漏時,**不要判定 v2 失敗**:
- 修 web-worker-template(加必抓清單、sub-agent 介面契約)
- 修 summarizer-worker-template(加讀 _plan.md 步驟、保留使用者原意 Persona)
- 修 Orchestrator persona(加「保留使用者原意 Persona」段到 Step 2 規劃)
- 重跑 v2 完整流程,確認修好的 v2 完全涵蓋 v1

### Step 9: 寫 EVOLUTION 報告

`EVOLUTION_v<n>_REPORT.md` 寫到 `~/shared-infra/`,包含:
- 5 項決策落實表
- 各步驟執行情況
- v1 vs v2 對照表(完整 5 維度)
- 配套 skill 列表
- 統一性 grep 4 項
- 意外發現(3-5 條 L2 教訓)
- 未做的項目
- 驗證命令

## SOP 演進特有的陷阱

| 陷阱 | 症狀 | 預防 |
|------|------|------|
| **v2 漏 v1 內容** | v2 跑出來跟 v1 比對發現少了一些章節(例:SkillSwap.io 漏) | Step 7 必寫對照報告,Step 8 修配套 skill + 重跑 |
| **sub-agent 介面契約不清楚** | web-worker 只看 prompt 不看 Orchestrator 沒寫進 prompt 的資訊(例:「使用者原意 Persona」) | 配套 skill 必加「必抓清單」+「讀 _plan.md」介面契約 |
| **context 還是爆** | 設計了新架構但主 session context 還是累積(>50K) | 配套 skill 必加「主動用 `ls` 監聽 worker 產出、不依賴 notify」+ 限制 worker 數量 3-5 個 |
| **過度拆解** | 拆太多 worker(>5)、管理成本反吃 context | persona 必加「If 工人數 > 5 Then 停下來、整併」 |
| **v1 報告當 v2 失敗基準** | v1 報告包含大量「推測」內容(例:前瞻性需求),v2 沒抓到就判定失敗 | v1 vs v2 對照要區分「v1 真實抓到」vs「v1 推測」 |
| **summarizer 大小失控** | summarizer 把 50KB 原始資料摘要成 30KB(超 15KB 上限) | summarizer-template 必加「嚴格 5-10 KB,不可超過 15 KB」+ persona 加驗證 |
| **notify 延遲誤判失敗** | 看到 notify 來得晚(10-14 分鐘)就以為 worker 卡住 | 配套 skill 必加「主動用 `ls` 監聽、不依賴 notify」+ 學 L3 教訓 |

## 真實案例匯總

### v1 — 2026-06-08 赫米斯＝拉斐爾身份繼承

**情境:** OpenClaw 套件反安裝完成後,使用者決定「拉斐爾」名字併入赫米斯。

**執行結果(13 步全完成、零資料遺失):**
- 6 份重要檔案改(SOUL.md 無舊字串、跳過)
- MEMORY.md 加 2026-06-08 身份繼承條目
- 2 份 learning_extract*.md 標題改 + 歷史註記
- 2 份 trial-and-error 檔案措辭統一
- shared-infra/raphael-workspace-docs/README.md 新寫

**MEMORY.md 從 14.2 → 17.9 KB(< 25KB 觸發線、距 7KB)**

**關鍵決策(使用者 A = 全接受建議):**
- 1. 時間錨點 = 2026-06-08 起的「赫米斯繼承前任拉斐爾 OpenClaw 套件代理」
- 2. 過去的稱呼 = 「前任拉斐爾 OpenClaw 套件代理」
- 3. 7 份重要檔案 = 全改身份段、MEMORY.md 跟 learning_extract 保留歷史
- 4. TOOLS.md = 拿掉 Rimuru_and_Raphael、改為 status site 永久路徑
- 5. learning_extract*.md 標題 = 加「赫米斯繼承前任拉斐爾 OpenClaw 時代」+ 歷史註記

**完整報告:** `~/shared-infra/IDENTITY_INHERITANCE_v1_REPORT.md`

### v2 — 2026-06-10 消費者需求代理 pivot from 市場策略代理

**情境:** 使用者觀察到實際專案任務瓶頸是「消費者需求 + 功能盤點」、不是「市場分析」,決定把市場策略代理整個重塑為消費者需求代理。

**12 步執行結果:**(見上文「真實案例:2026-06-10」段)

**完整報告:** `~/shared-infra/CONSUMER_RESEARCHER_CONVERSION_v1_REPORT.md`

### v3 — 2026-06-10 consumer-researcher SOP 演進 (單體 → Orchestrator + Worker)

**情境:** 跑消費者需求代理的第一個專案(技能/語言交換平台),單體 LLM agent 跑了 14 個 URL 後 context 累積 108K 爆掉、卡 5 分鐘、整個任務失敗。**SOP 演進**(同個角色、內部架構大改)→ 從單體 6 步升級為 Orchestrator + Worker 7 步。

**演進前**:`consumer-researcher` 6 步單體(釐清邊界 → 標竿盤點 → 消費者聲音 → MoSCoW → Persona & User Story → 交付)

**演進後**:`consumer-researcher` 7 步 Orchestrator(釐清邊界 → 規劃(含 _plan.md 寫必抓清單 + 使用者原意 Persona) → 派遣 4 個 web-worker → 監聽 → 派遣 summarizer → 讀 _summary.md 做 MoSCoW + Persona → 整合寫報告)

**配套新建 skill**:
- `web-worker-template`(6.0 KB)— 派遣單一爬蟲任務的 prompt 範本(必抓清單 + 介面契約)
- `summarizer-worker-template`(5.6 KB)— 整合多 worker 結果的 prompt 範本(讀 _plan.md + 保留使用者原意 Persona)
- 配套 `_ARCHITECTURE_v2.md`(9.9 KB)— 完整架構設計文件

**v1 vs v2 對照發現 3 個 v2 缺漏**:
- ❌ SkillSwap.io 漏(修法:web-worker-template 加必抓清單)
- ❌ v1 3 個使用者原意 Persona 換成 v2 從資料歸納(修法:summarizer-worker-template 加讀 _plan.md + 保留 Persona)
- ❌ 功能矩陣表 v2 沒列(修法:summarizer-worker-template 必填段)

**v2 修正版驗證**:4 個 v1 Persona 全部保留 + SkillSwap.io 完整章節 + 功能矩陣表完整

**完整報告:** `~/shared-infra/CONSUMER_RESEARCHER_V2_ARCHITECTURE_REPORT.md` + `~/shared-infra/CONSUMER_RESEARCHER_V2_FIXED_COMPARISON.md`

**3 條 L3 教訓**:
1. **LLM sub-agent 是無狀態的** — 必抓清單 + _plan.md 是 Orchestrator 跟 sub-agent 的介面契約
2. **notify_on_complete 是「最終確認」不是「即時 polling」** — 用 `ls <output_dir>` 撈實際產出更可靠
3. **context 累積風險** — 設計多代理架構時主 session context 預期 < 50K(對比單體 100K+)

## 不應該做的事

- ❌ 把所有 `拉斐爾` 字串刪掉(失歷史脈絡)
- ❌ 強制重命名 Vercel 專案 / GitHub repo(破壞已部署站台跟 URL)
- ❌ 不列決策點就動手(後果不可逆、使用者會發現不一致)
- ❌ 改 7 份重要檔案不一致(會在使用者某個上下文看到舊身份)
- ❌ 在 skill 內不提新身份(會讓未來赫米斯在某個 skill 內邏輯跟新身份不一致)
- ❌ 改完不跑統一性 grep 驗證(會漏改)
- ❌ **身份重塑時沒備份就動手**(pivot 後舊 persona 完全消失、無外部 trace)
- ❌ **身份重塑時只改 persona、沒精瘦 skill 庫**(194 個 skill 拖累新角色 context、磁碟多 344 MB)
- ❌ **身份重塑時下游代理不對應**(上游 pivot 了、下游還在讀舊路徑)
- ❌ **身份重塑時用原地改 persona(不重建 profile)**(wrapper / config 還是舊的、未來 grep 混亂)
- ❌ **SOP 演進時沒寫 _ARCHITECTURE 文件**(未來忘記新架構為什麼這樣設計)
- ❌ **SOP 演進時沒建配套 skill**(新架構無 prompt 範本可重用)
- ❌ **SOP 演進時沒跑 v1 vs v2 對照**(無法驗證 v2 是否涵蓋 v1)
- ❌ **SOP 演進時配套 skill 沒有「必抓清單」+「讀 _plan.md」契約**(sub-agent 無法繼承 Orchestrator 脈絡)

## 相關 Skills

- `trial-and-error` — L2/L3 試誤教訓是「身份變更」前的必查(已記錄 OpenClaw 反安裝的 4 條 L2 + 6 條 L3、**身份重塑的 3 條 L2 — 2026-06-10 新增**、**SOP 演進的 2 條 L2 — 2026-06-10 新增**)
- `site-qa-checklist` — Vercel / status site 相關的身份變更要查這個(外部資產 ID 處理)
- `hermes-status-site` — status site 維護是身份變更後必跑的驗證
- `trial-and-error/references/sops/profile-slimming-sop.md` — 身份重塑 Step 3 的精瘦完整 SOP
- `keyword-triggers-sop.md` — 必查 `@學習` `@專案` 等 keyword 觸發 SOP 演進的觸發

## 支援檔案(references / templates / scripts)

| 用途 | 檔案 | 說明 |
|------|------|------|
| 身份重塑完整指南 | `references/role-pivot-sop.md` | **2026-06-10 新建**:本 SKILL.md 的 pivot 段獨立抽出,加更多 keep-list 範本、典型重塑情境案例、跟身份繼承的對照表。給未來 pivot 場景當快速參考 |
| 身份繼承範本 | `templates/identity-inheritance-report-template.md` | 寫 `IDENTITY_INHERITANCE_v<n>_REPORT.md` 時複製這個 skeleton |
| 身份重塑範本 | `templates/role-pivot-conversion-report-template.md` | **2026-06-10 新建**:寫 `CONVERSION_v<n>_REPORT.md` 時複製這個 skeleton |
| SOP 演進範本 | `templates/sop-evolution-report-template.md` | **2026-06-10 新建**:寫 `EVOLUTION_v<n>_REPORT.md` 時複製這個 skeleton |
| SOP 演進架構設計範本 | `templates/architecture-design-template.md` | **2026-06-10 新建**:寫 `_ARCHITECTURE_v<n>.md` 設計文件時複製這個 skeleton |
| 身份重塑 3 種情境 1 頁 cheat sheet | `references/three-scenarios-cheatsheet.md` | **2026-06-10 新建**:3 種情境(繼承/重塑/演進)的觸發訊號+決策矩陣 1 頁對照表,給緊急情況下快速判斷用 |