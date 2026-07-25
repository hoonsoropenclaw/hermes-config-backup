# Hermes Internal: cron jobs, config.yaml, hermes internal architecture

---

### Scheduler `_get_script_timeout()` 優先級：jobs.json timeout_seconds 是無效的（2026-06-10）
**症狀**: `hermes-config-backup-daily` cron job timeout，jobs.json 已設 `timeout_seconds: 3600` 但仍 timeout after 600s
**根因**: Scheduler 的 `_get_script_timeout()` 有分層優先級：
1. `_SCRIPT_TIMEOUT` module patch（測試用）→ 不使用
2. `HERMES_CRON_SCRIPT_TIMEOUT` 環境變數（來自 `~/.hermes/.env`）→ **實際生效**
3. `config.yaml` 的 `cron.script_timeout_seconds` → fallback
4. `_DEFAULT_SCRIPT_TIMEOUT = 120` → 最终默认值

**jobs.json 的 `timeout_seconds` 欄位根本不被 Scheduler 讀取**——那是給任務本身用的，不是給 script timeout 的。這是一個長期的設計混淆。

**修復**（2026-06-10 驗證有效）：
```bash
# ~/.hermes/.env
HERMES_CRON_SCRIPT_TIMEOUT=600 → 3600

# ~/.hermes/config.yaml
cron:
  script_timeout_seconds: 600 → 3600
```

**驗證**（需重啟 Hermes 使 .env 改動生效）：
```bash
bash -c 'source ~/.hermes/.env && echo $HERMES_CRON_SCRIPT_TIMEOUT'
# 預期：3600
```

**預防**:
- **If** 要修復任何 cron script timeout **Then** 必須同時檢查 `.env` 和 `config.yaml` 的相關設定，jobs.json 的 `timeout_seconds` 無法覆蓋 Scheduler 的 timeout
- **If** 要對任何 cron job 調整 timeout **Then** 改 `~/.hermes/.env` 的 `HERMES_CRON_SCRIPT_TIMEOUT`，並同步更新 `config.yaml` 的 `cron.script_timeout_seconds`
- **If** 不確定哪個值正在生效 **Then** 在 `_get_script_timeout()` 的四層優先級中由上往下追蹤

**If→Then**: **If** cron job 仍 timeout 且 jobs.json 已設較高值 **Then** 檢查 `.env` 的 `HERMES_CRON_SCRIPT_TIMEOUT` 和 `config.yaml` 的 `cron.script_timeout_seconds`，兩者優先級都高於 jobs.json

---

### delegate_task 模型配置 Bug — delegation.model 被忽略（2026-06-09）
**症狀**: 在 `config.yaml` 的 `delegation.model` 設定了子 agent 專用便宜模型，但 subagent 仍繼承 parent model
**根因**: `delegate_task` 忽略 `config.yaml` 中的 `delegation.model` 設定，總是使用 parent session 的模型（Issue #11999, NousResearch/hermes-agent）
**代價**: cost tiering 完全失效 — 應該跑便宜模型的小任務消耗昂貴模型配額
**外部驗證**:
  - `curl -s https://github.com/NousResearch/hermes-agent/issues/11999` 確認 open bug
  - 官網文件 `hermes-agent.nousresearch.com/docs/user-guide/features/delegation` 說明 delegation.model 可配置，但實測被忽略
**workaround**: 透過 terminal 呼叫 `iris chat -q "..."` 可以正確使用設定的模型（hermes-agent spawning skill 提到的 workaround）
**預防**: **If** 要派遣大量 subagent 且想省成本，**Then** 先驗證 delegation.model 是否真的生效（不能只看文件）
**If→Then**: **If** 需要讓子 agent 用不同模型且正確吃到 delegation.model 設定 **Then** 先用 `delegate_task(goal="Report what model you are running on")` 驗證，目前 workaround 是用 terminal 取代 delegate_task 呼叫獨立 hermes 程序

### Background process 結束通知的 exit code 語意（2026-06-08）
**症狀**: 用 `terminal(background=true)` 啟動的 process 跑完，Hermes 自動通知 `Background process proc_xxx completed (exit code 143)`
**exit 143 = 128 + 15 = SIGTERM**：被 pkill / kill 送 SIGTERM 訊號的標準退出碼
**常見誤判**:
- 看到 `exit code 143` 以為 process 失敗 → 重新跑、浪費時間
- 實際是「我（或另一個指令）主動 kill 掉它的」,屬於預期內的正常 lifecycle
**判斷 SOP**:
```bash
# 1. 看 process 是不是自己 kill 的（grep 自己的指令紀錄）
history | grep -E 'pkill|kill.*<session_id>'
# 2. 看是不是 background 啟動的測試用 process
ps -ef | grep <proc 名> | grep -v grep
# 3. 看 log 最後 10 行有沒有 panic / unhandled exception
tail -20 <log 檔>
```
**If→Then**: **If** Hermes 通知 background process exit 143 **Then** 先用 SOP 判斷「是不是自己 kill 的」或「測試用 process 跑完正常結束」,不要直接當失敗重跑。**If** exit 124 = timeout、**If** exit 137 = SIGKILL（OOM 或強制）、**If** exit 130 = SIGINT（Ctrl+C）

