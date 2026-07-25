# Worker-2 報告:企業公告平台 + 標籤多邏輯篩選標竿抓取

> 任務:抓取企業公告/通知平台 + 標籤 + 多邏輯篩選設計模式的真實標竿
> 抓取時間:2026-06-11
> 抓取範圍:2 大類(企業公告平台 5 個 + 標籤邏輯平台 4 個)
> 標記:純事實抓取、不做分析與建議

---

## 標記類型說明

- **[企業公告直接標竿]**:核心公告/通知功能產品
- **[標籤邏輯直接標竿]**:多標籤 + AND/OR/NOT 邏輯篩選的標竿產品
- **[備援標竿]**:可選用、非首選

---

# PART A: 企業公告/通知平台

---

## A1. Microsoft Teams Channel Announcements [企業公告直接標竿]

### 基本資訊
- **名稱**:Microsoft Teams Channel Announcements(頻道公告功能)
- **定位**:在 Teams 頻道內發送「格式化的視覺公告」,而非普通對話訊息
- **客群**:Microsoft 365 企業用戶、教育用戶(學校 / 班級)
- **上線時間**:Microsoft Teams 內建功能,屬於頻道 post 格式的一種(無獨立發布日期,跟 Teams 主產品一起迭代)
- **定價**:隨 Microsoft Teams 訂閱方案提供(免費版 / Essentials / Business Basic / Standard / Enterprise)

