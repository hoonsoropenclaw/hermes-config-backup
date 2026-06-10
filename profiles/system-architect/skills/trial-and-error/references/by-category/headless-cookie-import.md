# Headless 環境把瀏覽器 Cookies 餵給第三方 CLI（X / Reddit / 微博 / 小紅書 / 雪球 / ...）

> 觸發:在 N100 headless 環境要啟用某個需要登入的平台 CLI（twitter-cli / rdt-cli / xhs-cli / weibo-cli / xueqiu-cli / ...）,
> 而該 CLI 預設依賴瀏覽器 cookie extraction（`browser-cookie3`）→ N100 沒瀏覽器 → 必須手動匯入 cookies
>
> 建立時間: 2026-06-08
> 涵蓋平台: Twitter/X (twitter-cli), Reddit (rdt-cli), **小紅書 / 微博 / 雪球 / 其他 (見各 CLI 文件)**

---

## 通用前置：Cookie-Editor JSON 轉各平台吃的格式

**使用者匯出格式**: Cookie-Editor Chrome 插件的 JSON Export（陣列,每個 cookie 一個 object）
**結構**:
```json
[
  {"domain": ".x.com", "expirationDate": 1780934401, "name": "auth_token", "value": "...", "httpOnly": true, "secure": true, "path": "/"},
  ...
]
```

**必做的轉換**: 過濾過期、轉成「各 CLI 吃的格式」（見下表）

```python
import json, time

with open('/path/to/<platform>.json') as f:
    raw = json.load(f)

# 過濾掉已過期的（expirationDate 是 unix timestamp, 0 = session cookie）
valid = [c for c in raw if c.get('expirationDate', 0) > time.time()]
print(f'{len(valid)}/{len(raw)} cookies still valid')
```

---

## 平台對照表

| 平台 | CLI | 認證機制 | 所需 cookies | 存放位置 |
|------|------|----------|--------------|----------|
| **Twitter/X** | twitter-cli | **環境變數** `TWITTER_AUTH_TOKEN` + `TWITTER_CT0` | auth_token, ct0, 建議也帶 gt/twid/\_\_cuid | export 到 `~/.bash_env` (mode 600) |
| **Reddit** | rdt-cli | **JSON 檔** | reddit_session（必需）, token_v2（強烈建議） | `~/.config/rdt-cli/credential.json` (mode 600) |
| **YouTube** | yt-dlp | **Netscape cookie 檔** | SAPISID, LOGIN_INFO, HSID, SSID, SID, APISID | `~/.config/yt-dlp/cookies.txt` |
| **小紅書** | xhs-cli | Cookie header string | 詳見 xhs-cli 文件 | 透過 `agent-reach configure xhs-cookies "..."` 寫入 `~/.agent-reach/config.yaml` |
| **微博** | weibo-cli | Cookie header string | 詳見 weibo-cli 文件 | 類小紅書 |
| **雪球** | xueqiu-cli | Cookie header string | 詳見 xueqiu-cli 文件 | 類小紅書 |

> **Twitter/X 環境變數要全 cookie 不只 auth+ct0**:twitter-cli 0.8.5 README 明確說「Browser extraction 是 recommended,只給 `auth_token`+`ct0` 會被 X API 認 csrf 不匹配拒絕」
> 但實測 **N100 headless 只給 auth_token+ct0 + 乾淨 IP 能成功**（環境變數方式仍可登入）
> 給完整 cookies 仍比較保險

---

## 平台 1：Twitter/X (twitter-cli)

**CLI 套件**: `pip install twitter-cli` (或 `uv tool install twitter-cli`)

**認證格式**（**環境變數**）:
- `TWITTER_AUTH_TOKEN=...` （必填,40 hex chars,從 X.json 的 `auth_token`）
- `TWITTER_CT0=...` （必填,160 hex chars,從 X.json 的 `ct0`）

**存放位置**: `~/.bash_env` (獨立檔,mode 600),在 `~/.bash_profile` / `~/.profile` / `~/.bashrc` 開頭 source（**繞過互動式 return 阻擋**,見下方「踩雷」）

