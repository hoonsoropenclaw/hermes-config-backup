# School Bulletin — Consumer Researcher 派遣計劃

建立日期: 2026-06-11
負責代理: consumer-researcher
專案 slug: school-bulletin

---

## ★ 使用者原意 Persona(寫死,summarizer 必須保留)

### Persona 1:小美(教務處行政人員)
- **角色**:台灣高中教務處行政助理,工作年資 3-5 年
- **日常工作**:每天要發 5-10 則公告(考試、課表異動、研習、競賽、學籍、升學),經手附件(word/PDF/Excel)
- **痛點猜測**:多處室沒有統一發布平台、附件散落在 email、Line 群、家長 FB 社團、學校官網

### Persona 2:佐藤(高二學生)
- **角色**:普通高中二年級學生,同時參加 2 個社團+ 1 個校隊
- **使用情境**:用手機看公告,需要快速知道「跟考試有關」、「跟我參加的活動有關」、「跟我選的組有關」
- **痛點猜測**:Line 群洗版、不知道哪則公告重要、附件下載後找不到、過期公告沒清掉

### Persona 3:陳媽媽(家長會代表)
- **角色**:家長會副會長,兩個小孩(國中+ 高中),職業是護理師需輪班
- **使用情境**:上下班空檔用手機看學校公告,要能快速過濾「我家小孩的年級」「特定處室」
- **痛點猜測**:多個孩子 = 多個學校系統要登入、公告洗版找不到重要訊息、不知道哪些是「已讀」

---

## Worker 派遣清單(共 4 個,平行執行)

### Worker 1:台灣校園 eNotice / 校務行政系統公告模組(必抓清單 1)
- **目標**:至少 2 個台灣校園公告系統標竿
- **必抓**:
  - 校務行政系統公告模組(校務系統 / 教務 / 學務子系統,例:神通、奇禾、優派)
  - 臺灣校園 e 化(校園 e 化 / eNotice / tNotice)
  - 校園 APP 平台(校園資訊系統 APP、均一、酷課雲相關)
- **輸出路徑**:`/home/hoonsoropenclaw/.hermes/handoff/school-bulletin/_raw/worker-1-taiwan-enotice.md`

### Worker 2:通用企業公告/通知平台(必抓清單 2)+ 標籤+多邏輯篩選(必抓清單 3)
- **目標**:至少 2 個企業標竿 + 至少 1 個標籤篩選標竿
- **必抓**:
  - Microsoft Teams 公告頻道(Channels announcement feature)
  - Slack announcement channels
  - Notion(公告 database + filter)
  - Yammer / Viva Engage
  - **標籤+多邏輯篩選**:Gmail labels、Notion filters、Trello labels、Jira JQL
- **輸出路徑**:`/home/hoonsoropenclaw/.hermes/handoff/school-bulletin/_raw/worker-2-enterprise-and-tags.md`

### Worker 3:多角色登入/權限分離(必抓清單 4)+ 附件系統(必抓清單 5)
- **目標**:至少 1 個 RBAC 標竿 + 至少 1 個附件系統標竿
- **必抓**:
  - WordPress roles & capabilities
  - Notion workspaces
  - Slack workspaces
  - **附件**:Google Drive + sharing、OneDrive、Notion page attachments
- **輸出路徑**:`/home/hoonsoropenclaw/.hermes/handoff/school-bulletin/_raw/worker-3-rbac-and-attachments.md`

### Worker 4:台灣校園公告真實痛點(學生/家長/老師抱怨 + 評比)
- **目標**:抓台灣 PTT / Dcard / Facebook 校園社群的真實抱怨 + 處室行政人員論壇
- **必抓方向**:
  - PTT 看板:Teacher 板、HighSchool 板、JuniorHigh 板、ParentChild 板
  - Dcard 搜尋:「學校公告」、「校務系統」、「校園 APP」、「tNotice」
  - Facebook 搜尋:家長社團抱怨文
  - 痛點面向:多處室沒統一平台、Line 群洗版、附件下載不便、標籤缺失、行動裝置體驗、權限混亂
- **輸出路徑**:`/home/hoonsoropenclaw/.hermes/handoff/school-bulletin/_raw/worker-4-taiwan-painpoints.md`

---

## Orchestrator 整合後的必交付(consumer-needs-research.md)
1. 3 個 Persona(用上面寫死的小美/佐藤/陳媽媽)
2. 5 個必抓標竿(每個寫:它是什麼、它的「公告/標籤/登入/附件」設計如何、真實評論或評比來源 URL)
3. 功能需求清單(MoSCoW,標籤 OR/AND 篩選必是 Must)
4. 痛點觀察(台灣校園公告常見的 5 個痛)
5. 全文繁體中文

## 禁止事項(do NOT)
- ❌ 不要寫 PRD
- ❌ 不要做技術選型(framework、DB、API)
- ❌ 不要定開發時程