### openclaw uninstall --all 不會清掉 systemd unit 殘檔（2026-06-08）
**症狀**: 跑 `openclaw uninstall --all --non-interactive --yes` 完、`~/.openclaw/` 刪了、service disable 了,但 `~/.config/systemd/user/` 還留著 `openclaw-gateway.service`、`mempalace-reintegrate.{service,timer}` 3 個 unit 檔
**根因**: `openclaw uninstall` 只清掉 `default.target.wants/` 跟 `timers.target.wants/` 內的 symlink,沒清 unit 檔本體（uninstall 邏輯 bug,不是預期行為）
**解法**: 手動 `rm -f ~/.config/systemd/user/openclaw-gateway.service ~/.config/systemd/user/mempalace-reintegrate.{service,timer} ~/.config/systemd/user/timers.target.wants/mempalace-reintegrate.timer ~/.config/systemd/user/default.target.wants/openclaw-gateway.service` + `systemctl --user daemon-reload` + `systemctl --user reset-failed`
**驗證**: `find ~/.config/systemd -name '*openclaw*' 2>&1 | head` 應為空
**If→Then**: **If** 跑前任拉斐爾 OpenClaw 套件代理反安裝後 `~/.openclaw` 已刪、但 `systemctl --user list-unit-files | grep openclaw` 仍出現 unit 檔 **Then** 那是 uninstall bug,手動 `rm` + `daemon-reload`,不要以為沒清乾淨重新跑 uninstall

