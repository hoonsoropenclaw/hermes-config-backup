---
name: workspace-folder-layout
description: "hoonsoropenclaw 工作區（home 根目錄 / Y 槽遠端硬碟）的檔案組織 SOP。當要建立新檔案/資料夾、判斷該放哪、搬移現有專案、**磁碟盤點與清理（「這資料夾亂七八糟，按目前分類規則重排」）、或維護 RULES.md 時載入此 skill。涵蓋三分層架構（permanent-projects / temporary-projects / tools）、命名規則、搬移前檢查清單（.git/.vercel/cron hardcode/.env.local 連動）、RULES.md 同步慣例、磁碟盤點 SOP（目錄檔案審計 + SHA256 內容驗證 + 雙保險 /tmp 備份）。"
version: 1.1.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [workspace, file-layout, organization, sop, n100, disk-cleanup, audit]
    triggers: [new-file-decision, project-move, rules-md-update, file-classification, disk-cleanup, disk-audit, messy-folder, classify-files]
    related_skills: [user-collaboration-style, trial-and-error, hermes-config-layout]
---

# Workspace Folder Layout — hoonsoropenclaw 工作區檔案組織 SOP

**核心職責**：當使用者問「這檔案該放哪」「這個專案要搬到哪」「RULES.md 要不要更新」「N100 搬移有什麼坑」時，提供**單一真實來源**的決策依據與標準作業流程。

**適用範圍**：`/home/hoonsoropenclaw/`（N100 迷你電腦的 home 目錄，對應使用者主電腦的 Y 槽遠端硬碟）。

**不適用範圍**：
- `~/.hermes/` 內部配置 → 用 `hermes-config-layout` skill
- `~/.openclaw/` 系統資料 → 不手動管
- 使用者專案內部結構（每個專案自己的 AGENTS.md / README 才是權威）

---

## 何時使用

**觸發**（任一符合即載入）：

- 使用者要建立新檔案/資料夾，問「該放哪裡」
- 使用者要搬移現有專案（含改路徑、分類、改 git remote）
- 使用者要更新 `~/RULES.md` 或對 RULES.md 內容有疑問
- 跨 session 維護工作區時，要驗證目錄結構還符合最新規則
- 接手 N100 上的舊專案，盤點其歸屬

**Always-on 提醒**：本 skill 是「決策輔助」，**不是自動執行**。赫米斯接到任務時應該先讀一次，再判斷要不要套用 SOP。

---

## 核心架構：三分層

```
~/ (home 根目錄)
├── permanent-projects/   ← 🟢 常駐專案（會持續維護、已部署、production）
├── temporary-projects/   ← 🟡 暫時專案（一次性產出、做完不維護）
├── tools/                ← 🔵 第三方工具鏈（CLI/npm，原始碼不動）
├── scripts/              ← ⚙️ 輔助腳本（shell/python，cron 用的）
├── documents/            ← 📄 正式文件 & 素材（公文、表單、子目錄分類）
├── Snapshot/             ← 📸 Hermes 自動螢幕快照（純圖片）
├── AutoLearningKnowledge/ ← 📚 學習素材（YT 字幕、書摘）
├── RULES.md              ← 📋 工作區單一真實來源（赫米斯必讀）
└── .hermes/ .openclaw/   ← 🔧 系統資料（不手動管）
```

### 三分層判斷標準

| 分類 | 進去該看到什麼 | 典型範例 |
|------|---------------|----------|
| `permanent-projects/` | `.git` + `.vercel` + `index.html` + `SPEC.md` | `hermes-portal/`、`hermes-status-site/` |
| `temporary-projects/` | 沒 `.git` 或只有本地 `.git`、可能有 `README.md` 標「做完沒」 | `raphael-portfolio/`、`raphael_workspace/dashboard/` |
| `tools/` | 完整第三方原始碼、可能有上游 remote（如 `jo-inc/...`） | `camofox-browser/` |

**判斷的核心問題**：

1. 這個專案 1 年後還會被維護嗎？→ 是 → permanent
2. 這個專案做完就放著？→ 是 → temporary
3. 這是別人寫的工具，我只是用？→ 是 → tools
4. 都沒有？→ 開新分類 + 同步更新 RULES.md

