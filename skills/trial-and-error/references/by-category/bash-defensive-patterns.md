# Bash 函式設計陷阱

> 觸發:寫 bash 函式要把結果傳給外層、定義函式內印 log、寫 production script
> 建立時間: 2026-06-07
> 條目數: 3

---

### Bash 函式內 echo 會被當成回傳值汙染 $(func) 結果

**發現時間**: 2026-06-07

**觸發情境**: 寫 `hermes-secrets-encrypt.sh` 內 `collect_secrets()` 函式,函式內用 `echo -e "  found .env"` 印 log,外層用 `tar_path=$(collect_secrets)` 抓 tar 路徑,結果 `tar_path` 變成包含所有 log 訊息的 multi-line 字串、gpg 找不到檔案

**症狀**:
```
gpg: can't open '  \x1b[0;36mfound\x1b[0m .env\n  \x1b[0;36mfound\x1b[0m auth.json\n
[0;36mPacking secrets -> /path/to/secrets-bundle-XXX.tar\n[0;32mOK: Packed 32K / 3 files[0m\n
/path/to/secrets-bundle-XXX.tar': No such file or directory
```

**根因**:
- bash 函式**沒有 return value 概念**,函式「回傳」是 echo 到 stdout 的最後一行
- `func() { echo "log1"; echo "log2"; echo "$result"; }` 被 `var=$(func)` 抓的時候,`var` 是 `"log1\nlog2\n$result"` 整串
- `echo -e` 還會把 ANSI 跳脫碼（`\x1b[0;36m` 之類）展開進字串
- gpg 收到這個「路徑」當然找不到檔案

**解法**:
1. **所有 log 訊息 echo 到 stderr**（`>&2`）,只有真正的回傳值走 stdout
2. 或**用獨立變數**（全域或命名變數）而非依賴 stdout

```bash
# 正確寫法
collect_secrets() {
  mkdir -p "$STAGING" >&2
  local file_names=()
  for f in .env auth.json; do
    [[ -f "$HERMES_HOME/$f" ]] && file_names+=("$f")
    echo "  found $f" >&2   # ← 關鍵:>&2
  done
  echo "$tar_path"          # ← 只有這行走 stdout
}

tar_path=$(collect_secrets)  # 現在 tar_path 是乾淨的路徑
```

**預防**:
- 寫任何會被 `$(func)` 或 backtick 包起來的函式時,**所有 log 改去 stderr**
- 函式最後一行 `echo` 才是回傳值,**前面所有 echo 都要 `>&2`**
- 或乾脆用 `declare -g result="..."` 把結果存全域變數

**驗證**:
```bash
test_func() { echo "log" >&2; echo "real_return"; }
result=$(test_func)
# 應該:result=real_return、log 印到螢幕
echo "[$result]"  # [real_return]
```

**相關條目**: 無

---

### bash `for f in glob 2>/dev/null` 在 for 結構內不支援 stderr 重導

**發現時間**: 2026-06-07

**觸發情境**: 想掃描 `~/.hermes/*.token`、`*.gpg` 等 secret 檔,用 `for f in "$HERMES_HOME"/*.{token,gpg,key} 2>/dev/null` 避免 glob 沒匹配時報錯

