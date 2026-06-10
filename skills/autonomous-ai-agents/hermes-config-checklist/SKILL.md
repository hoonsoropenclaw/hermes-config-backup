---
name: hermes-config-checklist
description: "赫米斯工具鏈配置檢查清單：依優先順序設定 API tokens、啟用工具能力、驗證工具可用性。當用戶問「如何設定 X 的 API」或「抓取各個 API token」時使用。"
version: 1.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [setup, tokens, api-keys, tools, configuration]
    triggers: [api-token, setup-tool, configure, hermes-config, tool-enable]
---

# Hermes 工具鏈配置檢查清單

## 使用時機
- 用戶問「如何設定 X 的 API Key」
- 用戶問「抓取各個 API token」讓工具可用
- 用戶要求「統整並列出詳細的修正方向建議」（P0 → P1 → P2 優先順序）

## 第一步：查看當前狀態

```bash
hermes status
```

這會顯示：
- 哪些 API Keys 已設定（`✓`）vs 未設定（`✗`）
- 哪些 Auth Providers 已登入
- 哪些工具可用

---

## 第二步：優先順序框架

### P0 — 立竿見影（設定後立即能用）

| 工具/服務 | 設定指令 | 啟用技能 |
|-----------|----------|----------|
| **GitHub** | `gh auth login` | `github`, `github-pr-workflow`, `github-issues`, `github-code-review` |
| **Tavily 搜尋** | 申請 key → `hermes config set secrets.tavily.key your_key` | `web_search` 底層 |
| **Vercel** | `vercel login` | `frontend-dev` 部署 |

### P1 — 開啟高階功能（值得投資）

| 工具/服務 | 取得地點 | 用途 |
|-----------|----------|------|
| **OpenAI** | https://platform.openai.com | Codex CLI、Codex coding agent |
| **DeepSeek** | https://platform.deepseek.com | 便宜國產模型、程式碼任務 |
| **Google Gemini** | https://aistudio.google.com | 多模態模型（圖片/影片分析） |
| **Firecrawl** | https://firecrawl.dev | 將網站轉換為 LLM 可讀格式 |

### P2 — 工作流強化（長期有價值）

| 工具/服務 | 取得地點 | 用途 |
|-----------|----------|------|
| **Discord Bot** | https://discord.com/developers | 整合 Discord 通知 |
| **阿爾丁 Alpha Vantage** | https://www.alphavantage.co | 股票/外匯 API（需翻牆） |
| **Tiingo** | https://tiingo.com | 股票數據，有免費層 |

---

## 第三步：驗證工具是否正常

設定 token 後，用一個簡單命令驗證：

```
# 驗證 GitHub
gh auth status

# 驗證 Tavily
curl -s "https://api.tavily.com/search?query=test&api_key=$TAVILY_KEY" | head -50

# 驗證 Vercel
vercel whoami
```

---

## 第四步：金融工具配置邏輯

金融工具不需要一次全設定。先確認用戶用哪個資料源：

| 資料源 | API Key 需求 | 適用場景 |
|--------|-------------|----------|
| **Yahoo Finance (yfinance)** | 不需要，Python 套件 | 用 `terminal` + Python 呼叫 |
| **Alpha Vantage** | 需要免費 key | 股票/外匯/指標 |
| **Twelve Data** | 需要 freemium key | 即時股票數據 |
| **Tiingo** | 需要免費 key | 股票數據 |

---

## 第五步：Dangerous Command 審批設定（approvals.mode）

`approvals.mode` 控制危險命令的審批行為：

```yaml
approvals:
  mode: manual   # manual | smart | off
```

| Mode | 行為 |
|------|------|
| `manual`（預設）| 對所有危險命令顯示互動式審批對話框 |
| `smart` | 用輔助 LLM 評估命令是否真的危險——低風險自動通過，高風險才問你 |
| `off` | 完全跳過審批（等同 `HERMES_YOLO_MODE=true`）|

**設定方式**（`~/.hermes/config.yaml`，用 `sed` 直接改避免 YAML 解析問題）：
```yaml
approvals:
  mode: 'off'   # ⚠️ 用單引號避免 YAML 解析成布林
  timeout: 60
  cron_mode: deny
  mcp_reload_confirm: false
  destructive_slash_confirm: false
```
**實際設定**（2026-05-30）：`mode: 'off'`，`hermes config set` 會寫成布林，要用 `sed -i "s/mode: false/mode: 'off'/" ~/.hermes/config.yaml` 修正。

**其他相關設定**：
```yaml
# 破壞性斜槓命令（/rm, /delete 等）無需確認
approvals:
  destructive_slash_confirm: false
```

---

## 第六步：hermes-agent 配置相關

### tool_use_enforcement 設定

**重要修正（2026-05-30）**：

| 設定值 | 行為 | 觸發模型 |
|--------|------|----------|
| `"auto"`（預設）| 只有 GPT/Codex/Grok/Gemini 等收到 enforcement | MiniMax 不在列表，會被排除 |
| `true` | 所有模型強制 enforcement | **所有模型（含 MiniMax）** |
| `false` | 完全關閉 | — |
| `["gpt", "codex"]` | 自定義模型列表 | 自定義 |

