# Architecture Handoff 範本目錄

> **給 system-architect 代理用的交付物範本**。每個新專案從這裡 clone 範本開始寫。

## 範本清單

| 範本檔 | 對應交付物 | 適用複雜度 | 必產 |
|--------|-----------|-----------|------|
| `architecture.template.md` | `architecture.md`(系統架構 + 3 C4 圖) | S/M/L | ✅ |
| `database-schema.template.md` | `database-schema.md`(ER + 規格 + 索引 + 估算 + 備份) | S/M/L | ✅ |
| `api-spec.template.md` | `api-spec.md`(RESTful + 認證 + 限流 + WebSocket) | S/M/L | ✅ |
| `architecture-decisions.template.md` | `architecture-decisions.md`(ADR) | **M/L only** | M+ |

## 複雜度對照(決定產幾份)

| 等級 | 觸發條件 | 產出份數 |
|------|---------|---------|
| **S** | MVP、<8 元件、<10 表、無明確 NFR | 3 份(架構 + 資料庫 + API) |
| **M** | 標準 SaaS、8-20 元件、10-25 表、有 SLA | 4 份(+ ADR) |
| **L** | 平台級、>20 元件、>25 表、有資安/法遵/多區 | 5 份(+ 部署拓樸,見 `architecture.template.md` §4 範例) |

## 使用方式

1. **複製範本到專案目錄**:
   ```bash
   cp ~/.hermes/handoff/_template/architecture/architecture.template.md \
      ~/.hermes/handoff/<project-slug>/architecture.md
   # 重複每個需要的範本
   ```

2. **替換 `[...]` 佔位符**

3. **確認每份文件最後一節「1 小時上手 checklist」都標好** — 這是 system-architect 對 engineering-lead 的介面保證

4. **完成後寫到 `~/.hermes/handoff/<project-slug>/`** 並通知 default orchestrator

## 完整方法論

見 `~/.hermes/profiles/system-architect/skills/system-architecture/SKILL.md`(6 步 SOP + S/M/L 規則 + v2 Orchestrator 觸發條件)

見 `~/.hermes/profiles/system-architect/skills/architect-web-worker-template/SKILL.md`(v2 模式拆 web-worker 平行研究技術棧/schema/API)

見 `~/.hermes/profiles/system-architect/persona.md`(代理定位 + 上下游契約 + 自我審查)
