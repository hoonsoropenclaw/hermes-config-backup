# 使用者自訂 keyword 觸發規則 SOP（2026-06-09 啟用）

> HERMES 沒有內建 user-defined macro。所有「之後我說 X 時請執行 Y」的跨 session 規則都透過這套 agent-level 機制實作。

## 觸發流程（agent 收到訊息時）

```
收到訊息
  ↓
掃訊息含不含「@<關鍵字>」（@ 是慣例前綴、Telegram/LINE 都吃、不要用 / 避免跟 slash command 撞）
  ↓ 命中
讀 AGENTS.md 開頭「🎯 使用者自訂 keyword 觸發規則」表的對應列
  ↓
按該列的「觸發行為」描述執行
  ↓
結尾報告「跑了什麼、改了什麼」
```

## 目前啟用的 keyword（2026-06-09 狀態）

| Keyword | 觸發行為 | 模式 |
|---|---|---|
| `@學習` | 1. 掃此次對話試誤 → 跟 `trial-and-error` skill 既有條目去重 → 只新增沒重複的 L2 條目到 `references/by-category/` 對應分類<br>2. 對話摘要篩出「跨 session 重要事項」→ 視情況更新 MEMORY.md / AGENTS.md<br>3. 結束時**統一報告**改了哪些檔 | **B 模式**：有把握的真新教訓直寫、結尾報告；沒把握的問使用者確認 |
| `@刷新` | 跑 `hermes status` + `ls ~/.hermes/memories/` + 報告系統狀態 | 預留未啟用 |
| `@備份` | 跑 `~/.hermes/scripts/hermes-backup-v4.sh` → 報告備份結果 | 預留未啟用 |
| `@專案` | 1. 觸發「跨 profile handoff pipeline」：**赫米斯（default）當 orchestrator**，**根據任務需求動態決定要串接哪幾個常駐代理**（現有：`consumer-researcher`、`product-planner`；未來可加：`engineering-lead`、`designer` 等），每段把上個代理的產出寫到 `~/.hermes/handoff/<slug>/`、再交給下個代理<br>2. **會話中**用戶說「這個用 `@專案` 跑」或「走 handoff 流程」即啟動；`@專案` 適合「需求調查→PRD→工程實作→視覺設計」這類**多階段、需要角色分工**的任務（**鏈的長度、順序、起點終點全部由任務內容動態決定**,上述只是常見的典型範例之一）<br>3. 結束時報告每段代理的產出位置 + 串接結果<br>4. **🚨 高資料量任務風險**(2026-06-10 親身踩到):prompt 含「30+ 聲音」「完整 X」「所有 Y」這類要求時,常駐代理 10 分鐘後 context 會衝到 100K+、LLM 進入 thinking loop 卡住。**必用 background 模式 + monitor log**,5 分鐘沒新 API call 且 in_tokens > 100K 立即 kill + default 接手。**完整 SOP 見本檔下方「@專案 SOP 段」+「Context 累積風險」段** | 採 A 模式:default 赫米斯跑 N 次工具呼叫串接(**N = 鏈上代理數**;**新增常駐代理後 N 自動增加、不需改 SOP**)。**不是全自動**——使用者會看到工具呼叫、且每段代理要等跑完才能接下段 |

## 三種觸發模式（給未來參考）

| 模式 | 行為 | 適用情境 |
|---|---|---|
| **A** 確認優先 | 每次都列清單等使用者逐一勾選 | 高風險任務（清資料、刪檔、動 config） |
| **B** 直寫+報告 | 有把握的真新教訓直寫、結尾報告；沒把握的問確認 | **中風險**（像 @學習 寫進 trial-and-error、可回退） |
| **C** 寬鬆 | 看到訊息就動、不需等確認 | 低風險（讀檔、跑 status、列清單） |

## 新增 keyword 的 SOP（給未來自己看）