**設定方式**：
```bash
hermes config set agent.tool_use_enforcement true
```

### 兩個不同的強制機制（重要觀念澄清）

千萬不要混淆這兩個東西：

| 機制 | 作用 | 適用範圍 |
|---|---|---|
| **Skills Scan**（系統提示的 `available_skills` 段落） | 遇到任務時，先查有沒有相關技能，有就加載 | **所有模型，Universal** |
| **Tool Use Enforcement**（`tool_use_enforcement` 設定） | 不要只說要做什麼，實際呼叫工具 | 受模型名稱限制（auto）或全部（true） |

`tool_use_enforcement` 不是「遇到情況先去查技能」，而是「不要只描述意圖，要實際執行」的約束。

**Enforcement 對話示例**：
```
沒有 enforcement: 模型說「我來幫你搜尋...」然後結束，沒有實際呼叫
有 enforcement:    模型說「我來搜尋」→ 同一回覆裡直接 web_search(...)
```

---

## 常見設定命令

```bash
# 設定 API key
hermes config set secrets.tavily.key your_key
hermes config set secrets.github.key your_key

# 設定模型
hermes model

# 登入 auth provider
hermes auth add nous --type oauth
hermes auth add minimax-oauth

# 檢查狀態
hermes status
hermes doctor
```

---

## 對話統整模式

當用戶要求「統整並列出詳細的修正方向建議」時，使用以下結構：

```
1. 目前已設定 vs 未設定（以表格呈現）
2. 詳細修正方向，建議分 P0 / P1 / P2 三個階
   - 每個項目：工具名、狀態、取得方式、設定指令
3. 總結優先順序和建議實作順序
```

---

## 第七步：替代 Token 與多帳號工作流（2026-06-05 session 新增）

> **場景**：使用者有多個 GitHub / Vercel 帳號，備用帳號的 token 不走 `gh auth login`（通常因為缺 `read:org` scope 或有其他限制），需要本地保存並跨 session 重複使用。

### 核心原則

- **不要把 token 寫進 `~/.bashrc`**（會被 shell history 留下、會被任何備份工具抓走）
- **不要把 token 寫進 `~/.hermes/.env`**（混在主帳號 secrets 裡容易誤刪）
- **不要在對話框貼 token**（任何 LLM 對話都可能 log、上傳、留 cache）
- **統一走 `alt-token-secrets-layout` 技能**（GPG 對稱加密 + 雙目錄分離）

### 多帳號切換工作流（GitHub 為例）

```bash
# 1. 主帳號走 gh CLI（標準）
gh auth login                              # 標準 OAuth / token
gh auth switch --user <username>          # 同一 host 多帳號切換

# 2. 備用帳號：token 存到隔離檔、由 GPG 加密（不要直接灌進 gh）
echo "ghp_新token" > ~/.config/hermes/alt_gh_tokens/<account>
chmod 600 ~/.config/hermes/alt_gh_tokens/<account>
# 然後照 alt-token-secrets-layout 加密

# 3. 未來用備用帳號時:
GH_TOKEN=*** gpg --batch --pinentry-mode loopback \
    --passphrase-file ~/.local/share/hermes/secrets/.<account>_passphrase \
    --decrypt ~/.config/hermes/alt_gh_tokens/<account>.gpg)
gh api user
```

### gh CLI 已知坑（影響多帳號工作流）

| 坑 | 解法 |
|---|---|
| `gh auth login --with-token` 對缺 `read:org` 的 token 失敗 | 改用手寫 `~/.config/gh/hosts.yml` 的 `users:` 區塊 |
| `gh auth status` 對「手寫進 yml 但缺 scope」的帳號標 X，但實際仍可用 `GH_TOKEN` 走 API | 這是正常現象，不要看到 X 就以為帳號壞了 |
| 同一個 `github.com` 主機只能有一個 active 帳號 | 用 `gh auth switch --user <username>` 切換，或用 `GH_TOKEN` 環境變數繞過 |
| 手動改 `hosts.yml` 之前一定要備份 | `cp hosts.yml hosts.yml.bak`，否則 gh 內部 cache 跟 yml 不一致會很難除錯 |

### 載入到這個工作流

**完整 SOP**（雙目錄佈局、GPG 參數、shred 步驟、Python sandbox 遮罩陷阱、端到端驗證）見 `alt-token-secrets-layout` 技能。

**觸發關鍵字**：當使用者說「幫我存這個 token」「我想保留這個 PAT 給未來用」「用 hoonsor 帳號」（= 切到備用帳號）「刪除/清掉備用帳號的 repo」時，**先載入 alt-token-secrets-layout**。

---

## 支援檔案

- **`references/sop-enforcement.md`**（在 `hermes-self-improvement` 技能下）— SOP 強制執行架構
- **`references/token-priorities.md`** — 各工具優先順序詳細說明
- **`references/mempalace-mcp-config.md`** — MemPalace MCP Server 配置（含 args 語法、29 tools、測試指令）
- **`alt-token-secrets-layout`**（獨立技能）— GPG 加密 + 雙目錄分離儲存替代 token 的完整 SOP
