### creative-pipeline-01 Creative Pipeline Orchestration — DAG 串聯框架缺失（2026-07-13）

**症狀**：用戶提出「做一個宣傳影片」類高階創意目標時，赫米斯缺乏將其分解為 text→image→video→speech 的 DAG 執行框架，導致：
1. 試圖在同一個 prompt 完成所有環節（LLM context 不穩定）
2. 未告知用戶分步驟時序依賴
3. 角色一致性（character continuity）斷裂

**根因**：mmx 6-type taxonomy（Cycle 486-490 已固化）只定義了單步觸發，未定義多步依賴關係。理論確認：「character continuity is an agent problem」（AI Video Production Playbook 2026, Data Science Collective）。

**工具驗證**：mmx video generate 全模式確認可用
```
T2V:  Hailuo-2.3        # text → video
I2V:  Hailuo-2.3 / Hailuo-2.3-Fast  # image → video（--first-frame）
SEF:  Hailuo-02         # first+last frame → video interpolation（--last-frame）
S2V:  S2V-01             # subject reference → video（--subject-image，角色一致性）
--async / --no-wait     # 非同步（agent mode）
--poll-interval <sec>   # 輪詢間隔
```

**DAG 邏輯**（mmx 工具鏈）：
1. `mmx image generate --subject-ref <角色圖>` → 固定角色參照
2. `mmx video generate --subject-image <角色圖> --prompt "..."` → 以角色圖為參照生成影片（S2V-01，--async --quiet）
3. `mmx speech synthesize` → 配音/narration
4. `mmx music generate` / `mmx music cover` → 背景音樂或翻唱版本
5. 最終產出拼接

**music cover 模式**（Cycle 489 驗證）：`mmx music cover` 為獨立子命令，輸入為參考音訊 URL，輸出為翻唱版本。適用於：用戶想用自己喜歡的歌曲風格生成類似音樂。

**If→Then**:

**If** 用戶描述一個包含「做一個影片/宣傳/動畫」類型的創意任務  
**Then** 先識別該任務隸屬於 6-type taxonomy 的哪個主軸（video/music/speech），再用 DAG 思維檢查上游依賴：
- 視頻類任務：上游 = image generate（角色圖）→ video generate（--subject-image 角色一致性）→ speech synthesize（配音）→ 最終產出
- 每個下游環節都需等待上游完成後以 `--async --quiet` 模式輪詢
- 不要試圖在同一個 prompt 內完成所有環節，明確告知用戶分步驟執行的時序

**驗證命令**：
```bash
timeout 10 npx -y mmx-cli video generate --help 2>&1 | grep -E "T2V|I2V|SEF|S2V|--subject-image"
# 應顯示：T2V: Hailuo-2.3, I2V: Hailuo-2.3, SEF: Hailuo-02, S2V: S2V-01
# 應顯示：--subject-image（角色一致性）, --async/--no-wait, --poll-interval
```

**預防**：新增 `minimax-multimodal-toolkit/references/creative-pipeline-orchestration.md` 單一 SOP，涵蓋意圖分類 → DAG 依賴圖 → 各工具 `--async` 串聯 → 輪詢閉環的完整決策鏈。觸發：當創意 session 意圖包含 2+ 個 6-type 類型（即需要 pipeline）時，立即啟動此 runbook。

**If→Then 深化（Cycle 494 補充）**：

**If** 用戶想要角色一致性（同一個人物出現在多個鏡頭中）
**Then** 使用 `mmx video generate --subject-ref "type=character,image=<path>" --model S2V-01`（不是 --first-frame）
**Why** --first-frame 綁定的是「風格」，S2V-01 綁定的是「角色身份」；两者是不同需求

**If** 用戶想要一個「宣傳影片/動畫/多鏡頭」
**Then** 先做意圖分類（Diagrid orchestration framework）：
- 識別該任務需要哪些 6-type 類型（image? video? speech? music?）
- 畫出 DAG：哪個步驟依賴哪個步驟的輸出
- 告知用戶分幾步、每步產出什麼、預計等待時間
- 用 `--async --quiet` 模式輪詢下游步驟

**If** DAG 中某步失敗
**Then** 不重跑整個 pipeline——Diagrid durable execution 原則：每步結果獨立持久化，只重跑失敗步驟

**相關條目**：[[creative-skills-dependency-gap-20260616]], [[ai-tools-usage.md]]
