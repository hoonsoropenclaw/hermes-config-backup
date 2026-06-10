# Cycle Quantitative Analysis (週期量化自評)

> **新增日期**:2026-06-08
> **觸發時機**:每累積 100 個 cycle 後的下一個 cycle 自動跑一次,或被使用者明確要求時
> **核心目的**:把「產出量大」跟「真的學到了」分開,識別 5 大盲點

---

## 為什麼需要這個

108 個 cycle 跑下來,赫米斯本身**自我感覺**良好（格式 100% 達標、If→Then 平均 6 條/cycle、自我審查每個都有),但**真實狀態**卻是:

- **5% 明確空轉** (自承「無新發現」的 cycle)
- **30-40% If→Then 是同類議題重複生產**
- **D1 識字型學習佔 50%**,真的改架構 (D4) 只有 5%
- **驗證閉環率只有 20%** (從「找到問題」到「真的修復」)

**如果沒有量化指標**,這些盲點會被「成功產出格式 100% 達標」掩蓋。108 個 cycle 的產出看起來很豐富,但結構性進步的「水分」高。

---

## 量化指標 5 項

### 指標 1: 格式達標率

**定義**:每個產出段的出現率

```python
sections = {
    '## 學習摘要': 0,
    '## 自我審查': 0,
    '[TO_MEMORY]': 0,
    '## If→Then 經驗': 0,
    '## 對赫米斯現有 Skills 的建議': 0,
    '## Gap Identified': 0,  # SKILL 要求但 0% 出現
}
for f in files:
    for s in sections:
        if s in open(f).read():
            sections[s] += 1
print({s: f"{c}/{len(files)}" for s, c in sections.items()})
```

**108 cycle 結果**:
- 學習摘要、自我審查、TO_MEMORY = **100%** (形式達標)
- Gap Identified = **0%** (SKILL 要求未達標)

### 指標 2: Cycle 模式分布

**自動分類**(用學習摘要段的關鍵字):

```python
import re
type_label = "learning"
if re.search(r'緊急修復|回歸正常|critical|GH013|secret\s*leak', summary):
    type_label = "emergency_repair"
elif re.search(r'(?:已|已經).*(?:修復|實作|安裝|部署|建立|寫入|完成)', summary):
    type_label = "implementation"
elif re.search(r'無.*?新|沒.*?新|本(週期|次).*?無', summary):
    type_label = "empty"
elif re.search(r'識別.*?(?:缺口|技能|主題)|研究|聚焦', summary):
    type_label = "research"
```

**108 cycle 結果**:

| 模式 | 數量 | 佔比 | 說明 |
|------|------|------|------|
| implementation | 32 | 30% | 真的改了系統 |
| learning | 33 | 31% | 消化應用型 |
| research | 27 | 25% | 純研究新概念 |
| emergency_repair | 11 | 10% | critical/緊急 |
| empty | 5 | 5% | 明確無新發現 |

### 指標 3: 議題去重率

**問題**:同樣的「缺口主題」在多個 cycle 重複出現 → 代表「缺口識別」沒真正解決

**108 cycle 觀察**:
- 「Layer 2.5 SOP 驗收整合缺口」被識別 **5 次** (2026-05-31 16:38、22:42、2026-06-02 01:18、05:22、2026-06-03 01:50)
- 「沒有外部驗收的 self-improvement 是裝飾」被提及 **6 次**
- 「If→Then 規則」總計 643 條,SKILL 自己說「同領域不該超過 3-5 條」

**If 議題去重率 < 30%** (同樣缺口被識別 ≥ 3 次)
**Then** 觸發緊急自審

### 指標 4: 驗證閉環率

**定義**:「提到修復了 X」但下次 cycle 仍 error 的次數 / 總修復次數

**108 cycle 觀察**:
- 「Layer 2.5 整合缺口」5 cycle 識別 → **1 cycle 真實修復** → 閉環率 20%
- GH013 secret leak 修復 → 後續 cycle 確認 `ok` → 閉環率 ~80% (這算好)

**If 驗證閉環率 < 50%**
**Then** Phase 4 自我審查**必須**附「驗證命令 + exit code」,不接受純文字「已修復」

### 指標 5: trial-and-error 對應率

