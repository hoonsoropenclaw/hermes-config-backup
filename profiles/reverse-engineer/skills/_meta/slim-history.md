# Reverse Engineer Profile — Skill 精瘦紀錄

> 2026-06-11 初次建立。

## 建立歷程

| 階段 | 時間 | 動作 | skill 數變化 |
|------|------|------|------------|
| 建立 | 2026-06-11 | `hermes profile create reverse-engineer --clone`(從 default 帶 ~194 個) | 0 → ~194 |
| 修補 trial-and-error SOP | 2026-06-11 | 從 consumer-researcher cp 進完整 references/sops/ 結構 | 不變 |
| 新增自寫 skill | 2026-06-11 | 寫 reverse-engineer-methodology SKILL.md(8 視角核心方法論) | 194 → 195 |
| Opt-out bundled | 2026-06-11 | `hermes -p reverse-engineer skills opt-out --remove --yes`(自動刪 bundled 65 個) | 195 → 193 |
| 精瘦 opt-out | 2026-06-11 | 依白名單刪除 160 個跟反向工程無關的 skill | 193 → 33 |

## 精瘦決策(為什麼保留這 33 個)

### Hermes 基礎設施(5 個,必留)
- `general-workflow` / `user-collaboration-style` / `trial-and-error` / `workspace-folder-layout` / `anti-panic-protocol`
- 理由:任何代理都需要赫米斯基礎設施

### 反 slop / 反 pattern(3 個,必留)
- `anti-pattern-czar` / `anti-slop-design` / `antislop`
- 理由:避免 reverse-arch 報告 / 架構圖說明變 AI-slop

### defensive 程式(4 個,必留)
- `bash-defensive-patterns` / `python-anti-patterns` / `python-observability` / `python-resilience`
- 理由:trace 與分析腳本的 defensive 規範

### 抓取 / 視覺(5 個)
- `web_search` / `agent-browser` / `browser` / `vision-analysis` / `scrapling`
- 理由:分析網站 / 截圖 / 錄影時的工具來源

### 程式碼閱讀 / 結構分析(2 個)
- `code` / `software-development`
- 理由:理解原始碼、識別 anti-pattern、給重構建議的核心方法論
- (註:白名單原列 3 個,`code-reviewer` 在 engineering-lead 不在 default,故 33 個為實際命中數)

### 架構圖 / 文件輸出(8 個,必留)
- `diagram-generator` / `beautiful-mermaid` / `minimax-docx` / `minimax-pdf` / `minimax-xlsx` / `docx` / `pdf` / `xlsx`
- 理由:架構圖要能輸出 PDF / DOCX / XLSX 給工程師

### 規劃 / 工具輔助(4 個)
- `hermes-tier-router` / `hermes-architecture` / `new-conversation` / `skill-docker`
- 理由:複雜拆解時的方法論支援 + session 結束掃雷
- (註:`systematic-debugging` 在 engineering-lead 不在 default,故未列入)

### 反向工程核心(2 個,必備)
- `reverse-engineering` (clawic, TRACE 協議 + evidence ladder + interface map):通用方法論祖先
- `reverse-engineer-methodology` (本代理自寫,架構圖導向):8 視角展開 SOP + 證據等級標記 + Mermaid 規範

## 對標其他常駐代理的 skill 數量

| Profile | skill 數 | 角色 |
|---------|---------|------|
| consumer-researcher | 56 | 消費者需求研究 |
| product-planner | 64 | PRD 撰寫 |
| engineering-lead | 85 | 程式實作 + sprint |
| system-architect | 102 | 技術架構 |
| test-engineer | 42 | 整合 / E2E 測試 |
| **reverse-engineer** | **33** | **反向工程(本次建立,2026-06-11)** |

reverse-engineer 33 個是所有常駐代理中最少的,**符合預期**:
- 角色單一(只看 / 拆 / 畫 / 寫 SOP,不寫 code)
- 不需要 sprint / spec / product 規劃工具鏈
- 核心 8 視角流程靠自寫 skill + clawic reverse-engineering 即可

## 磁碟大小驗證

- 精瘦前:預估 ~344 MB(跟其他 194 個 skill 的 profile 同基準)
- 精瘦後:**126 MB**
- 節省:**~218 MB**(~63%)

## 驗證 4 件套(精瘦 SOP §3)

- [x] 專屬 skill 還在:`reverse-engineer-methodology` + `reverse-engineering`
- [x] 4 個通用必留:general-workflow / trial-and-error / user-collaboration-style / workspace-folder-layout
- [x] 主代理(default)依然完整:196 skill(未動)
- [x] opt-out marker 存在:`.no-bundled-skills` 在

## 怎麼 undo(後悔的話)

```bash
# 1. 刪 opt-out marker
rm ~/.hermes/profiles/reverse-engineer/.no-bundled-skills

# 2. 跑一次 hermes update 觸發 seeding
hermes -p reverse-engineer update

# 3. 但已刪的 skill 不會自動回來(除非原本是 bundled),要手動:
hermes -p reverse-engineer skills install <skill-name>

# 或從 default 端整個 cp:
cp -r ~/.hermes/skills/<skill> ~/.hermes/profiles/reverse-engineer/skills/
```

## 後續維護

- reverse-engineer 跟其他 5 個常駐代理同 model(`MiniMax-M3`)、同 wrapper 格式(`exec hermes -p <name> "$@"`)
- 跟既有 handoff chain **解耦**,可獨立接收輸入、可同時餵給多個下游
- 8 視角的「視角 1-5 結構」可借鏡 system-architect(同樣是「從外部推導內部結構」)
- 8 視角的「視角 6-8 橫切」是 reverse-engineer 獨有的安全/效能/錯誤視角,system-architect 沒有
