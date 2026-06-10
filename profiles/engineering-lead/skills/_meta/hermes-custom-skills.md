# 赫米斯自創技能目錄 (Hermes Custom Skills)

> 本目錄記錄赫米斯 agent 自己創建或修改的技能，與從網路下載、龍蝦市場取得的技能分開管理。
> 龍蝦/網路技能請查閱各技能目錄的 `source` 欄位。

---

## 目錄結構

```
~/.hermes/skills/
├── _meta/
│   └── hermes-custom-skills.md    # 本目錄
├── [category]/
│   └── [skill-name]/
│       └── SKILL.md
└── ...
```

---

## 自創技能列表

### productivity/

| 技能名稱 | 檔案路徑 | 創建日期 | 修改日期 | 說明 |
|---------|---------|---------|---------|------|
| `site-qa-checklist` | `productivity/site-qa-checklist/SKILL.md` | 2026-05-30 | 2026-05-30 | 赫米斯狀態網站部署前 QA 檢查清單。含三層歷史問題搜尋（session_search → mempalace → LLM re-rank）+ Playwright 自動化測試 Phase。 |

### (其他分類待擴充)

---

## 自創修改技能列表（修改現有技能）

> 以下為從網路/龍蝦下載後有進行修改的技能

| 技能名稱 | 原 source | 修改日期 | 修改摘要 |
|---------|----------|---------|---------|
| (目前無) | | | |

---

## 技能新增 SOP

1. **新建技能**：完成後將資訊填入上方「自創技能列表」
2. **修改技能**：將修改摘要填入上方「自創修改技能列表」
3. **下載龍蝦技能**：在 `source` 欄位標明來源，不列入本目錄
4. **刪除技能**：從列表移除，註明刪除日期和原因

---

## 待建立技能藍圖

| 代號 | 技能名稱 | 方向檔路徑 | 狀態 |
|-----|---------|---------|------|
| `skill-composer` | 技能搭配建議之技能 | `productivity/skill-composer/DESIGN.md` | 方向書已完成，待實作 |

### skill-composer 方向書摘要
- **願景**：動態推薦最佳技能組合，根據反饋持續學習
- **核心功能**：Skill Scanner → Composer Engine → Combo Registry → Feedback Tracker → Score Board
- **MVP 範圍**：技能掃描 + 簡單推薦 + 組合註冊 + 手動評價
- **推薦策略**：主技能 + 輔助技能 + 驗收技能 + 通訊技能的 L1-L4 複雜度分級
