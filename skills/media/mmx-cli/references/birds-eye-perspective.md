# image-01 Bird's-Eye View + Style Conflict — 完整踩坑記錄

本文檔是 `mmx-cli/SKILL.md` 的深度參考，專門記錄 **image-01 對 bird's-eye view（鳥瞰視角）的 text-image alignment 問題**，以及已驗證適用的解法。

---

## 核心問題（2026-06-16 確認）

image-01 對 `bird's-eye view` + `portrait` + 特定風格（line art/comic）的组合有**結構性綁定失敗**——text encoder 將「鳥瞰視角」和「人像主體姿態」視為競爭性 binding，導致 model 放棄視角而非放棄姿態。

**驗證方法**：用同義 prompt 跑 `--n 4`，若 4/4 都忽略 bird's-eye 語法，確認是結構性問題而非隨機種子。

---

## ✅ 已驗證可行方案（2026-06-26）

### 方案 A：`--prompt-optimizer` flag（首選）

```bash
mmx image generate \
  --prompt "portrait of a person, minimalist line art, bird's-eye view, overhead shot, studio lighting" \
  --prompt-optimizer \
  --aspect-ratio 1:1
```

**效果**：自動重寫衝突關鍵字（line art vs photorealistic、bird's-eye vs portrait pose），生成成功。

**注意**：optimizer 會修改 prompt 內容，偏離原始意圖程度取決於衝突程度。商用場景建議先看優化結果再決定是否使用。

**何時首選**：
- 衝突關鍵字多（同時有 line art + portrait + perspective）
- 需要快速測試不想手動調 prompt
- 風格方向可以接受小幅調整

### 方案 B：`overhead flat-lay composition` 片語（保守）

```bash
mmx image generate \
  --prompt "portrait, minimalist line art, clean lines, flat colors, overhead flat-lay composition, camera positioned directly above subject, top-down perspective, studio lighting softbox" \
  --aspect-ratio 1:1
```

**效果**：用場景片語替代 raw 透視關鍵字，觸發率比 `bird's-eye view` 更高。

**何時首選**：
- 商用場景不能接受 prompt 被改動
- 需要精確控制輸出一致性

---

## ❌ 已確認無效模式（不要用）

| 失效語法 | 原因 |
|---------|------|
| `bird's-eye view, looking down` | model 完全忽略 |
| `high angle shot` | model 完全忽略 |
| `camera directly above looking straight down` | model 完全忽略 |
| `top-down view of subject` | model 完全忽略 |
| 單一透視關鍵字 | 需疊加 3-5 個同義片語 |

**避免組合**：
- `minimalist line art + portrait + bird's-eye view` → NSFW aesthetic（text encoder 對這组合產生錯誤 binding）
- `young beautiful woman + bird's-eye + line art` → 結構性失敗 + 可能觸發不當內容

---

## 失敗機制分析

根據 2026-06-16 跑 8 張全失敗的觀察：

1. **競爭性 binding**：「bird's-eye view」和「portrait subject pose」的 text embedding 有重疊，model 二選一時傾向保留主體姿態
2. **風格衝突時的降級行為**：當 `minimalist line art`（線條插畫）和 `photorealistic` 衝突時，model 傾向寫實而非插畫風格
3. **NSFW 觸發**：特定透視 + 人像組合（bird's-eye + portrait + line art）與 NSFW aesthetic illustration 訓練資料高度重疊

---

## If→Then 規則

**If** 使用者要求 bird's-eye view + 特定藝術風格（line art / comic / watercolor）
**Then** 直接用 `--prompt-optimizer` flag，不嘗試 naive bird's-eye 語法

**If** `--prompt-optimizer` 結果偏離原始意圖（商用精確控制場景）
**Then** 改用 `overhead flat-lay composition` + `camera positioned directly above` + `top-down perspective` 疊加片語

**If** 使用者同時給「主體描述 + 姿態 + 透視」
**Then** 簡化為「主體 + 透視」或「主體 + 風格」，避免三個方向同時競爭

**If** 跑完 optimizer 還是失敗（罕見）
**Then** 檢查 prompt 是否含有 body-shape 形容詞（豐滿/voluptuous/curves），這些會觸發 content filter 導致 partial rejection

---

## 與 mmx-cli SKILL.md 的分工

| 內容 | 位置 |
|------|------|
| 安裝/認證/基本語法 | `SKILL.md` 主體 |
| 透視角控制實戰技巧 | `SKILL.md` §透視角控制章節 |
| 完整失敗模式 + 驗證過的解決方案 | `references/birds-eye-perspective.md`（本文） |
| 其他踩坑（auth / subprocess / content filter） | `references/content-filter-20260709.md` |