**症狀**:
```
syntax error near unexpected token `2'
```

**根因**:
- bash 的 `for` 變數展開 (`for x in word;`) 不支援 redirect syntax
- `2>/dev/null` 在 `for` 結構中**只**能放在 `; do` **後面**,但這樣的話 stderr 還是會在 for 內每個 iteration 印出
- bash 4+ 對 `for x in ...; do` 的 token 化階段就把 `2>/dev/null` 當獨立 token、語法錯

**解法 1（推薦）— 用 nullglob**:
```bash
shopt -s nullglob   # 沒匹配時 glob 展開成空字串、不報錯
for f in "$HERMES_HOME"/*.token "$HERMES_HOME"/*.gpg; do
  [[ -f "$f" ]] || continue
  echo "$f"
done
shopt -u nullglob   # 還原
```

**解法 2 — 先存進 array**:
```bash
files=( "$HERMES_HOME"/*.token ) 2>/dev/null
for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  echo "$f"
done
```

**預防**:
- bash `for ... in ...; do` **不能**接 `2>/dev/null` 或 `>/dev/null`
- 改用 `shopt -s nullglob` 或先存 array
- 或用 `if [[ -e "$pattern" ]]; then for f in $pattern; do ...; done; fi` 模式

**驗證**:
```bash
bash -n script.sh  # 確認無語法錯誤
shopt -s nullglob
for f in /nonexistent/*; do echo "$f"; done  # 不報錯、什麼都沒印
```

**相關條目**: 無

---

### bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功

**發現時間**: 2026-06-07

**觸發情境**: 寫 `hermes-backup-v4.sh` 的 push 步驟、用 `if git push ... | grep -qE "(GH013|error:)"` 想同時看輸出 + 判斷有沒有錯

**症狀**:
- `git push origin main` 真的失敗（remote 拒絕）
- 但腳本顯示「✓ GitHub push 成功」、整個備份流程 exit 0
- 後來單獨跑 `git push` 才看到「`! [remote rejected] main -> main (pre-receive hook declined)`」
- 這個 bug 讓**我以為已經把 trial-and-error 條目推上 GitHub、實際上完全沒推**（浪費一個 session 才發現）

**根因**:
- bash 預設 `pipefail` 沒開的話、pipe 的 exit code 取決於**最後一個**指令
- `git push ... 2>&1 | grep -qE "..."` 的 exit code 是 `grep` 的（0=找到、1=沒找到）
- 就算 `git push` 失敗（exit 1）、`grep` 沒匹配到也會回 1
- `if 1; then ... fi` 在 bash 內是 false、不會跳到 err 分支
- 但**輸出已經被 grep 過濾掉**、完整錯誤訊息看不到

**解法**（兩種）：

**解法 1 — 用變數存輸出、別用 pipe**（推薦）：
```bash
local push_output
push_output=$(git push origin main 2>&1) || true   # 一定要 || true、否則 set -e 會殺掉腳本
echo "$push_output" | tail -10                       # 顯示完整錯誤

# 分別檢查各類錯誤
if echo "$push_output" | grep -qE "GH013.*secrets"; then
  err "觸發 GH013"
  return 1
fi
if echo "$push_output" | grep -qE "GH001.*Large files"; then
  err "檔案 > 100MB"
  return 1
fi
if echo "$push_output" | grep -qE "(\[remote rejected\]|error:|fatal:)"; then
  err "其他錯誤"
  return 1
fi
ok "GitHub push 成功"
```

**解法 2 — 開 `set -o pipefail`**（但要小心副作用）：
```bash
set -o pipefail   # pipe 中任一指令失敗就視為 pipe 失敗
if git push ... 2>&1 | grep -qE "error:"; then  # 現在 push 失敗就會跳進 err
  err "push failed"
fi
```
- 缺點：腳本其他 pipe 也會被影響、可能誤判
- 優點：不用 `|| true` 暫時關掉 set -e

**預防**:
- **任何「要判斷 pipe 中**前段**指令是否失敗」的場景、都要用**變數暫存**而不是 pipe
- 寫 `if X | Y` 之前先想「Y 失敗會讓我看起來 X 也成功嗎？」
- push/pull/sync 這類**外部副作用**的命令、**永遠**用變數接輸出、顯示完整給人看

**驗證**:
```bash
# 故意跑一個會失敗的指令
fake_command 2>&1 | grep -qE "anything"
echo "exit: $?"  # 1（grep 沒匹配）
# 但 fake_command 真的跑了、輸出被 grep 吃掉了
# 修正：
fake_command 2>&1 | tee /tmp/out | grep -qE "error"
echo "exit: $?"  # 還是錯的、要用變數
```

**If→Then**:
- **If** 寫 push / deploy / rm -rf / curl 之類**會改外部狀態**的腳本 **Then** 永遠用 `out=$(cmd) || true` 存輸出、別用 `cmd | grep`
- **If** 腳本顯示「成功」但 GitHub 沒收到 push **Then** 懷疑這個 bug、單獨跑 `git push` 看真實錯誤

**相關條目**: [[hermes-internal#自我審查：自我報告 ≠ 驗證（2026-06-06 確立）]]

---

### bash `[[ "$array[@]" "regex" =~ "pattern" ]]` 在 array expansion + regex 比對會炸

**發現時間**: 2026-06-07

**觸發情境**: 想檢查一個檔名是否已在 array 內,用 `[[ ! " ${file_names[@]} " =~ " $bn " ]]` 比對

**症狀**:
```
syntax error near unexpected token `2'
```
（報錯位置錯亂、有時指 line 85 實際是 line 89 的問題）

**根因**:
- `[[ ... =~ ... ]]` 內 **array 展開**（`${arr[@]}`）會把每個元素當作 regex 的一部分
- 元素含 regex meta char（`.`、`*`、`[`）就會把 regex 引擎搞壞
- bash 報錯 line 跟實際錯誤 line 差好幾行、難 debug

**解法 — 用 glob 風格比對**:
```bash
# 錯
if [[ ! " ${file_names[@]} " =~ " $bn " ]]; then

# 對（用 case 取代 [[ =~ ]]）
case " ${file_names[*]} " in
  *" $bn "*) ;;   # already in list
  *)
    file_names+=("$bn")
    ;;
esac
```

**預防**:
- 任何 array membership test **不要用 `[[ =~ ]]**、改用 `case` 或 explicit loop
- regex 比對在 bash 內有太多陷阱（quoting、glob、meta char escape）、能避就避
- 嚴格遵守：「`[[ =~ ]]` 只對純字串 regex 比對、不對 array」

**驗證**:
```bash
arr=(a b c)
case " ${arr[*]} " in
  *" b "*) echo "found" ;;
  *) echo "not found" ;;
esac
# 應該印 "found"
```

**相關條目**: 無


---

### Bash heredoc 內含 `${VAR:0:N}` 截斷會破壞 token 完整性(2026-06-07 Vercel 部署實戰)
**發現時間**: 2026-06-07
**觸發情境**: 部署 hermes-portal 想從 `.env.local` 抽 SUPABASE_URL 跟 Vercel 已設的比對
**症狀**:
- 寫 `echo "${SUPABASE_URL:0:30}..."` 在 shell 裡正常運作
- 但放進 heredoc(`cat << EOF ... EOF`)或 `python3 -c` 內,**`:` 後面被解讀為檔案路徑分隔符**或其他特殊字元
- 報 `syntax error near unexpected token`、`unexpected EOF` 等不明錯誤
- 結果:花 10 分鐘找「為什麼簡單的 echo 在 heredoc 裡壞掉」

**根因**:
- `${VAR:0:N}` 是 bash parameter expansion,只在一級 shell 解析
- heredoc 內部如果**已經經過一次變數展開**(如 `cat << EOF` 沒引號),會在錯誤的解析階段被切斷
- Python `subprocess.run` 內含 `f"..."` 跟 bash `${}` 混用也會壞

**修法**:
1. **用 `set -a; source .env; set +a;` 後用 `$VAR`** 取代字串截斷:
   ```bash
   set -a
   source /path/.env.local
   set +a
   echo "SUPABASE_URL: $SUPABASE_URL"
   echo "  length: ${#SUPABASE_URL}"  # 用 ${#} 取代 ${:0:30}
   ```
   `${#VAR}`(取長度)在 heredoc 內**不會**壞

2. **避免在 heredoc 內用 `${VAR:N:M}`**:
   - 改用 `cut -c1-30`、`head -c 30`、或 `python3 -c "print('$VAR'[:30])"`

3. **heredoc 加引號**:
   ```bash
   cat << 'EOF'  # 注意單引號,內部不展開變數
   literal text
   EOF
   ```

**If** → **Then** 規則:
- **If** 在 heredoc 內用 `${VAR:0:N}` 壞掉 **Then** 改用 `${#VAR}` 取長度、並在外面 set -a; source; set +a;
- **If** 截斷字串要 partial preview **Then** 用 `head -c 30 <<< "$VAR"` 或 `cut -c1-30 <<< "$VAR"`
- **If** 確認變數值不該被展開 **Then** heredoc 加 `<< 'EOF'` 單引號
- **If** 同時要 shell + python **Then** 不要混用 `$VAR` 跟 `f"{$VAR}"`,先設 env、再用 `os.environ['VAR']`

**已驗證**:
- 2026-06-07 部署 hermes-portal 時用 `set -a; source .env.local; set +a; echo "${SUPABASE_URL:0:30}..."` 直接壞掉
- 改用 `${#SUPABASE_URL}` 取長度(151、40、7)+ 顯示完整前 30 字元(用 head -c 30)成功比對 Vercel env

---

### `find -maxdepth N` 找不到東西時,要懷疑路徑寫法(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 使用者給 Windows 路徑 `Y:\permanent-projects\hermes-status-site`,在 Linux 找對應路徑
**症狀**:
- `ls -la /mnt/y` 回 no such file
- `ls -la /y` 回 no such file
- `ls -la /media/y` 回 no such file
- `find / -maxdepth 4 -name "hermes-status-site" -type d` 卻**什麼都沒找到**(明明存在於 /home/hoonsoropenclaw/permanent-projects/hermes-status-site)

**根因**:
- `/home/hoonsoropenclaw/` 是 **Tailscale 同步目錄**,對應到 Windows 的 `Y:\`(整個 home 目錄,不是 /mnt/y 之類的特定 mount)
- `find -maxdepth 4` 對 `/home/hoonsoropenclaw/permanent-projects/hermes-status-site` 來說:
  - `/`(depth 0)
  - `/home`(depth 1)
  - `/home/hoonsoropenclaw`(depth 2)
  - `/home/hoonsoropenclaw/permanent-projects`(depth 3)
  - `/home/hoonsoropenclaw/permanent-projects/hermes-status-site`(depth 4)
- 剛好 4 層,**在邊界**,Linux find 對 maxdepth 邊界處理不同版本略有差異

**修法**:
1. **加大 maxdepth**:`find / -maxdepth 6 -name "hermes-status-site" -type d`(給點 buffer)
2. **不用 maxdepth 限制**,直接全找:`find / -name "hermes-status-site" -type d 2>/dev/null | head -5`
3. **先懷疑 mount 路徑**:`mount | grep -i "y\|tailscale"` 看實際掛載點
4. **先 `ls /home/<user>/`** 看家目錄結構,Tailscale 同步的通常直接是家目錄

**If** → **Then** 規則:
- **If** 接到 Windows 路徑(`C:\`、`D:\`、`Y:\` 等) **Then** **先問使用者** Tailscale 同步對應到哪個 Linux 路徑,**不要**瞎猜 `/mnt/y`、`/y`、`/media/y`
- **If** 使用者說 Tailscale 同步到 home **Then** 直接用 `/home/<user>/...`
- **If** find -maxdepth 找不到明明存在的東西 **Then** 加大 maxdepth 或拿掉限制
- **If** 路徑懷疑是 Tailscale 同步 **Then** `ls /home/<user>/` 看家目錄,別從 `/mnt/*` 開始找

**已驗證**:
- 2026-06-07 `find / -maxdepth 4 -name "hermes-status-site" -type d` 回空
- 改用 `find / -maxdepth 5` 找到 `/home/hoonsoropenclaw/permanent-projects/hermes-status-site`
- 事後確認 Y:\ = /home/hoonsoropenclaw/(Tailscale 同步整個 home)

---

### `git reflog` 看不到其他分支的 reset 紀錄、只看到本地 HEAD 移動(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 想用 `git reflog` 找回 raphael-status-site 被某次 force push 砍掉的早期 commit
**症狀**:
- 跑 `git reflog` 只看到 `HEAD@{0}: commit: v2` / `HEAD@{1}: reset: moving to origin/main` / `HEAD@{2}: pull --no-rebase` / `HEAD@{3}: reset: moving to HEAD~1` 等
- **沒看到「force push 砍掉 css 的那次 commit」**
- 以為本地有 reflog 就能找回所有 commit,其實不行

**根因**:
- `git reflog` 是**本地 HEAD 的 ref log**,只在本地 repo 追蹤
- **force push** 後:
  - 遠端 history 被覆蓋,本地 `git fetch` 後也看不到
  - 但**本地的 reflog 還保留 force push 之前的 commit**(一段時間內,直到 git gc)
  - `git reset --hard origin/main` 會把 HEAD 指向新位置,**但舊 commit 物件仍在 reflog 裡**
  - `git reset --hard origin/main` 再 `git pull --rebase` 跟遠端同步後,本地 reflog 會被新的 HEAD 移動覆蓋
- 重置多次後,reflog 只能看到「最近 reset 點」,**之前真正 force push 砍掉的 commit SHA 找不到**

**修法**:
1. **真正的救援是 GitHub reflog**(網頁 → repo → commits → 看「Recover lost commits」)
2. **本地找回**:
   - `git reflog --all` 看所有 ref(包括分支、stash)
   - `git fsck --lost-found` 找 dangling commit
   - `git stash list` 看有沒有 stash
3. **如果已經 reset --hard 多次**,用 `git fsck --no-reflogs` 強制掃所有物件
4. **或直接放棄,從別的 source 撈**(GitHub raw URL、備份、其他 clone)

**If** → **Then** 規則:
- **If** 想找回 force push 砍掉的 commit **Then** **先看 GitHub 網頁 reflog**,不是本地 reflog
- **If** 本地 reflog 看不到早期 commit **Then** `git fsck --lost-found` 或 `git reflog --all`
- **If** 找不回 **Then** 用 `curl raw.githubusercontent.com/<owner>/<repo>/<old-commit-sha>/<path>` 撈舊版
- **If** 是重要檔案 **Then** 預防勝於治療,`git tag` 標記穩定版本(避免未來被 force push 蓋掉)

**已驗證**:
- 2026-06-07 `git reflog` 看不到 css 還在的早期 commit(96f0055 已經被砍了)
- 用 `curl raw.githubusercontent.com/hoonsoropenclaw/raphael-status-site/96f0055/css/styles.css` 撈回

---

### `execute_code` 5 分鐘 timeout 對 `npm install` 不夠(2026-06-07)
**發現時間**: 2026-06-07
**觸發情境**: 部署 hermes-portal 前用 `execute_code` 跑 `npm install` 預裝 node_modules
**症狀**:
- `execute_code` 報 `timeout`
- 5 分鐘過去,npm install 還在跑(393 packages,可能要 6-8 分鐘)
- `execute_code` 是 foreground,卡住 5 分鐘後強制中斷

**根因**:
- `execute_code` 預設 timeout = 300 秒(5 分鐘)
- Vercel 部署時 Vercel 會自己跑 `npm install`(6-9 秒,因為有 build cache)
- 我手動 `npm install` 想預裝是**多餘的**、反而造成 timeout

**修法**:
1. **不要預跑 npm install**,讓 Vercel build 時自己跑
2. **必須預跑時用 background**:
   ```bash
   # 跑在背景、看 log、不卡 foreground
   npm install &> /tmp/npm-install.log &
   ```
3. **或拆成多個小 step**(每個 < 5 分鐘)

**If** → **Then** 規則:
- **If** 部署 Vercel 專案 **Then** **不要**手動 `npm install`,讓 Vercel build 處理
- **If** 必須跑長時間命令(> 5 分鐘) **Then** 用 `terminal(background=true)`
- **If** 在 `execute_code` 跑命令 **Then** 確認 < 5 分鐘、否則用 background
- **If** 已經 timeout **Then** 檢查 process 是否還活著(`ps aux | grep npm`)、可能需要 kill

**已驗證**:
- 2026-06-07 `execute_code` 跑 `npm install` timeout,但 Vercel 部署時 6-9 秒就跑完(它有自己的 cache)
- 改用 `rm -rf node_modules` 後直接 `vercel --prod`,Vercel 自己處理依賴安裝

---

### cron 部署腳本 git push rejection 自我修復（2026-06-08）
**症狀**: `run_skill_stats.sh` 在 `git push origin main` 時失敗，錯誤：`Updates were rejected because the remote contains work that you do not have locally`。原因是 remote (a7b2c1b) 比 local main (edd2892) 更新。
**根因**: cron script 跑完後其他 process/cache 更新了 origin/main，導致 local main 落後。下次 cron 觸發時 local main 落後更多，形成惡性循環。
**解法**: 
1. `git fetch origin main` 抓最新遠端狀態
2. 比對 local HEAD vs origin/main — 若相同表示已同步（別的 worker 修好了）
3. 若落後，`git rebase origin/main` 自動合併（stats 是 CRON 產出，沒有需要保留的 local commits）
4. rebase conflict 時 `git rebase --abort` + `git reset --hard origin/main` + 重新執行 stats script
5. 最多重試 2 次後放棄（防止無限迴圈）
6. 整個流程包成 `deploy_with_git_recovery()` 函數
**預防**: 
- 任何 cron 部署腳本（hermes-status-site、備份上傳等）都要有 git recovery 機制
- `git push --force-with-lease` 比 `git push --force` 安全（不會蓋掉別人的 commit）
- Vercel deploy 失敗不阻斷 script exit（git push 成功才是關鍵）
**If→Then**: **If** `git push` rejection 且 local commits 不是用戶手動編輯 **Then** 自動 fetch + rebase + push（最多 2 次），不回頭問用戶
**相關條目**: [[hermes-backup-design-pitfalls#cron job 的 skills 陣列不能放 MCP 工具]]，[[vercel-deployment#vercel --prod 需要 --yes]]

---

### Python subprocess grep literal match vs regex（2026-06-08）
**症狀**: `subprocess.run(["grep", "^AGENT_API_KEY=***", str(env_path)])` — `***` 是 grep regex 的「任意字元」wildcard，但 shell `/bin/bash -c` 不展開它，結果變成搜尋字面 `AGENT_API_KEY=***`（三個 `*`），永遠找不到（因為實際值是 `0770415`），導致 `api_key=None` → `sys.exit(1)`。
**根因**: 
- `***` 在正則表達式 = 零或多個 `*`，不是「任意字元」的 wildcard
- shell 環境中 `***` 也不會展開（`echo ***` 不會列出所有檔案）
- 解決：直接用 Python 讀檔迭代，不用 `subprocess + grep`，完全繞過 shell/Grep regex 複雜度
**解法**: 
```python
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("AGENT_API_KEY=") or line.startswith("export AGENT_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
```
**預防**: 
- 任何 .env 讀取不用 subprocess，直接 Python file I/O
- 如果堅持用 grep，`grep -F` 是 literal match（`-F, --fixed-strings`），但要小心 pipe/quote 問題
**If→Then**: **If** 要從 `.env.local` 讀取變數 **Then** 用 Python file I/O 不用 subprocess + grep
**相關條目**: [[hermes-internal#eval-sync AGENT_API_KEY not found bug 修復（2026-06-08）]]
