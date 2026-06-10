# 新增條目 SOP（2026-06-09 從 `@學習` 觸發場景歸納）

> **本檔是 trial-and-error SKILL.md「新增條目 SOP」段的完整版**——SKILL.md 只放 4 步流程、完整決策樹、判斷範例放這。

## 觸發情境

1. 使用者說「`@學習`」/「把這次當 SOP 存起來」/「這個以後會用到」
2. metacognitive-learner cycle 結束時 Phase 4 分流到 L3 隔離
3. 任何 `write_file` 寫進 `references/by-category/*.md` 之前
4. agent 自己發現「我犯的這個錯以前好像也有過」

## 4 步流程（核心）

### Step 1：掃對話

從對話紀錄裡抓候選條目。每個候選至少要含：
- **症狀**（什麼樣的錯誤訊息/失敗行為）
- **根因**（為什麼會這樣）
- **解法**（怎麼修）
- **預防**（If→Then 怎麼寫才不會再犯）

**沒新教訓時**：
- 主動說「我沒看到新教訓」+ 列「我掃了哪些訊息、用什麼方法」+ 問使用者要不要繼續
- **不要硬擠假教訓進去**（污染 trial-and-error）

### Step 2：去重（最容易出錯的步驟）

對每個候選**必須**在整個 trial-and-error 找相似概念：

```bash
# 用 search_files 在所有 references/by-category/ 找
search_files(
  pattern="<候選症狀的關鍵字>",
  target="content",
  path="references/by-category/"
)

# FTS5 全文檢索（更精準）
search_files(
  pattern="<候選症狀 + 根因 + 解法的核心概念>",
  target="content",
  path="."
)
```

**判斷重疊的 3 種情況**:
- **完全重複** → 不新增、告訴使用者「這條之前有寫過、要不要補強」
- **症狀相似但根因不同** → 新增、但在**現有那條**和**新條**都加 `**相關條目**` 連結
- **概念抽象層級不同** → 寫進 MEMORY.md 當 L3、不污染 L2 條目庫

### Step 3：判斷層級

| 層級 | 寫去哪 | 判斷問題 | 範例 |
|---|---|---|---|
| **L2** 具體解法 | `references/by-category/<分類>.md` | 「這個 bug 只在 X 類任務會出現嗎？」 | venv 沒 pip、bash_profile 互動式 return 阻擋 |
| **L3** 抽象教訓 | `MEMORY.md` | 「這個以後別的任務也會踩到嗎？」→ 會 = L3 | 「卸載前必先 dry-run」、「MEMORY 寫 X 是 Y 也要寫驗證命令」 |
| **L1** 具體操作 | **不寫任何檔**、只進 state.db | 「這是 session 內單次操作嗎？」→ 會 = L1、session_search 撈得到 | 單次 deploy 結果、單個 PR 編號 |

**判斷訣竅**:
- 寫得出 `If 觸發情境 Then 解法` = L2
- 寫得出 `If 跨領域情境 Then 抽象決策原則` = L3
- 寫不出 If→Then、只是「那時候做了 X」 = L1、**不寫**

### Step 4：驗證寫入（必跑、不能省）

```bash
# 1. 條目數 +1
grep -c "^### " ~/.hermes/skills/trial-and-error/references/by-category/hermes-internal.md
# 預期：原本 27 → 28（新增 1 條）

# 2. MEMORY.md 沒踩 25 KB 警戒線
wc -c ~/.hermes/memories/MEMORY.md
# 警戒線 25 KB = 25600 chars

# 3. 必跑實際系統驗證（如果是 hermes 相關）
bash -i -c 'hermes status 2>&1 | head -3'
# 不能只信 patch 工具的成功訊息
```

**結尾統一報告**改了什麼（給使用者看、不要藏）：
- 改了幾個檔
- 每個檔改了什麼段落
- 沒做的事跟為什麼

## 常見錯誤（這次對話自己犯的）

### 錯誤 1：寫錯檔（把 L3 教訓塞 AGENTS.md、放回 MEMORY.md 才對）

- **症狀**: patch 完才發現層級跟檔案不對
- **預防**: 寫之前先問「這是 L2 還是 L3？L3 寫進 MEMORY.md 唯一、不是 AGENTS.md」

### 錯誤 2：條目數驗算算錯（少算既有條目、以為 patch 沒生效）

- **症狀**: 預期 +4 條、結果 +5 條、嚇一跳以為重複
- **預防**: `grep -c "^### "` 跑前**先列既有條目**、**算清楚**再加

### 錯誤 3：FTS5 去重沒用 search_files、純手動比對（不嚴謹）

- **症狀**: 手動看條目標題就說「沒重複」、漏掉概念相似的條目
- **預防**: 強制跑 `search_files` 全文檢索、不靠 LLM 記憶判斷

## If→Then 速查

- **If** 候選條目跟現有某條「症狀相似但根因不同」 **Then** 新增、雙向加 `**相關條目**` 連結
- **If** 候選條目跟現有某條「完全重複」 **Then** 不新增、告訴使用者、問要不要補強
- **If** 不知道該放 L2 還是 L3 **Then** 問「這個以後別的任務也會踩到嗎？」→「會」= L3、→「只會在 X 類任務」= L2
- **If** 寫完忘記驗證 `grep`/`wc` **Then** 補跑、不靠 patch 工具的成功訊息
- **If** 對話沒新教訓 **Then** 主動問「要不要繼續」、**不要硬擠**假教訓
- **If** 使用者採「B 模式」（有把握直寫、結尾報告） **Then** 照本 SOP 跑、**不要**列清單等使用者逐一勾（浪費時間）
- **If** 寫錯檔 **Then** 立刻 patch 撤回、**不要**留著「反正兩個檔都有」當冗餘

## 相關條目

- [[../SKILL.md#新增條目 SOP]] — 本檔的精簡版
- [[./by-category/hermes-internal.md]] — 27 條 L2 條目所在
- [[../../memories/MEMORY.md#MEMORY 寫「X 是 Y」也要寫「怎麼驗證」]] — 對應 L3 教訓
