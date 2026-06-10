# Google Cloud Console 2025-2026 UI 改版陷阱

> **寫這篇的由來**：2026-06-07 跟使用者建立 YouTube OAuth 用戶端時，我跟使用者**都卡在「重新導向 URI 設定區找不到」**，浪費了 4 輪對話。根因是 Google Cloud Console 在 2025-2026 改版後，多個 UI 細節跟舊版不同。

---

## 陷阱 1：專案「顯示名稱」≠ 專案 ID

### 症狀
- 你在 Console 看到「**Raphael**」這個專案
- 但 URL 寫 `project=enki-489612`
- 你的 OAuth 用戶端 ID 是 `200915391477-xxxxx` 開頭
- 撈「iam.googleapis.com/v1/projects/...」API 時 ID 也是 `enki-489612`

### 根因
Google 給專案兩組識別碼：
- **專案名稱（顯示用）**：使用者自訂，可改變
- **專案 ID（API 用）**：建立時自動產生的英數字串（e.g. `enki-489612`），**建立後不能改**
- **專案編號（內部用）**：純數字（e.g. `200915391477`），所有 OAuth 用戶端 ID 都用這個開頭

### 解法
三個識別碼**都指向同一個專案**，沒有衝突。要確認是同一個專案，看專案編號（OAuth client ID 前 10 碼）一致即可。

---

## 陷阱 2：「檢視頁」vs「編輯頁」混淆

### 症狀
點進 OAuth 用戶端後看不到「**已授權的重新導向 URI**」設定區。

### 根因
新版 Console 進到用戶端預設是「**詳細資訊檢視**」，只有「Additional information」、「用戶端密鑰」、「建立日期」這些**唯讀**資訊。

「**+ 新增 URI**」按鈕**只出現在編輯模式**。

### 解法
**找「✏️ 編輯」按鈕**。位置隨版本變動：
- **舊版**（`/apis/credentials/...`）：用戶端那行最右邊「✏️ 鉛筆」圖示
- **新版**（`/auth/clients/...`）：頁面左上「🗑 刪除」**左邊**的編輯圖示（可能因為視窗太窄被截掉，**拉寬視窗**）

判斷當前是檢視還是編輯：
| 特徵 | 檢視 | 編輯 |
|------|------|------|
| 「+ 新增 URI」按鈕 | ❌ | ✅ |
| 底部「儲存」按鈕 | ❌ | ✅ |
| 「Additional information」section | ✅ | ❌（被表單取代）|
| URL 結尾 | `.../details` | `.../edit` |

### 終極解法：建立表單就有 URI 欄

乾脆**不要編輯**現有用戶端。建立新用戶端時的表單**就有「已授權的重新導向 URI」欄位**（在「應用程式類型」下方），**一次填完**。比編輯少一步。

---

## 陷阱 3：左邊側邊欄「IAM 與管理」含「設定」

### 症狀
點 Google Cloud logo 或返回首頁後，**左邊整片都是 IAM 與管理的子選單**（身分與存取權管理、PAM、政策疑難排解工具、IAM 與管理 設定 等），**沒有「API 和服務」**。

### 根因
新版 Console 把「**設定**」放進 IAM 與管理選單，讓人誤以為在 OAuth 設定頁。其實**設定**頁是改專案名稱、標籤、IAM 政策的，跟 OAuth 用戶端無關。

### 解法
**用頂端搜尋框**（網址列正下方）：

1. 點搜尋框
2. 輸入「**憑證**」或「**Credentials**」
3. 結果跳「**API 和服務 → 憑證**」
4. 點下去 → 跳到對的頁面

或者直接用**捷徑 URL**：

| 想去的頁 | URL |
|---------|-----|
| 舊版憑證主頁 | `https://console.cloud.google.com/apis/credentials?project=PROJECT_ID` |
| 新版 OAuth 用戶端列表 | `https://console.cloud.google.com/auth/clients?project=PROJECT_ID` |
| 同意畫面 | `https://console.cloud.google.com/auth/audience?project=PROJECT_ID` |
| API 庫 | `https://console.cloud.google.com/apis/library?project=PROJECT_ID` |

把 `PROJECT_ID` 換成你的專案 ID（不是名稱）。

---

## 陷阱 4：URL 變 `?project=...` 不代表錯的專案

### 症狀
- 你點了用戶端 A，URL 變 `?project=foo`
- 但 Console 頂端下拉顯示「**Raphael**」
- 你擔心「我切到別的專案了」

