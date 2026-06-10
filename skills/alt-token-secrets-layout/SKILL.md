---
name: alt-token-secrets-layout
description: "當使用者要把 GitHub / Vercel / 其他 token 存成本機檔、且不想放在 ~/.bashrc 或明文 ~/.config 時,使用 GPG 對稱加密 + 雙目錄分離佈局,避免兩個檔案被同一個工具/掃描同時撈走。"
version: 1.2.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [secrets, gpg, encryption, github, vercel, public-repo-safety]
    triggers: [token 儲存, secret, gpg 加密, sync 到公開 GitHub, GH013]
---

# 替代 Token 安全儲存佈局

當使用者要在本機保存 GitHub / Vercel / 其他服務的 PAT 或 API key,並且不希望走 OS keystore、明文 .env、或家目錄的純檔案時,使用這個 GPG 對稱加密 + 雙目錄分離佈局。

## 何時使用

- 使用者說「幫我存這個 token」「我想保留這個 PAT 給未來用」之類
- 使用者對安全性有疑慮但又不想用 keystore / 硬體金鑰等太重的方案
- token 需要跨 session 重複使用 (例如主帳號 + 備用帳號切換、CI bot token 等等)
- 不適用於:已內建 OS keystore 的場景 (macOS Keychain、Linux libsecret + daemon)、需要硬體金鑰的高敏感場景

## ⚠️ 絕對禁止：把 secrets 同步到公開 GitHub repo（2026-06-05 真實事件）

**事件**：`md-files-daily-sync` 把 `MEMORY.md` 內的 `vcp_***REDACTED***` 同步到 `hermes-status-site/assets/md-files.json`，推到公開 GitHub repo，觸發 GH013 push protection 失敗 4+ 天。

**2026-06-06 升級事件**：找到 root cause 後完整修復：
- `MEMORY.md` 的 token literal 已被 scrub
- `sync_md_files.py` 加了 pre-write secret scan + 移除 hardcoded token fallback
- 用 `git-filter-repo` 重寫 17 個 commit 的 SHA
- 完整 SOP 收錄在 `~/.hermes/skills/cron-secret-leak-emergency-fix/SKILL.md`

**教訓**：
- 所有「把本地檔同步到公開 GitHub repo」的腳本必須內建 **pre-commit secret scan**
- `MEMORY.md` / `USER.md` 等被同步的檔案**只放抽象教訓**，**不放具體 token 值**（用 `***` 取代）
- 完整修復 SOP 見 `references/cron-secret-leak-scrub.md` + `~/.hermes/skills/cron-secret-leak-emergency-fix/SKILL.md`

**`sync_md_files.py` 必須加**：
```python
TOKEN_PATTERNS = [
    (r'vcp_[a-zA-Z0-9]{20,}', '[Vercel Token]'),
    (r'ghp_[a-zA-Z0-9]{36}', '[GitHub Token]'),
    (r'sk-[a-zA-Z0-9]{48}', '[OpenAI Key]'),
    (r'gho_[a-zA-Z0-9]{36}', '[GitHub OAuth]'),
    (r'glpat-[a-zA-Z0-9]{20,}', '[GitLab Token]'),
    (r'\bhms_[a-zA-Z0-9_]{20,}', '[Hermes Portal Key]'),
]
# 在寫入 JSON 之前對 content 跑 regex.sub
```

詳細內容見 `references/secrets-in-sync.md`（同 metacognitive-learner 內副本）。

## User Preferences（已驗證的偏好,新 session 預設帶入）

