# Worker-3: RBAC + 附件系統 標竿抓取

任務:多角色登入/RBAC + 檔案附件系統 — 標竿事實抓取
抓取日期:2026-06-11
Worker 身份:獨立 hermes session,只整理事實,不做分析/建議

---

## 任務 A:多角色登入 / 權限分離(RBAC 標竿)

### A-1. WordPress Roles and Capabilities [權限設計直接標竿]

**事實來源:**
- WordPress.org 官方文件:https://wordpress.org/documentation/article/roles-and-capabilities
- Pair Networks KB:https://www.pair.com/support/kb/wordpress-user-roles-and-capabilities
- WP Engine 部落格:https://wpengine.com/blog/wordpress-user-management

**核心角色設計:**
- WordPress 預設 6 個角色(原文:"WordPress has six pre-defined roles: Super Admin, Administrator, Editor, Author, Contributor and Subscriber")
- 1.Super Admin(僅 Multisite 多站台安裝才有) — 擁有全部能力(network management)
- 2.Administrator — 完整站台控制(可管理使用者、外掛、佈景主題、更新、站台選項)
- 3.Editor — 可管理「所有人的內容」(可寫、發布、編輯任何人的 post/page、可管理分類、tag、審核留言)
- 4.Author — 只能寫/編輯/發布/刪除「自己的」post、可上傳檔案
- 5.Contributor — 只能寫/編輯自己的 post、**不能發布**、**不能上傳檔案**
- 6.Subscriber — 只有 `read` 能力,只能管理自己的 profile

**程式化擴充能力(原文):**
```
add_cap()      // Assign a capability to a role
remove_cap()   // Remove a capability from a role
add_role()     // Create a new role
remove_role()  // Remove an existing role
```

**自訂角色實作社群方案 — User Role Editor 外掛(由 Vladimir Garagulya 開發):**
- 來源:https://wordpress.org/plugins/user-role-editor
- 統計:700,000+ active installs、4.5/5 stars、287 reviews、支援 27 種語言
- 核心功能:勾選 checkbox 新增/移除能力、從頭新增角色或複製現有角色、按使用者指派能力、單一使用者可同時擁有多個角色、Multisite 支援
- Pro 版額外:封鎖選定的後台選單項目、依角色限制 widget 顯示、Export/Import 角色設定、Network Admin 一次同步、shortcode `[user_role_editor role="editor"]content[/user_role_editor]` 依角色顯示內容

**對「內部公告系統」最有參考價值的功能:**
- 「Editor 可管理所有人的內容 / Author 只能管自己」這個分層 → 直接對應「公告發布者(可改別人的)vs 部門承辦(只能改自己的公告)」分層
- Contributor 「不能發布、要等 Editor/Admin 審核」 → 對應「公告需審核」流程(草稿 → 送審 → 公告管理員發布)
- Subscriber「只能讀」→ 對應「全體教職員/學生家長」角色,純唯讀公告
- `add_cap() / add_role()` 程式化 API → 學校未來可新增「教務主任」「總務主任」「家長會長」等自訂角色
- 「Author 可上傳檔 / Contributor 不能上傳」→ 對應「公告附件上傳權限」的精細切分

**真實評論 / 評比:**
- 「Simple and works nicely」(Pk Gibson, June 2025):"Very nice, lightest and most simple."
- 「Worked great for my site」(indivisible, April 2025):"Vast capabilities and is organized to make it easy to navigate. Very intuitive."
- 「Plugin works great!」(LambrosHatzini, Nov 2024):"I've tried two other plugins to no avail. This one works great!"
- 負評「Wont save capabilities for custom role」(jen000, April 2025):"We have wasted so much time and lost orders because of a known bug... I can see that others have reported this bug from at least 4 months ago."
- 負評「Didn't work on multisite」(shirax, March 2025):"On multisite, trying to give user permissions to install plugins."
- 來源:https://wordpress.org/plugins/user-role-editor(總評價 243 五星 / 10 四星 / 6 三星 / 4 二星 / 24 一星)

