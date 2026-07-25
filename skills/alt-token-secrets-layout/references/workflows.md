---
name: alt-token-secrets-layout
description: "適用本 skill 的小型工作流:memory 膨脹控制、token 在對話中的傳遞禮儀"
---

# 小型工作流

## Memory 膨脹控制（2026-06-05 user preference）

使用者對「赫米斯長期記憶膨脹」的明確態度：

  - **預設不寫記憶**：完成任務、踩坑修復、做完部署後,赫米斯**不主動 add 進記憶**
  - **明確指示才寫**：「把這個記起來」「這個以後會用到」「寫進記憶」才動手
  - **例外**（赫米斯可主動建議一次、仍須使用者確認）：
    - 穩定偏好（INTJ 性格、想看結構化輸出、要繁體中文等）
    - 環境事實（gpg 版本、headless 無 keystore daemon、IP/主機名等）
    - 新建立的長期檔案/工具路徑（如本 skill 建立的 `~/.local/share/hermes/secrets/`,赫米斯需要知道它的存在）
  - **不寫**：任務進度、已完成的工作、具體 PR/issue 編號、commit SHA、單次 session 結果、token 字串本身、機密內容
  - **7 天內會過期的東西不入記憶**
  - 短期 session 細節、要回憶時用 `session_search` 撈
  - **定期清理**：MEMORY.md 超過 25 KB 時赫米斯主動建議掃一次、刪除過時條目

**這個偏好是跨 skill 適用的**——任何赫米斯任務都該自動套用,不只本 skill。

### 在本 skill 的具體應用

- 寫入記憶時,寫「**佈局存在的事實 + 路徑 + 加密參數 SOP**」,**不寫**「這次加密了哪個 token、給哪個 service 用」
- 單次操作紀錄（具體刪了哪些 repo、哪次部署）**不入記憶**,用 `session_search` 撈
- 加密參數（AES-256 + s2k 設定）**入記憶**（未來可重複使用）,但使用者選的 cipher / 路徑偏好（如不想分兩個目錄）**不入記憶**（太具體、可能下次就改）

## Token 在對話中的傳遞禮儀

**強烈禁止**：
- ❌ 使用者把 token 貼在對話框
- ❌ 赫米斯在回應中印出明文 token
- ❌ 赫米斯把 token 寫進任何 .md / .log / session transcript 檔
- ❌ 把 token 當作 URL query string 的一部分傳遞（會留在 access log、proxy log）

**正確做法**：
- 使用者用 `echo "ghp_xxx" > ~/.config/hermes/alt_gh_tokens/<account> && chmod 600` 寫到隔離檔
- 赫米斯**只讀檔、不印內容**——只在內部使用
- 對話中討論 token 時用「ghp_***」或「<token>」這種遮罩形式
- 備份環境變數時,只存 encrypted blob,不要解密後再存

**意外發生時的處置**：
- 若 token 已在對話框曝光,立即：
  1. 提醒使用者去 GitHub revoke 該 token
  2. 重新發一組新 token
  3. 把舊 token 從所有可能的位置（含對話紀錄、log）徹底清除
  4. 即使 LLM 對話紀錄本身無法事後清除,**新 token 也要立刻換**
- 若 token 在 sandbox 內意外被印出（`print(token)`）→ 立刻停止、重新發 token,sandbox 的 stdout 可能進 log

## 跨 session 重用 token 的標準流程

使用者說「用 hoonsor 帳號做 X」時：
1. 讀 `~/.local/share/hermes/secrets/.hoonsor_passphrase` 拿密碼
2. GPG 解密 `~/.config/hermes/alt_gh_tokens/hoonsor.gpg` 拿 token
3. 注入 `GH_TOKEN` 環境變數
4. 走 `gh api` 或 curl 呼叫
5. **不要**印出任何解密中間值

整個鏈路赫米斯內部完成,使用者看不到任何 token 字串。
