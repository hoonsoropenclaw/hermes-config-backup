# Handoff Chain PRD 驗收 SOP

**用途**：任何 ≥ 2 棒 handoff chain 結束後，主 session 必須對照 PRD Must 清單執行 4 步驗收。  
**觸發條件**：`^專案` chain 跑完後自動觸發（不論 sub-agent 自評結果）。

---

## 4 步驗收流程

### Step 1：撈 PRD Must 清單
```
# 從 handoff/<slug>/prd.md 找所有 Must 項目
grep -n "Must" ~/.hermes/handoff/<slug>/prd.md
```
產出：一份 Must 編號 + 描述清單（如 M-01 ~ M-09）

---

### Step 2：撈 sub-agent 自評
```
# 找 chain 上每棒結尾的 self-audit 檔
ls ~/.hermes/handoff/<slug>/line_*_completion.md
cat ~/.hermes/handoff/<slug>/line_*_completion.md
```
重點：確認 sub-agent 是否填了「實作位置」（檔案/函式/行號），空填 = 未實作。

---

### Step 3：真實命令驗收（每個 Must 逐項）
對每個 Must，跑**真實命令**驗證：

| Must 類型 | 驗證命令 |
|-----------|---------|
| API 存在 | `cat <實作檔>` 或 `grep -n "method\|route" <實作檔>` |
| UI 存在 | `ls <前端檔路徑>` 或 `cat <前端檔>` |
| 功能正確 | `curl http://localhost:3000/api/...`（需先確認 local server 在跑）|
| 資料庫 | `cat <schema檔>` 查 table schema |
| RBAC/隔離 | `grep -n "audience\|role\|permission" <實作檔>` |

**禁止**：只靠 sub-agent 自評的 ✅/🟡/❌ 標記。  
**必須**：自己 grep/cat 驗證，附實際輸出到最終報告。

---

### Step 4：落差報告
產出 `~/.hermes/handoff/<slug>/deliverable_audit.md`，格式：

```markdown
## 完成度總覽
| 狀態 | 數量 | Must 編號 |
|------|------|----------|
| ✅ 通過 | N | M-xx, M-yy |
| 🟡 半套 | N | M-zz |
| ❌ 未做 | N | M-ww |

**最終完成度 = N/9 = XX%**
```

---

## Must 狀態判定標準

| 判定 | 條件 |
|------|------|
| ✅ 通過 | API + UI + 資料庫 全部到位，且可驗證 |
| 🟡 半套 | API 有但 seed 無測試資料，或無真實上傳/操作測試 |
| ❌ 未做 | sub-agent 自評空白、實作位置為 `(空)`、或 `v1 不做` |

---

## 額外檢查：密碼修改 / 編輯 UI / 刪除 UI
這 3 項常被 sub-agent 忽略但使用者預期會有：
- 密碼修改：`grep -n "change.password\|password" <slug>/**/route.ts`
- 編輯 UI：`ls <slug>/**/edit/page.tsx`
- 刪除 UI：`ls <slug>/**/AnnouncementActions.tsx`

---

## 判定邏輯

```
If 任何 Must 是 ❌
    Then 不交付完整完成度
    Then 在最終報告標註具體缺少的 Must
    Then 問使用者「要補完還是先上線」

If 所有 Must 都是 ✅
    Then 完成度 100%
    Then 可交付

If Must 完成度 < 70%
    Then 這是 handoff chain 的系統性失敗
    Then 觸發「為什麼 engineering-lead 漏了 M-06/M-07/M-08」的自審
```

---

## 與 handoff-monitor 的關係

- `handoff-monitor`（`~/.local/bin/handoff-monitor`）：**過程監控**，每 5 分鐘檢查 sub-agent 是否活著、產出是否增加
- 本 SOP（`handoff-chain-acceptance-sop.md`）：**結果驗收**，chain 跑完後對照 PRD 逐項檢查

兩者**不可替代**。monitor 正常不代表驗收通過。

---

## 2026-06-11 school-bulletin 案例教訓

| 問題 | 教訓 |
|------|------|
| engineering-lead 自評 M-01 ✅，但 UI Edit/Delete 實為 ❌ | sub-agent 自評不可信，Step 3 必須自己 grep |
| M-06(M-07/M-08) 完全未做，聲稱「v1 不做」但 PRD 無此記錄 | PRD 沒有「v1 不做」共識就跳過 = 私自縮減範圍 |
| 密碼修改 / 編輯 UI / 刪除 UI 是額外補強項，不是 PRD Must | 使用者預期基本功能被當「補強」= 溝通斷裂 |
| 4 棒 chain 跑完才發現 55% 完成 | 沒有 intermediate checkpoint，每棒做完都該驗 |

---

**If** `^專案` chain 跑了 ≥ 2 棒  
**Then** 本 SOP 必跑  
**If** Must 完成度 < 100%  
**Then** 不在最終報告寫「圓滿完成」，要如實呈現落差
