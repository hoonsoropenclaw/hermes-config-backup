# Keyword 觸發 SOP（使用者自訂 `@` 指令集中管理）

> 2026-06-09 啟用。HERMES 沒有內建 user-defined macro，**keyword 觸發是 agent-level 行為**——每次收到訊息時 agent 自己掃、命中就跑預先寫好的 SOP。本檔集中管理所有 keyword 的完整執行細節，AGENTS.md 的表格只放摘要。

---

## 通用原則（所有 keyword 都適用）

- **前綴掃描**：每次收到使用者訊息，先看訊息**開頭**或**結尾**是否有 `@<keyword>`。命中才觸發，不要在訊息中間的引用文字誤觸發。
- **觸發確認**：觸發後**第一句話**要說「`@<keyword>` 觸發 → <行為>」讓使用者知道跑起來了。
- **結尾報告**：每個 keyword 跑完都要**統一報告**改了哪些檔、做了哪些動作，方便使用者事後審查。
- **不寫進 cron**：這些都是會話內觸發，**不是**排程任務，不要污染 cron 設定。
- **If** 收到帶 `@` 前綴的訊息 **Then** 觸發對應 SOP
- **If** 使用者說「以後說 X 觸發 Y」**Then** 當下在 AGENTS.md 表格 + 本檔新增段落，跑 `grep` 驗證寫入

---

## @學習（已啟用，2026-06-09）

**觸發情境**：會話結束、或使用者覺得這次對話有值得記下的教訓。

**執行步驟**：
1. 掃此次對話紀錄的試誤（看使用者糾正過什麼、agent 自己卡過什麼）
2. 跟 `trial-and-error` skill 既有條目去重（`grep -F "<新教訓>"` 看有沒有）
3. 只新增**沒重複**的 L2 條目到 `references/by-category/` 對應分類
4. 對話摘要篩出「跨 session 重要事項」→ 視情況更新 MEMORY.md / AGENTS.md
5. 結尾**統一報告**改了哪些檔

**模式**：B 模式（agent 有把握的「真新教訓」直寫、結尾報告；沒把握的問使用者確認）。

**驗證**：
```bash
grep -F "<新教訓關鍵字>" ~/.hermes/skills/trial-and-error/references/by-category/*.md
# 期望：本次新寫的教訓有命中、其他不重複
```

---

## @刷新（預留，未啟用）

**觸發情境**：使用者想看赫米斯系統狀態（profile 數、記憶大小、最近活動）

**預定執行**：
```bash
hermes status 2>&1 | head -30
echo "---"
ls -la ~/.hermes/memories/ | head -20
echo "---"
ls ~/.hermes/profiles/ 2>&1
```

**未啟用原因**：目前 `hermes status` 報的東西不夠全面、custom report 還沒設計。

---

## @備份（預留，未啟用）

**觸發情境**：使用者想跑 Hermes 雙雲端備份（v4.1 架構）

**預定執行**：
```bash
bash ~/.hermes/scripts/hermes-backup-v4.sh 2>&1 | tail -30
```

**未啟用原因**：備份通常已設 cron 自動跑（`v4-backup-tier1-daily` 02:00、`v4-backup-tier2-daily` 02:30），手動觸發情境少。

---

## @專案（已啟用，2026-06-09）

**觸發情境**：使用者交辦明確多階段、需要角色分工的任務（市場調研→PRD→工程 等鏈式工作）。**會話中**使用者說「這個用 `@專案` 跑」或「走 handoff 流程」即啟動。

**核心觀念**：
- **赫米斯（default profile）= orchestrator**：跨 profile 記憶隔離，**只有 default 能記得全貌**。兩個常駐代理之間不互通、需要 default 當中繼。
- **不是全自動**：使用者會看到至少 2 次工具呼叫（每個常駐代理 1 次 `chat -q`）。預期這是 trade-off、不是 bug。
- **適合任務**：鏈式、多階段、需要不同專業角色（市場策略 / 產品規劃 / 工程實作 / 視覺設計 等）

**4 步執行 SOP**：

### 步驟 1：解析任務、決定代理鏈
- 讀使用者訊息，拆解成「階段 1 → 階段 2 → ...」
- 對應到現有常駐代理（`market-strategist` / `product-planner` / 未來其他）
- 若代理不存在 → 提示使用者先建（走「精瘦 profile SOP」）

### 步驟 2：建立 handoff 目錄
```bash
mkdir -p ~/.hermes/handoff/<project-slug>
# project-slug 用 kebab-case，例：freelancer-tax-tool / ai-tutor-app
```

### 步驟 3：依序跑每段代理
```bash
# 範例：跑市場策略代理
terminal(command="market-strategist chat -q \"請做 <任務> 的市場調研...\" --cli", timeout=600)
```

**重要細節**：
- 用 wrapper（`market-strategist` / `product-planner`）呼叫，**不要**用 `hermes -p <name> chat`
- 加 `--cli` flag 走 non-interactive 模式
- `timeout` 設 600 秒（10 分鐘）給足時間，複雜調研可能 5-8 分鐘
- **一定要等這段跑完**才能進入下段（不要並行——後段需要前段產出）

### 步驟 4：撈報告、寫到 handoff、傳給下段
```bash
# 撈最新 session 的產出
SESSION_DIR=~/.hermes/profiles/market-strategist/sessions/
LATEST=$(ls -t $SESSION_DIR/*/transcript.json 2>/dev/null | head -1)
# 解析出最終 assistant 回覆（看 transcript.json 結構）
# 寫到 handoff
cp <report> ~/.hermes/handoff/<project-slug>/market-research.md
# 然後跑下段
terminal(command="product-planner chat -q \"@~/.hermes/handoff/<project-slug>/market-research.md 請寫 PRD...\" --cli", timeout=600)
```

**驗證**：
```bash
ls -la ~/.hermes/handoff/<project-slug>/
# 期望：market-research.md + prd.md 都存在
```

**結尾報告**：
- 跑了幾段代理
- 每段產出檔案位置
- 下一步建議（例如 PRD 完成後要不要建工程代理實作）

---

## 未來可能新增的 keyword（保留位）

| Keyword | 預定行為 | 觸發時機 |
|---------|---------|----------|
| `@部署` | 跑 `vercel --prod` + health check | 程式碼完成要上線時 |
| `@翻譯` | 把指定檔案翻成指定語言、保留格式 | i18n 工作 |
| `@截圖` | 對指定 URL 截圖 + vision 分析 | 視覺驗證 |

**If** 新增 keyword **Then** 同步更新 AGENTS.md 表格 + 本檔段落 + MEMORY.md「更新記錄」+ `grep` 驗證
