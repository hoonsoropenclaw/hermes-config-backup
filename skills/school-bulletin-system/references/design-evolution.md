# 學校公告系統設計演進（v1→v4）

> 本檔案記錄 matchAudience 受眾匹配邏輯的演進。未來任何人要改 audience 邏輯，必須先讀完本檔。

## 設計聖經

**「登入後能看到的 >= 未登入」**

這是最高指導原則。違反這條會讓「登入」變成負面動機。

---

## v4（C 方案最終版，2026-06-11 定案）

**核心邏輯**：任何角色都看全部公告，不做 audience 過濾。

**為什麼廢棄 v3 的 audience 過濾**：
1. 「登入後能看到的 >= 未登入」是設計聖經
2. 登入的價值 = 看到內部公告，不是 audience 命中
3. 在「內部公告」機制未建立前，受眾不該被 audience 阻擋
4. 否則 teacher_lin 登入後看到比訪客還少 → 登入動機消失 → 設計 bug

**實作**：
```typescript
// route.ts GET — 不做任何 audience 過濾
const items = await listAnnouncements(filter, /* 無 audience 限制 */)

// route.ts POST/PATCH/DELETE — 只有 dept_officer 和 sysadmin 可操作
if (me.role !== 'dept_officer' && me.role !== 'sysadmin') {
  return 403
}
```

**E2E 驗證**：
- 訪客（無 cookie）→ 4 個 ✅
- 6 個處室帳號 → 4 個 ✅
- teacher_lin → 4 個 ✅
- parent_chen → 4 個 ✅
- student_wang → 4 個 ✅
- 受眾帳號 POST 公告 → 403 ✅
- 處室帳號 POST 公告 → 201 ✅

---

## v3（廢棄）

**邏輯**：訪客看公開、處室看全部、受眾看 audience 命中

**廢棄原因**：違反「登入後 >= 未登入」聖經

---

## v2（廢棄）

**邏輯**：受眾帳號 role = teacher/parent/student（不再用 dept_officer），API POST/PATCH/DELETE 擋非處室

**廢棄原因**：角色矩陣是對的，但 matchAudience 邏輯不對

---

## v1（廢棄）

**邏輯**：教務處只看到教務處的、訓導處只看到訓導處的（處室隔離）

**廢棄原因**：違反直覺，處室承辦應該知道各處室在發什麼，不能被 audience 阻擋

---

## 未來：內部公告機制

若未來要重啟 audience 分流：

1. `announcements` 表加 `audience_type: 'public' | 'internal' | 'role_specific'` 欄位
2. `matchAudience` 加邏輯：
   - `audience_type === 'public'` → 所有人可見
   - `audience_type === 'internal'` → 需登入
   - `audience_type === 'role_specific'` → 用 `role_tag_ids` 命中
3. **E2E 測試重點**：確認 teacher_lin 登入後看到的 >= 訪客

## SOP：改 audience 邏輯前

1. 先在本檔案新增一筆決策（時間/觸發/上一版/這版/為什麼/E2E/決策者）
2. 更新 `matchAudience` 實作
3. 跑 E2E 驗證（訪客 + 各角色）
4. **必須滿足**：任何人登入後看到的公告數 >= 同一時間未登入看到的數量