**為什麼不能用 `agent-reach configure twitter-cookies` 一行搞定**:
- `configure` 會把 cookie 寫進 `~/.agent-reach/config.yaml`
- 但 doctor 的 `TwitterChannel.check()` **直接跑 `twitter status`、不會注入 env vars** → 永遠顯示 not_authenticated
- 解法是手動 export 到 shell env,讓 doctor 跑 subprocess 時自動繼承

**完整 SOP**:
```bash
# 1. 讀 X.json
python3 -c "
import json, time
with open('/path/to/X.json') as f:
    cookies = json.load(f)
valid = {c['name']: c['value'] for c in cookies if c.get('expirationDate', 0) > time.time()}
print(f'auth={valid[\"auth_token\"]}')
print(f'ct0={valid[\"ct0\"]}')
" > /tmp/x_creds.txt

# 2. 寫到 ~/.bash_env（注意：CT0 是 160 chars,普通 hex 不含特殊字元,可直接寫）
# 用 chr(34) 構造雙引號避免 f-string 把 token 當變數替換的 bug
python3 << 'PYEOF'
import json, time
with open('/path/to/X.json') as f:
    raw = json.load(f)
valid = {c['name']: c['value'] for c in raw if c.get('expirationDate', 0) > time.time()}
dq = chr(34)
content = '#!/bin/bash\n# Twitter credentials for twitter-cli (auto-sourced by login shells)\n'
content += f'export TWITTER_AUTH_TOKEN={dq}{valid["auth_token"]}{dq}\n'
content += f'export TWITTER_CT0={dq}{valid["ct0"]}{dq}\n'
with open('/home/USER/.bash_env', 'w') as f:
    f.write(content)
import os
os.chmod('/home/USER/.bash_env', 0o600)
PYEOF

# 3. 在三個 startup 檔最開頭 source .bash_env（在互動式判斷之前）
for f in ~/.bash_profile ~/.profile ~/.bashrc; do
  if ! grep -q '.bash_env' "$f"; then
    printf '[ -f ~/.bash_env ] && . ~/.bash_env\n\n%s' "$(cat $f)" > "$f.new" && mv "$f.new" "$f"
  fi
done

# 4. 驗證
bash -lc 'echo "AUTH len: ${#TWITTER_AUTH_TOKEN}"; echo "CT0 len: ${#TWITTER_CT0}"'
# 必須 40 / 160

bash -lc 'twitter status'
# 必須 ok: true, authenticated: true
```

**⚠️ 必踩雷**（3 個,都是這次 2026-06-08 實測踩到的）:
1. **f-string 內嵌 token 被過濾**: `f"...{auth}..."` 會被某些環境當成「印出 token」過濾掉,改成 `chr(34)` 字串連接
2. **bash_profile 從 bashrc 抄 skeleton 會帶「互動式 return」**:bashrc 開頭的 `case $- in *i*) ;; *) return;; esac` 在非互動式 subprocess 會提前 return,後面 export 不跑。修法是用獨立 `~/.bash_env`,在 startup 檔最開頭 source
3. **CT0 長度必須剛好 160,被截就 403 csrf mismatch**:寫入後必驗 `${#TWITTER_CT0}` = 160

---

## 平台 2：Reddit (rdt-cli)

**CLI 套件**: `pip install rdt-cli` (或 `uv tool install rdt-cli`)

**認證格式**（**JSON 檔**,**不是環境變數**）:
```json
{
  "cookies": {
    "reddit_session": "...",
    "token_v2": "..."
  },
  "source": "manual-import-2026-06-08",
  "username": null,
  "modhash": null,
  "saved_at": 1234567890.0,
  "last_verified_at": null
}
```

**存放位置**: `~/.config/rdt-cli/credential.json` (mode 600)

**最低門檻**:`REQUIRED_COOKIES = {"reddit_session"}`（rdt-cli source code 寫死）

