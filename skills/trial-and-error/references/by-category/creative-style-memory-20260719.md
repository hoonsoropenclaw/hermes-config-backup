### creative-style-01 Multi-Session Creative Style Memory — Persistent Creative Direction缺失（2026-07-19）

**Created**: Cycle 519, 2026-07-19
**Type**: D3-learn (實作型)
**Validated by**: Superside (2026), getimg.ai Style Elements (2026), Talk2Image arXiv:2508.06916

---

## 背景

現有創意 SOP 矩陣：

| SOP | 覆蓋階段 | 缺失 |
|-----|---------|------|
| `creative-intent-classification-20260716.md` | 請求分類 + 6-type routing | 收到請求時意圖判斷 |
| `creative-pipeline-dag-20260713.md` | DAG 串聯 + fault tolerance | pipeline 協調 |
| `creative-pipeline-execution-state-20260719.md` | checkpoint + retry | 執行狀態追蹤 |
| `creative-output-quality-verification-20260717.md` | post-gen quality check | 產出後品質驗證 |
| `image-moderation-reframing-20260709.md` | content moderation | 語義替換重試 |
| **(本 SOP)** | **multi-session style memory** | **跨 session 風格記憶** |

**核心問題**：Talk2Image (arXiv:2508.06916) 確認 Intention Drift 是 multi-turn generation 的頭號挑戰。
Superside (2026) 指出：generative AI 沒有品牌記憶，每個 generation 都從隨機噪聲開始。
getimg.ai Style Elements 實作：Style Element = 保存的視覺參照集（palette、lighting、finish、mood），可在任意 prompt 中呼叫。

赫米斯現有架構中，用戶可能在 session 1 要求生成漫畫風格，session 2 說「繼續」，但赫米斯無法自動繼承 session 1 的風格參數。

---

## 理論框架

**Talk2Image Dialogue State Memory**：
```
Hₜ = {(u₁,r₁), (u₂,r₂), ..., (uₜ₋₁,rₜ₋₁)}
Pₜ^text = f_θ(Hₜ, uₜ)
```
每個 turn 都融合歷史狀態，防止 intention drift。

**getimg.ai Style Element 結構**：
- 帳戶級儲存，自動套用於每次生成
- 單一 Element 包含：palette, lighting, finish, mood
- 可透過 `@StyleName` 在任意 prompt 中呼叫
- 8-15 張多樣化參照圖像效果最好

**Superside Brand Brain 三層模型**：
1. 品牌指南 — 規則、voice、compliance
2. 學習積累 — 過去作品、反饋審批、表現洞察
3. 協作流程 — 團隊角色偏好、工作流

---

## 三層創意記憶系統

### Layer 1：對話內風格記憶（in-conversation）

每次創意生成成功後，將 style parameters 寫入 session 內的 TODO 追蹤：

```python
# Style parameters captured after successful generation
style_memory = {
    "subject_ref": "/path/to/reference.jpg",  # if user provided
    "style_keywords": ["watercolor", "soft lighting", "muted palette"],
    "prompt_structure": "4-block layout",
    "negative_prompt": "no text, no watermark",
    "mmx_params": {"seed": 42, "--aspect": "16:9"},
    "brand_elements": ["minimalist", "earth tones"],
    "rejected_attempts": ["too dark", "over-saturated"]
}
```

**If** 同一 session 內用戶要求新生成，且 style_memory 存在
**Then** 將 style_memory 的關鍵參數自動注入新 prompt 的開頭

### Layer 2：跨 session 創意品牌檔案（persistent）

**檔案位置**：`~/.hermes/creative_brand_profiles/<profile_name>.json`

```json
{
  "profile_name": "user_default",
  "created_at": "2026-07-19",
  "updated_at": "2026-07-19",
  "dominant_style": "watercolor illustration",
  "color_preferences": ["#E8D5B7", "#8B7355", "#F5F0E8"],
  "lighting": "soft natural",
  "composition": "centered subject, negative space",
  "avoid": ["harsh shadows", "text overlays", "anime style"],
  "reference_images": [],
  "last_session_id": "20260708_070038",
  "successful_prompts": [
    "A serene mountain lake at dawn, watercolor style, soft light..."
  ],
  "moderation_escape_phrases": ["artistic interpretation", "illustrative portrait"]
}
```

