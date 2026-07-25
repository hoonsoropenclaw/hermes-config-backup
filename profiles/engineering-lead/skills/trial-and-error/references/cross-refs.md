# 跨分類關聯索引

> 這份檔案列出「一個症狀可能涉及多個分類」的交叉案例
> 用 [[分類#條目]] 格式連結到各 by-category 檔

## 「token 處理」相關交叉

| 症狀 / 場景 | 涉及分類 |
|---|---|
| Python 內送 token 進 gh API | [[python-sandbox#Python sandbox 把 token 遮罩成 *** 導致字串截斷]] + [[gh-cli-and-github#gh auth status 顯示 Failed 但 GH_TOKEN 環境變數仍可走 API]] + [[secrets-and-env#替代 token 加密佈局]] |
| gpg 加密 token 檔 | [[gpg-encryption#gpg 預設產出檔案 mode 是 0644,加密後必 chmod 0600]] + [[gpg-encryption#gpg 第一次跑會自動建 ~/.gnupg/pubring.kbx,是正常現象]] + [[secrets-and-env#替代 token 加密佈局]] |
| 加新 GitHub 帳號進 gh | [[gh-cli-and-github#gh CLI 對缺 read:org scope 的 token 會拒絕 auth login --with-token]] + [[secrets-and-env#GitHub PAT 加密儲存(SOP)]] |

## 「部署」相關交叉

| 症狀 / 場景 | 涉及分類 |
|---|---|
| 部署 Vercel 前想驗證 | [[vercel-deployment#Vercel 部署區分「新建專案」vs「更新現有」]] + [[browser-automation#Playwright headless 環境需要先 pip install playwright + playwright install chromium]] |
| Vercel 部署時 token 過期 | [[vercel-deployment#vercel CLI 報錯「token 無效」不等於 API token 無效]] + [[secrets-and-env#~/.hermes/.env 是 Vercel 等 token 的合法存放位置]] |
| 部署 SPA tab-based 站後用 headless browser 驗證 | [[vercel-deployment#innerHTML 注入的 HTML 內 <script> 不會被瀏覽器執行（最隱蔽的雷）]] + [[browser-automation#Playwright headless 環境需要先 pip install playwright + playwright install chromium]]（驗證流程必須從首頁 click tab,不能單獨打 tab 檔案） |

## 「Python 跑 CLI」相關交叉

| 症狀 / 場景 | 涉及分類 |
|---|---|
| Python 想跑 curl / sqlite3 / jq 等 CLI | [[python-sandbox#Python sandbox 內 sqlite3 / curl / jq 等 CLI 工具可能不在]] |
| Python 想呼叫 gh CLI | [[gh-cli-and-github#gh auth status 顯示 Failed 但 GH_TOKEN 環境變數仍可走 API]] + [[python-sandbox#Python sandbox 把 token 遮罩成 *** 導致字串截斷]] |

---

## 維護提醒

- 新增條目時,如果一個症狀跨多個分類,**在主要分類寫詳細條目,其他分類寫簡短連結**即可
- 條目數變多後,本檔案可能也要拆分(例如「token 處理」「部署」「CLI 工具」各自一個 cross-ref)
