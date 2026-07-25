# Secrets / .env / 憑證管理相關踩雷

> 觸發:任何 .env 編輯、token 儲存、加密 vs 明碼的取捨、憑證管理佈局
> 建立時間: 2026-06-05
> 條目數: 3

---

### 替代 token 加密佈局(GPG + 雙目錄分離)
**發現時間**: 2026-06-05
**觸發情境**: 任何備用 token(GitHub PAT、Vercel token 等非主帳號的 secrets)需要本機保存時
**症狀**: 想找一個「比明碼好、但又不需要 OS keystore / 硬體金鑰」的方案
**根因**: 沒有單一方案同時滿足「安全 + 便利 + headless 可用」
**解法**: GPG 對稱加密 + 雙目錄分離佈局
```
~/.config/hermes/alt_<service>_tokens/<account>.gpg     # 加密檔 (mode 600)
~/.local/share/hermes/secrets/.<account>_passphrase      # passphrase (mode 600)
```
兩個檔案分散在兩個目錄樹,自動化掃描工具要同時撈到兩個的機率低
**完整 SOP**: 見 skill `alt-token-secrets-layout`
**預防**: 所有替代 token 統一走這個佈局,不另開新格式
**相關條期**: [[gpg-encryption#gpg 預設產出檔案 mode 是 0644,加密後必 chmod 0600]] + [[python-sandbox#Python sandbox 把 token 遮罩成 *** 導致字串截斷]]

---

### ~/.hermes/.env 是 Vercel 等 token 的合法存放位置
**發現時間**: 2026-05-30
**觸發情境**: 找 Vercel API token 從哪來
**症狀**: 不知道 vercel token 放哪、`vercel whoami` 報 No credentials
**根因**: Vercel token 在 `~/.hermes/.env` 內以 `VERCEL_API_TOKEN=vcp_xxx` 形式儲存,**`vercel` CLI 看不到**它
**解法**: 讀取方式:
```bash
. ~/.hermes/.env
echo $VERCEL_API_TOKEN
# 或
grep VERCEL_API_TOKEN ~/.hermes/.env
```
Python:
```python
import os
from pathlib import Path
for line in Path("~/.hermes/.env").read_text().splitlines():
    if line.startswith("VERCEL_API_TOKEN="):
        token = line.split("=", 1)[1].strip()
        break
```
**預防**: 赫米斯內部任何 token 引用都從 `~/.hermes/.env` 讀,不要 hardcode
**相關條目**: [[vercel-deployment#vercel CLI 報錯「token 無效」不等於 API token 無效]]

---

### GitHub PAT 加密儲存(SOP)
**發現時間**: 2026-06-05
**觸發情境**: 主帳號以外的 GitHub 帳號的 PAT 需要保存
**症狀**: 想用 gh CLI 存 token 但缺 read:org scope 失敗
**根因**: 詳見 [[gh-cli-and-github#gh CLI 對缺 read:org scope 的 token 會拒絕 auth login --with-token]]
**解法**: GPG 加密 + 雙目錄分離,完整 SOP 見 `alt-token-secrets-layout`
**預防**: 主帳號 token 在 gh CLI hosts.yml,備用帳號 token 走 GPG 加密佈局
**相關條目**: [[gh-cli-and-github#gh CLI 對缺 read:org scope 的 token 會拒絕 auth login --with-token]] + [[gpg-encryption#gpg 預設產出檔案 mode 是 0644,加密後必 chmod 0600]]


---

## 額外條目（2026-06-06 從 MEMORY.md 移入）

### 環境工具狀態盤點（gpg / openssl / shred / keystore）
**環境事實**（2026-06-05 確認）:
- gpg 2.4.4、openssl 3.0.13、shred 都有
- python secretstorage 3.5.0、keyring 已安裝
- **headless 環境無 OS keystore daemon 在跑**（gnome-keyring、kwalletd 都未啟動）
**決策**: 走 GPG 雙目錄加密佈局,不走 OS keystore

### Python sandbox 會遮罩 token 字串值
**症狀**: 寫在 Python 程式碼字串裡的 `ghp_xxx` / `vcp_xxx` / `sk-xxx` token 自動被遮罩成 `***`
**根因**: Hermes Python sandbox 有 token 遮罩機制
**解法**: 從檔案讀取 token,或用 `headers={"Authorization": "Bearer " + token}` 串接（不要寫字面值）
**預防**: 寫 Python 程式碼時,token 一律從檔案讀,不在 source code 內放明文

---

### 備份腳本 secret 掃描設計
**發現時間**: 2026-06-06
**觸發情境**: 實作 `backup_hermes.sh` 時，發現 trial-and-error 文件內含 `DEEPSEEK_API_KEY=` 變數名提及被舊版 regex 誤判為真實 credential
**症狀**: secret scanner 阻擋備份，顯示 `SECRET HIT: execution-sop.md (matches DEEPSEEK_API_KEY=...)` 但檔案內只是變數名解釋文字，無實際值
**根因**: 
1. 舊版 regex `DEEPSEEK_API_KEY=.*[^ "]'` 會匹配任何 `DEEPSEEK_API_KEY=` 後面的內容，包括文字解釋
2. 文件中常有「設定 `DEEPSEEK_API_KEY` 環境變數」這類描述，會被誤判
**解法**: 改用只抓真實 credential format 的 regex：
- `ghp_[A-Za-z0-9]{36}` — GitHub token
- `gho_[A-Za-z0-9]{36}` — GitHub OAuth
- `glpat-[A-Za-z0-9_-]{20,}` — GitLab PAT
- `vcp_[A-Za-z0-9]{20,}` — Vercel token
- `sk-[A-Za-z0-9]{40,}` — OpenAI key
- `hms_[A-Za-z0-9_]{20,}` — Hermes custom tokens
- 不再對 `*_API_KEY=` 做泛化匹配，只對已知 prefix 做精確格式匹配
**預防**: 
- 設計 secret scanner 時，優先用格式匹配（prefix + 長度）而非 key name 匹配
- 文件中的變數名提及（如「請設定 MINIMAX_API_KEY」）不應觸發攔截
- 測試時用實際檔案驗證（包括內含變數名提及的檔案）
**If→Then**: **If** 你要設計一個 secret scanner  **Then** 用 credential format（prefix+長度）匹配，不要用 key name + value 的泛化 regex

---

### subprocess 不繼承 ~/.bashrc 設定的 env var（hermes 環境）
**發現時間**: 2026-06-07
**觸發情境**: execute_code 或 terminal 跑 cron script 時，`os.environ['VERCEL_API_TOKEN']` 是 `None`，但 `~/.hermes/.env` 明明有值
**症狀**: 
- `~/.hermes/.env` 有 `VERCEL_API_TOKEN=vcp_xxx`
- `os.environ` 沒有這個 key
- subprocess 預設也不繼承它（即使 `shell=True`）
**根因**: 
1. `~/.bashrc` 設定只在**登入互動式 shell** 生效
2. Hermes 的 `execute_code` / `subagent` 是 Python subprocess，不走 bashrc
3. `subprocess.run()` 的 `env=` 參數預設是**替換**（replace）而非**合併**（merge）——不傳就完全沒有
**解法**:
```python
import os
from pathlib import Path

# 從 ~/.hermes/.env 讀取 token
def get_token(key="VERCEL_API_TOKEN"):
    for line in Path("~/.hermes/.env").expanduser().read_text().splitlines():
        if line.startswith(f"{key}=") and not line.startswith(f"{key}=***"):
            return line.split("=", 1)[1].strip()
    return None

token = get_token()
if token:
    # 正確：env= 合併 os.environ + 自訂 token
    result = subprocess.run(
        ['curl', '-s', '-H', f'Authorization: Bearer {token}', 'https://api.vercel.com/v9/projects'],
        capture_output=True, text=True,
        env={**os.environ, 'VERCEL_API_TOKEN': token}
    )
```
**預防**: 
- 赫米斯所有 cron script / execute_code / terminal 若需 API token，必須從 `~/.hermes/.env` 讀取再用 `env={**os.environ, 'KEY': value}` 傳遞
- 不要假設 token 已在 `os.environ`（在 hermes 環境這**從來都不成立**）
- `vercel CLI` 無法自動讀 `~/.hermes/.env`，要用 `source` 後再執行，或直接從檔案讀取並透過 env 傳給 CLI
**If→Then**: **If** 你在 execute_code/terminal/subagent 裡需要用到 API token  **Then** 從 `~/.hermes/.env` 讀取並透過 `env={**os.environ, 'TOKEN': value}` 傳給 subprocess
**相關條目**: [[hermes-internal#hermes cron edit --script 對 no_agent jobs 的 Bug]] + [[python-sandbox#Python sandbox 會遮罩 token 字串值]]

### OAuth Device Code Flow 對 installed/電腦 client 類型不支援（2026-06-07 新增）
**發現時間**: 2026-06-07
**觸發情境**: 在 N100 headless 環境跑 YouTube OAuth，嘗試用 Device Code Flow（`https://oauth2.googleapis.com/device/code`）拿 user_code 想避免本地開瀏覽器
**症狀**:
- Client type = "Desktop app / installed"（已驗證 JSON 有 `"installed": {...}`）
- POST 到 `https://oauth2.googleapis.com/device/code` 帶 client_id + scope
- 回 **HTTP 401 Unauthorized**，body 沒具體 error message
**根因**:
- **Google OAuth 2.0 Device Authorization Grant 只支援這些 client 類型**：
  - ✅ `TV and limited-input devices`
  - ✅ `iOS` / `Android`
  - ❌ **`Desktop app / installed`（電腦應用程式）** — 回 401
- 原因是 Desktop client 的設計假設是有瀏覽器的環境，所以只給 `redirect_uri` flow
- 「installed」/「電腦」類型**只能走 redirect URI flow**（localhost:PORT 接 callback）
**解法**:
- 走原本的 localhost redirect URI flow（你已建好 client 有 `redirect_uris: ['http://localhost']`）
- 但 N100 headless 沒瀏覽器需要：SSH tunnel + Windows Chrome 跑 OAuth，或 VNC + camofox 視覺
- **或** 刪掉現有 client，**重建一個「TV and limited-input devices」類型**，才能用 Device Code Flow
- 重建後赫米斯只需：拿 user_code + verification URL → 你 Windows 開 Chrome 輸入 → 自動 callback 收 token
- Device Code Flow 赫米斯腳本範例見 `~/.hermes/scripts/youtube_oauth_device.py`（已寫好，等 TV client）
**預防**:
- 在 Google Cloud Console 建 OAuth client 之前，**先想清楚 headless 環境限制**：
  - N100/headless server → **優先選 TV / limited-input device**（可用 Device Code Flow，使用者只要輸入一組代碼）
  - 一般桌面用 → 才選 Desktop app
- 已經建了 Desktop app client 才發現要 headless 跑：**不要嘗試 hack**（改 scope、改 grant_type 都沒用），直接重建 client
- OAuth 選 client type 時，**把 "headless 跑得起來嗎" 當作第一個決策標準**
**If→Then**:
- **If** 你要在 N100/headless server 跑 OAuth 且 client 已經是 Desktop app  **Then** 重建 client 為 TV / limited-input 類型，**不要**浪費時間在 Desktop app 上找 hack
- **If** 已經跑了 Device Code endpoint 拿 401  **Then** 確認 client 類型（讀 `youtube_client.json` 看 `"installed"` 還是 `"web"` / `"tv"`），不是 client_id 錯也不是 scope 錯
- **If** 拿到 Device Code 成功（200 response + user_code）**Then** 使用者**只需要**在**自己**的瀏覽器打 `https://www.google.com/device` + 輸入 user_code + 選帳號 + 按允許，赫米斯**自動**輪詢收 token
**相關條目**: [[secrets-and-env#OAuth client 被刪除 → refresh_token 立刻失效]] + [[browser-automation#noVNC 黑畫面 = 沒按 Connect]]

---

### OAuth client 被刪除 → refresh_token 立刻失效，「The OAuth client was deleted」錯誤（2026-06-07 新增）
**發現時間**: 2026-06-07
**觸發情境**: 嘗試用 `~/.openclaw/workspace/youtube_tokens.json` 內的 refresh_token 換 access_token，準備 reuse 之前的 YouTube OAuth 流程
**症狀**:
- 讀取 token JSON 看起來正常（有 access_token, refresh_token, scope, expires_in）
- 對 `https://oauth2.googleapis.com/token` POST refresh request
- 回 HTTP 401，body: `{"error": "invalid_client", "error_description": "The OAuth client was deleted."}`
**根因**:
- OAuth 2.0 的安全模型：refresh_token 綁定 client_id（client_secret hash）
- 在 Google Cloud Console 刪除 OAuth 用戶端（或整個 GCP 專案被刪/移轉）後，server 端把這個 client_id 標記為 revoked
- **所有對應的 refresh_token 立刻失效**，連 access_token 也會在到期前 401
- 跟「access token 過期」是不同層級的錯誤（access 過期是正常 refresh，client deleted 是**永久**死掉）
- 唯一解法是**重新走一次 OAuth flow 拿新 client 的新 token**
**解法**:
```python
# 診斷：先試 refresh 一次，根據錯誤訊息判斷
import requests
r = requests.post('https://oauth2.googleapis.com/token', data={
    'refresh_token': tokens['refresh_token'],
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'grant_type': 'refresh_token',
})
if r.status_code == 401:
    err = r.json().get('error_description', r.json().get('error'))
    if 'client was deleted' in err or 'invalid_client' in err:
        # OAuth client 死了，必須重跑 OAuth flow
        print("✗ OAuth client 已被刪除，需重新授權")
        # 走完整的 InstalledAppFlow 或自寫 HTTP server flow
    elif 'invalid_grant' in err:
        # refresh_token 自己過期或被 revoke
        print("✗ refresh_token 過期，需重新授權")
```
**預防**:
- 赫米斯所有 OAuth client 的 client_id / client_secret **統一從 `~/.local/share/hermes/secrets/` 讀**，不要 hardcode 在 `~/.hermes/scripts/youtube_oauth.py` 等腳本
- 刪除 Google Cloud 專案前先 grep 所有 token JSON 檔，看哪些 token 綁這個專案
---
**If→Then**:
- **If** 你嘗試 refresh OAuth token 拿到 401 + "The OAuth client was deleted"  **Then** 立刻停止繼續修，**重新走 OAuth flow** 拿新 client（可能是新建立的 client_id）的新 token，現有 token 已經**無法修復**
**相關條目**: [[secrets-and-env#替代 token 加密佈局(GPG + 雙目錄分離)]] + 本 skill 的「subprocess 不繼承 ~/.bashrc 設定的 env var」

---

### Device Code Flow: youtube.force-ssl / subscriptions.readonly scope 不合法（2026-06-07）
**發現時間**: 2026-06-07
**觸發情境**: N100 headless 跑 YouTube OAuth，用 Device Code Flow + 想拿「讀取訂閱」權限
**症狀**:
- POST 到 `https://oauth2.googleapis.com/device/code` 帶 `scope=https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl`
- 回 HTTP 400 `{"error": "invalid_scope", "error_description": "Invalid device flow scope: https://www.googleapis.com/auth/youtube.force-ssl"}`
- 改用 `subscriptions.readonly` 一樣 HTTP 400 `invalid_scope`
- 只有 `youtube.readonly` + `openid` + `email` + `profile` 對 Device Code Flow 合法
**根因**:
- Google OAuth 2.0 Device Code Flow **對 scope 有限制**：
  - ✅ `youtube.readonly`、`openid`、`email`、`profile`、其他基本 scope
  - ❌ `youtube.force-ssl`（需要 HTTPS only environment，Device Flow 不支援）
  - ❌ `subscriptions.readonly`（雖然文件說這是 YouTube API scope，但 Device Flow endpoint 不接受）
- 注意：**`subscriptions.readonly` 用 web app / desktop app 走 redirect URI flow 是合法的**（這是 YouTube API v3 的官方 scope），**只在 Device Code Flow 不行**
- 結論：**Device Code Flow 不能拿「訂閱讀取權限」** — 但 `youtube.readonly` **本身** 就能調用 `subscriptions.list` API（Google 允許 read-only scope 讀取訂閱資料）
**解法**:
- Device Code Flow **只申請** `youtube.readonly` 就夠
- 之後用這個 access_token 調 `subscriptions.list` API 拿訂閱清單（**不需要 `subscriptions.readonly` scope**）
```python
# 驗證 scope 可行性測試
for scope in ['youtube.readonly', 'youtube.force-ssl', 'subscriptions.readonly', 'openid']:
    r = requests.post('https://oauth2.googleapis.com/device/code', data={
        'client_id': CLIENT_ID, 'scope': scope,
    })
    print(f"{scope}: {r.status_code}")  # 看到哪些 200 哪些 400
```
**預防**:
- 寫 OAuth script 時**先一個個 scope 測**，**不要一開始就用 list 全部試**
- Device Code Flow 寫死只支援 4 個 scope：**youtube.readonly / openid / email / profile**
- 想拿 subscriptions 權限 → 用 `youtube.readonly` 就好，**subscriptions.readonly 在 Device Flow 純粹不存在**
**If→Then**:
- **If** Device Code endpoint 回 400 `invalid_scope`  **Then** 把 scope 縮成單一 `youtube.readonly` 重試，**不要**懷疑 client_type 或 client_id
- **If** 想用 Device Code Flow 讀取 YouTube 訂閱  **Then** 申請 `youtube.readonly` 就夠，**不要**想用 `subscriptions.readonly`（會被 Google 擋）
**相關條目**: 本 skill 的「OAuth Device Code Flow 對 installed/電腦 client 類型不支援」

---

### Device Code polling slow_down 不是錯：應該暫停 5 秒繼續，不該 break 出去（2026-06-07）
**發現時間**: 2026-06-07
**觸發情境**: 寫 Python script 輪詢 Google OAuth Device Code token endpoint，等使用者輸入 user_code
**症狀**:
- 每 5 秒 POST 一次 `/token` 拿 access_token
- 過 60-100 秒後 Google 回 HTTP 403 `{"error": "slow_down", "error_description": "Forbidden"}`
- Script 收到 `slow_down` 後** break 出去**或 raise exception → 等超時失敗，**但使用者其實還在輸代碼**
**根因**:
- `slow_down` 是 Google 的**速率限制保護**：當 polling **看起來太頻繁**（即使每 5 秒）時，Google 要求 client **放慢**
- 這**不是錯誤**，是「Google 要我慢一點」的訊號
- Google 的預期行為：`slow_down` → client 把 polling 間隔加 5 秒 → 繼續輪詢
- 我原本的 script 邏輯：
  ```python
  if err in ('authorization_pending', 'slow_down'):  # ✅ 正確
      continue
  else:
      log(f"❌ {err}")
      break  # ❌ 不該 break，但有些版本寫成這樣
  ```
- 或更糟的版本（先 raise_for_status 再判斷）：
  ```python
  resp.raise_for_status()  # ❌ HTTP 403 會 raise HTTPError 直接 crash
  ```
**解法**:
```python
elif resp.status_code in (400, 403, 428):
    err = resp.json().get('error', '')
    if err == 'authorization_pending':
        continue
    elif err == 'slow_down':
        interval += 5  # ← 關鍵：放慢
        log(f"   ⏸️  slow_down - 間隔改成 {interval} 秒")
        continue  # ← 關鍵：繼續 loop
    elif err == 'access_denied':
        break  # 這才是錯誤
    else:
        break  # 其他未知錯誤
```
**預防**:
- **不要用 `raise_for_status()` 在 polling loop**（400/403/428 都是「正常等待狀態」不是錯）
- `slow_down` **永遠 continue**，把 `interval += 5` 然後繼續
- polling 起始 `interval` 設 **5 秒**（不要更快，Google 會 rate limit）
- script 預設 `expires_in=1800` 給 30 分鐘緩衝，slow_down 加 5 秒不影響大局
**If→Then**:
- **If** Device Code polling 收到 `slow_down`  **Then** interval += 5 + continue，**不要** break 或 raise
- **If** 寫 OAuth polling script  **Then** 把 `authorization_pending` + `slow_down` + `access_denied` 三個 error code 當 first-class state，不要混在 HTTP error 處理
**相關條目**: 本 skill 的「OAuth Device Code Flow 對 installed/電腦 client 類型不支援」

---

### 重新拿 device_code 會讓舊 user_code 立刻作廢（Google 端機制）（2026-06-07）
**發現時間**: 2026-06-07
**觸發情境**: N100 headless 跑 YouTube OAuth，赫米斯 polling 失敗後「重跑 device code」想換一個 user_code
**症狀**:
- 第 1 輪：拿 user_code `TGX-PQW-CWN` → 使用者輸入 → 等到 401 / slow_down → 赫米斯判斷失敗
- 第 2 輪：赫米斯「重新拿 device code」→ 拿到 `XSQ-TQG-DPDJ`
- **但使用者**這時**還在用 `TGX-PQW-CWN`**（不知道已作廢） → Google 顯示「驗證碼不正確，請再試一次」
- 結果：**兩輪都失敗**，浪費使用者 5 分鐘
**根因**:
- Google OAuth 2.0 Device Code Flow 設計：每個 client 同時間**只允許一個 active device_code**
- **赫米斯重新 POST `/device/code` 會讓前一個 device_code 立即失效**
- 使用者輸入舊代碼時 Google 回 `invalid_grant` 或 `400 Bad Request` → 顯示「驗證碼不正確」
- 這跟 access_token 過期 / refresh_token 過期是**完全不同的錯誤層級**
- 設計原因：Google 防止 device code 長期懸置被竊用
**解法**:
- **不要重新拿 device_code 來「再試一次」** — 舊的 user_code 已經死了，再拿新的只會讓使用者更混亂
- 一旦決定重新拿 device_code → **立刻、明確**告訴使用者：
  ```
  之前的 user_code TGX-PQW-CWN 已作廢
  新的 user_code XSQ-TQG-DPDJ（30 分鐘有效）
  請在 Windows Chrome 重新輸入新代碼
  ```
- 如果使用者已經輸入了舊代碼但沒看到成功訊息 → **讓他繼續輸也無用**，必須改用新代碼
- **更好的做法**：一開始就**確認拿到的是有效代碼**（HTTP 200 response 內含 user_code 才是真的有效）
**預防**:
- 赫米斯在 OAuth session 中**只發一次 user_code 給使用者**
- 重跑 device_code 是「放棄前一個流程」的意思，**必須把舊的明確標示作廢**
- background script 寫到 file log 而非 stdout（避免 Hermes background tool 的 output buffer 問題，使用者看不到「最新」的 user_code）
- 顯示 user_code 時**大字、明顯**標示「**唯一有效**」
**If→Then**:
- **If** OAuth Device Code polling 失敗想重跑  **Then** 先 kill 舊 background process → 拿新 device_code → **明確告訴使用者「舊代碼作廢」** → 不要假設他會自動知道
- **If** 使用者報告「Google 說驗證碼不正確」 **Then** 90% 是用了舊的 user_code，問他用了哪個 → 對照赫米斯 log 給新代碼
- **If** 赫米斯 background script 跑了多輪 device_code  **Then** file log 內只有**最後一輪**的 user_code 有效，前面的都死了
**相關條目**: 本 skill 的「OAuth Device Code Flow 對 installed/電腦 client 類型不支援」 + 本 skill 的「Device Code polling slow_down 不是錯」

---

### YouTube 影片內容赫米斯看不到：只有 RSS metadata（2026-06-07）
**發現時間**: 2026-06-07
**觸發情境**: 使用者要求「看 YouTube 影片內容 → 寫 Obsidian 詳細筆記 → 轉 podcast / 心智圖 / 測驗」
**症狀**:
- 赫米斯能抓 YouTube 公開 RSS feed（標題、發布時間、影片連結、頻道、縮圖）— 24 支影片全抓到
- 但**完全沒辦法拿到影片本身**：
  - ❌ 沒有影片字幕（赫米斯沒有 YouTube Data API v3 的 captions.download 權限 + 需要 OAuth 登入 + 自動字幕只能用影片擁有者下載）
  - ❌ 沒辦法看影片（headless 環境、播放需要瀏覽器 + cookies + 高頻寬）
  - ❌ 沒辦法下載 mp4 再餵給 LLM（容量太大、轉錄太慢）
  - ❌ auto-generated captions（CC）**用 yt-dlp 可以抓**，但**赫米斯目前還沒裝 yt-dlp + 沒試過**
- 「NotebookLM 轉 podcast / 心智圖 / 測驗」 — NotebookLM 本身**有**這些功能，**但 NotebookLM MCP server 沒在 Hermes 跑**、**NotebookLM 沒登入 cookies**、**赫米斯能觸發的 API 不包含 podcast 產生**（podcast 產生是 NotebookLM 的 UI 功能）
**根因**:
- **YouTube 內容層級**：metadata (RSS) → thumbnails → captions (auto-gen) → 影片本身
- 赫米斯能拿到的最遠是 **metadata**（RSS feed）— 這層不需要任何 token
- 進到 **captions 層**需要：`yt-dlp` 工具、或 YouTube Data API v3 的 `captions.download`（**需要 OAuth 認證 + video owner 授權**，個人用戶拿不到別人影片的字幕）
- 進到 **影片本身**需要：headful 瀏覽器 + 已登入 YouTube 的 cookies + 影片播放（**赫米斯 N100 headless 跑不起來**）
- **NotebookLM 的 podcast/心智圖/測驗是 UI 功能**，**沒有對應的 API endpoint**（NotebookLM API 還在 beta、不包含生成 podcast）
**解法**:
- **現實可做到**（**不需要新工具**）：
  - 從 RSS 拿 metadata → 寫 Obsidian 筆記（**明確標示「無內容、只有標題」**）
  - 從 RSS 標題做**簡單主題分類**（心智圖、tag）
  - 把筆記融進 RAG（讓查詢時能找到影片標題 + 連結）
  - 寫「影片筆記範本」讓使用者**自己看完影片後填筆記**
- **需要新工具**：
  - `yt-dlp` 安裝（`pip install yt-dlp` 或 `apt install yt-dlp`）→ 抓 auto-generated 字幕
  - 用 `yt-dlp --write-auto-subs --skip-download --sub-format vtt` 拿 SRT/VTT
  - 餵給本地 LLM 做摘要
- **NotebookLM podcast**：赫米斯只能「協助使用者登入 NotebookLM + 幫使用者把筆記放進去」，**赫米斯不能自動化 podcast 產生**（NotebookLM UI 按鈕觸發、不是 API 觸發）
- **備案**：用 `text_to_speech` (MiniMax/edge TTS) 工具把筆記**直接轉成語音**（雖然不是 NotebookLM 風格，但能用）
**預防**:
- 接到「YouTube 影片 → 詳細筆記 / 摘要 / podcast / 心智圖 / 測驗」任務時 → **第一步先確認赫米斯拿得到影片內容**：
  - 使用者提供 SRT/VTT 字幕檔 → 可以做摘要
  - 使用者貼影片描述 / 留言 → 可以做主題分析
  - **只有 RSS metadata** → 只能做標題級分類 + 誠實告知
- **不要**假設「赫米斯能分析 YouTube 影片」 — 這是 2026-06-07 才學到的能力邊界
- **不要**對 NotebookLM 自動化抱有幻想：NotebookLM 是 Google 的「個人學習工具」設計，不是「API 服務」
**If→Then**:
- **If** 使用者要求「分析 YouTube 影片」 **Then** 第一步問「你手上有字幕檔嗎？」或「你願意裝 yt-dlp 讓我抓 auto-gen 字幕嗎？」 — 沒有的話就只能做 metadata-level 整理
- **If** 使用者要求「轉成 podcast」 **Then** 說明 NotebookLM podcast 是 UI 功能（不能 API 觸發），建議備案：用赫米斯 `text_to_speech` 工具轉語音，或手動用 NotebookLM 上傳筆記後按 UI 按鈕
- **If** 接到「看影片內容自動學習新工具」任務  **Then** 必須先拿到字幕才能做 — 沒字幕 = 赫米斯只能從 metadata 推斷，**推斷 ≠ 真實內容**
- **If** 評估「赫米斯能不能做 X 任務」  **Then** 預設 N100 headless + 無瀏覽器 + 無字幕抓取 = 只能做 RSS/公開 API 層級的事
**相關條目**: 本 skill 的「OAuth Device Code Flow 對 installed/電腦 client 類型不支援」

---

### YouTube 影片分析不需要播放：字幕 + 封面圖就夠（2026-06-07）
**發現時間**: 2026-06-07
**觸發情境**: 使用者提供一份完整自動化架構文件，主張 AI 應該讀「影片的文字結構 + 視覺封面」而非真的播放
**根因**:
- 之前赫米斯一直卡在「赫米斯看不到 YouTube 影片」的思維，**只想到 metadata (RSS)**
- 沒有意識到：YouTube 影片 = **字幕（文字）** + **封面圖（靜態）**，這兩層都是**公開、合規、不需登入**就能拿
- **關鍵 insight（使用者提供）**：「AI 實際上不需要真的『播放』影片，而是讀取影片的文字結構與視覺封面」
**解法**:
- **字幕層**：`youtube-transcript-api` Python 套件 → 抓 auto-generated captions
  - 完全公開、不需登入
  - 90%+ YouTube 影片有 auto-gen CC（少數頻道關閉）
  - 輸出格式：時間戳 + 純文字（可調成純文字）
- **封面圖層**：YouTube 提供固定 URL 推導規則，**不需 API**
  - 高畫質：`https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg`
  - 中畫質：`https://img.youtube.com/vi/VIDEO_ID/hqdefault.jpg`
  - 縮圖：`https://img.youtube.com/vi/VIDEO_ID/1.jpg`（自動從影片抓 4 張）
- **LLM 摘要層**：把字幕文字 + 封面圖送進 LLM（Gemini 1.5/2.0 多模態效果最好、本地 qwen2.5:1.5b 對中文摘要堪用）
- **輸出層**：Markdown 內嵌封面圖 + 結構化筆記（章節摘要、重點、引用、Action items）
**預防**:
- 接到 YouTube 內容分析任務時**第一時間問自己**：「真的需要播放影片嗎？字幕 + 封面夠不夠？」
- **不要**直覺想到「下載 mp4 餵 LLM」（成本高、轉錄慢、侵權風險）
- 95% YouTube 影片的「知識內容」**字幕已經全寫了**，**視覺元素只有封面圖有意義**（章節圖示在影片內但無法直接抓）
**If→Then**:
- **If** 使用者要 YouTube 影片的「知識整理 / 筆記 / 摘要」  **Then** 預設用「字幕 + 封面圖 + LLM」pipeline，不要想下載 mp4
- **If** youtube-transcript-api 拿不到字幕  **Then** 是影片本身沒字幕或關閉了 — 不要 fallback 到爬影片，**直接跳過**該影片並告知
- **If** 想做 NotebookLM 風格的 podcast/心智圖/測驗  **Then** NotionLM 走不通（API 不支援），改用赫米斯 LLM 摘要 + Mermaid 心智圖 + 結構化測驗 markdown（赫米斯能做）
**相關條目**: 本 skill 的「YouTube 影片內容赫米斯看不到：只有 RSS metadata」

---


---

### Supabase REST API 必須用 service_role key、anon key 會 401/403(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 驗證 portal 評價 DB 連線狀態
**症狀**:
- 直接打 `curl https://<supabase-url>/rest/v1/evaluations?select=*` 回 `JWT cryptographic operation failed` 或 `PGRST301`
- 帶 anon key 也回 401
- 只有 `SUPABASE_SERVICE_ROLE_KEY` 才能讀 / 寫評價資料

**根因**:
- Supabase Row Level Security (RLS) 預設嚴格:
  - **anon key** = 公開、只能讀公開 view / 表的 RLS 允許部分
  - **service_role key** = 繞過 RLS、有完整讀寫權限
  - portal 評價 DB 對 anon 是關閉的,只有 server-side 用 service_role 能操作
- anon key 開頭通常是 `eyJ...`(長 JWT),service_role 也是 `eyJ...`,**開頭看起來一樣**,但 base64 解開 payload 後 `role` 欄位不同

**修法**:
1. **Server-side 腳本永遠用 `SUPABASE_SERVICE_ROLE_KEY`**:
   ```python
   from supabase import create_client
   supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
   result = supabase.from('evaluations').select('*').execute()
   ```

2. **驗證 RLS 是否啟用**:
   ```bash
   curl "$SUPABASE_URL/rest/v1/<table>?select=*" \
     -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
     -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
   ```
   service_role 同時填 apikey 跟 Authorization 才能 bypass RLS

3. **不要把 service_role key 推到前端 / 公開 repo**:
   - 前端只能用 anon key
   - service_role 只能在 server 端
   - portal 評價 .env.local 的 `SUPABASE_SERVICE_ROLE_KEY` 是 server-side OK

**If** → **Then** 規則:
- **If** 想從 server script 讀寫 Supabase 資料 **Then** 用 service_role key
- **If** Supabase API 回 401/403/PGRST301 **Then** 檢查用的 key 是不是 service_role
- **If** 接到兩個長得很像的 key **Then** 用 `jwt-decode` 工具或 base64 解 payload 比對 `role` 欄位
- **If** 想驗證 portal 評價 **Then** `set -a; source .env.local; set +a` 後用 service_role key
- **If** 部署到 Vercel **Then** env 變數名要一致、值要用 service_role、不是 anon

**已驗證**:
- 2026-06-07 直接 `curl` Supabase 報 PGRST301(JWT 失敗)
- 改用 `set -a; source .env.local; set +a` + service_role key 成功讀 4 筆 works、1 筆 evaluation
- 確認 portal 評價鏈:server script → service_role → Supabase → 回 JSON
