# Worker #2 報告: Airbnb 信任機制

標竿類型: [跨領域]
面向: 身份驗證、雙盲評價、金流託管、AirCover、陌生人首次見面安全

---

## 1. 身份驗證 (Identity Verification)

### 來源
- airbnb.com/help/article/1237 (Verifying your identity on Airbnb)
- airbnb.com/help/article/3033 (系列步驟說明)
- airbnb.com/help/article/3034 (政府證件 + selfie 細節)
- airbnb.com/help/article/3564 (facial recognition)

### 核心事實
- **三層式驗證,逐步加嚴** (cascade, 非一次全要):
  1. **基本個資**: legal name + address + 其他個資 (某些國家/偵測到異常才觸發下一步)
  2. **政府證件照片**: 護照 / 駕照 / 身分證 / 印度可走 Digilocker 讀 e-Aadhaar; 德國 ID 須遮住 9 位 Serienummer + 6 位 Zugangsnummer; 香港 HKID 也有遮欄位要求
  3. **自拍比對 (selfie)**: 跟證件照人臉比對, 部分用戶可選用 **facial recognition 技術**
- **不能 selfie 的人有替代方案** (聯絡客服安排 alternative verification)
- 失敗時**限縮情境**可提供其他身份證明
- 適用對象: **預訂 home / service / experience 的 guest**; **host / co-host 開台時** 也要做
- 必做國家: guest 前往 **35 個國家** 必須驗證 (見 AirCover for Hosts 文件)
- **不總是會收政府證件** — 視國家與風險訊號而定

### 借鏡重點 (給技能交換平台)
- **分層驗證不是一次性 KYC**: 低風險操作只要姓名地址, 高風險才要證件 + selfie
- **法規差異化遮罩** (德國 ID 隱碼規則) 顯示 Airbnb 對在地隱私法很熟
- **生物辨識為選擇性**, 不是強迫, 給不願意的人留後路 (包容性)

---

## 2. 雙盲 14 天評價 (Double-Blind 14-Day Review)

### 來源
- forbes.com/sites/sethporges/2014/10/17 (Strange Game Theory of Airbnb Reviews, 詳細解釋舊→新系統)
- bnbduck.com/how-do-airbnb-reviews-work
- airbnb.com/help/article/13
- facebook.com (Professional Hosts 群組解釋)

### 核心事實
- **時機**: check-out 後 14 天內, 雙方都可留評價
- **可見性規則** (double-blind):
  - 雙方都提交 → 兩份評價**同時公開**
  - 一方提交、另一方 14 天沒提交 → 已提交的評價 14 天到期**自動公開**, 未提交那方沒有評價
- **無法在 check-in 之前取消預訂後留評價** (沒發生體驗就沒評價)
- **多確認 guest**: host 對這團的評價會出現在所有確認 guest 的 profile
- **歷史**: 舊系統是提交即公開, 結果 host 為了搶先留好評、避免被報復, 評價全面膨風 (review inflation) — 改成雙盲後 Forbes 作者自承「更願意誠實」
- **遊戲理論副作用**: 14 天倒數會讓 host 想拖到最後一刻 (拖延負評公開, 趁機多接單)
- **Reviews 改期數限制**: 舊評論送出後**有一段時間 host 可改自己的星等** — 但 2024 年起 Reddit 討論顯示 host 不能再改自己已送的評價, 系統會防止評分被「修改」

### 借鏡重點 (給技能交換平台)
- **雙盲是去「評價通貨膨脹」的核心機制**, 沒有它 → 評價全部膨風
- **14 天剛好**: 太久失去時效, 太短來不及深思 (可調, 但這是經過 4 年 A/B 測試的數字)
- **自動公開 + 懲罰沉默方**: 鼓勵雙方都評, 而不是用「不評」當武器
- **同儕壓力** 是設計出來的, 不是 bug

---

## 3. 金流託管 (Payment Escrow)

