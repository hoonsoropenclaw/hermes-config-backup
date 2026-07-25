---
name: hermes-resident-agent
description: 在 Hermes Agent 內建「常駐代理」架構的 SOP。當使用者要求建立長期運作的專屬代理（例如「建一個常駐策略代理」「幫我做一個監控代理」「這個專案要有專人負責」），載入此技能以產出完整的常駐代理設定。
version: 1.0.0
author: hoonsor
tags: [hermes, agent, profile, tmux, resident, persistent, architecture]
---

# Hermes Resident Agent — 常駐代理架構 SOP

## 核心概念

在 Hermes Agent 內建「常駐代理」= 跨 session 持續運作、擁有獨立 persona、獨立技能、獨立記憶庫的代理。
**正解**：`hermes profile create <name> --clone` + 寫 persona.md + 專屬 skill + tmux 持久化對話。
**誤區**（2026-06-09 之前曾用，已廢棄）：`~/.hermes/agents/*.yaml` 身份檔 + Python 後台行程的 `persistent-subagent` skill。

### 與 `delegate_task` 派遣 subagent 的差異

這是**最容易混淆**的點，必須分清：

| 概念 | 用途 | 工具 | 生命週期 |
|------|------|------|----------|
| **常駐代理** | 跨 session 持續運作的專屬代理 | `hermes profile + tmux` | 永久（或直到 profile 刪除） |
| **派遣 subagent** | 一次性背景任務 | `delegate_task` 工具 | 單次任務結束即銷毀 |

- **If** 使用者說「建一個常駐 X 代理」「幫我做一個長期監控代理」**Then** 走本 skill 的 profile + tmux 路線
- **If** 使用者說「派遣一個 subagent 去看 X」「派個視覺代理評分」**Then** 走 `delegate_task` 工具（**不要**當成常駐代理處理）

## 觸發情境

載入本 skill 的明確觸發：
- 「建一個常駐策略代理」「幫我做專案經理代理」「監控代理」
- 「這個領域要有專人負責」「給 X 領域一個常駐身份」
- 「profile + tmux 怎麼建」「常駐代理的架構」
- 使用者要擴展代理團隊（多個專責代理分工）

## 標準建置流程（7 步）

### Step 1 — 釐清代理的職責邊界
- 這個代理要做什麼、不做什麼？
- 輸入觸發：什麼情況下被啟用？
- 輸出形式：交付什麼檔案 / 回什麼訊息？
- 跟其他代理的關係：是獨立運作、還是接收 handoff？

### Step 2 — 確認 profile 名稱慣例
- kebab-case：`market-strategist`、`product-planner`、`security-monitor`
- 不用底線（Hermes 內部會自動轉）
- 不用太長（≤ 30 字、未來要打 wrapper 指令）

### Step 3 — 建 profile（從 default clone）
```bash
hermes profile create <name> --clone \
  --description "<一句話說明這個代理適合什麼任務>"
```
這會自動：
- 從 default 複製 config.yaml、.env、SOUL.md
- 帶 197 個 default skills（若不要帶，加 `--no-skills`）
- 建 wrapper：`~/.local/bin/<name>`（PATH 已有，可直接打）
- 註冊到 `hermes profile list`

### Step 4 — 寫 persona.md（核心）
位置：`~/.hermes/profiles/<name>/persona.md`
內容必填：
- **核心信念**（3-5 條，這個代理的工作哲學）
- **擅長方法論**（這個代理會用的工具/框架）
- **標準工作流程**（拿到任務後依序做什麼）
- **交付物格式**（輸出檔案的 markdown 結構）
- **禁止事項**（明確切割邊界）
- **handoff 規則**（完成後交給誰、怎麼交）
- **語言與風格**（繁中/英文、條列/敘述）

### Step 5 — 裝專屬 skill（可選，但強烈建議）
位置：`~/.hermes/profiles/<name>/skills/<skill-name>/SKILL.md`
- 結構化這個代理的工作流程
- 必填：觸發情境、標準流程、自我審查清單
- 用 frontmatter 標明 name/description/triggers（讓代理自動載入）

### Step 6 — 設 handoff 共享區（多代理協作必做）
```bash
mkdir -p ~/.hermes/handoff
```
- 慣例：`~/.hermes/handoff/<project-slug>/{market-research.md, clarifications.md, prd.md}`
- 每個代理完成交付後寫到這裡，handoff 給下一棒

