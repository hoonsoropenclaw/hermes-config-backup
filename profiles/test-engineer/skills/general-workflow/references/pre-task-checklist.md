# Pre-Task Checklist（任務開始前 SOP）

> **建立時間**: 2026-06-07
> **建立原因**: 使用者回饋赫米斯「有時候不主動撈 trial-and-error 就開始做事、出事才後悔」
> **使用時機**: **每個任務第一個 tool call 之前必跑**
> **更新**: 2026-06-07 加入 Step 6（驗證 compact summary 內的事實 — 2026-06-07 compact 內 hallucinated SHA 4a8b3f3 事件）

---

## 為什麼需要這個 checklist

LLM 預設會**直接開始做事**（patch / terminal / execute_code），但**有時候任務類型屬於「赫米斯過去踩過雷的類型」**。如果先看 trial-and-error 該分類，可能提早 10 個 tool call 發現問題。

**另外**：context compaction summary 內的「事實」（commit SHA / PR 編號 / URL）**可能是 LLM 編造的**。新 session 開始時必須驗證，不能憑敘事。

**觸發情境（任一符合就跑 checklist）**:
- 使用者訊息含 vercel / deploy / Vercel / CDN / git push / GPG / rclone / Drive / token / .env / API key / execute_code / browser / playwright / hermes cron / bash script
- 使用者問「X 可以不備嗎」「X 是 Y 還是 Z」「X 真的能砍嗎」
- 任務涉及「寫檔」「跑 script」「deploy」「git push」「加密」「備份」「cron」「自動部署」
- 新 session 開始 + compaction summary 內有具體 ID（commit SHA / PR / issue / deployment）

---

## Checklist 7 步

### Step 1: 掃使用者訊息找 HARD TRIGGER 詞（5 秒）

把使用者訊息快速掃一次，找以下任一組：
- **部署類**: vercel / deploy / Vercel / CDN / cloudflare / github pages
- **Git 類**: git push / filter-branch / BFG / GH013 / GH001 / force push / large file
- **加密類**: GPG / gpg / encrypt / decrypt / 簽章 / passphrase
- **備份類**: rclone / Drive / 備份 / backup / purge / crypt
- **環境變數**: token / .env / API key / process.env
- **Python sandbox**: execute_code / python3.12 / subprocess / sandbox
- **Python 套件裝**: pip install / uv venv / uv pip / pyproject.toml / hatchling / wheel / editable install / force-include
- **瀏覽器**: browser / playwright / headless / camofox
- **Bash**: for f in / 2>&1 / pipefail / set -e / 2>/dev/null
- **Hermes**: hermes cron / hermes status / config / gateway
- **平台 CLI 認證 / cookies**: cookies / Cookie-Editor / X.json / reddit.json / twitter-cli / rdt-cli / yt-dlp / agent-reach / 小紅書 / 微博 / 雪球
- **YouTube / 影片下載**: yt-dlp / 字幕 / 抓 YouTube / B站下載 / Bilibili

**Step 2 載入對應分類**（本次對話 2026-06-08 新增映射）:
- 命中「Python 套件裝」→ `python-sandbox.md`（uv venv 無 pip、force-include 衝突、editable fallback、venv CLI PATH、yt-dlp JS runtime、f-string sanitization 6 條）
- 命中「平台 CLI 認證 / cookies」→ `headless-cookie-import.md`（Twitter/Reddit/YouTube/小紅書/微博/雪球 SOP）

### Step 2: 命中就 `skill_view` 對應分類（10 秒）

```python
# 範例
skill_view(name='trial-and-error', file_path='references/by-category/vercel-deployment.md')
skill_view(name='trial-and-error', file_path='references/by-category/gh-cli-and-github.md')
# 一次可載多個分類
```

### Step 3: 判斷性問題必查備份 pitfalls（5 秒）

如果使用者問「X 可以不備嗎」「X 是 Y 還是 Z」「X 真的能砍嗎」：
```python
skill_view(name='trial-and-error', file_path='references/by-category/hermes-backup-design-pitfalls.md')
# 找 Rule 12（rebuild 判斷要先查）
```

### Step 4: 評估任務類型（10 秒）

