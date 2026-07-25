# 跨分類執行 SOP（Cross-Cutting Execution SOPs）

以下 SOP 橫跨多個 by-category 分類，屬於「改動某一個檔案時的標準作業流程」。建立於 2026-06-06 session，源於 cron model 改動、.env 加入新 provider key 的實際操作。

## SOP-1: 改動 `~/.hermes/cron/jobs.json` 的 model / provider 欄位

**為什麼需要這個 SOP**：直接編輯 jobs.json 沒有內建備份；改錯 model id 或忘了驗證 key 存在，會讓 cron tick 失敗但沒人發現（因為錯誤被 `skipped` 標記而非 error）。

### 觸發情境
- 用 `hermes config set delegation.model X` 改全域 delegation
- 手動編輯 jobs.json 把某個 cron job 從繼承主 session 改成指定 model
- 新增 cron job（指定 model）
- 移除 provider（要把該 provider 對應的所有 cron job model 改掉）

### 標準步驟

**Step 1 — 備份 jobs.json**
```bash
cp ~/.hermes/cron/jobs.json ~/.hermes/cron/jobs.json.bak.$(date +%s)
```

**Step 2 — 確認目標 provider 的 key 存在於 .env**
```bash
grep -iE "^<PROVIDER>_API_KEY=" ~/.hermes/.env | sed -E 's/=.{8,}$/=<set>/'
```
- 若 key 不存在 → 停止，要求使用者先補 key
- 若 base_url 是自訂的（非預設）→ 順便確認 `<PROVIDER>_BASE_URL` 也有設

**Step 3 — 改 model / provider**
- 手動編輯：用 Python 讀 → 改欄位 → 寫回去（不要用 `hermes cron edit --script` 對 no_agent jobs，那個有 bug）
- 改完驗證：把整個 jobs.json `cat` 出來看目標 job 段落，確認 `model`、`provider` 欄位正確

**Step 4 — 重啟 gateway（如果 cron 是透過 gateway 觸發）**
```bash
hermes gateway restart
```
- 不是所有 cron job 都需要重啟，但改 model 屬於「啟動時讀一次」的配置 → 重啟最保險

**Step 5 — 觀察下次 tick**
- `hermes cron list --all` 看到 `Last run: ok` 就代表成功
- 第一次失敗不要慌，可能是 provider 還沒 warm-up，第二次 tick 會好

### 常見錯誤
- ❌ 改完沒備份 → 出問題時 jobs.json 直接壞掉
- ❌ 沒驗證 key 存在 → cron tick 用錯誤 model，錯誤被 `skipped` 標記（**極難發現**）
- ❌ 沒重啟 gateway → 舊 model 仍生效，新設定沒被讀到
- ❌ 用 `hermes cron edit --script` 改 no_agent jobs 的 script 路徑 → bug，會把 script path 寫到 prompt 欄位

### 驗證清單
- [ ] 備份檔存在於 `~/.hermes/cron/jobs.json.bak.<timestamp>`
- [ ] 目標 provider key 在 .env
- [ ] jobs.json 內 model/provider 欄位正確（cat 確認）
- [ ] gateway 已重啟
- [ ] 下次 tick 顯示 ok

---

## SOP-2: 改動 `~/.hermes/.env`（新增 / 修改 / 移除 API key）

**為什麼需要這個 SOP**：.env 是明文（即使 mode 600）、任何寫入動作都會被 shell history 記錄、改錯一個 key 可能影響其他 key 的讀取。

### 觸發情境
- 新增 provider 的 API key（DEEPSEEK_API_KEY、OPENROUTER_API_KEY 等）
- 撤銷舊 key 後換新 key
- 移除不再使用的 key
- 批量更新多個 key

### 標準步驟

**Step 1 — 確認 .env 當前權限**
```bash
stat -c "%a" ~/.hermes/.env
```
- 必須是 `600`（`-rw-------`），其他權限都不安全
- 不對的話：`chmod 600 ~/.hermes/.env`

**Step 2 — 取得新 key 的方式**

**安全做法（推薦）**：
```bash
# 1. 使用者把 key 寫到暫存檔
echo '<new-key>' > /tmp/new_key.txt && chmod 600 /tmp/new_key.txt

# 2. 赫米斯讀取並寫入 .env（用 patch 工具，不開 cat）
# 3. 赫米斯刪除暫存檔
shred -u -z -n 3 /tmp/new_key.txt
```

**不安全做法（避免）**：
- ❌ 使用者直接在對話裡貼 key → 進 prompt history、無法收回
- ❌ 赫米斯 `cat ~/.hermes/.env` 顯示完整內容 → 雖然 mode 600 擋其他人，但 prompt history 還是有
- ❌ 寫 .env 時用 `echo "KEY=value" >> ~/.hermes/.env` shell heredoc → 進 shell history