- **「防君子不防小人」優先**：使用者說過「反正我已經撤銷 token 的刪除 repo 權限了,應該不用太擔心」。當被問「要不要再強化」時,**不要主動推薦**硬體金鑰、TPM、passphrase + 環境變數分開等更激進方案,直接照本 SOP 執行即可
- **不要勸說升級安全等級**：使用者說「防君子不防小人」時,意思是「夠用就好」。赫米斯若再回「但其實你可以更安全」,會被視為繞圈子
- **給使用者主控權**：把 passphrase 存哪、用什麼 cipher、要不要雙目錄分離——這些都讓使用者選。**預設值就是 SOP 寫的版本**,不要再問
- **使用者對 LLM 對話有警覺**：曾說過「不要在對話框貼 token」「總之你寫個檔案就好」。所以 token 的接收一律用檔案,不要請使用者在對話中打 token 字串
- **Sync 檔案不含真實 token**（2026-06-05 新增）：使用者說過「MEMORY.md 等被同步的檔案不放具體值」。赫米斯若在會被同步的檔內寫 `ghp_xxx` / `vcp_xxx` 字面值,等同 credential leak 風險,必須用 `***` 取代

## 威脅模型假設

這個佈局**不是**防 root、防完整磁碟 dump、防國家級攻擊。它防的是:
- 隨機掃 / 撈家目錄的自動化工具 (備份誤送、CI artifact、dotfile 同步)
- 不小心 sync 整個 `~/.config/` 到公開位置
- 同機一般使用者偷看 (前提是 owner 設定正確 + 600/700)
- **同步腳本未過濾就把 secrets 推到公開 GitHub**（2026-06-05 新場景）

如果使用者要求更高的安全等級,提示選項 D (環境變數注入) 或硬體金鑰。

## 雙目錄佈局

```
~/.config/hermes/alt_<service>_tokens/          (目錄 700)
  └── <account>.gpg                              (檔案 600, 加密後的 token)

~/.local/share/hermes/secrets/                   (目錄 700, 新建)
  └── .<account>_passphrase                       (檔案 600, 解密密碼)
```

兩個檔案分散在兩個完全不同的目錄樹下 (`~/.config/` vs `~/.local/share/`),自動化掃描工具要同時撈到兩個目錄的機率低於單一目錄。

## 標準作業流程

### 1. 確認 GPG 與工具

```bash
gpg --version                # 需要 2.x
which shred                   # 需要 coreutils
```

### 2. 接收 token

絕對不要讓使用者在對話框貼 PAT。請使用者寫到隔離檔:

```bash
echo "ghp_xxxxxxxx" > ~/.config/hermes/alt_gh_tokens/<account>
chmod 600 ~/.config/hermes/alt_gh_tokens/<account>
```

然後使用者告訴你「已寫入」,你讀檔繼續。

### 3. 驗證 token 有效

```python
import urllib.request, json
token = open(path).read().strip()
req = urllib.request.Request("https://api.github.com/user",
                             headers={"Authorization": "Bearer " + token})
data = json.loads(urllib.request.urlopen(req).read())
# 確認 login、id、scopes 都符合預期
```

如果 401,要求使用者重發新 token。**不要**在主 session 內 retry 多次,token 可能已被 revoke。

### 4. 生高熵 passphrase

```python
import secrets, string
alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
passphrase = ''.join(secrets.choice(alphabet) for _ in range(64))
```

64 字元,a-z A-Z 0-9 加常見特殊符號,熵約 6.5 bits/字元 × 64 = 416 bits,遠超 AES-256 強度。

### 5. 存 passphrase 到分離目錄

```python
from pathlib import Path
pp_path = Path("/home/<user>/.local/share/hermes/secrets/.<account>_passphrase")
pp_path.parent.mkdir(parents=True, exist_ok=True)
pp_path.parent.chmod(0o700)
pp_path.write_text(passphrase + "\n")
pp_path.chmod(0o600)
del passphrase  # 從 Python 變數抹掉
```

### 6. GPG 對稱加密

```bash
gpg --batch --pinentry-mode loopback \
    --passphrase-fd 0 \
    --symmetric \
    --cipher-algo AES256 \
    --s2k-mode 3 \
    --s2k-count 65011712 \
    --output <encrypted_path> <plaintext_path>
```

