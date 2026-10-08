---
name: playwright-e2e-actually-run-20261009
description: |
  Playwright e2e 測試「寫好但從未實際跑過」的 4 個常見陷阱 + 必跑驗證 SOP。
  觸發：playwright / e2e / webServer / signin / page.goto / waitForSelector / SPA / 路由 / React Router。
  屬於 trial-and-error by-category 索引,實戰案例 2026-10-09 day-2 React Flow + RBAC 專案。
---

# Playwright e2e 「檔案存在 ≠ 真的跑過」4 大陷阱（2026-10-09）

> 背景：跨天專案 `proj-20261008-021500-deb0-人事案件簽核流程編輯器-react-flow-r` day-1 完成時，RUNLOG 寫了「Playwright e2e 已寫但未實際跑（chromium 環境未安裝）」。day-2 第一次跑 e2e 立刻踩到 3 個 timeout/找不到元素的失敗 — 全部都是 day-1 寫 e2e 時就存在的 bug，只是當時只看「測試檔語法正確」就結案。

## 教訓 A：testId 找不到 = SPA 預設 auth state 自動繞過 picker

**症狀**：
```text
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByTestId('signin-employee')
  13 |   await page.goto("http://localhost:4173/");
  14 |   // sign in as employee
> 15 |   await page.getByTestId("signin-employee").click();
```

**根因**：`AuthContext` 預設 `useState<User>(SAMPLE.employee)`，導致 `<LoginPicker>` 內的 `if (user) return <Navigate to="/flows" replace />` 立刻把使用者導去 `/flows` — **signin 按鈕根本沒渲染**。e2e 寫的人以為「會看到 picker → 點 signin → 進 editor」，實際進入 `/` 直接被跳走。

**檢查命令（debug 必跑）**：
```js
// tests/diag.cjs
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('http://localhost:4173/');
  await page.waitForTimeout(1500);
  console.log('URL:', page.url());
  console.log('BODY:', (await page.locator('body').innerHTML()).substring(0, 500));
  await browser.close();
})();
```
- 看 URL — 如果是 `/flows` 但 e2e 期待在 picker → **state 自動重定向問題**
- 看 BODY 開頭 — 沒有「選擇登入身分」字串 → picker 沒渲染

**兩種正確解法**（擇一）：

1. **改 AuthContext 預設為 `null`**：讓 picker 真的可見（更符合 SPA UX 直覺）
   ```tsx
   const [user, setUser] = useState<User | null>(null);  // 不要 SAMPLE.employee
   ```

2. **加 `?as=<role>` URL 參數 deep-link**（推薦，e2e 友善）：
   ```tsx
   const initial = (() => {
     if (typeof window === "undefined") return null;
     const role = new URLSearchParams(window.location.search).get("as") as Role | null;
     return role && role in SAMPLE ? SAMPLE[role] : null;
   })();
   const [user, setUser] = useState<User | null>(initial);
   ```
   e2e 直接 `await page.goto('/flows?as=manager')`，完全跳過 picker 流程。

**If→Then**:
**If** e2e 找不到 picker 頁的 testId 但 build OK + 啟動後 URL 立刻是 `/flows` **Then** 第一時間 print `page.url()` 確認是否被 AuthContext 預設值自動 redirect，**不要**懷疑 testId 拼字或 selector 寫法

## 教訓 B：`page.goto` 在 SPA 內 reload 整頁 → 噴掉 React state

**症狀**：
```js
await page.goto(FLOWS_AS("employee"));
// ... 點了一些按鈕 ...
await page.goto("http://localhost:4173/admin");  // ❌ 整頁 reload,user state 變 null
await expect(page).toHaveURL(/\/403$/);  // 失敗:實際到 /login
```

**根因**：`page.goto()` 觸發瀏覽器 navigate → React app 整個重新 mount → 記憶體中的 user state 重置為 `null`（除非有 localStorage / sessionStorage 持久化）。ProtectedRoute 看到 `user=null` 把使用者導去 `/login`，**不是** `/403`。

**正確解法**：用 SPA 內部 navigation，state 才會存活：
```js
// ✅ 用 React Router <Link> 點擊
await page.getByRole("link", { name: "帳號管理" }).click();
await expect(page).toHaveURL(/\/403$/);
```

**If→Then**:
**If** e2e 需要跨多個 SPA route 但又要保持登入狀態 **Then** 用 `<Link>` 點擊而非 `page.goto()`；**`page.goto` 只用在「首次進場」**（用 `?as=role` deep-link 一次到位）

