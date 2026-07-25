# Handoff Chain Timeout SOP

**用途**：當 `^專案` handoff chain 派遣 sub-agent 時，預防 timeout + 監控過程。  
**觸發條件**：`^專案` 派遣任何 sub-agent（engineering-lead / system-architect / consumer-researcher 等）。

---

## 核心參數

| 參數 | 值 | 理由 |
|------|----|------|
| `timeout_seconds` | **1200s（20 分鐘）** | 600s 太短，sub-agent 升套件 + 整合 + 寫大檔會超時 |
| Monitor 間隔 | 300s（5 分鐘） | 4 次檢查 = 20 分鐘，完整覆蓋 timeout 上限 |
| 驗證命令 | `pgrep -f "<wrapper> chat"` | 確認 sub-agent PID 還活著 |

---

## 派遣標準命令

```bash
# 標準派遣（background + notify）
terminal(
  background=True,
  timeout=1200,
  notify_on_complete=True,
  command="hermes chat -q '...' --profile <profile> 2>&1 | tee /tmp/handoff-<slug>.log"
)

# 同時啟動 monitor（在另一個 terminal call）
terminal(
  background=True,
  timeout=1250,  # 比 agent timeout 多 50s
  command="~/.local/bin/handoff-monitor <slug> <wrapper> /tmp/handoff-monitor-<slug>.log"
)
```

---

## handoff-monitor 腳本使用方式

```bash
# 用法
handoff-monitor.sh <project-slug> <sub-agent-wrapper-name> [output-log]

# 例
handoff-monitor.sh school-bulletin engineering-lead /tmp/monitor.log

# 腳本位置：~/.local/bin/handoff-monitor
# 功能：每 5 分鐘檢查 sub-agent 是否活著、產出目錄是否有新檔
```

---

## Timeout 發生時的處理

**If** sub-agent timeout（1200s 到了但没完成）:
1. **不要**立刻重跑——先檢查 `handoff-monitor` log，看有沒有新產出
2. 如果有部分產出：主 session 接手，在現有基礎上繼續
3. 如果完全没產出：重新派遣，但先檢查上次的瓶頸在哪

**If→Then**: **If** sub-agent timeout 且 handoff dir 裡没有新檔 **Then** 上次問題是「根本没啟動」，檢查 wrapper 是否正確安裝 + `hermes chat` 是否可執行

---

## 為什麼 timeout 要 1200s

觀察記錄（2026-06-11）：
- engineering-lead 跑 600s 超時，實際需要 900-1100s
- 瓶頸：升套件（npm i） + 寫 architecture.md + 寫大量程式檔
- 600s = 10 分鐘，連 1 個 engineering-lead 都 Cover 不住

---

## 與 handoff-chain-acceptance-sop 的關係

- **handoff-chain-timeout-sop**（本檔）：派遣前如何設定 timeout + monitor
- **handoff-chain-acceptance-sop**：chain 跑完後如何對照 PRD 驗收

兩者**順序**：先 timeout 預防 → 再 acceptance 驗收

---

## 2026-06-11 學校網站案例

| 問題 | 教訓 |
|------|------|
| 600s 太短，engineering-lead 跑了 10+ 分鐘才發現超時 | timeout 要 1200s |
| 超時後没監控，不知道 sub-agent 是停了還是還在跑 | 同時跑 handoff-monitor |
| 來不及寫完 M-06/M-07/M-08（M-08 還直接放棄） | timeout 只是一環，根本問題是 PRD 範圍太大 |

**If** `^專案` 任務的 PRD 有 ≥ 9 個 Must **Then** 評估是否需要分段（每棒只做 3-4 Must），而不是一次丟給 engineering-lead