加密參數說明:
- `AES256`:目前業界標準,2026 沒有已知實際攻擊
- `--s2k-mode 3`:iterated + salted S2K,防 rainbow table
- `--s2k-count 65011792`:OpenPGP 建議的迭代次數,大幅增加暴力破解成本

加密檔產生後**立刻修權限為 600** (gpg 預設產出是 644)。

### 7. 刪除明文 token 檔

```bash
shred -u -z -n 3 <plaintext_path>
```

- `-u`:刪除檔案
- `-z`:最後一輪用 0 覆寫(隱藏 shred 痕跡)
- `-n 3`:3 輪隨機覆寫

對 SSD 而言,`shred` 不保證磁碟底層真的被清(SSD 會做 wear leveling),但對備份誤送 / 公開上傳這類情境,檔案系統層的清除已經足夠。

### 8. 端到端驗證

```bash
# 解密驗證
gpg --batch --pinentry-mode loopback \
    --passphrase-file ~/.local/share/hermes/secrets/.<account>_passphrase \
    --decrypt ~/.config/hermes/alt_<service>_tokens/<account>.gpg

# 拿解密出來的 token 打 API,確認能登入
```

驗證必須包含「解密後的 token 真的能進目標服務」這一步,確保 passphrase 沒打錯、加密沒出問題。

### 9. 未來自動解密

赫米斯之需要用 token 時,跑:

```bash
TOKEN=$(gpg --batch --pinentry-mode loopback \
            --passphrase-file ~/.local/share/hermes/secrets/.<account>_passphrase \
            --decrypt ~/.config/hermes/alt_<service>_tokens/<account>.gpg)
GH_TOKEN=$TOKEN gh api user
```

整個鏈路赫米斯內部完成,使用者不用手動。

## 已知陷阱

1. **Python sandbox 會把 token 字面值遮罩成 `***`**,所以在 `f"Bearer {token}"` 這種寫法會被截斷。改用 `headers={"Authorization": "Bearer " + token}` 串接,或從檔案讀取。**這個坑反覆踩到,本 session 因此多 retry 3 次,務必記住**
2. **GPG 第一次跑會自動建 `~/.gnupg/pubring.kbx`**,這是正常現象,不是錯誤。
3. **GPG 2.4+ 的 AEAD 加密格式 header 是 `0x8c 0x0d` 開頭**,不是舊的 `0x85`,不要誤判成加密失敗。
4. **gpg 預設產出檔案 mode 是 644**,加密完要手動 chmod 600,不要漏。
5. **gh CLI 的 `gh auth login --with-token` 對缺少 `read:org` scope 的 token 會失敗**,這時改用手寫 `~/.config/gh/hosts.yml`,在 `users:` 下加帳號。gh auth status 對「自己寫進 yml 但缺 scope」的帳號會標 X,但實際操作仍可用 `GH_TOKEN` 環境變數走 API。
6. **shred 對 SSD 效果有限**,但對家用備份意外、誤傳到公開地方這類威脅已經足夠。
7. **不要把 passphrase 跟加密檔放同一個目錄** — 這是整個佈局的核心,失效等於沒加密。
8. **不要在對話框貼 token** — 任何 LLM 對話都可能 log、上傳、留 cache。請使用者一律寫到隔離檔。
9. **絕對不要把 secrets 同步到公開 GitHub repo**（2026-06-05 新增） — 即使是「被 sync 工具拷貝過去」也算,等於主動洩漏。完整修復見 `references/cron-secret-leak-scrub.md`。
10. **.env.local 可能含多行同名變數**（2026-06-05 新增） — 用 `grep | cut` 讀 token 會取到錯的行。改用 `awk -F= '/^KEY=/{print $2; exit}'` 或 `re.search(r"^KEY=(...)", content, re.MULTILINE)`。完整案例見 `portal-401-troubleshoot/references/multiline-env-local.md`。

