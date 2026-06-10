# YouTube Data API v3 — OAuth 設定指南

> **適用場景**：需要讀取**自己**的 YouTube 訂閱頻道、播放清單、上傳紀錄、收藏影片等私人資料。
> **不適用**：只查**公開**資料（影片標題、頻道統計）— 改用 API key 就好，不需要走 OAuth。

---

## 1. 為什麼不能只靠 API key

YouTube Data API 對「**我的訂閱 / 我的播放清單 / 我的上傳**」一律需要 OAuth 授權，因為這些是**用戶私人資料**。API key 只能查公開 metadata（影片標題、頻道 ID 對應名稱等）。

---

## 2. 完整設定步驟（從零開始）

### 步驟 1：建立 / 選定 Google Cloud 專案

1. 開 https://console.cloud.google.com/projectselector2/home/dashboard
2. 「**+ 新增專案**」或選現有專案
3. 專案名稱（例如 `Raphael`）與 **專案 ID**（例如 `enki-489612`，**這是兩碼不同的事**，詳見下方 pitfall）是**自動產生**的，**專案 ID 唯一且不可改**

### 步驟 2：啟用 YouTube Data API v3

1. 開 https://console.cloud.google.com/apis/library
2. 搜尋「YouTube Data API v3」→ 點進去
3. 按「**啟用**」

### 步驟 3：設定 OAuth 同意畫面

1. 開 https://console.cloud.google.com/auth/audience
2. User type 選「**外部**」（Internal 限定 Workspace 帳號）
3. 填：
   - 應用程式名稱：`Raphael`（或任何名字）
   - 支援電子郵件：你的 Gmail
   - 開發人員聯絡資訊：你的 Gmail
4. 「**儲存並繼續**」→ 範圍頁直接「**儲存並繼續**」→ 測試使用者加入你的 Gmail → 「**儲存並繼續**」

### 步驟 4：建立 OAuth 用戶端 ID

1. 開 https://console.cloud.google.com/apis/credentials
2. 上面「**+ 建立憑證**」→ 「**OAuth 用戶端 ID**」
3. 應用程式類型：**電腦**（或「桌面應用程式」— 兩者等價）
4. 名稱：例如 `Raphael YouTube 2026`
5. **已授權的重新導向 URI**（**建立表單本身就有這欄**！不要漏填）：
   - 點「+ 新增 URI」
   - 填 `http://localhost:8765`（赫米斯 OAuth 腳本預設 port；如要改記得兩邊同步）
6. 按「**建立**」

> ⚠️ **新版 Google Cloud Console 陷阱（2025-2026+）**：「已授權的重新導向 URI」欄位**只在建立流程的表單裡**出現；建立完成後，**用戶端的「編輯」頁會把這欄位隱藏起來**（即使有「✏️ 編輯」按鈕，按進去也看不到）。如果想事後改 URI，標準做法是**刪掉重來**，不要花時間找編輯入口。
>
> 同樣道理，「已授權的重新導向 URI」**只對「網頁應用程式」應用程式類型顯示**，「電腦 / 桌面應用程式」類型**完全隱藏這欄**。對電腦類型來說這是 Google 原生設計 — 電腦類型用 loopback redirect，**不需要預先註冊** URI，Google 會接受任意 `http://localhost:port`。
>
> 如果你卡在「找不到 URI 欄位」：檢查你選的應用程式類型。電腦類型看不到是**正常的**。

### 步驟 5：下載用戶端 JSON

Google 會跳對話框顯示用戶端 ID / 密鑰。**重要**：
- 對話框上的「**⬇ 下載 JSON**」按鈕 — 按下去拿 `client_secret_XXX.json`
- 重新命名為 `youtube_client.json`
- 搬到赫米斯 secrets 目錄：
  ```bash
  mv ~/Downloads/client_secret_*.json ~/.local/share/hermes/secrets/youtube_client.json
  chmod 600 ~/.local/share/hermes/secrets/youtube_client.json
  ```

