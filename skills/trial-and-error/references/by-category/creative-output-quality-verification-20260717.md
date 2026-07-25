### creative-output-01 Creative Output Quality Verification — Post-Generation Verification缺失（2026-07-17）

**Created**: Cycle 510, 2026-07-17
**Type**: D3-learn (實作型)
**Validated by**: ELIQ (arxiv 2602.03558v2), CLIP Score (torchmetrics), MT2IE (arxiv 2505.00759v2)

---

## 背景

現有創意 SOP 矩陣：

| SOP | 覆蓋階段 | 缺失 |
|-----|---------|------|
| `creative-intent-classification-20260716.md` | 請求分類 + 6-type routing | 生成前意圖判斷 |
| `creative-pipeline-dag-20260713.md` | DAG 串聯 + fault tolerance | 生成中 pipeline 協調 |
| `image-moderation-reframing-20260709.md` | content moderation 處理 | 生成後審核 |
| **(本 SOP)** | **post-generation quality verification** | **Output vs Brief 對齊檢查** |

---

## 核心問題

ELIQ 研究確認：generative visual quality 與 prompt-alignment 是**兩個不同維度**，需要不同評估方法：
- **視覺質量**：傳統 distortion-based metrics（FID, SSIM, PSNR）已被證明與人類感知不一致
- **Prompt-Image Alignment**：CLIP-based scoring 是事實標準（MT2IE, arxiv 2505.00759 驗證）

---

## 理論框架

**ELIQ (Label-Free Framework for Quality Assessment of Evolving AI-Generated Images)**：
- 兩個軸：Visual Quality + Prompt-Image Alignment
- 無需 human annotation，透過 positive/negative pair construction 實現遷移學習
- 支援 AIGC→UGC 泛化

**MT2IE (Multimodal T2I Evaluation)**：
- 使用 MLLM 作為 evaluator
- 迭代生成評估問題並打分
- 比靜態 benchmark（TIFA160）更高效

**CLIP Score**（torchmetrics.multimodal.clip_score）：
- 標準工具：`openai/clip-vit-large-patch14`
- 輸入：image + caption (prompt)
- 輸出：0-100 相似度分數

---

## If→Then 經驗固化

### If 赫米斯完成了一個創意生成任務（image/video/speech/music）
### Then 立即執行 post-generation verification，使用 3-level quality ladder：

**Level 1 — CLIP Score (Automated, 適用於 image/video frames)**:
```python
from torchmetrics.multimodal.clip_score import CLIPScore
metric = CLIPScore(model_name_or_path="openai/clip-vit-large-patch14")
score = metric(images, ["prompt text"])
# score > 0.7 → 通過
# score 0.5-0.7 → 警告，建議用戶確認
# score < 0.5 → 失敗，需重新生成
```

**Level 2 — MLLM Aesthetic Judgment (Subjective quality)**:
```
Prompt: "Does this image/video look visually appealing and professional? 
Rate from 1-5. Briefly explain your rating."
# 3分以上 → 通過
# 2分 → 警告
# 1分 → 失敗
```

**Level 3 — Full ELIQ Assessment (High-stakes commercial use)**:
```
使用 ELIQ 框架：
1. 提取 positive/negative aspect pairs
2. 雙維度評分：visual quality + prompt alignment
3. 0.5 threshold 為通過線
```

---

### If 用戶請求的是 image 生成
### Then 執行 Image Verification Pipeline：

1. **Prompt-Alignment Check**（CLIP Score ≥ 0.65 通過）
2. **Moderation Check**（使用 image-moderation-reframing SOP）
3. **Aesthetic Check**（MLLM 3/5 通過）
4. **如有任何一項失敗** → 告知用戶具體失敗維度 + 詢問是否重新生成

**驗證命令（torchmetrics CLIPScore）**:
```bash
python3 -c "
from torchmetrics.multimodal.clip_score import CLIPScore
import torch
metric = CLIPScore(model_name_or_path='openai/clip-vit-large-patch14')
# 模擬：image tensor + prompt
# score = metric(image_tensor, ['a photo of a cat'])
print('CLIPScore ready')
"
# 需確認：torchmetrics 已安裝 + clip-vit-large-patch14 可下載
```

---

### If 用戶請求的是 video 生成
### Then 執行 Video Verification Pipeline：

1. **Frame Sampling**（均勻採樣 4-8 frames）
2. **Per-frame CLIP Score**（平均分 ≥ 0.60 通過）
3. **Temporal Consistency Check**（MLLM 評估幀間過渡是否自然）
4. **Prompt-Alignment**（取中間幀做 CLIP Score）

**驗證命令（frame extraction）**:
```bash
ffmpeg -i input.mp4 -vf "fps=1" frame_%04d.jpg
# 每秒採樣 1 幀，用於 CLIP Score
```

---

### If 用戶請求的是 speech 或 music 生成
### Then 執行 Audio Verification Pipeline：

1. **SNR Estimation**（信噪比檢查）
2. **Transcription Accuracy**（speech only：speech-to-text → 與原文對比）
3. **MOS Estimation**（MLLM 評估音頻質量）
4. **如 music 生成** → 風格標籤分類確認

---

## 實作優先順序

| 優先級 | 工具 | 實現難度 | 適用場景 |
|--------|------|---------|---------|
| P1 | CLIP Score (image/video frames) | 低（torchmetrics） | 快速自動化 |
| P2 | MLLM aesthetic judgment | 中（需 LLM 呼叫） | 專業產出 |
| P3 | ELIQ full framework | 高（需訓練 adaptation） | 商業級品質 |

---

## 預防

**觸發條件**：當創意生成任務完成後（任意 6-type 生成成功或失敗），立即啟動 post-generation verification。

**為什麼需要独立 SOP**：
- Generation quality vs output quality 是不同階段
- 現有創意 SOP（intent classification、pipeline DAG、moderation）都停在「生成完成」階段
- 沒有驗证的生成是用戶信任的主要破壞者

---

## 關聯條目

- `creative-intent-classification-20260716.md` — 請求分類
- `creative-pipeline-dag-20260713.md` — 生成 pipeline
- `image-moderation-reframing-20260709.md` — content moderation
- `skill-selection-routing-20260716.md` — skill routing
