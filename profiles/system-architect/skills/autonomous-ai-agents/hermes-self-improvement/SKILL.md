---
name: hermes-self-improvement
description: "赫米斯的自我改進機制：技能更新、記憶管理、SOP 服從性與外部驗收循環的架構說明。"
version: 1.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [self-improvement, skills, memory, SOP, compliance]
    triggers: [skill-update, memory-write, self-reflection]
---

# Hermes 自我改進機制

## 核心問題

赫米斯的「越用越聰明」是有限度的。在沒有外部驗收機制的情況下，所謂的「學習」只是裝飾。

### 為什麼「越用越聰明」可能只是假象

1. **SOP 服從性不是 100%**：每次推理時，所有上下文原料（soul.md、skills、MEMORY、當前任務）都會被動態加權，不是剛性約束
2. **沒有客觀驗證**：LLM 無法自己驗證「這次更新是否真的帶來更好的結果」
3. **自我感覺良好可能是錯覺**：沒有外部信號告訴系統「你上次學錯了」

---

## 三層決策架構

```
輸入原料
  ├── soul.md（赫米斯身份定義）→ 影響風格和方向
  ├── MEMORY.md（長期記憶）→ 影響判斷偏好
  ├── USER.md（用戶檔案）→ 影響對特定用戶的適配
  ├── skills/*/SKILL.md（80+ 技能文件）→ 定義任務處理方式
  └── 當前對話上下文 → 即時情境

LLM 推理（動態加權，不是剛性）
  ↓
輸出（70-80% 符合 SOP，20-30% 可能偏移）
```

---

## 技能系統（可變部分）

### 技能更新流程
```
發現更好的做法 → 用 skill_manage(action='patch') 更新對應 SKILL.md
                                     ↓
                           下次遇到同類任務自動加載新版本
```

### 記憶更新流程
```
值得記住的經驗 → 用 memory(action='add') 寫入 ~/.hermes/memories/*.md
                                    ↓
                          下次對話開始時自動注入 context
```

### 技能與記憶的區別
- **技能（Skill）**：定義「這類任務怎麼做」——流程、步聚、坑洞
- **記憶（Memory）**：記住「誰是這個用戶、系統環境、偏好設定」——事實性知識

### 記憶管理三層試誤原則（2026-06-05 session 確立）

**使用者明確偏好的「對話紀錄保留原則」**：

- **預設不寫**：完成任務、踩坑修復、做完部署後，赫米斯**不主動 add 進記憶**
- **使用者明確說要存才存**：「把這個記起來」「這個以後會用到」「寫進記憶」才動手
- 例外情況（赫米斯發現未來會重複用到、可主動建議一次但仍須使用者確認）：
  - 穩定偏好（INTJ 性格、想看結構化輸出、要繁體中文等）
  - 環境事實（gpg 版本、headless 無 keystore daemon、IP/主機名等）
  - 新建立的長期檔案/工具路徑
- **7 天內會過期的東西不入記憶**
- 短期 session 細節、需要回憶時用 `session_search` 撈（會跨所有過去 session 搜，沒真的消失）

**試誤經驗的三層處理**（關鍵！原本規則太寬，會把 L3 教訓掃掉，2026-06-05 修正）：

| 層級 | 內容 | 處理 |
|---|---|---|
| **L1 具體操作** | 跑了什麼指令、時間戳、輸出 | 自動存 state.db、**從不進記憶** |
| **L2 具體 bug 解法** | 一步步怎麼修好 | state.db 可撈、**記憶只留一句話指向**（「這個 bug 之前解過，session_search 找『xxx』」） |
| **L3 抽象教訓/規律** | 通用規律（例：「gpg 預設產出 mode 0644 必 chmod 0600」） | **必進記憶**——這才是「越用越聰明」的關鍵 |

**MEMORY.md 自我清理觸發**：
- 閾值：**超過 25 KB** 時赫米斯主動建議掃一次
- 赫米斯**不直接動手**清理，先列「建議刪除的條目 + 為什麼過時」給使用者看，確認後才刪

**MEMORY.md 清理判斷標準**：

