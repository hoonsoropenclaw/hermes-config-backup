# 「該建常駐 profile 還是單次派遣 subagent」決策樹

這是**最容易踩錯的判斷**，先用決策樹確認再動手。

## 觸發問題

使用者說了某個跟「代理、子代理、agent」有關的話，請用以下決策樹分流：

```
Q1: 這個代理是要跨 session 持續運作，還是只做一次？
│
├─ 跨 session 持續運作 ──→ 走 hermes-resident-agent skill（建 profile + tmux）
│   例：「建一個常駐策略代理」「長期監控 X 領域」「這個專案要有專人負責」
│
└─ 只做一次性任務 ──→ 用 delegate_task 工具
    例：「派遣一個 subagent 去看網站視覺」「派個瀏覽器代理去抓資料」「子代理幫我評分」

Q2: 這個代理有自己的 persona/技能/記憶庫需求嗎？
│
├─ 有（需要專屬身份、特定技能、隔離記憶）──→ 走 hermes-resident-agent skill
│
└─ 沒有（只是一個普通背景任務）──→ 用 delegate_task 工具

Q3: 這個代理的結果是給人看（互動），還是給程式接（自動化）？
│
├─ 給人看、需要互動 ──→ 走 hermes-resident-agent skill（用 `hermes -p <name> chat` 互動）
│
└─ 給程式接、要結構化輸出 ──→ 兩者皆可，但單次任務用 delegate_task 較輕量
```

## 對照表

| 特徵 | 常駐 profile | delegate_task subagent |
|------|-------------|------------------------|
| 生命週期 | 跨 session 持續 | 單次任務結束即銷毀 |
| 是否有 persona.md | ✓（必填） | ✗（用通用代理人設） |
| 是否有專屬 skill | ✓（可選但建議） | ✗（共享 default skills） |
| 是否有隔離記憶 | ✓（profiles/<name>/memories/） | ✗（共用 session 記憶） |
| 啟動方式 | `hermes -p <name> chat` 或 tmux gateway | `delegate_task(goal=...)` |
| 輸出 | 互動對話 + 寫入 handoff 共享區 | 回傳 summary 給父 session |
| 適用 | 專案經理、策略分析師、監控代理、QA 代理 | 視覺驗證、網站評分、單次資料蒐集 |

## 常見誤判

### 誤判 1：「派遣 subagent 去監控 X」

- **直覺**：以為是 `delegate_task` 派遣背景任務
- **正解**：監控是**跨 session 持續**的工作，應該建常駐 profile（如 `security-monitor`）+ tmux
- **判斷口訣**：持續 vs 一次性

### 誤判 2：「這個領域要有專家負責」

- **直覺**：以為是建常駐 profile
- **正解**：這要看「負責」是什麼意思
  - 「每個任務來都自動套這個領域的 SOP」→ 走**常駐 profile**
  - 「這次這個任務請領域專家做」→ 走**delegate_task 帶 context**

### 誤判 3：「幫我做一個代理」

- **直覺**：以為是建常駐
- **正解**：要問「是長期掛著？還是一次性？」
  - 長期 → 常駐 profile
  - 一次性 → delegate_task

## 判斷後的下一步

- 決定走常駐 → 載入 `hermes-resident-agent` skill，按 7 步流程建
- 決定走 delegate_task → 直接呼叫 `delegate_task(goal=..., context=...)` 工具

## 歷史教訓

- 2026-05-31 ~ 2026-06-08：曾有「派遣 subagent + 讀身份檔」方案，**介於常駐和單次派遣之間**，實作起來兩邊都不是，**已廢棄**。
- 2026-06-09：清理舊方案，新增本決策樹避免再混淆。