---

## 新檔案落點決策流程

拿到新任務（建立檔案/資料夾/專案）時，依序問這 4 題：

```
Q1. 這是「第三方工具/CLI/工具鏈」嗎？
   → 是 → tools/<tool-name>/
   → 否 → Q2

Q2. 這是「會持續維護的常駐專案」嗎？
      （要部署、要推 GitHub、production 環境）
   → 是 → permanent-projects/<project-name>/
   → 否 → Q3

Q3. 這是「一次性的暫時專案」嗎？
      （作品集、實驗性 dashboard、做完就放）
   → 是 → temporary-projects/<project-name>/
   → 否 → Q4

Q4. 這是「腳本/文件/截圖/素材」嗎？
   → 可執行腳本 (.sh/.py) → scripts/
   → 正式文件/公文        → documents/<分類子目錄>/
   → 自動螢幕截圖         → Snapshot/
   → 學習素材（YT 字幕等）→ AutoLearningKnowledge/<來源>/

❓ 都不符合？
   → 開新分類目錄
   → 同步回來更新 ~/RULES.md 的「根目錄分層架構」圖
   → 同步回來更新本 skill 的「核心架構」段落
```

**禁止的反模式**：
- ❌ 把網站專案塞進 `Snapshot/`（截圖目錄）
- ❌ 把 `.git` 專案直接放 `permanent-projects/` 沒先確認 git remote
- ❌ 把第三方工具放 `permanent-projects/`（會誤以為是我寫的）
- ❌ 開新分類沒同步 RULES.md（下次赫米斯找不到規則）

---

## 命名規則

### 專案資料夾（kebab-case，全小寫）

| 父層 | 適用情境 | 範例 |
|------|----------|------|
| `permanent-projects/` | 會部署、會回頭改 | `hermes-portal/`、`hermes-status-site/` |
| `temporary-projects/` | 一次性產出 | `raphael-portfolio/` |
| `tools/` | 第三方 CLI | `camofox-browser/` |

### 專案字尾慣例（選用但建議）

| 字尾 | 適用 | 範例 |
|------|------|------|
| `-site` | 純靜態網站 | `hermes-status-site/` |
| `-portal` | 入口網站 | `hermes-portal/` |
| `-app` | 需要後端的全端應用 | `school-form-app/` |
| `-dashboard` | 儀表板類 | `my-dashboard/` |
| `-portfolio` | 個人/對外作品集 | `raphael-portfolio/` |
| （無字尾） | npm 工具 / CLI | `camofox-browser/` |

### 文件 & 素材

格式：`<編號>_<名稱>.<副檔名>`，編號補零兩位

✅ `documents/demo_gov_docs/01_年度工作計畫書.png`
❌ `documents/demo_gov_docs/年度工作計畫書.png`（沒編號）
❌ `documents/年度工作計畫書.png`（沒分類子目錄）

### 截圖

格式：沿用工具預設。`Snapshot/` 內舊檔不強迫改名。

---

## 協作風格備註（2026-06-10 使用者要求確立）

**使用者說「先做零風險清理，然後一步一步確認」** —— 這代表：

- ✅ **磁碟清理任務**預設要「分批、每批做完整驗證才進下批」
- ✅ **不要一次性動手**所有可疑檔案
- ✅ **先列分類評估報告**（每個檔案該不該動、建議去哪、為什麼），使用者看完決策後再分批執行
- ✅ **每批結束要回報「改了什麼、驗證什麼、SHA256 對不對、/tmp 備份在哪還原」**

---

## 磁碟盤點 SOP（清理「很亂的資料夾」用，2026-06-10 新增）

**觸發情境**：
- 使用者說「X 資料夾看起來很亂」「Y 資料夾裡的檔案都是會用到的嗎」「按照目前分類規則重排」
- 接手一個沒盤點過的工作區目錄
- 想驗證現有目錄是否符合 hermes 設計慣例（例如 `~/.hermes/` 應有 `cache/` `config/` 子目錄）

### 為什麼要獨立 SOP

「X 資料夾有哪些檔案要搬」**不是**單純 `ls` 就好——需要交叉驗證 3 件事：
1. **這個檔案應不應該在這**（vs 上游/工具的設計慣例）
2. **這個檔案有沒有被別人 reference**（hardcode 路徑、其他程式讀取）
3. **搬了會不會壞**（上游會自動重建？active 設定依賴？）

