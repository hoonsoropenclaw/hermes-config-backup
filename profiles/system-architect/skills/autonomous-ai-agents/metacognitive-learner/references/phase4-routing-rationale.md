# Phase 4 分流決策樹的設計理由

2026-06-06 session 修訂 Phase 4 時，補上這份 reference 解釋「為什麼這樣設計」，避免下次 metacognitive-learner cycle 看到決策樹卻不理解背後脈絡就 bypass 掉。

## 三個設計前提

### 前提 1：MEMORY.md 25KB 警戒線是 USER.md 訂的，不是任意值

USER.md「對話記錄保留原則」段落明文寫：

> 定期清理：MEMORY.md 超過 25 KB 時赫米斯主動建議掃一次、刪除過時條目

這個閾值的意義是：**MEMORY.md 是給赫米斯「啟動時一次讀完」的檔案**。赫米斯開新 session 時會把 MEMORY.md 整份塞進 context window。如果 MEMORY.md 膨脹到 25KB+，每次開新 session 都會多燒這麼多 tokens（即使這次 session 完全用不到那些內容）。

換言之：**MEMORY.md 裡的每 1KB 都是「赫米斯每次開 session 都要付的固定成本」**。這個成本結構跟 trial-and-error skill（按需 read_file）完全不同。

### 前提 2：trial-and-error skill 的存在改變了「L3 教訓該住哪」的最優解

2026-06-05 之前，L3 抽象教訓沒地方去，MEMORY.md 是唯一選擇——所以膨脹是必然結果。

2026-06-05 建立了 `trial-and-error` skill，有 7 個 by-category 分類檔：
- gpg-encryption.md
- gh-cli-and-github.md
- vercel-deployment.md
- python-sandbox.md
- secrets-and-env.md
- browser-automation.md
- hermes-internal.md

這個 skill 的設計是**症狀導向、按需讀取**——使用者問到 gpg 才讀 gpg-encryption.md，問到 Vercel 才讀 vercel-deployment.md。**完全沒有「開 session 就要載入」的成本**。

所以 2026-06-06 修訂 Phase 4 時，**L3 教訓的住處從 MEMORY.md 改到 trial-and-error skill 是 Pareto 改進**：
- 對 metacognitive-learner cycle：寫入位置語意更清楚（按工具分類）
- 對赫米斯開新 session：MEMORY.md 變輕，每次開 session 省 tokens
- 對 trial-and-error skill：內容更豐富，未來遇到類似症狀時可參考

### 前提 3：「單次任務結果」不該污染長期記憶

USER.md 寫：

> 不寫的東西：任務進度、已完成的工作、具體 PR/issue 編號、commit SHA、單次 session 結果、token 字串本身、機密內容
> 7 天內會過期的東西不入記憶

這條的邏輯是：**單次任務結果的價值是「現在回頭查」，不是「未來啟發」**。未來要查時用 `session_search`（FTS5 全文搜尋 SQLite session store），根本不需要存在 MEMORY.md。

## 分流決策樹的設計意圖

```
學習成果是什麼?
│
├─ L3 抽象教訓（可跨 session 複用、不綁特定任務）
│   └─ 進 trial-and-error skill 對應分類 ← 症狀導向、按需讀取
│
├─ 環境事實 / 架構決策 / 跨領域通用原則
│   └─ 寫進 MEMORY.md（必須 < 10 KB）← 啟動成本高，要斤斤計較
│
└─ 任務進度 / 單次 session 結果 / 7 天內過期資訊
    └─ 用 [TO_MEMORY] 區塊標記，由赫米斯主體決定是否收
       預設不進長期記憶（因為未來用 session_search 撈更划算）
```

這個三層結構的設計意圖：

**L3 進 trial-and-error**：症狀導向、未來遇到同症狀時可撈、有專屬分類維持秩序
**環境事實進 MEMORY.md**：因為是赫米斯**每天都需要**知道的（如 headless 無 keystore daemon），不能等到「症狀出現」才撈
**單次結果不進 MEMORY.md**：因為未來要查時 session_search 更快更準，避免把 MEMORY.md 當 session log 用

## 為什麼不直接全部丟進 trial-and-error？

直覺想法：既然 trial-and-error 那麼好用，連「環境事實」也丟進去好了。

不行。原因是：
- trial-and-error 是**症狀導向**——它的讀取觸發是「遇到症狀」
- 「環境事實」如「host 是 N100」是赫米斯**每天規劃 cron、寫工具腳本都要知道**的背景知識
- 把環境事實丟進 trial-and-error 會導致赫米斯在「症狀沒出現」時不知道這件事（如寫 cron 腳本時忘了 headless 限制）

所以 MEMORY.md 還是必要的，但只能放**每天都會用到的抽象背景知識**，量要精簡。

## 「MEMORY.md < 10 KB」這個目標怎麼來的

USER.md 寫的閾值是 25 KB（觸發清理），但 2026-06-06 清理後是 6 KB。

10 KB 這個 target 的計算：
- 25 KB / 2 = 12.5 KB（給清理留一倍 buffer）
- 6 KB（清理後現況）→ 還有 ~4 KB 空間可以新增環境事實
- 10 KB 是「再膨脹到這個值就該警覺」的中間值

**這不是硬限制，是 soft target**。如果某天真的有重要的跨領域決策原則要加，超過 10 KB 也沒關係——但要明確標記「為什麼這條必須在 MEMORY.md 而不是 trial-and-error」。

## 給未來 cycle 的提醒

如果你（metacognitive-learner sub-agent）看到這份 reference，代表：
- 你在跑的 cycle 已經是 2026-06-06 之後的版本
- Phase 4 決策樹已經是最新設計
- **不要**因為「MEMORY.md 看起來還有空間」就把 L3 教訓塞回去——這違背設計意圖
- **不要**因為「trial-and-error 寫起來比 MEMORY.md 麻煩」就偷懶——長期成本差很多

如果你發現決策樹有 bug 或缺漏（例如某個新類型既不適合 trial-and-error 也不適合 MEMORY.md），**不要默默 bypass**——在最終報告明確標記「分流決策樹需要擴充，建議新增 X 分類」。

## 變更歷史

- 2026-06-06：建立本 reference，記錄 Phase 4 決策樹的三個設計前提與意圖
