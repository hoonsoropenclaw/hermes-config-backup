# 常駐 Subagent 技能建置規格書
**日期**：2026-05-31
**目標**：建立一個讓 subagent 品質穩定、具有長期記憶搜尋能力的 skill

---

## 一、標竿技能研究（ClawHub）

### 1.1 hamster-self-improving（最接近目標）

| 項目 | 內容 |
|------|------|
| **來源** | ClaWHub - theo-jobs/hamster-self-improving |
| **核心機制** | Self-reflection + Self-criticism + Self-learning + Self-organizing memory |
| **目錄結構** | `~/self-improving/` HOT/WARM/COLD 三層架構 |

```
~/self-improving/
├── memory.md       # HOT: ≤100 lines，永遠載入
├── index.md       # 主題索引
├── projects/      # WARM: 每個專案的學習
├── domains/       # WARM: 領域知識（code, writing, comms）
├── archive/       # COLD: 衰退模式
└── corrections.md # 最後 50 筆修正日誌
```

**關鍵機制**：
- **自動推播**：同一模式出現 3 次 → 推播到 HOT
- **自動貶降**：90 天未用 → 歸檔到 COLD
- **命名空間隔離**：project > domain > global
- **衝突解決**：最具體的贏（project > domain > global）

### 1.2 pskoett/self-improving-agent

| 項目 | 內容 |
|------|------|
| **核心機制** | 捕捉 learn/修正/錯誤/功能請求 |
| **目錄結構** | `.learnings/LEARNINGS.md`, `ERRORS.md`, `FEATURE_REQUESTS.md` |
| **升級機制** | 廣泛適用的學習 → 推播到 `CLAUDE.md`, `AGENTS.md` |

**日誌格式**（結構化）：
```
## [LRN-YYYYMMDD-XXX] category
**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Area**: frontend | backend | infra | tests | docs | config
### Summary
### Details
### Suggested Action
```

---

## 二、影響 Subagent 能力的參數分析

### 2.1 delegate_task 參數

| 參數 | 影響程度 | 建議值 |
|------|----------|--------|
| `goal` | **極高** — subagent 所有輸出的核心 | 具體、封閉、可驗證 |
| `context` | **極高** — 品質與細節成正比 | 完整 spec + 檔案路徑 + 錯誤訊息 |
| `toolsets` | **中** — 能力 vs 專注取捨 | `['terminal', 'file']` 實作任務 |
| `role` | **中** — 安全 vs 彈性 | 預設 `leaf`，不用 `orchestrator` |
| `tasks`（批次） | **高** — 平行效率 | 不超過 `max_concurrent_children` |

### 2.2 config.yaml  delegation 參數

| 參數 | 預設值 | 建議值（N100） | 效果 |
|------|--------|---------------|------|
| `max_concurrent_children` | 8 | 5-6 | 穩定並行的安全值 |
| `child_timeout_seconds` | 1800 | 600-1800 | 任務複雜度決定 |
| `max_iterations` | 50 | 50-100 | 複雜任務提高 |
| `max_spawn_depth` | 1 | 1 | 保持扁平，安全 |
| `subagent_auto_approve` | false | false | 互動模式永遠 false |
| `inherit_mcp_toolsets` | true | true | 保持完整能力 |

### 2.4 技能（Skills）使用方式

**結論：subagent 可以自主呼叫 `skill_view` 載入技能。**

| 項目 | 狀態 |
|------|------|
| `skill_view` 被 block？ | ❌ **沒有** — 不在 `DELEGATE_BLOCKED_TOOLS` |
| subagent 可以用？ | ✅ **可以** — 透過 toolset 繼承 |
| 需要主體預先載入？ | ❌ **不需要** — subagent 自己會呼叫 |

**機制說明**：

```
skills_tools toolset 包含：
  - skill_view
  - skills_list
  - skill_manage

當主體的 toolsets 包含 skills_tools（或 enabled_toolsets=None）
subagent 會自動繼承這些工具
```

**Subagent 內部流程**：
```
subagent 收到任務
     ↓
自己判斷需要什麼技能
     ↓
自己呼叫 skill_view("relevant-skill")
     ↓
載入 SKILL.md 並按照指示執行
```

**與 context 注入的對比**：

| 方式 | 誰觸發 | 適用場景 |
|------|--------|----------|
| **Context 注入** | 主體在被派遣前 | 必須知道的固定資訊（檔案路徑、專案慣例） |
| **技能自主呼叫** | subagent 自己判斷 | 按需求選用的專業技能（RAG、程式開發、爬蟲等） |

### 2.5 整合無盡學習系統的關鍵修正

**原本的理解（被動模式）**：
```
主體搜尋記憶 → 注入 context → 派遣 subagent
```

**新的理解（主動模式）**：
```
主體派遣 subagent，告訴它：
  - 任務目標
  - 「你需要時可以呼叫 skill_view 載入記憶技能」

subagent 自己決定何時：
  1. 呼叫 skill_view("memory-search") 搜長期記憶
  2. 執行任務
  3. 透過 [TO_MEMORY] 回傳學習結果
```

**對 skill 設計的影響**：

skill 內需要明確說明「何時應該呼叫這個技能」，觸發條件要具體。

---

## 三、整合無盡學習系統的架構設計

### 3.1 目標
```
無盡學習系統完成後
     ↓
subagent 變得更聰明（品質提升）
     ↓
每個 subagent 都能搜尋相關領域的長期記憶
```

### 3.2 記憶讀取流程（新設計）