### 根因
舊版切換專案時**頂端下拉同步更新**。新版有時 URL 帶 `?project=...` 但下拉還沒更新（或反過來）。

### 解法
**比對 OAuth 用戶端 ID 前 10 碼（專案編號）**，跟你的目標專案是否一致。一致就是同一個專案。

---

## 陷阱 5：建立 OAuth 用戶端時漏填重新導向 URI

### 症狀
建立後才發現沒填 URI，要去「編輯」才能加（觸發陷阱 2）。

### 根因
建立表單**有**這個欄位，但因為它出現在「應用程式類型」下方（位置不像必填），使用者常直接跳過。

### 解法
**看到表單就先往下捲到「已授權的 JavaScript 來源」+「已授權的重新導向 URI」** 兩個區塊，先把 URI 加好再按「建立」。

---

## 陷阱 6：「應用程式類型」決定 UI 行為

### 症狀
- 選「**電腦 / 桌面應用程式**」→ 看不到「已授權的重新導向 URI」欄位（建立表單 + 編輯頁都沒有）
- 選「**網頁應用程式**」→ 完整 URI 欄位，但對 `https://` 強制（localhost 例外）

### 根因
Google 原生設計：
- **電腦類型用 loopback redirect**（`http://localhost:port`），Google 接受**任意 port** 而不需預先註冊 — 所以 UI 隱藏 URI 欄位
- **網頁應用程式**要把 token 用 HTTPS post 回去 → 必須預先註冊可信任的 URI

### 對赫米斯的實務影響
- 赫米斯 OAuth flow 是**本機 desktop CLI**，用「**電腦**」類型才對
- 「電腦」看不到 URI 欄位**是正常的，不要花時間找**
- 如果你選了「網頁應用程式」才看到 URI 欄位，那是因為你**選錯類型**了
- **不要**為了「能填 URI」而選網頁應用程式 — 下載的 JSON 結構會不同（`web` 不是 `installed`），赫米斯 OAuth 腳本讀不到

### 怎麼驗證選對了
下載 JSON 後看頂層 key：
- `{"installed": {...}}` → ✅ 電腦類型（你要的）
- `{"web": {...}}` → ❌ 網頁應用程式（要重來）

---

## 診斷 SOP（懷疑自己在錯的頁面時）

30 秒自我檢查：

1. **看網址列**：
   - `?project=...` → 哪個 project ID
   - 路徑是 `/apis/credentials` 還是 `/auth/clients`？
2. **看左側導航高亮**：
   - 「API 和服務」高亮 + 子選單看到「憑證」→ 對
   - 「IAM 與管理」高亮 + 看到「設定」→ 錯，IAM 跟 OAuth 無關
3. **看頁面有沒有「+ 建立憑證」按鈕**：
   - 有 → 對，這是憑證主頁
   - 沒有 → 你可能在別的頁

最快的修正方法：**按 `https://console.cloud.google.com/apis/credentials?project=PROJECT_ID` 直接跳過去**，別在側邊欄迷路。

---

## 已知 Console 改版時程（給未來踩雷時查）

| 日期 | 改版內容 |
|------|---------|
| 2025-09 | 引入 `/auth/clients/` 新路徑（OAuth 設定統一入口）|
| 2025-11 | 「應用程式類型」UI 改成 radio button（舊版是下拉）|
| 2026-01 | 「應用程式密鑰」區塊從 OAuth 用戶端頁分出，變成獨立 entity |
| 2026-04 | 預設進入「檢視」模式而非「編輯」模式（**這就是陷阱 2 的源頭**）|

## 陷阱 7：用戶端頁面上的「應用程式密鑰」≠ OAuth client_secret

### 症狀
- 從 OAuth 用戶端「檢視」頁看到「**+ Add secret**」按鈕（顯示 `****heOB` 之類）
- 以為這是 OAuth client_secret
- 把它的值拿去 OAuth flow 跑 → 失敗 `invalid_client`

### 根因
新版用戶端頁有**兩種 secret**（容易混淆）：

| 秘密 | 用途 | 出現位置 |
|------|------|---------|
| **OAuth client_secret** | OAuth 2.0 flow 用 | 下載 JSON 時就包含（在 `installed.client_secret`）|
| **應用程式密鑰（Add secret）** | 額外的 API key，可加可不加 | 用戶端頁面「+ Add secret」按鈕 |

**OAuth flow 只認 client_secret**，跟「應用程式密鑰」無關。

### 解法
- 看到「+ Add secret」**不要動**（你不需要它）
- 真要 OAuth client_secret，**重新下載 JSON** 拿 `installed.client_secret` 欄位