使用者說「之後我說 X 時請執行 Y」時：

1. **當下就在 `~/.hermes/memories/AGENTS.md` 開頭的 keyword 表格新增一行**——不要等、不要只回對話
2. **如果是多步驟 SOP**（像 @學習 4 步流程）：建 reference file（像本檔或 `~/.hermes/skills/trial-and-error/references/adding-entries-sop.md`），AGENTS.md 表格該列寫「完整 SOP 見 references/sops/<name>.md」
3. **跑 `grep` 驗證**寫入了——不靠 patch 工具的成功訊息
4. **如果 SOP 是新類別的**（不是已有 skill 能管的）：考慮建獨立 skill，避免 AGENTS.md 表格膨脹
5. **驗證 SOP 真的可被新 session 讀到並執行**：把表格內容寫成「新 session 也能直接執行」的具體指令（具體路徑、預期輸出），不要寫敘述性語句

## If→Then 速查

- **If** 收到「之後我說 X 時請執行 Y」**Then** 當下在 AGENTS.md 開頭表格新增一行 + `grep` 驗證
- **If** keyword 觸發的 SOP 超過 3 步 **Then** 建 reference file 拆出去
- **If** 不確定該用 A/B/C 哪個模式 **Then** 預設 B（@學習 模式），使用者後續要求可調
- **If** 觸發的行為改了系統狀態（動了檔、跑 cron、砍東西）**Then** 結尾一定要報告改了什麼（不要只說「跑完了」）
- **If** 發現既有 keyword 表格的 SOP 指向不存在的檔 **Then** 立刻補建（AGENTS.md 不能指向虛無）
- **If** 觸發失敗（找不到 skill、找不到檔）**Then** 不要硬擺、誠實說「這個 SOP 還沒寫完」+ 給建議怎麼補

## @專案 SOP 段（2026-06-10 補建,補系統遺留缺陷）

> **情境**:使用者在主 session 說「@專案」或「走 handoff 流程」,表示這個任務需要**多個常駐代理分工串接**,default 赫米斯當 orchestrator 跑 N 次工具呼叫（**N = 鏈上代理數**,由任務動態決定）。

### 觸發判定

- 使用者訊息明確含 `@專案` 觸發詞
- 或使用者說「走 handoff 流程」「讓多個代理分工跑」「這個用 A→B→C 跑」

### 流程（4 步）

1. **解析任務 → 決定代理鏈**:
   - 讀使用者訊息,釐清任務範圍
   - `hermes profile list` 看現有常駐代理
   - 動態決定鏈的起點/終點/中間節點(不要寫死)
   - 缺哪個代理 → 提示使用者先建(用 `hermes profile create <name> --clone`)
   - **預估每段代理的 prompt 資料量**——如果任務要求「30+ 消費者聲音」「完整功能矩陣」這類**高資料量**的 prompt,**考慮拆段或降要求**(見下方「context 累積風險」段)

2. **依序跑每段代理**:
   ```bash
   # 用 wrapper + --cli 跑(non-interactive)
   ~/.local/bin/<agent-name> chat -q "<這段任務指令>" --cli
   ```
   - 每段任務指令要附上前段產出的絕對路徑(用 `@` 引用)
   - 不用 tmux、不背景跑,等每段跑完再接下段
   - **不要**包成一個 shell script 一次跑(失敗 debug 困難、且會擋住互動)
   - **必用 `terminal(background=true, notify_on_complete=true)`** 跑超過 5 分鐘的代理(預設 foreground 上限 600s = 10 分鐘,超過會被 timeout 砍掉)。background 模式讓 orchestrator 可以輪詢進度、不會被卡住