漏一個就壞、或搬了等於白搬。

### 標準步驟（5 階段）

**階段 1 — 盤點（只看、不動）**

```bash
# 1.1 列出所有根目錄檔案（不包含子資料夾）與大小、時間
cd <target-dir>
find . -maxdepth 1 -type f -printf "%-10s  %TY-%Tm-%Td %TH:%TM  %p\n" | sort -k2,3

# 1.2 列出所有子目錄
ls -d */
```

**為什麼先盤點**：知道有幾個檔案、總大小、有沒有「撐場」大檔（state.db 273MB 之類），決定後續要分幾批。

**階段 2 — 分類（按職責標記）**

對每個檔案依序問 5 題：

```
Q1. 這個檔案是「系統/上游設計就在這」嗎？
   → 是 → 標記 🔵 不可動（找出證據：grep 原始碼、讀 README、查設計文件）
   → 否 → Q2

Q2. 應該在某個子目錄嗎？（cache/、config/、logs/、archive/...）
   → 是 → 標記 🟢 可搬到子目錄
   → 否 → Q3

Q3. 應該移到 hermes 外部嗎？（secrets → ~/.local/share/hermes/secrets/）
   → 是 → 標記 🔴 需移到外部（高風險、需評估相依性）
   → 否 → Q4

Q4. 是孤兒/過期/可清嗎？
   → 是 → 標記 🟠 可刪
   → 否 → Q5

Q5. 兩個位置都有、內容不同的檔案？
   → 是 → 標記 ⚠️ 雙檔衝突（使用者決策哪份才是 source of truth）
```

**關鍵原則**：標記前**先 grep 證據**（不要憑印象判斷）。例如：
- 「`SOUL.md` 該不該在根目錄」→ grep hermes 啟動程式碼，看它從哪讀
- 「`interrupt_debug.log` 搬了會怎樣」→ grep 看有沒有程式會自動重建
- 「`*.pre-refresh-*` 過渡檔能不能刪」→ grep 看 active 程式碼是否 reference

**階段 3 — 給使用者看評估報告（不動手）**

報告必含 4 段：
1. **總覽圖**（按 Q1-Q5 標記分組的檔案清單）
2. **每個檔案的決策依據**（grep 證據 + 為什麼這樣分）
3. **風險分級**（零風險 → 高風險）
4. **預設計畫**（哪些先做、哪些要再決策）

**為什麼先報告不動手**：使用者 INTJ、要求「非常詳細且完整的各個方面的修正方向建議，請儘量不要漏掉」。先報告 = 給他機會審視方向，避免做白工。

### 階段 4 — 分批執行（每批獨立備份+驗證）

每批的 SOP：

```bash
# 4.1 備份：先 SHA256 + 純文字副本到 /tmp
mkdir -p /tmp/<cleanup-name>-<date>
cp -p <file1> <file2> ... /tmp/<cleanup-name>-<date>/
sha256sum <file1> <file2> ... | tee /tmp/<cleanup-name>-<date>.sha256

# 4.2 動手：mv / rm（先建好目標子目錄）
mkdir -p <target-subdir>
mv <file> <target-subdir>/

# 4.3 驗證：SHA256 對比、檔案在目標處、根目錄已清
cd <target-subdir>
sha256sum <file>     # 對比 /tmp 備份的 fingerprint
cd <target-dir>
ls -la <file> 2>/dev/null || echo "✅ 根目錄已清"
```

**或者用自動化腳本**（省下手動 4 步）：

```bash
~/.hermes/skills/workspace-folder-layout/scripts/atomic-move-with-verify.sh \
  <source-file> <target-dir> [label]
```

腳本會自動：(1) 備份到 `/tmp/hermes-cleanup-<label>-<date>/`、(2) 記 SHA256、(3) 建目標、(4) mv、(5) 驗證 SHA256、來源已清、(6) 失敗自動 rollback。輸出末段會印出還原指令。

