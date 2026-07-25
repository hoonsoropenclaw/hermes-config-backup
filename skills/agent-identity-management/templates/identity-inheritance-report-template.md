# 代理身份繼承報告 — 範本

> 寫 `IDENTITY_INHERITANCE_v<n>_REPORT.md` 時複製這個 skeleton。基於 2026-06-08 赫米斯＝拉斐爾身份繼承案例提煉。

```markdown
# 代理身份繼承 v<n> 報告

**執行日期**:YYYY-MM-DD
**決策觸發**:<一句話描述為什麼要繼承>
**代理**:default orchestrator
**執行時長**:約 <N> 分鐘

---

## 1. 5 項決策落實表

| # | 決策點 | 採用方案 | 落實位置 |
| --- | --- | --- | --- |
| 1 | 身份繼承的時間錨點 | <YYYY-MM-DD 起的「...」> | 7 份重要檔案的開頭段 |
| 2 | 如何稱呼「過去的那個」 | <前綴修飾:前任 X> | 同上 |
| 3 | 7 份重要檔案改哪些 | <全部 vs 部分> | <列具體改哪些> |
| 4 | 外部資產 ID 改名 vs 保留 | <保留+歷史註解> | TOOLS.md / MEMORY.md 內「外部資產身份繼承」段 |
| 5 | 學習萃取 / 歷史檔案 | <標題改+歷史註解> | <列具體改哪些> |

---

## 2. 各步驟執行情況(13 步)

### Step 1: 全盤 grep 確認影響面 ✅
- 跨 7 份重要檔案:<N> 個檔案
- 跨所有 skill:<N> 個 skill
- 跨 shared-infra:<N> 個檔案
- 跨永久專案:<N> 個檔案

### Step 2: 7 份重要檔案身份段統一改寫 ✅
| 檔案 | 改的段 | 改動摘要 |
| --- | --- | --- |
| IDENTITY.md | 身份卡 | ... |
| AGENTS.md | 標題 + 檔頭 + 重要規範段 | ... |
| USER.md | 興趣範圍 + GitHub 帳號偏好 | ... |
| HEARTBEAT.md | 跟身份相關的描述 | ... |
| TOOLS.md | 拿掉過時共享倉庫、補上 status site 永久路徑 | ... |
| SOUL.md | (通常無) | 跳過 |
| MEMORY.md | 大規模替換、保留歷史脈絡 | ... |

### Step 3: 跨 skill 引用更新 ✅
- `trial-and-error/SKILL.md` 措辭統一
- `trial-and-error/references/by-category/*.md` 加前綴
- 任何 `*-status-*` skill 更新
- 任何 trigger 詞的 skill 確認仍觸發得到

### Step 4: 外部資產處理 ✅
| 不可改的資產 | 保留原因 | 註解位置 |
| --- | --- | --- |
| Vercel 專案名 | 已部署站台、URL 不能改 | TOOLS.md |
| GitHub repo 名 | rename 是大動作 | TOOLS.md |
| 第三方 ID | 不可改 | TOOLS.md |

### Step 5: 學習萃取 / 歷史檔案處理 ✅
- `learning_extract*.md`:標題改 + 歷史註記
- 歷史檔案備份:`shared-infra/<filename>.original.md` + `shared-infra/raphael-workspace-docs/README.md`

### Step 6-7: 統一性驗證 + 報告交付 ✅
- 詳見下方「統一性檢查」段

---

## 3. 統一性檢查

### 3.1 grep 統一性
- 7 份重要檔案內「新身份描述」用字完全一致 ✅
- 跨 skill 引用全部對應 ✅

### 3.2 大小檢查
- MEMORY.md 從 <before> KB → <after> KB(< 25KB 觸發線、距 <N> KB)

### 3.3 「前任」標籤總數
- 每個檔案內應該 1+ 次
- 7 份重要檔案內「<前代理名>」總次數:<N> 次(合理範圍 5-30)

---

## 4. 意外發現(值得記的)

---

## 5. 刻意保留(避免無謂改動風險)

---

## 6. 未做的(刻意不做)

---

## 7. 後續可考慮(非本次任務範圍)

---
```
