# Hermes 代理 Handoff Chain 範本區

> **這裡是「未來要建新鏈時的範本區」，不是「目前進行中的鏈」。**
> 目前進行中的鏈直接放在 `~/.hermes/handoff/<project-slug>/`（頂層目錄），例如 `skill-language-exchange-platform/` 就是「`^專案`」這個活躍鏈的 project。

---

## 怎麼用這目錄

### 情境 A：你想建一條新鏈

1. 開新的 chat 跟 default orchestrator 說：「我要建一條叫 X 的鏈」
2. default orchestrator 會從這目錄的範本 + 既有 `@learning` 範例幫你規劃
3. 規劃好後 default orchestrator 會建一個 `~/.hermes/handoff/<new-slug>/` 並寫 `_plan.md`
4. **不要**在這目錄建任何東西（這目錄是唯讀範本區）

### 情境 B：你只想看目前有哪些鏈

```bash
ls ~/.hermes/handoff/   # 看到的就是目前所有「進行中 + 已完成 + 失敗」的 project
```

**注意**：每個 `<project-slug>/` 都是一條**曾經跑過**的鏈、不是範本。範本統一在 `_chains/` 跟 `_template/`。

---

## 這目錄有什麼

| 檔 | 用途 |
|----|------|
| `README.md` | 本檔、使用手冊 |
| `SCHEMA.md` | 鏈條結構定義（鏈由什麼組成、怎麼算合法鏈） |
| `EXAMPLE-at-project.md` | 「`^專案`」鏈的結構化範例（**目前唯一真實鏈**） |

---

## 目前真實鏈的盤點（2026-06-11）

| 鏈名 | project-slug | 階段數 | 狀態 | 走過的代理 |
|------|--------------|--------|------|-----------|
| **`^專案`** | `skill-language-exchange-platform` | 5 階段 | ✅ 完成（Jun 10 21:11） | consumer-researcher → product-planner → system-architect → (engineering-lead 預定) → (test-engineer 預定) |

> **命名說明**：
> - 「`^專案`」= 觸發 handoff pipeline 的 keyword（**Shift+6 鍵盤原生**、與 `@學習` 視覺分工明確）
> - 2026-06-11 從 `@專案` 改為 `^專案`：避免 `@學習` skill 觸發混淆、shell 無風險、輸入零摩擦
>
> **重要**：常駐代理的「`@學習`」= `trial-and-error` skill（試誤學習的觸發標記），**不是 handoff 鏈**。Handoff chain 都是「專案」維度、不是「技能學習」維度。

**只有 1 條**。其他目錄：
- `school-multidept-site/` —— 2 階段早期測試（market-research → prd）、**不代表真實鏈**
- `test-engineer-bootstrap/` —— 基礎建設驗證用、**不是專案鏈**

---

## 未來想建新鏈時、怎麼做

### 步驟 1：想清楚 3 件事

| 問題 | 範例（@學習） |
|------|--------------|
| **輸入是什麼**？ | 學習者痛點、語料 |
| **輸出是什麼**？ | 教學網頁 + 互動題庫 |
| **需要哪些職能**？ | 研究 + 規劃 + 教學設計 + 工程 + 測試 |

### 步驟 2：對照 SCHEMA.md 決定鏈條

- 需要消費者研究嗎？→ 找 `consumer-researcher`
- 需要 PRD 嗎？→ 找 `product-planner`
- 需要技術架構嗎？→ 找 `system-architect`
- 需要實作嗎？→ 找 `engineering-lead`
- 需要測試嗎？→ 找 `test-engineer`
- **缺哪個職能**？→ 跟 default orchestrator 討論要不要建新代理

### 步驟 3：跟 default orchestrator 說「走 handoff 流程」

default orchestrator 會：
1. 跟你確認鏈條、跳過哪些階段
2. 建 `~/.hermes/handoff/<新-slug>/` 並寫 `_plan.md`
3. 觸發第一階段代理
4. 串接後續

### 步驟 4：追蹤進度

```bash
# 看所有進行中/已完成的 project
ls ~/.hermes/handoff/

# 看某 project 的 _plan.md（鏈條規劃）
cat ~/.hermes/handoff/<slug>/_plan.md

# 看某 project 的 _handoff-log.md（觸發時間軸）
cat ~/.hermes/handoff/<slug>/_handoff-log.md
```

---

## 為什麼「不建具體鏈、只建架構」

> 你的要求：「其他的鏈先不要建，但可以先把這個架構建立起來」

理由：
- **不建反編譯鏈**：decompiler-agent 還沒建、refactor-architect 還沒建、沒有任何真實輸入（你沒給我「這坨 .exe 跑出 pseudocode 給我重構」的需求）
- **建架構就夠**：有了 SCHEMA + EXAMPLE、未來你給需求時 default orchestrator 可以直接拿範本套
- **避免「先建好但從來沒跑」的空殼鏈**：MCP 顯示 `ls` 會看到一堆目錄、誤導「這些是 active 鏈」、但實際沒用過

---

## 跟 `_template/` 的差別

| | `_template/` | `_chains/` |
|---|--------------|-----------|
| **用途** | 5 階段**交付物**範本（consumer-needs-research.md 長什麼樣、prd.md 長什麼樣） | 鏈條**組合**範本（要跑哪些代理、跳過哪些、怎麼串） |
| **粒度** | 單一檔案（一份報告的格式） | 整條鏈（一個 project 的代理順序） |
| **怎麼用** | `cp consumer-needs-research.template.md <new-project>/consumer-needs-research.md` | `cp EXAMPLE-at-project.md <new-project>/_plan.md` 後改 |

兩個目錄是**正交**的：`_template/` 解決「每個代理產出什麼格式」、`_chains/` 解決「哪些代理按什麼順序串起來」。
