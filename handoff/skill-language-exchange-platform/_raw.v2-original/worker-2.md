# Airbnb 信任機制資料蒐集

> 給技能交換平台借鏡。整理事實、不做分析。
> 蒐集時間：2026-06-10
> Worker：web-worker #2

## 1. 身份驗證機制（Identity Verification）

### 政策時程
- 2022 Winter Release：先在 Airbnb 前 35 大國家/地區對 booking guest 強制實施
- 2023 年 6 月底：擴展到全球 — **所有 booking home 的 guest 與所有 primary host 都必須完成身份驗證**才能上線或下單
- 未完成驗證的 primary host → **行事曆會被鎖住**，無法接受新訂單
- 未完成驗證的 guest → 無法送出預訂

### 驗證層級（從輕到重）
1. **基本個資比對**：法定姓名、地址、電話、出生日期；在美國可用 SSN 與第三方資料庫比對
2. **政府證件照片**：駕照、護照、國民身分證、居留證（如英國 BRP）— 需四邊入鏡、未過期、原件（不接受影本/PDF/數位版）
3. **自拍 + liveness detection**：即時拍照，與證件照片比對；防止用既有照片、螢幕錄影、面具欺騙
4. **替代文件**：在標準驗證失敗的有限情境下，可提供結婚證書、法院命令等
5. **地區專屬**：南韓、印度用第三方合作夥伴；部分國家可用 NFC 晶片驗證；歐盟/巴西居民因稅務法規需提供額外納稅資料

### 強制時機與死線
- **Guest 下單時**觸發，多數人只做一次
- 若入住時間在 **12 小時內** → 必須在 **1 小時內**完成驗證
- 否則需在預訂後 **12 小時內**完成
- 預訂在 deadline 前是 **pending** 狀態，未完成就不會確認
- 通常 **1 小時內**處理完；若資料不準確可能延遲或需補件

### 隱私與極限
- 證件照片**不會**顯示給其他 user、不會出現在 profile
- 自拍**不會**出現在 profile 或給其他 user 看
- Host 只能看到「Verified 徽章」與「Airbnb 已確認身分」這類狀態，**看不到**實際證件內容
- 身份驗證**不等於**完整的犯罪背景調查 — Airbnb 明確聲明「不能保證某人是其所宣稱的身分」

### 技術外包與資料保護
- 第三方驗證商需符合嚴格標準（如英國 GDPR）
- 個資 in transit / at rest 採業界標準加密
- 生物辨識資料只用於驗證、依隱私政策儲存
- 比對來源：trusted third-party 資料庫 + 政府證件

### 來源
- Airbnb Help Center #1237（官方政策原文）
- Airbnb Newsroom "An update on identity verification"（2023-06 公告）
- Smoobu 部落格 "Airbnb Identity Verification: Complete Guide"

---

## 2. 雙向評價機制（Double-Blind Review）

### 評論時機
- 退房日（check-out）後開始算 **14 天評論窗口**
- 雙方都有 14 天可提交評價
- 期限到了之後，**任一方都不能再留評價**

### 雙盲機制（核心設計）
- 任一方提交評論後，**自己看不到對方的評論**，直到自己提交或 14 天到期
- **雙方都提交** → 評論立刻公開
- **只有一方提交** → 評論保持隱藏直到 14 天窗口結束才公開
- 一旦公開，**不能編輯**（但可加「回覆」）

### 評論結構
- 5 星評分 + 文字
- Guest 評 Host 採分類評分：cleanliness / accuracy / check-in / communication / location / value
- 可附 **private note** 給對方（透過訊息系統、不公開）
- 還可針對性別代詞要求 Airbnb 編輯

### 戰略誘因（Forbes 分析）
- 舊制（公開即時）→「互相褒揚的競賽」 — 為了怕被報負而傾向先給好評
- 結果：負評少、neutral 評讀作「隱性負評」、新用戶被誤導
- 新制（雙盲 14 天）→ 不必擔心即時報復，**誠實度提升**
- 但有副作用：覺得會被負評時可「拖過時鐘」、讓負評晚 14 天下架（多 2 週接單機會稀釋負評影響）

### 懲罰機制（Retaliatory Review 防範）
- Airbnb 明確禁止**報復性評論**：
  - 為了報復 host 執行政策而寫偏頗、不真實的評論
  - 常見觸發情境：回報違規人數、用押金扣款、聯絡 Resolution Center、拒絕退款
- 移除條件：評論違反以下任一類型
  1. **偏頗/操縱**（金錢交換、虛假預訂、多帳號協調好評、報復性）
  2. **不相關**（沒住過、只談觀光）
  3. **內容違規**（歧視、暴力、威脅、隱私洩漏、違法、情色、假冒、隱私侵權）
- 申請移除：到 desktop 「Start the request」→ 選評論 → 選理由 → 上傳證據 → 提交 → 客服最終裁決

### 經營誘因
- 持續留評論是 **Superhost 排名因子**之一
- 4.8 是 Superhost 達標基準
- Host 留評最佳實踐：用性別中立範本、3 天延遲（確保沒有後續損壞）

### 來源
- Forbes "The Strange Game Theory Of Airbnb Reviews"（Seth Porges, 2014）
- iGMS "Airbnb Review Policy: How It Works + Unfair Reviews"
- Airbnb Community / AirHostsForum 用戶討論

---

## 3. 金流託管（Payment Escrow）

