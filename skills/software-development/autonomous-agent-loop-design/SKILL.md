---
name: autonomous-agent-loop-design
description: "When an autonomous agent loop is burning tokens by self-duplicating work (recurring spawn-loop, fixed-rate LLM consumption, same task re-run N times), diagnose the loop architecture, then redesign for accumulation instead of repetition. TRIGGER on signals like: minimax/api quota draining at fixed rate, `ps` shows long-running hermes chat sessions running the same task across multiple work_dirs, OS cron with high-frequency schedule (`*/5`, `*/10`) spawning LLM sessions, '200+ orphan learning_<timestamp>_<i> directories', 'same task done N times across multiple sessions with no carry-over'. Class is broader than cron — covers kanban workers, scheduled sub-agents, autonomous learners, recursive taskers."
version: 0.1.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [autonomous-loop, spawn-loop, token-economy, architectural-redesign, self-recursive-agent, work-dir-design]
    triggers: [fixed-rate token drain, SYSTEM_HEARTBEAT, autonomous spawn loop, 孤兒目錄, 自我重複 spawn, recursive LLM worker]
    related_skills: [cron-job-health-monitor, systematic-debugging, trial-and-error]
---

## Umbrella relationship (2026-08 curator pass)

Autonomous loop design is the persistence/dedup subsection of agent orchestration. Combine it with resident-profile and Kanban lifecycle work when needed; dated spawn incidents remain experiential references in `trial-and-error`.



當赫米斯（或其他 LLM agent）進入「**週期性 spawn 沒有 persistent memory 的 session**」的模式時，會以**固定速率**消耗 token、把同一件事重做 N 輪、留下大量孤兒成品。本技能提供診斷三層根因 + 重設計 5 元素 + 驗證清單。

## 何時使用

- minimax / OpenAI / Anthropic 額度以**固定速率**被消耗（不是突波、不是手動操作）
- `ps -eo etime,cmd | grep hermes chat` 顯示多個 session 跑同一類任務、跑很久不退出
- `~/.hermes/projects/learning_*/` 出現 100+ 個孤兒目錄（每次 spawn 都建新目錄）
- OS crontab 有 `*/5` / `*/10` 高頻排程、spawn 出新 LLM session
- agent 結尾自我承認「已內化」某個踩坑 → 下一個 session 不讀這段、又踩一次
- spawn 出來的 prompt 含「自主學習」「自主決策」「不問人類」「自己做主」等鼓勵無限 retry 的詞彙

## 三層根因框架（診斷）

任何「固定速率額度消耗」的真凶都落在這三層之一（或疊加）：

### L1 表面 — 監測與觸發失控
**症狀**：cron 排程頻率過高、或 spawn 邏輯沒有上限。
**檢測**：
```bash
crontab -l | grep -v '^#' | grep -E 'spawn|heartbeat|learn|worker'
ps -eo pid,etime,cmd | grep -E 'hermes chat|hermes.*--yolo' | grep -v grep
```

### L2 結構 — Session 間無記憶
**症狀**：spawn 出來的每個 session 是**完全 fresh context**、不知道上輪踩過什麼、不知道已有哪些 helper script、不知道上輪寫到一半的程式碼在哪。
**檢測**：
```bash
ls -d ~/.hermes/projects/learning_* | wc -l  # 100+ = 嚴重
grep -l "<同樣的任務>" ~/.hermes/projects/learning_*/local.log | wc -l  # 同類任務重複輪數
# 如果 ≥ 3 → 確認 spawn 設計有問題
```

### L3 哲學 — 「燒 token」被當成目標
**症狀**：spawn 邏輯裡的決策 prompt 明確鼓勵「burn tokens」「max capacity」「maintain high pace」——把消耗當成目的。
**檢測**：
```bash
# 找 spawn 源頭 script
grep -rl "burn tokens\|燒 token\|be aggressive" ~/.hermes/*.py ~/.hermes/scripts/
```

**為什麼三層都要查**：L1 修了好比「把漏水的水龍頭關小」、L2 修了好比「在水龍頭下放個桶」、L3 修了好比「換掉漏水的水龍頭」。只修一層會留下另兩層的浪費。

## 重設計 5 元素（從教訓 39 歸納）

如果確認是 spawn 自我重複模式，spawn 系統必含這 5 個元素（缺一就會自我重複）：

### 1. work_dir 持久化（topic-based，不時間戳）
**原則**：同 topic → 同 work_dir；不同 topic → 不同 work_dir。
```python
# ❌ 錯：每次都建新目錄、同 topic 重複 spawn 在不同目錄、無法累積
work_dir = f"/.../learning_{timestamp}_{i}"

# ✅ 對：topic hash 決定固定目錄
import hashlib
def get_or_create_work_dir(topic: str, idx: int = 0) -> str:
    topic_hash = hashlib.sha256(topic.strip().lower().encode("utf-8")).hexdigest()[:12]
    safe_topic_slug = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]", "_", topic)[:16]
    base = f"{PROJECTS_DIR}/learning_{safe_topic_slug}_{topic_hash}"
    return f"{base}_{idx}" if idx > 0 else base
```
**驗證**：第二次呼叫同 topic 應回傳同路徑（`os.path.exists(work_dir)`）。

