### creative-pipeline-02 Creative Pipeline Execution State — Checkpoint/Retry 實作規則（2026-07-19）

**Gap 症狀**：creative-pipeline-dag-20260713.md 已建立 DAG 框架，但缺少執行狀態管理規則。當 `--async` 任務失敗或超時時，赫米斯不知道：
1. 如何判斷該重試（retry）還是中止放棄（abort）
2. 如何在重試時不重跑已成功的上游步驟
3. checkpoint 狀態該存在哪裡、如何讀寫

**理論基礎**：
- Claro Digital (2026): 73% major incidents involve cascade failures; 5 agents × 95% reliability = 77% overall
- Diagrid durable execution: checkpoint each step, resume from last successful step
- Reddit AI-agents consensus: "workflow-level retry on failure means re-running 7 steps that already succeeded — waste of time + duplicate side effects"

---

## Checkpoint 格式

```bash
# 位置：~/.hermes/creative_pipeline_checkpoints/<workflow_id>.json
# 結構：
{
  "workflow_id": "cmp_20260719_<timestamp>",
  "steps": {
    "step_name": {
      "status": "pending|running|success|failed|skipped",
      "output_path": "/path/to/output",
      "error": "error message if failed",
      "retry_count": 0,
      "completed_at": "ISO timestamp"
    }
  },
  "created_at": "ISO",
  "updated_at": "ISO"
}
```

---

## If→Then 執行規則

### 規則 1：失敗分類電路口

**If** mmx 任務返回 `moderation_rejected` 或內容審核錯誤
**Then** 觸發「語義替換重試」流程（image-moderation-reframing SOP）：
1. 解析被拒絕的 prompt 區塊
2. 套用 semantic replacement table
3. 重試最多 2 次（--retry-count ≤ 2）
4. 超過 2 次 → 標記為 `failed`，進入 human-in-the-loop 節點（告知用戶）

**If** mmx 任務超時（--poll-interval 達到上限）
**Then** 分類超時原因：
- 任務還在生成中（伺服器忙碌）→ 繼續輪詢，最多 3 次額外輪詢
- 任務已明確失敗（明確 error 響應）→ 標記為 `failed`，進入 checkpoint 回退邏輯
- 網路/連接錯誤 → 重試 1 次，失敗則 abort

**If** 任務返回部分輸出但品質不符預期
**Then** 這是「品質失敗」不是「系統失敗」：
- 不要重跑 pipeline
- 告知用戶：該步驟有輸出但品質有風險，問是否接受或重做該步

### 規則 2：Checkpoint 讀寫時機

**If** 開始執行 DAG 中任何一個步驟
**Then** 立即寫入 checkpoint（status: running）

**If** 步驟成功完成
**Then** 更新 checkpoint（status: success, output_path, completed_at）

**If** 步驟失敗
**Then** 更新 checkpoint（status: failed, error, retry_count++）

**If** 整個 pipeline 完成（或中止）
**Then** 刪除 checkpoint 檔案（或移到 archive/）

### 規則 3：Resume 邏輯

**If** 用戶再次提到同一個創意 project，且 checkpoint 存在
**Then** 讀取 checkpoint，顯示：「檢測到上次未完成的 pipeline，狀態如下」，並詢問用戶：
- 接受現有進度，從失敗步驟繼續
- 全部重來
- 只重做特定步驟

**If** 要從 checkpoint 恢復
**Then** 按以下順序：
1. 讀取 checkpoint JSON
2. 找到第一個 status=failed 或 status=pending 的步驟
3. 該步驟的所有上游步驟 output_path 載入記憶
4. 只執行受損步驟，下游步驟 status 改為 pending

### 規則 4：Async 輪詢紀律

**If** 使用 `--async --quiet` 模式發出任務
**Then** 輪詢紀律如下：
- `--poll-interval 30`（30 秒，平衡速度與 API 負擔）
- 最多輪詢 40 次（20 分鐘超時）
- 每次輪詢更新 checkpoint current_step
- 40 次後仍無結果 → 標記為 `failed`，觸發規則 1 超時分類

---

## Human-in-the-Loop 節點

以下情況必须停下来询问用户，不要自己决定：

1. 同一個步驟失敗 3 次（重試預算用盡）
2. 系統錯誤（非 content moderation 錯誤，如 API 500）
3. 用戶沒有提供足夠素材完成下一步（如需要角色圖但用戶只給了文字描述）
4. Pipeline 執行時間預計超過 30 分鐘

---

## 驗證命令

```bash
# 確認 checkpoint 目錄存在
ls -la ~/.hermes/creative_pipeline_checkpoints/ 2>/dev/null || echo "DIR_NOT_FOUND"

# 測試 checkpoint 讀寫
python3 -c "
import json, os
from pathlib import Path
ckpt_dir = Path.home() / '.hermes/creative_pipeline_checkpoints'
ckpt_dir.mkdir(exist_ok=True)
test_ckpt = {
    'workflow_id': 'test_20260719',
    'steps': {'step1': {'status': 'success', 'output_path': '/tmp/test.mp4'}},
    'created_at': '2026-07-19T00:00:00Z'
}
path = ckpt_dir / 'test_20260719.json'
path.write_text(json.dumps(test_ckpt, indent=2))
loaded = json.loads(path.read_text())
print('WRITE_OK' if loaded['steps']['step1']['status'] == 'success' else 'WRITE_FAIL')
path.unlink()
"
# 預期輸出：WRITE_OK
```

---

**相關條目**：
- `creative-pipeline-dag-20260713.md` — DAG 框架基礎
- `image-moderation-reframing-20260709.md` — 語義替換重試
- `ai-tools-usage.md` — mmx 工具使用