### Bash 腳本撰寫陷阱（2026-06-07 新增 — 寫 GPG 加密腳本時踩到）

這 3 個 bash 坑在寫 `hermes-secrets-encrypt.sh` 跟 `hermes-restore-v4.sh` 時各踩一次、未來任何 GPG + rclone 自動化腳本都會碰到。**先記住、後寫**。

11. **for-loop 內的 `2>/dev/null` 會吃 `;`** — `for f in glob/*.token 2>/dev/null; do` 在某些 bash 版本（特別是 dash 相容模式）會報 `syntax error near unexpected token`。修法：
    ```bash
    # 錯
    for f in "$HERMES_HOME"/*.token 2>/dev/null; do

    # 對：用 shopt nullglob
    shopt -s nullglob
    for f in "$HERMES_HOME"/*.token; do
        [[ -f "$f" ]] || continue
        ...
    done
    shopt -u nullglob
    ```

12. **函式內的 `echo` 會汙染 command substitution 回傳值** — `tar_path=$(collect_secrets)` 會把所有 echo（含 ANSI 色碼）抓進 `$tar_path`，導致 `gpg --output "$tar_path"` 開一個不存在的「整串 echo」檔案。修法：**函式內所有 status/progress echo 都改去 `>&2`**，只有最終結果走 stdout：
    ```bash
    collect_secrets() {
        mkdir -p "$out" >&2          # 去 stderr
        echo "found .env" >&2         # 去 stderr
        ...
        echo "$tar_path"              # 只有這行走 stdout（函式回傳值）
    }
    ```

13. **`${arr[@]}` 在 `[[ =~ ]]` regex 比對內會展開成多元素、regex parser 抓狂** — `if [[ ! " ${file_names[@]} " =~ " $bn " ]]; then` 在 bash 4.x 會 parse error。修法：**用 glob pattern 風格的 `==` 取代 `=~`**，或改用 `case`：
    ```bash
    # 錯
    if [[ ! " ${file_names[@]} " =~ " $bn " ]]; then

    # 對（pattern 比對、無 regex）
    if [[ ! " ${file_names[*]} " == *" $bn "* ]]; then

    # 對（case 寫法、最清楚）
    case " ${file_names[*]} " in
        *" $bn "*) ;;  # already in list
        *) file_names+=("$bn") ;;
    esac
    ```

**症狀速查**：
- bash 報 `syntax error near unexpected token` 但 hexdump 看該行 100% 正確 → **錯在前一行**（bash error line off-by-one，line N 報的錯其實是 N-1 沒收尾）
- `gpg: can't open '<一整串 ANSI 碼>'` → **第 12 坑**
- bash 報 `syntax error` 在 `2>/dev/null` 那行 → **第 11 坑**

### Python Sandbox Token 遮罩問題（2026-06-05 session 重大坑點）

**問題**：在 `execute_code` 內用 f-string 或 `"""..."""` 寫入 token 字面值時,sandbox 會在語法解析階段把 `ghp_xxx` 整串替換成 `***` 並截斷字串,造成 `SyntaxError: unterminated string literal`。

**症狀**：
```
File "<script>", line N
    token = "ghp_***"
              ^
SyntaxError: unterminated string literal (detected at line N)
```

**預防策略（按優先順序）**：

1. **不寫死 token**——從環境變數讀取（推薦）:
   ```python
   import os
   token = os.environ["GITHUB_TOKEN"]  # sandbox 看不到這個 env var 內容
   ```
2. **從檔案讀取**（sandbox 不會遮罩檔案內容）:
   ```python
   from pathlib import Path
   token = Path("/path/to/token").read_text().strip()
   ```
3. **不要用 f-string 寫 token**——改用字串串接:
   ```python
   # 錯:f-string 會被遮罩
   req = urllib.request.Request(url, headers={"Authorization": f"Bearer ***"})
   # 對:字串串接
   req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
   ```
