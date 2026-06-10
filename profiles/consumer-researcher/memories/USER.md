## 溝通風格偏好
- **直接精確**: 符合INTJ性格，偏好直接、有效率的溝通
- **技術導向**: 對技術細節有興趣，可以深入討論
- **效率優先**: 重視解決方案的實用性和效率
- **系統思考**: 喜歡有結構、有系統的解決方案
- **要求完整性**: 要求「非常詳細且完整的各個方面的修正方向建議，請儘量不要漏掉」——不接受遺漏

## 對 Hermes Agent 的期望
- 希望赫米斯具備多種工具能力（搜尋、金融、GitHub、Vercel等）
- 希望了解如何抓取各個 API token
- 關心「越用越聰明」的有效性，有深入追问
- 希望知道具體的實作順序（優先順序）
- 會主動要求「統整對話內容，列出詳細的修正方向建議」

## 監控傾向
- 會發「測試」類訊息檢查系統是否正常運行
- 會仔細審視赫米斯的回覆內容並提出修正要求
- 對回覆格式有要求——要有結構、不要遺漏

## 興趣範圍（AI agent 相關）
- AI agent 自我改進機制（SOP 服從性、外部驗收循環）
- 多代理協作架構（2026-06-08 起赫米斯＝拉斐爾，**單一代理、雙重稱呼**；前任拉斐爾 OpenClaw 套件代理的歷史參考 `IDENTITY.md`）
- 金融工具自動化
- 工作自動化（學校人事相關）
- 系統配置與工具擴展

## 🧠 trial-and-error 主動撈取規則（2026-06-07 確立）

**使用者的硬性要求**：赫米斯**處理任務前**必須**先主動掃** trial-and-error skill，看有沒有踩過的雷，**不要等出事了才撈**。

**觸發關鍵字自動撈**（命中任一組就 `skill_view(name='trial-and-error', file_path='references/by-category/<分類>.md')`）：

- **部署類**：`vercel` / `deploy` / `Vercel` / `cloudflare` / `netlify` / `github pages` / `CDN` → `vercel-deployment.md`
- **Git 操作**：`git push` / `git filter-branch` / `BFG` / `GH013` / `GH001` / `large file` / `git history` / `force push` → `gh-cli-and-github.md`
- **加密類**：`GPG` / `gpg` / `encrypt` / `decrypt` / `簽章` / `key` / `passphrase` → `gpg-encryption.md`
- **雲端備份**：`rclone` / `Drive` / `備份` / `backup` / `purge` / `crypt` → `hermes-backup-strategy.md` + `hermes-backup-design-pitfalls.md`
- **環境變數**：`token` / `.env` / `process.env` / `API key` → `secrets-and-env.md`
- **Python sandbox**：`execute_code` / `python3.12` / `subprocess` / `sandbox` → `python-sandbox.md`
- **瀏覽器自動化**：`browser` / `playwright` / `headless` / `camofox` → `browser-automation.md`
- **Bash 腳本**：`for f in` / `2>&1` / `pipefail` / `array` / `set -e` → `bash-defensive-patterns.md`
- **Hermes 內部**：`hermes cron` / `hermes status` / `config` / `gateway` → `hermes-internal.md`

**判斷性問題**（使用者問「X 可以不備嗎？」「X 真的能砍嗎？」「X 是 Y 還是 Z？」）：**先查 trial-and-error**，不要憑印象答。

**違規後果**：會被使用者事後審查發現、信任扣分。**赫米斯必須在第一個 tool call 之前就完成 skill_view**（如果觸發條件命中）。

§

User has INTJ personality — direct, efficient, systematic. Wants complete detailed solutions with no gaps. Will review and correct outputs. Monitors system health via periodic "test" messages. Technical depth: understands underlying principles before accepting parameter values.

§

