# 圖片風格一致性 — 跨多張生成的一致性問題（2026-07-21）

## 問題背景

用戶在 2026-06-15 和 2026-06-16 跑了共 **261 條訊息**處理圖片生成問題，
核心抱怨：多輪對話中相同風格描述，輸出結果風格不一致。

**根本原因**：prompt-only 風格描述在多張生成後會漂移（3-5 張後開始不一致）。
image-01 是 stateless generation，沒有跨張的風格記憶。

## 2026 年業界標準解法

### 1. Reference-Image Anchoring（I2V 模式）

使用 `--first-frame` 把第一張滿意的圖當作 style anchor，後續生成墊圖：

```bash
# 生成滿意的參考圖（作為 style anchor）
mmx image generate --prompt "<style description>" --aspect-ratio 16:9 --n 1
# 找到滿意的結果，設為 anchor

# 後續生成墊同一張圖保持一致性
mmx image generate --prompt "<new scene, same style>" --first-frame anchor.jpg --aspect-ratio 16:9 --n 1
```

**原理**：I2V 模式中 `--first-frame` 不只是提供構圖，還傳遞風格特徵。
`--subject-image` (S2V) 更專注於主體一致性。

### 2. Reference Set（10-20 張參考圖）

建立風格參考集，透過 AI persona pipeline 達到跨張一致性：

```bash
# 1. 建立風格參考集目錄
mkdir -p ~/.hermes/img-ref/<project>/

# 2. 生成 10-20 張涵蓋不同場景但相同風格的參考圖
for scene in "outdoor" "indoor" "portrait" "full-body"; do
  mmx image generate --prompt "<style> $scene" --aspect-ratio 1:1 --n 4
done

# 3. 後續 prompt 加入風格關鍵字
mmx image generate --prompt "<new subject>, <captured style keywords from reference set>"
```

**2026 research**（OFGenerator、Midjourney community）：
- 10-20 張乾淨的參考圖 = 最佳實踐起點
- 頻繁重新驗證（每 200-300 張生成後重新墊 anchor）防止 drift
- LoRA fine-tuning 是終極一致性解法，但需要 GPU 資源

## If→Then 規則

```
IF 用戶要求「保持相同風格」「風格一致」「看起來像OO但場景不同」
THEN → 不要只靠重複相同的 prompt 關鍵字
     → 主動建議使用 --first-frame（I2V）或 --subject-image（S2V）
     → 若用戶拒絕墊圖，說明 drift 風險，請用 seed 固定隨機種子

IF 用戶抱怨「為什麼這張跟上一張顏色/風格不一樣」
THEN → 這是 prompt-only drift，確認上一次的滿意圖是否可當 anchor
     → 若無滿意圖，建議建立 3-5 張風格參考集

IF 需要長期、品牌級一致性（AI influencer、漫畫角色、遊戲美術）
THEN → 這已超出日常 prompting 範疇，建議評估 LoRA fine-tuning 方案
```

## 與 mmx-cli 現有決策樹的整合

現有 SKILL.md 的 `Step 5: Prompt 衝突時` 處理單張生成內的風格衝突；
本節處理**跨張生成**的風格漂移問題，兩者互補。

| 問題類型 | 現有章節 | 本節 |
|---------|---------|------|
| 單張 prompt 內多個衝突關鍵字 | Step 5（--prompt-optimizer） | — |
| 多張生成間的風格漂移 | — | 本文（reference anchoring） |

## 研究來源

- OFGenerator: "How to Build a Consistent AI Persona in 2026"（2026-07-21 查閱）
- Midjourney Community: "How To Create Consistent Style In Midjourney 2026"（2026-07-21 查閱）
- AtlasCloud Blog: "Best AI Image Generation APIs in 2026"（2026-07-21 查閱）