**問題**:赫米斯主體是否真的把 [TO_MEMORY] 寫進 trial-and-error skill?

**驗證方法**:
```python
# 比對每個 trial-and-error 檔案 mtime 跟最接近的 cycle mtime
for t_file, t_mtime in t_and_e_files.items():
    t_dt = datetime.fromisoformat(t_mtime)
    closest_cycle = min(files, key=lambda f: abs(...))
    # 接近程度 = 自動寫入的證據
```

**108 cycle 觀察**:
- 13 個 trial-and-error 檔案全部對應到某個 cycle
- mtime 差距範圍 1 分鐘 ~ 1 小時 53 分鐘
- 代表赫米斯主體**不是即時**寫入,而是「在後續對話」中處理 [TO_MEMORY] 才寫入

---

## 學習深度 4 等級 (D1-D4)

取代「產出量大就是學習好」迷思:

| 等級 | 描述 | 佔比 | 判斷 |
|------|------|------|------|
| **D1 識字型** | 知道新概念、無運作 | ~50% | 「學了但沒用」|
| **D2 整合型** | 識別缺口、提出整合方案 | ~25% | 「會想但沒動」|
| **D3 實作型** | 真的改代碼/配置/系統 | ~20% | 「真的做了」|
| **D4 結構型** | 改變赫米斯根本架構 | ~5% | 「真的改變系統」|

**108 cycle 真正的 D4 產出只有 1 個**:automated-sop-validation skill 從無到有 (2026-05-31 cycle 12 觸發實作)

---

## 108 cycle 真實結構性改進 (11 項 D3+)

| # | 改進 | 起始 cycle | 對應檔案 |
|---|------|------------|----------|
| 1 | automated-sop-validation skill 建立 | 2026-05-31 08:20 | `~/.hermes/skills/productivity/automated-sop-validation/` |
| 2 | SOP validator 雙軌模式 (AgentContract + FallbackValidator) | 2026-05-31 14:30 | 同上 |
| 3 | 修復 validator 從未被消費端呼叫的整合缺口 | 2026-05-31 16:38 | 同上 + 接入 cron |
| 4 | headless-cookie-import 技能 | 2026-06-01 00:43 | `~/.hermes/skills/trial-and-error/references/by-category/headless-cookie-import.md` |
| 5 | Camofox 環境變數標準化 | 2026-06-01 13:01 | trial-and-error |
| 6 | 24/7 自主憑證輪換機制 | 2026-06-01 21:13 | OLLAMA_WEB_SEARCH 處理 |
| 7 | 多模型路由 (Minimax 2.7/3/deepseek) | 2026-06-06 12:39 | multi-model-routing cheatsheet |
| 8 | GH013 secret leak 修復 | 2026-06-06 06:21 | 完整處理流程 |
| 9 | eval-sync 401 追蹤 (*** key mask) | 2026-06-08 09:53 | hermes-internal.md |
| 10 | backup-verification skill 建立 | 2026-06-07 10:03 | 觸發 hermes-backup-design-pitfalls v3 |
| 11 | Camofox 容器斷線 5 天自動偵測 | 2026-06-06 21:03 | cron job health monitor |

---

## 主題時序演進 (9 天學了什麼)

### Day 1-2 (2026-05-30 ~ 05-31): Layer 1/2/3 SOP 架構、automated-sop-validation 實作
- 「越用越聰明」失效的根因 = 沒外部驗收
- 實作了 automated-sop-validation skill (D4 等級)
- Reflexion 論文 (Stanford Shinn et al.) 研究:verbal self-reflection 在有 rubric 下從 58.3% → 78.2%

### Day 3 (2026-06-01): 多智能體協作、Camofox 設定、24/7 自主憑證
- Supervisor/Network/Hierarchical 三種多 agent 模式
- Camofox 環境變數標準化
- OLLAMA_WEB_SEARCH key 過期自動偵測

### Day 4 (2026-06-02): RAG、LangGraph/CrewAI/AutoGen、Ontology
- RAG 在學校行政的應用
- LangGraph state machine、CrewAI role-based、AutoGen 對話
- ontology skill 從 JSONL 升級

### Day 5 (2026-06-03): cron 失敗追蹤、yfinance+Plotly、Camofox VNC 黑畫面

