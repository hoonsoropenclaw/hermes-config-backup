# image-01 Style Binding Spectrum（2026-06-25）

## 核心原理

image-01 的 prompt interpreter 對不同類型的「風格關鍵詞」有不同的綁定行為：

| 關鍵詞類型 | 示例 | image-01 行為 |
|-----------|------|--------------|
| **Abstract artistic** | `line art`, `flat colors`, `minimalist`, `simple illustration` | 收斂到 photorealism fallback（洗成寫實） |
| **Commercial art** | `comic book style`, `ink outlines`, `halftone`, `cel-shaded`, `vector illustration` | 忠實渲染 |
| **Photography-native** | `Canon EOS R5`, `85mm`, `golden hour`, `studio lighting` | 忠實渲染 |

**為什麼會這樣**：image-01 的訓練數據中，「line art + bird's-eye portrait」這類組合極少見。當 prompt 同時包含「抽象藝術風格」和「特定視角」時，model 缺乏足夠的 training signal 收斂到「忠實線條」，於是 fallback 到它最有信心的領域——photorealism。

## Bird's-eye + Portrait 的可靠風格（已驗證）

| 風格關鍵詞 | 成功率 | 備註 |
|-----------|--------|------|
| `comic book style, ink outlines, halftone` | ✅ 3/3 (2026-06-19) | 鳥瞰漫畫肖像，halftone 清晰可見 |
| `anime style, cel-shaded` | ✅ (2026-06-19) | 動漫女孩測試 exit 0 |
| `vector illustration with thick black outlines` | ✅ (pipeline 建議置換) | |
| `minimalist line art` | ❌ washes to photoreal | 失敗 cluster |
| `flat colors` alone | ❌ washes to photoreal | 失敗 cluster |
| `minimalist` + `looking down` + portrait | ❌ washes to photoreal | 失敗 cluster |

## Bird's-eye + Portrait 的鏡頭語言標準公式

**⚠️ 自然語言被忽略**：`looking down`、`from above` 這類自然語言描述會被 model 忽略。

**標準 cinematography 術語（放在 prompt 最開頭）**：
```
bird's eye view, overhead shot, top-down perspective, [subject], [context], [style]
```

不是：
```
A woman looking down from above...  ← 被忽略
```

## 實務決策樹

```
prompt 含 bird's-eye + portrait + 藝術風格?
│
├─ 含 line art / flat colors / minimalist
│   └─ 告知用戶：image-01 對 abstract artistic keywords 會 wash to photoreal
│      → 置換為：comic book style + ink outlines + halftone
│      → 或提議 FLUX.1-dev（需 FAL_KEY，~$0.025/image）
│
├─ 含 anime / cel-shaded / comic book
│   └─ ✅ 可直接生成，成功率 high
│
└─ 含攝影語言（Canon/85mm/golden hour）
    └─ ✅ 直接生成，photorealism 是 image-01 的強項
```

## If→Then

**If** 使用者 prompt 含 `bird's-eye` + `line art`/`flat colors`/`minimalist` 且要求忠實於藝術風格
**Then** 立即告知限制，給出替換方案（comic book / anime / FLUX），並解釋原理
**If** 使用者拒絕替換風格且無 FAL_KEY
**Then** 告知這是 image-01 的架構限制，無法通過 prompt 改寫解決
