# 跨分類執行 SOP（Cross-Cutting Execution SOPs）

以下 SOP 橫跨多個 by-category 分類，屬於「改動某一個檔案時的標準作業流程」。建立於 2026-06-06 session，源於 cron model 改動、.env 加入新 provider key 的實際操作。

---

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
- ❌ 把 key 寫到註解行（`# DEEPSEEK_API_KEY=...`） → 完全不會被讀
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