**If** 用戶提到「之前那個風格」「繼續上次的專案」「和之前一樣的風格」
**Then** 查詢 `creative_brand_profiles/` 中最新的 profile，自動套用 dominant_style 和 color_preferences

**If** 用戶提供了新的參考素材（圖片、描述）
**Then** 更新該 profile 的 reference_images 和 dominant_style

### Layer 3：創意請求中的 Style Inheritance 觸發詞

**If** 用戶請求包含以下關鍵詞：
- 「跟上一次一樣」「沿用這個風格」「風格統一」
- 「和之前那張圖的風格相同」
- 「還記得上次的漫畫嗎」

**Then** 執行 Style Inheritance 流程：
1. 讀取 `creative_brand_profiles/user_default.json`（或 project-specific profile）
2. 提取 dominant_style、color_preferences、lighting、mmx_params
3. 自動生成 style injection prompt 前綴
4. 告知用戶「已套用 [profile_name] 的風格設定」

---

## If→Then 經驗固化

### If 赫米斯完成了一個創意生成任務（image/video/speech/music），用戶表示滿意
### Then 立即執行 Style Memory Capture：

1. 從成功生成的 prompt 中提取 style keywords（lighting、composition、color palette、mood）
2. 從 mmx 參數中提取 seed、--aspect、--style-preset 等持久化參數
3. 如果用戶提供了 reference image，複製到 `~/.hermes/creative_brand_profiles/references/`
4. 更新 `~/.hermes/creative_brand_profiles/user_default.json` 的 `successful_prompts` 和 `updated_at`
5. **不要只寫「已完成」** — 這個 capture 步驟是強制的，距離下一個創意請求可能隔幾天

```python
# 驗證命令：Style Memory Capture 完整性
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
# 預期輸出：MEMORY_COMPLETE 或 PROFILE_NOT_FOUND
```

---

### If 用戶要求一個新的創意生成，且 creative_brand_profiles/user_default.json 存在
### Then 在執行創意 pipeline 前，先執行 Style Inheritance：

1. 讀取 user_default.json
2. 生成 style injection 前綴：「[dominant_style], [lighting], [color palette], [composition]」
3. 將前綴插入 user request 的 prompt 前
4. 告知用戶：「套用風格記憶：[dominant_style]，包含 [lighting] + [color_preferences]」

---

### If 用戶要求新的創意生成，且提供了一個具體的 project name（如「專案：夏日行銷」）
### Then 為該 project 建立專屬 brand profile：

1. 建立 `~/.hermes/creative_brand_profiles/<project_name>.json`
2. 初始結構從 user_default.json 複製
3. 後續該 project 的所有生成都更新同一個 profile
4. 用戶說「繼續『夏日行銷』」→ 讀取該 project profile 而非 user_default

---

### If 用户要求「和之前风格相同」的生成，但 user_default.json 中没有 dominant_style 记录
### Then 向用户请求澄清：

「检测到您提到『沿用之前的风格』，但当前没有记录到之前的风格参数。请提供：
1. 参考图片（可直接粘贴）
2. 或者描述您想要的风格关键词（如：色调、光线、构图、情绪）

这样下次我就能自动记住了。」

---

## 預防

**觸發時機**：creative pipeline 成功完成後，交付給用戶之前，**強制執行** Style Memory Capture（Layer 1 + Layer 2）。

**為什麼需要独立 SOP**：
- Intention Drift 是 Talk2Image 確認的多輪生成頭號挑戰
- 每個 session 從隨機噪聲開始是 AI image generation 的固有缺陷
- 「赫米斯沒有記憶」是使用者最常抱怨的創意相關問題

---

## 關聯條目

- `creative-intent-classification-20260716.md` — 請求分類
- `creative-pipeline-dag-20260713.md` — 生成 pipeline
- `creative-pipeline-execution-state-20260719.md` — checkpoint/retry
- `creative-output-quality-verification-20260717.md` — 產出品質驗證
- `image-moderation-reframing-20260709.md` — content moderation
- `mmx-image-style-decision-tree-20260628.md` — mmx 風格決策樹
