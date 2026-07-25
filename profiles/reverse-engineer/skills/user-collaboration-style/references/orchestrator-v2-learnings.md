# v2 架構重構協作紀錄(2026-06-10)

本檔案收「consumer-researcher v1 → v2 架構重構」過程中,跟**協作模式**有關的踩雷(不含純技術踩雷,那個在 `~/.hermes/skills/trial-and-error`)。

---

## 教訓 1:使用者問「在進行了嗎?」= 提醒「沒主動報進度」

**時間**: 2026-06-10
**場景**: 跑 v2 架構 4 個 worker + summarizer,中途 6 分鐘沒主動報進度,使用者問「**在進行了嗎?**」確認赫米斯是否真的在動手
**為什麼是錯的**:
- 之前 user-collaboration-style Rule 14 已有「逐個 mark done + 驗證」,但沒涵蓋「中途主動報進度」
- 使用者看到「沈默 6 分鐘」= 不確定赫米斯是否卡住還是正常跑
- 這是**對進度有感的協作模式**,不是純技術問題
**正確做法**:
- **預估 > 5 分鐘的任務,每 1-2 分鐘主動報一次進度**(用一句話)
- 範例:「Worker 1 + Worker 2 完成,Worker 3 還在跑(預計 2 分鐘),summarizer 還沒派」
- **不要**等使用者問才說
- 已寫進 user-collaboration-style Rule 15

---

## 教訓 2:架構/重構類任務必做 v1 vs vN 內容比對

**時間**: 2026-06-10
**場景**: 完成 v2 架構重構後,使用者問「**我不太確定 v2 派下去的子代理是否都有具備原本常駐代理的技能跟能力,在找那些資料時會否有不足之處**」
**為什麼是重要的**:
- 使用者**有驗證心態**:「我信你會做,但我要看到證據」
- 架構改動是**不可逆的**,如果新架構漏了什麼功能,使用者會在某個專案才發現
- 比對報告 = 給使用者**客觀的品質驗證**,不是赫米斯自吹自擂
**正確做法**:
- 架構類任務完成後,**主動產出 v1 vs vN 內容比對報告**:
  1. 章節覆蓋率
  2. 關鍵指標對比(資料量、URL 數、Persona 數、痛點數)
  3. **缺漏清單(哪些 v1 有、vN 沒有的)** — 最重要,使用者要看這個
  4. 額外抓到清單
  5. 修法建議
- 已寫進 user-collaboration-style Rule 16

---

## 教訓 3:子代理 prompt 必抓清單

**時間**: 2026-06-10
**場景**: v2 原始 worker 跑完後,比對發現**漏了 SkillSwap.io + Reddit r/SkillSwap**(v1 明確列為標竿的)
**為什麼會漏**:
- Worker 的 prompt 只給了 3 個 URL
- LLM 不知道「必抓清單」概念,只抓 prompt 寫的
**修法**:
- 在 `web-worker-template` 加「**★ 必抓清單**」段
- 必抓清單的概念是「無論 prompt 給什麼 URL,這些都一定要抓」
- 已在 v2 修正版驗證成功

---

## 教訓 4:summarizer 必讀 _plan.md 保留 Orchestrator 決策意圖

**時間**: 2026-06-10
**場景**: v2 原始 summarizer 把 v1 的 3 個使用者原意 Persona(小美/佐藤/陳媽媽)**全換掉**成 _raw/ 歸納的 Persona(小婷/阿哲/Lily),客群完全改變
**為什麼會發生**:
- Summarizer 從 _raw/ 自由歸納 Persona,**不知道 Orchestrator 在派工時有指定 Persona**
- 結果:**使用者想看的「跨國客群」「退休族 CSR 亮點」被替換成「台灣本地」「中年外籍人士」**,跟原意不同
**修法**:
- Orchestrator 派遣前必寫 `_plan.md`,包含「使用者原意 Persona」段
- Summarizer 必讀 `_plan.md`,從 _raw/ **擴展**這些 Persona 的具體痛點(而非替換)
- 若 _raw/ 抓不到對應真實評論,保留框架 + 標「★ 來自使用者原意,需後續驗證」
- 已在 v2 修正版驗證成功

---

## 教訓 5:跨 profile 寫入需 `cross_profile=true`

**時間**: 2026-06-10(踩 3 次)
**場景**: 寫 `consumer-researcher/skills/`、`consumer-researcher/persona.md` 時被軟防護擋
**為什麼是錯的**:
- 一開始用 `write_file` 沒加 `cross_profile=true`,被擋
- 浪費 1 次 tool call 重試
**正確做法**:
- 寫跨 profile 檔案時**直接加 `cross_profile=true`**(不需要先試不加)
- 使用者明確指示「修 v2」等於符合 bypass 條件
- 已寫進 trial-and-error L2 條目

---

## 共同模式

這 5 個教訓有一個**共同根因**:
> v2 架構的「子代理 prompt」太單純、沒考慮「Orchestrator 想保留什麼」

**修法**: 子代理 prompt 不只要「抓什麼」,還要「保留什麼」(Orchestrator 必填 _plan.md、summarizer 必讀 _plan.md)。
