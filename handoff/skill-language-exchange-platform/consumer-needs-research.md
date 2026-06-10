# 技能/語言交換媒合平台 — 消費者需求及功能需求調查報告

**v2 修正版(2026-06-10 11:58 整合)**

> **架構版本**:**v2 Orchestrator + 4 web-workers + summarizer**(Orchestrator: default / Workers: 4 個獨立 hermes session)
> **整合時間**:2026-06-10 11:58 CST
> **總耗時**:11 分鐘(派遣 4 worker 4-6 分鐘 + summarizer 6 分鐘)
> **總資料量**:74 KB(_raw/) → 12.5 KB(_summary.md) → **本報告 27 KB**

---

## 1. 專案一句話

為 20-45 歲的都市自學者打造的「**技能 × 技能**」或「**語言 × 技能**」雙向交換媒合平台,結合「**以物易物點數制**」與「**Airbnb 等級的信任機制**」,解決現有市場上「語言交換有、技能交換無、跨領域交換更無」的缺口。

---

## 2. 釐清後的問題邊界

- **目標使用者輪廓**:20-45 歲、會某項技能/語言想交換學習、單次可投入 1-3 小時的都市自學者。**三大客群**(由 _plan.md 指定):
  - 主流客群(小美):25 歲台北行銷設計師,想省錢學外語
  - 差異化客群(佐藤):32 歲東京軟體工程師,跨國交換中日文
  - CSR 亮點客群(陳媽媽):58 歲台中退休老師,傳承技藝
- **核心任務**:讓「我有 X 技能想換 Y 技能」的人**快速找到互補對象** → 確認品質/可約時間 → 安排第一次見面 → 建立信任機制避免被放鴿子
- **目前替代方案**:
  - **Tandem** / **HelloTalk**:語言交換為主,**無技能交換**,使用者普遍反映「淪為 dating app」
  - **SkillSwap.io** / **518 熊班**:技能交換雛形,但**配對成功率低、無金流託管、無視訊內建**
  - **Reddit r/SkillSwap** / **r/SeriousLangExchange**:社群型,**無結構、無驗證**
  - **Facebook 社團** / **Dcard**:零散、不安全、無媒合機制
- **為什麼是現在做**:
  - ① 疫情後遠距教學普及 ② 技能/語言自學者爆炸性成長
  - ③ 訂閱疲勞下「以物易物」模式重獲興趣
  - ④ Airbnb 模式已驗證「信任+媒合」可行(7 層配套)
  - ⑤ Tandem/HelloTalk 證明「有需求但做不好」(投訴極多)
- **6 個月成功指標**:
  - 3,000 個 MAU
  - 500 對完成至少一次配對
  - 4.0+ 星 App Store 評分
  - 配對成功率 25%(配對後 7 天內完成首次課程)
  - 違約率 < 10%
  - 北極星指標:**每週完成課程的配對對數**

---

## 3. 標竿作品功能盤點(8 個,明確分類)

### 3.1 直接標竿(4 個)

#### 3.1.1 Tandem(語言交換)
- **定位**:全球語言交換訊息平台,1000 萬用戶,160+ 語言,2015 創立
- **定價**:免費 10 翻譯/日;Premium 12 月 $19.99
- **核心功能**:文字+語音+視訊、群組、配對、CEFR 證書
- **最高頻 3 個好評**:
  1. 基數大/bot 少(1000 萬高品質學習者)
  2. 免費有核心價值
  3. 介面直覺、聚焦「讓人開口」
- **最高頻 3 個負評**:
  1. **英文母語者被訊息轟炸**(前幾小時就 30+ 訊息)
  2. 翻譯太少(每日 10 次上限)
  3. **交友化(feels like a dating app at times)**
