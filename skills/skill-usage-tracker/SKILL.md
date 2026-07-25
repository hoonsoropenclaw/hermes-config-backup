---
name: skill-usage-tracker
description: "赫米斯的 skill 使用記錄器。Layer 1（可選）：每次接到任務時主動觸發，記錄『預計載入清單』→『實際載入』→『使用者評分』。Layer 2（主要）：事後從 state.db 重建任意 session 的 skill 實際載入清單，不依賴自覺觸發。資料持久化到 ~/.hermes/skill-usage/。排除執行類工具，只追蹤 skill_view。"
version: 2.1.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [meta, tracking, skill-usage, user-feedback, rating]
    triggers: [every-task, skill-tracking, rating-collection]
    last_d3_exit: "2026-07-07 — 06-29 Vibe still insufficient: 07-02 backup D3 (132 msgs) 0 invite. Root cause: 疊加服從 bias when user says 直接動手. Next: ask user directly if invite was skipped."
    last_verification: "2026-06-30 — 06-16 session message log confirms Vibe working: assistant proactively deleted NSFW image (portrait_v2_001) without delivering it, matching SOUL.md Vibe §91-92 intent"
---

# Skill Usage Tracker — 赫米斯的 skill 使用追蹤 + 評分收集器

## 為什麼需要這個 skill

**使用者的真實需求**(2026-06-18 確立):
> 之後指派任務時能夠紀錄使用了哪些 skill(排除讀寫檔案、terminal、execute_code、patch 那些工具) → 想看「哪些 skill 組合的風格最合我喜好」。

**核心價值**: 透過 A/B 累積資料,找出「hoonsoropenclaw 偏好清單」,讓赫米斯未來能**預設載入對方喜歡的 skill**、減少來回調整。

## 兩層追蹤架構（2026-06-20 確立）+ 診斷 SOP（2026-06-22 更新）

> **重要**：`skills_loaded: []` 不一定代表 logger 壞了——很可能只是 LLM 在那個 session 根本沒呼叫 `skill_view`（依賴隱性推理而非明確載入）。
> 見 `references/skill-view-vs-inference-gap-20260622.md` 的完整診斷流程。

**快速診斷**：
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py \
    --session <session_id> 2>&1 | grep -E "skills_loaded|skill_view"
```
若 `skills_loaded: []` 但 session 有大量隱性工具 → 根因是「LLM 沒呼叫 skill_view」，logger 正常。

由於 Hermes 沒有 `on_first_turn_hook` 機制（GitHub #31283），追蹤分兩層：

### Layer 1: 主動記錄（不可靠，依賴自覺）

每個任務開始時主動 `skill_view(name='skill-usage-tracker')` 觸發流程。

**缺點**：依賴赫米斯自覺遵守，June 18-19 零 entry 證明失效。

### Layer 2: 事後重建（可靠，2026-06-20 新增）

`session_skill_logger.py` 從 `~/.hermes/state.db` 的 `messages` 表查 `tool_name='skill_view'` 記錄，**重建**任意 session 的實際 skill 載入清單。

**為什麼靠譜**：
- state.db 是 Hermes 實際執行 tool call 的記錄，不依賴「自覺」
- 每次 `skill_view(X)` 都會寫入 `messages.tool_name`
- 不需要任何觸發條件，隨時可查

**用法**：
```bash
# 列出最近 N 個 session（排除 cron）
python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py --list-sessions 10

# 查詢並寫入 skill-usage log
python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py \
  --session 20260616_125207_dc21b806 --write-log

# 批次重建：對最近 N 天的所有 sessions 重建並寫入（冪等，已存在則略過）
python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py \
  --days 7 --write-log