---

### A-2. Notion Workspaces [權限設計直接標竿]

**事實來源:**
- Notion 官方 Help Center:https://www.notion.com/help/add-members-admins-guests-and-groups
- Notion 官方:https://www.notion.com/help/guides/who-should-be-a-workspace-member-who-should-be-a-guest
- Uno Notion VIP:https://uno.notion.vip/user-types
- Thomas Frank Ultimate Guide:https://thomasjfrank.com/notion-sharing-permissions-the-ultimate-guide

**Workspace 層級角色(4 種 user types):**
- 1.Workspace Owner — 最高權限,可管理 workspace settings、可**刪除整個 workspace**、Enterprise plan 可批次管理所有 users/groups/teamspaces
- 2.Membership Admin(僅 Enterprise plan) — 協助管理 Members/Guests/Groups;大公司常見 C-level 主管擔任
- 3.Member — Team/Enterprise plan 的「完整參與者」
- 4.Guest — 最低權限;Free plan 限制 5 個 guests,Paid plan 無限

**Page 層級權限(6 個等級,從高到低):**
- Full Access — 編輯、分享、修改/移除他人權限、刪除
- Can Edit(僅 Paid plans) — 編輯和刪除 page;不能修改權限或分享
- Can Edit Content(僅 Paid plans,僅 Databases) — 可新增/編輯/刪除 page;**不能**新增/移除/編輯 properties、不能改 view 設定、不能建立 views
- Can Comment — 可對 page 及其內容加留言
- Can View — 唯讀
- No Access — 無存取(可透過 public Forms 提交)

**特殊設計:**
- 「Highest permission rule wins」(最高權限規則優先) — 同一人透過多個規則取得存取時,以權限最大的為準
- 「Sub-pages inherit permissions from their nearest parent by default」 — 子 page 預設繼承上層權限
- 「Temporary Member」 — 給 Notion Marketplace 顧問用,有時效(最長 1 年),不佔付費 seat
- Allowed Email Domains — 設定公司網域後,該網域使用者 onboarding 時可自動加入
- Guest Access Request(預設啟用,Enterprise 可關) — 外部人可主動請求存取 page,通知 page 建立者審核
- Page-level access rules(Business/Enterprise only) — 資料庫層級的細粒度權限,可用 person 或 created_by property 對應到「列層級」權限
- 「Can Create Pages」 toggle(2026-03 新功能) — No Access/Can View/Can Comment 的人也能新增 entry(不用給 full edit 權限)

**對「內部公告系統」最有參考價值的功能:**
- 6 層 page 權限(尤其 Can Edit Content)→ 對應「教務處可編輯教務公告、不能編輯總務公告」的精細分工
- Teamspace(子空間)設計 → 對應「各處室/科室」分區,各有自己的 owner
- 「最高權限規則優先」+「子 page 繼承」→ 預設安全(全站成員讀得到、只能自己編輯),例外的部分用子 page 覆蓋
- Temporary Member → 對應「實習老師/代課老師/短期訪客」這種時效性帳號
- Allowed Email Domain → 對應「@school.edu 自動加入、不用人工審核」
- Page-level access rules → 對應「公告的『可閱讀對象』」依部門/班級/角色設定

**真實評論 / Reddit/G2 評比:**
- Reddit r/Notion 「Users with Can Edit Content can edit everything?」:"I have a database I have shared with guests with permission level 'can edit content', however they still can edit views, delete views and add new, delete and [more]" — 代表 Can Edit Content 在 view 層級的權限邊界有混亂
- 來源:https://www.reddit.com/r/Notion/comments/1ddf0h1/users_with_can_edit_content_can_edit_everything
- Facebook Notion Business 社群:"I love the new Can Edit Content permission level, the problem is that it's not available on views." — view 層級權限問題
- 來源:https://www.facebook.com/groups/notionbusiness/posts/1277703499775570

