# Handoff 共享區完整慣例

## 為什麼需要 handoff 共享區

Hermes 內建每個 profile 有自己的 `memories/` 目錄（記憶庫隔離），但**多代理協作需要共享工作介面**：
- 市場策略代理做完的報告，產品規劃代理要接手
- 產品規劃代理做完的 PRD，工程代理要接手
- 每棒之間需要結構化交付，不能只靠「下一個 session 自己去挖記憶」

handoff 目錄 = **結構化交付物 queue**，比 hermes memory 更適合這個用途。

## 目錄慣例

```
~/.hermes/handoff/
├── README.md                              # 給人看的慣例說明
└── <project-slug>/                        # kebab-case 專案代號
    ├── market-research.md                 # 市場策略代理的交付物
    ├── clarifications.md                  # 反問與回覆（可選）
    └── prd.md                             # 產品規劃代理的交付物
```

`<project-slug>` 慣例：
- 全部小寫、kebab-case：`freelancer-tax-tool`、`ai-tutor-app`、`hr-automation`
- 不用底線、空白、中文
- 30 字內

## 為什麼不用 hermes memory 內建 handoff

1. **profile 記憶庫隔離**：各 profile 有自己的 `memories/`，跨 profile 看不到
2. **handoff 是結構化文件**：該用檔案系統存，不該塞進對話歷史
3. **可被版本控制**：未來要 `git init ~/.hermes/handoff/` 追蹤交付歷史
4. **人也能直接 cat**：debug 時不用開 hermes session

## Handoff 流程範本

### 1. 市場策略代理完成後

```bash
mkdir -p ~/.hermes/handoff/<project-slug>
cp market-research-<project-slug>.md ~/.hermes/handoff/<project-slug>/market-research.md
hermes -p product-planner chat -q "@~/.hermes/handoff/<project-slug>/market-research.md 請根據這份市場策略報告，產出對應的 PRD。重點放在：MVP 範圍、三大 Persona 的 User Story、風險對應的決策、成功指標。"
```

### 2. 產品規劃代理接手後

- 讀 `~/.hermes/handoff/<project-slug>/market-research.md`
- 反問 5 個釐清問題（寫到 `clarifications.md`）→ 觸發市場策略代理回覆
- 拆解 MVP 範圍（MoSCoW）
- 寫入 `prd.md`

### 3. 整個專案結束後

可選：把整個 `<project-slug>/` 目錄 tar 起來放 archive，避免 handoff 區無限膨脹。

## README 範本（給 `~/.hermes/handoff/README.md`）

```markdown
# Hermes 代理 Handoff 共享區

這個目錄是市場策略代理（market-strategist）↔ 產品規劃代理（product-planner）之間的交付介面。

## 目錄慣例

~/.hermes/handoff/
└── <project-slug>/                # kebab-case 專案代號
    ├── market-research.md         # 市場策略代理的交付物
    ├── clarifications.md          # 產品規劃代理反問、市場策略代理回覆（可選）
    └── prd.md                     # 產品規劃代理的交付物
```

## 注意事項

- handoff 區是**共享**的，不歸任何 profile 所有
- 完成的專案可 tar 起來移到 archive
- 寫入前先確認 `<project-slug>` 沒撞名（`ls ~/.hermes/handoff/` 看一下）