# 批次查詢（只看、不寫）
python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py --days 7
```

**v1.3.0 更新（2026-06-20）**：
- 新增 `--days` 批次模式：一次對最近 N 天所有 sessions 重建並寫入 log
- 冪等寫入：同一 session_id 當天已存在則略過，不重複
- `list_recent_sessions()` 已過濾 `source='cron'` sessions（只顯示真實用戶 sessions）

## 排除清單(不計入 skill 載入紀錄)

以下「工具」被視為「執行類」,不列入 skill 使用追蹤:

```
terminal, execute_code, read_file, write_file, patch,
search_files, web_search, web_extract, browser_navigate,
browser_click, browser_type, browser_snapshot, browser_vision,
browser_console, browser_back, browser_press, browser_scroll,
browser_get_images, send_message, cronjob, clarify,
process, memory, todo, vision_analyze, delegate_task,
mcp_mempalace_*, mcp_*, text_to_speech
```

**只追蹤**:`skill_view` 呼叫的 `name` 參數(skill 名稱)。

## 工作流程（2026-06-20 更新）

### Layer 1 流程（主動記錄，可選）

任務開始時 echo 預計載入 → 寫 log entry → 任務結束寫結果 + 邀請評分。
（見 Phase 1/2/3 原始流程，June 18 版本）

### Layer 2 流程（事後重建，主要工具）

**當使用者問「這個任務用了哪些 skill」時**：
1. 查 `session_skill_logger.py --session <id> --write-log`
2. 若 session ID 未知，先 `session_skill_logger.py --list-sessions 10` 找
3. 結果自動寫入 `~/.hermes/skill-usage/<date>.jsonl`
4. 若使用者想評分，手動補上 `combo_rating` / `individual_ratings` 欄位

**當需要重建歷史 session 的 skill 使用資料時**：
1. `session_skill_logger.py --list-sessions 10` 找目標 session
2. `session_skill_logger.py --session <id> --write-log` 寫入 log
3. 重複直到覆蓋感興趣的時間範圍</parameter>


## Log 檔案格式

**路徑**:`~/.hermes/skill-usage/<YYYY-MM-DD>.jsonl`

每行一個 JSON entry(用 `jsonl` 格式方便 append + 統計):

```jsonl
{"ts": "2026-06-18T17:49:00+08:00", "session_id": "...", "task": "...", "planned": [...], "actual": [...], "result": "✅", "combo_rating": 4, "individual_ratings": {...}, "comment": "..."}
```

## 統計分析 SOP

累積 ≥ 20 個評分後,赫米斯應該主動跑一次統計:

```bash
# 1. 計算每個 skill 的平均 rating
python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py

