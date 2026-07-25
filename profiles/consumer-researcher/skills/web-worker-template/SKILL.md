---
name: web-worker-template
description: |
  Web Worker 模板 — 給 consumer-researcher Orchestrator 用的「單一任務爬蟲」prompt 範本。
  **特徵**:獨立 hermes session(context 隔離)、只整理事實不做分析、寫到指定 _raw/ 路徑就結束。
  **使用情境**:consumer-researcher 拆分大型研究任務給多個 worker 平行執行。
  **觸發關鍵字**:「派遣 web-worker」、「分頭抓」、「平行爬」、「邊抓邊整」
risk: safe
source: hermes-internal
date_added: "2026-06-10"
last_updated: "2026-06-10"
---

# Web Worker 模板

> **目的**:給 consumer-researcher (Orchestrator) 用,派遣**獨立 hermes session** 跑單一爬蟲任務,避免主 session context 累積爆掉。

## 何時使用

- consumer-researcher 接到大型研究任務(>10 個 URL 要抓)
- 任務可拆分為多個獨立子任務
- 需要平行執行(節省時間)
- 預期單一任務會消耗大量 context(>50K)

## 不適用情境

- 單一 URL 或簡單搜尋(直接讓主 session 跑就好)
- 需要 LLM 深度推理的任務(worker 沒 persona,只做整理)
- 涉及帳號登入 / 表單互動的任務(用 browser skill 比較好)

## 核心設計原則

### 1. 獨立 session、context 隔離
- 每個 worker 跑**獨立的 hermes chat session**
- 用 `hermes chat -q "..." --cli`(不是 `-p consumer-researcher`)
- 不繼承任何 persona / SOUL / skill 庫
- **每個 worker 的 LLM context 完全隔離**(主 session 不會被污染)

### 2. 只整理事實、不做分析
- Worker 的 prompt 必須明確寫「**不要分析、不要總結、不要給建議**」
- Worker 只做:抓 → 整理成結構化 markdown → 寫檔
- 分析、洞察、決策是 Orchestrator 的工作

### 3. 寫到 _raw/ 就結束
- Worker 完成後**只輸出 "DONE"**,不傳詳細結果給主 session
- Orchestrator 用 `cat` / `read_file` 撈檔案
- 避免主 session context 累積 worker 的中間輸出

### 4. 失敗要明確
- Worker 失敗時輸出 "FAILED: <原因>"
- Orchestrator 看到 FAILED 才需要手動介入
- 不要讓 worker 假裝成功(寫空檔案、回 "完成" 但實際沒抓到)

---

## Prompt 範本

### 範本 A:標竿分析 worker

```bash
hermes chat -q "$(cat <<'EOF'
你是 web-worker。**標竿分析**任務:從 <N> 個 URL 抓取內容,每個 URL 整理成結構化 markdown。

# 你的身份
- 你是獨立 hermes session,**不隸屬任何 profile**
- 你**不繼承任何 persona / SOUL / skill**
- 你**只整理事實,不做分析、總結、建議**
- 你的工作完成後**只輸出 "DONE"**

# 任務
<任務描述>

# ★ 必抓清單(2026-06-10 教訓:這些標竿是 consumer-needs-research 的核心覆蓋,不能漏)★

**直接標竿(語言交換類)**:
- Tandem(https://actualfluency.com/tandem 或 tandem.io)
- HelloTalk(https://www.fluentu.com/blog/reviews/hellotalk 或 hellotalk.com)
- 任何 Reddit r/languagelearning 評論

**直接標竿(技能交換類)**:
- **SkillSwap.io(https://skillswap.io)— 必抓,英文技能交換代表**
- **Reddit r/SkillSwap(https://www.reddit.com/r/SkillSwap/)— 必抓,社群代表**
- **Reddit r/skilltrade(https://www.reddit.com/r/skilltrade/)— 必抓**
- 518 熊班台灣技能交換(https://www.518.com.tw/article/2253)

**間接標竿**:
- Facebook 語言交換/技能交換社團(搜尋結果)
- 其他 Reddit 子版(r/SeriousLangExchange 等)

**跨領域典範**:
- Airbnb 信任機制(身份驗證、雙盲評價、金流託管)

如果任務指定的 URL 不包含上述必抓,**主動用 web_search 補抓**,不要因為 prompt 沒列就跳過。

# 來源 URL
1. <URL 1>
2. <URL 2>
3. <URL 3>

# 每個 URL 整理的欄位
- 基本資料(名稱/定位/客群/定價/上線時間)
- 核心功能清單(已實作/部分實作/未實作,至少 10 項)
- 使用者評價(評分 + 最高頻 3 個好評 + 3 個負評)
- 來源 URL
- **標竿類型標記**:[直接]/[間接]/[跨領域]

# 輸出格式
寫到 **絕對路徑** `/home/<使用者>/.hermes/handoff/<slug>/_raw/worker-<編號>.md`

# 硬性要求
- ✅ 用絕對路徑 `/home/<使用者>/.hermes/handoff/...` 寫檔
- ✅ 用 `web_search` / `web_extract` 抓資料
- ✅ 必抓清單內的標竿**不可漏**(除非搜尋明確找不到)
- ✅ 每個標竿**標記類型**[直接]/[間接]/[跨領域]
- ✅ 完成後**只輸出 "DONE"**,不要貼詳細結果
- ❌ 不要做分析、總結、建議
- ❌ 不要新增 worker 沒抓到的資訊
- ❌ 失敗時輸出 `FAILED: <原因>`,不要假裝成功

開始執行。
EOF
)" --cli
```