---

### A-3. Slack Workspaces [權限設計直接標竿]

**事實來源:**
- Slack 官方 Types of roles:https://slack.com/help/articles/360018112273-Types-of-roles-in-Slack
- Slack 官方 Permissions by role:https://slack.com/help/articles/201314026-Permissions-by-role-in-Slack
- Slack 官方 Change a member's role:https://slack.com/help/articles/218124397-Change-a-members-role
- Slack 官方 Primary Owner:https://slack.com/help/articles/360038161033-Understand-the-Primary-Owner-role
- Haekka Blog:https://www.haekka.com/blog/what-are-slack-roles

**Workspace 層級角色:**
- 1.Primary Owner(workspace 或 Enterprise org 各 1 個) — 唯一可「刪除 workspace」或「轉移所有權」的人
- 2.Owner — 與 Primary Owner 相同權限,**除了**不能刪除/轉移 workspace
- 3.Admin — 由 Owner 建立;可管理 users(含 guest accounts)、可把 member 升為 admin、可封存 channel
- 4.Member — 預設大多員工在此;可使用大部分功能,**有限度**管理 members 或改 workspace settings;**注意**:預設可安裝 Slack App Directory apps
- 5.Guest — 兩種:Multi-Channel Guest(可加入多個 channel)、Single-Channel Guest(只能加入 1 個 channel)

**Enterprise Grid 額外 System Roles:**
- Channels Admin — channel 管理;可公開/私有互轉
- Compliance Admin — 法律保留(legal hold)管理
- Roles Admin — 編輯使用者角色
- Users Admin — 建立/刪除/停用使用者

**核心權限對照(節錄自官方文檔,部分):**
- Send messages and upload files — Owner/admin/Member/Guest 都有
- Join any public channel — Owner/admin/Member 有,Guest 無
- Create a channel — Owner/admin/Member 有(Workspace owner 可限制此權限),Guest 無
- Convert a channel to private — 僅 Owner/admin
- Archive a channel — Owner/admin/Member
- Delete a channel — 僅 Owner/admin
- Set channel retention — 需 Owner 開啟(✦)
- Invite guests to public channels — 僅 Owner/admin
- Invite single-channel guests to private channels — 僅 Owner/admin
- Delete other people's messages — 僅 Owner/admin
- Deactivate a member's account — 僅 Owner/admin
- Transfer primary ownership — **僅 Primary Owner**
- Delete workspace — **僅 Primary Owner**
- Create a custom role — **僅 Org primary owner** 或 **Roles admin**(僅 Enterprise)

**對「內部公告系統」最有參考價值的功能:**
- 「Guest 兩種(單/多 channel)」→ 對應「訪客只能看公告 vs 訪客可參與部分討論」的差別
- 「Primary Owner 唯一可刪/轉移」→ 對應「系統管理員」要明確單一,避免「所有人都能砍站」的風險
- 「Channel retention 設定」→ 對應「公告保存期限」(90 天後自動封存)
- 「Set posting permissions」→ 對應「誰能在某個公告板發文」,管理員可在 channel 設 post-only mode
- 「@channel / @here / @everyone」分層 → 對應「公告可標註哪些層級的人」
- 「System Roles 分工」(Channels/Compliance/Roles/Users)→ 對應大企業「校務系統管理員」「資安管理員」「帳號管理員」分權

**真實評論:**
- 來源:Haekka Blog 提到重點「Default Slack permissions grant members the ability to install Slack App Directory apps in a workspace」 — 代表預設 member 可裝第三方 app,常被企業 IT 視為資料外洩風險
- 「Be mindful of what channels and data invited guests can access. Sometimes guests do not have the same training or clearances as full-time employees.」 — 代表 guest 預設可能看到不該看的資料

---

## 任務 B:檔案附件 + 公告系統(附件標竿)

### B-1. Google Drive + Sharing [附件系統直接標竿]