| 留 | 刪 |
|---|---|
| 穩定偏好 | 任務進度 |
| 使用者習慣 | 具體 commit / PR / issue 編號 |
| 重要工作流程指引 | 單次 session 結果 |
| 選擇/決策的「為什麼」 | 可由 session_search 撈回的細節 |
| 抽象教訓/規律 (L3) | token 字串、機密內容 |
| 環境事實 | 短期操作 log |
| 新建立的長期檔案路徑 | 過時的技術細節 |

**簡記原則**：能 `session_search` 撈回的事 = 留個概念/路徑就夠；只有「使用者為什麼這樣決定」「跨 session 都該這樣做」「這個環境就是這樣」「未來會重複踩的雷是這個」這類才進長期記憶。

**/new 行為**：`/new` 不會自動摘要、不會自動寫進長期記憶。如果使用者想存，就「在 /new 之前先說一句話」。**沒有自動摘要機制、不會偷偷加東西。**

---

## SOP 服從性問題

### 現實：不是 100%
`soul.md`、`MEMORY.md`、skills 對 LLM 輸出的影響是 soft guidance，不是 hard constraint。

### 影響加權的因素
- 任務的緊急性質（緊急任務更容易跳過嚴格流程）
- 對話上下文的新異性（偏離 SOP 的問題可能引發偏離的回覆）
- 模型自身的推理偏好（有些模型傾向於展現「聰明」而不是服從）

### 提升服從性的已知方法
1. **詳細的觸發條件**：當某個 SOP 被觸發的條件寫得越詳細，遵守率越高
2. **Tool Use Enforcement**：`config.yaml` 中的 `tool_use_enforcement: true`（已於 2026-05-30 設定）可約束所有模型「不要只描述要做什么，要實際呼叫工具」
3. **外部驗收循環**（Layer 2.5 / Layer 3 — 尚未實作）：任務完成後對照 SOP 檢查，發現偏移要求重做

**Research-backed 機制對照表**：

| 機制 | 驗證層級 | 狀態 |
|------|----------|------|
| SOP-Agent（arxiv 2501.09316）| Layer 2.5 | 原理已理解，待實作 `automated-sop-validation` skill |
| CRITIC（ICLR 2024）| Layer 3 | 需外部工具驗證，MiniMax 目前無專屬工具介面 |
| Reflexion | Layer 3 | 需跨 session 持久 reflection memory，已部分融入赫米斯架構 |
| Agentic Reward Modeling | Layer 3 | 需可驗證正確性信號，目前依賴用戶反饋 |
| Agent Behavioral Contracts | Layer 3 | 需 runtime enforcement，待工具支援 |

**Layer 2.5 實作缺口**：目前赫米斯缺乏「sub-agent 交付後、實際發送給用戶前」的自動化對照 SOP 檢查。這是從 Layer 1/2 邁向 Layer 3 的過渡步驟。實作方式：
- cron job 完成後觸發 SOP 比對腳本
- 關鍵字/結構比對檢查產出是否滿足 SOP 定義的交付標準
- 若不符，記錄偏差並可選觸發重新執行

### 當前已啟用的 Enforcement 狀態（2026-05-30 更新）

| 設定 | 值 | 效果 |
|------|---|------|
| `agent.tool_use_enforcement` | `true` | 所有模型強制收到「實際執行，不要只描述」引導 |
| `agent.task_completion_guidance` | `true` | 所有模型強制收到「任務完成後不要停在計劃，要交付實際成果」引導 |
| `delegation.max_concurrent_children` | `8` | 同時最多 8 個 sub-agent（N100 硬體，建議值 5-6） |
| `delegation.child_timeout_seconds` | `600` | 每個 sub-agent 10 分鐘超時 |

**與 MiniMax 的關係**：
- 原本 `"auto"` 時，MiniMax 不會收到 enforcement（不在名單列表里）
- 改為 `true` 後，MiniMax 現在會收到同樣的約束引導

---

### 坑洞預警（2026-06-03 新增）