### Step 7 — tmux 持久化（可選，看需求）
- 如果代理需要長期掛著收訊息/監控：用 `tmux new -d -s <name> '<name> gateway start'`
- 如果只是「跨 session 保留 persona」就夠：不用 tmux，每次 `hermes -p <name> chat` 重啟即可

## 跨 profile 操作的 Hermes 軟防護

當從 `default` profile 操作其他 profile 的檔案時會被擋：
```
Cross-profile write blocked by soft guard: ... belongs to Hermes profile '<name>',
but the agent is running under profile 'default'. ...
```

**這是 defense-in-depth，不是阻擋**。明確知道要做什麼就繞：
- `write_file(..., cross_profile=True)`
- `patch(..., cross_profile=True)`

**If** 在建常駐代理的過程中碰到這個擋 **Then** 直接用 `cross_profile=True`，**不要** 懷疑「是不是不該動別的 profile」——本來就是這個任務的核心。

## 各 profile 的 .env 隔離策略

`--clone` 會複製 default 的 .env（含所有 API keys）到新 profile。

**預設行為**：所有 profile 共用同一份 API keys。

**If** 想讓某個 profile 走便宜的模型省錢 **Then** 編輯 `~/.hermes/profiles/<name>/.env`，只改 `MODEL` 那一行，**不要**動 API keys（會失效）。
**If** 想讓某個 profile 走不同的 provider **Then** 整份 .env 用專屬 keys（從各 provider 後台申請）。

## 驗證建置成功

```bash
hermes profile list                            # 看到新 profile
hermes -p <name> skills list                   # 看到專屬 skill
hermes -p <name> --help                        # wrapper 運作
cat ~/.hermes/profiles/<name>/persona.md       # persona 寫入成功
```

預期輸出：
- profile 狀態欄出現新名稱（gateway 顯示 stopped，待用）
- `skills list` 內有剛建的專屬 skill（status: enabled）
- persona.md 存在且內容正確

## 已知陷阱（pitfalls）

1. **不要用 `~/.hermes/agents/*.yaml` 身份檔方案** — 這是 2026-05-31 ~ 2026-06-08 的舊實驗，已在 2026-06-09 全清。**未來再看到「agents/ 目錄 + 身份 yaml」方案就是錯的**，應走本 skill 的 profile + tmux 路線。
2. **不要把 `delegate_task` 派遣跟常駐代理混為一談** — 派遣是單次任務、常駐是跨 session 持續。前者用 `delegate_task` 工具、後者用本 skill。
3. **`hermes profile create` 撞名 = 目錄已存在** — 可能是之前 mkdir 建的空殼。手動 `rm -rf` 整個空 profile 目錄再重建即可（**沒有任何 profile 內容就不算 profile**）。
4. **`--clone` 帶 197 個 skills = 197 個通用 skill 全部繼承** — 如果只想要空 profile，用 `--no-skills` 旗標。
5. **handoff 目錄沒有 owner** — `~/.hermes/handoff/` 不屬於任何 profile，預設就 shared（這是設計，handoff 是跨 profile 介面）。
6. **跨 profile 寫檔要明確 bypass** — 見「跨 profile 操作的 Hermes 軟防護」段。

## 詳見（support files）
- `references/handoff-conventions.md` — handoff 共享區完整慣例、目錄結構、為什麼不用 hermes memory
- `references/profile-vs-subagent-decision-tree.md` — 「該建常駐 profile 還是單次派遣 subagent」決策樹
- `references/persona-template.md` — persona.md 完整範本（含各 section 範例文字）
- `references/skill-template.md` — 專屬 skill 的 SKILL.md 範本（含 frontmatter 範例）
- `references/chain-automation.md` — 多代理 chain 自動化 wrapper script 模板與 SOP（2026-06-10 新增）

## 歷史

- 2026-05-31：曾有 `persistent-subagent` skill + `~/.hermes/agents/*.yaml` 身份檔方案（已廢棄，2026-06-09 全清）
- 2026-06-09：建立 `market-strategist` 與 `product-planner` 兩個常駐代理（沿用本 skill 的 7 步流程），從實作中沉澱出本 skill
- 2026-06-09：MEMORY.md 加入 L3 教訓「常駐子代理 = profile + tmux」防未來回頭用舊方案
