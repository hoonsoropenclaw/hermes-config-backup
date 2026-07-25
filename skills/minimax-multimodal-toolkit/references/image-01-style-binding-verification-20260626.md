# image-01 Style Binding — Live Verification (2026-06-26)

## 驗證方法

用 PIL/Pillow 檢查輸出 JPEG 檔案大小（KB）即可判斷 style binding 成敗，**不需要視覺分析**：
- <350KB → 風格失效（寫實攝影預設，model 忽略了 style tokens）
- **350–500KB → 灰區（comic style 可能部分渲染，但不穩定）**
- >500KB → 風格成功（漫畫/插畫風格，model 忠實渲染）

原理：漫畫/插畫風格 JPEG 含 halftone dots、厚線條區塊，壓縮後仍較大；寫實攝影 compression ratio 高，檔案較小。

## 灰區解讀（2026-06-26 新增）

| 檔案大小 | 意義 | 建議動作 |
|---------|------|---------|
| 350–400KB | comic/halftone style 可能部分失效，model 有收斂傾向 | 用 `--n 4` 多生成幾張，挑選 >500KB 的 |
| 400–500KB | style 有渲染但 compression ratio 偏高（漫畫筆觸不夠密集） | 仍算成功但信頼度中等 |
| >500KB | ✅ 明確成功 | 無需多驗 |

**實務建議**：灰區出現時，不要只靠單張判斷。跑 `--n 4`，從 4 張中挑選 size 最大者重新評估。

## 2026-06-26 實測結果

| Prompt | 輸出檔案大小 | 實際風格 | 判定 |
|--------|------------|---------|------|
| `minimalist line art, clean lines, flat colors, studio lighting` | **299KB** | photorealistic（風格失效） | ❌ |
| `comic book style, bold ink linework, halftone patterns, vibrant colors, Marvel cover art style` | **622KB** | comic book（風格保留） | ✅ |
| `bird's eye view, overhead shot, top-down perspective + comic book style, ink outlines, halftone` | **409KB** | 灰區臨界（comic style 部分渲染） | ⚠️ |

生成參數：`--aspect-ratio 1:1 --n 1`，model `image-01`。

## 應用：快速診斷流程

```python
import os

def check_style_binding(jpeg_path):
    size_kb = os.path.getsize(jpeg_path) // 1024
    if size_kb < 350:
        return "⚠️ 風格可能已失效（<350KB ≈ photoreal fallback）"
    elif 350 <= size_kb <= 500:
        return f"⚠️ 灰區（{size_kb}KB），comic style 不穩定，建議 --n 4 多張驗證"
    else:
        return f"✅ 風格成功保留（>{size_kb}KB ≈ 漫畫/插畫風格）"

# 使用範例
result = check_style_binding('/tmp/style_test/line_art_test_001.jpg')
print(result)
```

**何時用**：當不方便用 vision_analyze（或 vision provider 設定有問題）時，用檔案大小快速判斷。
