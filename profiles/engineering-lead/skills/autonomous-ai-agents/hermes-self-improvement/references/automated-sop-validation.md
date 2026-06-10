# Automated SOP Validation — 實作路徑

## 目標
在 sub-agent 交付後、發送給用戶前，自動對照 SOP 檢查產出。

這是 Layer 2.5（半自動化驗收）——比純 soft guidance（Layer 1）更強，但還不到完全外部基準驗收（Layer 3）。

---

## 觸發時機

每次 sub-agent 回傳「完成」狀態時，由赫米斯主體觸發，不是 sub-agent 自己做。

---

## 檢查模式

### 1. 關鍵字比對（基礎）
```python
# 讀取 SKILL.md 中的「交付標準」章節
# 在 sub-agent 產出中搜尋關鍵字是否出現
# 缺點：LLM 可通過「假裝包含關鍵字」欺騙
```

### 2. 結構比對（進階）
```python
# 檢查產出是否具備 SOP 定義的結構要素
# 例如：程式碼交付應包含「 imports、函式定義、錯誤處理」
# 報告交付應包含「背景、方法、結果、結論」
```

### 3. 外部基準（Layer 3，需要自動化測試）
```python
# 對預先定義的輸入，檢查輸出是否匹配預期
# 例如：send_email skill → 實際發送郵件並驗證送達
# 例如：code generation → 執行測試案例驗證正確性
```

---

## 實作架構

```
sub-agent 完成 →
  hermes 主體接收產出 →
  讀取對應 SKILL.md 的「交付標準」 →
  執行檢查腳本（關鍵字/結構比對）→
    合規 → 交付給用戶
    不合規 → 記錄偏差，觸發重新執行或標記「unconfirmed」
```

---

## 與赫米斯 cron 的整合

在 `cron/jobs.json` 中，`metacognitive-learner` 任務完成後，可串接 `automated-sop-validation` 檢查。

實際流程：
1. `metacognitive-learner` 產生學習報告
2. `automated-sop-validation` 對照 `metacognitive-learner/SKILL.md` 的交付標準檢查
3. 若通過，寫入 memory；若不通過，記錄偏差

---

## 限制

- Layer 2.5 仍依賴 LLM 解讀結構，理論上仍可被欺騙
- 真正杜絕欺騙需要 Layer 3（外部基準、自動化測試、人類反饋）
- 赫米斯目前沒有專屬的測試執行環境（如 `playwright` 已具備但非所有技能都適用）

---

## 參考資源

- SOP-Agent 論文：https://arxiv.org/pdf/2501.09316（decision-graph 將 SOP 轉為可執行工作流）
- CRITIC 論文：https://proceedings.iclr.cc/paper_files/paper/2024/hash/fef126561bbf9d4467dbb8d27334b8fe-Abstract-Conference.html
- Agent Behavioral Contracts：https://github.com/agentcontract/agentcontract-py