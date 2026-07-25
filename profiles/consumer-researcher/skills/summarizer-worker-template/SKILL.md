---
name: summarizer-worker-template
description: |
  Summarizer Worker 模板 — 讀取 _raw/ 內所有 worker 輸出,做去重 + 分類 + 摘要,寫到 _summary.md。
  **特徵**:獨立 hermes session、嚴格大小控制(5-10 KB)、保留所有具體數字/URL/人名。
  **觸發關鍵字**:「summarizer」、「去重」、「合併摘要」、「_raw/ 整理」
risk: safe
source: hermes-internal
date_added: "2026-06-10"
last_updated: "2026-06-10"
---

# Summarizer Worker 模板

> **目的**:讀取所有 web-worker 的 _raw/ 輸出,做去重 + 分類 + 摘要,壓縮成 5-10 KB 的 _summary.md,給 Orchestrator 後續做 MoSCoW + Persona。

## 何時使用

- 所有 web-worker 派遣完成後
- 需要把多個 _raw/*.md 合併成單一可讀的摘要
- Orchestrator 需要做後續整合(避免讀 50K+ 的 _raw/ 原始資料)

## 不適用情境

- _raw/ 只有 1-2 個檔案(直接讀就好,不用 summarizer)
- Orchestrator 想要「原汁原味」的資料

## 核心設計原則

### 1. 嚴格大小控制
- **目標 5-10 KB**(不可超過 15 KB)
- 太大 → Orchestrator context 累積風險高
- 太小 → 丟失關鍵資訊

### 2. 去重是核心價值
- 多個 worker 可能抓到「同一個使用者抱怨」「同一個平台」
- summarizer 必須識別並合併,**只留最詳細的版本**
- 標記「出現次數」(例:Tandem 像 dating app 抱怨 4 次 → 標「高頻痛點 #4」)

### 3. 分類要明確
- 摘要結構按 Orchestrator 需求預先固定(標竿 / 消費者聲音 / Persona 素材)
- 不要重新組織、發明新分類

### 4. 保留所有具體細節
- ❌ 不要泛化「使用者不滿」
- ❌ 不要丟數字(「$5/月」不能改成「便宜的」)
- ❌ 不要丟 URL(每個事實都要附原始 URL)
- ✅ 但可以**壓縮敘述**

---

## Prompt 範本

```bash
hermes chat -q "$(cat <<'EOF'
你是 summarizer-worker。任務:讀取 _raw/ 目錄所有檔案,做去重 + 分類 + 摘要,寫到 _summary.md。

# 你的身份
- 獨立 hermes session
- **不繼承任何 persona / SOUL / skill**
- 只整理事實,不做分析、決策、建議

# 輸入
讀取以下目錄所有 .md 檔:
/home/<使用者>/.hermes/handoff/<slug>/_raw/

**步驟**:
1. 先讀取 `/home/<使用者>/.hermes/handoff/<slug>/_plan.md`(看 Orchestrator 有無指定 Persona 跟必抓清單)
2. 用 terminal `ls -la <目錄>` 看有幾個 _raw/ 檔案
3. 逐個 read_file 讀取
4. 做去重 + 分類 + 摘要
5. 寫到 `/home/<使用者>/.hermes/handoff/<slug>/_summary.md`

# 輸出目標
寫到 `/home/<使用者>/.hermes/handoff/<slug>/_summary.md`
**嚴格大小控制:5-10 KB(不可超過 15 KB)**

# 摘要結構(必須照這個)

```markdown
# <專案名稱> 消費者需求研究摘要

建立日期:YYYY-MM-DD
負責代理:summarizer-worker
來源:_raw/ 目錄內 <N> 個 worker 檔案
總原始資料:<N> KB
摘要後大小:<M> KB(壓縮比 <X>%)

---

## 1. 標竿分析摘要

### 直接標竿(<N> 個)— 必填,不可漏
| 標竿 | 類型 | 定位 | 客群 | 定價 | 最高頻 3 好評 | 最高頻 3 負評 | 來源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tandem | [直接] | ... | ... | ... | ... | ... | URL |
| HelloTalk | [直接] | ... | ... | ... | ... | ... | URL |
| SkillSwap.io | [直接] | ... | ... | ... | ... | ... | URL |
| 518 技能交換 | [直接] | ... | ... | ... | ... | ... | URL |

### 間接標竿(<N> 個)— 必填,不可漏
| 標竿 | 類型 | 為什麼列為間接 | 來源 |
| --- | --- | --- | --- |
| Reddit r/SkillSwap | [間接] | 證明「有需求但無好平台」 | URL |
| Facebook 技能交換社團 | [間接] | 自由度高但無平台規範 | URL |

### 跨領域典範(<N> 個)— 必填,不可漏
| 標竿 | 類型 | 為什麼列為跨領域 | 來源 |
| --- | --- | --- | --- |
| Airbnb | [跨領域] | 驗證「陌生人首次見面需要 3 層信任」 | URL |

### 功能矩陣表(核心)— 必填
| 功能 | 直接標竿 1 | 直接標竿 2 | 直接標竿 3 | 間接標竿 | 跨領域 | 消費者呼聲 |
| --- | --- | --- | --- | --- | --- | --- |
| 技能清單 + 想要技能標籤 | ... |
| 自動配對(基於互補技能) | ... |
| 身份驗證(防止假帳號) | ... |
| 時數點數/金流託管 | ... |
| ... |

---

## 2. 消費者聲音摘要(目標 20-30 則,分高/中/低頻)

### 2.1 高頻痛點(≥ 3 次)
| # | 痛點摘要 | 出現次數 | 來源統計 | 代表 URL |
|---|---------|---------|---------|---------|

### 2.2 中頻痛點(2 次)
### 2.3 低頻痛點(1 次,值得追蹤)

---

## 3. Persona 素材摘要(目標 3-5 個)

### ★ 重要:summarizer 必須保留 Orchestrator 在 _plan.md 內指定的「使用者原意 Persona」★

如果 Orchestrator 在 `_plan.md` 內有指定 Persona(例:使用者主動填的目標客群、或 v1 推測的 Persona),summarizer **必須**:
1. 把這些 Persona 列在前面
2. 從 _raw/ 抓的資料**擴展**這些 Persona(加具體痛點、現有替代方案、代表聲音)
3. _raw/ 內歸納的新 Persona 補充在後面

格式範例:
```markdown
### Persona 1:[名字]([職業])— ★ 使用者原意 Persona(來自 _plan.md)
- **人口統計**:[Orchestrator 在 _plan.md 提供的資料]
- **核心痛點**:
  - [從 _raw/ 抓的具體痛點 + URL]
  - [從 _raw/ 抓的具體痛點 + URL]
- **現有替代方案**:[從 _raw/ 抓]
- **代表聲音**:[URL 1]、[URL 2]

### Persona 2:[名字]([職業])— 從 _raw/ 歸納的新 Persona
... (同上)
```

如果 _plan.md 沒指定 Persona,summarizer 從 _raw/ 自由歸納 3 個。

---

## 4. 來源索引

| 編號 | URL | 來源類型 | 對應摘要段落 |
| --- | --- | --- | --- |
| 1 | <URL> | 標竿/聲音/Persona | §1.1 / §2.1 / §3.1 |
| 2 | ... | | |
```

# 硬性要求
- ✅ 嚴格大小控制(5-10 KB,不可超過 15 KB)
- ✅ 去重:多個 worker 抓到的相同內容,只留最詳細的 + 標出現次數
- ✅ **標竿分析必填「直接/間接/跨領域」三個分類**(2026-06-10 教訓)
- ✅ **功能矩陣表必填**(每個標竿 × 每個核心功能)
- ✅ **Persona 必須保留 Orchestrator 在 _plan.md 指定的原意 Persona**(2026-06-10 教訓)
- ✅ 分類:照上述 4 段固定結構
- ✅ 保留所有具體數字、URL、人名、平台名
- ✅ 每個事實都附原始 URL
- ❌ 不要做分析、決策、建議
- ❌ 不要新增原始 _raw/ 沒有的資訊

# 壓縮技巧
- 句子合併:把多個相似句子合併成一句
- 列表精簡:5 項類似的「使用者抱怨」→ 合併成 1 個總結 + 標出現次數
- 數字保留:不可省略具體數字

# 完成後
- 輸出 "DONE: <最終大小> KB"
- 失敗時輸出 `FAILED: <原因>`

開始執行。
EOF
)" --cli
```

---

## Orchestrator 端的銜接

```bash
# 1. 確認所有 web-worker 完成
ls -la ~/.hermes/handoff/<slug>/_raw/

# 2. 派遣 summarizer-worker
terminal(command="/path/to/summarizer.sh", background=true, notify_on_complete=true)

# 3. 等待完成
process(action='wait', session_id=summarizer, timeout=300)

# 4. 撈 _summary.md
read_file(path=~/.hermes/handoff/<slug>/_summary.md)

# 5. 驗證大小
wc -c ~/.hermes/handoff/<slug>/_summary.md
# 應該 5K-15K 之間
```

---

## 失敗處理

| 失敗模式 | 處理 |
| --- | --- |
| 摘要太大(> 15 KB) | 重跑,prompt 加「精簡到 5 KB」 |
| 摘要丟失關鍵資訊 | 重跑,prompt 強調「保留所有具體數字、URL」 |
| 摘要加入 _raw/ 沒有的內容 | 退回重跑,加「嚴格禁止 hallucination」 |
| summarizer 自己卡住 | Orchestrator 自己讀 _raw/ 整理(放棄 summarizer) |

---

## 預期效益

| 指標 | 無 summarizer | 有 summarizer |
| --- | --- | --- |
| Orchestrator 讀的資料量 | 50-100 KB | 5-15 KB |
| Orchestrator context 風險 | 高 | 低 |
| 資料整理時間 | 5-10 分鐘 | 3-5 分鐘 |
| 去重品質 | LLM 容易漏 | 專注做去重,品質高 |

---

## 相關檔案

- `web-worker-template` — 對應的「派遣單一爬蟲任務」skill
- `consumer-researcher/persona.md` — Orchestrator 7 步 SOP
- `_ARCHITECTURE_v2.md` — 完整架構設計文件
