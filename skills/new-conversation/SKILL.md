---
name: new-conversation
description: "結束 session 前先掃描本次對話,自動列出值得紀錄的 L3 抽象教訓,讓使用者確認後納入 trial-and-error skill,然後使用者手動打 /new 開新對話。觸發:使用者想「掃雷 + 開新對話」的工作流,等於把 /new 之前的掃雷 SOP 自動化。"
version: 1.0.0
author: Hermes Agent (auto-saved)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [session, trial-and-error, workflow]
    aliases: [新對話, wrap-up, end-session]
---

# /new-conversation — 結束 session 前自動掃雷

結束 session 前的標準工作流:掃雷 → 確認寫入 → 開新對話。

**別名（中文）**: `/新對話`、`/結束對話`
**別名（英文）**: `/wrap-up`、`/end-session`

> 注意:hermes skill 自動掃描機制會把 skill 名稱 sanitize 成英文小寫加連字號,
> 所以實際 slash command 形式是 `/new-conversation`(以及未來如果加 alias 也會被 sanitized)。
> 中文 /新對話 在 hermes 內部以「description 中說明」的方式告知使用者,
> 赫米斯在 cli/gateway 顯示時也會列出此 skill,使用者看到中文描述即可。

## 何時觸發

- 使用者明確說「結束對話」「要走了」「/新對話」「/wrap-up」之類
- 使用者輸入 `/new-conversation`
- 不觸發:使用者只是要查詢、跑單一工具、不準備結束

## 標準作業流程

### Step 1 — 確認要掃雷
```
你: /新對話
我: 收到,準備掃雷。要繼續嗎?(預設 5 秒後自動繼續)
```

如果對話很短(< 5 輪 user 訊息),直接回「這次對話太短,沒有需要掃的,直接打 /new 開新 session 吧」並跳過。

### Step 2 — 掃描本次對話
從 state.db 撈這次 session 的所有訊息:
```python
# 簡化版
import sqlite3
conn = sqlite3.connect("~/.hermes/state.db")
msgs = conn.execute(
    "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
    (current_session_id,)
).fetchall()
```

### Step 3 — 過濾 L3 候選
識別「症狀 + 根因 + 解法」三段式都有的踩雷,排除:
- L1 具體操作(命令列、時間戳、輸出)
- L2 步驟細節(要時 session_search 撈)
- 任務進度、commit/PR 編號
- 已知/已記的條目(比對 trial-and-error skill 已有的 by-category 檔)

### Step 4 — 列出候選清單
格式:
```
本次對話掃到 N 條可能的 L3 抽象教訓:

  1. [簡短標題]
     分類建議: gpg-encryption / gh-cli-and-github / vercel-deployment /
              python-sandbox / secrets-and-env / browser-automation
     一句話描述: <症狀 + 根因 + 解法 濃縮成一句>

  2. [簡短標題]
     ...

請問要納入哪些?(輸入數字多選,例如「1,3」)
或輸入「全部」/「跳過」
```

### Step 5 — 寫入
對每條確認的候選,按 `~/.hermes/skills/trial-and-error/templates/entry-template.md` 格式
新增到對應分類檔的 `references/by-category/<name>.md` 末尾。

### Step 6 — 回報
```
新增 N 條踩雷到 trial-and-error:
  - gpg-encryption.md: 1 條
  - python-sandbox.md: 2 條
  - secrets-and-env.md: 0 條
  - ...

跳過 M 條(使用者未勾選或無新內容)。
```

### Step 7 — 提示手動開新 session
```
掃雷完成。準備好後請手動輸入 /new 開新 session。
(不會自動觸發 /new,讓你保留最後確認權)
```

## 例外情況

- 使用者說「這次不用掃」「跳過」 → 跳過掃雷,直接提示 /new
- 對話太短(< 5 輪 user 訊息) → 不掃
- 沒看到新踩雷 → 不囉嗦、直接回「沒有新踩雷,直接打 /new 即可」
- session 已經在做 `/new` / `/reset` 流程中 → 跳過,避免重複

## 核心原則

- 預設自動掃
- 不預設自動寫(**詢問 → 確認 → 才寫**)
- 保留使用者最終決定權
- 不自動觸發 /new(避免掃雷到一半被切斷)
- 失敗時優雅降級:state.db 撈不到 → 改用上下文記憶判斷

## 與其他 skill 的關係

- **trial-and-error**:這個 skill 的輸出目標(候選條目最終寫到 trial-and-error)
- **alt-token-secrets-layout**:加密相關的踩雷會歸到 trial-and-error/references/by-category/{gpg-encryption,secrets-and-env,python-sandbox}.md

## 維護提醒

- 每 3 個月檢查一次 skill 是否仍被自動掃描(`scan_skill_commands()` 結果)
- 改名要同步更新使用者的中文/英文別名
- 任何 SOP 變更,也要同步更新 MEMORY.md 的「/new 自動掃雷 SOP」段落