**⚠️ 路徑混淆陷阱（重大教訓）**
- `hermes-status-site` ≠ `hermes-portal`（評價網站）≠ `~/.openclaw/workspace/status_dashboard/`（OpenClaw 舊站）
- 混淆後果：部署到錯誤的倉庫、刪除錯誤的檔案、錯誤的 Vercel project ID
- **正確對照表**：
  ```
  hermes-status-site（自身狀態網站）
    - 本機：/home/hoonsoropenclaw/hermes-status-site/
    - GitHub：hoonsoropenclaw/raphael-status-site
    - Vercel：prj_6FcNdvnHwPoXdkjr5csknUVJ5bUX
    - 用途：排程同步、技能統計、自身狀態展示
  
  hermes-portal（評價網站）
    - 本機：/home/hoonsoropenclaw/hermes-portal/
    - GitHub：hoonsoropenclaw/hermes-portal（部署在 Vercel）
    - Vercel：prj_uUsJw3x4NZCofkO1KKFT7viCNvLD
    - 用途：接收用戶上傳的成品（網站/程式/圖片/簡報），收集評價
    - 包含：api/works.js、api/evaluations/sync.js 等 API
    - 環境變數：AGENT_API_KEY（格式：hms_hermes...y_2026，33字，位於 .env.local）
  
  ~/.openclaw/workspace/status_dashboard/
    - OpenClaw 舊狀態頁，與赫米斯無關，不要碰
  ```
- **預防原則**：每次執行「部署/同步/更新」前，必須先確認目標是哪個專案
- **驗證方法**：`hermes cron list` 的結果同步到 `raphael-status-site`；評價同步到 `hermes-portal`

**⚠️ 環境變數同步陷阱**
- 本機 `.env.local` 中的 `AGENT_API_KEY` 和 Vercel 部署時設定的環境變數**可能不一致**
- Vercel Dashboard 的環境變數需要手動同步，不會自動繼承 `.env.local`
- 401 Unauthorized 時，先懷疑 Vercel 端的環境變數是否已設定

### 支援檔案
- **`references/sop-enforcement.md`** — SOP 強制執行架構詳解（三層服從模型、驗收機制設計原則、實用檢查清單）
- **`references/automated-sop-validation.md`** — Layer 2.5 實作路徑（sub-agent 交付後自動對照 SOP 檢查的架構設計）
- **`references/vercel-portal-401-troubleshooting.md`** — hermes-portal 401 排查實錄（持續更新中）

## 當前真實能力邊界

| 能力 | 現實狀態 |
|------|----------|
| 更新技能文件 | ✅ 可做到，且馬上生效 |
| 寫入長期記憶 | ✅ 可做到，但需要自己主動 |
| 自動驗證更新是否有效 | ❌ 做不到 |
| 保證 SOP 100% 遵守 | ❌ 做不到 |
| 自動發現自己的錯誤 | ⚠️ 需要外部觸發（用戶反饋或審查） |

---

## 後設認知職責（給 metacognitive-learner 的補充）

每次後設認知學習循環除了「學新東西」，還必須包含：

1. **SOP 偏移審查**：檢查最近任務中是否有違背已記錄 SOP 的情況
2. **外部驗證**：新學到的結論嘗試找外部資料驗證，不要只靠 LLM 推理
3. **偏移記錄**：發現偏移時明確記錄「錯誤是什麼，正確應該是什麼」

---

## 與 OpenClaw 的差異

| 維度 | Hermes | OpenClaw |
|------|--------|----------|
| 技能可更新性 | ✅ 即時更新 Markdown | ✅ 可更新但沒有主動更新循環 |
| 外部驗收機制 | ❌ 無 | ❌ 無（但有 cron 強制執行腳本） |
| 主動後設認知觸發 | ⚠️ 靠 cron job 每 2 小時 | ⚠️ 靠 cron job 每 5 分鐘 |
| SOP 服從性 | ~70-80% | ~70-80%（推測相同限制） |

---

## 理想架構（未來方向）

一個真正「越用越聰明」的系統需要：

1. **外部驗收迴圈**：任務完成後，自動化測試對照 SOP 檢查結果
2. **量化追蹤**：記錄每次 SOP 被偏離的次數，統計趨勢
3. **偏差學習**：每次偏移被糾正後，自動更新對應 SOP，避免重蹈

這需要額外的工程開發，不是純 LLM 能自動解決的。