**事實來源:**
- Pipeline Digital 教學:https://pipelinedigital.co.uk/blog/google-workspace-updates/mastering-google-drive-sharing-permissions
- University of Michigan ITS 文件:https://documentation.its.umich.edu/google-drive-sharing
- Google Support(virus scan):https://support.google.com/drive/thread/225474267/virus-scanning-files-in-google-drive-larger-than-100mb
- Google Support(preview limit):https://easyfilerenamer.com/blog/2022/05/18/file-is-too-large-to-preview-error-in-google-drive

**檔案/資料夾分享 — 4 種角色:**
- Viewer — 唯讀
- Commenter — 可加意見/建議
- Contributor — 可新增、編輯、分享,**但不能刪除**
- Editor — 完整控制(新增/編輯/刪除/分享)

**存取範圍 — 2 種模式:**
- Restricted(預設,最安全) — 連結只對被加入的人有效
- Anyone with the link — 拿到 URL 的人皆可存取(敏感文件不建議)

**Shared Drives(團隊雲端硬碟)— 5 種角色:**
- Manager — 可新增/移除成員、管理所有內容
- Content Manager — 可新增、編輯、移動、刪除檔案
- Contributor — 可新增/編輯檔案
- Commenter — 可加留言
- Viewer — 唯讀

**重要設計:**
- 「不能把個人 Google 帳號(如一般 Gmail)直接加為 Shared Drive 成員,但可分享 Shared Drive 內的特定 folder/file 給外部使用者」
- 即將推出改變:**Folder 設定將覆寫 file 設定**(原本可在 shared folder 內的單檔設限,未來由 folder 決定)

**病毒掃描 / 預覽限制(來自 Google 官方 + 使用者回報):**
- 病毒掃描:「Google Drive does not scan files larger than 100 MB for viruses. This is because scanning large files can take a long time」
- 超過 100MB 的檔案:不掃毒、下載時會跳「無法掃描病毒」警告
- 預覽限制:Google Docs 50MB、Google Sheets 100MB、其他類型依格式而異
- 使用者回報 20-100MB 之間的檔案可能隨機跳病毒掃描警告

**對「公告系統的附件需求」最有參考價值的功能:**
- 「Viewer / Commenter / Contributor / Editor」4 層 → 對應「公告附件誰能下載/誰能加意見/誰能改附件」的精細分層
- 「Restricted vs Anyone with the link」 → 對應「校內公告 vs 對外公開公告」的分享範圍
- 「Shared Drives」模型 → 對應「處室/科系共用的雲端硬碟,離職員工走了檔案還在」
- 「100MB 病毒掃描上限」 → 對應「公告附件最大限制」決策依據(超過要掃毒或跳警告)
- 「Folder 覆寫 file 設定」即將上路 → 對應「公告附件放在哪個 folder 就吃那個 folder 權限」是未來趨勢

---

### B-2. OneDrive for Business [附件系統直接標竿]

**事實來源:**
- Microsoft 官方 Share files:https://support.microsoft.com/en-us/office/share-files-and-folders-in-microsoft-onedrive-9fcc2f7d-de0c-4cec-93b0-a82024800c07
- Microsoft 官方 Manage sharing:https://support.microsoft.com/en-us/office/manage-sharing-and-permissions-in-onedrive-and-sharepoint-0a36470f-d7fe-40a0-bd74-0ac6c1e13323
- Microsoft Learn(version history):https://learn.microsoft.com/en-us/sharepoint/document-library-version-history-limits
- Microsoft Support(restrictions):https://support.microsoft.com/en-us/office/restrictions-and-limitations-in-onedrive-and-sharepoint-64883a5d-228e-48f5-b3d2-eb39e07630fa
- Orchestry(depth):https://www.orchestry.com/insight/sharepoint-onedrive-version-history