**Step 3 — 改 .env**
- 用 patch 工具（不是 sed），因為 patch 有 fuzzy matching 比較安全
- 一次只改一個 key，避免一次寫壞多個
- 改完用 `grep` 驗證：
  ```bash
  grep -iE "^<KEY_NAME>=" ~/.hermes/.env | sed -E 's/=.{8,}$/=<redacted>/'
  ```

**Step 4 — 確認其他 key 沒被影響**
- 改之前先 `wc -l ~/.hermes/.env`
- 改完再 `wc -l`，行數變化要在預期內（+1 / -1 / 0）

**Step 5 — 重啟需要讀 .env 的服務**
- hermes CLI → 退出重啟
- hermes gateway → `hermes gateway restart`
- cron → 大部分 cron job 是 no_agent script 不需要重啟，但 model-driven job（metacognitive-learner-24h）需要 gateway 重新讀

### 常見錯誤
- ❌ 改 .env 後沒重啟 gateway → 舊 key 仍生效，新 key 沒被讀到
- ❌ 一次寫多個 key 結果其中一個格式錯 → 所有 key 都壞
- ❌ 把 key 寫到註解行（`# DEEPSEEK_API_KEY=***`） → 完全不會被讀
- ❌ 忘了 `chmod 600` → 任何同主機使用者都可讀

### 驗證清單
- [ ] .env 權限 600
- [ ] 暫存檔已 shred 刪除（若使用暫存檔流程）
- [ ] 改完 grep 驗證 key 存在
- [ ] .env 行數變化符合預期
- [ ] 已重啟相關服務

---

## SOP-3: 改動 `~/.hermes/config.yaml` 的 model / provider 設定

**為什麼需要這個 SOP**：config.yaml 是 Hermes 啟動時一次讀完的，mid-session 改不會生效；改錯 model id 會讓整個 session 開不起來。

### 觸發情境
- 切換主 session model（從 minimax-M3 換到 M2.7）
- 設定 delegation.model（讓 sub-agent 走特定 model）
- 新增 auxiliary model（vision、compression）

### 標準步驟

**Step 1 — 確認 provider 在 hermes 支援清單內**
- 查 `hermes-agent` skill 的 Providers 段落
- 確認 base_url 格式正確（OpenAI-compatible / Anthropic-compatible）

**Step 2 — 備份 config.yaml**
```bash
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date +%s)
```

**Step 3 — 改 model 區塊**
- 用 patch 工具，不用 write_file 整個覆蓋（config.yaml 有 13K+ 內容）
- 一次只改一個區塊（model / delegation / auxiliary）
- 改完驗證：把該區塊 cat 出來看

**Step 4 — 完全重啟**
- 退出當前 hermes session（不是 /reset，是整個退出）
- 重啟 gateway（`hermes gateway restart`）
- 開新 session

**Step 5 — 驗證新設定生效**
- 開新 session 後下 `/model` 或 `hermes model`，確認顯示正確

### 常見錯誤
- ❌ mid-session 改 config.yaml → 不生效但不報錯
- ❌ 改了 model 但忘了重啟 → 行為沒變
- ❌ 整個 write_file 覆蓋 config.yaml → 註解、格式化、其他區塊全沒了

### 驗證清單
- [ ] 備份存在
- [ ] provider / model 都在 hermes 支援清單內
- [ ] 改完完全重啟 hermes
- [ ] 開新 session 後 `/model` 顯示正確

---

## SOP-5: 用 `patch` 工具編輯檔案（避免 cascade damage）

**為什麼需要這個 SOP**：`patch` 工具用 fuzzy 9 種策略比對 `old_string`，如果 `old_string` 太短或太常見（例如只抓 `- **` 開頭的 markdown 條目），fuzzy 會**匹配到錯誤的段落**——匹配成功後**默默把新內容插入，但原本要保留的內容也跟著被替換掉**。2026-06-09 trial-and-error SKILL.md 案例：

```python
# old_string 過短（只抓一個 list prefix）
old_string = "- **卸載前用 `ps -o ppid=` 查 PPID 判斷..."
# patch 成功，diff 看起來正常
# 但其實前一段的 L3 條目「卸載前用 ps -o ppid=」被替換成 opt-out 相關內容
# 因為 fuzzy 找到了「**卸載前用**...」開頭的另一個條目
```

**根因**：`patch` 的 fuzzy 匹配是**有時太聰明**的——給的 anchor 太短、會匹配到語意相近但不是你想找的那段。**整個段落被 silently 替換**。