### 常駐代理 sandbox HOME 隔離：絕對路徑可能繞路（2026-06-10）
**症狀**: 跑 `market-strategist chat -q "..." --cli` 後、agent 內部 `write_file ~/.hermes/handoff/<slug>/market-research.md` 顯示成功，但從 default session 跑 `ls ~/.hermes/handoff/<slug>/` 有時看到檔、有時看不到。`cat` 跟 `wc` 結果在 `terminal` 跟 `read_file` 之間不一致。
**根因**: hermes 的 profile sandbox 把 `HOME` 環境變數改成 `~/.hermes/profiles/<name>/home/`——所以 agent 內部看到的 `~/.hermes/handoff/...` **實際是 `~/.hermes/profiles/<name>/home/.hermes/handoff/...`**。但 hermes 對路徑的「轉換」行為不完美：有些工具（write_file、read_file）會把絕對路徑（`/home/.../harness/.../handoff/...`）解析到**主目錄的**真實位置，**繞過** profile 隔離；其他工具（terminal + 內部 ls）有時仍用隔離後的路徑。最終結果：**主目錄的同名檔案**跟 **profile 隔離目錄的同名檔案**可能並存，**寫入端點跟讀取端點可能不同**。
**驗證 SOP**:
```bash
# 1. 確認主目錄 handoff 真的有檔
ls -la ~/.hermes/handoff/<project-slug>/
# 2. 確認檔案大小、行數、章節
wc -lwc ~/.hermes/handoff/<project-slug>/<expected-file>.md
# 3. 確認 profile 隔離目錄下沒「幽靈副本」
ls -la ~/.hermes/profiles/<agent>/home/.hermes/handoff/ 2>&1 | head
```
**預防**:
- **跨 profile handoff pipeline**（用 `chat -q --cli` 跑常駐代理）時，**預期會有路徑混亂**——這不是 bug、是 sandbox 設計副作用
- 不要相信 agent 內部「檔案已寫入」的自報——**總是在 default session 用 `ls` + `wc` 二次驗證**
- 看到 agent 報「寫入成功」但 `terminal ls` 找不到 → 嘗試 `find ~/.hermes -name "<file>.md"`（搜全樹、不只主目錄）找出實際位置
- **If** `@專案` pipeline 跑完看不到預期檔 **Then** 跑 `find ~/.hermes -name "<project-slug>*.md"`、不要慌，這只是 sandbox 繞路
**If→Then**:
- **If** 常駐代理回報「寫入成功」但 default 看不到檔 **Then** `find ~/.hermes -name "<file>"` 找實際位置，再決定 `cp` 還是 `mv` 到 handoff 標準位置
- **If** handoff 目錄下看到**幽靈副本**（profile 隔離目錄裡的同名檔）**Then** `rm` 清掉、避免下次同檔名誤讀
- **If** 想讓 pipeline 100% 確定寫到主目錄 handoff/ **Then** 在 prompt 加「請用 `read_file` 確認寫入位置、或請用絕對路徑 `/home/<user>/.hermes/handoff/...`」、但**不要假設 prompt 能改 sandbox 行為**——驗證仍是必要
**相關條目**: [[#常駐 profile 精瘦 SOP（2026-06-09）]]、`~/.hermes/memories/references/sops/keyword-triggers-sop.md`「@專案 SOP 段」
### 精瘦 profile 的 keep 清單若帶註解、awk 取第一欄才不會 match 0（2026-06-10）
**症狀**: 寫 keep 清單時為了好讀,每行加 `# 註解` 說明(如 `anthropic-customer-research   # 客戶/消費者研究方法論`)。跑 `comm -12 <(ls skills/ | sort) <(sort keep.txt)` 比對,**結果顯示 0 個 match、要砍全部 194 個 skill**。
**根因**: `grep -v "^$"` 只過濾空行,不會去掉行尾的 `# 註解`。`comm` 比對時 `anthropic-customer-research   # 客戶/消費者研究方法論` 跟 `anthropic-customer-research` 視為不同字串。
**解法**: 比對前用 `awk '{print $1}'` 取第一個欄位(純 skill 名稱):
```bash
# 修正前(0 match)
grep -v "^#" keep.txt | grep -v "^$" | sort -u > keep.clean.txt
comm -12 <(ls skills/ | sort) <(sort keep.clean.txt)  # → 0 match

# 修正後(41 match)
grep -v "^#" keep.txt | grep -v "^$" | awk '{print $1}' | sort -u > keep.clean.txt
comm -12 <(ls skills/ | sort) <(sort keep.clean.txt)  # → 41 match
```
**驗證**: `wc -l keep.clean.txt` 跟 `comm -12 ...` 結果應該一致
**預防**:
- 寫 keep 清單時**只用純名稱、不要加註解**(或註解放獨立 `# 開頭` 行,不要放在行尾)
- **If** 精瘦 profile 後 `comm -12` 顯示 0 match 但 keep.txt 內明明有該 skill **Then** 檢查 keep.txt 行尾有沒有註解、`awk '{print $1}'` 處理

### hermes profile delete 需要 PTY 餵確認字串(普通 stdin 會被視為 cancel)（2026-06-10）
**症狀**: 跑 `hermes profile delete <name>` 提示「Type '<name>' to confirm:」、普通 `echo "<name>" | hermes ...` 餵 stdin → 直接「Cancelled.」退出,profile 沒刪。
**根因**: hermes 的 `profile delete` 用 `input()` 讀確認字串,普通 stdin 在 pipe 模式下被視為「已關閉」(EOF),不是「使用者已輸入」。需要 PTY 模擬互動式終端機。
**解法**: 用 `pty=true` 餵確認字串:
```bash
echo "market-strategist" | hermes profile delete market-strategist  # 普通:取消
# 改用 pty=true
echo "market-strategist" | hermes profile delete market-strategist  # pty 模式:成功
```
或在 python/expect 內送:
```python
import pexpect
child = pexpect.spawn('hermes profile delete market-strategist')
child.expect("to confirm:")
child.sendline("market-strategist")
child.expect(pexpect.EOF)
```
**驗證**: `hermes profile list | grep <name>` 應該找不到
**預防**:
- **If** 跑 hermes 互動式 CLI(`profile delete`、`setup`、`install`)需要餵確認字串 **Then** 用 `pty=true`、不要用普通 stdin
- **If** 真的無法用 pty **Then** 改用對應的「force」或「--yes」flag(但 `profile delete` 沒有,只能用 pty)

### hermes curator 會自動把刪掉的 skill 補回來(2026-06-10)
**症狀**: 精瘦 profile 後 skill 數從 194 → 41。但過一會兒(幾分鐘到幾小時),磁碟上 skill 數又變成 54,多了 13 個(apple、autonomous-ai-agents、creative、data-science、email、github、media、mlops、note-taking、productivity、smart-home、social-media 等)。
**根因**: hermes curator 背景 cron 比對 `~/.hermes/profiles/<name>/skills/.bundled_manifest` 跟實際磁碟。manifest 是 default profile 帶過來的完整清單(hash + name),curator 看到 manifest 內有但磁碟沒有 → 自動從 default 的 bundled source 補回。
**解法**: 三選一
1. **接受**:每次驗證前手動再砍一次(`rm -rf` 13 個 skill,簡單但要記得)
2. **修改 manifest**:用 `hermes skills opt-out <name> --remove` 正式 opt-out(避免 curator 補回),但需要逐個跑
3. **停用 curator**:在 `~/.hermes/profiles/<name>/config.yaml` 加 `curator.enabled: false`(沒驗證過、可能有副作用)
**驗證**:
```bash
# 精瘦後
ls ~/.hermes/profiles/<name>/skills/ | grep -v "^\." | wc -l  # 41
# 等 10 分鐘後再跑
ls ~/.hermes/profiles/<name>/skills/ | grep -v "^\." | wc -l  # 54 → curator 補回了
```
**預防**:
- **If** 精瘦 profile 是為了「永久精瘦」不是「測試」**Then** 跑 `hermes skills opt-out` 逐個標記(慢但最乾淨)
- **If** 精瘦 profile 是「暫時省磁碟」**Then** 直接 `rm -rf`,接受 curator 會補回
- 寫驗證命令時加上「過 N 分鐘後重跑」以驗證 curator 沒搞鬼
- **If** `hermes skills list` 跟磁碟 `ls` 數字對不上(差 3-4 倍) **Then** CLI 把子目錄也算成 enabled,實際磁碟才是真相,參考 [[#精瘦 profile 原則:常駐代理 = 30-60 個 skill]]