判斷這個任務屬於哪一類:
- **新功能**: 可以開始
- **既有專案修改**: 先 `git status` + `git log --oneline -5` 確認狀態
- **部署類**: 確認 .env 有 token、看 trial-and-error 的部署 SOP
- **加密類**: 確認 gpg agent 狀態、看 GPG 條目
- **備份類**: 看 Rule 12（rebuild 判斷）

### Step 5: 列「可能踩雷的 3 個點」（10 秒）

每個任務開始前，**強制**用 `todo` 工具列 3 個「這個任務可能踩到 trial-and-error 哪幾條」：
```python
todo([
    {'id': '1', 'content': '看 trial-and-error 的 vercel-deployment.md', 'status': 'in_progress'},
    {'id': '2', 'content': '確認 .env 有 VERCEL_API_TOKEN', 'status': 'pending'},
    {'id': '3', 'content': 'git status 確認 main 是 clean', 'status': 'pending'},
])
```

### Step 6: 🚨 驗證 context compaction summary 內的「事實」（5 秒，2026-06-07 新增）

**新 session 開始時,如果 compaction summary 提到具體 ID**:
- **commit SHA**（`abc1234` 形式）→ 第一個動作必是 `git log --oneline -5` 或 `git reflog` 確認真的存在
- **PR 編號**（`#1234` 形式）→ `gh pr view 1234` 確認存在
- **issue 編號** → `gh issue view 1234` 確認存在
- **deployment ID**（`dpl_xxx` 形式）→ Vercel API `GET /v13/deployments/{id}` 確認存在
- **檔案路徑** → `ls` 確認存在
- **使用者名稱 / 帳號** → 確認還有效

**為什麼需要這條**（2026-06-07 案例）:
前次 session 結束前 commit SHA `4a8b3f3` 已被 compaction summary 記錄為事實。**新 session 一開始引用這個 SHA 當作事實處理,30 分鐘後才發現 git reflog 根本沒有這個 commit**。LLM 編造的 SHA 是 hex 格式,看起來合法,但不是事實 — compact summary 把 hallucinated 細節「洗白」成了事實。

**解法 SOP**:
```bash
# 任務開始前（特別是涉及「前次 session 做的修改」）
git log --oneline -5                          # 確認 SHA 真實
git reflog | head -5                          # 確認所有 commit 歷史
gh pr list --state all --limit 5              # 確認 PR 編號真實
gh issue list --limit 5                       # 確認 issue 編號真實
ls /path/to/file                              # 確認檔案存在
```

**If→Then**:
- **If** compaction summary 提到 commit SHA **Then** 第一個 action 必是 `git log` 驗證
- **If** 驗證發現 SHA 不存在 **Then** 立即告知使用者「前次提到的 SHA 找不到、實際 SHA 是 X」,**不要**繼續敘事前次的故事
- **If** 發現前次 commit 真的存在但跟 compact summary 寫的不同 **Then** 告知使用者實際 SHA + 重新跑後續驗證
- **If** compact summary 提到「已 push」「已 deploy」 **Then** 必查 `git ls-remote origin` + Vercel API,**不要**直接接受

### Step 7: 開始第一個 tool call

**前 6 步完成後**才開始 patch / write_file / terminal / execute_code。

---

## 違規後果

- **跳過 Step 1-2 直接做事**: 信任扣分（使用者審查會發現「為什麼一開始不查」）
- **跳過 Step 6 接受 compact summary 內的 hallucinated 細節**: **嚴重違規**,30 分鐘後使用者會回報 bug,但實際上根本沒做過那個修改
- **第 5 個 tool call 內遇到「看起來以前踩過的雷」症狀**: **立即停止、回頭載入 trial-and-error**

---

## 範例: 任務開始前的正確流程

