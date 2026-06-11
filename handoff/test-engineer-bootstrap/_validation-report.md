# Test-Engineer 首次驗證報告

> **驗證日期**: 2026-06-11
> **驗證者**: default orchestrator (主要 session)
> **被驗證對象**: test-engineer profile + 4 個新 opt-in skill
> **session ID**: `20260611_121230_22c9c4`
> **結果**: ✅ **PASS** —— 4 個 skill 全部載入、決策矩陣正確套用、互引用機制運作正常

---

## 1. 驗證目標

test-engineer 在 2026-06-11 11:38 完成 profile 建立（slim 到 38 個 skill），並新增 4 個專屬 skill：
- `test-environment-bootstrap` (從 arch 段落建立 test env)
- `e2e-suite-runner` (從 sprint ticket 自動生成 Playwright E2E)
- `bug-report-generator` (從失敗 log 生成 .docx bug 報告)
- `sprint-qa-signoff` (從三層測試結果生成 signoff + PASS/FAIL 決策)

**問題**: 這 4 個 skill 真的能在 test-engineer session 內被讀到嗎？決策矩陣真的會被套用嗎？

---

## 2. 驗證方法

3 個問題，分別測試「載入」、「靜態決策」、「跨 skill 互引用」：

### Q1: 4 個 skill 都載入得到嗎？
**預期**: test-engineer 列出 4 個 skill 的 description，內容跟 SKILL.md 寫的一致

### Q2: 假設情境下的 PASS/FAIL 決策
**題目**: sprint-1 跑完，unit/integration/E2E 全 PASS，但 performance 測試超標 30%，severity S2，SLA 是 5s 實測 6.5s，PERF-001 不是核心交付
**預期**: test-engineer 引用 sprint-qa-signoff SKILL.md「性能超 SLA」條款、給 FAIL、明確說「SEV2 非核心不等於豁免」

### Q3: Critical bug 的決策
**題目**: 只有 E2E 失敗一個 ticket（SEV1、production 阻塞）、其他都 PASS
**預期**: test-engineer 引用「1 個 critical bug = FAIL（不管其他多完美）」條款、給 FAIL、建議跑 bug-report-generator

---

## 3. 驗證結果（test-engineer 實際回應）

### Q1 結果: ✅ PASS

test-engineer 列出 4 個 skill 的 description，全部跟 SKILL.md frontmatter 一字不差：

```
1. test-environment-bootstrap
   從 arch-<slug>.md 的 docker-compose 段落建立 test environment、跑 smoke test、
   確認所有服務 healthy。test-engineer 跑任何測試前必走。

2. e2e-suite-runner
   從 sprint-<N>-report.md 的 Given/When/Then ticket 自動生成 Playwright E2E 測試、
   跑、回報。test-engineer 跑 E2E 時必走。

3. bug-report-generator
   從失敗的 E2E / integration / performance test log 自動生成 .docx bug 報告。
   test-engineer FAIL sprint 必用。

4. sprint-qa-signoff
   從三層測試結果（unit + integration + E2E + performance）+ bug 清單生成
   sprint-N-qa-signoff.md + PASS/FAIL 決策。test-engineer 唯一對外的交付物、必走。
```

**結論**: 4 個 skill 都被載入、frontmatter 內容 100% 一致。

---

### Q2 結果: ✅ PASS（決策 FAIL，依據正確）

**test-engineer 給的決策**:
```
決策: ❌ FAIL
依據是 sprint-qa-signoff SKILL.md Step 2 的決策矩陣(原樣引用):

  ┌─────────────────────────────────────────────────────────────┐
  │                    PASS / FAIL 決策矩陣                      │
  ├─────────────────────────────────────────────────────────────┤
  │ 全 ticket PASS + 沒 critical bug + 性能在 SLA 內  → ✅ PASS │
  │ 1-2 個 minor bug + 性能在 SLA 內                  → ⚠️ COND  │
  │ 有 critical bug / 性能超 SLA / >30% ticket FAIL  → ❌ FAIL  │
  └─────────────────────────────────────────────────────────────┘

第三條的 3 個觸發條件是用 OR 連接（任一成立就 FAIL），「性能超 SLA」就是其中
一個明確觸發條件。
```