**為什麼用 `cp -p` + `mv` 而不是 `rm`**：
- `rm` 後悔就沒了
- `cp -p` 保留權限/時間戳、`mv` 在同一個 filesystem 是 atomic
- /tmp 雙保險比單一 .git stash 可靠（/tmp 不進 git）

**階段 5 — 最後驗證（heres / 程式還能跑）**

```bash
# 5.1 主程式還在
which hermes && hermes --version

# 5.2 設定檔仍可讀
python3 -c "import yaml, json; yaml.safe_load(open('config.yaml')); json.load(open('auth.json'))"

# 5.3 重大東西還在
ls -la state.db  # 或其他不能動的檔

# 5.4 列出 /tmp 備份位置（給使用者後悔藥）
ls -la /tmp/<cleanup-name>-<date>/
```

### 風險分級表（給使用者決策用）

| 等級 | 動作 | 必做驗證 | 還原難度 |
|------|------|----------|----------|
| 🟢 零風險 | 搬到沒人 reference 的子目錄、刪過渡檔 | SHA256 + 檔案還在目標處 | 1 指令從 /tmp 還原 |
| 🟡 中風險 | 動 hermes runtime 會讀的檔 | 額外跑 hermes --version、檢查所有 .lock/.pid | 還可能觸發 hermes 自動重建 |
| 🟠 高風險 | 動 state.db 系列、active config、雙檔衝突 | 完全重啟 hermes、跑 cron job 測試 | 可能要 restore from backup |
| 🔴 不可動 | 上游 hardcode 在根目錄（`.hermes_history`、`state.db`） | 不動 | — |

### 易踩的坑（2026-06-10 實戰記錄）

- ❌ **沒 grep 就判斷「這個檔案可以搬」**——可能漏掉上游 hardcode。例如 `cli.py:12558` 把 `interrupt_debug.log` 寫死根目錄，搬了等於白搬（下次 hermes 自動重建）
- ❌ **沒備份就刪**——使用者後悔無法還原
- ❌ **一次動太多檔案**——出問題難定位是哪個動作造成的
- ❌ **驗證只看「檔案在目標處」沒看「根目錄真的清了」**——可能 mv 失敗半殘
- ❌ **沒分批、沒分報告**——使用者看不到「這次動了什麼」，信任扣分
- ❌ **「應不應該在這」憑印象**——必 grep 原始碼、必看 README、必驗證路徑

### 驗證清單（每批結束都跑）

- [ ] SHA256 對比：原檔 vs 目標處（內容沒被改）
- [ ] 目標路徑有該檔（用 `ls -la` 確認）
- [ ] 來源路徑已清（用 `ls <file> 2>/dev/null || echo 清`）
- [ ] 重大程式仍能跑（`which hermes`、`hermes --version`）
- [ ] /tmp 雙保險備份還在（給使用者後悔藥）
- [ ] 整批動作記錄下來（檔名、大小、來源 → 目標、SHA256）

### 跟搬移 SOP 的差別

| 維度 | 搬移 SOP（已有） | 磁碟盤點 SOP（本節） |
|------|------------------|----------------------|
| 觸發 | 把已知專案搬到目標分類 | 評估「這資料夾看起來很亂，該不該清」 |
| 範圍 | 一個專案 | 一整個目錄的 N 個檔案 |
| 動作類型 | `mv` 整個專案 | 個別檔案分級（搬/刪/留/外部化） |
| 驗證重點 | `.git` `.vercel` `.env.local` 連動 | SHA256 內容、grep reference、hermes 仍能跑 |
| 協作節奏 | 一次執行 | 分批、每批報告後等使用者決策 |

---

## 搬移 SOP（最常被踩雷的環節）

**為什麼需要獨立 SOP**：搬專案看似只是 `mv`，但實際上會連動 `.git` remote、`.vercel` 專案 ID、cron 腳本 hardcode 路徑、`.env.local` 位置。**漏一個就壞**。

### 觸發情境

- 把現有專案從 `~/` 根目錄搬到 `permanent-projects/` / `temporary-projects/` / `tools/`
- 重新分類現有專案（permanent ↔ temporary）
- 把第三方工具放進 `tools/`

### 標準步驟

**Step 1 — 預先盤點（搬之前必做）**

