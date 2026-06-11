# 建新常駐 Profile 評估 Checklist (resident-profile-onboarding)

> 從 `general-workflow` 的「建新常駐 profile SOP」pattern 抽出來的具體評估 checklist + 範例。配合 2026-06-11 實戰（test-engineer 建立 + 「全能工程師」評估不建案例）。

## 何時用這個檔

收到以下任一訊號：

- 「建一個 X 代理」「建一個常駐 profile」「新增一個角色」「我要個 X agent」
- 「X 該接在 chain 第幾棒」「補上 X」「下一個是 X」
- chain 缺一環（handoff 流程跑到一半、下一棒不存在）

## Step 1: 評估 (5 個核心問題)

### Q1: 用戶說的「X 代理」是「新身份」還是「舊身份重塑」？

- **新身份**: 從零撰寫 persona + SOUL
- **舊身份重塑**: 備份現有、覆寫、可從歷史 git/gitignore 救回

### Q2: 跟現有 chain 有什麼上下游契約？

- 上游誰給 handoff
- 下游誰接（或不接 = 鏈尾）
- 寫進 `~/.hermes/handoff/README.md`（chain 5 段流程段）

### Q3: 該代理的職責跟現有代理會不會 70%+ 重疊？

**判斷標準**:
- 70%+ 重疊 → 補 skill 給現有 / 不另建
- 30%-70% 重疊 → 考慮重塑
- < 30% 重疊 → 另建

### Q4: 該代理的職責邊界是什麼？

列出 1 句話:
- 角色定位 = [鏈哪一棒] + [職責一句話] + [明確邊界]
- 例: 「E2E/integration/perf 測試 / 接收 engineering-lead 的 sprint 報告, 跑三層測試, 給 PASS/FAIL 決策 / **不**寫 unit test、**不**寫架構」

### Q5: 預估 skill 庫大小（30-60 為目標）

- 列必備的 4 類 skill: 核心 + 工具 + 觀察 + 對外契約
- 對比 default 完整版（195 個）、opt-out 不需要的

## Step 2: 給使用者的評估報告

4 段結構:

```
1. 角色定位
   - 一句話描述該代理做什麼
   - 在 chain 第幾棒
   - 上游誰給 handoff、下游誰接

2. 跟現有代理的職責重疊分析
   - 跟 [代理 A]: N% 重疊
   - 跟 [代理 B]: N% 重疊
   - 如果重疊 > 70%: 補 skill 給現有代理就夠

3. skill 庫預估
   - 預估 30-60 個 skill
   - 必留 4 類 + opt-out 清單

4. 預估工作量
   - 建 + slim + 寫 persona/SOUL: 約 60-90 分鐘
   - 含 4 個專屬 skill: 約 +60 分鐘
   - 總: 2-3 小時
```

## Step 3: 等使用者選 (1 個 `clarify()` 問完所有決策)

4 個關鍵決策:

1. **角色定位** (確認 Q4 答案)
2. **hierarchy 邊界** (上下游契約是否如我列的)
3. **要不要重塑舊的** (如果重疊 > 70%)
4. **要不要保留舊的** (預設「重塑就砍舊」, 用戶明示才保留)

## Step 4: 執行 (5 步 SOP 見 SKILL.md 本體)

| Step | 動作 | 預估時間 | 驗證 |
|------|------|----------|------|
| 1. clone | `hermes profile create <name> --clone --description "..."` | 30 秒 | `hermes profile list` 出現 |
| 2. slim | `hermes -p <name> skills opt-out --remove --yes` + 手動 opt-out 156 個 | 5 分鐘 | `ls .../skills/ \| wc -l` 30-60 |
| 3. 寫 persona | 從零撰寫, ≥ 5KB | 30 分鐘 | `wc -c` 驗 |
| 4. 寫 SOUL | 從零撰寫, ≥ 4KB | 20 分鐘 | `wc -c` 驗 |
| 5. marker | 給 30-60 個 skill 加 .user-modified + 紀錄 | 5 分鐘 | `find ... -name .user-modified \| wc -l` 對 |

## 失敗模式速查

| 症狀 | 原因 | 解法 |
|------|------|------|
| 用戶問「這個代理會怎樣」時回「我有 195 個 skill 不知怎麼選」 | 跳過 slim 精瘦 | 立刻跑 opt-out |
| 改壞 persona 無法 revert | 沒備份 | `cp persona.md /tmp/persona.md.bak.$(date +%s)` |
| 改 SKILL.md 內容被未來 hermes update 覆蓋 | 沒加 .user-modified marker | 給每個 opt-in 進去的 skill 加 touch .user-modified |
| Slim 完後 last_status 卡 error 不翻 | 沒跑真 cron 觸發 | `hermes cron run <name>` + `hermes cron tick` |

## 完整範例: 建 test-engineer（2026-06-11 實戰）

### 評估階段
- 角色: chain 第 5 棒 (鏈尾) / 跑三層測試 / 給 PASS/FAIL
- 跟 engineering-lead: 0% 重疊（一個寫 code、一個驗收）
- 跟 system-architect: 10% 重疊（都看架構文件）
- 預估 skill: 30-50 個

### 決策階段
- 用戶選 B 方案: 完整建（不是重塑）
- hierarchy: 接收 engineering-lead 的 sprint report, 不接下棒（鏈尾）

### 執行階段
- 195 → 38 skills (reduction 80.5%)
- persona 9.8KB (6 步工作流程 + 5 個核心設計決策 + 4 個禁止事項)
- SOUL 6.8KB (語氣特徵 + 互動風格 + 工具偏好)
- 38 個 .user-modified marker

### 驗證階段
- `~/.local/bin/test-engineer chat -q "ping"` → 正確回應（"Pong, test-engineer 在線"）
- `hermes profile list` → 6 個 profile 全在
- 38 個 skill 都有 .user-modified marker

## 完整範例: 不建「全能工程師」（2026-06-11 實戰, 評估後拒絕）

### 評估階段
- 用戶問: 「請繼續完成撰寫程式碼之『全能工程師代理』」
- 跟 engineering-lead: 70%+ 重疊（sprint 跟 code-driven 本質同一件事的兩階段）
- 跟 system-architect: 0% 重疊

### 決策階段
- 給用戶 3 個選項:
  - A. 另建「全棧工程師」profile（90 分鐘）
  - B. 補 4 個 debug skill 給 engineering-lead（5 分鐘）
  - C. 不建, 觀望
- 用戶選 B

### 執行階段
- 補 4 個 skill: debug / systematic-debugging / writing-plans / tech-debt
- engineering-lead skill 81 → 88 (+4 個 opt-in)

### 驗證階段
- 4 個新 skill 都在
- engineering-lead persona 加第 11 條核心信念
- engineering-lead skill 數從 74 → 88

**結論**: 補 4 個 skill 5 分鐘解掉了問題, 不需要 90 分鐘另建 profile

_Last updated: 2026-06-11_