```python
# 使用者訊息：「請部署 hermes-cli-reference 新版到 Vercel」

# Step 1: 掃觸發詞 → 命中「Vercel」「部署」
# Step 2: 載入
skill_view(name='trial-and-error', file_path='references/by-category/vercel-deployment.md')
# → 看到 7 條踩雷紀錄,特別是「.env 是 token 唯一可靠來源」、「部署成功 200 ≠ 使用者打得開」、「GitHub push 沒觸發 Vercel auto-deploy」

# Step 3: 不是判斷性問題,跳過
# Step 4: 既有專案修改,先 git status
terminal(command="cd ~/permanent-projects/hermes-cli-reference && git status && git log --oneline -3")

# Step 5: 列可能踩雷的點
todo([
    {'id': '1', 'content': '✅ 已看 vercel-deployment.md (7 條)', 'status': 'completed'},
    {'id': '2', 'content': '確認 .env 有 VERCEL_API_TOKEN', 'status': 'in_progress'},
    {'id': '3', 'content': 'git push 後必須用 Vercel API 確認 deployment 觸發', 'status': 'pending'},
    {'id': '4', 'content': '部署後等 5 分鐘讓 CDN 失效 + 用 production URL 驗證', 'status': 'pending'},
])

# Step 6: 如果 compact summary 提到 commit SHA → 必驗證
# (新 session 一開始就應該跑,不要等用到才查)
terminal(command="cd ~/permanent-projects/hermes-cli-reference && git reflog | head -10")

# Step 7: 開始第一個 tool call（patch / 改檔案）
```

---

## 跟「無盡學習系統 v1.0」的關係

- 這份 checklist 是 P0「確保不停止」+ P1「讓學習成果真正有用」的延伸
- 把「學習」從「被動回憶」變成「主動檢查」
- 跟 metacognitive-learner skill 互補：那個負責「寫 SOP」、這個負責「用 SOP」

---

## If→Then 規則彙整

- **If** 使用者訊息含 vercel / deploy 任一字 **Then** 第一個 tool call 必是 `skill_view(vercel-deployment.md)`
- **If** 使用者訊息含 token / .env 任一字 **Then** 第一個 tool call 必是 `skill_view(secrets-and-env.md)` + 確認 .env 存在
- **If** 使用者訊息含 git push / GH013 任一字 **Then** 第一個 tool call 必是 `skill_view(gh-cli-and-github.md)`
- **If** 使用者訊息含 pip install / uv venv / uv pip / pyproject.toml / hatchling / wheel / editable install / force-include 任一字 **Then** 必載入 `python-sandbox.md`（2026-06-08 新增 — 6 條踩雷,uv venv 無 pip、force-include 衝突、editable install fallback 等）
- **If** 使用者訊息含 cookies / Cookie-Editor / X.json / reddit.json / twitter-cli / rdt-cli / yt-dlp / agent-reach / 小紅書 / 微博 / 雪球 任一字 **Then** 必載入 `headless-cookie-import.md`（2026-06-08 新分類 — N100 headless 平台 CLI 認證 SOP）
- **If** 任務是「部署網站」**Then** todo 必含「驗證 production URL 使用者打得開」這一條
- **If** 任務是「改既有檔案」**Then** 必先 `git status` 確認 working tree clean
- **If** 任務是「加密 / 簽章」**Then** 必先 `gpg --list-keys` 確認 key 存在
- **If** 看到 compact summary 提到具體 ID（commit SHA / PR / issue / deployment）**Then** 第一個 action 必是驗證該 ID 真實存在

## 更新記錄

- 2026-06-07: 初版建立,根據 hermes-cli-reference 搜尋「更新」沒結果事件
- 2026-06-07: 加入 Step 6（驗證 compact summary 內的事實）— 2026-06-07 赫米斯 hallucinated commit SHA 4a8b3f3 事件,compact summary 內被當作事實繼承
- 2026-06-08: Step 1 觸發詞清單擴充「Python 套件裝」+「平台 CLI 認證 / cookies」+「YouTube / 影片下載」3 組(2026-06-08 agent-reach 完整安裝對話實際命中,未來 session 接到同類任務必載入對應 trial-and-error 分類)
- 2026-06-07: 初版建立,根據 hermes-cli-reference 搜尋「更新」沒結果事件
- 2026-06-07: 加入 Step 6（驗證 compact summary 內的事實）— 2026-06-07 赫米斯 hallucinated commit SHA 4a8b3f3 事件,compact summary 內被當作事實繼承
