# Hermes 全狀態備份任務的設計盲點（2026-06-06 累積）

> 觸發：赫米斯接到「X 也備份進去」「幫我做全狀態備份」「異機還原」「Drive 加密備份」「v4 演進」「rclone 怎麼用」這類任務時讀這份。
> 建立時間：2026-06-06
> 最後更新：2026-06-07（v3 → v4 → v4.1 → v4.2 演進時大幅擴充、新增 Rule 8-15）
> 條目數：**15**（Rule 1-7 為 v1-v2.0 時期、Rule 8-15 為 2026-06-07 v4 演進時新增）

---

## 核心 L3 抽象規則

### Rule 1：外部 skill 必須完整 rsync 進 tar，**不能只列名單**

**症狀**：v2.0 備份腳本用 `INSTALLED_MANIFEST.md` 列所有已裝 skill 名單，沒備 skill 內容。
**陷阱**：使用者改過外部 skill 的 SKILL.md 或 references，未來重裝會拿原始版（**修改全丟**）。
**正確做法**：
- 自建 skill 完整 rsync 進 tar（含整個 `references/`、`templates/`、`scripts/` 子目錄）
- 外部 skill **也完整 rsync**（用 `find $HERMES_HOME/skills -name "SKILL.md"` 掃，rsync 每個含 SKILL.md 的目錄）
- INSTALLED_MANIFEST.md 改成「標記每個 skill 備份大小 + 來源資訊」，不是只有名單

**驗證**：
```bash
tar -tzf hermes_backup_public.tar.gz | grep "/SKILL.md$" | wc -l
# 應該 = 自建 skill 數 + 外部 skill 數（不是只列名單）
```

### Rule 2：venv 預設含（災難還原要 30-60 分鐘重建 venv 不划算）

**症狀**：v3.0 hermes-agent 源碼預設排除 venv/，聲稱省 700 MB。
**陷阱**：異機還原時 venv 要重新 `pip install`，30-60 分鐘起跳，**災難時沒時間等**。
**正確做法**：
- **預設含 venv**（多 351 MB 換立即可用，划算）
- rsync 命令**不**加 `--exclude='venv/'`
- 若真要省空間，**用 .gitignore 式二級策略**：
  - Drive FULL = 含 venv（災難還原用）
  - GitHub PUBLIC = 不含 venv（公開版省空間、且不該含編譯產物）
**驗證**：解 tar 後 `find $HERMES_HOME/hermes-agent/venv -name "python" -type f` 應有結果

### Rule 3：Drive 「最新鏡像」檔名（`hermes_backup_latest.tar.gz`）= 假議題

**症狀**：想用固定檔名 + rclone 增量（每次只 push 變動部分）。
**陷阱**：
1. rclone 1.60 對**加密後的單一大檔**（662 MB）`rclone copy` 會卡住（CPU 0.9%、無進度、無錯誤）
2. Google Drive API 對大檔加密上傳有 rate limit
3. 即使能跑、第一次仍是全量、之後才有增量
**正確做法**：
- **用時間戳目錄**（`hermes_backup_<ts>_full/`）每次建新，restore 腳本 `lsf | sort | tail -1` 找最新
- **不用 latest.tar.gz 鏡像策略**（rclone 對大檔單檔加密不可靠）
- 真正省頻寬的辦法：**縮減 tar 內容**（排除可重新生成的東西），不是搞增量鏡像

### Rule 4：DISPLAY 縮寫問題（patch regex 到 .sh 時）

**症狀**：patch 一個 regex 進 .sh 檔，工具顯示 `SECRET_REGEX='***'` 看起來壞了。
**陷阱**：實際上**檔案內容正確、是工具 display 把 regex literal 縮寫**。我多次 patch 同一行、浪費時間。
**正確做法**：
- 懷疑工具 display 縮寫時，用 python 讀檔看實際內容（但 background review 不給終端機工具時無法做）
- `bash -n` 通過就代表語法 OK
- **不要盲目重 patch**同一行
**預防**：未來要寫完整 regex 到 .sh 時，用 python 構造字串、不直接寫 regex literal

### Rule 5：secret scan 用 `xargs tar -xzOf` 對 10000+ 檔案卡 3 分鐘