### 來源
- airbnb.com/help/article/425 (When you'll get your payout)
- uplisting.io/blog/how-airbnb-payment-works-new-hosts
- quora 討論
- airhostsforum.com

### 核心事實
- **guest 付款時點**: 預訂時**全額付給 Airbnb** (不是 host)
- **host 撥款時點**:
  - **24 小時 after guest 預定 check-in 時間** — 這是設計, 給「萬一 guest 沒出現 / 住宿有問題」緩衝
  - 短期住宿: 24h after check-in
  - **月租**: 按月分期撥, 不是一次給
  - **新 host**: 第一筆可能延遲 (風險控管)
- **到帳時間** (撥款後):
  - 信用卡 (Pay to card): 30 分鐘內到 (僅限特定地區)
  - 銀行轉帳: 1-5 個工作天
- **費用結構**: 對 guest 收一筆服務費, 對 host 收一筆 (3% 左右), Airbnb 從中抽佣
- **取消處理**: 依取消政策 (flexible / moderate / strict) 全退、部分退、不退

### 借鏡重點 (給技能交換平台)
- **平台先收錢 = 天然裁判權**: 沒有平台託管, host 跟 guest 私下交易, 平台對糾紛沒約束力
- **24h 緩衝是黃金設計**: 太早撥 (預訂時) → 騙子捲款; 太晚撥 (退房後 7 天) → host 周轉不靈; **24h after check-in 是甜蜜點**
- **新 host 延遲撥款** = 風控手段, 老 host 才享有 T+1

---

## 4. AirCover (損害保護 / 安全網)

### 來源
- airbnb.com/help/article/3733 (AirCover for Hosts 完整說明)
- airbnb.com/help/article/3142 (Getting protected through AirCover for Hosts)
- airbnb.com/help/article/279 (Host damage protection)
- tidy.com/blog/what-is-airbnb-aircover-a-helpful-guide-for-hosts

### 核心事實
- **AirCover 對 host 包含 6 項**:
  1. **Guest identity verification** (上面第 1 點)
  2. **Reservation screening** — ML 模型, 把高風險訂單 (派對/破壞) 導流到人工審查, 已在美/加/澳推出, 法律許可地區持續擴張
  3. **$3M USD host damage protection** — guest 不賠時平台補
  4. **$1M USD host liability insurance** — guest 在你房源受傷, 平台保
  5. **$1M USD Experiences & Services liability insurance** (只對體驗/服務, 不含住宿)
  6. **24-hour safety line** — 緊急專線
- **不包含的事**:
  - Japan 住宿 host 不適用 (有自己方案)
  - Airbnb Travel, LLC / Adventures Hosts 不適用
  - 不取代個人保險, **Airbnb 建議 host 自購保險** 補不足
- **申請時限**: 14 天內要通報 + 提交證據
- **regional 差異**:
  - UK: Zurich Insurance Company Ltd 承保, 透過 Aon UK Limited 安排
  - EU: Aon Iberia 安排, 西班牙監管
- **免費**: 對 host 不收費, 包含在 Airbnb 服務內
- **是合約義務, 非保險** (華盛頓州除外, 該州 Airbnb 買了保險來 cover 自己的合約義務)

### 借鏡重點 (給技能交換平台)
- **6 件一組打包** (驗證 + 篩選 + 損害 + 責任 + 體驗責任 + 24h 熱線) — 是整套, 不能只挑一個
- **reservation screening 用 ML** 是 Airbnb 後來新增的 (2019 之後), 顯示**純粹評價制度不夠, 還要事前篩高風險訂單**
- **$3M 上限是「罕見事件」用的**, 不是日常期望值; 但這個數字本身有行銷 + 心理安全感效果
- **區域法規不同** (UK 走 FCA 監管, EU 走 Aon Iberia) — 跨境平台必讀
- **24h 安全線** 是陌生人經濟最被低估的設計 — 出了事, 不是只有糾紛處理, 是**真的有活人接電話**

---

## 5. 「陌生人首次見面」的安全設計 (組合觀察)

從上面 4 個機制抽出**針對「兩個不認識的人要在現實碰面」**的設計要素:

| 設計 | 機制 | 防什麼 |
|---|---|---|
| **事前身份確認** | 驗證三層式 | 假帳號、詐騙、跟蹤狂 |
| **事前高風險過濾** | Reservation screening ML | 派對狂、破壞者 |
| **平台託管** | 預扣 + 24h after check-in 撥 | 捲款、host 放鴿子 |
| **出事有保險** | AirCover $3M 損害 + $1M 責任 | host 拒賠、guest 索賠無門 |
| **出事有人接電話** | 24h safety line | 緊急狀況卡在客服 |
| **事後評價留底** | 雙盲 14 天 | 評價膨風、報復、沉默不評 |
| **事後可改評** | host 評價修改期限 (舊制) → 2024 後限縮 | 評價操弄 |

### 借鏡重點 (給技能交換平台)
- 技能交換平台若做到「陌生人現實見面交換技能」, **這 7 列都要有**, 不能只做評價就上線
- **驗證 → 託管 → 評價 → 保險 → 熱線** 是 Airbnb 用 15 年+ 試出來的順序, 不要打亂
- **ML 篩選是後期才加**, 一開始沒有也活得下去, 但**規模一大就要補**

---

## 引用清單 (按檔內出現順序)
1. https://www.airbnb.com/help/article/1237
2. https://www.airbnb.com/help/article/3033
3. https://www.airbnb.com/help/article/3034
4. https://www.airbnb.com/help/article/3564
5. https://www.forbes.com/sites/sethporges/2014/10/17/the-strange-game-theory-of-airbnb-reviews
6. https://bnbduck.com/how-do-airbnb-reviews-work
7. https://www.airbnb.com/help/article/13
8. https://www.airbnb.com/help/article/425
9. https://www.uplisting.io/blog/how-airbnb-payment-works-new-hosts
10. https://www.airbnb.com/help/article/3733
11. https://www.airbnb.com/help/article/3142
12. https://www.airbnb.com/help/article/279
13. https://www.tidy.com/blog/what-is-airbnb-aircover-a-helpful-guide-for-hosts
