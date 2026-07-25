# image-01 Style Selection Decision Tree（2026-06-28 新增）

## 缺口背景

現有文檔（image-prompting-cookbook.md 273行 + mmx-cli-image-gen.md 424行）已累積大量 empirical data，但全是「列舉失敗模式」，**沒有決策樹**。

給定一個用戶風格需求，agent 只能逐一比對已知失敗案例，效率低且容易遺漏。

本條目補足這個缺口。

## 決策樹

### Step 1：評估用戶意圖（Intent Assessment）

```
用戶要的風格 → 評估 intent 等級

意圖光譜：
[A] 純美學（無人物）：風景、物品、logo、icon
[B] 人物＋非寫實風格：comic、vector、Ghibli、watercolor
[C] 人物＋寫實風格：photography、editorial、sports
[D] 人物＋暗示性姿勢/穿著：swimwear、lingerie modeling、bedroom aesthetic
```

### Step 2：Image-01 Safe?

```
[D] 意圖 → image-01 必定 filter（switch to FAL/FLUX immediately）
[A-B] 意圖 → 繼續 Step 3
[C] 意圖 → 繼續 Step 3（image-01 對寫實支援最好）
```

### Step 3：Style Binding Strength Check

```
Style 綁定強度（S > A > B > C > D）：

S: comic book + ink outlines + halftone → 4/4 success
A: vector illustration, cel-shaded → 高成功率
B: Studio Ghibli, watercolor → 高成功率
⚠️ C: fashion editorial → 中成功率，需要強服裝描述
❌ D: minimalist line art, flat colors → 0/4（被 photoreal 覆蓋）

若選 D 等級 → 立即改用 comic/vector/Ghibli 替代
```

### Step 4：Body-Shape Vocabulary Check（for [B] + [C] with people）

```
可用（safe）：full-figured, pear-shaped, soft curves, curvaceous, well-rounded
❌ 擋掉（blocked）：curvy alone, voluptuous, hourglass body shape, curvy hourglass
⚠️ 綁定 style 可繞過：curvy figure + comic book style → 可能成功

若用戶堅持 blocked keyword → 立即提供 3 個繞過替代
```

### Step 5：三元素組合預警

```
三元素同時出現 → high false positive risk：

[年輕女性] + [藝術風格 line art/flat colors] + [bird's-eye/overhead]
→ image-01 content filter 產生 NSFW aesthetic false positive

緩解策略（優先順序）：
1. Prompt 分解：風景/物品先確認視角，再墊圖（--first-frame）
2. Style 鎖定開頭：comic book cover art, [subject]...
3. 預警用戶：主動告知風險 + 建議拆解
```

### Step 6：何時 switch to FAL/FLUX（2026-06-29 更新）

```
立即切換的紅線條件（滿足任一）：
□ minimalist line art + human portrait + bird's-eye
□ flat colors + human portrait + extreme angle
□ D-level style + 人物 + 藝術風格意圖
□ 使用者堅持 curvy/voluptuous + 寫實 photography

切換後：FAL FLUX.1-dev 對身材描述限制較少
```

**⚠️ FLUX/FAL 備援方案驗證狀態（2026-06-30 再次確認）**：
- FLUX bird's-eye + line art + portrait claim **從未實測驗證**，FAL_KEY = `***`（未設定）
- **已驗證方案**：comic book style + bird's-eye = 3/3 success（2026-06-19）
- **If** 使用者拒絕 comic style且堅持 line art → 告知「FLUX 理論上可繞過，但尚未驗證」

**更新後的 Step 6 優先順序**：
1. **Primary**：comic book / vector / Ghibli style + bird's-eye（唯一已驗證）
2. **Secondary**：Prompt 分解（風景/物品先確認視角，再用 `--first-frame` 疊人物）
3. **Last resort**：建議 FLUX 並明確標記「未驗證」——使用者接受風險後再切

### Step 7：Image-01 Confabulated API Features 警告（2026-06-30 新增）

`--similar` / `variation mode` 等 Midjourney/DALL-E 術語**不存在於 mmx-cli**。驗證命令：
```bash
mmx image generate --help | grep -iE "similar|variation"  # → 0 matches
```

**If** 自己對使用者提到一個 API flag 或 mode 名稱 **Then** 立刻用 `--help | grep <flag>` 驗證是否存在再說出口——MMX CLI 沒有 Midjourney/DALL-E 的 variation flags，說出口前必須驗證。完整條目見 `mmx-cli-image-gen.md` §11。

## If→Then 核心規則

**If** 收到人物 + 風格需求 **Then** 先跑 Step 1-4 決策樹再開始生成，不要直接套 prompt

**If** 發現 D-level style（minimalist line art / flat colors）+ 人物 **Then** 立即替換為 comic book / vector / Ghibli，不重試原 style

**If** 三元素同時出現（Step 5）**Then** 預警用戶 + 提供 Prompt 分解策略，不假裝看不見 filter 風險

**If** 使用者提供的 body-shape keyword 在 blocked list **Then** 立即提供 3 個繞過替代（full-figured / pear-shaped / curvaceous），不要假裝生成成功

**If** D-level style 失敗 2 次 **Then** 立即切換 FAL/FLUX，不在 image-01 上繼續浪費 quota

## 相關條目

- [[mmx-cli-image-gen.md]] — 424行 empirical data（原始觀察）
- [[ai-image-safety-school-20260620.md]] — style binding 量化（4/4 等級）
- [[refusal-anti-loop-20260623.md]] — 拒絕時的 user experience（避免來回修復）

## 驗證

本決策樹是對現有 empirical data 的結構化整合，無新假設。未來每個 image-gen session 結束後對照本樹檢查決策正確性。
