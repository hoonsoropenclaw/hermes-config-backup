---

### image-01 三元約束失敗（bird's-eye + body-shape + line art）— D3 實作（2026-06-21）

**症狀**：同時包含「bird's-eye + body-shape 形容詞 + 藝術風格」的 prompt，image-01 會依序忽視其中 1-2 個約束，導致輸出偏攝影而非插畫風格。

**根因**：image-01 的安全過濾器對三類 token（身體形狀、攝影視角、藝術風格）有獨立的降級邏輯，三者同時出現時模型選擇性忽略部分約束。

**解法**：將 prompt 重構為「情境 vocabulary」（volleyball build/sports physique）代替身體形狀形容詞，camera angle token 放在 prompt 最前面，並使用 `comic book style, ink outlines, halftone`（而非 minimalist line art）綁定藝術風格。

**預防**：新增 `minimax-multimodal-toolkit/references/image-generation-pipeline.md` 單一 SOP，涵蓋 prompt → probe → 生成 → 失敗分類 → 修復/切換 FLUX 的完整決策鏈。觸發：當 image generation session 跑了 10+ 次嘗試仍不滿意，即表示缺乏系統性 SOP，應立即啟動此 runbook。

**If→Then**：**If** prompt 含 body-shape adjective + bird's-eye + line-art/flat-colors **Then** 直接告知三約束會衝突，推 FLUX 重構方案，不要 retry image-01。

**驗證命令**：
```bash
ls -la ~/.hermes/skills/minimax-multimodal-toolkit/references/image-generation-pipeline.md
# mtime 應為 2026-06-21
```

**相關條目**：[[minimax-multimodal-toolkit#Style Failure Patterns]], [[minimax-multimodal-toolkit#image-generation-pipeline]]
