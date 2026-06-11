# v4-P7 skills 同步 bug 完整記錄（2026-06-07）

> 這份是 hermes-backup-design-pitfalls.md 內 v4-P7 P0 教訓的完整版（包含細節、對話、決策過程）。給未來真的踩到時一次看完。

## 對話觸發

```
User: 本次對話相關內容請寫入試誤學習技能
User: skill是同步到github不是嗎？
```

第一句觸發 5 個 L3 條目寫進 trial-and-error。第二句才是這份記錄的核心。

## 真正問題

赫米斯在 v4-P7 之前（v4-P2 補完整備份時）寫了一個 `hermes-backup-v4.sh` 腳本，**顯式列了 5 個 rsync 步驟**（config.yaml、agents/、memories/、scripts/、docs/），但**完全漏了 `skills/`**。

trial-and-error skill 寫完 5 個新條目後，跑 backup-v4.sh → 顯示「沒有變動、跳過 commit」→ 用戶一眼看穿「skills 沒進去」。

## 完整事件鏈

1. 寫 trial-and-error skill 5 個新條目
2. 跑 `hermes-backup-v4.sh --tier1`
3. 輸出「沒有變動、跳過 commit」
4. 赫米斯還以為成功（其實 push 假成功、下面解釋）
5. 用戶問「skill是同步到github不是嗎？」
6. 赫米斯發現 trial-and-error 5 個新條目根本沒進 staging
7. 修腳本加 skills/ 同步步驟 + 排除清單
8. 又踩到 4 個連鎖 bug（見下）
9. 全部修完、push 成功、commit ac8147f

## 4 個連鎖 bug

### Bug 1：.curator_backups/ 含 119 MB tar.gz → GH001

```
remote: error: GH001: Large files detected.
remote: error: File skills/.curator_backups/2026-06-06T03-54-08Z/skills.tar.gz is 119.44 MB
```

**修法**：staging 根 .gitignore 加 `.curator_backups/` + `*.tar.gz` + `*.tar` + `*.zip` + `*.7z`

### Bug 2：metacognitive-learner/references/ 含真實 vcp_ token → GH013

```
remote: —— Vercel Personal Access Token ——————————————————————
remote:   - commit: c016387a90...
remote:     path: skills/autonomous-ai-agents/metacognitive-learner/references/secrets-in-sync.md:18
```

**這個 token 是 2026-06-05 md-files-daily-sync 事件後第二次踩到**（第一次在當時被 GH013 擋下、寫進 alt-token-secrets-layout skill 修復 SOP，但當時 SOP 沒改教學文件本身、所以留有真實 literal）。

**修法**：
1. 從 staging 工作目錄刪除 references/
2. 加進 .gitignore
3. **真實的修復** = 去 Vercel revoke 重新申請（token 已公開洩漏）

### Bug 3：push 失敗訊息被 grep 吞掉、exit 0 假成功

**原版 bug**：
```bash
if git push origin main 2>&1 | grep -qE "(GH013|error:)"; then
  err "push 失敗..."
  return 1
fi
ok "GitHub push 成功"  # ← 即使 push 失敗、也跑到這
```

**根因**：
- `set -e` 在 `if` 條件內**不會觸發**（bash 設計）
- `git push ... | grep` 的 exit code 是 grep 的、不是 push 的
- 即使 push 失敗、grep 沒 match、判斷為「成功」

**修法**：
```bash
local push_output
push_output=$(git push origin main 2>&1) || true
echo "$push_output" | tail -10
# 分別檢查 GH013 / GH001 / 其他錯誤
if echo "$push_output" | grep -qE "GH013.*secrets"; then ...; return 1; fi
if echo "$push_output" | grep -qE "GH001.*Large files"; then ...; return 1; fi
if echo "$push_output" | grep -qE "(\[remote rejected\]|error:|fatal:)"; then ...; return 1; fi
ok "GitHub push 成功"
```

### Bug 4：filter-branch 改寫後 SHA 不變

`git filter-branch -f --index-filter 'git rm -rf --cached --ignore-unmatch <path>' --prune-empty -- --all` 跑完、SHA 完全沒變（commit tree 物件還引用舊 blob）。

**附帶災難**：`rm -f .git/objects/pack/pack-*.pack` 想清 dangling blob → 整個 staging 壞掉（HEAD 報 "bad object"）→ 只能從 GitHub 重新 clone + 從 /tmp 備份覆蓋。

**最終決策**：**砍掉 c016387 整個 commit**、用 `git reset --hard 1eab220` 回到上次乾淨狀態、重新整理改動、重新 commit ac8147f 一次推上去。

## 最終結果

- commit `ac8147f` 推上去
- 13 個 trial-and-error 條目全部進 GitHub
- sparc-methodology / bash-defensive-patterns / hermes-backup-design-pitfalls / hermes-backup-strategy / gh-cli-and-github 強化版都進了
- vcp_ token 已被永久排除（references/ 加 .gitignore、未來不會再 push 觸發 GH013）
- **但 token 仍需去 Vercel revoke**（歷史 commit 留有痕跡、GitHub 仍記得）

## 給未來赫米斯的清單

下次設計任何「把 A 同步到 B」腳本時、開頭先寫：

```bash
# === SYNC 範圍（每次新增/刪除要回來更新這份清單）===
# 包含：
#   config.yaml
#   auth.json.template
#   agents/
#   memories/
#   scripts/
#   docs/
#   skills/        # ← 容易漏
#   cron/

# 排除（技術性 --exclude）：
#   .git/  .curator_backups/  .archive/  venv/  __pycache__/
#   *.pyc  *.tar.gz  *.tar  *.zip  *.7z
#   agentdb.rvf  agentdb.rvf.lock
#   state.db  *.db-wal  *.bak.*  *.lock  *.clean.*
```

然後每個 `if [[ -d X ]]; then rsync ...` 步驟**嚴格對應這份清單**、不額外加。