**test-engineer 額外給的補充**:
- 題目情境: SLA 5s、實測 6.5s → 超 SLA 30%（踩「性能超 SLA」）
- PERF-001 是不是核心交付 / SEV2 多輕微 → **矩陣沒給降級條款**
- SOP「注意」段明確寫:「性能 p95 差 50% SLA 內但 p99 超 SLA = 看架構怎麼定義
  (default = FAIL)」 —— 預設就是 FAIL、沒有「非核心性能超標可以放行」的例外

**結論**: test-engineer **直接引用 SKILL.md 原句**、正確套用 OR 邏輯、識別「題目陷阱」（SEV2 非核心想誤導成 CONDITIONAL）、明確拒絕降級。

---

### Q3 結果: ✅ PASS（決策 FAIL，依據 + 跨 skill 引用都正確）

**test-engineer 給的決策**:
```
決策: ❌ FAIL
依據是 sprint-qa-signoff SOP「注意」段（原樣引用）:
  「1 個 critical bug = FAIL（不管其他多完美）」

題目情境完全踩中:
- E2E 一個 ticket FAIL + SEV1 = critical + production 阻塞
- critical 定義（來自 bug-report-generator SOP）:「主流程全斷、無 workaround」
- 其他全 PASS（踩不到第一條「全 ticket PASS」） — 對 FAIL 結果無影響
```

**test-engineer 額外給的 4 步退工程流程**:
1. 跑 bug-report-generator 生成 .docx（SEV1 critical 加紅色標記）
2. 立刻 flag 給主 session（SEV1 = 立刻 flag）
3. 退回 engineering-lead、附「為什麼退回」清單
4. 不 merge、觸發 engineering-lead 修 bug + 新 sprint 重測

**結論**: test-engineer **跨 skill 引用 bug-report-generator 的 critical 定義**、**自動決定觸發下個 skill**、**完整退工程流程**。

---

## 4. 整體結論

| 驗證項 | 結果 |
|--------|------|
| 4 個新 skill 載入 | ✅ 全載入、description 100% 一致 |
| sprint-qa-signoff 決策矩陣 | ✅ OR 邏輯正確、不模糊 |
| bug-report-generator 互引用 | ✅ Q3 自動決定觸發 |
| 抗「題目陷阱」能力 | ✅ Q2 拒絕 SEV2 降級、堅持矩陣 |
| 「為什麼退回」清單 | ✅ 兩個情境都給完整理由 |
| 工作流閉環 | ✅ sprint-qa-signoff → bug-report-generator → flag 主 session → 退工程 → 重測 |

**test-engineer 已就緒、可在 handoff chain 第 5 階段正常運作。**

---

## 5. 副作用紀錄

- 新 session 留在 history: `20260611_121230_22c9c4`（`hermes --resume 20260611_121230_22c9c4 -p test-engineer` 可恢復）
- 沒新建任何外部檔案、沒改任何設定
- `_plan.md` + 本檔共 2 個檔寫入 `~/.hermes/handoff/test-engineer-bootstrap/`

---

## 6. 後續可觀察

- 第一次真實 sprint 跑完後，test-engineer 會不會真的寫 `qa-signoff.md` 進 `~/.hermes/handoff/<project>/`
- 4 個 skill 在真實 docker / playwright / .docx 環境下能不能正常運作（這次是純 SOP 推理測試）
- default orchestrator 自動觸發下個代理的機制（目前手動、未來可考慮 cron 監控 `~/.hermes/handoff/<project>/` 出現新檔）

---

**驗證者簽名**: default orchestrator @ 2026-06-11 12:23
