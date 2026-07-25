# Hermes 代理 Handoff 共享區

這個目錄是 **handoff chain 5 個代理** 之間的交付介面。

```
consumer-researcher  →  product-planner  →  system-architect  →  engineering-lead  →  test-engineer
   (chain 第 1 棒)        (第 2 棒)            (第 3 棒)            (第 4 棒)            (第 5 棒鏈尾)
   消費者研究              PRD 撰寫              技術架構            程式實作             品質驗收
```

> **2026-06-11 更新**:test-engineer 加入、handoff chain 終於閉環。PRD / Sprint / QA 範本補完。

## 目錄慣例（5 階段完整版）

```
~/.hermes/handoff/
└── <project-slug>/                          # kebab-case 專案代號
    ├── consumer-needs-research.md           # consumer-researcher 交付（必）
    ├── sources.json                         # 引用 URL 索引（可選）
    ├── clarifications.md                    # 反問 5 個釐清問題（可選）
    ├── prd.md                               # product-planner 交付（必）
    ├── architecture.md / database-schema.md  # system-architect 交付（必 3 份）
    ├── api-spec.md / architecture-decisions.md  # M+ 必加
    ├── sprint-<N>-report.md                 # engineering-lead 交付（必, 每 sprint 一份）
    ├── bug-report-<N>.docx                  # test-engineer 交付（必, FAIL 時）
    ├── sprint-<N>-qa-signoff.md             # test-engineer 交付（必, 每 sprint 一份）
    └── qa-artifacts/                         # 測試產出（截圖、log）
        └── sprint-<N>/
            ├── e2e-screenshots/
            ├── performance-baseline/
            └── bug-evidence/
```

`<project-slug>` 用 kebab-case,例:`freelancer-tax-tool`、`ai-tutor-app`、`school-multidept-site`。

## 5 階段 handoff 流程

### 1. consumer-researcher → product-planner
- 寫 `consumer-needs-research.md`（結構見範本）
- 可選 `sources.json`（便於下游追蹤 URL）
- 主 orchestrator 收到後觸發 product-planner

### 2. product-planner → system-architect
- 寫 `prd.md`（結構見範本）
- 可選 `clarifications.md`（反問 + 回覆）
- 主 orchestrator 收到後觸發 system-architect

### 3. system-architect → engineering-lead
- 寫 3 份（`architecture.md` / `database-schema.md` / `api-spec.md`），M+ 加 `architecture-decisions.md`
- 主 orchestrator 收到後觸發 engineering-lead

### 4. engineering-lead → test-engineer
- 寫 `sprint-<N>-report.md`（每 sprint 一份）
- 主 orchestrator 收到後觸發 test-engineer

### 5. test-engineer → 主 session（鏈尾）
- 跑單元 + 整合 + E2E + 性能測試
- 寫 `sprint-<N>-qa-signoff.md`（PASS / CONDITIONAL PASS / FAIL 決策）
- 失敗時附 `bug-report-<N>.docx` + `qa-artifacts/sprint-<N>/`
- **不再 handoff 給下一棒** — 主 session 看到決策就決定下個 sprint 怎麼走

## 為什麼不用 hermes memory 內建 handoff

- 各 profile **記憶庫隔離**（各 profile 有自己的 memories/ 目錄）
- handoff 是**結構化交付物**，不該塞進自由對話
- 用檔案系統當 queue：人也能直接 `cat` 看到內容、版本控制能用 git 追蹤
- default orchestrator 是唯一的中繼者（profile 間不互通）

## 怎麼看現有 handoff

```bash
ls -la ~/.hermes/handoff/                                 # 看所有進行中/已完成的專案
ls -la ~/.hermes/handoff/<project-slug>/                   # 看單一專案的所有階段交付物
cat ~/.hermes/handoff/<project-slug>/sprint-1-report.md   # 看 sprint 1 報告
cat ~/.hermes/handoff/<project-slug>/sprint-1-qa-signoff.md  # 看 sprint 1 QA 決策
```

## 範本位置

| 範本檔 | 對應交付物 | 適用複雜度 | 對應代理 |
|--------|-----------|-----------|---------|
| `_template/consumer-needs-research.template.md` | `consumer-needs-research.md` | S/M/L | consumer-researcher |
| `_template/prd.template.md` | `prd.md` | S/M/L | product-planner |
| `_template/architecture/architecture.template.md` | `architecture.md` | S/M/L | system-architect |
| `_template/architecture/database-schema.template.md` | `database-schema.md` | S/M/L | system-architect |
| `_template/architecture/api-spec.template.md` | `api-spec.md` | S/M/L | system-architect |
| `_template/architecture/architecture-decisions.template.md` | `architecture-decisions.md` | M/L only | system-architect |
| `_template/sprint-report.template.md` | `sprint-<N>-report.md` | - | engineering-lead |
| `_template/qa-signoff.template.md` | `sprint-<N>-qa-signoff.md` | - | test-engineer |

完整報告範本見各 `_template/*.template.md`。

## 歷史

- **2026-06-11**：test-engineer 加入、PRD/Sprint/QA 範本補完、handoff chain 5 階段全通
- **2026-06-10**：從「市場策略代理 (market-strategist)」重塑為「消費者需求代理 (consumer-researcher)」
- **2026-06-09**：首次建立 handoff 目錄
