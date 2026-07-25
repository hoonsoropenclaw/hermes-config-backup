# skill-usage-tracker 自動觸發缺口 — 根因分析（2026-06-19）

**2026-06-20 更新：Layer 2 事後重建已解決核心問題**
`session_skill_logger.py` 從 state.db 重建 skill 載入清單，不再依賴自覺觸發。
本文件的 Layer 1 根因分析仍有歷史價值，但 Auto-trigger Gap 已不再是阻塞問題。

## 問題（歷史）

使用者 2026-06-18 明確說「之後在我指派任務時能夠紀錄使用了哪些 skill」，skill-usage-tracker 當日建立。但截至 2026-06-19 15:07：
- `~/.hermes/skill-usage/` 只有 **1 筆 demo entry**，0 筆真實用戶任務
- `analyze.py` 輸出：「⚠️ 沒有任何 skill 累積到 ≥ 3 個評分」

**根本原因**：Hermes **沒有 `on_first_turn_hook` 機制**。

## 已知架構限制

GitHub Issue #31283（"Session startup hook: auto-load skill or run preflight on first turn"）確認：

> "Currently, skills are loaded manually via /skill or -s flag. There is no mechanism to automatically run a skill or preflight logic on every new session start."

## 三層 Hook 評估（歷史，仅供參考）

| Hook 系統 | 觸發時機 | 可否綁定「每任務必執行 skill-usage-tracker」 | 現狀 |
|-----------|---------|-----------------------------------------|------|
| **Gateway Hook** `~/.hermes/hooks/` | `session:start` | ❌ handler 是 Python，無法 inject skill load 進 agent 首輪 | 未部署 |
| **Shell Hook** `config.yaml hooks:` | 每個 message | ⚠️ 可行但每 session 都跑（噪聲大） | 未部署 |
| **Plugin Hook** `ctx.register_hook()` | tool call 時 | ❌ 設計用於攔截，non-blocking | N/A |

## 當前觸發依賴（歷史）

Skill 文件說「Always-on • 每個任務開始時主動 skill_view 一次」，但這依賴赫米斯**自覺遵守**。2026-06-18~19 的零 entry 證明自覺失效。

## 解決方案（已解決）

### 方案 A：Shell Hook 部署（過渡方案，已擱置）
```bash
# 在 config.yaml 加入：
hooks:
  session_start:
    - command: hermes skill run skill-usage-tracker
```
**優點**：真正自動化
**缺點**：每次 session 都觸發，包含使用者只是想「問一句」的簡單對話，噪聲大

### 方案 B：依賴使用者每次提醒（失效）
使用者每次一開始就說「請記錄 skill」，赫米斯才執行。缺點：不可靠。

### 方案 C：等待官方 feature（長期，已擱置）
追蹤 GitHub #31283，等待 `agent.on_first_turn_hook` 實作。

### 方案 D：Layer 2 事後重建（✅ 已實作，2026-06-20）

`session_skill_logger.py` 從 `~/.hermes/state.db` 的 `messages.tool_name='skill_view'` 記錄**重建**任意 session 的實際 skill 載入清單。

**為什麼靠譜**：
- state.db 是 Hermes 實際執行 tool call 的 ground truth，不依賴「自覺」
- 每次 `skill_view(X)` 都會寫入 messages.tool_name
- 不需要任何觸發條件，覆蓋所有歷史 session

**用法**：
```bash
# 列出最近 N 個 session
python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py --list-sessions 10

# 查詢並寫入 skill-usage log
python3 ~/.hermes/skills/skill-usage-tracker/scripts/session_skill_logger.py \
  --session 20260616_125207_dc21b806 --write-log
```

**驗證方式**：
```bash
# 檢查 skill-usage log 累積量
wc -l ~/.hermes/skill-usage/*.jsonl

# 檢查眞實 entry（非 demo session_id）
grep -v "demo" ~/.hermes/skill-usage/*.jsonl | wc -l
```

## 相關條目

- GitHub: NousResearch/hermes-agent#31283
- 支撐資料：Hermes Hook 文檔（hermes-agent.nousresearch.com/docs/user-guide/features/hooks）
- `scripts/session_skill_logger.py` — Layer 2 實作（state.db 查询）
