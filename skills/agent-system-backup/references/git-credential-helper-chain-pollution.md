# Git Credential Helper Chain Pollution — 403 陷阱

## 問題

**症狀**：`hermes-config-backup-daily` push fails with 403 "denied to hoonsor"，但 interactive session 中 `git push` 成功。

**錯誤訊息**：
```
remote: Permission to hoonsoropenclaw/hermes-config-backup.git denied to hoonsor.
fatal: unable to access 'https://github.com/hoonsoropenclaw/hermes-config-backup.git/': The requested URL returned error: 403
```

**根因**：`~/.git-credentials-raphael` 包含 legacy credential `https://hoonsor:ghp_...@github.com`（錯誤帳號）。在非互動式 cron/script 環境中，git credential helper chain 在 `gh auth git-credential` 回傳前就觸發 fallback，用了錯誤帳號 → 403。

## Git Credential Helper Chain 解析順序

```
1. credential.https://github.com.helper = !/usr/bin/gh auth git-credential  (正確，使用 hoonsoropenclaw)
2. credential.helper = store --file ~/.git-credentials                     (全域 fallback)
3. ~/.git-credentials-raphael                                                (legacy per-user fallback)
```

`~/.git-credentials-raphael` 有 legacy credential for user `hoonsor`。當 script 無 TTY 時，`gh auth git-credential` 可能提前退出，觸發 fallback 到 `~/.git-credentials-raphael`。

## 驗證方式

```bash
# 確認錯誤憑證檔存在
cat ~/.git-credentials-raphael
# → https://hoonsor:ghp_...@github.com  ❌（錯誤帳號）

# 確認 gh auth 登入正確帳號
gh auth status
# → ✓ Logged in to github.com account hoonsoropenclaw ✅

# 確認 git config credential helpers
git config --list | grep credential

# 在非互動式 context 中測試 push（關鍵驗證）
bash -c 'cd ~/.hermes/hermes-backup-staging && git push origin main'
# → "Everything up-to-date" ✅（在 script 環境成功與否決定是否為此 bug）
```

## 修復方式（按順序，選一個）

### 方式 1：刪除錯誤憑證檔（最簡單）
```bash
rm ~/.git-credentials-raphael
# 驗證
bash -c 'cd ~/.hermes/hermes-backup-staging && git push origin main'
```

### 方式 2：在 backup script 中明確設定 credential.helper
在 `hermes-backup-v4.sh` 的 `tier1_github()` 函式 push 之前加：
```bash
git config --global credential.helper "!/usr/bin/gh auth git-credential"
```

### 方式 3：執行 `gh auth setup-git`
```bash
gh auth setup-git  # 注入 !gh auth git-credential 到 .gitconfig
```

## If→Then 規則

**If** git push works in interactive session but fails in cron/script with 403 "denied to hoonsor"
**Then** 懷疑 `~/.git-credentials-raphael` credential pollution — 檢查該檔是否包含錯誤帳號
**Then** 修復：刪除該檔或執行 `gh auth setup-git`
**Then** 驗證：`bash -c 'cd ~/.hermes/hermes-backup-staging && git push origin main'`

**If** 任何 cron/script git push 神秘失敗（無論 interactive 是否成功）
**Then** 檢查 `~/.git-credentials*` 所有檔案的帳號是否正確
**Then** 檢查 `~/.gitconfig` credential.helper 是否指向正確 helper

## 為何 interactive session 不受影響

Interactive session 有 TTY，`gh auth git-credential` 在 TTY 環境下更可靠（更能正確互動取得 token）。Script subshell 沒有 TTY，credential helper 行 為不同，導致 fallback 到 legacy store。

## 預防

在 `~/.bashrc` 或 shell 初始化時設定 `credential.helper = !/usr/bin/gh auth git-credential` 並確保 `~/.git-credentials-raphael` 不包含來自錯誤帳號的凭證。