### 公告功能設計
- **誰能發公告**:頻道內任何成員皆可在切換到「Announcement」格式後發公告(權限由 channel 層級控制;若 channel 設為「只有 owner 可發 post」,則只有 owner 能發)。[來源:Microsoft Support](https://support.microsoft.com/en-us/teams/teams-channels/send-an-announcement-to-a-channel-in-microsoft-teams)
- **能不能置頂**:無原生「公告置頂」機制;Teams 頻道 post 是依時間排序,公告跟一般 post 混在一起。但有 `Pinned posts`(釘選)功能,可由 channel owner / moderator 手動釘選(不專屬於公告)。
- **已讀功能**:**無**。Microsoft Teams 公開 Q&A 明確指出:「Teams does not currently support read receipts for channel posts」;read receipts 只支援 1:1 與群組聊天,且聊天超過 20 人自動關閉。[來源:Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2262919/microsoft-teams-read-receipts)
- **推播/通知**:公告會依 channel 通知設定送達(activity feed / banner);若在公告中使用 `@channel` 或 `@team`,會主動通知全頻道或全團隊成員(透過 Teams 與 email)。[來源:Microsoft Support - Announcements and tabs](https://support.microsoft.com/en-us/teams/education/announcements-and-tabs-in-microsoft-teams)
- **附加檔案**:支援(公告 compose 視窗可附加檔案 / 圖片)
- **標記受眾(指定誰要收到)**:**有限支援**。Teams 本身以「整個 team 或整個 channel」為單位;若要對全公司廣播,需建立「All-Company team」(上限 25,000 人,2024 後從 20K 提升)並把公告 post 到該 team 的 channel。對部分子集廣播需要靠 `Audience` 功能(在 Viva Connections / Viva Amplify 中才有精細受眾控制)。[來源:Reddit r/MicrosoftTeams](https://www.reddit.com/r/MicrosoftTeams/comments/17m5bti/announcements_in_teams)
- **時效性(下線)**:無原生「公告自動下線」設定。公告會永遠留在 channel 中,需手動刪除。

### 公告格式細節
- 提供 **Headline**(標題)+ **Color scheme**(背景色)+ **Background image**(背景圖,含 AI-powered image generation)
- 公告**僅在頻道內**可用,**不可用於 1:1 或群組聊天**。[來源:Microsoft Support](https://support.microsoft.com/en-us/teams/teams-channels/send-an-announcement-to-a-channel-in-microsoft-teams)

### 真實評比

**G2 / Capterra**:Teams 作為整體產品在 G2 上獲得高度評價;但「Channel Announcements」作為單一子功能沒有獨立評分。G2 上的「Microsoft Teams」條目為主。

**Reddit r/MicrosoftTeams** 對「announcement」功能的討論反映常見痛點:
- 「Is there a way in Teams to have an all-organizational type of announcement that is sent to everyone?」— 原 PO 反映**沒有乾淨的全公司公告機制**,建議用 All-Company Team(限 25,000 人)、Company Communicator 開源 app、或付費的 Viva Amplify。
- 社群主流建議:免費用「All-Company team + restricted posting」;若需要更精細受眾管理、發送追蹤、報告 → 改用 **Viva Amplify**(付費)。
- 公司通訊開源 app「Company Communicator」可自架(GitHub: `OfficeDev/microsoft-teams-apps-company-communicator`),但微軟正在把它淘汰、由 Viva Amplify 取代。
- [來源:Reddit r/MicrosoftTeams 討論](https://www.reddit.com/r/MicrosoftTeams/comments/17m5bti/announcements_in_teams)
- [來源:Microsoft Q&A - 公告已讀問題](https://learn.microsoft.com/en-us/answers/questions/4392852/annoucements-in-ms-teams-get-an-overview-of-who-ha)

**Microsoft Q&A 確認「已讀回條缺失」是常見抱怨**:有公司明確反應「We would like to move to MS Teams to make announcements and updates on business related topics… how to know who has seen it?」— 這條問題在 Microsoft Q&A 沒有乾淨的官方解法。

### 來源 URL 彙整
- 官方:https://support.microsoft.com/en-us/teams/teams-channels/send-an-announcement-to-a-channel-in-microsoft-teams
- 官方(教育版):https://support.microsoft.com/en-us/teams/education/announcements-and-tabs-in-microsoft-teams
- 官方:https://support.microsoft.com/en-us/teams/teams-channels/manage-channel-notifications-in-microsoft-teams
- 第三方:https://utiatechnology.tennessee.edu/microsoft-teams-tip-channel-conversations-and-announcements
- 第三方(社區):https://learn.microsoft.com/en-us/answers/questions/4392852/annoucements-in-ms-teams-get-an-overview-of-who-ha
- Reddit:https://www.reddit.com/r/MicrosoftTeams/comments/17m5bti/announcements_in_teams
- 開源補充(Company Communicator):https://github.com/OfficeDev/microsoft-teams-apps-company-communicator
- 付費補充(Viva Amplify):https://www.microsoft.com/en-us/microsoft-viva/amplify
- 已讀機制極限:https://office365itpros.com/2020/01/13/teams-read-receipts-personal-chats
- 20 人 read receipt 限制:https://learn.microsoft.com/en-us/answers/questions/5663652/teams-read-receipts-disabled-in-group-chat-after-e

---

## A2. Slack Announcement Channels [企業公告直接標竿]

### 基本資訊
- **名稱**:Slack Announcement Channels(公告頻道)
- **定位**:把「任何 channel」轉為「只允許特定對象發 post」的單向公告空間,降低噪音、確保 single source of truth
- **客群**:中大型企業(Slack Plus / Enterprise Grid 客戶);Salesforce 收購後擴展
- **上線時間**:**2019 年 8 月 14 日**(官方部落格發文日:[Slack Blog: Managing Slack at scale](https://slack.com/blog/transformation/managing-slack-at-scale-announcement-channels-and-new-admin-apis))
  - 註:研究需求中提到「2020 年」應為「2019 年 8 月 14 日」的概略,實際官方公告日為 **2019-08-14**;2020 起 Enterprise Grid 客戶大量採用。
- **定價**:**Slack Plus 與 Enterprise Grid 方案才支援**;一般 Free / Pro / Business+ 預設不開啟此權限。[來源:Slack Blog](https://slack.com/blog/transformation/managing-slack-at-scale-announcement-channels-and-new-admin-apis)

### 公告功能設計
- **誰能發公告**:Admin / Owner 可把任何 channel 設為「只有指定成員(最多 100 人)能發 post」,其他成員只能讀、回 thread。Admin 可進一步限制「誰能改 channel posting permissions」。[來源:Slack Help](https://slack.com/help/articles/360004635551-Manage-channel-posting-permissions)
- **能不能置頂**:**無原生「置頂公告」機制**。Slack 改用「公告 channel 模式」本身:任何人打開 channel 看到的都是「公告」內容(因為其他人被限制發文)。如需「釘選一則訊息到 channel 頂端」需用 Canvas(2022 後)或第三方整合。
- **已讀功能**:**無**。Slack 公告 channel 不提供已讀回條;反應用 emoji reaction(:eyes: 看到、:white_check_mark: 確認)是社群常用的「軟性」已讀替代方案。Slack 官方部落格明確提到:"Emoji reactions on messages provide instant insights into how people feel about announcements"。[來源:Slack Blog](https://slack.com/blog/transformation/managing-slack-at-scale-announcement-channels-and-new-admin-apis)
- **推播/通知**:公告 channel 內的訊息預設仍會送 channel 通知給所有訂閱者;但 admin 可關閉「不允許 @channel / @here / @everyone」(避免被濫用來打擾所有人)。[來源:Slack Help - Manage channel posting permissions](https://slack.com/help/articles/360004635551-Manage-channel-posting-permissions)
- **附加檔案**:支援(Slack 原生檔案 / 連結 / Canvas)
- **標記受眾(指定誰要收到)**:**有限支援**。Slack 是「channel-based membership」模型,要把公告送給「全校」需訂閱同一個 channel(All-Company 或 #announcements-global 等);不能像 email 那樣精細到個人。Slack Connect(2020 起)允許跨組織 channel。
- **時效性(下線)**:無內建「公告時效」機制。Slack 提供 `Scheduled messages` 排程發送,以及 Workflow Builder 自動 archive,但都不是公告「自動下線」功能。

### 公告設計的官方說法
- 官方目標:**降低噪音、讓重要訊息不被淹沒**。原文:"Keeps surrounding chatter to a minimum, leaving the space clear for important updates"。
- 典型命名慣例:`#announcements-it`、`#announcements-usa`、`#announcements-global`(地域 / 部門 / 公司層級公告)
- 額外設計:可允許成員「在 thread 內回覆」,不污染主 channel。[來源:Slack Blog](https://slack.com/blog/transformation/managing-slack-at-scale-announcement-channels-and-new-admin-apis)
- Slack 自家 `#announcements-global` 範例:每週由 internal comms team 發送「公司頭條新聞、各部門頭條、公司 metrics、重要 deadline」一站式 digest。[來源:Slack Blog - How channels extend the reach of internal communications](https://slack.com/blog/collaboration/slack-on-slack-how-channels-extend-the-reach-of-internal-communications)

### 真實評比
- **G2**:Slack 在 G2 獲得 4.5/5 評分(23,000+ reviews 為整體 Slack 產品)
- **Capterra**:4.7/5(整體 Slack 評分)
- **G2 / Capterra** 沒有對「Announcement Channel」單獨評分;它是 Slack 整體的子功能
- [來源:Delightree 彙整](https://www.delightree.com/competitor-alternatives/slack-alternatives)

**Reddit r/Slack** 對 announcement channel 結構的真實討論:
- 160 人 / 5 國的 Business+ workspace 主問「怎麼架 announcement channel 才不會太散」,社群主流建議:
  - 從「現有的公告類型」出發,不要一開始就為每個部門建頻道
  - 「Ask who is the target audience」— 不要每件事都 @ 全員
  - 用 workflow 把「送公告」標準化(避免被當聊天區用)
  - 把所有 announcement channel 用 **Sidebar sections** 分群
- 範例結構:`announce-global` / `announce-devel` / `announce-us` / `announce-incidents` / `announce-biztech`
- [來源:Reddit r/Slack](https://www.reddit.com/r/Slack/comments/132a725/how_do_you_setup_announcement_channels)

**Reddit r/Slack 另一條**反映「公告 channel 不能用 app 自動發」的痛點:
- 「Restricted posting in public channel, but allow for apps」— 想讓 announcement channel 接受「人發的 + 整合 app 自動發」,但 Slack 公告 channel 預設會擋掉整合 bot;需手動開白名單。
- [來源:Reddit r/Slack](https://www.reddit.com/r/Slack/comments/1asha1y/restricted_posting_in_public_channel_but_allow)

### 來源 URL 彙整
- 官方公告文(2019-08-14):https://slack.com/blog/transformation/managing-slack-at-scale-announcement-channels-and-new-admin-apis
- 官方:https://slack.com/help/articles/360004635551-Manage-channel-posting-permissions
- 官方(自家案例):https://slack.com/blog/collaboration/slack-on-slack-how-channels-extend-the-reach-of-internal-communications
- 官方 Whats New:https://slack.com/whats-new
- Reddit:https://www.reddit.com/r/Slack/comments/132a725/how_do_you_setup_announcement_channels
- Reddit:https://www.reddit.com/r/Slack/comments/1asha1y/restricted_posting_in_public_channel_but_allow
- 第三方:https://www.delightree.com/competitor-alternatives/slack-alternatives

---

## A3. Notion 公告 Database + Page [企業公告直接標竿 — 備援]

### 基本資訊
- **名稱**:Notion 公告 Database + Page
- **定位**:Notion 不是「公告平台」,但常用「Database(篩選 + 標籤) + 公開 Page」做為企業/團隊公告系統
- **客群**:中小團隊 / SaaS 公司 / 教育機構(很多學校老師用 Notion 做公告)
- **上線時間**:Notion 2016 上線;Database 功能 2018 後成熟;Web publishing 2020 起;Nested filters 2020-05 推出
- **定價**:Free / Plus / Business / Enterprise

### 公告功能設計
- **誰能發公告**:Notion 沒有「公告」物件,但可透過「Database」設計一個「公告 board」,設定 teamspace 權限控管誰能新增 page。[來源:Notion Help](https://www.notion.com/help/views-filters-and-sorts)
- **能不能置頂**:**無內建公告置頂**。實務做法:在 page 頂端放一個「callout / toggle」段,或用 **Database view** 把重要 page 排序到最上面。Database 本身可手動 `Sort by priority`。
- **已讀功能**:**無**。Notion page 沒有讀者清單 / 已讀回條(只有 page analytics 在 paid plan 提供「page view 次數」,**不是「誰看到」**)。
- **推播/通知**:Notion 提供「comment notification」與「mention notification」;但**公告 page 本身沒有「所有人自動推播」機制**,需手動 @ mention 對方。
- **附加檔案**:完整支援(任何 block 內含 file / image / embed)
- **標記受眾**:Database 內可加 `Audience` 屬性(select / multi-select);但 Notion **沒有「公告指定受眾後自動只讓那些人看到」機制** — 權限是 page-level 共享。
- **時效性(下線)**:`Publish to web` 提供 `Link expires` 選項 — 公開 page 可設 URL 到期日。[來源:Notion Help](https://www.notion.com/help/guides/publish-notion-pages-to-the-web)
- **發布為公開網站**:`Share → Publish` 一鍵把 page 變成可被搜尋引擎索引的公開網站(有 SEO/GA/custom domain 等 paid 選項)。[來源:Notion Help](https://www.notion.com/help/public-pages-and-web-publishing)

### 真實評比
- **Notion 官方 Templates gallery** 有大量「公告 / 內部溝通」模板
- **Reddit r/Notion** 對「share a read-only, filtered database view」的反應:常見抱怨是「Notion 沒辦法真正分享只讀 + 篩選後的 view,除非對方有 Notion 帳號,且能改 filter」— 這對企業公告的可控性是痛點。
- [來源:Reddit r/Notion - read-only filtered view](https://www.reddit.com/r/Notion/comments/1omlndr/why_is_it_still_impossible_to_share_a_truly)

### 來源 URL 彙整
- 官方(發布為公開網站):https://www.notion.com/help/public-pages-and-web-publishing
- 官方(發布指南):https://www.notion.com/help/guides/publish-notion-pages-to-the-web
- 官方(views / filters):https://www.notion.com/help/views-filters-and-sorts
- Reddit:https://www.reddit.com/r/Notion/comments/1omlndr/why_is_it_still_impossible_to_share_a_truly
- 模板庫:https://www.notion.com/templates/collections/publish-to-web

---

## A4. Confluence Blog Posts / Space Announcements [企業公告直接標竿 — 備援]

### 基本資訊
- **名稱**:Atlassian Confluence Blog Posts + Space Announcements
- **定位**:Confluence 內每個 Space 可設「Blog」功能(類似企業內部落格);新文章透過 watcher / email / 通知發送給訂閱者
- **客群**:企業 IT / 開發團隊 / 文件密集型組織
- **上線時間**:Confluence 2004 上線;Blog 功能自 v1 就有
- **定價**:Confluence Cloud Free / Standard / Premium / Enterprise

### 公告功能設計
- **誰能發 blog post**:依 Space permission;預設「Create blog post」權限需手動授予
- **能不能置頂**:**有限**。Space 主頁可設「Featured」(由管理員挑選置頂內容);blog post 本身不提供「永久釘選」。[來源:Confluence Documentation - Blog posts](https://confluence.atlassian.com/spaces/DOC/pages/834222533/Blog+posts)
- **已讀功能**:**無**。Confluence 只提供 page view counter(非個人層級)
- **推播/通知**:使用者可「Watch」page / blog post / space → 任何更新透過 email 推播;新 blog post 預設會通知所有 watcher。[來源:Confluence Documentation - Watch](https://confluence.atlassian.com/spaces/DOC/pages/834222533/Blog+posts)
- **附加檔案**:完整支援
- **標記受眾**:無;Watcher 是「整個 blog / space」訂閱,不能精細到「某部門才看」
- **時效性(下線)**:**無**。Confluence blog post 預設永久存在(可手動刪除 / archive)
- **可被 watch 的好處**:能訂閱整個 blog,新文章自動到信;不需手動進去看

### 真實評比
- **Atlassian Community** 真實抱怨:有使用者反映「Confluence blog post is sending notifications every time an update happens」— 意即**每改一次 blog post 就通知所有 watcher**,沒有「只通知首次發布」的控制項,這對公告是個噪音源。
- [來源:Atlassian Community](https://community.atlassian.com/forums/Confluence-questions/Confluence-blog-post-is-sending-notifications-every-time-an/qaq-p/1121849)
- 另有用戶要求「Configure new Blog post email notifications to only show excerpt」— 預設 email 是**全文寄送**,對長篇公告體驗不佳。
- [來源:Atlassian Community](https://community.atlassian.com/forums/Confluence-questions/Configure-new-Blog-post-email-notifications-to-only-show-excerpt/qaq-p/1025416)

### 來源 URL 彙整
- 官方(Blog posts):https://confluence.atlassian.com/spaces/DOC/pages/834222533/Blog+posts
- 官方(Watch pages, blogs, spaces):https://support.atlassian.com/confluence-cloud/docs/watch-pages-spaces-and-blogs
- 官方(Email notifications):https://confluence.atlassian.com/spaces/CONF93/pages/1502350695/Email+Notifications
- 官方(Best practices):https://www.atlassian.com/software/confluence/resources/guides/best-practices/productive-blogging
- Atlassian Community 評論:https://community.atlassian.com/forums/Confluence-questions/Confluence-blog-post-is-sending-notifications-every-time-an/qaq-p/1121849

---

## A5. Microsoft Viva Engage (前身 Yammer) [企業公告直接標竿 — 備援]

### 基本資訊
- **名稱**:Microsoft Viva Engage(2023 改名;前身為 Yammer,2012 被微軟收購)
- **定位**:企業內部「社群網路」,類似 Facebook for work — 公告、Q&A、貼文、pinned post
- **客群**:Microsoft 365 企業用戶
- **上線時間**:Yammer 2008 創立;2012 微軟收購;2023 改名 Viva Engage
- **定價**:隨 Microsoft 365 / Viva Suite 訂閱

### 公告功能設計
- **誰能發公告**:Community Admin 可發「Announcement」類型 post,「pushes notifications of a post into members' inbox」(強制推播到成員收件匣,不受個人通知設定影響)。[來源:Cornell IT - Viva Engage Community Admin Guide](https://it.cornell.edu/sites/default/files/itc-drupal10-files/Viva-Engage-Community-Admin-Guide-and-Best-Practices.pdf)
- **能不能置頂**:**有「Pinned post」**。社區管理員可把 post 釘選在 feed 頂端;但預設是「collapsed」(折疊),目前**沒有 setting 可以強制展開** — 微軟 Q&A 確認此限制。[來源:Microsoft Q&A](https://learn.microsoft.com/en-au/answers/questions/5509438/viva-engage-pinned-posts-issue-default-collapsed)
- **已讀功能**:**無**。Viva Engage 沒有個人層級的「誰看到了」報告;只能看到「reactions / replies / views 總數」
- **推播/通知**:**Announcement 強制推播** + 一般 post 可 @ mention + Viva Engage Email digest(可訂閱)
- **附加檔案**:支援
- **標記受眾**:依「Community membership」;社區成員自動收到該社區的 announcement
- **時效性(下線)**:**無**。Viva Engage 沒有「公告自動下線」機制;只有「Featured conversation」(精選對話,類似置頂)由 admin 控制

### 真實評比
- **Atlassian / Microsoft Q&A / Reddit** 反映兩個痛點:
  1. **Pinned post 預設 collapsed** — 釘選了大家也看不到內容,釘選變得無效
  2. **Pinned section 編輯限制** — 對 pinned 順序的調整能力不足
- [來源:Microsoft Q&A - Viva Engage Pinned Posts Issue](https://learn.microsoft.com/en-au/answers/questions/5509438/viva-engage-pinned-posts-issue-default-collapsed)
- [來源:Microsoft Tech Community - Editing Pinned Section](https://techcommunity.microsoft.com/discussions/viva_engage_community_managers/editing-the-pinned-section-in-my-viva-engage-community/4208322)

### 來源 URL 彙整
- 官方:https://support.microsoft.com/en-us/viva/engage/vivaengage/feature-a-conversation-in-viva-engage
- 官方(改名):https://m365admin.handsontek.net/viva-engage-pinned-resources-related-communities-teams-ios-2
- 第三方(學校 IT 指南):https://it.cornell.edu/sites/default/files/itc-drupal10-files/Viva-Engage-Community-Admin-Guide-and-Best-Practices.pdf
- 社區抱怨:https://learn.microsoft.com/en-au/answers/questions/5509438/viva-engage-pinned-posts-issue-default-collapsed
- 社區抱怨:https://techcommunity.microsoft.com/discussions/viva_engage_community_managers/editing-the-pinned-section-in-my-viva-engage-community/4208322

---

# PART B: 標籤 + 多邏輯篩選設計模式

---

## B1. Gmail Labels + Multiple Label Search [標籤邏輯直接標竿]

### 基本資訊
- **名稱**:Gmail Labels(可多重套用 + search operator 邏輯篩選)
- **定位**:Email 標籤系統,支援「多重標籤 + 邏輯運算子」搜尋
- **客群**:個人 / 企業 Gmail 用戶
- **上線時間**:Gmail 2004 上線,標籤系統自始即為核心;search operator 多邏輯(`AND/OR/NOT`)為其後擴充
- **定價**:Gmail Free / Workspace

### 多標籤 + AND/OR/NOT 邏輯設計
Gmail 的搜尋 bar **本身就是一套邏輯查詢語言**,支援以下運算:

| 概念 | Gmail Search 語法 |
|------|-------------------|
| AND | 多個條件用 **空格** 隔開(預設為 AND) |
| OR | 大寫 `OR`(必須大寫),例: `from:alice OR from:bob` |
| NOT | 字首加 `-`,例: `-is:snoozed` |
| 群組 | 用 `( )` 把 OR 條件包起來,例: `(has:red-bang -is:snoozed) OR (in:draft -has:yellow-bang)` |
| Label | `label:ProjectA`、`label:Work` |
| 多 label(AND) | `label:Project2025 label:TrumpAdmin` (空格分隔) |
| 多 label(OR) | `label:{Project2025 OR TrumpAdmin}` (大括號=OR) |
| 排除 label | `-label:Spam` |

[來源:Google Support - Multiple Inbox Search Operators](https://support.google.com/mail/thread/98207778/multiple-inbox-search-operators-combining-or-and-not-logic?hl=en)

**範例(經典 3-層邏輯)**:
```
(has:red-bang -is:snoozed) OR (in:draft -has:yellow-bang -has:red-star -has:yellow-star)
```

### 設計理念 / 限制
- **設計理念**:讓使用者用「搜尋」就能精準找到想要的 email,**不需為每種過濾建 folder**。所有 label 都能 AND / OR / NOT 組合。
- **UI 設計**:搜尋 bar **就是 query bar** — 不像 Notion 是「filter builder」,Gmail 是「query string」+ 一個「Create filter」按鈕(把常用 query 存成自動 filter)。
- **「Create filter」** 可把 query 變成「自動套用 label / 跳過 inbox / 轉寄 / 刪除」等動作。
- **限制**:**搜尋是「整個 conversation(對話串)級別」,不是「單一訊息級別」**。即使對話串內只有一封信符合條件,整個串都會出現;反之,若對話串內有任何一封信符合 NOT 條件的 label,排除也會失效。
- [來源:Web Applications Stack Exchange](https://webapps.stackexchange.com/questions/62881/excluding-messages-with-a-given-label-is-ignored-if-other-messges-in-the-convers)

### 真實評論
- **Reddit r/GMail** 反映出兩派:
  - **進階派**:「Parentheses can be used in place of AND, and curly brackets in place of OR」— 把 Gmail 搜尋當作「小型程式語言」用,覺得強大但要學
  - **入門派**:**用「Create filter」UI 表單**比較直覺;query string 對非技術人員不友善
- 常見痛點:**「Filter has words」欄位不支援多個 AND 條件** — 例如想要 `from: AND to: AND subject:(test AND demo)` 需用 `from: to: subject:(test AND demo)`(大寫 AND 才有效);Stack Overflow 有大量此類討論。
- [來源:Stack Overflow](https://stackoverflow.com/questions/22460488/gmail-filter-has-words-how-to-include-multiple-and-queries)
- [來源:Reddit r/GMail](https://www.reddit.com/r/GMail/comments/1fmkbee/filter_search_by_multiple_tagslabels)

### 來源 URL 彙整
- 官方論壇(完整語法):https://support.google.com/mail/thread/98207778/multiple-inbox-search-operators-combining-or-and-not-logic?hl=en
- 官方(Kinsta 整理的 operator 清單):https://kinsta.com/blog/gmail-search-operators
- 第三方(cloudHQ,多 label 過濾):https://support.cloudhq.net/how-to-create-gmail-filter-with-multiple-labels-as-a-tab
- API 視角(Nylas):https://cli.nylas.com/guides/gmail-categories-api
- Reddit:https://www.reddit.com/r/GMail/comments/1fmkbee/filter_search_by_multiple_tagslabels
- Stack Overflow:https://stackoverflow.com/questions/22460488/gmail-filter-has-words-how-to-include-multiple-and-queries
- 限制(Web Apps SE):https://webapps.stackexchange.com/questions/62881/excluding-messages-with-a-given-label-is-ignored-if-other-messges-in-the-convers

---

## B2. Notion Database Filters (Advanced / Nested) [標籤邏輯直接標竿]

### 基本資訊
- **名稱**:Notion Database Filters — Advanced / Nested
- **定位**:Database 內每個 view 可設 filter;新版本支援「nested filter groups」(AND/OR 巢狀)
- **客群**:Notion 個人 / 團隊用戶
- **上線時間**:基礎 filter 2018+;**Nested filter groups 於 2020-05 推出**(被 Notion 社群暱稱為「Nested filtering」);**Advanced Database Filters 於 2024-05 推出**(更豐富的 filter capability)
- **定價**:Free / Plus / Business / Enterprise

### 多標籤 + AND/OR/NOT 邏輯設計

**2020-05 之前**:Notion 的 filter UI **只能「全部 AND」或「全部 OR」**,**無法在同一個 filter 內混用 AND 與 OR**。這被社群視為大缺陷。[來源:Reddit r/Notion](https://www.reddit.com/r/Notion/comments/f6pwiv/creating_more_complex_database_filters)

**2020-05 推出 Nested Filters**:可以新增「filter group」,每個 group 內的條件 AND/OR 各自設定,group 之間還能再選 AND/OR,形成**巢狀邏輯**。例如:`(Status=A AND Priority=Urgent) OR (Status=B AND DueDate<today)` 變成可表達。

**2024-05 推出 Advanced Database Filters**:強化對日期、status、formula 等的 filter 能力;filter 群組依然是「AND/OR 邏輯」核心。[來源:Notion Help - Advanced database filters](https://www.notion.com/help/guides/using-advanced-database-filters)

**API 層面**:Notion API 對 filter 的設計是「top-level AND,各條件內可含 OR」,與 SQL WHERE 概念一致。`filter` 接受 `and` / `or` 陣列,內可放各種 property condition。[來源:Notion API Docs - Filter database entries](https://developers.notion.com/reference/post-database-query-filter)

### 設計理念
- Notion 的哲學:**filter 是 view-level 的「可分享設定」**,每個 view 可有不同 filter;分享 view link 時別人只看到 filter 後的結果(view 可獨立被分享)。
- Notion 官方說法:"Filter groups are useful when combining `AND` logic and `OR` logic in your filter"。[來源:Notion Help](https://www.notion.com/help/guides/using-advanced-database-filters)

### 真實評論
- **2020-05 之前** r/Notion 充滿抱怨:「I can't find a way to create AND/OR rules in the SAME database filter. It seems like rules in a filter must be…」
- **2020-05 推出 nested** 後被譽為「a long-awaited feature」([Reddit](https://www.reddit.com/r/Notion/comments/gsbrtf/a_long_awaited_feature_is_here_nested_filtering))。但仍有用戶反映「limitations」— 特別是「shared view 仍可被對方改 filter」的權限問題。
- **Formula workaround 經典**:有高手(如 Notion 社群名人 ben-something)寫出用 formula property 模擬複雜 AND/OR 的 workaround,證明**雖然 nested filter 出來了,仍有人偏好 formula 表達更彈性**。
  - 範例: `formatDate(prop("Due Date"), "L") == formatDate(now(), "L") or format(...) == formatDate(...)` 把「昨天或今天」壓成一個 formula checkbox,然後 filter 用 checkbox 篩。
- [來源:Reddit r/Notion - complex filter workaround](https://www.reddit.com/r/Notion/comments/f6pwiv/creating_more_complex_database_filters)
- **複雜度/效能抱怨**:Database 過大或 formula 太複雜會讓 Notion 變慢,這是過度設計 filter 的副作用。
- [來源:Reddit r/Notion - 複雜度](https://www.reddit.com/r/Notion/comments/1keikmg/what_makes_a_database_complex_in_terms_of_how)

### 來源 URL 彙整
- 官方(Advanced filters):https://www.notion.com/help/guides/using-advanced-database-filters
- 官方(views / filters / sorts):https://www.notion.com/help/views-filters-and-sorts
- 官方 API(filter 規格):https://developers.notion.com/reference/post-database-query-filter
- Reddit(Nested 推出):https://www.reddit.com/r/Notion/comments/gsbrtf/a_long_awaited_feature_is_here_nested_filtering
- Reddit(複雜 filter):https://www.reddit.com/r/Notion/comments/f6pwiv/creating_more_complex_database_filters
- Reddit(複雜度):https://www.reddit.com/r/Notion/comments/1keikmg/what_makes_a_database_complex_in_terms_of_how
- 第三方(Formula in filters):https://thomasjfrank.com/formulas/formulas-in-database-filters

---

## B3. Jira JQL (Jira Query Language) [標籤邏輯直接標竿]

### 基本資訊
- **名稱**:Jira Query Language (JQL)
- **定位**:Jira 內建的「議題搜尋查詢語言」,支援完整 AND/OR/NOT/IN/CONTAINS/WAS/ORDER BY 等 SQL-like 語法
- **客群**:軟體開發團隊 / 專案管理 / Agile squad
- **上線時間**:Jira 2002 上線;JQL 為 Jira 4(2010 左右)後的核心 search 功能
- **定價**:Jira Free / Standard / Premium / Enterprise

### 多標籤 + AND/OR/NOT 邏輯設計

JQL 是**最強**的標籤 + 多邏輯篩選設計標竿,語法幾乎是 SQL 子集:

**基本元素**:
- **Field**:議題的屬性(`project`、`status`、`assignee`、`priority`、`labels`、`fixVersion`...)
- **Operator**:`=`(等於) / `!=`(不等於) / `>` / `<` / `>=` / `<=` / `IN` / `NOT IN` / `~`(`CONTAINS`) / `IS` / `IS NOT` / `WAS` / `WAS NOT` / `WAS IN` / `WAS NOT IN`
- **Value**:具體值(Urgent / High / "Project Name" / JIRA-101)
- **Keyword**:`AND`(且)、`OR`(或)— **必須大寫**
- **Function**:`linkedIssues()`、`closedSprints()`、`endOfDay()`、`currentUser()`...

**完整 AND/OR/NOT 範例**:
```jql
Priority = Urgent AND Status != Done AND "Epic Link" = STAN-5
```
```jql
status IN ("To Do", "In Progress", "Closed")
```
```jql
assignee WAS francis
```
```jql
project = "BLOG" AND status = open AND fixVersion = "Current Sprint"
  AND fixVersion WAS "Last Sprint" AND (priority = Urgent OR priority = High)
```
```jql
due < endOfDay("+2") AND assignee = francis AND project = "BLOG" AND priority = Urgent
```

**Precedence(優先順序)**:
- **AND 優先於 OR** — `status=resolved OR project="Planning" AND assignee=Francis` 會被解析為 `status=resolved OR (project="Planning" AND assignee=Francis)`
- 用括號 `()` 明確覆寫優先順序
- 完整 precedence 文件:https://support.atlassian.com/jira-software-cloud/docs/jql-operators/

**UI 設計**:
- **Basic Search**:表單式 UI(Status dropdown / Assignee picker / Project picker)
- **Advanced Search**:**純文字 JQL 編輯框**,即時顯示 ✅ 綠勾(語法正確)或 ❌ 紅叉(語法錯誤),有 auto-suggest
- **Save As** 把 JQL 存成「saved filter」,可加到 dashboard 訂閱
- [來源:Atlassian Community - JQL Basics with Syntax](https://community.atlassian.com/forums/Jira-articles/JQL-Basics-with-Syntax/ba-p/2947797)
- [來源:Atlassian Support - Use advanced search with JQL](https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql)

### 設計理念
- **SQL-like 的 power + 「即時回饋」降低門檻** — 輸入時顯示綠勾/紅叉是經典設計
- **進階使用者** 可以寫複雜 saved filter(例如「上個 sprint 沒關 + 這次 sprint 還沒做 + 緊急或高優先」一鍵查)
- **JQL 是 Jira「saved filter → dashboard gadget → email subscription → automation」的源頭** — 整個 Jira 自動化的基礎

### 真實評論
- **Reddit r/jira** 主流聲音:JQL 是「最強大的 Jira 功能之一」,但「學習曲線陡」,需要練習
- 「How can I improve my JQL skills?」— 該 Reddit 貼文有大量留言提供學習資源;主流建議「先看官方 JQL operators / fields / functions / keywords 四個文件,再寫小 filter」
- [來源:Reddit r/jira](https://www.reddit.com/r/jira/comments/1t771c8/how_can_i_improve_my_jql_skills)
- 第三方文章「Is Jira Easy to Learn? A Comprehensive Analysis」認為 Jira UI 對非技術人不友善,JQL 雖然強大但「新手需要時間」
- [來源:Medium - Is Jira Easy to Learn](https://medium.com/@sajiveva1112000/is-jira-easy-to-learn-a-comprehensive-analysis-bca52c53ffc9)
- 現代趨勢:有 LinkedIn 貼文示範用 AI(Claude / ChatGPT)生成 JQL,降低學習門檻
- [來源:LinkedIn - Anahit Sukiasyan](https://www.linkedin.com/posts/anahitsukiasyan_jira-jql-atlassian-activity-7394310283256754176-Kn_1)

### 來源 URL 彙整
- 官方(Atlassian Community JQL 教學):https://community.atlassian.com/forums/Jira-articles/JQL-Basics-with-Syntax/ba-p/2947797
- 官方(JQL operators):https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql
- 官方(JQL fields):https://support.atlassian.com/jira-service-management-cloud/docs/jql-fields/
- 官方(JQL keywords):https://support.atlassian.com/jira-service-management-cloud/docs/jql-keywords/
- 官方(JQL functions):https://support.atlassian.com/jira-service-management-cloud/docs/jql-functions/
- 第三方(ScriptRunner 教學):https://www.scriptrunnerhq.com/inspiration/resources/tutorials/a-guide-to-jira-query-language
- 第三方(Salto 綜合指南):https://www.salto.io/blog-posts/jira-jql-guide
- 第三方(Amoeboids):https://amoeboids.com/blog/a-quickstart-guide-to-jira-query-language-jql
- Reddit:https://www.reddit.com/r/jira/comments/1t771c8/how_can_i_improve_my_jql_skills
- Reddit:https://www.reddit.com/r/jira/comments/1bbhpsx/jira_query_language_jql_beginner_guide
- Medium:https://medium.com/@sajiveva1112000/is-jira-easy-to-learn-a-comprehensive-analysis-bca52c53ffc9

---

## B4. Trello Labels [標籤邏輯直接標竿 — 備援]

### 基本資訊
- **名稱**:Trello Labels
- **定位**:Trello card 上的「色塊 + 文字」標籤,可用於視覺分類與 board 過濾
- **客群**:團隊 / 個人 / Kanban 用戶
- **上線時間**:Trello 2011 上線;labels 為核心功能
- **定價**:Free / Standard / Premium / Enterprise

### 多標籤 + AND/OR/NOT 邏輯設計

- **Trello labels = color + text(可選)**;**30 種顏色** + colorless 選項
- **單一 card 可掛多個 label**(無上限)
- **過濾機制**:**「Filter by labels」UI 介面** — 點選 label 後,只顯示「有該 label」的 cards
  - **邏輯本質**:每個 label 過濾 = `label = X` 的「OR」集合(多選多個 label = 任一符合即顯示 = **OR 邏輯**)
  - **無原生 AND 邏輯** — 不能用 UI 表達「同時有 label A 與 label B」
  - **無 NOT 邏輯** — 無法表達「不要某 label」
- [來源:Atlassian Support - Add a label to a card](https://support.atlassian.com/trello/docs/adding-labels-to-cards)
- [來源:Atlassian Community 提問 - 同色 label 多選](https://community.atlassian.com/forums/Trello-questions/Can-i-filter-a-trello-board-with-all-labels-of-same-color-but/qaq-p/912262)
- [來源:Unito 整理 - 5 種 Trello labels 用法](https://unito.io/blog/unlimited-trello-labels)

### 設計理念
- **極簡**:Trello labels 主打「視覺區分」,不是「強邏輯查詢」
- **進階 AND 邏輯**需要靠 Butler(自動化)或第三方整合(如 Unito sync 到其他工具)

### 真實評論
- Trello 用戶對「能不能用 AND/OR/NOT 邏輯 filter」的回饋:**官方不支援,用第三方** — 這是 Trello 設計哲學的反映(極簡 UI,不堆功能)
- 第三方整合(如 Unito)可把 Trello 同步到 Jira / Asana / ClickUp,**繞過** 原生邏輯限制

### 來源 URL 彙整
- 官方(Add a label):https://support.atlassian.com/trello/docs/adding-labels-to-cards
- Atlassian Community:https://community.atlassian.com/forums/Trello-questions/Can-i-filter-a-trello-board-with-all-labels-of-same-color-but/qaq-p/912262
- 第三方(Unito):https://unito.io/blog/unlimited-trello-labels
- 第三方(教學):https://www.iambacon.co.uk/blog/filtering-your-trello-board-with-labels

---

# 附錄:資料抓取方法與覆蓋率

## 抓取方法
- **搜尋引擎**:Tavily / Ollama web search 雙軌
- **搜尋關鍵字**:
  - 「Microsoft Teams announcement channel feature official documentation」
  - 「Slack announcement channels feature 2020 launch official docs」
  - 「Notion database filter AND OR logic how it works」
  - 「Gmail multiple labels filter AND OR NOT operators」
  - 「Jira JQL tutorial AND OR NOT operators query language」
  - 「Confluence space announcements blog feature documentation」
  - 「Viva Engage announcement feature community post pinned」
  - 「G2 / Reddit / Capterra 評比」
- **內容萃取**:`web_extract` 抓 5-8 個關鍵 URL 的核心段落 + 3 個 Reddit 討論串

## 覆蓋率
- ✅ **企業公告平台 5 個**:Microsoft Teams(深)、Slack(深)、Notion(中)、Confluence(中)、Viva Engage(中)
- ✅ **標籤邏輯 4 個**:Gmail(深)、Notion filters(深)、Jira JQL(深)、Trello(中)
- **每個標竿至少 1 個來源 URL**:達成(實際 5-10 個)
- **必抓官方文件、G2/Capterra 評比、Reddit 評論**:達成(針對 Microsoft Teams / Slack 有特別找 G2 與 Reddit 評比;Notion 與 Jira 主要用 Atlassian Community 與 Reddit r/jira / r/Notion 評論)

## 未涵蓋但提示
- **Facebook Workplace**:2022 起新客戶停止;2023 退役;2025-2026 進入 read-only 模式。**沒抓到足夠現代評比**,故不列入主標竿。
- **G2 / Capterra 直接連結**:Slack/Teams 整體評分有抓到,但**「Channel Announcements」子功能沒有獨立評分**;這是市場現況(子功能不會單獨評分),已如實標明。
- **Microsoft 365 內部 G2 評論**:Microsoft Q&A / Reddit 是更貼近企業 IT 真實抱怨的來源;G2 較偏整體滿意度。

---

DONE