**分享選項 — 4 種存取範圍:**
- Anyone — 拿到連結的任何人(可能含組織外),可轉發
- People in <Your Organization> with the link — 組織內有連結的人
- People with existing access — 已有權限的人(不變更)
- Specific people — 只有你指定的人;被轉發的話只有原本有權限的人能用

**額外設定:**
- Allow editing(預設開) — 有 Microsoft 帳號的人可編輯
- Block download(僅 work/school 帳號,編輯關閉時可用) — 禁止下載檔案
- Set expiration date(僅 Microsoft 365) — 連結到期失效
- Allow editing 在 Word 文件可改成 **Can review**(僅留言/建議)

**重要警語(原文):**
> "Caution: When you share folders with Edit permissions, people you share with can add the shared folders to their own OneDrive and see all of the folder's contents."
> "Recipients can only add shared *folders* to their OneDrive, not individual *files*. If you want the recipient to only see certain files, put the files in a separate folder first, and then share that folder."

**版本歷史(Version History):**
- 「We can only set minimum file versioning to 100. By default, MS 365 wants you to keep 500 versions of each file. You cannot disable versioning」
- 預設:每檔 500 個版本
- 最小值:100 個版本
- **無法完全停用**版本歷史
- 對儲存配額的影響:每個 major version 在儲存配額上算一個**完整獨立副本**(不是增量)
- Microsoft 365 全域/SharePoint 管理員可設定 organization 層級上限;site admin 可對個別 site/library 覆寫

**限制(來自 Microsoft Support 官方):**
- 對 work/school 帳號:**無法一次分享多個檔案**(只能一次 share 一個)
- 短網址格式:`https://1drv.ms` (Twitter 友善)

**對「公告系統的附件需求」最有參考價值的功能:**
- 「Block download」 → 對應「校內公告附件只能線上預覽、不能下載」(保密性高的文件)
- 「Set expiration date」 → 對應「公告附件 30 天後自動失效」
- 「Can review」(Word 限定) → 對應「校稿階段只能加意見、不能直接改正式公告」
- 「Specific people」+ 連結綁定 email → 對應「公告附件指定給特定收件人、不能外流」
- 版本歷史預設 500 個 → 對應「公告附件修訂追蹤」,但要小心儲存配額爆掉
- 「Folder 共享時可被加到對方 OneDrive」 → 對應「公告附件 folder 共享給處室後,處室可同步到自己的 OneDrive 離線存取」
- 「無法關閉版本歷史」 → 設計選擇(可選擇預設保留幾版)

**真實評論:**
- 「We can only set minimum file versioning to 100. By default, MS 365 wants you to keep 500 versions of each file. You cannot disable versioning」 — 代表企業 IT 常抱怨「不能完全關掉版本歷史」會吃儲存配額
- 來源:https://sardhianto.medium.com/microsoft-onedrive-file-versioning-setting-4aa7567c48ba

---

### B-3. Notion File Attachments + File Blocks [附件系統直接標竿]

**事實來源:**
- Notion 官方:https://www.notion.com/help/images-files-and-media
- Notion API docs(檔案上傳):https://developers.notion.com/guides/data-apis/uploading-small-files
- Notion API docs(取回檔案):https://developers.notion.com/guides/data-apis/retrieving-files
- Files2Notion 部落格:https://www.files2notion.com/blog/notion-file-management
- Notion Mastery:https://notionmastery.com/pushing-notion-to-the-limits

**檔案大小限制(以方案分):**
- Free Plan:每檔 ≤ 5MB(所有檔案類型)
- Paid Plan:PDF 上限 20MB、Images (PNG/JPG) 上限 5MB
- 單一檔案最大:**5GB**(Paid Plan 才有)
- Free Plan 無「總儲存上限」,只有「單檔 5MB」限制
- Free Plan guest 限制 5 個(對外 collaborator 計數),Paid Plan 無限

**支援格式:**
- Images:HEIC, ICO, JPEG, JPG, PNG, TIF, TIFF, GIF, SVG, WEBP
- Documents:PDF
- Audio:MP3, WAV, OGG
- Video:MP4(可能因壓縮問題不支援,可改轉檔)

