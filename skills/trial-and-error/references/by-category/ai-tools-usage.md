
---

### mmx-cli image generation: skill lacks scripts/ causing repeated boilerplate (2026-07-07)

**症狀**: 用戶在 2026-07-07 session (132 msgs) 需要生成圖片時，赫米斯每次都要重寫 Python subprocess 腳本（20+ 行），包含：
1. API key 讀取（踩 `***` glob 遮蔽坑）
2. JSON 輸出解析
3. 多圖 batch 生成迴圈
4. Error handling

**根因**: `mmx-cli` skill (SKILL.md v1.2.0) 只有決策樹文件和 `references/birds-eye-perspective.md`，沒有 `scripts/` 目錄。所有 wrapper 邏輯每次都要從零重建。

**解法**: 
- D3 exit 2026-07-07: 建立 `~/.hermes/skills/media/mmx-cli/scripts/mmx-image-gen.sh`
- 用 `grep -F` (fixed string) 避免 `***` glob 問題
- 單行 CLI interface：`mmx-image-gen.sh "prompt" [dir] [aspect]`

**預防**: 以後任何 skill 有「每次使用都要重寫同樣 20+ 行 Python」的模式，**立即建立 scripts/ wrapper**，不要等第三次。

**If→Then**: **If** 使用者對某個工具有重複性需求、但 skill 只有文件沒有 script **Then** 這是 D3 trigger，立即建 wrapper script