```
┌─────────────────────────────────────────────┐
│  主體（具有無盡學習系統的能力）              │
│                                             │
│  1. 接收任務                                │
│  2. 解析任務領域（domain classification）   │
│  3. 搜尋相關長期記憶（memory search）       │
│  4. 把記憶注入 context                      │
│  5. 派遣 subagent，附帶完整 context         │
│  6. subagent 執行                          │
│  7. 透過 [TO_MEMORY] 回收 subagent 的學習   │
└─────────────────────────────────────────────┘
```

### 3.3 三層記憶系統（參考 hamster-self-improving）

| 層級 | 位置 | 大小限制 | 載入方式 |
|------|------|----------|----------|
| **HOT** | `memory.md` | ≤100 lines | 永遠載入 |
| **WARM** | `projects/`, `domains/` | ≤200 lines/檔 | context match 時載入 |
| **COLD** | `archive/` | 無限 | 明確查詢時載入 |

### 3.4 Subagent 學習封閉問題

**目前的限制鏈**：
```
subagent 完成任務
     ↓
subagent 無法寫入 memory.md（blocked）
     ↓
只能透過 [TO_MEMORY] 區塊回傳
     ↓
主體讀到 [TO_MEMORY] 才寫入記憶
     ↓
依賴主體主動處理，subagent 無法自主學習
```

**解決方案 A（被動模式）**：主體在派遣前主動搜記憶並注入 context
**解決方案 B（主動模式）**：在 skill 裡實作 "memory sync" 步驟，主體主動讀取 subagent 回傳的 `[TO_MEMORY]`

---

## 四、實作方向與細節

### 4.1 Skill 名稱建議

```
persistent-subagent 或 resident-subagent
```

### 4.2 目錄結構

```
~/.hermes/skills/persistent-subagent/
├── SKILL.md                    # 主技能文件
├── references/
│   ├── memory-system.md        # 三層記憶系統實作
│   ├── context-templates.md    # 各類任務的 context 範本
│   └── agent-templates.md      # subagent prompt 範本
└── scripts/
    └── memory_sync.py          # 記憶同步腳本
```

### 4.3 核心功能

#### F1：自動記憶注入（派遣前）
```python
# 任務到來
# 1. 領域分類
domain = classify_task(task_description)

# 2. 搜尋相關記憶
memories = search_long_term_memory(domain, query=task_description)

# 3. 注入 context
context = f"""
[來自長期記憶的相關資訊]
{memories}

[任務描述]
{task_description}
"""
```

#### F2：學習回收（派遣後）
```python
# 讀取 subagent 回傳的 [TO_MEMORY] 區塊
memory_blocks = parse_to_memory_blocks(subagent_output)

# 寫入對應層級的記憶檔案
for block in memory_blocks:
    write_to_memory(block)
```

#### F3：穩定輸出模板
```python
SUBAGENT_OUTPUT_TEMPLATE = """
[TO_MEMORY]
category: {category}
domain: {domain}
content: {learned_content}
[/TO_MEMORY]

## 執行結果
{result}

## 品質自檢
- [ ] 符合 spec？
- [ ] 通過品質標準？
"""
```

### 4.4 Context 品質分級

| 等級 | 品質 | 內容量 |
|------|------|--------|
| **PEAK** | 最高 | 完整 spec + 檔案路徑 + 錯誤訊息 + 預期輸出格式 + 專案慣例 |
| **GOOD** | 良好 | 任務描述 + 相關檔案 + 約束條件 |
| **DEGRADING** | 普通 | 僅任務描述，無細節 |
| **POOR** | 差 | 模糊/最小化的 goal |

### 4.5 與無盡學習系統的整合點

```
無盡學習系統（MCL）
     │
     ├── 技能缺口分析 → 寫入 memory.md（HOT）
     ├── 模式識別 → 寫入 domains/
     ├── 專案學習 → 寫入 projects/
     │
     ▼
Hermes 主體派遣 subagent
     │
     ├── 讀取相關 memory（HOT/WARM/COLD）
     ├── 注入到 subagent context
     │
     ▼
subagent 執行（具有背景知識）
     │
     ├── 完成任務
     ├── [TO_MEMORY] 回傳新學習
     │
     ▼
主體同步到記憶系統
```

---

## 五、待確認/待解決的問題

1. **subagent 無法自主寫入記憶**：需確認是否可能修改 `DELEGATE_BLOCKED_TOOLS` 讓 subagent 有條件地寫入特定檔案
2. **領域分類的準確性**：需要建置領域分類的關鍵字列表
3. **記憶搜尋的精確度**：目前的 `session_search` 是 FTS5，未來可考慮語意向量搜尋
4. **無盡學習系統還未完成**：需等到 MCL 完成後才能完整整合

---

## 六、實作順序建議

### Phase 1：建立 Skill 框架
- [ ] 建立 `persistent-subagent` skill 目錄結構
- [ ] 實作 `memory_sync.py`（記憶讀寫）
- [ ] 撰寫 `context-templates.md`

### Phase 2：與無盡學習系統整合
- [ ] 確認 MCL 的輸出格式
- [ ] 實作領域分類
- [ ] 實作記憶注入流程

### Phase 3：品質穩定化
- [ ] 建立各類任務的 prompt 範本
- [ ] 實作 output format 驗證
- [ ] 建立錯誤恢復機制

---

**報告基於**：ClaWHub 標竿技能分析 + Hermes Agent 原始碼研究（config.yaml、run_agent.py、delegate_tool.py）