```bash
# 1. 確認要搬的專案有什麼
cd ~/<project>/
ls -la
echo "---"

# 2. 確認 .git 狀態（哪些有、remote 是誰）
for d in <projects-to-move>; do
  if [ -d "$d/.git" ]; then
    echo "=== $d ==="
    cd "$d"
    git branch --show-current
    git remote -v | head -1
    git status --short
    cd ..
  fi
done
```

**為什麼**：先知道有沒有 `.git`、有沒有 `.vercel`、有沒有 `node_modules`（會讓 mv 變慢）。

**Step 2 — 找出所有 hardcode 這個路徑的地方**

```bash
# 1. cron jobs 有沒有提到這個專案
grep -rl "<project-name>" ~/.hermes/cron/ 2>/dev/null

# 2. scripts/ 內有沒有 hardcode
grep -rl "<project-name>" ~/scripts/ 2>/dev/null

# 3. 其他專案（若跨專案引用）
grep -rl "/home/hoonsoropenclaw/<project-name>" ~ --include="*.sh" --include="*.py" --include="*.md" 2>/dev/null | head -20
```

**為什麼**：cron 腳本（例如 `portal_upload_check.sh`）跟 SPEC.md 都可能 hardcode 絕對路徑，搬完這些會失效。

**Step 3 — 用 `mv` 搬（不用 `cp -r`）**

```bash
# 1. 先建好目標分類目錄
mkdir -p ~/permanent-projects ~/temporary-projects ~/tools

# 2. mv 整個資料夾（保留 .git、.vercel、權限）
mv ~/<project> ~/permanent-projects/
```

**為什麼用 mv 不用 cp -r**：
- ✅ 保留 hardlink、symlink、extended attributes
- ✅ 保留 `.git` 內部結構（不會被破壞）
- ✅ 速度比 cp 快（不需要 copy inode）
- ✅ 天然 atomic，不會出現「搬一半」的中間狀態

**Step 4 — 修所有 hardcode 路徑**

針對 Step 2 找出來的每個檔案：
- 絕對路徑 `/home/hoonsoropenclaw/<project>` → 改成 `/home/hoonsoropenclaw/<新分類>/<project>`
- 用 `sed` 或 `patch` 工具
- 改完 `grep` 驗證

**Step 5 — 驗證清單（必跑）**

```bash
# 1. 確認新位置有東西
ls -la ~/permanent-projects/<project>/  # 或新分類
echo "---"

# 2. 確認 .git 還在
test -d ~/permanent-projects/<project>/.git && echo "✅ .git 保留" || echo "❌ .git 掉了"
cd ~/permanent-projects/<project>/ && git status  # 確認 git 沒壞
echo "---"

# 3. 確認 .env.local 還在（如果原本有）
test -f ~/permanent-projects/<project>/.env.local && echo "✅ .env.local 保留" || echo "⚠️ 沒 .env.local（可能原本就沒有）"
echo "---"

# 4. 跑 live cron 腳本（如果有）做 dry-run
# 例：bash -n scripts/portal_upload_check.sh
# 例：模擬前 20 行，確認 PORTAL_DIR 變數指向新位置
```

### 常見錯誤（搬移必看）

- ❌ **用 `cp -r` 搬**：會把 `.git` 內部 metadata 搞壞，git push 會出錯
- ❌ **沒先找 hardcode**：cron 腳本跑失敗，使用者收到莫名其妙的 log
- ❌ **搬到一半出錯沒 rollback**：必須先想好「如果 mv 失敗，怎麼 revert」
- ❌ **沒驗證 .env.local**：很多專案依賴 .env.local 裡的 API key，路徑錯就直接 500
- ❌ **忘了更新 ~/RULES.md**：下次赫米斯進場不知道有這個分類
- ❌ **搬完才發現 `.vercel/project.json` 裡的 `projectId` 不對**：不會自動壞，但 Vercel 部署時會建立新專案而不是更新現有

### 驗證清單

- [ ] Step 1 盤點完成（知道有 `.git`/`.vercel`/`node_modules`）
- [ ] Step 2 找出所有 hardcode 檔案
- [ ] Step 3 用 `mv` 搬（沒用 `cp -r`）
- [ ] Step 4 修完所有 hardcode 路徑
- [ ] Step 5 跑完驗證（`.git` 在、`.env.local` 可讀、cron dry-run 成功）
- [ ] 更新 `~/RULES.md` 反映新結構
- [ ] （選填）回報使用者：新位置 + 哪些 hardcode 已修 + 還沒做的事

