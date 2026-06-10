---
name: workspace-folder-layout
description: "hoonsoropenclaw 工作區（home 根目錄 / Y 槽遠端硬碟）的檔案組織 SOP。當要建立新檔案/資料夾、判斷該放哪、搬移現有專案、或維護 RULES.md 時載入此 skill。涵蓋三分層架構（permanent-projects / temporary-projects / tools）、命名規則、搬移前檢查清單（.git/.vercel/cron hardcode/.env.local 連動）、RULES.md 同步慣例。"
version: 1.0.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [workspace, file-layout, organization, sop, n100]
    triggers: [new-file-decision, project-move, rules-md-update, file-classification]
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
| 1.0.0 | 2026-06-06 | 初版：三分層架構（permanent/temporary/tools）、決策流程、搬移 SOP、RULES.md 維護慣例 |
