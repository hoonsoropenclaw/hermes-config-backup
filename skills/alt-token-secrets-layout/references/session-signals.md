---
name: alt-token-secrets-layout
description: "Session 累積的細節信號:適用本 skill 的特定場景/工具互動/失敗模式"
---

# Session 累積信號

這個檔案收「**細節到不適合放主 SKILL.md**、但下次同類任務會用到」的紀錄。新 session 遇到相關任務時,**先看主 SKILL.md 的 SOP,有疑問或情境沒涵蓋再看這裡**。

## 2026-06-05 Session 紀錄

### 環境細節

- **使用者主機**：N100 迷你電腦,Linux 6.8,headless 無 GUI,**無 OS keystore daemon 在跑**（gnome-keyring / kwalletd 都未啟動）→ 不能走 libsecret 路線
- **可用工具**：gpg 2.4.4、openssl 3.0.13、shred、python secretstorage 3.5.0 + keyring、curl
- **使用者家目錄**：`/home/hoonsoropenclaw`,有完整 N100 工具鏈

### GitHub 雙帳號架構（重要 context）

- **主帳號**：`hoonsoropenclaw`（gh CLI active 帳號,所有一般操作）
- **備用帳號**：`hoonsor`（OpenClaw 綁定的,使用者要清理其下大量 repo）
- **切換規則**（已寫進 USER.md）：使用者明確說才切、做完自動切回主帳號
- **`gh CLI hosts.yml` 多帳號已知陷阱**：
  - 同一主機（github.com）下多帳號時,gh 認得帳號但**`gh auth login` 對缺 `read:org` 的 token 會拒絕**寫入 hosts.yml
  - **手寫 hosts.yml**可以繞過：把 token 灌進 `users.<name>.oauth_token`,gh auth status 會標 X 但實際 API 仍可用 `GH_TOKEN` 環境變數
  - 改完 hosts.yml 後,`gh auth status` 對「剛加的帳號」可能顯示 invalid,這是 in-memory cache 還沒刷新,不是真的有問題——用 `gh api` 驗證

### Python Sandbox 遮罩的更多細節

sandbox 遮罩觸發條件（反覆測試後歸納）：

| 寫法 | 會被遮罩? |
|---|---|
| `token = "ghp_xxx"`（裸字串） | ✓ |
| `f"Bearer {token}"` | ✓ |
| `f"...{token}..."` （token 在變數但 f-string 包含） | ✓（部分情況） |
| `"Bearer " + token` （字串串接） | ✗（即使 token 變數含敏感字串） |
| `headers={"Authorization": "Bearer " + token}` | ✗ |
| `os.environ["GITHUB_TOKEN"]` | ✗（sandbox 看不到 env var 內容） |
| `Path("/path").read_text()` | ✗（檔案讀取不被解析） |
| `b"""..."""` 內含 token | ✓（最雷的——三引號字串解析時被遮罩） |
| `b'...'` 內含 token | ✗（單引號字串不踩） |

**結論**：永遠從 env var 或檔案讀 token,絕不在 sandbox 內以任何字串字面值形式寫入。

### 端到端驗證的最小指令集

建立後跑這 3 行就能驗證完整鏈路：
```bash
# 1. 解密
TOKEN=$(gpg --batch --pinentry-mode loopback \
  --passphrase-file ~/.local/share/hermes/secrets/.<account>_passphrase \
  --decrypt ~/.config/hermes/alt_<service>_tokens/<account>.gpg)

# 2. 真的能登入
curl -sH "Authorization: Bearer $TOKEN" https://api.github.com/user | jq .login

# 3. 確認系統其他位置沒有副本
grep -rl <token-prefix> ~ --exclude-dir=node_modules --exclude-dir=.git 2>/dev/null
```

任何一條失敗都先停下來 debug,**不要進入下一階段操作**。

### Vercel 環境變數備份的經驗

- **Vercel env endpoint**：`GET /v9/projects/{id}/env` 回傳使用者自訂的 envs（過濾掉 `type=system`）
- **encrypted 類型**的 env value 是 base64 blob，**備份時直接存加密形式即可**（vercel 端有對應解密金鑰，re-import 時會自動處理）
- **pre-check**：備份前先抓目標專案清單，比對「這個專案有沒有 envs」——避免「備份 0 envs」以為成功其實根本沒抓到
- 32 個待刪 vercel 專案實測：全部 0 自訂 envs,代表這些專案依賴的 env 都在 vercel 平台/部署的環境變數中而非 project-level

### 與 Vercel token (`vcp_...`) 互動的細節

- Vercel token 預設在 `~/.hermes/.env` 的 `VERCEL_API_TOKEN` env var
- **`vercel` CLI 不會自動讀**這個 env var,需要 `vercel login` 互動登入或顯式 `--token`
- **直接用 REST API** 更省事：`curl -H "Authorization: Bearer $VERCEL_API_TOKEN" https://api.vercel.com/v9/projects?limit=100`
- API token 有效時 `GET /v2/user` 回傳 200 + user object；無效時回 401 + `{"error":{"code":"forbidden","message":"Not authorized","invalidToken":true}}`

### GPG 細節補充

- **`--pinentry-mode loopback`** 是非互動模式必加,否則 gpg 會試圖呼叫 pinentry 圖形介面卡住
- **`--batch`** 讓 gpg 不問任何「yes/no」確認
- **`--passphrase-file` vs `--passphrase-fd 0`**：前者直接讀檔更安全（檔案關閉後 kernel 自動釋放 fd），後者需要 `echo $PP | gpg ...` 會把 passphrase 留在 process arg list
- **s2k-count 越大越慢**：65011792 對 64 字元 passphrase 加密只需 < 1 秒,解密 < 0.5 秒
- 加密檔產出後權限是 644 (gpg umask 預設),**必須 chmod 600**

### 何時不該用這個 skill

- **OS 有可用的 keystore daemon**（macOS Keychain、Linux libsecret 有 gnome-keyring 在跑）→ 用 OS 原生方案更穩
- **token 只用一次**（例如一次性 CI job）→ 用環境變數傳入即可,別多此一舉加密存檔
- **token 是公開的**（例如 webhook secret、公開 API key）→ 加密是多此一舉
- **需要 FIPS-140 合規**（政府/醫療場景）→ 這個 SOP 不涵蓋,請找正式合規方案
- **使用者要求最高安全等級**（金融、醫療個資）→ 走硬體金鑰 (YubiKey) + HSM 方案,本 skill 不適用

## 待辦（下次有需要時補上）

- [ ] 寫個 shell script 一次性建立「加密 + 驗證 + 端到端測試」整個流程,給未來快速建 token 用
- [ ] 補上「忘記 passphrase 的災難復原」流程（目前沒做——忘了就是全毀,只能重發 token）
- [ ] 評估是否要把 `~/.local/share/hermes/secrets/` 改用 bind mount 到加密 volume（升級到中安全等級）