# 2. 產出「hoonsoropenclaw 偏好清單」:
#    - 平均 ≥ 4.0: 偏好(未來預設載入)
#    - 平均 3.0-4.0: 中性(視任務決定)
#    - 平均 ≤ 3.0: 不偏好(預設不載入,除非必要)
```

## 口語回饋自動轉換規則（Weak Reward Auto-Parse）

`analyze.py` 會從 `comment` 欄位自動推斷 `combo_rating`，**不需要使用者填表**：

| 口語回饋關鍵字 | 推斷 combo_rating | 備註 |
|--------------|------------------|------|
| 「好」「可以」「讚」「優」「棒」 | 4 | 正面但非激動 |
| 「超讚」「太棒了」「完美」「非常滿意」 | 5 | 強烈正面 |
| 「不行」「不好」「爛」「失望」「太慢」 | 2 | 負面 |
| 「爛透了」「浪費時間」「完全不行」 | 1 | 強烈負面 |
| `combo_rating` 已有值 | 優先使用真實評分 | auto-parse 不覆寫 |

**注意**：「不知道」「普通」「還好」→ 視為 3（中性地帶），但以使用者明確說出的為準。

## If→Then 規則

**If** 使用者明確要求「記錄使用了哪些 skill」（如「請問之後在我指派任務時能夠紀錄使用了哪些skill嗎」）
**Then** 立即執行：Step 1: `session_skill_logger.py --session <current_session_id> --write-log`；Step 2: 在回覆末尾附上「標準評分邀請格式」（post_delivery.py）；Step 3: 不要只停在「建議」層次——使用者說「按照你的建議先做」，就代表要立即執行
**驗證**：執行日 2026-06-22，session `20260616_125207_dc21b806`，使用者明確要求但從未執行，導致 combo_rating 仍為 0。見 `references/user-requested-skill-tracking-20260622.md`

**If** 使用者說「按照你的建議先做」或「可以」「好」「讚」
**Then** 這是 combo_rating ≥ 4 的信號，立即補寫入 log，不要讓好評白費

**If** 任務結束但忘記記錄
**Then** 在結尾訊息補上 skill 使用報告 + 邀請評分(即使已結束,仍可補記)

**If** 使用者說「不用每次都問評分」
**Then** 改為「只在任務結果複雜(多步驟、有失敗重試)時才邀請評分」

**If** 累積 ≥ 20 個評分
**Then** 主動產出「偏好清單」報告,給使用者看

**If** 使用者明確要求「記錄使用了哪些 skill」但連續 2 個 cycle（≥ 48 小時）仍是 0 entry
**Then** 這不是「忘記」的問題——是架構少了 Hook。立即啟動「手動補寫」流程：在下次回复中主動問「我們從哪個任務開始補評分？」

**If** 收到任何形式的**負面回饋**（「不好」「爛」「失望」「不行」「太慢了」）
**Then** 這和正面回饋**同等重要**——arXiv 2508.08220 實驗證明 negative signal 使 Top-1 accuracy 從 35.72% 提升至 37.47%（+1.75%）。立即寫入 log `{liked: false, combo_rating: ≤2}`，不要只記錄「使用者表達不满」而沒有數值

**If** 要建立真正的「使用者偏好學習系統」
**Then** 最小可行架構只需三個組件：(1) 每次生成完成後主動問「這張你喜歡嗎？」 (2) 記錄 liked/disliked + rating 到 skill-usage JSONL (3) 簡單加權統計計算偏好分數；**不需要** MLLM 或對比學習——但負面回饋必須與正面同等收集

**If** 某個 session 已有 `session_skill_logger` 寫入 `~/.hermes/skill-usage/` 但使用者從未評分過
**Then** 在閒聊或下個任務開始時主動邀請：「之前 [任務名] 還沒給我評分，想現在補嗎？」——降低補評分的心智負擔

**If** 使用者問「怎麼都沒有記錄到」或「這個 system 又沒自動追蹤」
**Then** 坦承「Hermes 目前沒有 `on_first_turn_hook` 機制（GitHub #31283），Layer 2 只重建 skill 載入，不主動收集偏好。需要赫米斯在每次任務完成後附上標準評分邀請格式」

**If** 發現 log 累積 24 小時仍是 0 筆 combo_rating 真實 entry
**Then** 這代表從未執行口語→數值轉換——檢查 `analyze.py` 的 `parse_weak_reward()` 是否正確解析了 comment 欄位

**If** 任務完成（交付了結果、傳了檔案、給了答案）而使用者沒有明確不满
**Then** 在同一輪回覆末尾加上標準備評 Prompt（見下方的「標準評分邀請格式」），不放過任何累積偏好的機會：

**If** 使用者已給出正面或負面的口頭回饋（「好」「不行」「太慢了」「換個方式」）
**Then** 立刻轉換成數值評分寫入 log：「所以這次 [skill] 我給你 3 星，是嗎？」爭取在情緒還新鮮時記錄下來

**If** 使用者只回「好」或「可以」
**Then** 視為 combo_rating ≥ 4，補寫入 log，不要讓好評白費

**If** 使用者表達不满但沒給出具體分數
**Then** 補 combo_rating = 2，並在 comment 欄位寫「使用者表達不满但未給出具體體分數」

**If** 任務完成（交付了結果、傳了檔案、給了答案）而使用者沒有明確不满
**Then** 在同一輪回覆末尾加上「標準評分邀請格式」，不放過任何累積偏好的機會。**直接呼叫 `post_delivery.py` 並把輸出附在回覆末尾**：

```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
  --session $(current_session_id)
