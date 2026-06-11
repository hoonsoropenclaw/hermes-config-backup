# MEMORY 25 KB 警戒線清理 SOP（2026-06-09 從本次對話歸納）

> **觸發情境**：`wc -c ~/.hermes/memories/MEMORY.md` > 25600（25 KB 警戒線）時自動啟動。
> **本 SOP 是「plan-first-not-just-do」原則的具體落實**：動手清理前先列清單給使用者看、絕不直接動手。

## 為什麼需要這條 SOP

MEMORY.md 是赫米斯的長期記憶檔，**每次新 session 都會讀**。膨脹到 25 KB 以上會：
- 拖累 context 載入速度
- 增加 token 消耗
- 讓抽象教訓被雜訊淹沒

但**直接動手刪**是反模式：MEMORY 裡的東西都是「過去某個時刻被認為有價值」、刪錯了 L3 教訓會丟失抽象決策原則。

## 5 步流程

### Step 1：跑 wc -c 看真實大小

```bash
wc -c ~/.hermes/memories/MEMORY.md
# 警戒線 25600 = 25 KB
# 高於 = 觸發本 SOP
```

### Step 2：分析檔案結構、找出候選段

```bash
# 看每個 ## / ### 段的大小排行
awk '/^## /{section=$0; len=0; next} /^### /{print len" → "section" / "$0; section=$0; len=0; next} {len+=length($0)+1} END{print len" → "section}' \
  ~/.hermes/memories/MEMORY.md | sort -rn | head -10
```

### Step 3：分類候選段、列清單

對每個候選段按三類歸檔：

| 類別 | 判斷問題 | 處理 |
|---|---|---|
| **🗑️ 刪** | 「這條仍符合 7 天內會過期的條件嗎？」「這條可用 `session_search` 撈回嗎？」→「會」| 直接刪（不需移檔）|
| **📦 移** | 「這條有專門的 skill / classification 該接住嗎？」（如備份細節、平台認證）| 寫到 `trial-and-error/references/by-category/<分類>.md`、MEMORY 換成 L3 索引 |
| **✅ 留** | 「這是 L3 抽象教訓 / 環境事實 / 使用者決策的為什麼？」| 留、但檢查能不能再精簡 |

**特別注意**：
- 過期的「已停用」「2026-05-XX 歷史」段 → 🗑️ 刪
- 「具體平台已認證清單」（Twitter/Reddit 帳號等） → 📦 移到 trial-and-error 或 agent-reach skill
- 「Y:\ = /home/hoonsoropenclaw/」這類環境事實 → ✅ 留、但寫驗證命令（見下）

### Step 4：列清單給使用者看、等他確認（**plan-first-not-just-do**）

把 🗑️/📦/✅ 三類清單列成 Telegram 友善格式（**不要用 pipe table**），寫出：
- **每條為什麼刪/移/留**
- **預期效果**（刪多少 chars、預計降到幾 KB）
- **備案**（如果使用者覺得某條不能刪）
- 問「**好**」或具體哪幾條要保留

**使用者只回「好」** → 才動手。

### Step 5：動手 + 跑 3 件驗證

```bash
# 1. 改完跑 wc -c 看實際效果
wc -c ~/.hermes/memories/MEMORY.md
# 預期：低於 25600

# 2. grep 驗證重要條目還在
grep -c "## 🌟" ~/.hermes/memories/MEMORY.md
# 預期：跟改前一致（重要 ## 段沒被誤刪）

# 3. 跑 hermes status 確認沒改壞
bash -i -c 'hermes status 2>&1 | head -3'
```

### Step 6：結尾報告

照 `@學習` B 模式慣例：
- 改了什麼檔、改了幾段
- wc -c 對照（之前 → 之後）
- 沒刪/沒移的條目跟原因
- 任何**沒達標**的誠實說（例如這次 MEMORY 從 26160 → 25924 chars、仍高於警戒線 324 chars、要不要再清一輪）

## 與 trial-and-error SKILL.md 的 If→Then 對應

- **If** 看到「該清 MEMORY / 該刪 X / 該改 Y」任務 **Then** **plan-first-not-just-do**——動手前先列「推薦處理方案 + 預期效益 + 影響範圍 + 備案」給使用者看。完整 SOP 見本檔。
- **If** 改 MEMORY/AGENTS **Then** 跑完 `patch` 必 `grep` 驗證寫入、不靠 patch 工具成功訊息

## 常見錯誤（這次對話自己犯的）

### 錯誤 1：估算不清、實際效果比預期小

- **症狀**：預期「會砍 ~1700 chars」、實際只砍 ~225 chars
- **根因**：估算時假設被刪段「全段都會被砍」、沒算到新增訊息會填補部分空間
- **預防**：Step 3 列清單時**保守估**、用「預期縮減 50% ~ 80%」區間告訴使用者

### 錯誤 2：分多輪 patch 沒跑中間驗證

- **症狀**：跑 3-4 次 patch 之後才驗證、其中一次可能 patch 寫到錯的位置
- **預防**：每次 patch 後 `grep` 一下確認（即使不麻煩）

### 錯誤 3：把 L3 抽象教訓放錯檔

- **症狀**：把 L3 寫進 AGENTS.md、才發現應該寫 MEMORY.md
- **預防**：Step 3 分類時強制過一次「L3 → MEMORY.md 唯一、L2 → references/by-category/」的判斷

## 相關條目

- [[../SKILL.md#「決策前要看『推薦清單 + 預期效益』再行動」]] — plan-first 原則的源頭
- [[./adding-entries-sop.md]] — 寫新條目 SOP（4 步流程）跟本 SOP 是姊妹篇
- [[./keyword-triggers-sop.md]] — `@學習` 觸發時也會用到本 SOP（清 MEMORY 是 `@學習` 的其中一條產出）
- [[../../memories/MEMORY.md#MEMORY 寫「X 是 Y」也要寫「怎麼驗證」]] — L3 教訓，影響 Step 3 判斷（留的條目要補驗證命令）
