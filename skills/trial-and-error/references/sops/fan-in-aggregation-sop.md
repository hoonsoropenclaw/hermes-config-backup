# Fan-In 結果彙整 SOP

> **目的**：當 N 個平行 worker 完成後，Orchestrator 如何安全地彙整結果、檢測失敗、處理衝突。
> **依賴**：`orchestrator-worker-architecture` skill（Fan-Out/Fan-In 失敗模式表）
> **觸發**：任何使用 `delegate_task(tasks=[...])` 或 `terminal(background=true)` 平行派遣 2+ workers 的任務

---

## 決策樹：選哪種彙整策略？

```
抵達 Fan-In 節點，Worker 結果已就緒。

任務類型是什麼？

├─ 事实类蒐集（各自獨立，無衝突）
│   └─ Strategy A：LLM Synthesis（可接受，但須先驗檔）
│
├─ 多视角分析（結果可能衝突）
│   └─ Strategy B：列點 + 衝突標記 + Orchestrator 裁決
│
└─ 投票/评分类（可量化）
   └─ Strategy C：投票或加權平均，不走 LLM synthesis
```

---

## Strategy A：事實蒐集（LLM Synthesis）

### 步驟

**Step 1：驗證所有 expected 檔都存在且非空**

```bash
# 在 _raw/ 目錄驗
ls -la ~/.hermes/handoff/<slug>/_raw/

# 每個檔大小 > 100 bytes
wc -c ~/.hermes/handoff/<slug>/_raw/worker-*.md

# 若有任何檔消失或為 0 → 該 worker 失敗
```

**Step 2：計算實際結果數**

```python
import os
raw_dir = Path("~/.hermes/handoff/<slug>/_raw/").expanduser()
worker_files = sorted(raw_dir.glob("worker-*.md"))
expected_count = N  # 派遣時預期的 worker 數
actual_count = len(worker_files)
if actual_count < expected_count:
    missing = expected_count - actual_count
    print(f"⚠️ {missing} worker(s) failed — do NOT proceed to synthesis")
    # 進入 partial failure 處理
```

**Step 3：LLM Synthesis**

prompt 必須明確區分「事實」vs「意見」，要求 LLM 保留所有來源。

```bash
hermes chat -q "$(cat <<'EOF'
你是結果彙整專家。任務：讀取以下 N 個 worker 結果檔，合併成一份結構化報告。

# 結果檔
{worker_files_list}

# 嚴格規則
1. 只合併事實（數字、URL、功能清單），不創造新事實
2. 每個聲稱必須標明來源檔
3. 若多個 worker 對同一事實描述不一致，**保留差異**（不要和稀泥）
4. 發現衝突時明確標記：[CONFLICT: worker-X 說...，worker-Y 說...]
5. 不要假裝衝突不存在

# 輸出格式
## 合併事實清單
## 衝突記錄（若有的話）
## 來不及完成的（若有的話）

大小限制：10 KB 以內
EOF
)" --cli
```

---

## Strategy B：多視角分析（衝突預期）

### 額外步驟

**Step 1-3 與 Strategy A 相同（驗檔、算數）**

**Step 4：列點 + 衝突標記**

```bash
hermes chat -q "$(cat <<'EOF'
你是結果彙整專家。多視角分析任務，每個 worker 代表一個視角，**不要和稀泥**。

# 結果檔
{worker_files_list}

# 嚴格輸出格式（全部必填）
## 視角矩陣
| 問題/面向 | worker-1 結論 | worker-2 結論 | worker-3 結論 |
|-----------|--------------|--------------|--------------|
（逐行列點）

## 衝突點清單
1. [CONFLICT] <問題>: worker-X 主張 <A>，worker-Y 主張 <B>
2. ...

## 無衝突共識
1. <共識點>

## 待裁決（証據不足）
1. <無法決定的點>

大小限制：8 KB 以內
EOF
)" --cli
```

**Step 5：Orchestrator 裁決**

Orchestrator 根據使用者意圖 + _plan.md 指定的優先策略，做最終裁決：

```
裁決原則（在 _plan.md 預先定義）：
- 優先採用：最新時間戳 OR 指定 worker（e.g., worker-1 為主）
- 裁決方式：[CONFLICT] 逐項說明「為何選 A 而非 B」
- 若無法裁決：明確標記「留待使用者決定」，不偽裝共識
```

---

## Strategy C：投票/评分类

### 步驟

**Step 1-2 與 Strategy A 相同**

**Step 3：結構化提取 + 投票**

```bash
hermes chat -q "$(cat <<'EOF'
你是結構化提取專家。每個 worker 對同一組選項評分/投票。

# 結果檔
{worker_files_list}

# 任務
1. 從每個 worker 檔提取評分/投票結果（轉為結構化數字）
2. 計算每個選項的：
   - 得票數 / 平均分
   - 標準差（衡量分歧程度）
3. 輸出投票矩陣

# 輸出格式
## 評分結果
| 選項 | worker-1 | worker-2 | worker-3 | 平均 | 標準差 |
|------|---------|---------|---------|------|------|
（逐行）

## 共識（標準差 < 0.5）
## 分歧（標準差 >= 0.5，需裁決）

大小限制：5 KB 以內
EOF
)" --cli
```

