# 代理身份重塑報告 — 範本

> 寫 `CONVERSION_v<n>_REPORT.md` 時複製這個 skeleton。基於 2026-06-10 `consumer-researcher` 重塑案例提煉。

```markdown
# 代理身份重塑 v<n> 報告:<old-name> → <new-name>

**執行日期**:YYYY-MM-DD
**決策觸發**:<一句話描述為什麼要 pivot>
**代理**:default orchestrator (<主 session 名>)
**執行時長**:約 <N> 分鐘

---

## 1. <N> 項決策落實表

| # | 決策點 | 採用方案 | 落實位置 |
| --- | --- | --- | --- |
| 1 | profile 名稱 | <A/B/C> | `~/.hermes/profiles/<new-name>/`、`~/.local/bin/<new-name>` |
| 2 | skill 庫 | <保留 N 個、砍 M 個> | `~/.hermes/profiles/<new-name>/skills/`(<before> → <after>) |
| 3 | 核心工作流 | <6 步新流程/...> | `persona.md` 「標準工作流程」段 |
| 4 | 報告命名 | `<new-deliverable>-<slug>.md` | `persona.md` 交付物格式、`~/.hermes/handoff/_template/` 範本 |
| 5 | 下游銜接 | <同步更新 <downstream> 的 N 處> | `~/.hermes/profiles/<downstream>/persona.md` |
| 6 | 專案任務 | <A 通用 SOP / B 立即跑一次驗證> | 範本 + handoff README 完整建立 |

---

## 2. 各步驟執行情況

### Step 1: 備份 ✅
- 路徑:`~shared-infra/<old-name>-backup-<date>/`
- 備份內容:`persona.original.md`、`SOUL.original.md`、`config.original.yaml`、`skill-list.original.txt`

### Step 2: 建立新 profile ✅
- 命令:`hermes profile create <new-name> --clone`
- 結果:clone 成功(<N> skill + SOUL.md + config 從 default 帶過來)
- Wrapper 自動建:`~/.local/bin/<new-name>`

### Step 3: 重寫 persona.md ✅
- 新檔:`persona.md`(<N> bytes)
- 結構:身份說明 → 核心信念 → 方法論 → 6 步 SOP → 交付物格式 → Handoff 流程 → 禁止事項 → 語言風格 → 歷史脈絡

### Step 4: 重寫 SOUL.md ✅
- 新檔:`SOUL.md`(<N> bytes)
- 語氣定位:<一句話>

### Step 5: 精瘦 skill 庫 ✅
- 保留清單 <N> 個,分類:...
- 刪除 <M> 個(包含 <特別提到的 N 個>)

### Step 6: Wrapper ✅
- 路徑:`~/.local/bin/<new-name>`(clone 自動建立)

### Step 7: Handoff 目錄 + 範本 ✅
- README 更新:<N> KB
- 範本:`~/.hermes/handoff/_template/<new-deliverable>.template.md`(<N> KB)
- 既有專案處理:<保留/重命名/標 DEPRECATED_>

### Step 8: 更新下游 <downstream> ✅
- <N> 處更新:
  1. ...
  2. ...
  3. ...
  4. ...

### Step 9: 刪除舊 profile ✅
- 命令:`hermes profile delete <old-name>`(PTY 餵確認字串)
- 刪除內容:`~/.hermes/profiles/<old-name>/` + wrapper
- 驗證:`hermes profile list` 顯示只剩 default + <new-name> + <downstream>

### Step 10: 啟動測試 ✅
- 命令:`<new-name> chat -q "請自我介紹..." --cli`
- 結果:persona 完美套用
- 啟動耗時:<N> 秒

### Step 11: 本報告 ✅

---

## 3. 統一性檢查

### 3.1 grep 驗證:沒有殘留「<old-name>」在前線文件

```bash
# 應該為空(只有歷史脈絡說明)
grep -rn "<old-name>" ~/.hermes/profiles/<new-name>/ \
  ~/.hermes/profiles/<downstream>/ ~/.hermes/handoff/README.md