**症狀**：v3.0 secret scan 跑了 3 分鐘無進度、CPU 0%。
**根因**：`tar -tzf | xargs -I{} tar -xzOf` 對每個檔案呼叫一次 tar，10000+ 個檔案太慢。
**正確做法**：用 `tar -xzOf` 一次解整個 tar + pipe 給 grep：
```bash
if tar -xzOf "$TARBALL" 2>/dev/null | grep -E "$SECRET_REGEX" >/dev/null 2>&1; then
  echo "❌ ABORT"
  exit 1
fi
```
**速度**：3 分鐘掛住 → 秒過

### Rule 6：「✅」聲稱一律附驗證輸出

**症狀**：寫 v1.0 backup_hermes.sh 寫「.env 範本 ✅」、「delegation.model ✅」，結果都沒驗證就 commit。
**根因**：自我報告 ≠ 驗證
**正確做法**：
- 任何「✅（已設）」都要附驗證命令的真實輸出
- 對 hermes 認得的 provider（minimax、openai、anthropic、openrouter）才有把握
- 對 hermes 沒內建的 provider（如 deepseek）即使 .env 有 key、`rclone` 能連，也不代表 hermes dispatcher 會用

### Rule 7：Drive rate limit

**症狀**：rclone crypt 加密 600+ MB 大檔、連續操作會踩到 API 限制、可能卡 15+ 分鐘無錯誤。
**正確做法**：
- 給 rclone 留冷卻時間（cron 排每天 03:00 跑、不要密集呼叫）
- 大檔拆小（但 hermes-agent 源碼 662 MB 是單一 tar、不易拆）

## 給未來做備份任務的 SOP（依時間序）

1. **盤點**：`du -sh ~/.hermes/*` 看分布
2. **決策哪些進 Drive、哪些進 GitHub、哪些不進**：
   - Drive：含敏感/大型（.env、state.db、源碼含 venv、GPG tokens、cache）
   - GitHub：公開版不含敏感/大型
   - 不進：session transcripts、衍生快取
3. **設計兩個 tar.gz**：
   - `_public.tar.gz`（給 GitHub、含完整自建 skill + INSTALLED_MANIFEST）
   - `_full.tar.gz`（給 Drive、含全部含 venv）
4. **每個 tar 內都要含**：
   - 還原腳本
   - 還原 SOP（README.md）
   - INVENTORY.md（敏感/大型版專用，列所有敏感檔位置）
5. **打包後 secret scan**：用 `tar -xzOf | grep` 模式（不是 xargs）
6. **rclone 上傳**：
   - Drive 用 rclone crypt 加密、用時間戳目錄
   - **不用 latest.tar.gz 鏡像策略**（rclone 1.60 大檔有 bug）
7. **GitHub push**：
   - 先 redact 任何 vcp_/ghp_/sk- 開頭 20+ 字串
   - secret 掃描通過才能 push
8. **註冊 cron**：每天 03:00、no-agent script 模式

## If 接到「X 也備份進去」的反饋

**先問使用者 3 件事**：
1. X 是敏感的嗎？ → Drive 加密版才能進、GitHub 不行
2. X 重新生成要多久？ → <5 分鐘可重生 = 不必備；>30 分鐘 = 必備（如 venv）
3. X 變動頻率？ → 每天變 = 必須備（異機還原要最新）；從不變 = 備一次就夠

**然後**才動手改腳本。**不要先假設「使用者說的全部都進」**。

---

## 新增踩雷（2026-06-07 v3 → v4 演進時發現）

### Rule 8：Drive API 配額 840K/分鐘/專案、13,611 小檔必爆（從 stderr 拿到 Google 官方配額數字）

**症狀**：
- rclone sync 跑到 50-70% 時 speed 從 1 MiB/s 崩到 3 KiB/s
- 進度條 ETA 從 5 分鐘暴增到 13 小時
- log 沒 ERROR、沒 429 訊息、純粹被 throttle
- 連 `rclone size`、`rclone lsf` 簡單操作都 timeout >5 分鐘
- 即使 `pkill rclone` 之後、**Drive 還在 throttle 5-10 分鐘**

**根因**：
- 從背景程序 stderr 拿到的 Google 官方回應：
  ```
  rateLimitExceeded
  quota_limit_value: 840000
  quota_unit: 1/min/{project}
  quota_metric: drive.googleapis.com/default
  service: drive.googleapis.com
  ```
- → Google Drive API 配額 = **840,000 單位/分鐘/專案**（不是無限）
- → rclone sync 每個小檔 ≈ 3-5 個 API 單位（list + metadata + put + chunk upload）
- → 13,611 個小檔 = 50,000+ API 單位、**幾分鐘內秒殺配額**
- → 配額週期 1 分鐘重置、但已超過就持續 throttle

