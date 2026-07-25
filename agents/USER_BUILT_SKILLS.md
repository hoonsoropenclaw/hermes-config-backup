# 自建技能清單（User-Built Skills）

本清單用於區分「內建技能（built-in）」與「自建技能（user-built）」。

---

## 自建技能（User-Built）

| 技能名稱 | 版本 | 說明 | 建立日期 |
|----------|------|------|----------|
| `persistent-subagent` | 1.0.0 | 常駐 Subagent 派遣系統，自動讀取身份設定檔注入 context | 2026-05-31 |

---

## 自建身份設定檔（Agents）

| 檔案 | 版本 | 說明 |
|------|------|------|
| `researcher.yaml` | 1.0.0 | 研究者代理 — 資訊收集、事實查證 |
| `writer.yaml` | 1.0.0 | 寫手代理 — 內容創作、文檔撰寫 |
| `coder.yaml` | 1.0.0 | 程式設計師代理 — 程式實作、審查 |
| `analyst.yaml` | 1.0.0 | 資料分析師代理 — 數據解讀、洞察生成 |
| `reviewer.yaml` | 1.0.0 | 審查者代理 — 品質把關、邏輯驗證 |
| `planner.yaml` | 1.0.0 | 規劃師代理 — 任務分解、流程設計 |

---

## 更新記錄

### 2026-05-31
- 新增 `persistent-subagent` skill
- 新增 6 個身份設定檔（researcher/writer/coder/analyst/reviewer/planner）

---

## 如何新增自建技能

1. 在 `~/.hermes/skills/` 下建立 skill 目錄
2. 撰寫 `SKILL.md`
3. 在本清單中新增一列

---

## 內建技能（Built-in）vs 自建技能

- **內建技能**：跟隨 Hermes Agent 更新，位於 `~/.hermes/skills/` 同步區
- **自建技能**：自主維護，不會被 Hermes Agent 更新覆蓋，位於 `~/.hermes/skills/` 自建區

如需明確區分，可將自建技能放在：
```
~/.hermes/skills/persistent-subagent/     ← 自建
~/.hermes/skills/autonomous-ai-agents/    ← 內建（跟隨更新）
```