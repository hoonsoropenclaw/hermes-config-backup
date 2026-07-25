# SOP Enforcement Architecture — 外部驗收機制設計

## 核心問題

LLM 每次推理時從多個原料（soul.md、MEMORY.md、skills、context）動態加权，導致輸出不穩定。即使更新了 SOP 文件，也無法保證下次會遵守。

**「越用越聰明」只在有外部驗收機制的情況下才成立。**

---

## 三層服從架構

### Layer 1：Soft Guidance（最低保障）

- **機制**：SOP 寫在技能文件裡，LLM 上下文注入
- **問題**：這次會參考，下次不一定；LLM 對自己輸出有正向偏差
- **穩定性**：★☆☆☆☆

### Layer 2：Tool Enforcement（約束）

- **機制**：`tool_use_enforcement: auto` in config.yaml，某些場景必須用指定工具
- **優點**：硬約束，比 soft guidance 穩定
- **穩定性**：★★★☆☆

### Layer 2.5：Automated SOP Validation（半自動化，已實作 ✅）

- **機制**：sub-agent 交付後自動對照 SOP 檢查，FallbackValidator 備援
- **實作**：`skills/productivity/automated-sop-validation/scripts/sop_validator.py`
- **合約**：`skills/productivity/automated-sop-validation/contracts/*.contract.yaml`
- **穩定性**：★★★★☆
- **關鍵**：CRITIC 發現「LLM 無法僅靠自身進行可靠的自我驗證，驗證必須是外部觸發」

### Layer 3：External Validation（真正有意義）

- **機制**：
  1. 任務完成後，外部系統對照 SOP 檢查結果
  2. 發現偏移，強制要求重新執行或記錄偏差
  3. 偏差記錄當作反饋，納入下次的決策流程
- **關鍵**：這個驗收系統不能依賴 LLM 自己判斷（否則又回到 Layer 1）

---

## 驗收機制設計原則

### 觸發條件（什麼時候該驗收）

- **每次任務交付前**：必須對照 SOP 檢查
- **用戶問「做到了嗎」**：用外部基準回答，不是 LLM 自我報告
- **主動匯報改進成果時**：必須有量化數據或外部驗證

### 驗收方式

1. **自動化測試**：寫測試案例驗證 SOP 行為（如 unit test）
2. **外部基準**：對照預先定義的正確輸出
3. **人類反饋**：用戶回饋是唯一可靠的驗收信號
4. **量化追蹤**：記錄偏移次數、重新執行次數

### 當偏差發生時

1. 明確標記「這次偏離了 SOP，正確應該是 Y」
2. 重新執行
3. 記錄到日誌，累積數據

---

## 與 Hermes 的整合

### tool_use_enforcement 配置

在 `config.yaml` 中：
```yaml
tool_use_enforcement: auto  # 強制某些場景使用指定工具
```

### 驗收循環（Hermes 主體執行）

1. Sub-agent 完成任務，回傳結果
2. 主體對照 SOP 檢查
3. 若偏移，記錄並要求重新執行
4. 結果寫入 memory

---

## 常見誤解

| 誤解 | 真相 |
|------|------|
| 「把 SOP 寫清楚就會遵守」 | Layer 1 的 soft guidance，LLM 可選擇性忽略 |
| 「我聲稱進步了 = 有進步」 | LLM 對自己輸出有正向偏差，需要外部驗證 |
| 「學會了技能 = 會用」 | 沒有 enforcement，技能只是知識不是行為 |
| 「Layer 2.5 已經有人做了」 |2026-05-31 之前只是理論檔案，本次才是真正實作 |

---

## 實用檢查清單（每次交付前）

- [ ] 這次任務有沒有對照 SOP？
- [ ] 輸出是「unconfirmed」還是「verified」？
- [ ] 有沒有外部信號（用戶/測試）驗證結果？
- [ ] 如果偏離了，正確做法是什麼？