### 範本 B:消費者聲音 worker

```bash
hermes chat -q "$(cat <<'EOF'
你是 web-worker。消費者聲音抓取任務:從 <N> 個 Reddit 看板 / PTT / 應用商店評論抓真實抱怨/需求。

# 你的身份
- 獨立 hermes session
- 只整理事實,不做分析

# 任務
抓取 <N> 則消費者真實聲音(抱怨/需求/痛點),每則含:
- 原文擷取(關鍵 1-2 句)
- 來源 URL
- 來源平台(Reddit / PTT / Dcard / App Store / Product Hunt)
- 提煉的「潛在功能需求」([功能名稱]:[為什麼需要])
- 痛感(高/中/低)
- 頻率標記(這則是不是同類議題的第 N 次出現)

# 來源
- Reddit 子版:r/<subreddit 1>、r/<subreddit 2>
- PTT 看板:<看板>
- App Store 評論:搜尋「<app name> review」找 1-3 星評論

# 輸出格式
寫到 `/home/<使用者>/.hermes/handoff/<slug>/_raw/worker-<編號>.md`

# 硬性要求
- 至少抓 <N> 則
- 同類議題**標註頻率**
- 完成後輸出 "DONE"
- 失敗時輸出 `FAILED: <原因>`

開始執行。
EOF
)" --cli
```

---

## Orchestrator 端的派遣 SOP

```bash
# 1. 規劃 worker 任務清單
cat > ~/.hermes/handoff/<slug>/_plan.md << 'EOF'
# Worker 派遣計劃
- Worker 1: 3 個直接標竿(Tandem / HelloTalk / 518)
- Worker 2: 1 個跨領域典範(Airbnb 信任機制)
- Worker 3: 15 則消費者聲音(Reddit r/languagelearning)
- Worker 4: 15 則消費者聲音(Reddit r/SkillSwap + 應用商店評論)
EOF

# 2. 平行派遣
terminal(command="/path/to/web-worker-1.sh", background=true, notify_on_complete=true)
terminal(command="/path/to/web-worker-2.sh", background=true, notify_on_complete=true)

# 3. 監聽所有 worker
process(action='wait', session_id=worker-1, timeout=600)

# 4. 撈所有 _raw/ 檔案
ls -la ~/.hermes/handoff/<slug>/_raw/
```

---

## 失敗處理

| 失敗模式 | 處理 |
| --- | --- |
| Worker 輸出 FAILED | 在主 session 重試;若還是失敗,跳過該 worker |
| Worker 寫到 sandbox 隔離目錄 | 用 `find ~/.hermes -name "worker-*.md"` 找實際位置,再 `mv` |
| Worker 寫空檔案 | 視為失敗,重試 |
| Worker 寫出非預期格式 | Orchestrator 自己讀 + 整理格式 |

---

## 預期效益

| 指標 | v1 單體 | v2 + web-worker |
| --- | --- | --- |
| 主 session context | 108K(爆) | 30-50K(可控) |
| 單一 worker context | N/A | 5-30K(隔離) |
| 總執行時間 | 10 分鐘(序列) | 5-7 分鐘(平行) |
| 失敗容錯 | 整個失敗 | 單一 worker 失敗可重試 |

---

## 相關檔案

- `summarizer-worker-template` — 對應的「讀 _raw/ 寫 _summary.md」skill
- `consumer-researcher/persona.md` — Orchestrator 7 步 SOP
- `_ARCHITECTURE_v2.md` — 完整架構設計文件