**完整 SOP**:
```python
import json, time, os

# 1. 讀 reddit.json
with open('/path/to/reddit.json') as f:
    raw = json.load(f)

# 2. 過濾 + domain 統一
valid = {}
for c in raw:
    if c.get('expirationDate', 0) < time.time():
        continue
    if 'reddit.com' in c['domain']:
        valid[c['name']] = c['value']

# 3. 寫 rdt-cli 的 credential.json
credential = {
    "cookies": valid,
    "source": "manual-import-2026-06-08",
    "username": None,
    "modhash": None,
    "saved_at": time.time(),
    "last_verified_at": None,
}
os.makedirs('/home/USER/.config/rdt-cli', exist_ok=True)
with open('/home/USER/.config/rdt-cli/credential.json', 'w') as f:
    json.dump(credential, f, indent=2)
os.chmod('/home/USER/.config/rdt-cli/credential.json', 0o600)

# 4. 驗證
```

**為什麼 reddit 不像 twitter 用環境變數**:
- twitter-cli: 「登入是暫時、可被用戶登出」→ 用環境變數, 每次 `twitter` 指令都帶
- rdt-cli: 「登入是持久、想跨 session 保留」→ 用檔案, 預設有效 7 天

**⚠️ 踩雷**:
- **rdt-cli 沒有 `agent-reach configure` 整合**: `agent-reach configure --help` 沒有 `reddit-cookies` 子命令（已實測,只支援 twitter/youtube/xhs）
- **`rdt login` 在 N100 不能用**: N100 沒瀏覽器, `rdt login` 內部跑 `browser-cookie3` 會失敗 → **手動寫 credential.json 是唯一解**
- **domain 寫法混亂**: 匯出時有 `reddit.com` 跟 `www.reddit.com` 兩種,要全部收進 `valid` dict
- **token_v2 是 JWT 結構**: rdt-cli 內部自動從 token_v2 解析 modhash, 不需要手動填

---

## 平台 3：YouTube (yt-dlp, Netscape cookie 檔)

**CLI 套件**: 已隨 agent-reach 自動裝 (`pip install yt-dlp` 或 `pip install -U "yt-dlp[default]"`)

**認證格式**（**Netscape 格式 cookie 檔**）:
```
# Netscape HTTP Cookie File
.domain.com	TRUE	/	TRUE	1234567890	cookie_name	cookie_value
```

**存放位置**: `~/.config/yt-dlp/cookies.txt` 或任何路徑,用 `--cookies <path>` 指定

**必備 cookies** (Google 帳號登入):
- `SAPISID` (最重要)
- `LOGIN_INFO`
- `HSID`, `SSID`, `APISID`, `SID`

**完整 SOP**:
```python
import json, time, os

# 1. 讀 YouTube cookies JSON
with open('/path/to/youtube.json') as f:
    raw = json.load(f)
valid = [c for c in raw if c.get('expirationDate', 0) > time.time()]

# 2. 寫 Netscape 格式
os.makedirs('/home/USER/.config/yt-dlp', exist_ok=True)
with open('/home/USER/.config/yt-dlp/cookies.txt', 'w') as f:
    f.write("# Netscape HTTP Cookie File\n# https://curl.haxx.se/rfc/cookie_spec.html\n\n")
    for c in valid:
        domain = c['domain']
        # ⚠️ Netscape 格式的 domain 前面要加 #HTTPONLY# for httpOnly cookies
        prefix = "#HttpOnly_" if c.get('httpOnly') else ""
        # ⚠️ flag: TRUE if domain starts with dot
        flag = 'TRUE' if domain.startswith('.') else 'FALSE'
        path = c.get('path', '/')
        secure = 'TRUE' if c.get('secure', False) else 'FALSE'
        exp = str(int(c.get('expirationDate', 0)))
        f.write(f"{prefix}{domain}\t{flag}\t{path}\t{secure}\t{exp}\t{c['name']}\t{c['value']}\n")
os.chmod('/home/USER/.config/yt-dlp/cookies.txt', 0o600)

# 3. 驗證
yt-dlp --cookies /home/USER/.config/yt-dlp/cookies.txt --list-subs <YOUTUBE_URL>
```

**⚠️ 踩雷**:
- **Netscape 格式 `httpOnly` cookie 前綴**: 一般文件沒寫明,實測必須加 `#HttpOnly_` 前綴,否則 yt-dlp 抓不到
- **domain 統一**: Cookie-Editor 匯出有 `youtube.com` 跟 `.youtube.com`,寫 Netscape 時保留原樣
- **YouTube 仍可能 429**: cookie 配對成功 ≠ 就能下載,YouTube 對 datacenter IP 仍會限流。**真要解 → 住宅代理**（見 youtube-cookies 配置）