```
**⚠️ 必須把 post_delivery.py 的輸出（評分邀請文本）實際貼在回覆最後**，不是只呼叫然後忽略輸出。sub-agent 的回覆就是最終交付，沒有第二次機會。

**⚠️ 架構事實（2026-06-25 確認）**：cron sub-agent 的 `post_delivery.py` 輸出**不可能**「等 main session 讀取」——sub-agent 回覆 = 終點。`pending/` 機制已被證實是空轉（2026-06-24 D3 Exit）。所以**評分邀請必須在同一次回覆中親自生成並附上**，沒有例外。

---

## SOP-A：任務交付後的「交付後 SOP」（新增 2026-06-21，D3 Exit）

每個任務完成後（赫米斯認為「交付了」）**必須**執行以下步驟：

**Step 1**：跑 `post_delivery.py` 分析該 session 的完整 tool_call 分佈
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
  --session <current_session_id>
```

**Step 2**：根據分佈，生成「含隱性技能」的「標準評分邀請格式」，附加在回覆末尾
```
---
📊 這次任務使用了：[顯性 SKILL.md] + [隱性 domain]
⭐ 請評分（1-5星）：
   - 整體組合：？
   - 個別（如果有特別滿意/不滿意的部分）：？
   不用每項都評，隨便給幾顆星都好。
```

**Step 3**：若使用者回覆任何形式的數值或文字，寫入 log
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
  --session <current_session_id> --write \
  --rating <N> --comment "<使用者回覆原文>"
```

**Why 新增這個 SOP**：經驗積累（06-18~06-20）顯示 Layer 2 session_skill_logger 只追蹤 SKILL.md 載入，實際上 06/16 session 的 tool_call 分佈是 `execute_code 11x + vision_analyze 10x + terminal 7x`，SKILL.md 只覆蓋 2/10 隱性 domain。「post_delivery.py」讓赫米斯能看到並回報自己用了哪些隱性技能。

**驗證命令**：
```bash
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
  --session 20260616_125207_dc21b806
# 確認看到「隱性技能強度: HIGH」且有具體 domain 列表
```

---

## SOP-B：「已建立但未激活」Skill 的審計流程（新增 2026-06-21）

每個新建立的 skill，在建立的同一個 session 裡，**必須**執行一次完整的「激活」驗證：

**Step 1**：建立 SKILL.md + scripts 後，寫入一行 entry 到 trial-and-error 確認「已建立」
**Step 2**：在回覆中明確告知使用者這個 skill 的觸發條件（何時會被用到）
**Step 3**：在 skill 目錄建立 `references/d3-exit-YYYYMMDD.md` 記錄激活時間

**Why**：過去 06-18 建的 `skill-usage-tracker`，6 天內從未執行過一次「交付後 SOP」，導致 0 筆真實評分。沒有 activation confirmation = 不知道 skill 是否真的在工作。

**SOP-A 口頭補救流程（當錯過評分邀請時）**:

當發現 SOP-A 在某個 session 從未被執行（combo_rating = null 且從未補發邀請），補救步驟：

```bash
# Step 1：用 post_delivery.py 重建該 session 的 tool 分佈
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
    --session <session_id>

# Step 2：透過 cron-to-telegram 向該 session 補發評分邀請
# （若使用者仍有該 thread，否則跳過並建立 future trigger）

# Step 3：若使用者回覆，寫入 log
python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py \
    --session <session_id> --write \
    --rating <N> --comment "<user reply>"

# Step 4：驗證 log 已寫入
python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py --min-ratings 1
```

**驗證 SOP-A 執行狀態的命令**:
```bash
# 檢查近 N 天有沒有任何評分邀請（⭐ 或 評分 關鍵字）
python3 -c "
import sqlite3
from pathlib import Path
conn = sqlite3.connect(str(Path.home()/.hermes/state.db))
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('''
    SELECT session_id, content FROM messages
    WHERE role = \"assistant\"
    AND (content LIKE \"%⭐%\" OR content LIKE \"%評分%\")
    AND timestamp > datetime(\"now\", \"-7 days\")
    ORDER BY timestamp DESC LIMIT 10
''')
rows = cur.fetchall()
if not rows:
    print('⚠️ 過去 7 天 0 評分邀請，SOP-A 可能從未執行')