### Day 6 (2026-06-04): 金融 Python 模式、HR 自動化、RAGAS/TruLens

### Day 7 (2026-06-05): nodriver、MiniMax-M3 vision、portal 401

### Day 8 (2026-06-06): GH013 修復、模型路由、Camofox 斷線
- GH013 secret leak 完整處理
- 多模型路由
- Camofox Docker 容器斷線 5 天自動偵測

### Day 9 (2026-06-07 ~ 06-08): status site 覆蓋、eval-sync 401、vercel 部署 skill 擴充

---

## 真實盲點 (給未來 metacognitive 改版用)

### 盲點 1: 重複生產同類知識
- 30-40% If→Then 是同類議題重複
- 議題去重機制弱 (同樣缺口識別 5 次)

### 盲點 2: 驗證閉環薄弱
- 從「找到問題」到「真的修復」閉環率只有 20%
- 緊急修復 cycle 跟 implementation cycle 沒有明顯追蹤連結

### 盲點 3: 使用者價值不可量化
- 「真實解決使用者痛點」的比例無法從 cycle 紀錄量化
- 沒有「使用者滿意度回饋通道」接到 metacognitive

### 盲點 4: 議題追蹤無 ID
- 每次 cycle 結論沒有議題 ID
- 7 天後無法統計「哪些議題真的解決了、哪些只是重複識別」

### 盲點 5: cron 跑了 ≠ 有產出
- cron `last_status: ok` 不代表有真實學習
- 需要比對 trial-and-error 增量

---

## 改進建議 (給未來 metacognitive 改版)

1. **加強「去重」**:Phase 1 缺口掃描前先比對「過去 7 天的 cycle 紀錄」,避免重複識別同樣的缺口
2. **加強「真實驗證」**:每個 implementation 類 cycle **必須**附「改了哪個檔、什麼 mtime、什麼命令的 exit code」
3. **加強「使用者價值導向」**:每 24 個 cycle 應該做一次「過去 24 個 cycle 學到的東西、真的被使用者用過幾次」的自評
4. **加強「議題追蹤」**:每次 cycle 結論應該標註「議題 ID」,7 天後可以統計
5. **改 cron 頻率**:從「every 120m」改成「every 4h」(減少無聊 cycle),但加強「真實觸發條件」(例如 Phase 1.5 發現 ≥ 1 個 cron error 才立刻跑)

---

## 量化自評的觸發 SOP (給未來 cycle)

### 觸發判斷
```bash
# 每次 cycle 開頭檢查
COUNT=$(ls /home/hoonsoropenclaw/.hermes/cron/output/6edfe1507888/ 2>/dev/null | wc -l)
if [ $((COUNT % 100)) -eq 0 ]; then
    echo "本 cycle 是第 $COUNT 個、執行量化自評"
    # 跑 Python 統計 (見下方腳本)
fi
```

