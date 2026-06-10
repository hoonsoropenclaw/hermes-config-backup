# [專案名稱] 架構決策紀錄(範本)

> **這是 system-architect 代理的 ADR (Architecture Decision Record) 範本**。適用於 M/L 複雜度等級專案。
> 完整方法論見 `~/.hermes/profiles/system-architect/skills/system-architecture/SKILL.md`。
> 複製這個檔、把 `[...]` 佔位符替換成實際內容,完成後存到 `~/.hermes/handoff/<project-slug>/architecture-decisions.md`。

---

建立日期:YYYY-MM-DD
負責代理:system-architect
決策數量:[N 個]
複雜度等級:[M / L]

---

## 什麼是 ADR?

**Architecture Decision Record (ADR)** 記錄「**為什麼我們做這個技術選型**」,讓未來接手者不用再猜。**每個關鍵決策一篇 ADR**,包含:

1. **Context(背景)**:當下我們面對什麼問題?有什麼約束?
2. **Decision(決策)**:我們選了什麼?
3. **Status(狀態)**:提議中 / 已採用 / 已棄用 / 已取代
4. **Consequences(後果)**:好的結果 + 壞的代價 + 風險
5. **Alternatives Considered(替代方案)**:我們考慮過哪些?為何不選?

---

## ADR-001: [決策標題]

**狀態**:[已採用 / 提議中 / 已棄用]
**日期**:YYYY-MM-DD
**決策者**:[誰]

### Context(背景)

[當下我們面對什麼問題?有什麼約束?有什麼利害關係人?]

例:
> 我們需要為 <系統名稱> 選擇主要後端框架。約束:
> - 團隊 4 人都熟 Python、不熟 Go
> - 6 個月內 MVP 上線、不想投資 Go 學習曲線
> - 需要 async 支援(預期 WebSocket 推播、長連線)
> - 預期 1 年內 MAU 1-5 萬、不需極致效能

### Decision(決策)

我們選擇 **[具體選型]**。

例:我們選擇 **Python FastAPI** 作為主要後端框架。

### Alternatives Considered(替代方案)

| 方案 | 優點 | 缺點 | 為何不選 |
|------|------|------|---------|
| Python FastAPI | async 支援、TS-like 開發體驗、自動 OpenAPI、團隊熟 | 沒有 Django 的 admin / ORM 全配套 | — |
| Python Django + DRF | 內建 admin / ORM、文件完整 | async 支援需 Django 3.1+ 且生態系尚在演化、OpenAPI 整合較差 | 暫不選,但若 admin 需求變重可考慮 |
| Node.js (Express + TypeScript) | async 原生、前後端同語言、SSR 友善 | 團隊不熟 TS、需要投資學習 | 6 個月時間壓力下風險高 |
| Go (Gin / Echo) | 效能強、編譯期型別檢查 | 團隊完全不熟、學習曲線陡 | 學習成本不划算 |

### Consequences(後果)

**好的結果**:
- 團隊可用既有 Python 經驗、不需投資新語言
- async 支援原生,WebSocket 整合容易
- 自動產生 OpenAPI 文件,前端可同步開發

**壞的代價 / 風險**:
- Python 動態型別 → 大型 codebase 需靠 mypy 補強
- GIL 限制 CPU-bound 效能 → ML 推論需獨立的 Python process(已預留架構空間)
- 沒有 Django admin → 後台需要自建或用 Retool

**未來什麼情境下要改**:
- 若 MAU > 50 萬需要更高效能 → 改 Go 重寫瓶頸服務
- 若 admin 後台需求暴增 → 評估 Django + DRF

---

## ADR-002: [決策標題]

[同上結構]

### Context
### Decision
### Alternatives Considered
### Consequences

---

## ADR-003: [決策標題]
[同上]

---

## 給 engineering-lead 的「1 小時上手 checklist」

- [ ] 看完所有 ADR 能在 5 分鐘內抓到「為什麼選 X、為什麼不選 Y」
- [ ] 知道每個決策的「未來什麼情境下要改」
- [ ] 知道替代方案是什麼、若要改可以怎麼走
- [ ] 若有疑問,知道哪個 ADR 文件可以深讀

---

## 自我審查(交付前必跑)

- [ ] 每個關鍵技術選型都有對應 ADR?
- [ ] 每個 ADR 都有 Context / Decision / Alternatives / Consequences 四段?
- [ ] 「未來什麼情境下要改」有寫清楚(避免未來 6 個月接手者不知道為何)?

---

**版本**:v0.1 (初稿)