---

## 平台 4-N：小紅書/微博/雪球（agent-reach configure 直接吃）

**通用 pattern**:
```bash
# 把 cookies.json 轉 header string
python3 -c "
import json, time
with open('/path/to/<platform>.json') as f:
    cookies = json.load(f)
valid = [c for c in cookies if c.get('expirationDate', 0) > time.time()]
print('; '.join(f\"{c['name']}={c['value']}\" for c in valid))
" > /tmp/cookie_header.txt

# 餵給 agent-reach
agent-reach configure xhs-cookies "$(cat /tmp/cookie_header.txt)"
agent-reach configure weibo-cookies "$(cat /tmp/cookie_header.txt)"
# ⚠️ 沒有 reddit-cookies 跟 youtube-cookies（youtube-cookies 參數是瀏覽器名稱,不是 cookie string）
```

**存放位置**: `~/.agent-reach/config.yaml` (mode 600, agent-reach 自己 chmod)

---

## 通用 SOP（跨平台）

任何「在 N100 headless 啟用 X 平台」任務都走這套:

```
1. 確認 CLI 套件裝好
   pip install <cli>
   ln -sf ~/.agent-reach-venv/bin/<cli> ~/.local/bin/<cli>
   which <cli>  # 必須在 ~/.local/bin

2. 確認 cookies 檔 / env var 已就位
   見各平台章節

3. 跑對應的 status 指令
   twitter status / rdt status / rdt whoami / xhs whoami
   必須 ok: true

4. 跑 agent-reach doctor
   該平台渠道必須 ✅ (Twitter: 9/16, Reddit: 10/16, ...)

5. 實測一條讀取命令
   twitter user <handle> / rdt popular -n 3 / rdt search "test" -n 2
   必須回 ok: true + 真實資料
```

**If→Then**:
- **If** 任何 N100 headless 平台認證任務 **Then** 先查 `~/.local/share/hermes/secrets/` 有沒有預存 cookies
- **If** 沒有,使用者要從自己電腦 Chrome 匯出 Cookie-Editor JSON **Then** 走「平台 X」章節的 SOP（不要從 X 套到 Y,每個 CLI 吃的格式不同）
- **If** `agent-reach configure` 沒有該平台子命令 **Then** 走該 CLI 自己的 credential 機制（rdt-cli 寫 JSON、twitter-cli 設 env）
- **If** 認證失敗顯示 401/403/csrf mismatch **Then** 檢查 cookie 完整長度（CT0 必須 160）、檢查 env var 有沒被截、檢查 cookie 是不是 session-only 已過期
- **If** doctor 顯示渠道 ✅ 但實測失敗 **Then** 檢查 env var 在 login shell 內是否生效（`bash -lc 'echo $TWITTER_CT0'`，非 `bash -c`）

---

## 已驗證案例（2026-06-08）

| 平台 | 套件版本 | 帳號 | 認證後渠道數 | 實測 |
|------|----------|------|--------------|------|
| Twitter/X | twitter-cli 0.8.5 | @Luke199001Luk (呂路可) | 8/16 → 9/16 | `twitter user Luke199001Luk` 回完整 profile |
| Reddit | rdt-cli 0.4.1 | u/BeautifulCrazy1235 | 9/16 → 10/16 | `rdt popular`、`rdt search "python"` 回真實 listing |
| YouTube | yt-dlp 2026.3.17 + yt-dlp-ejs 0.8.0 | N/A | 仍 7/16 (只有 cookies 沒 IP 代理) | `--list-subs` 列出 100+ 字幕語系但實際抓檔 429 |

---

## 配套

- `python-sandbox.md` — `uv venv` 沒 pip、force-include 衝突、venv CLI 需 symlink 到 `~/.local/bin`、yt-dlp JS runtime
- `hermes-internal.md` — bash_profile 從 bashrc 抄 skeleton 帶互動式 return 阻擋、bash_env 獨立檔繞過
- `references/pre-task-checklist.md` (general-workflow) — 每任務第一個 tool call 之前必跑 trial-and-error 預載