### 完整 Python 統計腳本
```python
import os, re
from collections import Counter
from datetime import datetime

cycle_dir = "/home/hoonsoropenclaw/.hermes/cron/output/6edfe1507888"
files = sorted([f for f in os.listdir(cycle_dir) if f.endswith('.md')])

# 1. 格式達標率
sections = {
    '## 學習摘要': 0, '## 自我審查': 0, '[TO_MEMORY]': 0,
    '## If→Then 經驗': 0, '## 對赫米斯現有 Skills 的建議': 0,
    '## Gap Identified': 0,
}
for f in files:
    content = open(os.path.join(cycle_dir, f)).read()
    for s in sections:
        if s in content:
            sections[s] += 1

# 2. Cycle 模式分布
modes = Counter()
for f in files:
    content = open(os.path.join(cycle_dir, f)).read()
    summary = re.search(r'## 學習摘要\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
    summary = summary.group(1) if summary else ""
    
    if re.search(r'緊急修復|回歸正常|critical|GH013|secret\s*leak', summary, re.IGNORECASE):
        modes['emergency_repair'] += 1
    elif re.search(r'(?:已|已經).*(?:修復|實作|安裝|部署|建立|寫入|完成)', summary):
        modes['implementation'] += 1
    elif re.search(r'無.*?新|沒.*?新|本(週期|次).*?無', summary):
        modes['empty'] += 1
    elif re.search(r'識別.*?(?:缺口|技能|主題)|研究|聚焦', summary):
        modes['research'] += 1
    else:
        modes['learning'] += 1

# 3. 議題去重率 (手動或簡化版)
gap_keywords = Counter()
for f in files:
    content = open(os.path.join(cycle_dir, f)).read()
    summary = re.search(r'## 學習摘要\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
    summary = summary.group(1) if summary else ""
    # 找 5+ 個關鍵字代表「同議題」
    for kw in ['Layer 2.5', 'SOP 驗收', 'agentcontract', 'fallback', '外部驗收']:
        if kw in summary:
            gap_keywords[kw] += 1

# 4. 驗證閉環率 (簡化版: 找提到「修復」+「下次仍 error」)
# 需要比對 jobs.json last_error 歷史、這裡只給框架
fixes = []
for f in files:
    content = open(os.path.join(cycle_dir, f)).read()
    if re.search(r'(?:已|已成功).*?(?:修復|resolved|fixed)', content):
        fixes.append(f)

# 5. trial-and-error 對應率
t_and_e_dir = "/home/hoonsoropenclaw/.hermes/skills/trial-and-error/references/by-category"
t_and_e_files = [f for f in os.listdir(t_and_e_dir) if f.endswith('.md')]
correspondence = 0
for te_file in t_and_e_files:
    te_mtime = os.path.getmtime(os.path.join(t_and_e_dir, te_file))
    # 找最接近的 cycle
    closest_diff = min(
        abs(te_mtime - os.path.getmtime(os.path.join(cycle_dir, f)))
        for f in files
    )
    if closest_diff < 86400 * 7:  # 7 天內
        correspondence += 1

print(f"格式達標率: {sections}")
print(f"Cycle 模式分布: {modes}")
print(f"議題關鍵字出現: {gap_keywords}")
print(f"修復類 cycle 數: {len(fixes)}")
print(f"trial-and-error 對應率: {correspondence}/{len(t_and_e_files)}")
```

### 輸出格式

```markdown
## 量化自評報告 (第 N 個 cycle)

### 格式達標率
- 學習摘要: 100% (N/N)
- 自我審查: 100% (N/N)
- TO_MEMORY: 100% (N/N)
- If→Then 經驗: 84% (N/N)  ← 目標 ≥ 80%
- Gap Identified: 0% (0/N)   ← 警示: SKILL 要求未達標

### Cycle 模式分布
| 模式 | 數量 | 佔比 |
|------|------|------|
| implementation | 32 | 30% |
| learning | 33 | 31% |
| research | 27 | 25% |
| emergency_repair | 11 | 10% |
| empty | 5 | 5% |

### 學習深度 (D1-D4)
- D1 識字型: 50%
- D2 整合型: 25%
- D3 實作型: 20%
- D4 結構型: 5%  ← 目標 ≥ 10%

### 議題去重率 (Top 5 重複議題)
- 「Layer 2.5 整合缺口」: 5 次
- 「沒有外部驗收的 self-improvement 是裝飾」: 6 次
- ...

### 驗證閉環率
- 從「找到問題」到「真的修復」: 20%  ← 警示: 過低

### trial-and-error 對應率
- 13/13 (100%)  ← 良好

### 結論
- ✅ 良好: 格式、trial-and-error 對應
- ⚠️ 需改善: 議題去重、驗證閉環
- ❌ 失敗: Gap Identified 0%
```

---

## 自我審查:為什麼這個方法論有效

1. **量化比質化有說服力**:「30-40% If→Then 是重複」比「我覺得好像有點重複」有用
2. **可比較的基準線**:有了 108 cycle 的指標,未來 200 cycle 可以直接比對
3. **早期預警**:D1 > 70% 連續 3 次、驗證閉環率 < 50% 都是「系統快退化」的早期訊號
4. **觸發條件明確**:每 100 cycle 跑一次,不是看心情決定

**不該做的事**:
- ❌ 不要把量化指標變成 KPI 競賽 (赫米斯不是員工)
- ❌ 不要因為「數字好看」就放寬標準
- ❌ 不要忽略「D1 高但 D4 也高」的情況 (D4 高代表真的改變了架構,值得稱讚)
