# SSH Push 403 — gh auth git-credential Helper 劫持 SSH 連線

**日期**：2026-06-12
**影響 Job**：`v4-backup-tier1-daily`
**嚴重度**：高（備份失敗）

---

## 症狀

```
last_error: remote: Permission to hoonsoropenclaw/hermes-config-backup.git denied to hoonsor.
fatal: unable to access 'https://github.com/hoonsoropenclaw/hermes-config-backup.git/': The requested URL returned error: 403
```

但：
- staging repo 是 **SSH URL**：`git@github.com:hoonsoropenclaw/hermes-config-backup.git`（不是 HTTPS）
- `ssh -T git@github.com` 成功：`Hi hoonsoropenclaw!`
- 手動 `git push` 成功

## 根因

`git config --global` 設定了：
```
credential.https://github.com.helper = !/usr/bin/gh auth git-credential
credential.https://gist.github.com.helper = !/usr/bin/gh auth git-credential
```

即使 remote URL 是 SSH，git 的 credential subsystem 仍可能在某些環境下被觸發。`gh auth git-credential` 在 cron 環境下回傳**錯誤帳號**（`hoonsor` 而非 `hoonsoropenclaw`）的 HTTPS token，導致 403。

錯誤訊息顯示 `https://...` 是因為 credential helper 被呼叫後，git 把 SSH URL 降級成 HTTPS 並用拿到的錯誤 token 嘗試。

## 修復

SSH push 不需要 credential helper。移除：

```bash
git config --global --remove-section credential.https://github.com
git config --global --remove-section credential.https://gist.github.com
```

## 驗證命令

```bash
# 確認 credential helpers 已移除（應無輸出）
git config --global --list | grep credential

# 確認 staging SSH URL 不變
cd ~/.hermes/hermes-backup-staging && git remote -v
# 應顯示：origin  git@github.com:hoonsoropenclaw/hermes-config-backup.git

# 驗證 push 成功
cd ~/.hermes/hermes-backup-staging && git add -A && git commit -m "test" --allow-empty && git push origin main
# 應成功：Everything up-to-date 或 [new branch]

# 確認 hermes cron 狀態翻轉
hermes cron run v4-backup-tier1-daily
sleep 20
python3 -c "
import json
d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
for j in d['jobs']:
    if 'v4-backup-tier1' in j.get('name',''):
        print('last_status:', j.get('last_status'), '| last_run_at:', j.get('last_run_at'))
"
```

## 與 Type J2 的差異

| | Type J2（舊） | Type J2-SSH（本案例） |
|---|---|---|
| Remote URL | HTTPS | SSH |
| 問題位置 | `~/.git-credentials-raphael` 含舊 token | `credential.https://github.com.helper` 被 SSH 推送錯誤觸發 |
| 修復 | `gh auth git-credential store` 更新 store file | 移除 credential helper（SSH 不需要） |

## 預防

若 GitHub 推送使用 SSH，應移除所有 `credential.https://*.helper` 設定，避免 cron 環境下 credential helper 被錯誤呼叫。

## If→Then

**If** cron job 的 SSH push 出現 403 且 error 顯示 `denied to hoonsor`（錯誤帳號）
**Then** 檢查並移除 `git config --global` 中的 `credential.https://github.com.helper`

**If** 要從 SSH URL 的 repo push 但出現 HTTPS 錯誤
**Then** credential helper 被錯誤觸發，移除 `credential.https://*.helper` 設定