3. **撈每段代理的最終產出**:
   - 預設產出位置:`~/.hermes/handoff/<project-slug>/<stage>.md`
   - 從 default session 跑 `ls -la` + `wc -lwc` 二次驗證檔案存在
   - **不信任代理自報**「已完成」(參考 [[#常駐代理 sandbox HOME 隔離:絕對路徑可能繞路（2026-06-10）]])
   - **如果代理超時或卡在 thinking loop** → 看 `~/.hermes/profiles/<agent>/logs/agent.log` 最後 5 分鐘,如果 5 分鐘沒新 API call → **果斷 kill 接手**(詳見下方「context 累積風險」段)

4. **報告交付**:
   - 每段代理的產出位置 + 行數/大小
   - 串接結果(下段代理有沒有讀到上段產出)
   - 最終產出給使用者看
   - 結尾**一定報告「跑了什麼、改了什麼」**(AGENTS.md 表格要求)
   - **如果哪段代理失敗/fallback** → 誠實說「這段是 default 接手整合的、不是代理親自寫的」、標明報告版本(`v0.1-default-fallback`)讓使用者知道品質

### 代理鏈典型範例（不要當 SOP,參考用）

- 媒合/平台/交易類產品:`consumer-researcher → product-planner`(現有 2 段)
- 加設計:`consumer-researcher → product-planner → designer`(未來 3 段)
- 完整生命週期:`consumer-researcher → product-planner → engineering-lead → designer`(未來 4 段)

> **關鍵**:鏈長動態決定,不要寫死。新增常駐代理後,鏈自動延伸、不需改 SOP。

### Context 累積風險（2026-06-10 親身踩到,本節是 @專案 最重要的坑）

> **症狀**:常駐代理跑超過 10 分鐘後、context 累積到 100K+ tokens,LLM 進入 5 分鐘+ thinking loop 無新 log、看起來像「卡住」但其實還活著。**foreground terminal 會被 600s timeout 砍掉**、background process 雖然繼續跑但 orchestrator 要手動 poll 判斷什麼時候要 kill 接手。

**根因**:
- `web_search` 每次回 1.6-4.6K chars 餵進 context
- `web_extract` 處理 5-30K chars 內容(LLM 摘要後 1.6-5K)
- 「30+ 消費者聲音」這類高資料量 prompt → 10-15 個 URL 就突破 100K
- context 越大、LLM 思考越慢、容易進入「停滯」狀態(沒有新 API call、沒有新 log、但 process 還在)

**預防(動手前)**:
- 評估 prompt 的「資料需求量」,**高資料量任務(< 30+ 聲音、5+ 標竿)必先降要求**或**拆成多段**
  - 例:把「30+ 消費者聲音」改成「15+ 高頻痛點 + 10+ 中頻痛點」(資料量減半)
  - 或在 prompt 加「找到 10 個高品質聲音就停止,品質 > 數量」軟性停止條件
- **預期 background 跑時間**:context 100K 內約 10-15 分鐘;**超過 100K 風險高、必用 background mode + 主動 monitor**

**診斷(跑中)**:
```bash
# 1. 看 log 最後時間
tail -5 ~/.hermes/profiles/<agent>/logs/agent.log

# 2. 看最後 API call 的 in_tokens 跟現在時間差
grep "API call" ~/.hermes/profiles/<agent>/logs/agent.log | tail -3
# 如果 in_tokens > 100K 且 5 分鐘沒新 API call → 砍

# 3. 看 process 還活著嗎
ps -p <pid> -o pid,etime,cmd
```

**處理(已卡住時)**:
- **果斷 kill + default 接手**:不要傻等、不要嘗試用 prompt「叫醒」
  ```bash
  # 找 process
  ps -ef | grep "<agent-name> chat"
  # kill
  kill <pid>
  # 接手整合:從 log 撈已抓 URL、從 partial handoff 撈已寫部分、default 自己補完
  ```
- **保留已花的成本**:agent 跑 10 分鐘通常已爬了 10+ URL、累積 100K+ chars 資料。這些都在 log 內、**不要浪費**
  ```bash
  # 撈已抓的 URL 清單
  grep -oE "https?://[^ )]+" ~/.hermes/profiles/<agent>/logs/agent.log | sort -u

  # 撈已抓的 chars 累計
  grep "tool web_search completed" ~/.hermes/profiles/<agent>/logs/agent.log | awk -F'chars' '{sum+=$1} END {print "累計 chars:", sum}'
  ```

**判斷門檻**:
| 觀察 | 判斷 | 動作 |
| --- | --- | --- |
| 5 分鐘內有新 API call | 正常跑 | 繼續等 |
| 5 分鐘沒新 API call + in_tokens < 100K | 可能 LLM 在整合 reasoning | 再等 3 分鐘,超過 8 分鐘就 kill |
| 5 分鐘沒新 API call + in_tokens > 100K | **幾乎肯定卡住** | 立即 kill、default 接手 |
| 10 分鐘沒新 API call 不論 in_tokens | 已死 | 立即 kill、default 接手 |
| API call 報錯 `peer closed connection` | 網路問題、可能 recover | 等 1 分鐘看是否 retry |
| `mempalace` MCP failed to connect | 跟任務無關 | 忽略、繼續等 |

**If→Then**:
- **If** 派 @專案 鏈任何一段代理的 prompt 含「30+」「完整 X」「所有 Y」這類**高資料量要求** **Then** 先降要求(改「15+」「核心 X」「關鍵 Y」)、**不要**盲目相信代理能在 100K context 內做完
- **If** 觀察到代理 5 分鐘沒新 log 且 in_tokens > 100K **Then** 立即 kill + default 接手、**不要**嘗試「再等一下看會不會醒」
- **If** 代理超時/卡住已接手整合 **Then** 報告裡**誠實標明**「這段是 default 接手、版本 v0.1-default-fallback」、**不要**包裝成「代理已完成」誤導使用者

### If→Then 速查

- **If** 收到 `@專案` **Then** 跑 4 步流程(解析→跑 N 段→撈→報告)
- **If** 代理鏈有缺(profile 沒建) **Then** 中斷、提示使用者先建,**不要**fallback 用 default 跑
- **If** 任何一段代理失敗 **Then** 中斷鏈,詢問使用者:重試/略過/降級
- **If** 代理產出檔案不在預期 handoff 位置 **Then** 跑 `find ~/.hermes -name "<expected-file>.md"` 找實際位置(參考 sandbox HOME 隔離條目)
- **If** `@專案` 鏈只有 1 段(只要某一個代理跑) **Then** 鏈長自動縮短、跑單段、停在該段產出

## 相關檔案

- `~/.hermes/memories/AGENTS.md` — keyword 表格的 source of truth（每次啟動讀）
- `~/.hermes/skills/trial-and-error/SKILL.md#新增條目 SOP` — @學習 4 步流程精簡版
- `~/.hermes/skills/trial-and-error/references/adding-entries-sop.md` — @學習 完整版（決策樹、常見錯誤、If→Then 速查）

## 設計決策的「為什麼」（給未來 audit 用）

| 決策 | 為什麼這樣選 |
|---|---|
| 用 `@` 前綴不用 `/` | `/` 在 Telegram/Discord 會被當 slash command、`@` 不會衝突且 platform 通用 |
| 寫進 AGENTS.md 不寫進 SOUL.md | AGENTS.md 是「行為/觸發規則」段、SOUL.md 是「人格/價值觀」段，職責分離 |
| 不建 cron / webhook | cron 是「獨立進程」、不是「會話內觸發」，會失去對話脈絡 |
| 預設 B 模式 | 跟 trial-and-error 既有 SOP 一致（@學習是 mid-task 行為、需要快速迭代、但又不能太寬鬆誤寫） |
| 不建獨立 `keyword-triggers` skill | 目前只 1 條啟用、AGENTS.md 表格就放得下；等 3+ 條 SOP 都成型再獨立 |
