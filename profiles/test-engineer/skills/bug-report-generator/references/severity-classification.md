# Bug Severity 分類指南

## 分類決策樹

```
Q1: 主流程完全壞了？
  YES → critical
  NO ↓
  
Q2: 主流程部分壞、無 workaround？
  YES → major
  NO ↓

Q3: 主流程有 workaround 但 UX 差？
  YES → major
  NO ↓

Q4: 主流程不影響、只是邊角功能壞？
  YES → minor
```

## 各類型定義 + 例子

### Critical（sprint 必 FAIL）

| 場景 | 例子 |
|------|------|
| 登入完全壞 | 任何 email/password 都 500 |
| 付款壞 | 結帳回 500、使用者扣款但訂單沒建 |
| 資料丟失 | 編輯文章後、原文消失 |
| 安全漏洞 | SQL injection、XSS 任意代碼執行 |
| 主要功能 0% 可用 | 整個 SPA 白屏 |

**處理**：立刻 flag 給主 session、sprint 不可能 PASS。

### Major（sprint 必 FAIL 除非有 workaround）

| 場景 | 例子 |
|------|------|
| 註冊壞但登入可用 | 新使用者進不來、現有使用者 OK |
| 第三方整合壞 | Stripe webhook 壞、付款狀態不更新 |
| 行動版壞 | 桌機 OK、手機完全不能用 |
| 重要功能 50% 可用 | 編輯文章能存、但不能上傳圖 |
| 主要 bug 影響 >30% 使用者 | 中文輸入法在某瀏覽器壞 |

**處理**：sprint 必 FAIL、除非有明確 workaround（如「用桌機版就好」）。

### Minor（sprint 可 CONDITIONAL PASS）

| 場景 | 例子 |
|------|------|
| 個人頭像上傳壞 | 顯示預設頭像、其他功能 OK |
| 次要 UI 對齊 | 按鈕偏 2px、但功能正常 |
| 邊角功能壞 | 刪除文章後沒跳轉回首頁、但停留在原地 OK |
| 錯誤訊息不明確 | 「操作失敗」但沒說為什麼 |
| 慢 1-2 秒但能完成 | API 從 200ms 變 400ms |

**處理**：3 個以下 minor = CONDITIONAL PASS、4 個以上 = 退回修。

## 同一個 bug 算一次還多次

| 場景 | 算幾次 |
|------|--------|
| 5 個使用者都遇到同一個登入 bug | **算 1 次**（critical） |
| 不同模組的 5 個不同 bug | **算 5 次**（各自處理） |
| 同一個 component 的 3 個小 bug | **算 3 次**（但顯示「同模組集中」） |
| 同一個 component 的 10 個小 bug | **算 1 次 major**（component 整體有問題） |

**原則**：以**使用者感受**為準——使用者感受到 1 個問題 = 1 個 bug、5 個不同問題 = 5 個 bug。

## 邊界 case

### Q: 登入能用但慢 5 秒、算 critical 還是 minor？
- A: **major**（不是 critical 因為能用、不是 minor 因為影響所有使用者）

### Q: 偶爾壞、20% 機率、算什麼？
- A: 看場景——20% 機率 = 5 個人 1 個遇到、主流程 = major、邊角 = minor

### Q: 視覺問題（按鈕顏色不對）算 bug 嗎？
- A: 算 minor（不影響功能、但影響體驗）

### Q: 文件錯誤（API spec 寫 GET、實際是 POST）算 bug 嗎？
- A: 算 minor（工程問題、不是使用者問題、但要修）

### Q: 安全性問題但沒被 exploit 過？
- A: **critical**（不管有沒被利用、都是 critical）

_Last updated: 2026-06-11（bug-report-generator 附錄）_