### 步驟 6：執行 OAuth 流程

赫米斯有現成的 OAuth 腳本：

```bash
python3 ~/.hermes/scripts/youtube_oauth.py
```

它會：
1. 啟動本地 HTTP server 監聽 `localhost:8765`
2. 開瀏覽器（如果你在 desktop 環境）跳出 Google 登入 + 授權畫面
3. 同意 scope（預設：`youtube.readonly` + `subscriptions.readonly`）
4. 收到 redirect 後自動存 token 到 `~/.hermes/youtube_tokens.json`

> **Telegram / 遠端環境**：腳本會印出授權 URL，讓你手動複製到**本機瀏覽器**開；授權完成後 redirect 失敗（因為沒有 port 8765 連回），**複製整條 redirect URL** 回傳給腳本。
>
> **更乾淨的做法（headless server 必讀）**：從本機建立 SSH tunnel，把 N100 的 port 8765 轉到本機：
> ```powershell
> # Windows PowerShell
> ssh -L 8765:localhost:8765 user@n100
> ```
> 然後在本機的瀏覽器打 `http://localhost:8765/` 開同意流程。Google 的 redirect URL 是 `http://localhost:8765` 寫死，所以**只需要本機的 Chrome 看得見** port 8765 就行（不用碰 N100 的防火牆）。OAuth 完成後 SSH tunnel 可以關掉。
>
> **絕對不要嘗試用 N100 跑 `lynx` 或 `w3m` 跑 OAuth** — Google 登入頁面太多 JavaScript，文字瀏覽器跑不動同意按鈕。

#### 步驟 6.1：Token 生命週期與 Refresh 行為

理解 token 何時過期能幫你 debug「昨天還能跑今天就壞了」這類問題。

| Token 類型 | 生命週期 | 觀察方式 |
|-----------|---------|---------|
| `access_token` | **1 小時**（3,600 秒）| `expires_in` 欄位值 |
| `refresh_token` | **預設 7 天**（604,800 秒）| `refresh_token_expires_in` 欄位值（Google 不一定會回）|
| 用戶端 `client_id` / `client_secret` | **永久**（除非手動刪除）| Google Cloud Console 用戶端設定頁 |

**關鍵行為**：
- `access_token` 過期 → 用 `refresh_token` 換新的（背景自動跑，無感）
- `refresh_token` 過期 → **必須重新走完整 OAuth flow**（使用者重按一次 Google 同意）
- **`client_id` 被刪** → 現有 token **立刻全部失效**，refresh 也會失敗（即使 refresh_token 還沒過期）

**赫米斯 OAuth 腳本**（`youtube_oauth.py`）的 refresh 邏輯：

```python
# 每次跑會自動：
if tokens and "refresh_token" in tokens:
    new = refresh_access_token(refresh_token, client_id, client_secret)
    if "access_token" in new:
        # ✅ refresh 成功，存新 access_token
        ...
    else:
        # ❌ refresh 失敗（client_id 被刪 / refresh_token 過期）
        # → 自動 fallthrough 重新走 OAuth flow
        tokens = None
```

> ⚠️ **陷阱**：`refresh_token` 在「使用者重新授權」時**會換新值**。如果你的腳本只在 access_token 過期時 refresh，**永遠拿不到新的 refresh_token** — 這是 Google 設計（避免 refresh_token 永久被竊用）。赫米斯腳本透過 `if "refresh_token" not in new` fallback 處理這個。

#### 步驟 6.2：常見 OAuth 錯誤與排查

