# GitHub push 卡死 troubleshooting 完整流程

> **2026-06-10 從 v4 backup push 卡死修復歸納**。任何 v4+ 備份腳本 / git push 失敗都適用。
> 對應 SKILL.md 第 10.6 / 10.7 段。

## 症狀識別

**`git push` 卡死不一定是 push 失敗**——有 3 種「卡」:

| 症狀 | 真凶 | 對應修法 |
|---|---|---|
| push 進度跑到 95% 後 server 端 disconnect | 單一大 blob(>100MB)被拒 | 見下方「情境 A」 |
| push 進度跑到 N% 完全卡住、不報錯 | SSH handshake 卡死 或 rclone 類似 | 見下方「情境 B」 |
| push 沒報錯但 `git rev-list` 顯示本地領先 | `gh auth` 跟 `git config` 帳號不一致 | 見下方「情境 C」 |

## 情境 A:push 95% 卡死(單一大 blob)

### 症狀
```
Writing objects: 95% (233/243), 40.15 MiB | 215.00 KiB/s
send-pack: unexpected disconnect while reading sideband packet
```
**本地驗證**:`git rev-list --left-right --count main...origin/main` 回 `1 0` 或 `2 0`。

### 修法(3 步)

**Step 1:找大物件**
```bash
# 找 staging 內 > 50MB 的 blob
find .git/objects -type f -size +50M 2>/dev/null
# 找 pack 內最大物件
git verify-pack -v .git/objects/pack/*.pack | sort -k3 -rn | head -5
# 看哪個 commit 引入
git log --all --pretty=format:"%H %s" --diff-filter=AM -- '**/skills.tar*'
```

**Step 2:清空 staging 並重 init**(必走)
```bash
cd ~/.hermes/hermes-backup-staging
rm -rf .git profiles skills memories scripts cron docs config.yaml
git init -q -b main
git config user.email "<your-email>"
git config user.name "<your-name>"
git remote add origin https://github.com/<user>/<repo>.git
```

**Step 3:重跑 rsync + force push**
```bash
# 跑修補後的 v4 腳本
bash ~/.hermes/scripts/hermes-backup-v4.sh --tier1

# force push(注意:不是 --force-with-lease)
git push --force --progress origin main
```

### 為何不用 `--force-with-lease`
新 init 的 `.git` 沒有共同祖先,`--force-with-lease` 會 reject 並報 `stale info`。**用 `--force`** 才是對的。

## 情境 B:push 完全卡住不報錯(SSH handshake)

### 症狀
`git push` 跑了 60s+ 完全沒進度、`Ctrl+C` 沒用、`ps aux | grep git` 還在。

### 修法
1. `Ctrl+C` 砍掉
2. 換 HTTPS:`git remote set-url origin https://github.com/...`
3. `git push` 試一次
4. **如果還是卡** → `gh auth setup-git`(見情境 C)

## 情境 C:`Permission denied to <備用帳號>`

### 症狀
```
remote: Permission to <org>/<repo>.git denied to <備用帳號>.
fatal: unable to access 'https://github.com/.../': The requested URL returned error: 403
```

### 真凶
`~/.gitconfig` 設了:
```ini
[credential]
    helper = store --file ~/.git-credentials-raphael
```

裡面存的是**舊帳號 token**(`hoonsor:ghp_xxx@github.com`)。`gh auth switch` **不會**改 git 全域認證。

### 修法
```bash
gh auth setup-git
```

這會在 `.gitconfig` 自動注入:
```ini
[credential "https://github.com"]
    helper =
    helper = !/usr/bin/gh auth git-credential
[credential "https://gist.github.com"]
    helper =
    helper = !/usr/bin/gh auth git-credential
```

之後 `git push` 就用 `gh auth status` 顯示的 active 帳號 token。

### 帳號管理 SOP
- `gh auth status` — 看當前 active 帳號是誰
- `gh auth switch --user <name>` — 切換 gh CLI active 帳號
- `gh auth setup-git` — 讓 git 用 gh active 帳號(必跑一次)
- 推 push 前永遠先 `gh auth status` 確認

## 驗證 SOP(必跑)

任何 push 完成後必驗證:
```bash
git rev-list --left-right --count main...origin/main
```
- 回 `0 0` = 完全同步
- 回 `N 0`(N > 0)= 有 N 個 commit 沒推上去 → 必查
- 回 `0 N` = remote 領先(罕見、可能是別人推到同 repo)

**If** push 完成沒報錯
**Then** **不要相信**、**必跑驗證**
**Then** `0 0` 才能標記備份成功