**媒體 block 類型(原文):**
- 🖼️ Image block — 從電腦上傳 / 用 URL embed / Unsplash 圖庫;可 resize、crop、mask、加 caption、alt text
- 📎 File block — 上傳或 embed link;可拖檔案到 page
- 🎥 Video block — embed(YouTube/Vimeo)或上傳;Notion 會自動轉成自家播放器
- 🎵 Audio block — embed 或上傳;會自動轉成自家播放器
- 🔖 Web Bookmark — 貼 URL 自動變書籤

**API 細節(來自開發者文件):**
- 上傳流程:Create File Upload object(取得 `id` 和 `upload_url`)→ send binary → attach to page/block/database property
- 取得下載連結:從 S3 取得臨時 URL,`expiry_time` 約 1 小時後過期
- 範例: `"url": "https://s3.us-west-2.amazonaws.com/secure.notion-static.com/..."`

**對「公告系統的附件需求」最有參考價值的功能:**
- 「File block 嵌入 page」 → 對應「公告內直接嵌附件,不用下載再開」
- 「5GB 單檔上限」 → 對應「公告附件大檔上限」的決策(可放影片/長 PDF)
- 「embed link 而非上傳」 → 對應「公告附件不一定要存在自家主機,可連結到外部雲端」
- 「Caption / Alt text」 → 對應「附件的替代文字(無障礙 + SEO)」
- 「Replace file」 → 對應「公告附件更新版本」功能
- 「Expiry time 1 小時」 → 對應「附件下載連結短期有效」(防外流)
- 「Free Plan 5MB 限制」 → 對應「學校可考慮用 Free Plan 撐輕量公告」
- 「Notion 自動轉成自家播放器」 → 對應「附件直接預覽、不用裝外掛」

**真實評論:**
- Notion Mastery「Pushing Notion to the Limits」:「If you have a Free plan subscription, you can only upload files up to 5MB in size. On any paid plan, the file upload size is listed as」— 免費版單檔 5MB 限制常被抱怨太小
- NotionAnswers 社群回答:「While there is a cap on each individual file that you upload on a Personal Plan (5 mb), there is no total limit of how many files you can upload.」— Free Plan 只有單檔限制、沒有總量限制,但有人警告「don't recommend archive massive amount of file in notion」
- 來源:https://notionanswers.com/51/is-there-a-file-limit-for-notion-free-users

---

## 抓取總結

**RBAC 標竿(任務 A):** 3 個完整抓取
- A-1 WordPress(6 角色 + 程式化擴充 + User Role Editor 外掛)
- A-2 Notion(4 user types + 6 page permission levels + Enterprise 細節)
- A-3 Slack(5 workspace roles + Enterprise System Roles)

**附件標竿(任務 B):** 3 個完整抓取
- B-1 Google Drive(4 分享角色 + 5 Shared Drive 角色 + 病毒掃描/預覽限制)
- B-2 OneDrive for Business(4 存取範圍 + 額外設定 + 版本歷史 + 限制)
- B-3 Notion File(以方案分的大小限制 + 5 種 block + API 流程)

**所有來源都附 URL** — 全部為官方文件(WordPress.org、Slack.com、Microsoft.com、Notion.com、Microsoft Learn、Notion 開發者文件)或可信第三方教學(Pair Networks KB、WP Engine、Thomas Frank、Pipeline Digital、Haekka、University of Michigan ITS、Orchestry、Files2Notion、Notion Mastery)。

**已涵蓋的真實評論來源:**
- WordPress.org plugin 評論(287 reviews、4.5/5)
- Reddit r/Notion 權限問題討論
- Facebook Notion Business 社群 view 權限問題
- NotionAnswers 社群 Free Plan 限制討論
- Medium 企業 IT 對 OneDrive 版本歷史抱怨

抓取完成。