---

## RULES.md 維護慣例

**`~/RULES.md` 是「工作區單一真實來源」**，赫米斯必讀。維護規則：

### 什麼時候要更新 RULES.md

| 觸發 | 動作 |
|------|------|
| 新建一級目錄 | 加進「根目錄分層架構」圖 |
| 重新分類現有專案 | 改對應的「適用範圍」描述 |
| 新增命名規則 | 加進「命名規則」段落 |
| 發現規則有缺漏 | 補進對應段落 + 記進「變更記錄」 |
| 使用者明確改變架構（如這次從「根目錄」改為「三分層」） | 大改 RULES.md + 更新本 skill |

### 變更記錄必填欄位

```markdown
| 日期 | 變更 | 觸發原因 |
|------|------|----------|
| YYYY-MM-DD | ... | ... |
```

### 不要做的事

- ❌ 把 RULES.md 寫成「待辦清單」（那應該是 TodoWrite）
- ❌ 把 RULES.md 寫成「個人筆記」（那應該是 MEMORY.md）
- ❌ 在 RULES.md 貼 token、API key、密碼
- ❌ 每次搬一個檔案就改 RULES.md（過度更新，只在「結構變動」時改）

---

## 與其他 skill 的關係

| Skill | 關係 |
|-------|------|
| `user-collaboration-style` | 本 skill 是「檔案組織」操作版，user-collaboration-style 是「協作風格」 |
| `hermes-config-layout` | 那管 `~/.hermes/` 內部配置；本 skill 管 `~/*` 使用者工作區。**不要混** |
| `trial-and-error/references/execution-sop.md` | SOP-1/2/3 是改 hermes 內部；本 skill 是搬使用者專案。**不同的 SOP 集合** |
| `general-workflow` | OpenClaw 拉的泛工作流，跟本 skill 職責不重疊 |
| `autonomous-ai-agents/hermes-self-improvement` | 管「赫米斯怎麼學」；本 skill 是「赫米斯怎麼管檔案」 |

---

## 已知未處理項目（隨 session 更新）

| 位置 | 問題 | 處置建議 | 優先度 |
|------|------|----------|--------|
| `Snapshot/hermes-commands-site/` | 網站不該放截圖目錄 | 等使用者確認要不要 push GitHub，屆時搬到 `permanent-projects/` | 🟡 中 |
| `~/raphael-portfolio/` | 還在根目錄 | 移到 `temporary-projects/`（待使用者確認內容） | 🟡 中 |
| `~/raphael_workspace/dashboard/` | 巢狀在 `raphael_workspace/` | 移到 `temporary-projects/`（待使用者確認內容） | 🟡 中 |
| `~/.hermes/projects/hermes-portal/` | 疑似跟新位置的 `hermes-portal/` 重複 | 下次進場用 `diff -r` 確認 | 🟡 中 |
| `~/chrome_profile_notebooklm/` | Chrome profile 暫存 | 不處理，瀏覽器自動管理 | 🟢 低 |

---

## 維護

- **patch > create**：本 skill 的「核心架構」「決策流程」「搬移 SOP」段是常駐的；「已知未處理項目」是動態的
- **跟 RULES.md 保持同步**：RULES.md 改了，這邊也要對應改；反之亦然
- **3 個月掃一次**：檢查分類還合不合時宜、有沒有新專案該重新分類
- **不寫敏感個資**：路徑、token、API key 都不該出現在本 skill 內

---

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.1.0 | 2026-06-10 | 新增「磁碟盤點 SOP」段（5 階段：盤點 → 分類 → 評估報告 → 分批執行 → 驗證）、風險分級表、易踩的坑（grep 證據、SHA256 雙保險、分批節奏）。回應使用者「先做零風險清理，然後一步一步確認」—— 協作風格備註段強調分批決策。description 加上「磁碟盤點與清理」觸發 |
| 1.0.0 | 2026-06-06 | 初版：三分層架構（permanent/temporary/tools）、決策流程、搬移 SOP、RULES.md 維護慣例 |
