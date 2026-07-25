### creative-style-02 Style Memory Trigger — Automatic Capture on User Approval
**Created**: Cycle 521, 2026-07-19
**Type**: D3-learn (實作型)
**Validated by**: Midjourney --sref mechanism (docs.midjourney.com) + arXiv:2606.06893v1 WSA Framework
**Gap**: creative-style-memory SOP (Cycle 519) describes WHAT to capture, but has no invocation trigger

---

## 背景

**Midjourney --sref 觸發機制**（2026-07-19 驗證）：
- `--sref <image_url_or_code>` 在 diffusion 過程中注入 style embedding
- 使用者對滿意的結果說「這個風格」→ Midjourney 自動記住 style code
- 關鍵：用戶表達滿意 = 隱式 style approval signal

**mmx style 機制**（2026-07-19 驗證）：
- `--prompt-optimizer`：自動展開 vague style keywords
- `--subject-ref`：character/image consistency reference
- **無內建 `--sref`  equivalent** — style 完全由 prompt text 控制
- **沒有自動記憶機制** — 每次 generation 都是從零開始

**赫米斯現有 SOP 缺口**：
- `creative-style-memory-20260719.md`：描述了 Layer 1/2/3 記憶系統，但**沒有定義觸發時機**
- 沒有「當用戶說這句話時，自動執行 style capture」的鉤子
- 導致：即使 SOP 存在，也從未被調用

**arXiv WSA Framework（R 組件）**：
- R（Routing Header）= skill 的觸發條件 + 適用場景描述
- Skill-IR: `Skill = (R, W + S + A runtime_specification)`
- **R 是 skill 的調用開關** — 沒有 R，skill 永遠不會被觸發

---

## 觸發信號分類

### Layer 1：用戶隱式 approval（最常見）

當用戶說以下任何一句話 → 觸發 Style Memory Capture：

| 信號類型 | 範例 |
|---------|------|
| 正面評價 | 「很好」「不錯」「滿意」「這張好」「喜歡」|
| 採用意圖 | 「就用這張」「這版吧」「可以」「OK」|
| 迭代停止 | 「先這樣」「先到此為止」「好了」|
| 特定表揚 | 「這個風格很好看」「色調很棒」|

**If** 用戶說了上述任何一句話，且這是創意生成任務（image/video/music）
**Then** 立即執行 Style Memory Capture（搶在使用者關閉對話前）

### Layer 2：用戶顯式 style request

| 信號類型 | 範例 |
|---------|------|
| 風格複用 | 「跟上張一樣的風格」「延續這個風格」|
| 風格調整 | 「要更亮一些」「改成暖色調」|
| 跨專案 | 「這個風格可以用在我的另一個案子」|

**If** 用戶請求「延續 / 跟隨 / 一樣的風格」
**Then** 先執行 Style Inheritance（讀取 user_default.json），再執行新 generation

### Layer 3：系統內部觸發

| 觸發條件 | 動作 |
|---------|------|
| 創意 pipeline 交付前閘門通過 | 自動執行 Layer 1 capture |
| 用戶上傳新的參考圖 | 複製到 `references/` + 更新 profile |
| `creative_brand_profiles/` 不存在 | 先創建目錄結構再寫入 |

---

## If→Then 經驗固化

### If→Then #1（自動捕獲觸發）

**If** [用戶對創意生成說了 approval signal（很好/不錯/就用這張/可以/OK/喜歡），且這是 image/video/music generation]
**Then** [在回覆用戶之前，先執行 Style Memory Capture，不能只說「好的」就結束]

步驟：
1. 從本次成功的 prompt 中提取 style keywords（lighting/color palette/mood/composition）
2. 從 mmx 參數提取 seed/--aspect/--style-preset（如果有）
3. 如果用戶提供了 reference image，複製到 `~/.hermes/creative_brand_profiles/references/<session_id>/`
4. 更新 `~/.hermes/creative_brand_profiles/user_default.json` 的 `successful_prompts` 和 `updated_at`
5. **然後**才回覆用戶

**Why** 用戶說「很好」的瞬間是最強的 style endorsement signal；過後用戶已轉移注意力，capture 意願最低

### If→Then #2（Style Inheritance 觸發）

**If** [用戶說「跟上張一樣的風格」「延續這個風格」「要跟上版權一樣的感覺」]
**Then** [先執行 Style Inheritance，再執行新 generation]

步驟：
1. 讀取 `~/.hermes/creative_brand_profiles/user_default.json`
2. 提取 `dominant_style` + `color_preferences` + `lighting` + `mmx_params`
3. 生成 style injection 前綴：「[dominant_style], [lighting], [color palette], [composition]」
4. 將前綴插入新 prompt 的開頭
5. 告知用戶：「已套用您的風格設定：[dominant_style]，包含 [lighting] + [color_preferences]」

**Why** Midjourney --sref 的核心價值：用戶滿意後說「這個」→ 系統自動記住；赫米斯應該實現相同體驗

### If→Then #3（目錄不存在時的防禦）

**If** [執行 Style Memory Capture 時，`~/.hermes/creative_brand_profiles/` 目錄不存在]
**Then** [立即創建目錄結構，然後繼續寫入]

```bash
mkdir -p ~/.hermes/creative_brand_profiles/references
```

**Why** Cycle 519 的教訓：SOP 文件存在 ≠ 系統就緒；目錄基礎設施是 Layer 2 persistent profiles 的前提

### If→Then #4（WSA R-Component 映射）

**If** [需要建立新的創意相關 SOP，且該 SOP 描述了一個工作流程]
**Then** [必須在 R（Routing Header）中定義明確的觸發條件，格式：「當 [X] 時，調用此 skill]

R 組件必備欄位：
```
觸發條件：[具體的用戶信號或系統事件]
適用場景：[什麼情況下應該用這個 skill]
不適用：[什麼情況下不應該用]
```

**Why** arXiv:2606.06893v1 WSA Framework 確認：沒有 R 組件的 skill = 永遠不會被觸發的 dead code

---

## 驗證命令

```bash
# 驗證目錄存在
python3 -c "from pathlib import Path; p=Path.home()/.hermes/creative_brand_profiles; print('READY' if p.exists() else 'MISSING')"

# 驗證 profile 完整性
python3 -c "
import json
from pathlib import Path
profile_path = Path.home() / '.hermes/creative_brand_profiles/user_default.json'
if profile_path.exists():
    p = json.loads(profile_path.read_text())
    required_keys = ['dominant_style', 'color_preferences', 'lighting', 'successful_prompts']
    missing = [k for k in required_keys if k not in p or not p[k]]
    print('MEMORY_COMPLETE' if not missing else f'MEMORY_INCOMPLETE: {missing}')
else:
    print('PROFILE_NOT_FOUND')
"

# 驗證 creative_brand_profiles 目錄結構
ls -la ~/.hermes/creative_brand_profiles/ 2>/dev/null || echo "DIR_MISSING"
```

---

## 關聯條目

- `creative-style-memory-20260719.md` — WHAT to capture（3-layer memory system）
- `creative-output-quality-verification-20260717.md` — 交付前審批閘門
- `creative-pipeline-dag-20260713.md` — pipeline 協調
- `creative-pipeline-execution-state-20260719.md` — checkpoint/retry
- `mmx-image-style-decision-tree-20260628.md` — mmx 風格參數