### 託管模型
- 三方：房東、房客、Airbnb 作為**負責的第三方處理交易**
- 類比：把押金放進 escrow account，**直到房客驗收完成才撥款**
- 房客付款時進入 Airbnb「escrow account」（使用者社群用語），**不是直接進房東戶頭**

### 撥款時機
- 預設：**房客 check-in 後 24 小時**撥款
- 目的：避免「假房源 / 詐騙 / 不可居住」情況下的付款損失
- 長期預訂（如月租）：改成**每月撥款一次**（而非一次收齊）
- 新房東特例：第一次預訂後可能 hold 30 天；若首次預訂在 30 天後，會在原訂 check-in 後 24 小時放行

### 退款與取消
- 由 Airbnb Resolution Center 處理
- 退款政策依房東設定（strict / moderate / flexible 等）

### AirCover for Hosts（核心保護傘，2024 起整合）
包含 5 個子計畫：
1. **Guest identity verification** — 預訂前先驗證
2. **Reservation screening** — 演算法篩掉高風險預訂
3. **Host damage protection** — **300 萬美元**保障，覆蓋房客損壞與特殊清潔費（汙漬、寵物意外、煙味去除）
4. **Host liability insurance** — **100 萬美元**房東責任險（房客受傷或財損）
5. **Experiences & Services liability insurance** — **100 萬美元**體驗/服務責任險
6. **24-hour safety line** — 24 小時安全專線

### 申請限制
- 不涵蓋 Airbnb Travel, LLC 提供的房源
- 日本房源不適用 AirCover（改用 Japan Host Insurance / Japan Experience Protection Insurance）
- 損壞申請需在 14 天內提交並附證據
- 房東需另外告知自己的個人保險公司（AirCover 不是個人保險替代品）

### 跨地區細節
- **英國**：underwriter Zurich Insurance Company Ltd，由 Airbnb UK Services Limited（Aon UK Limited 代表）安排，受 FCA 監管
- **EEA**：underwriter Zurich Insurance Europe AG（西班牙分公司），由 Airbnb Spain Insurance Agency S.L.U.（ASIASL）安排，受 DGSFP 監管
- 免費提供給 Host

### 來源
- Airbnb Help Center #3142（AirCover 官方頁）
- Airbnb Community（payout timing 討論）
- r/AirBnB 討論串（escrow 帳戶確認）

---

## 4. 「陌生人首次見面」的安全設計（彙整）

| 設計面向 | 具體機制 | 目的 |
|----------|----------|------|
| 預訂前 | 身份驗證徽章顯示在 profile | 雙方都能確認對方是「驗證過的真人」 |
| 預訂時 | Reservation screening 演算法 | 攔截高風險訂單（AirCover 一環） |
| 付款時 | 託管帳戶（不直接進房東） | 房東不會拿了錢不給住、房客不會付了錢沒人理 |
| 入住前 24h | 房東收到撥款（但房客已付） | 確保房東有誘因維護房源 |
| 入住時 | Smart lock 自動產生一次性密碼 / KeyNest lockbox | 房東不必親自交付鑰匙、首次見面壓力降低 |
| 入住後 14 天 | 雙盲評價窗口 | 鼓勵誠實評價、不用擔心即時報復 |
| 全程 | 24 小時安全專線 | 緊急狀況有人接 |
| 損壞發生 | AirCover 最高 300 萬美元 | 房東敢接陌生人、敢借出貴重空間 |

### 核心設計哲學（從來源萃取）
- 「Verification confirms identity ≠ confirms safety」：驗證只是門檻，不是保證
- Host 仍需評估通訊風格、profile、過去評價
- Guest 也仍需靠照片、評價、Host 回覆速度判斷
- 平台提供**工具與保護傘**，但**日常判斷**還是交回個人

### 來源彙整
- Airbnb Help Center #1237（身份驗證）
- Airbnb Newsroom "An update on identity verification"（2023-06）
- Smoobu 部落格（身份驗證 step-by-step）
- Forbes "The Strange Game Theory Of Airbnb Reviews"（雙盲評論分析）
- iGMS "Airbnb Review Policy"（評論政策細節）
- Airbnb Help Center #3142（AirCover）
- Airbnb Community（payout timing 24h 確認）
- r/AirBnB 討論串（escrow 帳戶確認）

---

## 給技能交換平台的借鏡重點（事實層面、待分析師判斷）

以下僅列**機制本身**的設計選擇，不做價值判斷：

1. **驗證層級化**：從輕量（姓名 + 地址比對）到重量（政府證件 + 自拍 + liveness）分級，依風險決定要求程度
2. **驗證 deadline 與 booking 狀態綁定**：未驗證 → 訂單 pending、不能 confirmed
3. **資料最小揭露**：對其他用戶**只顯示「已驗證」徽章**，不暴露證件內容
4. **雙盲 14 天評價窗口**：防止評價即時報復、提高誠實度；單方提交也保留發布機制
5. **明確禁止報復性評論** + 移除申請 SOP
6. **託管 + check-in 後 24h 撥款**：在「雙方都有誘因」的時點放款
7. **AirCover 多層保護**：身份驗證、訂單篩選、損壞險、責任險、安全專線
8. **工具降低首次見面壓力**：smart lock 一次性密碼、lockbox 機制 — 不需要房東親自交付
9. **新用戶 hold 期**：第一次預訂可能 hold 撥款 30 天（防範新人詐騙）
10. **跨地區在地化**：驗證方式、險種、納稅資料依國家法規調整

---

> 本檔僅做事實整理。借鏡分析、可行性評估、技術實作建議不在本 worker 範圍。
