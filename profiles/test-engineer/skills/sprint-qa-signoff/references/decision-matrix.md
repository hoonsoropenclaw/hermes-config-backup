# PASS/FAIL 決策矩陣詳細規則

## 決策規則（嚴格版）

### 1. 全 PASS 條件（必須**全部**滿足）

- [ ] 所有 ticket 都有 PASS（unit + integration + E2E 都要過）
- [ ] 沒 critical bug
- [ ] 沒 major bug（除非有明確 workaround）
- [ ] minor bug 數量 ≤ 3 個
- [ ] Performance p95 延遲 ≤ SLA 定義
- [ ] Performance p99 延遲 ≤ SLA 定義
- [ ] 併發 N RPS 錯誤率 < 0.1%
- [ ] test env 沒出問題

→ 結果：**✅ PASS**（可 merge to main）

### 2. CONDITIONAL PASS 條件（**任一**滿足且沒 FAIL 條件）

- [ ] 1-3 個 minor bug（不影響主流程）
- [ ] 1 個 major bug 但有明確 workaround（UX 差但不阻斷）
- [ ] Performance 邊緣值（p99 超 SLA 但 p95 還在）
- [ ] flaky test 1-2 個（測試不穩定、不是程式碼問題）

→ 結果：**⚠️ CONDITIONAL PASS**（merge 但下個 sprint 必加 bug fix ticket）

### 3. FAIL 條件（**任一**滿足）

- [ ] **任何 critical bug**（主流程全斷、無 workaround）
- [ ] **任何 major bug**（主流程部分壞、即使有 workaround）
- [ ] **>30% ticket FAIL**（5 個 ticket 2 個 FAIL = 40% = FAIL）
- [ ] **Performance 顯著超 SLA**（p95 超 50%）
- [ ] **整合錯誤**（unit 都過但整合壞 = 工程問題、不是測試問題）
- [ ] **test env 起不來**（持續 30 分鐘、嘗試 3 次都壞）
- [ ] **資料損壞**（migration 跑失敗、seed 跑失敗）

→ 結果：**❌ FAIL**（sprint 退回 engineering-lead）

## 模糊地帶的判斷

### Q：3 個 minor bug 算 PASS 還是 CONDITIONAL？
- A：**CONDITIONAL**（不是 PASS）。PASS 嚴格要求 ≤ 3 個 minor bug、3 個就剛好踩線。

### Q：1 個 major bug 但 performance 完美算什麼？
- A：**FAIL**。major bug 阻斷主流程、無法 CONDITIONAL PASS 蓋掉。

### Q：所有 unit test 過、E2E 全壞、算 PASS 嗎？
- A：**FAIL**。unit 跟 E2E 都重要、E2E 壞 = 整合錯誤 = 嚴重工程問題。

### Q：性能 p99 比 SLA 高 5%、其他完美算什麼？
- A：**CONDITIONAL**（不是 FAIL）。5% 是邊緣值、紀錄在下個 sprint 修。

### Q：30% ticket FAIL 但全 minor bug 算什麼？
- A：**FAIL**（條件已觸發）。FAIL 條件是 OR、minor 還是 major 不重要。

### Q：test env 起來 50% 機率、跑 5 次失敗 2 次、算什麼？
- A：**CONDITIONAL**（flaky 算 CONDITIONAL）。但**記下來**、下個 sprint 必修 test env 穩定性。

## 給主 session 的決策溝通格式

每次 sprint signoff、給主 session 一句話總結：

```
Sprint <N> 決策：<PASS / CONDITIONAL PASS / FAIL>
理由：<一句話>
需後續動作：<merge / 補 bug fix / 退回 engineering-lead>
```

範例：

```
Sprint 3 決策：CONDITIONAL PASS
理由：1 個 minor bug（個人頭像上傳）、其他全 PASS
需後續動作：merge + 下個 sprint 加 bug fix ticket
```

## 決策的不可逆性

- PASS → merge：可逆（下個 sprint 可 revert）
- CONDITIONAL PASS → merge：可逆但成本高（merge conflict）
- FAIL → 退回：可逆（修完重跑）
- **不要**「partial merge」（merge 一半、另一半等修）→ 引入 conflict、難追蹤
- **不要**「sprint 延長」（FAIL 不修、繼續下個 sprint）→ 累積技術債

## 重跑測試的時機

跑完 sprint-qa-signoff 後、**主 session 不應該立刻 merge**——應該：

1. 主 session 看 signoff、決定 PASS / CONDITIONAL PASS / FAIL
2. 若 CONDITIONAL PASS：使用者要明確「merge」才 merge（不是自動）
3. 若 FAIL：sprint 結束、進「bug fix sprint」、跑完再 signoff
4. **不要**「我覺得 PASS、看起來差不多」直接 merge

## 給工程團隊的回饋

sprint signoff 後、test-engineer 應該回饋：

### 給 engineering-lead
- 哪些 unit test 寫得不夠（從 integration 失敗推回去）
- 哪些 Given/When/Then 寫得不夠具體
- 哪些 component 風險高（從 bug 集中度看）

### 給 product-planner
- 哪些 User Story 的 Acceptance criteria 不夠嚴謹（從 bug 重現難度看）
- 哪些功能沒有測試計畫（沒在 sprint report 列出 E2E 重點）

### 給 system-architect
- 哪些架構決策導致整合測試難跑（docker compose 起不來 = arch 設計問題）
- 哪些 API 設計讓 E2E 難寫（要繞路、缺 data-testid）

**寫進** `qa-history.md` 累積、給下個 sprint 規劃用。

_Last updated: 2026-06-11_