---

## Partial Failure 處理

> **2026-06-14 識別**：當 N 個 worker 中 M 個成功、 K 個失敗，Orchestrator 常常假裝全部成功直接進 synthesis。

**處理流程**：

```
if actual_count < expected_count:
    1. 識別失敗者：比對 expected worker IDs vs actual file list
    2. 隔離失敗者：把失敗的 worker 檔案移到 _failed/<worker-name>.md
    3. 估算影響：
       - 若 K/N < 0.3（少數失敗）→ 可繼續，用現有結果 synthesis，但要在報告標注「N-K/N 完成」
       - 若 K/N >= 0.3（多數失敗）→ 停止 synthesis，報告「本次任務不具統計代表性，重試」
    4. 記錄失敗原因（從 job log 或 process output 抓）
    5. 在最終報告中如實呈現：「3/4 worker 完成，1 個 worker (worker-2) 因網路超时無結果」
```

**驗證命令（防止假裝成功）**：

```bash
# 每個 worker 檔必驗
for f in ~/.hermes/handoff/<slug>/_raw/worker-*.md; do
    size=$(wc -c < "$f")
    lines=$(wc -l < "$f")
    echo "$f: $size bytes, $lines lines"
    if [ "$size" -lt 100 ] || [ "$lines" -lt 5 ]; then
        echo "⚠️ SUSPICIOUS: $f is too small — possible fake success"
    fi
done
```

---

## 衝突 Resolution 預防

> **2026-06-14 識別**：`Aggregation hallucination`（summarizer 把衝突當共識）是最高頻失效。

**預防原則（在派遣前就定義）**：

1. **_plan.md 必填「結論採用策略」**：
   ```markdown
   ## 結論採用策略
   - 優先：最新時間戳（若多個 worker 結果時間不同）
   - 或：指定主 worker（worker-1 為主，worker-2/3 為輔）
   - 或：共識門檻（> 2/3 worker 同意才視為共識）
   ```

2. **派遣 prompt 明確要求 worker 標記置信度**：
   - 每個結論必須附 `[confidence: high/medium/low]`
   - 低置信度結論不參與共識投票

3. **嚴禁「LLM 自己判斷衝突是否存在」**：
   - 交給 Orchestrator（人類）裁決
   - summarizer 只列點 + 標記，不和稀泥

---

## 驗證清單（完成 Fan-In 後必跑）

```bash
# 1. 最終彙整檔存在且非空
[ -s ~/.hermes/handoff/<slug>/_summary.md ] && wc -c ~/.hermes/handoff/<slug>/_summary.md

# 2. 大小合規（5-15 KB）
size=$(wc -c < ~/.hermes/handoff/<slug>/_summary.md)
if [ "$size" -gt 15000 ]; then echo "⚠️ too large"; fi
if [ "$size" -lt 5000 ]; then echo "⚠️ too small"; fi

# 3. 沒有偽裝衝突（檢查關鍵詞）
grep -i "conflict\|CONFLICT\|分歧\|不一致" ~/.hermes/handoff/<slug>/_summary.md || echo "⚠️ no conflict markers found — possible hallucination"

# 4. 每個 worker 都有對應內容（來源索引）
# 若有 worker 被完全忽略，grep 會找不到該 worker 結論
```

---

## 與 orchestrator-worker-architecture 的整合點

| Fan-In 節點 | orchestrator-worker-architecture 對應章節 |
|------------|----------------------------------------|
| Strategy A/B/C 選擇 | 「Fan-Out/Fan-In 失敗模式表」Conflict resolution 欄 |
| Partial failure 隔離 | 「Partial failure 無人察覺」失敗模式 |
| 驗證清單 | 「驗證 SOP」章節 |
| 衝突預防 | 「If→Then 規則」（aggregation hallucination 規則）|

---

## If→Then 規則

**If** `delegate_task(tasks=[...])` 超過 5 個 workers **Then** 拆成兩批（每批 2-3 個）+ 中間彙整，避免 N(N-1)/2 衝突增長

**If** 任務是「同一問題多視角分析」（非事實類）**Then** 結果彙整不走 LLM synthesis，改走 Strategy B（列點 + 衝突標記 + Orchestrator 裁決）

**If** 任務是「各自獨立事實蒐集」**Then** 結果彙整可以 LLM synthesis，但必須先執行「驗證所有 expected 檔都存在且非空」

**If** `wc -c` 驗出任何 worker 檔 < 100 bytes **Then** 判定為「Worker 假裝成功」，不將該檔傳入 synthesis prompt

**If** actual_count < expected_count 且 K/N >= 0.3 **Then** 停止 synthesis，輸出「任務不具統計代表性，請重試」

---

## 來源

- Beam AI: 6 Multi-Agent Orchestration Patterns for Production (2026)
- arXiv 2507.08944: Optimizing Sequential Multi-Step Tasks with Parallel LLM Agents
- Developers Digest: How to Coordinate Multiple AI Agents: The Definitive Guide for 2026