```

**結果**:<N> 個殘留(...)

### 3.2 grep 驗證:舊 `<old-deliverable>` 引用都改了

```bash
grep -rn "<old-deliverable>" ~/.hermes/profiles/<new-name>/ \
  ~/.hermes/profiles/<downstream>/ ~/.hermes/handoff/_template/
```

**結果**:0 個殘留

### 3.3 檔案清單驗證

| 檔案 | 大小 | 狀態 |
| --- | --- | --- |
| `~/.hermes/profiles/<new-name>/persona.md` | <N> B | 新寫 |
| `~/.hermes/profiles/<new-name>/SOUL.md` | <N> B | 新寫 |
| `~/.hermes/profiles/<new-name>/skills/` | <N> 個 skill | <before> → <after> 精瘦 |
| `~/.hermes/profiles/<downstream>/persona.md` | <N> B → <N> B | <N> 處精準更新 |
| `~/.hermes/handoff/README.md` | <N> B | 從 <N> B 重寫 |
| `~/.hermes/handoff/_template/<new-deliverable>.template.md` | <N> B | 新建 |
| `~/.local/bin/<new-name>` | <N> B | 自動建立 |
| `~/.hermes/profiles/<old-name>/` | — | **已刪除** |
| `~/.local/bin/<old-name>` | — | **已刪除** |
| `~/shared-infra/<old-name>-backup-<date>/` | <N> 檔 | 保留備份 |

---

## 4. 意外發現(值得記的)

### 4.1 <新發現 1>
- 觀察:<具體症狀>
- 判斷:<bug / 合理 / 設計>
- 處理方式:<解法>
- L3 教訓:<一句話抽象原則>

---

## 5. 刻意保留(避免無謂改動風險)

| 項目 | 為什麼保留 |
| --- | --- |
| ... | ... |

---

## 6. 未做的(刻意不做)

| 項目 | 為什麼不做 |
| --- | --- |
| ... | ... |

---

## 7. 給未來 default orchestrator 的快速參考

### 7.1 怎麼呼叫 <new-name>

```bash
# 簡單對話(用於釐清任務邊界)
<new-name> chat -q "<任務說明>" --cli

# Handoff 模式(用於接收任務、產出報告)
<new-name> chat -q "<任務說明>" --cli
# 代理會自動把報告寫到 ~/.hermes/handoff/<project-slug>/<new-deliverable>.md
# 報告完成後,default orchestrator 收到訊息,再串接 <downstream>
```

### 7.2 預期代理的產出

- 完整 Markdown 報告(<N> 段:...)
- 路徑:`~/.hermes/handoff/<project-slug>/<new-deliverable>.md`

### 7.3 何時不該用 <new-name>

- 使用者要的是「...」→ 該用 <other-agent>
- 使用者要的是「...」→ **本代理不擅長**,只能給輔助章節
- 使用者要的是「...」→ 該用未來的 <future-agent>

---

## 8. 驗證命令(給未來週期性檢查用)

```bash
# 1. profile 是否存在
hermes profile list | grep <new-name>

# 2. wrapper 是否可執行
ls -la ~/.local/bin/<new-name>

# 3. skill 數量(應為 <N>)
ls ~/.hermes/profiles/<new-name>/skills/ | grep -v "^\." | wc -l

# 4. persona 是否還是新版
head -5 ~/.hermes/profiles/<new-name>/persona.md
# 應包含:「# <新角色名稱>」

# 5. 舊 profile 是否已刪除(應回空)
hermes profile list | grep <old-name>

# 6. 啟動測試
<new-name> chat -q "你是誰?" --cli 2>&1 | head -20
# 應出現:<新角色> 字樣
```

---

## 9. 後續可考慮(非本次任務範圍)

1. <後續優化 1>
2. <後續優化 2>
3. <後續優化 3>

這些等使用者主動提出再啟動。
```
