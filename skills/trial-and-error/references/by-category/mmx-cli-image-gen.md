# mmx-cli + Image Generation 踩坑彙整 (2026-06-16 驗證)

本檔專門收錄「從 hermes session 透過 `mmx-cli` 跑 image/video/audio 生成」會踩到的雷。是 `minimax-multimodal-toolkit` skill 的 **agent-side 補充**,針對 hermes 整合層的細節。

主 skill (`minimax-multimodal-toolkit/SKILL.md`) 已涵蓋:
- Auth 隔離 (mmx 不讀 hermes .env)
- Bash single-quote escaping
- image-01 body-description safety filter
- Aspect-ratio valid set

**本檔補主 skill 沒收的 agent-side 細節。**

---

## 11. LLM 虛構不存在的 API 功能（Confabulated API Features）— 2026-06-30 新增

**症狀**: 在 image generation 任務中，assistant 對使用者說「我使用 --similar mode」或「similar variants」，但 mmx-cli 根本**沒有** `--similar` flag。

**session 案例**: `20260616_125207`（98 msgs，AI 圖片生成 session）期間，assistant 多次提到 `--similar mode`、`similar variants`，但實際跑 `mmx image generate --help | grep similar` 返回 0 matches。

**根因**: LLM 訓練資料包含 Midjourney (`/similar`、V variation)、DALL-E（variation mode）等其他 image gen API 的文檔。當使用者說「再來一張類似的」，assistant 預設遷移到這些熟悉術語，**未驗證 mmx-cli 是否真的支援**。

**驗證命令**:
```bash
$ npx -y mmx-cli image generate --help 2>&1 | grep -iE "similar|variation"
# → 0 matches（exit 0 但輸出為空）

$ npx -y mmx-cli image generate --help 2>&1 | grep -iE "seed"
--seed <n>   Random seed for reproducible generation (same seed + prompt = identical output)
```

**正確替換方案**:

| 使用者需求 | 正確 mmx-cli 做法 |
|-----------|------------------|
| 「再來一張類似的」| `mmx image generate --prompt "..." --n 4`（每張隨機種子）|
| 「完全相同再生成一張」| 記錄第一次輸出的 `--seed N`，下次用相同 seed 重跑 |
| 「同角色不同風格」| `--subject-ref 'type=character,image=/path/to/ref.jpg'` |
| 「一次生 4 張變體」| `--n 4`（無 seed = 各自獨立隨機）|

**If→Then 規則**:
- **If** 自己對使用者提到一個 API flag 或 mode 名稱 **Then** 立刻用 `mmx image generate --help | grep <flag>` 驗證是否存在再說出口
- **If** 使用者說「再來一張類似的」**Then** 不要說 `--similar mode`（不存在），改說「用 `--n 4` 一次生 4 張變體」
- **If** 使用者要求「同一張再生成一次」**Then** 告知「需要 `--seed` 才能重現，請提供當時的 seed 值或讓我再跑一次並記錄 seed」

**預防**: 任何 image gen 任務開始前，先問「你想要的是(a)一次生多張變體 (b)同 prompt 重現 (c)同角色換風格」，再選對應 flag。

**相關**:
- `minimax-multimodal-toolkit/SKILL.md` — "Confabulated API Features" pitfall 已加入 image generate flags 說明
- `minimax-multimodal-toolkit/references/confabulated-api-features-20260630.md` — 完整 self-detection + correction 流程
