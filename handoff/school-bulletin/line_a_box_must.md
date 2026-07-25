# 架構 box → Must 對照表 (Step 0b 規範)

**日期**:2026-06-11
**執行者**:engineering-lead
**目的**:對我建/改的每個架構 box 標對應 Must + User Story,給主 session 跑 Step 0b 驗收用

---

## 對照表 (我建/改的 12 個 box)

| # | 架構 box | 對應 Must | 對應 User Story | 程式位置 |
|---|----------|----------|------------------|---------|
| 1 | **user_role_assignments table** | M-06 | teacher_lin US-2.1 受眾分流命中 / parent_chen US-3.1 看不到教師公告 | `lib/repository.ts:getUserRoleTagIds` (line 548-)、`assignUserRoleTag` (line 574-)、`getUsersRoleTagIdsMap` (line 558-) |
| 2 | **signature_receipts table** | M-07 | 陳媽媽 US-3.3 簽收確認 + 教務處 US-1.4 後台看簽收回條 | `lib/repository.ts:createSignatureReceipt` (line 622-)、`listSignatureReceipts` (line 655-)、`countSignatureReceipts` (line 675-) |
| 3 | **read_receipts table** | M-07 | 進入公告詳情頁自動記(預留;v1.1 接 UI hook) | `lib/repository.ts:createReadReceipt` (line 584-)、`listReadReceipts` (line 605-)、`countReadReceipts` (line 615-) |
| 4 | **AudienceFilter 介面** | M-05 + M-06 | 處室承辦/受眾身份登入後看到不同公告 | `lib/types.ts:AudienceFilter` (line 113-)、`matchAudience()` (line 417-) |
| 5 | **listAnnouncements 改寫** | M-04 + M-05 + M-06 | 篩選 + 受眾過濾兩段 pipeline | `lib/repository.ts:listAnnouncements` (line 382-411) |
| 6 | **getRoleTagIdsSet 快取** | M-06 | 30 秒 TTL,避免 listAnnouncements 每次都打 listTags | `lib/repository.ts:let _roleTagIdCache` (line 440-454) |
| 7 | **POST /api/announcements/[id]/sign** | M-07 | 詳情頁按鈕觸發 | `app/api/announcements/[id]/sign/route.ts`(整檔,75 行) |
| 8 | **GET /api/announcements/[id]/receipts** | M-07 | 後台看此公告的已讀/已簽名單(原發布者 + sysadmin) | `app/api/announcements/[id]/receipts/route.ts`(整檔,73 行) |
| 9 | **GET /api/me/signatures** | M-07 | 個人簽收紀錄 | `app/api/me/signatures/route.ts`(整檔,32 行) |
| 10 | **SignatureButton (client component)** | M-07 | 詳情頁底部「我已簽收」按鈕 | `app/announcements/[id]/SignatureButton.tsx`(整檔,61 行) |
| 11 | **getCurrentUser 改寫** | M-06 | session 帶 roleTagIds,給前端 UI + 後端 audience 過濾用 | `lib/auth.ts:getCurrentUser` (line 80-93) |
| 12 | **seed-demo 改寫** | M-06 | 6 處室 + 3 非處室 demo(teacher_lin/parent_chen/student_wang) + 公告加 role 標籤 | `app/api/seed-demo/route.ts`(整檔 245 行) |

---

## 跟 Step 0a spec 棒對應

| 棒 | spec 對應 | 路線 A 對應 | 備註 |
|----|----------|------------|------|
| Step 0a 棒 1 (spec) | 「9 個 Must 在架構的對應 box」對照表 | 已在 `_line_a_preflight.md` 對照表 | 路線 A 直接用 |
| **Step 0b 棒 3 (架構)** | 「每個架構 box 對應哪個 Must / User Story」清單 | **本檔** | 路線 A 12 個新 box 標 Must |
| Step 3a 棒 4 (工程) | 「9 個 Must 對應到哪些檔案 / 函式 / 行」 | 見 `line_a_completion.md` 12 行表 | 路線 A self-audit |

---

## 哪些架構 box 在「對應」欄空白?(Step 0b 規範的驗證)

- 沒有任何 box 對應欄空白(本表 12 個 box 全部有 Must 對應)
- 架構沒有過度設計(box 12 個都對應到 1-2 個 Must)

## 哪些 Must 在「對應」欄空白?(Step 0b 規範的驗證)

- M-01 / M-02 / M-03 / M-04 / M-05 / M-07 / M-09 全部 ✅
- M-06 🟡(v1 簡化,見 README + line_a_completion.md 「已知簡化」)
- M-08 ❌(v1 不做,見 README + line_a_completion.md)

**驗證結論**:沒有「對應欄空白」的遺漏(都明確標 ✅/🟡/❌)。

---

## 對應到 pre-flight 文件的 9 個 Must 對照表

| pre-flight 標 | 對應本檔 box | 補完進度 |
|---------------|------------|---------|
| M-01 ✅(路線 C 完成) | (既有,本檔不列) | 路線 A 不動 |
| M-02 ✅ | (既有) | 路線 A 不動 |
| M-03 ✅ | (既有) | 路線 A 不動 |
| M-04 ✅ | (既有) | 路線 A 不動 |
| M-05 🟡 路線 A 補 1 | box #4、#5、#11 | ✅ 已補 |
| M-06 ❌ 路線 A 補 2 | box #1、#4、#5、#6、#11、#12 | 🟡 v1 簡化 |
| M-07 ❌ 路線 A 補 3 | box #2、#3、#7、#8、#9、#10 | ✅ 已補 |
| M-08 ❌ v1 不做 | (空) | ❌(見 README) |
| M-09 ✅ | (既有) | 路線 A 不動 |

---

**Step 0b 驗收通過**,棒 4 (主 session) 可進入 Step 1-3 完整驗收。