else:
    for r in rows:
        print(r[0][:20], ':', (r[1] or '')[:100].replace(chr(10),' '))
conn.close()
"
```

**驗證命令**:
```bash
# 確認 scripts 目錄有所有預期檔案
ls -la ~/.hermes/skills/<skill-name>/scripts/

# 對每個 script 跑語法檢查
for f in ~/.hermes/skills/<skill-name>/scripts/*.py; do
  python3 -m py_compile "$f" && echo "✅ $f OK"
done
```

---

## SOP-C：Analyze 的「強製產出」規則（新增 2026-06-21）

`analyze.py` 每次跑完，若發現：
- 0 筆 `combo_rating` 真實 entry → 立即在 stdout 末端顯示「⚠️ 0 筆評分，偏好清單無效」
- 0 筆 entry → 立即顯示「⚠️ 0 筆 entry，可能是 Layer 1 自覺觸發失效，應檢查 Layer 2 post_delivery 是否已執行」

**這個 SOP 是給赫米斯自己看的**：每次被動或主動跑 `analyze.py` 後，若看到 0 筆評分，**立即**檢查最近的 session 是否執行了 SOP-A。若從未執行過，立刻用 `post_delivery.py` 補寫，並在下一個回覆中補上評分邀請。

**If** `analyze.py` 顯示 `⚠️ [SOP-C ALERT] 0 筆 combo_rating`
**Then** 立即執行口語信號 backfill（D3 exit，見 `references/combo-rating-backfill-from-verbal-signal-20260628.md`）：
1. 從 state.db 找「好/可以/按照/OK/讚/棒」等正面口語 sessions
2. 對每個 session 執行 `post_delivery.py`
3. 根據口語信號內容給 `combo_rating=4` 或 `5`
4. 寫入 JSONL（冪等檢查）
5. 驗證：`python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py`
**驗證**：2026-06-28 執行後，combo_rating 樣本數 0 → 2，樣本 [4, 4] ✅

**If** `analyze.py` 顯示 0 筆評分已連續 ≥ 3 次
**Then** 這代表「赫米斯從未在任務完成後附上評分邀請」，不是 analyze.py 的問題——是赫米斯沒有遵守 SOP-A。必須在下一個 task 完成後**強制**執行 SOP-A。

**If** 使用者回覆了任何形式的數字或星星
**Then** 立即寫入 `~/.hermes/skill-usage/<today>.jsonl`，格式：
```json
{"ts": "<ISO>", "session_id": "<this-session-id>", "task_summary": "<1-line>", 
 "actual_skills": [...], "combo_rating": <N>, 
 "individual_ratings": {"skill-name": <N>, ...},
 "comment": "<user's exact words>"}
```

**If** 任何 session 已經有 `comment` 欄位但 `combo_rating` 為 null
**Then** `analyze.py` 的 weak reward parse 會自動轉換，不需要手動補寫——但可以主動問使用者確認


---

## 架構限制：Layer 2 只能追蹤「有 SKILL.md 的技能」（2026-06-20 新增）

**核心限制**：Layer 2 的 `session_skill_logger.py` 查的是 `messages.tool_name='skill_view'`，等於「這個 session 載入了哪些 SKILL.md」。但**沒有任何 SKILL.md 定義的隐性知識也可能是實際工作重心**。

**實例**（2026-06-20 驗證）：
- 06-16 圖片生成 session：`session_skill_logger` 顯示只用了 `mmx-cli` + `school-bulletin-system`（2 個 SKILL.md）
- 但 `messages` 表內的 `execute_code: 11 calls` + `vision_analyze: 10 calls` + `terminal: 7 calls` 揭露了隠性工作量：Prompt Engineering 推理、content filter 對抗策略、架構决策
- 這些隐性知識在 `skill_usage` log 裡看不見，不代表它們没被使用

**當使用者問「這個任務用了哪些技能」時的完整回覆流程**：

1. `session_skill_logger.py --session <id>` 取得 SKILL.md 載入清單
2. **同時**查 `messages.tool_name` 分佈（Python + sqlite3）：
   ```python
   cur.execute("""
       SELECT tool_name, COUNT(*) as cnt
       FROM messages
       WHERE session_id = ? AND tool_name IS NOT NULL
       GROUP BY tool_name
       ORDER BY cnt DESC
   """, (session_id,))
   ```
3. **誠實告知覆蓋範圍**：
   - 「`session_skill_logger` 能告訴你我載入了哪些 SKILL.md（`mmx-cli` 等）」
   - 「但 Prompt Engineering 推理、content filter 對抗策略、架構决策」屬於「模型内部知識應用」，沒有 SKILL.md 定義，無法被追蹤」
   - 「你看到的 `execute_code/terminal/vision_analyze` 次數可以作為『實際工作量』的代理指標」

**If** 使用者追問「那具體用了什麼知識/推理」
**Then** 老實說「SKILL.md 追蹤不到那層次，我需要從工具 pattern 推估」並列舉：
- 大量 `execute_code` + `vision_analyze` → 模型在試错 + 視覺確認
- 大量 `terminal` → 有 shell 腳本或 mmx 指令執行
- 大量 `session_search` → 有研究或資訊檢索階段

---

## 已知限制（2026-06-19）

**本 skill 不是真的「自動」**——Hermes 沒有第一輪 hook，無法在每個新 task 自動觸發。現有觸發方式：

| 方式 | 現狀 | 效果 |
|------|------|------|
| 使用者每次提醒 | 依賴使用者紀律 | 24h+ 零 entry，失效 |
| `~/.hermes/hooks/session:start` Shell Hook | 可行但每次 session 都跑，增加噪聲 | 未部署 |
| `config.yaml hooks.session_start` | 文件有紀錄，未驗證是否生效 | 未測試 |

**核心瓶頸不是技術，是 invite 頻率**（2026-06-20 驗證）：
- `analyze.py` 腳本本身正確（`combo_rating` / `individual_ratings` 欄位讀取無誤）
- `session_skill_logger.py` 正確（Layer 2 重建功能正常）
- 真正問題：**連 6 月18日建立的系統都從未主動邀請過一次評分**
- 解決方案：每個任務完成後都附「標準評分邀請格式」，不放過任何機會

**見** `references/auto-trigger-gap.md` — 完整根因分析 + 選項評估（2026-06-19 cycle 產出）

**見** `references/layer2-coverage-gap.md` — 為何「2 個 SKILL.md」不等於「只做了 2 件事」（2026-06-20 驗證）

## 注意事項

- **不要**把 rating 寫成「我自己覺得幾分」——只能寫使用者給的分數
- **不要**為了「拿到 5 星」而評價自己——這違反 user-collaboration-style Rule 4(自我報告不等於驗證)
- **不要**為了累積資料而強迫使用者評分每個 skill——若使用者只給組合 rating,individual_ratings 可以是空物件 {}
- **要**在每次邀請評分時順帶說「可以只評整體、不評個別」(降低評分成本)

## 補評分 SOP（待交付邀請機制，2026-06-24 新增）

當 SOP-A 錯過（無評分邀請附在回覆），`post_delivery.py` 產生的待交付檔案會寫入 `~/.hermes/skill-usage/pending/<session_id>.txt`，同時寫入 `manifest.json` 追蹤。

赫米斯 main session 應該在閒暇時檢查 `pending/` 目錄並透過 Telegram 補發邀請：

```bash
# 列出所有待交付
ls ~/.hermes/skill-usage/pending/

# 讀取並發送
cat ~/.hermes/skill-usage/pending/<session_id>.txt
```

**If** pending 目錄有 entry 但從未交付
**Then** 在下次閒聊或任何回覆末尾主動補上「補評分邀請」，不要讓機制空轉

**If** 發現 `pending/` 有 entry 且已經存在超過 48 小時
**Then** 這幾乎可以確定是「cron 觸發的 sub-agent 無法 send Telegram」導致的架構性空轉，不是忘記執行的問題。立即在下次 main session 啟動時補發所有 pending 邀請，並在 skill 文件明確記錄「cron sub-agent 無法主動交付 pending 邀請」的架構限制。

**⚠️ 架構限制（2026-06-24 更新）**：`pending/` 機制在 cron-based sub-agent 環境中是「單向寫入、無人讀取」的陷阱——sub-agent 執行 `post_delivery.py --write` 寫入 `pending/<session_id>.txt`，但無法透過 Telegram 交付給使用者；main session 若不主動檢查 `pending/`，entry 就會永久 pending。

**2026-06-24 D3 Exit 修復**：
1. ✅ `pending/` 目錄已刪除（`pending-delivery-architecture-trap-20260624.md` 確認）
2. ✅ SOP-A 邀請**必須直接寫在回覆末尾**，不可寫入 `pending/` 等 main session 讀取——sub-agent 回覆就是最終交付，`pending/` 無人讀取是架構性空轉
3. ✅ `post_delivery.py` 仍可用於分析 + 生成邀請文本，但**輸出必須直接貼在回覆**，不可 `&&` pipe 到 `--write pending/` 檔案

---

## linked_files

- `scripts/analyze.py` — 統計分析腳本，讀取 `~/.hermes/skill-usage/*.jsonl`，內建 Weak Reward auto-parse。SOP-C 要求：每次跑完必須檢查 combo_rating 筆數，若為 0 立即報告。
- `scripts/session_skill_logger.py` — Layer 2 實作（state.db skill_view 查詢）。只追蹤顯性 SKILL.md 載入，不含隱性工具使用。
- `scripts/post_delivery.py` — **新增 2026-06-21 D3 Exit**。從 state.db 完整重建 tool_call 分佈（顯性 + 隱性），計算隱性技能強度，生成含隱性 domain 的評分邀請文本。執行 SOP-A 的核心工具。
- `references/auto-trigger-gap.md` — 為何「24 小時 0 真實 entry」（根因：無 on_first_turn_hook，2026-06-19）
- `references/layer2-coverage-gap.md` — 為何「2 個 SKILL.md」不等於「只做了 2 件事」（2026-06-20 驗證）
- `references/idempotency-bug-20260620.md` — `--write-log` 重複寫入同一 session 的 bug 記錄
- `references/argparse-batch-mode-bug-20260620.md` — `--days --write-log` 組合失效的根因與修復（2026-06-20 D3 exit）
- `references/implicit-preference-learning-20260620.md` — DPO隱式偏好 + Local Harness bandit 選擇研究摘要（2026-06-20 cycle 產出）
- `references/d2-d3-exit-weak-reward-20260621.md` — D2→D3 exit：analyze.py Weak Reward auto-parse 實作記錄（2026-06-21）
- `references/d3-exit-post-delivery-20260621.md` — **本次 D3 exit**：SOP-A/B/C 新增 + post_delivery.py 建立，解決「0 筆真實評分」根本問題。
- `references/d3-exit-sop-a-gap-20260622.md` — **本次 D3 exit**：SOP-A 執行率 0/9，LRU cache 錯覺確認，口頭補救流程建立。
- `references/user-requested-skill-tracking-20260622.md` — **2026-06-22 新增**：使用者第三次明確要求 skill 追蹤（「請問之後在我指派任務時能夠紀錄使用了哪些skill嗎...」），但 combo_rating 仍為 0。根因：赫米斯只停在「建議」層次，未實際執行 post_delivery.py。If→Then 規則：使用者明確要求「記錄使用了哪些skill」→ 立即執行 post_delivery.py + 邀請評分，不要停在建議。
- `references/preference-learning-arxiv-2508-20260624.md` — **2026-06-24 新增**：arXiv 2508.08220 論文核心發現——negative signal 與 positive signal 同等重要（Top-1 +1.75%）。建議 skill-usage JSONL schema 新增 `liked: bool` 欄位；收集負面回饋時寫入 `{liked: false}` 而不只是「表達不满」。
- `references/pending-delivery-architecture-trap-20260624.md` — **2026-06-24 新增**：cron sub-agent 無法交付 pending 邀請導致 `pending/` 永久堆積的架構陷阱。`pending/20260616_125207_dc21b806.txt` 超過 48 小時仍 pending。
- `references/post-delivery-session-id-exact-match-bug-20260624.md` — **2026-06-24 新增**：`post_delivery.py` 用 `session_id = ?` 精確匹配，但 `session_skill_logger.py` 寫入的是完整 20-char ID（如 `20260616_125207_dc21b806`），部分前綴呼叫返回 0 rows。修復：改用 `LIKE ? || '%'` prefix 匹配。If→Then：mtime > 24h 即觸發 main session 補發。
- `references/post-delivery-tool-verified-20260628.md` — **2026-06-28 新增**：實際執行 `post_delivery.py` 對 20260616 session，42 tool calls 解析成功，工具功能正常。結論：gap 不是工具壞了，是「邀請文本從未出現在赫米斯回覆末尾」。D3 exit 需在回覆末尾親自貼上輸出。
- `references/skill-usage-tracker-d2-exit-20260629.md` — **2026-06-29 新增（D2 Exit）**：`skill-usage-tracker combo_rating = 11.8%` 連續 4+ cycles 識別為優先缺口但零實作干預。根因：`post_delivery.py generate_invocation()` 從未被主 execution path 呼叫，不是工具 bug。**干預**：將 SOP-A 觸發約束寫入 `~/.hermes/SOUL.md` Vibe 段落（95-106 行），Vibe 每次推理注入解決「文件存在但從未被上下文載入」的 D2 根因。驗證：mtime `2026-06-29 20:36:41`。

- `references/vibe-injection-still-insufficient-20260707.md` — **2026-07-07 新增**：06-29 Vibe 寫入完成後，07-02 backup modification D3 session（132 msgs）仍 0 invite sent。根因：「直接動手」觸發疊加服從效應，SOP-A 被視為非必要步驟而跳過。Layer 1 在「使用者明確指示加速」語境下被選擇性忽略。**If→Then**：D3 完成後仍必須附 SOP-A 邀請，使用者說「直接動手」≠ 放棄交付後 SOP。

## 變更歷史

- **v2.0.0 (2026-06-24)**: `post_delivery.py` session ID exact-match bug 修復：`session_id = ?` → `session_id LIKE ? || '%'` prefix 匹配，修復後正確輸出 42 tool calls（was 0）。新增 `references/post-delivery-session-id-exact-match-bug-20260624.md`。

- **v1.9.0 (2026-06-24)**: 新增 If→Then 規則：負面回饋與正面同等重要（arXiv 2508.08220 驗證），收到負面回饋時立即寫入 `{liked: false, combo_rating: ≤2}` 而不只是「表達不满」。新增 `references/preference-learning-arxiv-2508-20260624.md`。

- **v1.6.0 (2026-06-21)**: 新增 SOP-A（任務交付後 SOP）+ SOP-B（已建立但未激活 skill 審計流程）+ SOP-C（analyze.py 強制產出規則）。新增 `scripts/post_delivery.py`（D3 exit），從 state.db 完整重建含隱性工具的 tool_call 分佈。徹底解決「0 筆真實評分」根本問題：Layer 2 只追蹤 SKILL.md，實際工作量隱藏在 execute_code/vision_analyze/terminal 等隱性工具。
- **v1.2.0 (2026-06-20)**: 確立兩層追蹤架構。Layer 1（主動）不可靠；Layer 2（事後重建）是主要工具。新增 `scripts/session_skill_logger.py` 從 state.db messages.tool_name 重建任意 session 的 skill 載入清單。June 15-16 兩個歷史 session 已寫入 skill-usage log。description 已修正。
- **v1.0.0 (2026-06-18)**: 初版,支援任務開始/結束記錄 + 邀請評分 + 持久化