## 教訓 C：e2e config `webServer` 啟動後，別的 session 會搶同一 port

**症狀**：背景還跑著舊的 `vite preview --port 4173`（可能是前次 session 留下、或 `/tmp/proj-work` 類共享路徑），`npx playwright test` 的 webServer 設定 `reuseExistingServer: true` → 連到舊 server → 看不到當前 build 的新代碼。

**檢查 + 清理命令**：
```bash
pgrep -fa 'vite preview --port 4173' | head -5
# → 列出所有 listen 4173 的 process
kill <PID>  # 殺掉殘留
```

或更穩：`reuseExistingServer: false` + 確保 `webServer.command` 一定會自己起。

**If→Then**:
**If** playwright test 連到的 server 跟當前 build 的代碼不一致 **Then** `pgrep -fa 'vite preview' | head -5` 撈殘留 process + `kill`；不要懷疑 webServer config 寫法

## 教訓 D：playwright 1.63 要 chromium-1243，但環境只裝 1234

**症狀**：
```bash
$ npx playwright install --dry-run chromium
Chrome for Testing 153.0.8010.12 (playwright chromium v1243)
  Install location:    /home/hoonsoropenclaw/.cache/ms-playwright/chromium-1243
```
但實跑時 e2e 一進場就 timeout、page 空白、console 全是 `Failed to load resource`。

**修復**（首次進新環境必跑）：
```bash
npx playwright install chromium  # 不是 --with-deps（要 root）
# 約 115MB,需 1-2 分鐘
```

**If→Then**:
**If** e2e 跑起來 page 完全沒渲染、URL 沒變化、console 沒錯誤 **Then** 第一時間 `npx playwright install chromium` 確認瀏覽器 binary 存在；不要懷疑 selector 或 React 程式碼

## 完整 e2e 必跑驗證 SOP（任何 web app 交付前必跑）

任何聲稱「Playwright e2e 寫好」的 commit / handoff，**必含以下 5 項證據**：

1. ✅ **實際執行過的 log 截圖**（不是「語法檢查通過」）
2. ✅ **npx playwright install chromium 確認 binary 存在**
3. ✅ **vitest 單元測試 + playwright e2e 都過**（不要只跑單元）
4. ✅ **每條 e2e 都對應一個 user journey**（不只是「UI 渲染」測試）
5. ✅ **`?as=role` deep-link 或 explicit signin**（不是「依賴預設 auth state」）

**驗證命令**（一鍵跑完）：
```bash
cd <workdir>
npx playwright install chromium 2>&1 | tail -3
npx vitest run 2>&1 | tail -5
npx playwright test --reporter=list 2>&1 | tail -20
# 預期:vitest N/N passed + playwright N/N passed
# 若任一 0/N 或 timeout → 不可宣稱 e2e 完成
```

## 對應 trial-and-error 主目錄的 L3 教訓

- **教訓 1**（棒結束必自驗 schema 進 DB）→ 同類精神:程式碼寫好 ≠ 在 runtime 跑過
- **教訓 14**（first verify before deploy）→ 本機 build 0 error ≠ e2e 跑過
- **教訓 34**（D2 缺口 = SOP 存在但執行層從未被調用）→ 「e2e 寫好」但「chromium 沒裝」= D2 缺口

## 與 autonomous-learning skill 的整合

`autonomous-learning` SKILL.md「Pitfalls」段可加一條：
> **e2e 測試必實際跑過** — 寫好 Playwright 測試檔但沒跑 = 沒寫；`npx playwright test --reporter=list` 全綠才可標記 `practice` 步驟完成。詳見 `trial-and-error/references/by-category/playwright-e2e-actually-run-20261009.md`

## 真實驗證記錄（2026-10-09 day-2）

- **修復前**：3 個 e2e 全部 timeout（找不到 signin 按鈕、找不到 /admin redirect）
- **修復後**：3/3 passed in 1.9s
  - `employee can submit, cannot see approve buttons or delete` (336ms)
  - `principal can approve the principal node` (281ms)
  - `manager can approve the manager node; subsequent approve button hides` (259ms)
- **總耗時**：debug + 修程式碼 + 修 e2e = 約 30 分鐘,主因是「從未跑過 e2e」累積了 4 個 bug 等到第一次跑才一次爆