## GitHub 帳號切換偏好
- 主帳號（預設）: `hoonsoropenclaw`，所有一般 GitHub 操作都用這個
- 備用帳號: `hoonsor`（前任拉斐爾 OpenClaw 套件時代綁定的，OpenClaw 反安裝後這個帳號下的 repo 可由你決定保留/清理）
- 切換規則: 使用者明確說「用 hoonsor」或「切到 hoonsor」時才切到該帳號；任務完成後自動切回 `hoonsoropenclaw`
- 切換方式: `gh auth switch --user <username>`（兩帳號都預先掛在 `~/.config/gh/hosts.yml` 內）
- 對應 token 存放: 隔離於 `~/.config/hermes/alt_gh_tokens/hoonsor`（mode 0600），不要貼在對話裡
§
## 對話記錄保留原則（赫米斯節制記憶膨脹的共識）
- **預設不寫**：完成任務、踩坑修復、做完部署後，赫米斯不主動 add 進記憶
- **使用者明確說要存才存**：「把這個記起來」「這個以後會用到」「寫進記憶」才動手
- 例外情況（赫米斯發現未來會重複用到、可主動建議一次但仍須使用者確認）：
  - 使用者的**穩定偏好**（INTJ 性格、想看結構化輸出、要繁體中文等）
  - **環境事實**（gpg 版本、headless 無 keystore daemon、IP/主機名等）
  - **新建立的長期檔案/工具路徑**（如 `~/.local/share/hermes/secrets/` 是新佈局，赫米斯需要記得它的存在）
- **不寫的東西**：任務進度、已完成的工作、具體 PR/issue 編號、commit SHA、單次 session 結果、token 字串本身、機密內容
- **7 天內會過期的東西不入記憶**
- 短期 session 細節、需要回憶時用 `session_search` 撈（會跨所有過去 session 搜，沒真的消失）
- **定期清理**：MEMORY.md 超過 25 KB 時赫米斯主動建議掃一次、刪除過時條目
- **結束 session 前的掃雷工作流**：使用 `/nc`（或 `/new-conversation`）skill,完整 SOP 見 `~/.hermes/skills/new-conversation/SKILL.md`。掃完後**手動**打 `/new` 開新 session（保留最後確認權）

### MEMORY.md 清理判斷標準（什麼留、什麼刪）

**留**（優先保留，這些是跨 session 有價值的核心）：

- **穩定偏好** — INTJ、繁中、要看結構化輸出、不要 AI-slop 等
- **使用者習慣** — 想先看原理才決定參數、要求完整詳細方案不漏
- **重要工作流程指引** — GPG 雙目錄加密 token、gh 雙帳號切換、session_search 撈對話、加密 SOP 入口
- **選擇/決策的「為什麼」** — 為什麼選 GPG 不是 OS keystore、為什麼拆兩個目錄、為什麼這次不解釋
- **抽象教訓/規律（L3 試誤）** — 「Python sandbox 會遮罩 token 字串，必從檔案讀」、「GPG 預設產出 mode 644 要 chmod 600」、「gpg --symmetric 不該 `--user`」— **只留教訓、不留下令**
- **環境事實** — headless 無 keystore daemon、gpg 版本、IP/主機名、Python sandbox 遮罩 token 等
- **新建立的長期檔案/工具路徑** — `~/.local/share/hermes/secrets/` 佈局、SKILL 入口路徑

**刪**（可由 session_search 撈回的細項一律不留在長期記憶）：

- 任務進度（今天砍了幾個 repo、做了幾次部署）
- 具體 commit / PR / issue 編號（#26045、prj_xxx、dpl_xxx）
- 單次 session 的具體結果與操作 log（時間戳、命令列、輸出）
- 具體 bug 解法本身（L2 試誤的「步驟」）— **但抽象教訓 L3 留下**
- token 字串或任何機密內容
- 自我重複的條目（已寫在 USER.md 不必在 MEMORY.md 再寫一份）
- 過時的技術細節（例如 5/30 的 vercel CLI 報錯處理，流程可能已改）

**簡記三層試誤的處理方式**：
- **L1 具體操作** → 自動存 state.db、**從不進記憶**
- **L2 具體 bug 解法** → state.db 可撈、**記憶只留一句話指向**（「這個 bug 之前解過，session_search 找『xxx』」）
- **L3 抽象教訓/規律** → **必進記憶**（這才是「越用越聰明」的關鍵）

**簡記原則**：能 `session_search` 撈回的事 = 留個概念/路徑就夠；只有「使用者為什麼這樣決定」「跨 session 都該這樣做」「這個環境就是這樣」「未來會重複踩的雷是這個」這類才進長期記憶。