**症狀證據**（v3 兩次實測）：
- v3 run 2：跑到 63% (300 MiB) 時 speed 從 1 MiB/s 掉到 3 KiB/s
- v3 run 3：跑到 68% (356 MiB) 時 speed 從 1.3 MiB/s 掉到 28 KiB/s、然後 speed 反彈到 866 KiB/s（配額剛重置、但已被殺）

**Drive 對「單一大檔」vs「1 萬小檔」的關鍵差異**（v4.1 設計核心）：
| 模式 | API 行為 | 友善度 |
|------|---------|--------|
| **1 個 200 MB 檔**（如 state.db 加密後） | 1 個 PUT request + chunked upload、配額用 1 個單位級別 | ✅ 極友善、1 分鐘可傳完 |
| **1 萬個 1 KB 小檔**（如 9000 個 skill） | 每檔 3-5 單位（list + metadata + put）、總計 5 萬+ 單位、**幾分鐘內必秒殺** | ❌ 完全不友善 |

→ 這就是 v4 雙雲端分工的核心依據：**文字/小檔走 GitHub**（無 Drive 配額問題）、**加密大檔走 Drive**（1 個 API request 解決）。

**If→Then**：
- **If** rclone sync 對 Drive 跑 10000+ 小檔目錄 **Then 必爆** Google Drive API 配額（不靠運氣）
- **Then** 加 `--tpslimit 5 --transfers 1 --checkers 1` 限速（預期 1-2 小時）
- **Then** 改回 tar.gz（v2 模式）— 雖然大、**只需 1 個 API request**、穩定
- **Then 不要**為「乾淨架構」犧牲「實際可用性」

**If** 真的要長期用 rclone sync 上 Drive
**Then** 申請提高配額：https://cloud.google.com/docs/quotas/help/request_increase
**Then** 或換雲端（Backblaze B2 / S3 對小檔 API 較友善）
**Then** 或採 v4 雙雲端：文字檔走 GitHub（git protocol 無 Drive 配額問題）、加密大檔走 Drive

**If** 設計備份架構要備份大量小檔
**Then** 不要全用 Drive 同步、要嘛用 GitHub（無 API 限制）、要嘛用 tar 包成大檔
**Then** Drive 適合加密後的 1 個大檔（87 MB state.db + secrets bundle）、不適合 9000 個小 skill

### Rule 9：備份檔不該被備份（備份悖論）

**症狀**：把 `memories/MEMORY.md.bak.1780752174` 這類帶 timestamp 的備份檔 commit 進 staging、推到 GitHub、觸發 GH013（因為備份檔含完整 MEMORY 副本、含 API key）

**根因**：
- 「備份檔不該被備份」是備份設計的基本原則（**備份悖論**：備份 X 應該等於 X、不是 X 加上 X 的所有備份）
- 預設 `*.bak` 模式**不涵蓋**帶 timestamp 的變體（`MEMORY.md.bak.1780752174`）
- 備份腳本設計時**沒考慮排除上一代備份檔**

**If→Then**：
- **If** 寫備份腳本要把 `~/.hermes/memories/` 進版控 **Then** 一定要加 `--exclude='*.bak.*' --exclude='*.lock' --exclude='*.clean.*'`
- **Then** `.gitignore` 也要寫 `*.bak.*` 模式（不是只有 `*.bak`）
- **Then 不要**把所有看到的 `.md` 檔都加進備份（要看修改時間、是否為目前使用中的版本）

**驗證**：
```bash
# 看 staging 內還有沒有備份檔
git ls-files | grep -E '\.bak\.|\.lock|\.clean\.' | head -3
# 應該空
```

