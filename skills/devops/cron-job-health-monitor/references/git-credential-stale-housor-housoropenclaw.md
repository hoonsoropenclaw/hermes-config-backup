# 類型 J2：Git 憑證過期導致 Stale Push Error（2026-06-11）

## 觀察背景

2026-06-11 `hermes-config-backup-daily` (65f2dc3583d5) 和 `v4-backup-tier1-daily` (108ce8cabdfc) 的 git push 在 cron 環境失敗：
```
remote: Permission to hoonsoropenclaw/hermes-config-backup.git denied to hoonsor.
fatal: unable to access 'https://github.com/hoonsoropenclaw/hermes-config-backup.git/': The requested URL returned error: 403
```

但從 login shell 手動執行 `git push origin main` 成功。

## 根因分析

### 問題分解

1. **gh auth status** 顯示 `hoonsoropenclaw` 已登入（SSH 協議）
2. 但 `hermes-backup-staging` 的 remote URL 是 `https://github.com/...`（HTTPS，非 SSH）
3. `~/.git-credentials-raphael` 存有 `https://hoonsor:ghp_akP3...SXQO@github.com`（舊 `hoonsor` 帳號）
4. `gh auth git-credential` 的 store helper 仍使用 store file 的舊 token
5. Scheduler 的 git push 走 credential.helper → 拿到舊 hoonsor token → 403
6. Login shell 的 git push 因為 `gh auth git-credential store` 已更新（上次 session 觸發過）→ 成功

### 觸發流程

```
hermes-backup-staging 的 git config:
  credential.helper = store --file ~/.git-credentials-raphael
  credential.https://github.com.helper = !/usr/bin/gh auth git-credential
```

當 cron scheduler 執行 `git push` 時：
1. git 查 credential helper：`~/.git-credentials-raphael` 有舊 hoonsor token
2. 優先使用 store file 的舊 token（`ghp_akP3...`）而非 gh 的新 token
3. GitHub 收到 `hoonsor/舊token` → 403 denied

### 為什麼 login shell 成功

從 login shell 手動執行 `git push` 時，`gh auth git-credential store` 在背景執行，把正確的 `hoonsoropenclaw` token 更新到 `~/.git-credentials-raphael`。但 cron 子進程沒有這個互動式觸發，所以一直用舊 token。

## 修復步驟

### 步驟 1：強迫 gh auth git-credential store 更新

```bash
# 在 staging repo 觸發一次 git push，強制 gh auth git-credential store 更新
cd ~/.hermes/hermes-backup-staging && git push origin main 2>&1
```

### 步驟 2：驗證 store file 更新

```bash
# 檢查 ~/.git-credentials-raphael
cat ~/.git-credentials-raphael
# 應該顯示 https://hoonsoropenclaw:ghp_SF...g2ex@github.com
# 不是 https://hoonsor:ghp_akP3...SXQO@github.com

# 確認只有 hoonsoropenclaw
grep -o 'https://[^:]*:' ~/.git-credentials-raphael
# 應該只有 hoonsoropenclaw，不是 hoonsor
```

### 步驟 3：若仍未更新，手動編輯 store file

```bash
# 備份
cp ~/.git-credentials-raphael ~/.git-credentials-raphael.bak.$(date +%Y%m%d)

# 替換舊 hoonsor URL 為 hoonsoropenclaw
sed -i 's|https://hoonsor:ghp_[a-zA-Z0-9]*@github.com|https://hoonsoropenclaw:ghp_SFvS2ex@github.com|g' ~/.git-credentials-raphael

# 驗證
cat ~/.git-credentials-raphael
```

### 步驟 4：驗證 git push 成功

```bash
cd ~/.hermes/hermes-backup-staging && git push origin main
# 預期：Everything up-to-date (exit 0)
```

### 步驟 5：強迫 cron last_status 翻轉

```bash
# 觸發 scheduler 立即跑一次
hermes cron run hermes-config-backup-daily
sleep 30

# 驗證 last_status
python3 -c "
import json
d=json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
for j in d['jobs']:
    if j.get('id')=='65f2dc3583d5':
        print('last_status:', j.get('last_status'))
        print('last_run_at:', j.get('last_run_at'))
"
```

## 預防設計

### 方案 A：只用 gh auth git-credential（推薦）

```bash
# 從 staging 的 git config 移除 store helper，只用 gh auth
cd ~/.hermes/hermes-backup-staging
git config --unset credential.helper
git config credential.https://github.com.helper '!/usr/bin/gh auth git-credential'
```

這樣 git push 時 gh 會直接提供正確 token，不依賴 store file。

### 方案 B：定期更新 store file

在 backup script 執行前加一行：
```bash
# 在 hermes-backup-v4.sh 的 tier1 步驟前
cd "$STAGING" && git push --quiet origin main 2>/dev/null || true
# 觸發 gh auth git-credential store 更新
```

### 方案 C：改用 SSH remote

```bash
# 把 hermes-backup-staging 的 remote 從 HTTPS 改成 SSH
cd ~/.hermes/hermes-backup-staging
git remote set-url origin git@github.com:hoonsoropenclaw/hermes-config-backup.git

# 驗證
git remote -v
# origin  git@github.com:hoonsoropenclaw/hermes-config-backup.git (push)
```

SSH 不需要 token，gh auth status 顯示 `Git operations protocol: ssh` 所以已設定好 SSH key。

## 驗證矩陣

| 環境 | 測試方式 | 預期結果 |
|------|---------|---------|
| Login shell | `git push origin main` | ✅ Everything up-to-date |
| Cron 子進程 | `hermes cron run` 觸發 | ✅ last_status: ok |
| 憑證 store file | `cat ~/.git-credentials-raphael` | 只有 hoonsoropenclaw URL |
| gh auth | `gh auth status` | hoonsoropenclaw 登入 |

## If→Then 規則

- **If** git push 被拒 `denied to hoonsor` 但 `gh auth status` 顯示 `hoonsoropenclaw` **Then** 檢查 `~/.git-credentials-raphael` 是否仍有舊 hoonsor token，執行一次 `git push` 觸發 `gh auth git-credential store` 更新
- **If** 憑證檔案已更新但仍有 `hoonsor` URL **Then** 手動編輯 `~/.git-credentials-raphael`，把 `https://hoonsor:ghp_xxx@github.com` 改成 `https://hoonsoropenclaw:ghp_yyy@github.com`
- **If** 想徹底避免此問題 **Then** 把 hermes-backup-staging 的 remote 從 HTTPS 改成 SSH（gh auth 已設定好 SSH key）
- **If** 備份 script 用 HTTPS remote **Then** 確保 credential.helper 只有 `!/usr/bin/gh auth git-credential`，不要加 `store --file ~/.git-credentials-raphael`