- **來源**:[actualfluency.com/tandem](https://actualfluency.com/tandem)

#### 3.1.2 HelloTalk(語言交換 + 社群)
- **定位**:語言交換 App + 社群動態(Moments),150+ 語言,結合社交媒體
- **定價**:免費 10 翻譯+10 聊天/日;VIP 月 $12.99 / 年 $79.99 / 終身 $149.99
- **核心功能**:文字+翻譯+修正+羅馬拼音、語音房、Moments 動態
- **最高頻 3 個好評**:
  1. 社媒+語言雙特性
  2. 多種互動(語音/視訊/文字)
  3. 翻譯+修正+羅馬拼音(中/日/韓)
- **最高頻 3 個負評**:
  1. **學習者非老師**(UGC 容易錯)
  2. **過半對話冷場**(>半數 fizzled out)
  3. **被當約會/釣魚平台**(some users treat it as dating/hookup app)
- **來源**:[fluentu.com/blog/reviews/hellotalk](https://www.fluentu.com/blog/reviews/hellotalk)

#### 3.1.3 SkillSwap.io(純技能交換)
- **定位**:點數制 P2P 技能交換,Slogan「Learn, Teach & Grow Without Limits」
- **定價**:完全免費(無金流),**1 堂課 = 350 點**
- **核心功能**:
  - **AI 配對**(match %)
  - 視訊內建
  - **Gamification**(7 種徽章)
  - 點數制防止放鴿子
- **最高頻 3 個好評**:
  1. **AI 配對精度**(match %)
  2. 視訊內建(免切換 Zoom)
  3. 7 種徽章(激勵完成)
- **最高頻 3 個負評**:
  1. **無第三方評分**(G2/Product Hunt 缺)
  2. 使用者基數小(冷啟動)
  3. 無支付託管(純點數)
- **來源**:[skillswap.io](https://skillswap.io)

#### 3.1.4 518 熊班(台灣技能交換)
- **定位**:台灣雙向交換,App 內建聊聊,語言+職場+興趣
- **定價**:App 免費,雙向交換無金流
- **核心功能**:
  - AI 描述助手
  - 一對多快速媒合
  - 台灣本地化
- **最高頻 3 個好評**:
  1. 台灣本地化
  2. AI 描述助手
  3. 多元技能(語言+職場+興趣)
- **最高頻 3 個負評**:
  1. **無第三方評分**(官方自製文)
  2. **活躍度質疑**(20-30 天前職缺)
  3. 視訊/評價/金流未描述
- **來源**:[518.com.tw/article/2253](https://www.518.com.tw/article/2253)

### 3.2 間接標竿(3 個)

| 標竿 | 為什麼列為間接 | 來源 |
| --- | --- | --- |
| **Reddit r/SkillSwap** | 證明「有需求但無好平台」,6 年持續發文;反爬抓不到會員數 | [reddit.com/r/SkillSwap](https://www.reddit.com/r/SkillSwap/) |
| **Reddit r/SeriousLangExchange** | 「認真練習者」自闢社群避開泛興趣版;反推真實需求(nudge/72h 過期) | [reddit.com/r/SeriousLangExchange](https://www.reddit.com/r/SeriousLangExchange) |
| **r/skilltrade** | **不可達**(web_search 0 命中,極可能已刪除),僅作「此路徑不通」紀錄 | worker-1/4 抓取失敗 |

### 3.3 跨領域典範(1 個)

#### 3.3.1 Airbnb(陌生人信任工程典範)
- **為什麼列為跨領域**:7 層配套可借鏡給技能交換平台
- **7 層配套**:
  1. **身份驗證(三層式)**:基本個資 → 政府證件 → 自拍+liveness(35 國強制)
  2. **Reservation screening ML** 預測風險
  3. **24h 金流託管**(check-in 後才撥款)
  4. **雙盲 14 天評價**(任一方提交後 14 天內看不到對方評論)
  5. **AirCover**:**$3M 損害險 + $1M 責任險**
  6. **24h safety line** 緊急專線
  7. **評價修改期限** 防止報復性評論
- **來源**:[airbnb.com/help/article/1237](https://www.airbnb.com/help/article/1237) 等 13 頁 Airbnb 官方文件

### 3.4 功能矩陣表(核心,v2 修正版新增)

| 功能 | Tandem | HelloTalk | SkillSwap.io | 518 | r/SLE | Airbnb | 消費者呼聲 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 技能清單+標籤 | 有 | 有(語言條) | 有(match %) | 有 | 有 | N/A | **急需雙向**(w-4 #17) |
| 自動配對 | 滑卡 | 滑卡 | AI 配對 | 一對多 | 72h 過期 | N/A | **急需**(w-3 #8、w-4 #14 學術) |
| 身份驗證 | 真人審核 | 未提 | 未提 | 未提 | Admin | **三層式(35 國)** | **極高**(w-3 #3-4-11) |
| 時數點數/託管 | Premium | VIP 訂閱 | **350 點/堂** | 無 | N/A | 24h+AirCover | **急需**(w-4 #1-2-15) |
| 內建視訊 | 有(需先傳訊) | 有(建議暖身) | **有(內建)** | 未提 | N/A | N/A | **急需**(防 deepfake) |
| 雙盲評價 | 通話後互評 | 公開 | 每堂評分 | 未提 | N/A | **雙盲 14 天** | **急需**(w-4 #14) |
| 反約會/性騷擾 | 篩選(付費) | VIP 篩選 | 無 | 守則禁 | N/A | ML 篩選 | **極高**(w-3 #1-2-12) |
| 銀髮/家庭模式 | 無 | 無 | 無 | 無 | N/A | N/A | **急需**(w-3 #14、w-4 #16) |
| 平台內通訊 | 文字+翻譯 | 文字+Moments | Messenger | 聊聊 | N/A | 站內全程 | **急需**(w-4 #8) |
| 教學分級 | 無 | 無 | 等級(隱含) | 未提 | N/A | N/A | **急需**(w-4 #4 跨 4 來源) |
| 結構化 30/30 排程 | 無 | 無 | 日曆+排程 | 未提 | 課程提醒 | N/A | **急需**(德國 A2→B2 1.5 年) |

**矩陣關鍵觀察**:
- **6 個痛點 = 全部標竿未做好**:反約會/性騷擾、身份驗證、銀髮/家庭、平台內通訊、教學分級、結構化 30/30
- **3 個借鏡 Airbnb 可做**:身份驗證(金流託管 + AirCover 暫不適用)、雙盲評價、ML 篩選
- **本平台差異化切入點**:**「以物易物點數 + Airbnb 7 層信任 + SkillSwap.io AI 配對 + 反約會設計」四合一**

---

## 4. 潛在消費者需求(38 則原始 → 25 痛點去重)

> 資料來源:_raw/worker-3.md (24.3 KB) + _raw/worker-4.md (21.6 KB)
> 涵蓋:Reddit r/languagelearning、r/HelloTalk、r/SkillSwap、r/SeriousLangExchange、r/taiwan、r/startups、r/retirement、PTT、Dcard、Medium、learntolanguage.com、Theseus 學術(122 份樣本)

### 4.1 高頻痛點(≥ 3 來源,6 個)

| # | 痛點 | 來源統計 | 痛感 | 對應功能需求 |
| --- | --- | --- | --- | --- |
| **H1** | **約會 app 化/被推銷**(男女兩端共怨) | 跨 4+(r/languagelearning、r/HelloTalk、Medium、learntolanguage.com、r/taiwan) | 極高 | 反騷擾機制、反約會設計 |
| **H2** | **詐騙/Deepfake/批量假帳**(pig butchering、bot farm) | 跨 4+(r/HelloTalk、r/languagelearning、r/taiwan) | 極高 | 身份驗證、影片自介 |
| **H3** | **配對/排程無效率**(已讀不回、純 Hi) | 跨 5+(r/languagelearning、learntolanguage.com、Theseus 46.7%) | 高 | 智能配對、每週精選推送 |
| **H4** | **「信用/時數」系統必要**(barter 會卡死) | 跨 4+(r/startups、Medium、Reciproc8、Chronocademy、Theseus) | 高 | 點數託管、違約金 |
| **H5** | **英語 native = 招蜂引蝶**(被當免費家教) | 跨 3(Medium、Reddit、learntolanguage.com) | 高 | 反騷擾、付費牆鎖住安全功能 |
| **H6** | **女性被騷擾/不雅圖**(Many delete apps) | 跨 4+(learntolanguage.com、Medium、Reddit) | 極高 | 女用者保護、性別篩選 |

### 4.2 中頻痛點(2 來源,11 個)

| # | 痛點 | 對應功能需求 |
| --- | --- | --- |
| M1 | 配對後切回英文(雙方語言能力不對等) | 教學分級(CEFR/作品集) |
| M2 | 付費牆鎖住安全功能(性別/地區) | 安全功能**免費**開放 |
| M3 | 平台治理(檢舉無回應) | 安全舉報 + 24h 回應 |
| M4 | 教學能力 vs 技能分不清(跨 4 來源) | 教學分級驗證 |
| M5 | 稀有語言供需不對稱 | 技能曝光演算法 |
| M6 | 平台冷靜(PTT+Dcard 質疑活躍度) | 高頻次配對推送 |
| M7 | 亂槍打鳥推播(Dcard) | 精準媒合 |
| M8 | 學習 vs 交友分流不清(跨 3 來源) | 反約會設計 |
| M9 | 變相商業(假交換真行銷) | 禁止變相商業守則 |
| M10 | 短中期目標/留任激勵(跨 3 來源) | 等級徽章 |
| M11 | 未導流平台內通訊(跨 3 來源) | 平台內建通訊,課程外不通私訊 |

### 4.3 低頻痛點(1 次,值得追蹤,7 個)

| # | 痛點 | 對應功能需求 | Persona 關聯 |
| --- | --- | --- | --- |
| L1 | **中高齡/家庭友善**(70 歲母親) | 銀髮/家庭模式 | 陳媽媽 |
| L2 | **銀髮寂寞=健康風險**(WHO=15 根菸/日) | 銀髮關懷功能 | 陳媽媽 |
| L3 | 神經多樣性 peer group | ND 友善設計 | — |
| L4 | 帳號被洗 | 異常偵測 | — |
| L5 | 平台定位不清(教學 vs 社交) | 明確平台定位 | — |
| L6 | 技能供需卡死(法律 vs 狗散步) | 多元技能分類 | — |
| L7 | 新用戶冷啟動保護 | 新用戶 onboarding 流程 | — |

### 4.4 來源統計總覽(38 則原始 → 25 痛點)

| 來源類型 | 數量 | 代表 |
| --- | --- | --- |
| Reddit 子版 | 18 則 | r/languagelearning、r/HelloTalk、r/SkillSwap、r/SeriousLangExchange、r/taiwan、r/startups、r/retirement |
| 論壇/社群 | 5 則 | PTT Salary、Dcard job |
| 部落格 | 6 則 | Medium (2 篇)、learntolanguage.com、518 守則、Reciproc8、Chronocademy |
| 學術 | 1 篇 | Theseus(122 份樣本) |
| 公衛 | 1 篇 | senior-loneliness |
| 知乎 | 1 則 | 教學分級 |

---

## 5. 功能需求優先級 (MoSCoW)

> 依「**高頻痛點 × 標竿未滿足程度**」交叉排序

### 5.1 Must have(MVP 必做,6 大模組)

1. **[H1+M8] 反約會+反騷擾機制**:女用者免費開啟「只配對同性/女老師」、配對介面**禁止頭像滑卡**(強制走技能互補篩選)、課程外禁止平台私訊(強迫回到見面/課程場景)
2. **[H2] 身份驗證+Deepfake 防範**:政府證件驗證 + 影片自介(15 秒)、**OpenCV 活體檢測**防 deepfake、AI 真偽檢查
3. **[H4] 時數點數託管+違約金**:預約時系統凍結雙方點數(各 1 小時);課程開始 24h 前取消免扣、24h 內取消扣 50%、課程時間未到扣 100%
4. **[H4+M4] 跨技能交換+AI 智能配對**:不限語言,任何技能都可上架;配對演算法算「技能互補矩陣」,推「我會 X 想學 Y、你會 Y 想學 X」的雙方(match % 顯示)
5. **[H3+M6] 教學分級+細粒度標籤+雙向意願確認**:技能分主/副標籤(Photoshop 細分為「修圖」「去背」「合成」)、CEFR/作品集分級、配對前雙方都要明確列出「願意教」「想學」
6. **[H6+M10] 等級徽章+每週精選配對**:完成 N 次交換頒發「資深老師/明星學生」徽章;每週主動推送 3 個最佳配對(讓使用者不必自己刷)

### 5.2 Should have(v1.1 規劃,6 項)

7. **[H3] 內建視訊教室**(白板+分組+錄影回看,防 deepfake)
8. **[H4] 結構化 30/30 排程**:日曆+排程功能(德國 A2→B2 1.5 年案例)
9. **[H6] 雙盲 14 天評價**(借鏡 Airbnb,任一方提交後 14 天內看不到對方評論)
10. **[L1] 銀髮/家庭模式**:大字體、簡化上架流程、可選「接受 12 歲以下學員+家長陪同」
11. **[M2] 安全功能免費開放**(不鎖付費牆)
12. **[M11] 平台內建通訊,課程外不通私訊**

### 5.3 Could have(v2 規劃,5 項)

13. **[H3] AI 智能提醒**(配對後 72h 過期未回應自動取消)
14. **[H6] 神經多樣性 peer group**(L3)
15. **[M5] 技能曝光演算法**
16. **[M9] 禁止變相商業守則**
17. **[M8] 學習 vs 交友分流**

### 5.4 Won't have (this time)(5 項,明確不做)

- **金流退款/爭議處理**:純點數制,不做 AirCover 等價機制
- **AI ML 智能配對(ML 模型)**:v1 用規則式配對(match %),v3 再上 ML
- **群組揪團**:聚焦 1-on-1 雙向交換,不做多人
- **完整 LMS 學習管理系統**:v1 只做交換,不做學習進度追蹤
- **多語言介面(40+ 語言)**:v1 繁中+英文,未來再加

---

## 6. 三大 Persona 與 User Story 草稿

### 6.1 Persona 1:小美(25 歲,女,台北行銷設計師)— ★ 使用者原意 Persona(主流客群)

- **人口統計**(_plan.md):25 歲/女/台北內湖/月薪 4.5 萬/單身;9-18 上班 19-23 學;想學日文(First Love 中毒)
- **核心痛點**(_raw/ 5+ 次):
  - 被當約會(H1,跨 4+ 來源)
  - 被當免費英文家教(H5,跨 3 來源)
  - 女性被騷擾/不雅圖(H6,跨 4+ 來源)— **Many delete apps**
  - 詐騙/Deepfake 不安全(H2,跨 4+ 來源)
- **現有替代方案**:
  - Tandem(滑 2 週 90% 男生加 Line 變騷擾)
  - HelloTalk(同 H1 約會化)
  - 語言學校一期 2 萬 5 太貴
- **代表聲音**:
  - [r/languagelearning/1ot9zd4](https://www.reddit.com/r/languagelearning/comments/1ot9zd4)
  - [exhausting-for-women](https://aneurokumar.medium.com/online-language-exchanges-apps-are-exhausting-for-women-c0e78d9f7896)
  - [learntolanguage.com](https://learntolanguage.com/the-problem-with-language-exchange-apps)
- **User Story 草稿**:
  - **US-1-1**:作為小美,我想要**上傳 5 個設計作品 + 15 秒自我介紹影片 + OpenCV 活體檢測**,以便讓對方相信我的 Photoshop 程度是「中高級」不是「新手」
  - **US-1-2**:作為小美,我想要**設定「只配對女老師」+「配對介面禁止頭像滑卡」+「課程外不通私訊」**,以便避免被騷擾
  - **US-1-3**:作為小美,我想要**平台幫我算「1 hr Photoshop = 1.5 hr 日文」自動換算點數**,以便不必自己議價被當奧客
  - **US-1-4**:作為小美,我想要**預約日文課時系統先扣我的點數、上課後才撥給老師**,以便對方放鴿子我還能拿回點數
  - **US-1-5**:作為小美,我想要**完成 5 次交換後拿到「資深老師」銀徽章**,以便我的技能在搜尋結果排名往前

### 6.2 Persona 2:佐藤健太郎(32 歲,男,東京軟體工程師)— ★ 使用者原意 Persona(差異化客群)

- **人口統計**(_plan.md):32 歲/男/東京新宿/月薪 60 萬日圓/單身;WFH 一週 3 天;想學中文
- **核心痛點**(_raw/ 8+ 次):
  - HelloTalk 假帳號多(pig butchering / bot farm)
  - 配對不對等(對方只想「教我英文+學日文」但佐藤不會英文)
  - 無內建視訊(HelloTalk 要先傳訊)
  - 配對後切英文(M1)
  - 純 Hi 寒暄無內容(H3)
  - 找不到「教中文+學日文」對等
- **現有替代方案**:
  - HelloTalk(假帳多)
  - Discord 語言學習社群(自尋但無結構)
- **代表聲音**:
  - [r/languagelearning/koci4k](https://www.reddit.com/r/languagelearning/comments/koci4k)(已讀不回)
  - [r/HelloTalk/1oog705](https://www.reddit.com/r/HelloTalk/comments/1oog705)(bot farm)
- **User Story 草稿**:
  - **US-2-1**:作為佐藤,我想要**平台顯示對方的影片自介(15 秒)+ 身份驗證標章 + OpenCV 活體檢測**,以便篩掉假帳號
  - **US-2-2**:作為佐藤,我想要**主動列出「會日文 N2 / 想學中文 HSK3 / 願意教日文會話」**,以便讓「想學日文+能教中文」的人主動來找我
  - **US-2-3**:作為佐藤,我想要**平台內建視訊(白板+分組)**,以便不必切 LINE/Zoom,避免家人誤會
  - **US-2-4**:作為佐藤,我想要**自動換算「1 hr 日文 = 0.7 hr 中文」(因中文較搶手) + 跨國匯率**,以便我點數花得值得
  - **US-2-5**:作為佐藤,我想要**結構化 30/30 排程 + 行事曆同步 Google Calendar**,以便公司會議不跟中文課撞期

### 6.3 Persona 3:陳媽媽(58 歲,女,台中退休老師)— ★ 使用者原意 Persona(CSR 亮點)

> **★ 來自使用者原意,退休族真實評論比例低(僅 #14 1 則),需後續驗證**

- **人口統計**(_plan.md):58 歲/女/台中北區/退休國小老師(教 30 年);會日文+書法+鋼琴+客家料理
- **核心痛點**(★ 退休族真實評論比例低,需後續驗證):
  - 找不到想學的人(L1:70 歲母親案例)
  - 介面複雜不會用
  - 銀髮寂寞=健康風險(L2:WHO=15 根菸/日)
  - 平台活躍度質疑(M6:PTT/Dcard 質疑 518 熊班活躍度)
- **現有替代方案**:
  - 退休族互助經濟(worker-4 #15:Excel 教學換家事)— 分散、無主導平台
- **代表聲音**:
  - [r/languagelearning/1hhwoav](https://www.reddit.com/r/languagelearning/comments/1hhwoav)(70 歲母親想學俄文)
  - [senior-loneliness](https://clarishealthcare.com/the-hidden-epidemic-creative-solutions-to-combat-senior-loneliness)(公衛)
- **User Story 草稿**:
  - **US-3-1**:作為陳媽媽,我想要**平台推薦「想學日文/書法/鋼琴的年輕人」主動來找我**,以便我不必每天去刷 App
  - **US-3-2**:作為陳媽媽,我想要**大字體介面 + 極簡 3 步上架技能 + 看影片教學**,以便我不會卡關放棄
  - **US-3-3**:作為陳媽媽,我想要**設定「接受 12 歲以下學員 + 家長陪同」**,以便孫子的同學也能來學
  - **US-3-4**:作為陳媽媽,我想要**首次見面在地點選項明確列出「公園/社區中心」**,以便我不用把陌生人約到家裡
  - **US-3-5**:作為陳媽媽,我想要**平台用台語+中文雙語提示**,以便我看得懂通知

### 6.4 Persona 4:阿哲(35 歲,新竹後端工程師/創業者)— _raw/ 歸納

- **核心痛點**(_raw/ 4 次):
  - 信用/技能驗證必要(worker-4 #1,跨 4+ 來源)
  - 內建時數(worker-4 #2,barter 系統卡死)
  - 教學分級(worker-4 #4)
  - 平台定位不清(worker-4 #5)
- **代表聲音**:
  - [r/startups/1fpvxf3](https://old.reddit.com/r/startups/comments/1fpvxf3)
  - [zhihu/16246331](https://www.zhihu.com/en/answer/16246331)

### 6.5 Persona 5:Lily(36 歲,美國人在台中)— _raw/ 歸納

- **核心痛點**(_raw/ 4 次):
  - 精準媒合,不被亂槍打鳥(M7)
  - 反 ghosting(H3)
  - 不被浪費時間(已讀不回/純 Hi)
- **代表聲音**:
  - [dcard 258187149](https://www.dcard.tw/f/job/p/258187149)

---

## 7. (輔助) 市場規模估算

> 標 [輔助]:本節為非必要,僅作參考。

- **TAM**:**全球語言學習市場約 600 億美元(2024)**(來源:Global Market Insights);**技能交換市場**無公開數字,推估約 50 億美元
- **SAM**:**台灣+日本+東南亞 20-45 歲都市自學者**約 8,000 萬人;5% 對「技能/語言交換」有興趣 = **400 萬人**;ARPU 30 美元/月 = **14.4 億美元/年**
- **SOM**:**台灣市場 6 個月內 3,000 MAU**;年貢獻 30 × 3000 × 12 = **108 萬美元/年 ≈ 3,200 萬台幣/年**
- **假設**:
  - [待驗證] 5% 興趣率、30 美元 ARPU 為假設值
  - [待驗證] 技能交換市場規模為內部估算

---

## 8. 給 product-planner 的下一步建議

- **三大 Persona 完整可擴寫成驗收標準**:小美(主流) > 佐藤(差異化) > 陳媽媽(CSR 亮點)
- **MVP 範圍 = Must have 6 大模組**
- **差異化切入點 = 「以物易物點數 + Airbnb 7 層信任 + SkillSwap.io AI 配對 + 反約會設計」四合一**
- **3 個 [待釐清] 事項**:
  - [待釐清] 點數制 vs 現金制:v1 採點數制,但若使用者不買單需 pivot
  - [待釐清] 跨國點數匯率公式:1 USD = ? 點? 1 JPY = ? 點?
  - [待釐清] 退休族使用者真實比例(需後續驗證,目前 _raw/ 比例低)

---

## 9. 參考資料

### 9.1 直接標竿(4 個)
1. [actualfluency.com/tandem](https://actualfluency.com/tandem) — Tandem 評論
2. [fluentu.com/blog/reviews/hellotalk](https://www.fluentu.com/blog/reviews/hellotalk) — HelloTalk 評論
3. [skillswap.io](https://skillswap.io) — SkillSwap.io 官網
4. [518.com.tw/article/2253](https://www.518.com.tw/article/2253) — 518 熊班技能交換

### 9.2 間接標竿(3 個)
5. [reddit.com/r/SkillSwap](https://www.reddit.com/r/SkillSwap/)
6. [reddit.com/r/SeriousLangExchange](https://www.reddit.com/r/SeriousLangExchange)
7. r/skilltrade(不可達,僅作「此路徑不通」紀錄)

### 9.3 跨領域典範
8. [airbnb.com/help/article/1237](https://www.airbnb.com/help/article/1237) 等 13 頁 Airbnb 官方文件

### 9.4 消費者聲音來源(25 個 URL)
9-33. r/languagelearning/1ot9zd4、r/HelloTalk/1drz0oh、r/languagelearning/1sk78qd、r/languagelearning/koci4k、r/languagelearning/1rl7ewe、r/HelloTalk/1oog705、medium.com/.../exhausting-for-women、r/languagelearning/1hhwoav、r/startups/1fpvxf3、zhihu.com/en/answer/16246331、r/taiwan/1g73ubo、learntolanguage.com、theseus.fi/.../Farabi_Al.pdf、518.com.tw/article/2251、clarishealthcare.com/.../senior-loneliness、dcard.tw/f/job/p/258187149、ptt.cc/bbs/Salary/M.1614919059.A.375.html、r/languagelearning/105qc3k、16dlhuu、1ioyasv、r/HelloTalk/1ex0mep、r/retirement/15jpezt、medium.com/.../time-banking

### 9.4 任務執行紀錄(v2 修正版)

- **v2 修正版啟動**:2026-06-10 11:43
- **4 個 worker 派遣**:11:43 ~ 11:51(8 分鐘平行)
  - Worker 1(標竿 + SkillSwap.io 必抓):4m 30s
  - Worker 2(Airbnb 7 層):2m 20s
  - Worker 3(Reddit 消費者 + Persona 標記):6m 12s
  - Worker 4(技能交換 + Persona 標記):7m 51s
- **summarizer 整合**:11:52 ~ 11:58(6m 9s,讀 _plan.md + 4 worker 檔)
- **總耗時**:11 分鐘
- **總資料量**:74 KB(_raw/) → 12.5 KB(_summary.md) → **27 KB(本報告)**
- **v2 修正版改進**:
  - ✅ 涵蓋 SkillSwap.io(v2 原始漏)
  - ✅ 保留 v1 全部 3 個使用者原意 Persona
  - ✅ 新增功能矩陣表(v2 原始漏)
  - ✅ 明確標竿分類(直接/間接/跨領域)
  - ✅ 新增 2 個 _raw/ 歸納 Persona(阿哲、Lily)
- **架構**:Orchestrator(default) → 4 web-workers(獨立 hermes session,context 隔離) + summarizer
- **主 session context**:30-50K(可控,v1 失敗時 108K)
