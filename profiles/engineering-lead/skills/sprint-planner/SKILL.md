---
name: sprint-planner
description: 從 system-architect 架構 handoff 拆出 sprint ticket,每個 ticket 標 S/M/L 複雜度 + feature/fix/refactor/infra 類型 + Given/When/Then 驗收。載入後自動套用雙維度規劃。
version: 1.0.0
author: hoonsor
tags: [sprint, planning, ticket, tdd, given-when-then, complexity, delivery-type]
---

# Sprint Planner Skill

從 system-architect 架構文件拆出可執行的 sprint ticket,每個 ticket 含:
- **Given/When/Then** 驗收條件(測試代理接手時直接跑)
- **複雜度 S/M/L** 評估(S=1 天 / M=2-3 天 / L=1 週)
- **類型 feature/fix/refactor/infra** 標記
- **依賴關係** 圖(Sequential vs Parallelizable)

## 觸發情境

- 收到 `arch-<slug>.md` handoff 從 system-architect
- 使用者明確說「開個 sprint」「拆 ticket」「規劃下個 sprint」
- sprint 結束後準備下個 sprint 的 ticket 拆解

## 標準流程(6 步)

### 1. 讀 handoff + 確認 scope

- 讀 `~/.hermes/handoff/<project-slug>/arch-<slug>.md`
- 讀可選的 `prd-<slug>.md` 跟 `consumer-needs-research.md` 補充
- 列出架構文件中的「待實作項目」(API endpoints、資料表、UI 元件、infra 資源)
- 確認 sprint 範圍(全做、還是只做某些模組?)

### 2. 反問釐清(1-2 題,使用 clarify 工具)

**反問範例**:
- 「API endpoint `/api/users` 預期要支援批量上傳嗎?」
- 「infra 的 PostgreSQL 是用現有的還是要新開?」
- 「UI 風格跟 system-architect 提的一致,還是有額外客製?」

不超過 2 題——避免 user 中途放棄。

### 3. 拆 ticket

每個待實作項目拆成 1+ 個 ticket。格式:

```markdown
## Ticket S-001: [簡短標題]

**類型**: feature
**複雜度**: S (1 天)
**依賴**: 無
**Parallelizable**: 是

### Given / When / Then

**Given** [前提條件]
- 系統已部署 PostgreSQL 15+
- 使用者已登入且 session 有效

**When** [動作]
- 使用者 POST /api/users 帶 email + password

**Then** [預期結果]
- 回 201 + 新 user id
- 資料庫 users 表新增一筆
- password 用 bcrypt 雜湊(不可明文儲存)

**And** [其他預期]
- 5xx 錯誤時回 JSON 結構
- p95 latency < 200ms

### 實作備註

- 用 `bcrypt.hashpw(password, 12)` 預設 cost 12
- 不可用 MD5/SHA1(資安理由見 security-review skill)
- migration 檔在 `migrations/2026XXXX_add_users_table.sql`
```

### 4. 標記依賴跟平行性

每個 ticket 標:
- **Sequential** vs **Parallelizable**
- **依賴**:列出此 ticket 需要哪些其他 ticket 先完成
- **Critical path**:第一個 sequential ticket ID

範例:

```markdown
| Ticket | 類型 | 複雜度 | 依賴       | 平行性           |
|--------|------|--------|-----------|------------------|
| S-001  | feature | S    | 無         | Parallelizable   |
| S-002  | feature | M    | S-001     | Sequential(待 S-001) |
| S-003  | feature | M    | S-001     | Parallelizable with S-002 |
| M-001  | infra   | M    | S-001, S-002 | Sequential(待 S-002) |
```

### 5. 決定 sprint 範圍

從所有 ticket 中挑出 sprint 內能完成的(預設 2 週 = 10 個工作天)。

容量估算(per 一個工程師):
- S ticket:每個 0.5 天(0.5 + 0.5 review)
- M ticket:每個 2 天(1.5 + 0.5 review)
- L ticket:每個 5 天(4 + 1 review)

Sprint 容量範例(2 週 = 10 天):
- 5 個 S + 2 個 M + 1 個 L(5×0.5 + 2×2 + 1×5 = 11.5 → 略超,改 4 個 S)
- 4 個 S + 2 個 M + 1 個 L(4×0.5 + 2×2 + 1×5 = 11 → 接近 10,可接受)

**輸出**: `~/.hermes/handoff/<project-slug>/sprint-<N>-plan.md`

### 6. 交接給 tdd-implementer skill

sprint plan 寫完後,呼叫 tdd-implementer skill 開始實作每個 ticket。

---

## 必用工具

- `read_file`:讀 handoff
- `write_file`:寫 sprint plan
- `clarify`:反問使用者
- `delegate_task`:開 sub-agent 平行實作多個 ticket

## 品質檢核(自我審查清單)

產出前自問:
1. 每個 ticket 都有 Given/When/Then? ✅ 必填
2. 複雜度 S/M/L 評估合理嗎?(L 超過 1 週就要再拆)
3. 依賴關係清楚嗎?(避免循環依賴)
4. 平行性標記了嗎?(parallelizable 的用 sub-agent 同時跑)
5. sprint 容量不超載嗎?(接近 10 天就好,留 1-2 天 buffer)

任一為否,回去補。

## 跟其他 skill 的關係

| Skill | 互動 |
|-------|------|
| `tdd-implementer` | 下游,sprint plan 完成後啟動 TDD 實作 |
| `system-architecture` | 上游,system-architect 用此 skill 寫架構 |
| `code-review` | 平行,sprint plan 也要經過 Spec Review |
| `anthropic-sprint-planning` | Anthropic 通用 sprint skill,可參考但本 skill 強調 Given/When/Then |

## 詳見

- `references/ticket-template.md`(完整 ticket 範本)
- `references/complexity-estimation-guide.md`(S/M/L 評估準則)