### 標準步驟

**Step 1 — `old_string` 必須包含足夠上下文**（**至少 3-5 行**或**整個條目**）
```python
# ❌ 錯：只抓開頭
old_string = "## 觸發時機"

# 對：抓整個段落的開頭到結尾
old_string = "## 觸發時機\n\n更新任何 ...\n\n## 標準步驟"
```

**Step 2 — 預覽 diff（看 patch 回傳的 `diff` 區塊）**
每次 `patch` 跑完，**先讀 diff** 確認有 `+` 也有 `-` 對應到你預期的範圍。如果只有 `+` 沒有 `-` 對應的內容（特別是「你沒預期要刪的部分」），**立刻 revert**。

**Step 3 — 重要檔案編輯前先備份**
```bash
cp ~/.hermes/memories/MEMORY.md ~/.hermes/memories/MEMORY.md.bak.$(date +%s)
```
備份的存在不是心安的——是真的要能在 1 分鐘內 `cp` 回去。

**Step 4 — 大段落修改優先用 write_file 重寫整個檔案**
- 如果要改的範圍超過 50% 的檔案 → 用 `read_file` 讀全 → `write_file` 整個重寫
- 避免多次 `patch` 串接（每步都增加風險）
- 重寫前**先 `cp` 備份**到 `*.tmp-pre-rewrite`

**Step 5 — 驗證 patch 結果**
```bash
# 比對行數
wc -l <file>
# grep 新內容
grep "<新內容關鍵字>" <file>
# grep 確認舊內容還在（如果有要保留的）
grep "<應保留內容>" <file>
```

### 常見錯誤
- ❌ `old_string` 只抓 anchor 開頭幾個字 → fuzzy 匹配到錯誤段落
- ❌ patch 成功就以為正確（不讀 diff）
- ❌ 多次 patch 串接（每步都增加風險）
- ❌ 改前沒備份
- ❌ 想用 `replace_all=true` 解決「找不到」問題 → 會把所有 anchor 全部替換、可能誤殺

### If→Then
- **If** 用 `patch` 改 trial-and-error SKILL.md / MEMORY.md / 任何 1KB+ 檔案 **Then** 必先備份 + `old_string` 包含至少 3-5 行上下文
- **If** patch 跑完看到 diff 有「沒預期要刪的內容」**Then** 立即 revert、用 read_file + write_file 重寫整段
- **If** `old_string` 在檔案裡有多個可能的 anchor **Then** 把 `old_string` 加長到 unique、避免 fuzzy 選錯

---

## SOP-6: 跨 profile 寫入 SKILL.md / persona.md（cross-profile soft-guard）

**為什麼需要這個 SOP**：Hermes 對「從 `default` profile 寫進其他 profile 的 `skills/` 或 `memories/`」有**軟防護**——會擋下並提示「Cross-profile write blocked by soft guard... To bypass this guard after explicit user direction, retry the call with `cross_profile=True`」。**2026-06-09 為 market-strategist / product-planner 寫專屬 skill 時直接撞到**。

### 觸發情境
- 從 `default` profile 跑 `hermes` 然後用 `write_file` 寫進 `~/.hermes/profiles/<其他-profile>/skills/...`
- 從 `default` profile 改其他 profile 的 `persona.md`
- 任何「主代理幫其他 profile 維護內容」的任務

### 標準步驟

**Step 1 — 確認使用者明確授權**
軟防護的訊息明確說「after explicit user direction」——代表需要使用者**當下這個任務**明確說「寫進去」「繞過」「OK」之類的指令。**不是**預設放行。

**Step 2 — 看到 soft-guard 訊息後用 `cross_profile=True` 繞過**
```python
# 第一次：被擋下（拿到 soft-guard 警告）
write_file(path="~/.hermes/profiles/market-strategist/skills/market-research/SKILL.md", content=...)

# 第二次：使用者確認 → 繞過
write_file(path="...", content=..., cross_profile=True)
```

**Step 3 — 仍要做 dry-run 驗證**
繞過不代表亂寫。**先**：
```bash
# 1. 確認目標 profile 存在
ls ~/.hermes/profiles/<name>/profile.yaml

# 2. 確認目標 skill 沒衝突
ls ~/.hermes/profiles/<name>/skills/<skill-name>/

# 3. 確認 default 那邊沒同名 skill（避免精瘦時誤刪錯份）
ls ~/.hermes/skills/<skill-name>/
```

**Step 4 — 寫完跑 hermes skills list 驗證**
```bash
hermes -p <target-profile> skills list | grep <skill-name>
# 看到 enabled 才算成功
```