4. **絕對不要用三引號字串包 token**——sandbox 解析 `b"""..."""` `b'''...'''` 都會踩到遮罩

**陷阱偵測**：
- 出現 `SyntaxError: unterminated string literal` + 旁邊有 `***` → 100% 是這個坑
- 出現 `Bad credentials` 401 → 先確認 token 沒被 shell 解析掉,再懷疑 token 本身過期

**踩到後正確處置**：
- 立刻停止 retry,改用「從檔案讀取」路線
- 不要在主 session 反覆嘗試不同寫法——會污染 context、且 90% 都是同一個原因

## 驗證清單

完成後必須驗證:
- [ ] 加密檔存在且 mode = 600
- [ ] passphrase 檔存在且 mode = 600
- [ ] 兩個檔案**不在同一目錄**
- [ ] 解密能還原出明文且與原 token 字元完全相同
- [ ] 用解密後的 token 真的能登入目標服務 (例如打 /user 確認 login)
- [ ] 明文原始檔已被 shred 刪除 (`ls` 找不到)
- [ ] 兩個檔案都已被 grep 驗證,系統其他位置沒有副本 (`/tmp`、`~/.bash_history`、log 等)
- [ ] **MEMORY.md / USER.md 等被 sync 的檔不含真實 token**（2026-06-05 新增）— `grep -E 'ghp_[A-Za-z0-9]{36}|vcp_[A-Za-z0-9]{40,}|hms_[a-zA-Z0-9_]{20,}' ~/.hermes/memories/*.md` 應該無輸出

## 與其他元件的關係

- **GPG / gh CLI 試誤教訓**（如「`gh auth login --with-token` 對缺 read:org 的 token 失敗」「gpg 預設產出 mode 0644」等 L3 教訓）→ 已寫入 `~/.hermes/memories/MEMORY.md` 環境工具段落
- **整套記憶三層原則（L1/L2/L3 試誤處理、25KB 清理閾值、預設不寫、明示才寫）** → 見 `hermes-self-improvement` 技能「記憶管理三層試誤原則」段落
- **多帳號切換的觸發模式**（主帳號 `hoonsoropenclaw`、備用帳號 `hoonsor`、「特別說才切、做完自動切回」）→ 寫入 `~/.hermes/memories/USER.md`「GitHub 帳號切換偏好」
- **Cron secret leak 完整修復**（2026-06-05 新增） → `references/cron-secret-leak-scrub.md`（本 skill 內）
- **cron-job-health-monitor**（2026-06-05 新增 skill）→ `~/.hermes/skills/devops/cron-job-health-monitor/` 提供 cron 失敗自動分類 + 修復指引
- **portal-401-troubleshoot** v1.2.0（2026-06-05 新增 Step 5.5）→ 處理 .env.local 多行陷阱

## 參考

- OpenPGP S2K 參數:https://www.gnupg.org/documentation/manuals/gnupg/OpenPGP-Options.html
- AES-256 安全分析:截至 2026 沒有量子電腦以外的實際攻擊
- shred 行為限制:https://unix.stackexchange.com/questions/536293/why-is-shred-less-secure-on-ssds
- 完整 cron secret leak 修復 SOP：`references/cron-secret-leak-scrub.md`（本 skill 內）
- Session-specific 細節信號（環境細節、sandbox 遮罩觸發表、端到端驗證指令集、與 Vercel/GitHub API 互動陷阱、何時不該用這個 skill）：見 `references/session-signals.md`
- 小型工作流（memory 膨脹控制、token 對話禮儀、跨 session 重用流程）：見 `references/workflows.md`
- GitHub Push Protection 文檔:https://docs.github.com/code-security/secret-scanning/working-with-secret-scanning-and-push-protection
- bfg-repo-cleaner:https://rtyley.github.io/bfg-repo-cleaner/