| 錯誤訊息 | 根因 | 解法 |
|---------|------|------|
| `The OAuth client was deleted.` | **用戶端已被刪**，但 token 還在 | 在 Google Cloud Console **重新建立 OAuth 用戶端**，拿新的 client_id / client_secret，重跑 OAuth flow |
| `invalid_client` | client_id 或 client_secret 跟 Google 端不符 | 重新下載用戶端 JSON 比對，確認用對的用戶端 |
| `redirect_uri_mismatch` | OAuth flow 跳回的 URI 跟 Console 註冊的不同 | 對電腦類型 loopback 通常不會發生；網頁類型需確認 redirect URI 跟 Console 一致 |
| `Token has been expired or revoked.` | access_token 過期 **且** refresh_token 也失效 | 完整重走 OAuth flow |
| `403: access_denied` (使用者按拒絕) | 使用者拒絕授權 | 重新跑、再次嘗試 |
| `403: access_denied` (測試使用者未加入) | OAuth 同意畫面在「測試中」狀態，使用者 email 沒加入白名單 | 在 Console → 同意畫面 → 測試使用者 → 加入你的 Gmail |

**診斷指令**：

```bash
# 看現有 token 跟用戶端 JSON 對不對
jq -r '.installed.client_id' ~/.local/share/hermes/secrets/youtube_client.json
diff <(jq -S . ~/.local/share/hermes/secrets/youtube_client.json) \
     <(jq -S . ~/.hermes/youtube_tokens.json 2>/dev/null)  # 兩個檔比對
```

#### 步驟 6.3：3 種 OAuth flow 環境方案（trade-off 比較）

赫米斯 OAuth flow 需要**有瀏覽器**的環境跑 Google 同意畫面。N100 是 headless server，**必須從別處觸發**。

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| **A. SSH tunnel**（`ssh -L 8765:localhost:8765`）| 最簡單、Google 100% 接受、token 留 N100 | Windows 要有 SSH client | 預設推薦 |
| **B. noVNC + camofox 圖形瀏覽器**（N100 端有現成基礎設施）| 全部在 N100 完成、不依賴 Windows | 需先啟動 camofox 瀏覽器、要 SSH tunnel 看 noVNC 介面 | 你想完全在 N100 端處理 |
| **C. Windows 本機直接跑 OAuth** | 跟 Google 互動最友善 | 需 Windows 安 Python、token 要複製回 N100 | Windows 已裝 Python |

**方案 B 詳細步驟**（N100 已有 camofox + noVNC 服務在 port 6080）：

1. 確認 camofox 瀏覽器連上：`curl http://localhost:9377/health` 看 `browserConnected: true`
2. Windows SSH 開雙 tunnel：
   ```powershell
   ssh -L 6080:localhost:6080 -L 8765:localhost:8765 hoonsoropenclaw@100.88.38.80
   ```
3. Windows 瀏覽器打 `http://localhost:6080/vnc.html` → noVNC → Connect 到 `localhost:5900`（無密碼）→ 看到 N100 桌面
4. 在 N100 SSH session 跑 `python3 ~/.hermes/scripts/youtube_oauth.py` → 印出授權 URL
5. 在 noVNC 視窗的 Firefox 網址列貼上 URL → Google 同意 → callback 回 8765（tunnel 已接好）→ 完成

### 步驟 7：驗證 token

```bash
curl -s -H "Authorization: Bearer $(jq -r .access_token ~/.hermes/youtube_tokens.json)" \
  "https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=5" | jq '.items[].snippet.title'
```

應列出你的 5 個訂閱頻道名稱。

---

## 3. Scope 選擇指南

| 想做的事 | 必要 scope |
|---------|-----------|
| 看自己訂閱頻道 | `https://www.googleapis.com/auth/youtube.readonly` 或更窄的 `subscriptions.readonly` |
| 看自己喜歡的影片 | `youtube.readonly` |
| 看自己上傳 | `youtube.readonly` |
| 訂閱 / 退訂頻道 | `youtube.force-ssl`（寫入權限，需重新授權）|
| 上傳影片 | `youtube.upload`（最強權限）|

**最小權限原則**：能讀就好就別給寫入。

---

## 4. 程式碼範本（Python）

### 4a. 完整 OAuth 流程（用 google-auth-oauthlib）

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os, json, pathlib

SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
CLIENT_SECRET = pathlib.Path.home() / '.local/share/hermes/secrets/youtube_client.json'
TOKEN_FILE = pathlib.Path.home() / '.hermes/youtube_tokens.json'

def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=8765)
        TOKEN_FILE.write_text(creds.to_json())
    return creds
```

### 4b. 查「我的訂閱」

```python
from googleapiclient.discovery import build
creds = get_credentials()
youtube = build('youtube', 'v3', credentials=creds)

subs = youtube.subscriptions().list(
    part='snippet', mine=True, maxResults=50
).execute()

for s in subs['items']:
    print(s['snippet']['title'], '→', s['snippet']['resourceId']['channelId'])
```

### 4c. 查「每個訂閱頻道的最新影片」

```python
# 用 activities API（每個 channel 最近活動，含新上傳）
for s in subs['items']:
    ch_id = s['snippet']['resourceId']['channelId']
    acts = youtube.activities().list(
        part='snippet,contentDetails',
        channelId=ch_id, maxResults=3
    ).execute()
    for a in acts.get('items', []):
        if a['snippet']['type'] == 'upload':
            vid_id = a['contentDetails']['upload']['videoId']
            print(f"  [{s['snippet']['title']}] https://youtu.be/{vid_id}")
```

### 4d. 跨頻道「新影片」差比對

存「上次檢查時間」到 JSON，跟 `publishedAt` 比對：

```python
import json, time
from pathlib import Path

state_file = Path.home() / '.hermes/youtube_new_videos_state.json'
state = json.loads(state_file.read_text()) if state_file.exists() else {}
last_seen = state.get('last_check', '2000-01-01T00:00:00Z')

# 對每個 sub 查 activities, 過濾 publishedAt > last_seen
new_videos = []
for s in subs['items']:
    ch_id = s['snippet']['resourceId']['channelId']
    acts = youtube.activities().list(
        part='snippet,contentDetails',
        channelId=ch_id,
        publishedAfter=last_seen,  # 過濾關鍵
        maxResults=5
    ).execute()
    for a in acts.get('items', []):
        if a['snippet']['type'] == 'upload':
            new_videos.append({
                'channel': s['snippet']['title'],
                'video_id': a['contentDetails']['upload']['videoId'],
                'published': a['snippet']['publishedAt'],
                'title': a['snippet']['title']
            })

# 存新時間戳
from datetime import datetime, timezone
state['last_check'] = datetime.now(timezone.utc).isoformat()
state_file.write_text(json.dumps(state, indent=2))
```

---

## 5. 配額與速率限制

YouTube Data API 預設配額：**每天 10,000 單位**。

| 操作 | 單位消耗 |
|------|---------|
| `subscriptions.list` | 1 |
| `activities.list` | 1 |
| `videos.list` | 1 |
| `search.list` | **100** ⚠️ |

**不要**用 `search.list` 查「某頻道最新影片」— 會燒光配額。改用 `activities.list`（每個頻道 1 單位）。

如果你有 200 個訂閱：
- 每天檢查一次：200 單位
- 加上偶爾補抓最新資料：總計 300-500 單位
- **完全在免費額度內**

---

## 6. Cron job 包裝範本

```bash
# ~/.hermes/cron/youtube_daily_check.sh
#!/bin/bash
python3 ~/.hermes/scripts/youtube_new_videos.py \
  --since "yesterday 00:00" \
  --format telegram \
  --send-to "telegram:dm" \
  | tee ~/.hermes/logs/youtube_check.log
```

`youtube_new_videos.py` 腳本要自己寫（赫米斯有現成的 `youtube_oauth.py` 但只列頻道，不查新影片 — 需要擴充）。

---

## 7. 參考資源

- 官方 docs：https://developers.google.com/youtube/v3
- API Explorer（互動測試）：https://developers.google.com/youtube/v3/docs
- Quota 監控：https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas
- 參考實作：`~/.hermes/scripts/youtube_oauth.py`（2026-05-26 建立，含 OAuth flow + subscriptions 抓取）