### 常見錯誤
- ❌ 預設 `cross_profile=True` 開著（會繞過所有 profile 邊界）
- ❌ 看到 soft-guard 直接放棄、不跟使用者確認
- ❌ 跨 profile 寫完沒用 `hermes -p <target> skills list` 驗證（不同 profile 看到的 skills/ 不一樣）
- ❌ 把 default 的「全套 skill 概念」硬複製到新 profile（要記得跑精瘦 SOP）

### If→Then
- **If** 從 default 寫進其他 profile **Then** 必看到 soft-guard → 跟使用者確認 → 用 `cross_profile=True`
- **If** 跨 profile 寫入後看不到 skill 生效 **Then** 用 `hermes -p <target> skills list` 驗證、檢查 .no-bundled-skills marker
- **If** 跨 profile 寫入要「複製 default 的 skill」 **Then** 考慮「直接用 default 那份」或「跑精瘦 SOP 重新設計」

---

## SOP-7: 備份 / cron 異常診斷 3 件套（4 個 tool call 內定位問題）

**為什麼需要這個 SOP**：使用者說「02:01 左右怎麼會有 50 則備份訊息、每次都這樣嗎」這類**備份/cron 異常**問題，**不先實地查就憑印象答**會出大錯（2026-06-11 實證：表面是 cron runner 把 stderr 倒進 telegram、實際有 4 個獨立 bug 同時爆——rsync mkdir、gh 帳號、scheduler 沒截斷、v4 腳本缺早退）。這個 SOP 4 個 tool call 內可定位 90% 異常。

### 觸發情境
- 使用者說「今天 / N 天有 X 則備份訊息」「cron 又噴訊息」「備份失敗」「通知怪怪的」
- 任何 `last_status: error` 的 cron job 出現
- `~/.hermes/cron/output/<job_id>/` 有新檔但 telegram 沒通知
- 任何「為什麼 Y 跑出 X 行為、每次都這樣嗎」類問句

### 標準步驟（4 個 tool call）

**Step 1 — `hermes cronjob list` 找異常 job**
```python
cronjob(action="list")
```
- 看 `last_status: error` 的 job
- 抄下 `job_id`（`108ce8cabdfc` 格式）跟 `last_error` 開頭 5-10 字

**Step 2 — 撈完整 log（不要只信 `last_error`）**
```python
# 看 output 資料夾
ls -la ~/.hermes/cron/output/<job_id>/
# 撈最新一份 log
read_file(path=f"~/.hermes/cron/output/<job_id>/<最新 .md>", limit=200)
```
- **不要**直接用 `last_error` 欄位下結論（這個欄位可能被截斷、或根本是 stack trace 不是 root cause）

**Step 3 — 量化「今天才爆 vs 一直這樣」**
```python
# 對照**前幾天**同一個 job 的 log 大小
for f in ~/.hermes/cron/output/<job_id>/*.md:
    echo "$f: $(wc -c < $f) bytes"
```
- **模式 A**（今天才爆、不是「每次都這樣」）：找出今天的差異（新增檔案、配置改動、token 過期）
- **模式 B**（一直這樣、5 天都 > 100KB）：是架構問題（cron runner 行為、scheduler.py 沒截斷）→ 修源碼
- 這個量化**必須做**——使用者問「每次都這樣嗎」時不能憑印象答

**Step 4 — 找根因（從 log 往外追）**
- log 開頭的 `Script exited with code N` → 找腳本本身
- log 中段的 `error:` / `fatal:` 行 → 抄下檔路徑 + line number
- 撈 hermes-agent 源碼對應 line：`read_file(path="~/.hermes/hermes-agent/<file>", offset=<line-5>, limit=15)`
- **4 個 bug 同時爆的實況**：rsync mkdir 失敗 + gh 帳號不對 + scheduler 沒截斷 + v4 腳本早退缺失 → 4 條都是 L3 教訓、要分開 patch

### 常見錯誤
- ❌ 看到 `last_error` 開頭就直接下結論（這個欄位是 stack trace 不是 root cause）
- ❌ 不對照歷史 log 就答「每次都這樣嗎」（**這是 INTJ 使用者必問的、不能跳過**）
- ❌ 只修表面（修 cron 排程不讓它跑）而不是修根因（腳本 bug、runner 行為）
- ❌ 改完 Python 源碼（`scheduler.py`）忘了**重啟 hermes-gateway 才生效**
- ❌ 驗證 exit code 用 `bash script.sh | tail; echo $?` → `$?` 是 tail 的 0、不是 script 的