### 2. Memory file（必讀 + 必寫）
**結構**：
```markdown
# 任務：<topic>

## 完成狀態
- 最後更新：<YYYY-MM-DD HH:MM>
- 完成階段：<0=未開始 / 1=進行中 / 2=完成 / 3=timeout>

## 已完成的子任務
- <子任務 1>（<時間>）
- <子任務 2>（<時間>）

## 踩坑清單（下次必讀）
- <坑 1>：症狀 → 解法
- <坑 2>：症狀 → 解法

## 下次接續點
- <未完成的工作>

## 產出物清單
- <檔案路徑 + 用途>
```
**Spawn prompt 必含**：
```
1.5 【跨 session 記憶】：請先 read_file 讀取 <memory_path>（若存在），
     從中接續，不要從零開始。
3.5 【memory 寫入義務】：本 session 結束前，必用 write_file 更新 <memory_path>
     （append-only，不要覆蓋既有內容），寫入這次完成的子任務 + 新踩的坑。
```

### 3. Dedup gate（spawn 前檢查）
**原則**：同 topic 24 小時內已完成 → 跳過。
```python
def is_topic_recently_completed(topic: str, hours: int = 24) -> bool:
    mem_path = get_memory_path(topic)
    if not os.path.exists(mem_path):
        return False
    content = open(mem_path).read()
    m_update = re.search(r"最後更新[：:]\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2})", content)
    m_stage = re.search(r"完成階段[：:]\s*(\d)", content)
    if not (m_update and m_stage):
        return False
    last_update = datetime.strptime(m_update.group(1).replace("T", " "), "%Y-%m-%d %H:%M")
    stage = int(m_stage.group(1))
    return stage in (2, 3) and (datetime.now() - last_update) < timedelta(hours=hours)
```
**驗證**：寫入 memory 後呼叫 `is_topic_recently_completed` 應回傳 True。

### 4. Spawn 上限（硬編碼，不要靠 LLM 動態決策）
**原則**：max_running_count 必是**保守**的數字（如 2），不要 5/10/20。
```python
# ❌ 錯：靠 LLM 動態決定、prompt 鼓勵「max capacity」
max_running_count = strategy.get('max_running_count', 5)  # LLM 想 spawn 20 個

# ✅ 對：硬編碼上限、LLM 只能在這個範圍內微調
max_running_count = strategy.get('max_running_count', 2)  # 永遠 ≤ 2
```
**為什麼**：LLM 看到「high quota」會傾向「burn more」，把上限交給 LLM 等於放任。

### 5. 「燒 token」語氣改成「聰明用 token」
**原則**：spawn 決策 prompt 應鼓勵「**quality over quantity**」、**dedup**、**accumulation**，不是「aggressive」「burn」。
```diff
- f"Rules:\n"
- f"1. If quota > 90%, you MUST be extremely aggressive to burn tokens! Launch max capacity."
+ f"Rules (EFFICIENCY-FIRST, NOT BURN-FIRST):\n"
+ f"1. If quota > 90%, you should still be productive but NOT waste tokens. Launch moderate. Quality over quantity."
+ f"5. CRITICAL: The system already filters out topics completed in the past 24 hours. DO NOT regenerate them."
```

## 動手前 SOP（5 步）

1. **備份**：`cp <spawn_script> /tmp/<name>.bak.$(date +%s)`
2. **建目錄**：`mkdir -p ~/.hermes/agent_memory`
3. **加 helpers**：5 個 helper functions（`get_topic_hash`、`get_or_create_work_dir`、`get_memory_path`、`is_topic_recently_completed`、`_scan_recent_completed_topics`）
4. **改 spawn 主邏輯**：work_dir、prompt、max_limit 三處
5. **dry-run 測試**：寫 `/tmp/test_<name>_dryrun.py`、跑 9 個 unit test、確認通過後再恢復 cron

## 驗證命令

```bash
# 1. 確認 spawn 源頭已改
diff <backup> <current> | head -50

# 2. dry-run 測試（不真的 spawn、只測邏輯）
python3 /tmp/test_<name>_dryrun.py
# 預期：9/9 通過

# 3. 確認 cron 還是註解狀態（避免誤觸發）
crontab -l | grep -v '^#' | grep <spawn_script>
# 應為空

# 4. 想真的測 → 手動跑一次（10 分鐘內觀察 token 消耗）
python3 <spawn_script>
# 應：max_running_count 套用新值 + dedup gate 跳過已知完成 topic

# 5. 正式恢復 cron
crontab -e  # 把註解取消
```

## 反例（不要做的事）

- ❌ 只 kill 當前 session（10 分鐘內會被重 spawn）
- ❌ 只暫停 `hermes cron list` 裡的 job（OS cron 不在裡面）
- ❌ 把 spawn 源頭 script 刪掉（保留以便未來「改設計後重新啟用」）
- ❌ 把 spawn 頻率從 `*/10` 改成 `*/60`（治標、L2 結構問題沒解決、還是會自我重複）
- ❌ 改 work_dir 命名但不改 dedup（半套解、仍會重複 spawn）

## 觀察案例（2026-08-04）

| 指標 | 數值 | 備註 |
|------|------|------|
| 跑的 session 數（3 天內） | ~100 個 | SYSTEM_HEARTBEAT 累積 |
| 留下的孤兒目錄 | 200+ | `~/.hermes/projects/learning_*` |
| 最終成功的成品 | 1 個 | 最後一輪 Playwright 套件 |
| **有效產出比** | **~1%** | 99% token 完全沒產出學習價值 |


## Deduplication boundary

The loop redesign rules are intentionally reusable across cron, Kanban, resident agents, and scheduled workers. Do not fork this skill for a new scheduler, model, or project; add the scheduler-specific probe or fixture under `scripts/` or `references/`.


- `cron-job-health-monitor` — 偵測 + 停止（本技能假設你已經抓到兇手）
- `systematic-debugging` — Phase 4 step 5「3 次失敗 = 問架構」正好對應本技能的「spawn 設計哲學錯誤」
- `trial-and-error` — 教訓 39（spawn 自我重複 = token 自殺模式）的完整記載