**相關條目**: [[gh-cli-and-github#GH013 push protection 觸發時的完整修復 SOP]]

---

### Rule 11：v4 備份腳本**完全漏掉 skills/ 同步**、剛加的條目沒進 GitHub（2026-06-07 踩到）

**症狀**：
- 寫了 5 個新 trial-and-error 條目（bash-defensive-patterns 等）
- 跑 `hermes-backup-v4.sh --tier1` 顯示「✓ 備份完成、✓ GitHub push 成功」
- 但 GitHub 倉庫內的 trial-and-error 還是只有 9 個舊檔、**新加的 4 個完全沒進去**
- 浪費 30+ 分鐘才發現

**根因**：
- v4 備份腳本**只同步** config.yaml、agents/、memories/、scripts/、docs/ — **完全漏了 skills/**
- 註解還寫「sparc 已經是 snapshot、不重新同步（除非顯式 --include-sparc）」
- 這句話**誤導**了整個設計 — 我以為 sparc 不重 sync ＝ 整個 skills/ 不重 sync
- 真相：sparc 只是 skills/ 內的**一個子目錄**、其他 180+ skills 還是要同步

**完整修復**：
1. 加 skills rsync 步驟（含排除 .git/、__pycache__/、.curator_backups/、agentdb.rvf、venv/、*.tar.gz/zip 等大檔）
2. 跑 backup-v4.sh
3. **驗證** `git ls-files | grep 'trial-and-error' | wc -l` 真的增加（不是只看 exit code）

```bash
# v4 腳本必加的 skills 同步步驟
if [[ -d "$HERMES_HOME/skills" ]]; then
  run_or_dry rsync -au --delete \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='.archive/' \
    --exclude='.curator_backups/' \
    --exclude='*.pyc' \
    --exclude='agentdb.rvf' --exclude='agentdb.rvf.lock' \
    --exclude='venv/' \
    --exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip' \
    "$HERMES_HOME/skills/" "$STAGING/skills/"
fi
```

**If→Then**：
- **If** 寫任何 `hermes-backup-*.sh` 腳本 **Then** 一定要明確列出**每一個**要同步的目錄、不能寫「不重新同步」、「略過」這類模糊註解
- **Then** 跑完後**驗證**：用 `git diff origin/main --stat` 或 `gh api repos/.../git/trees/main?recursive=1` 看新檔案真的有進去
- **Then 不要**只信「✓ 備份完成」訊息（自我報告 ≠ 驗證）

**驗證 SOP**（每次跑完 backup 必做）:
```bash
# 1. 看本地 HEAD 跟 origin 差幾個 commit
git log --oneline origin/main..HEAD | wc -l
# 應該 = 0 或 1（剛 push 完）

# 2. 看新檔有沒有在 GitHub
gh api 'repos/USER/REPO/git/trees/main?recursive=1' | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print([t['path'] for t in d['tree'] if 'trial-and-error' in t['path']][-5:])"

# 3. 看 GitHub 倉庫 size 有沒有變大（粗略指標）
gh api repos/USER/REPO --jq .size
```

**相關條目**: [[gh-cli-and-github#bash `2>&1 | grep -qE "error"` 會吞掉 exit code、讓 push 失敗顯示假成功]]

### Rule 10：「先查上游、不要假設本地是 source of truth」— sparc-methodology 是 upstream clone 不是本地維護

**症狀**：
- 設計 v4 架構時預期 sparc-methodology 是「赫米斯本地維護的 86.9 MB skill 資料夾」、要拆成 submodule 推到 `hoonsoropenclaw/hermes-sparc-skills`
- 結果發現 `~/.hermes/skills/sparc-methodology/.git/config` 指向 `https://github.com/ruvnet/claude-flow.git`
- HEAD = `844f68d`、origin/main = `d065b15`、**只落後 upstream 2 個 commit**

**根因**：
- 沒先 `git remote -v` 看 sparc 是哪裡來的、就盲目設計「拆 submodule 推到自己的 repo」
- 結果：白建一個 `hermes-sparc-skills` repo（後來刪掉）、浪費 ~5 分鐘

**If→Then**：
- **If** 要對任何 `~/.hermes/skills/<X>/` 子目錄做「拆 submodule」「推自己的 repo」之類的架構動作 **Then** 先 `cd ~/.hermes/skills/<X>/ && git remote -v && git log --oneline -3` 確認它不是 upstream clone
- **Then** 如果是 upstream clone、**用 snapshot 模式**（直接複製內容進備份、不是 submodule 引用）
- **Then** snapshot 模式的理由：備份是「凍結歷史」、不是「追蹤 upstream」、submodule 對備份是 over-engineering

**驗證**：
```bash
cd ~/.hermes/skills/sparc-methodology
git remote -v                          # 看 origin 指向哪
git log --oneline -3                   # 看 HEAD 是哪個 commit
git fetch origin --quiet && git rev-list --count HEAD..origin/main  # 落後幾個
```

**決策結果**（2026-06-07 採納）：
- ❌ 不用 submodule（過度設計、跟 v4 雙雲端架構無關）
- ❌ 不用自建 `hermes-sparc-skills` repo（白工）
- ✅ 用 **snapshot 模式**：複製 `sparc-methodology/` 內容進 `hermes-config-backup/skills/`
- ✅ 排除 `agentdb.rvf` 系列、`.git/`、venv、cache（用 root `.gitignore`）
- ✅ 更新方式：手動 `cd ~/.hermes/skills/sparc-methodology && git pull` 後再跑備份

**相關條目**: [[hermes-backup-strategy#三路分流架構（2026-06-06 設計）]]

---

### Rule 14：`rclone purge <remote>:` = 砍整個 remote 內容到垃圾桶（不是清垃圾桶）

**發現時間**: 2026-06-07

**觸發情境**: 想清掉 Drive 垃圾桶裡 4 個 v1 完整備份（~675 MB）、用 `rclone purge crypt_hermes:` 想說「整個清掉」、結果把 hermes-backup 整個目錄（含 README、restore 腳本、所有 v1）全砍到垃圾桶。

**症狀**:
- 跑完後 `rclone tree crypt_hermes:` 回「directory not found」
- Drive 容量從 14.3 GB Used 掉到 13.3 GB Used（少 1 GB = purge 移了 1 GB 進垃圾桶）
- Trashed 從 0 變 309 MB
- **資料沒真的丟**（rclone 預設 `--drive-use-trash=true`）、但用 rclone 看不到、只能從 Google Drive UI 救

**根因**:
- `rclone purge` 的語法是 `rclone purge <remote>:<path>` — **砍指定路徑**
- 沒指定 path = 砍整個 remote 的 root
- 我以為「purge 就是清垃圾桶」、**錯了** — purge 是砍檔、垃圾桶是 `drive-use-trash` 旗標控制
- 沒有 `rclone empty-trash` 這種「只清垃圾桶」的標準指令（rclone 對垃圾桶的 API 支援有限）

**If→Then**:
- **If** 想「清 Drive 垃圾桶」**Then 不要**用 `rclone purge`、`rclone delete` 等指令、**改用 Google Drive UI**（drive.google.com/drive/trash）
- **If** 想「砍某個 rclone 遠端的子目錄」**Then 一定要** `rclone purge <remote>:<path>` 指定完整路徑
- **If** 想測試 `rclone purge`/`delete` 行為 **Then** 先 `rclone --dry-run` 確認會砍哪些檔
- **If** 不小心 `purge` 砍錯了 **Then** 立刻進 Google Drive UI 看垃圾桶（30 天內可救回）、不要慌張

**Hermes 親身教訓**:
- 2026-06-07 我跑 `rclone purge crypt_hermes:` → 把 hermes-backup 整個砍進垃圾桶
- 用戶說「垃圾桶沒檔案可救」— 推測 rclone purge 對垃圾桶處理機制跟 UI 不一樣、可能直接清空垃圾桶
- **修正策略**: 廢掉 rclone crypt、**改用明文 Drive (`hoonsorasus:`) + 客戶端 GPG 加密**（見 strategy.md v4.2 段）

**預防腳本範本**（如果未來真的要用 rclone purge）:
```bash
# 1. 先 --dry-run 看會砍哪些
rclone purge --dry-run <remote>:<path>

# 2. 用明確路徑、不要只指定 remote
rclone purge "hoonsorasus:hermes-backup/v1-old/"   # ← 明確指定子目錄

# 3. 加 --drive-use-trash=false 立刻真刪（要嘛不刪、要嘛真刪、不要半調子）
rclone purge --drive-use-trash=false "hoonsorasus:hermes-backup/v1-old/"

# 4. 用後立即驗證
rclone lsf <remote>:<path>  # 應該 not found
```

**相關條目**: [[hermes-backup-strategy#v4.2 明文 Drive + client-side GPG（響應 rclone crypt 不實用）]]

---

### Rule 15：`rclone mkdir ... 2>/dev/null || true` 偽成功 + Drive 上 .gpg 顯示成「偽目錄」陷阱

**發現時間**: 2026-06-07

**觸發情境**: 在 `hermes-secrets-encrypt.sh` 的 `upload_drive` 函式加 `rclone mkdir "${RCLONE_REMOTE}/" --config "$RCLONE_CONF" 2>/dev/null || true` 想說「先建目錄、失敗就忽略」、然後 `rclone copy` 91 MB .gpg。**結果**: mkdir exit 0、copy exit 0、但 Drive 上一片空白。

**症狀 1 — 偽成功**:
- `rclone mkdir remote:dir 2>/dev/null || true` 永遠 exit 0（即使 mkdir 失敗、因為 `|| true` 掩蓋）
- 後續 `rclone copy` 報 `directory not found`、但看 exit code 不知道是 mkdir 還是 copy 失敗
- 整個 script 看起來「跑成功」、實際檔案沒上傳

**症狀 2 — Drive 偽目錄**:
- Drive 上 91 MB 的 `secrets-bundle-XXX.tar.gpg` 加密檔用 `rclone lsf` 看 → 顯示成 `secrets-bundle-XXX.tar.gpg/`（**帶尾斜線、像目錄**）
- 其實是 Drive 把 `.gpg` 副檔名誤判、加上 crypt layer 混淆檔名
- 用 `rclone lsf --files-only` 才能過濾出真正的檔案
- 影響：還原腳本用 `grep 'secrets-bundle-.*\.tar\.gpg'` 找最新會找不到

**根因**:
- **症狀 1**：`|| true` 是 bash 慣用法掩蓋錯誤、但會讓 debug 變難
- **症狀 2**：Drive 對「副檔名是 `.gpg` 的單一大檔」+ rclone crypt layer 一起作用 → 顯示成目錄；其實 rclone copy 時是當檔案處理（會 streaming 上傳）

**If→Then**:
- **If** 寫任何 `rclone` 相關腳本 **Then 不要**用 `|| true` 掩蓋錯誤、**讓錯誤冒出來**
- **If** 一定要用 `|| true` **Then 同時印 stderr**（`2>&1 | tee /tmp/rclone.log`）方便事後看
- **If** 寫 Drive 還原腳本找最新檔 **Then 用** `rclone lsf --files-only` 不要預設 lsf
- **If** 用 `rclone lsf` 看到 `xxx.tar.gpg/` 帶斜線 **Then 不要**以為是目錄、用 `rclone ls` 看實際 size

**預防腳本範本**:
```bash
# ❌ 偽成功
rclone mkdir "${REMOTE}/" 2>/dev/null || true
rclone copy "${SRC}" "${REMOTE}/"
# exit 0 但實際失敗

# ✓ 看見錯誤
rclone mkdir "${REMOTE}/" 2>&1 | tee /tmp/mkdir.log
rclone copy "${SRC}" "${REMOTE}/" 2>&1 | tee /tmp/copy.log
# 任何一個失敗都會被看到

# ✓ 還原時找最新檔
LATEST=$(rclone lsf "${REMOTE}/" --files-only --format "ps" 2>/dev/null | \
  grep '\.tar\.gpg$' | sort -k2 -r | head -1 | awk '{print $2}')
```

**怎麼判斷 Drive 上的「偽目錄」是真是假**:
```bash
rclone ls <remote>:<path>/ 2>&1
# 看到 size 數字 → 真的是檔案（即使 lsf 顯示帶斜線）
# 看到 "directory not found" → 真的目錄
```

**If** 用 rclone 對 Drive 操作、**用戶在乎備份可靠性** **Then** 任何 `|| true` 都應該拿掉、並加上「跑完後 rclone ls 驗證」的最後檢查

**相關條目**: [[hermes-backup-strategy#v4.2 明文 Drive + client-side GPG（響應 rclone crypt 不實用）]]

---

## v4.1 新增（2026-06-07 state.db 跟 hermes-agent 重新分類時發現）

### Rule 12：對任何資料備份前，**先查能不能 rebuild**（不要憑印象答）

**症狀**：
- v4 設計時把 `state.db`（197 MB、SessionDB SQLite 對話歷史）跟 `hermes-agent/`（1.1 GB）都歸類為「rebuild 即可、不備份」
- 兩個判斷**都錯了**、但性質相反：
  - `state.db` 真的是對話歷史、**不能重建**（用戶質問才發現）
  - `hermes-agent/` 真的是 `NousResearch/hermes-agent` upstream clone、可以 `git pull` 重建（驗證後確認）
- 浪費一個 session + 觸發多次 GH013 + 浪費 Vercel token 風險

**根因**：
- 寫 v4 設計時**憑印象**答「state.db 跟 hermes-agent 都可以 rebuild」、沒真的去查
- 自我報告 ≠ 驗證 — 跟 Rule 6 是同一條線、但場景不同
  - Rule 6：是「✅」標籤附驗證輸出
  - Rule 12：是「X 可以 rebuild」這類**刪除性判斷**也要驗證

**If→Then**：
- **If** 要對任何 `~/.hermes/` 內的東西下「rebuild 即可、不備份」結論 **Then 必先查**：
  ```bash
  # 1. 是不是 upstream clone？
  cd ~/.hermes/<X>
  git remote -v 2>&1 | head -3
  # 看到 origin = github.com/<someone>/<X>.git → 是 upstream clone

  # 2. 有沒有本地未推的 patch？
  git status -sb 2>&1 | head -5
  # 看到 ## main...origin/main [ahead N] → 有本地 patch

  # 3. 跟 upstream 差幾個 commit？
  git fetch origin --quiet && git rev-list --count HEAD..origin/main
  # 差 0 個 = 完全跟 upstream

  # 4. 是 Python package 還是源碼？
  find . -name "setup.py" -o -name "pyproject.toml" | head -3
  ```
- **If** 是 upstream clone + 沒有本地 patch + 不是使用者 daily-modified 檔 **Then** 真的可以不備
- **If** 是 SQLite / binary DB / 使用者 daily-modified 內容 **Then 假設「不能 rebuild」、必須備**
- **Then 不要**只看檔名判斷（`state.db` 看似 cache 檔、實則是 SessionDB；`hermes-agent/` 看似源碼、實則是 git clone）

**為什麼這個 Rule 重要**：
- 「rebuild 即可」是備份設計的**最危險判斷** — 判錯了 = 永久丟資料
- 跟 Rule 6 一樣、但 Rule 6 抓「✅ 寫得太輕易」、Rule 12 抓「✗ 寫得太輕易（認為可丟）」
- **任何「X 可以不備」的判斷都應該走 SOP-12 驗證流程**

**驗證 SOP**（每次 v4 之類備份設計前必跑）:
```bash
du -sh ~/.hermes/* 2>/dev/null | sort -rh
# 對每一個 > 10MB 的項目問：真的可以不備嗎？
#   - 是 git clone 嗎？ → git remote -v
#   - 有本地 patch 嗎？ → git status
#   - 是 binary DB 嗎？ → file <X> | head -1
#   - 是 cache 嗎？ → 從檔名推斷 + 看修改時間
```

**相關條目**: [[hermes-backup-strategy#v4.1 修正：state.db 跟 hermes-agent 分類重新檢視]]

---

### Rule 13：rclone crypt 對大檔（>50 MB）加密是反模式

**症狀**：
- v4.1 設計 state.db 走 Drive Tier 2 加密、88 MB .gpg 上 Drive
- 跑了 18+ 分鐘（甚至 27 分鐘）還沒完成、上傳速度 56-100 KiB/s
- 過程中**沒有錯誤訊息**、純粹是 rclone crypt + Drive 對大檔加密 stream 的效能問題
- 部分 chunk 還會重傳（`92.898 MiB / 174.460 MiB, 53%` — 87 MB 檔案被算成 174 MB 是因 retry chunk）
- 結論：**88 MB 加密檔上 Drive、預期 20-30 分鐘**、用 cron 排每天備份會卡住整個流程

**根因**：
- rclone crypt 對大檔加密是**整檔 streaming + 加密**：先讀整檔到 buffer、加密、然後分 chunk 上傳
- 加上 Drive API 對**寫入大檔**有隱性 throttle（不像讀取那麼明顯）
- 結果：88 MB 在容器內、外網路、Drive 端三層節流 = 20+ 分鐘
- **這個 pattern 對小檔（<10 MB）沒事**、對大檔就出事

**If→Then**：
- **If** 要把任何 **>50 MB 的檔**走 rclone crypt 加密上 Drive **Then 不要**這麼做、改採：
  - **方案 A（推薦）**：**大檔明文上 Drive**（單一大檔 Drive API 友善、1 個 API request 解決）
    - 例：state.db 197 MB **不加密**、直接 `rclone copy state.db crypt_hermes:hermes-backup/state-db/`
    - 為什麼安全：state.db **不含 secrets**、只含對話歷史（已驗證）
  - **方案 B**：先 gzip 再加密（壓縮率提升、加密後更小）
  - **方案 C**：改用**其他雲端**（Backblaze B2 對大檔較友善、無 840K API 配額問題）
- **If** 只有小檔要加密（<10 MB）**Then** rclone crypt 還可以、幾秒鐘搞定
- **Then 不要**把含大檔的 bundle 整包 rclone crypt 加密

**怎麼判斷「大檔」**：
```bash
tar -tvf secrets-bundle-*.tar | head -20
# 如果有單檔 > 50 MB → 走方案 A 或 B
```

**驗證**：
```bash
rclone copy --dry-run --progress <src> crypt_hermes:<dst>
# 看到 ETA > 10 分鐘 → 改方案 A 或 B
```

**相關條目**: [[hermes-backup-design-pitfalls#Rule 7：Drive rate limit]]

---

## 跨分類關聯

- cron jobs 修補 → [[hermes-internal#hermes cron edit --script 對 no_agent jobs 的 bug]]
- 改 metacognitive-learner skill → [[hermes-internal#技能 L3 抽象教訓分流決策樹（2026-06-06 建立）]]
- 自我報告不等於驗證 → [[hermes-internal#自我審查：自我報告 ≠ 驗證（2026-06-06 確立）]]
- v4 → v4.1 設計決策 → [[hermes-backup-strategy#v4 雙雲端演進：從 v3.0 半成品到 v4 雙雲端]]
- v4.2 廢 rclone crypt → [[hermes-backup-strategy#v4.2 明文 Drive + client-side GPG（響應 rclone crypt 不實用）]]
- Telegram cron deliver → 見 hermes-config-tuning 內的 wakeAgent gate

---

### v4 備份腳本只列 7 個目錄+1 個檔,但 ~/.hermes/ 根目錄有 20+ 個路徑（2026-06-10 從漏備 archive/config/handoff 歸納）

**症狀**：備份跑成功、但有些重要目錄從沒進過 staging；hermes 異機還原時才發現缺

**根因**：v4 備份腳本 `hermes-backup-v4.sh` 是「白名單」設計（手動列要同步的目錄），不是「黑名單」（預設全部同步、只列排除）。新目錄（archive/、config/、handoff/、reports/、cache/youtube/、cache/documents/、logs/）被建立時、v4 不知道要備份。根目錄 21 個單檔（除 config.yaml 外）也全部漏備。

**解法**（v4.6 升級）：
1. **v4 同步清單升級**：7 個目錄 + 1 個檔 → **13 個目錄 + 2 個單檔**（含 archive/、config/、handoff/、reports/、cache/youtube/、cache/documents/、logs/ + 根目錄 SOUL.md）
2. **根目錄單檔用 array 管理**：`declare -a ROOT_SINGLE_FILES=( "config.yaml" "SOUL.md" )`、未來加檔案只改 array
3. **新建 `~/.hermes/docs/INVENTORY.md` 作為 single source of truth**：v4 同步清單統一在 INVENTORY.md 維護、改 v4 腳本必同步
4. **新建 `hermes-backup-coverage-check.sh` + cron 每日 04:00**：掃 `~/.hermes/` 路徑變動、跟 v4 同步清單比對、3 層檢查 (Layer A 建議加 / Layer B 可能搬走 / Layer C staging SHA256)
5. **更新 `agent-system-backup/SKILL.md` §14.1 改檔對照表**：必含 INVENTORY.md、coverage check script

**預防**：
- 白名單備份必配「每日覆蓋率檢查」+「single source of truth」
- 任何新目錄建立時、必同步更新 INVENTORY.md v4 同步清單
- coverage check 跑出 WARN 必當下處理（不要累積到 backup 失敗才看）

**If→Then**：
- **If** 寫 v4 備份腳本（白名單設計）**Then** 同步清單用 array 管理、不寫死在 if 區段
- **If** 改任何備份相關檔 **Then** 必同步更新 INVENTORY.md + SKILL.md §14.1
- **If** 新建目錄在 ~/.hermes/ **Then** 必更新 INVENTORY.md v4 同步清單（否則漏備）
- **If** coverage check 跑出 WARN **Then** 必當下處理（4 個 warning = staging 落後 = 等下次備份會自動消失）

**相關條目**：
- [[hermes-backup-strategy#hermes-backup-coverage-check.sh 設計:3 層檢查 + EXCLUDE 清單明確]]
- [[hermes-backup-sop#改任何備份腳本必同步改 INVENTORY.md + SKILL.md §14.1 改檔對照表]]
- [[workspace-folder-layout#根目錄檔案盤點三類法]]