### 驗證清單
- [ ] 跑了 `cronjob list` 找到 `last_status: error` 的 job
- [ ] 撈了完整 log（不是只信 `last_error`）
- [ ] 量化了「今天 vs 前幾天」的 log 大小
- [ ] 找到根因（從 log 往外追到源碼 line）
- [ ] 列出所有 bug（**常見多個同時爆**、不要看到第一個就停）
- [ ] 修完驗證（**重跑 + 模擬失敗 + 還原**三步、不是只跑一次）

### If→Then
- **If** cron 異常 + 4 個 tool call 內沒定位 **Then** 停下來重新讀 log、不要繼續 debug——大概率在追錯方向
- **If** 看到 `last_error` 是 stack trace **Then** 抓 `error:` 開頭的那幾行、從那邊往外追
- **If** 量化後發現「今天才爆」**Then** 優先找今天的差異（git log、token 過期、配置改動）
- **If** 量化後發現「一直這樣」**Then** 是架構問題、修源碼、不要只在 surface patch
- **If** 改 hermes-agent Python 源碼（`scheduler.py` 等）**Then** 提醒「需要重啟 gateway」——Python 不像 bash 自動 reload

### 相關條目
- [[hermes-internal#notify_on_complete 是「最終確認」不是「即時 polling」]] — 為什麼 cron 跑完通知延遲 10-14 分鐘
- [[hermes-backup-strategy#案例 6：cron runner 把 191KB stderr 整份倒進 telegram 切 50 則（2026-06-11）]] — 這條 SOP 就是從那次故障歸納的
- [[bash-defensive-patterns#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]] — 為什麼驗證 exit code 別信 pipe 後面的指令

---

## SOP-4: 把 L3 抽象教訓寫進 trial-and-error skill（分流 SOP）

**為什麼需要這個 SOP**：metacognitive-learner skill 的 Phase 4 已於 2026-06-06 改為「L3 進 trial-and-error 對應分類、單次結果用 [TO_MEMORY] 區塊」，但「寫進去」這個動作本身的格式、檔名、分類判斷需要明確指引。

### 觸發情境
- metacognitive-learner cycle 結束，要落 L3 教訓
- 使用者說「把這個記起來」
- 從 MEMORY.md 清理出來的 L3 條目要搬家

### 標準步驟

**Step 1 — 判斷分類**

根據教訓涉及的**主工具/主題**，選對應分類檔：

| 教訓類型 | 目標檔案 |
|---|---|
| GPG / 加密 / 簽章 | `references/by-category/gpg-encryption.md` |
| gh CLI / GitHub API / 雙帳號 / token 操作 | `references/by-category/gh-cli-and-github.md` |
| Vercel CLI / API / 部署 / env 變數 | `references/by-category/vercel-deployment.md` |
| Python sandbox / token 字串遮罩 | `references/by-category/python-sandbox.md` |
| .env / 憑證管理 / GPG 加密佈局 | `references/by-category/secrets-and-env.md` |
| Playwright / headless browser / 反檢測 | `references/by-category/browser-automation.md` |
| cron jobs / config.yaml / hermes 內部架構 | `references/by-category/hermes-internal.md` |

**不確定時**：先看 `SKILL.md` 的「條目分類索引」段落，找到最接近的。

**Step 2 — 確認格式**

每個條目用以下結構：

```markdown
---

### [條目標題]
**症狀**: [使用者會看到什麼——具體錯誤訊息、命令列輸出]
**根因**: [為什麼會這樣——機制層次的解釋]
**解法**: [具體怎麼修——給指令碼或步驟]
**預防**: [未來怎麼避免]
**If→Then**（選填）: **If** [觸發條件] **Then** [動作]
**相關條目**: [[其他分類#條目標題]]
```

**Step 3 — 寫入**

用 patch 工具 append 到目標分類檔，**不要覆蓋既有內容**。

**Step 4 — 驗證**

- `wc -c references/by-category/<file>.md` 確認行數增加
- 讀最後 20 行確認新條目格式正確
- 若有跨分類關聯，在兩個分類檔的「跨分類關聯」段落互相加引用

### 常見錯誤
- ❌ 寫進 MEMORY.md（會污染、膨脹）
- ❌ 寫進不對應的分類檔（未來找不到）
- ❌ 條目太抽象（「gpg 怪怪的」）而不是症狀導向（「`gpg --symmetric --user alice` 卡住」）
- ❌ 解法只給方向（「重試一次」）而不是具體指令

### 驗證清單
- [ ] 分類檔選擇正確
- [ ] 條目格式符合症狀/根因/解法/預防四段
- [ ] 沒寫進 MEMORY.md
- [ ] 跨分類關聯有建立（如需要）
