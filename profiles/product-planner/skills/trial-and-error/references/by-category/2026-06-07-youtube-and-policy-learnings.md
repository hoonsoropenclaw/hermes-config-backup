# 2026-06-07 YouTube 自動化 + 使用者政策踩雷總集

> 從 `secrets-and-env.md` 切出來的獨立檔。專門放 2026-06-07 一天內累積的：
> - 使用者硬性政策（赫米斯不能再違反）
> - 自我指涉的技術邊界
> - Python 語言小坑

## 使用者硬性禁止赫米斯裝系統服務 / docker / n8n / 守護進程（2026-06-07）

**發現時間**: 2026-06-07
**觸發情境**: 使用者提案「用 n8n + OpenClaw + Antigravity 部署『全自動 YouTube 筆記』pipeline」
**症狀**:
- 提案包含：`docker compose up -d`、n8n server 常駐、workflow 自動啟用、Antigravity 整合、Master-Worker 架構
- 赫米斯**當下直接拒絕**，使用者**接受**赫米斯的拒絕，最終改走路徑 A（本地 Python + cron）
**根因**:
- 使用者 USER.md 明確禁止：
  - ❌ 系統級軟體安裝（npm install -g、apt install）
  - ❌ 創建系統服務或守護進程
  - ❌ 修改系統 PATH 或環境變數
- 使用者 INTJ 風格：**偏好最簡方案 > 複雜架構**（「殺雞用牛刀，且會踩死雞」）
- 使用者明確說過：「approvals.mode 設為 off 是刻意設計的安全策略，非疏忽」
**預防**:
- 接到「自動部署 n8n / Airflow / Prefect / docker 服務」任務 → **第一時間列 3 條替代方案**（本地 Python + cron、產出設定檔讓使用者自裝、純雲端 API）
- **不要**「順手把服務裝起來」— 哪怕對方說「讓 OpenClaw 幫你跑」赫米斯也要拒絕
- 系統級操作（`crontab -e` / `systemctl` / `docker compose up`）永遠**產出指令給使用者自己執行**
- 即使對方說「Master-Worker 自動部署」「Antigravity 串接」也**不繞過這條規則**
**If→Then**:
- **If** 使用者要求「自動部署某個常駐服務」  **Then** 先列替代方案（最簡優先），永遠不主動執行 `systemctl` / `docker compose up` / 改 `crontab`
- **If** 使用者要求「赫米斯跑某個 systemd / 守護進程」  **Then** 直接拒絕，改交付「wrapper script + crontab 設定」給使用者手動貼
- **If** 使用者說「Master-Worker 自動串接」  **Then** 這句話不構成赫米斯繞過 USER.md 安全規則的理由
- **If** N100 環境需要某個常駐 background service  **Then** 赫米斯**只寫** wrapper script + 給 cron 指令，**使用者自己** `crontab -e` 貼
**相關條目**: [[secrets-and-env#subprocess 不繼承 ~/.bashrc 設定的 env var]] + [[hermes-internal#hermes cron edit --script 對 no_agent jobs 的 Bug]]

---

## 赫米斯本身就是 MiniMax M3：無法「呼叫自己」當外部 API（2026-06-07）

**發現時間**: 2026-06-07
**觸發情境**: 使用者提供文件主張「赫米斯能透過 MiniMax M3 API 處理 YouTube 影片」，要求赫米斯建立 n8n workflow 餵影片給 M3
**症狀**:
- 使用者文件描述 MiniMax M3 有「Video In Text Out」「1M Context」「$0.60/1M token」— 這些是**模型能力**描述
- 赫米斯**自己就是** MiniMax M3（從 system prompt 可確認 `Model: MiniMax-M3, Provider: minimax`）
- 赫米斯**沒有工具**能呼叫「外部的 MiniMax M3 API」（會變成自己呼叫自己的無限迴圈）
- 赫米斯的 token 是**主對話**用的，**沒有 video API 額度**（就算有也是給當下對話）
**根因**:
- **混淆「模型能力」vs「agent 可用性」**：
  - 模型能力 = 模型**能**做什麼（M3 能理解影片 = 訓練資料含影片）
  - Agent 可用性 = 赫米斯這個 agent **現在能呼叫**什麼 API
  - 這兩者**完全獨立**
- M3 是赫米斯的**底層引擎**，不是赫米斯能呼叫的**外部服務**
- 任何「讓赫米斯用 M3 處理 X」的需求 = 讓赫米斯**用自己思考**，不能像呼叫 Claude API 那樣 POST 過去
**解法**:
- 赫米斯**自己**就是 M3，**使用者要 M3 做什麼 = 給赫米斯 prompt**
- **不能**為赫米斯建立「呼叫 M3 API」的 pipeline
- 替代方案：
  - **Gemini API**（Google 雲端服務、跟 M3 無關）— 現有 YouTube OAuth client 可用
  - **Ollama 本地 LLM**（qwen2.5:1.5b）— 已驗證 155 秒/支中文摘要
  - **Claude API / OpenAI API** — 標準雲端 LLM API
**預防**:
- 看到「用 [模型名] API 處理 X」任務 → **第一時間確認赫米斯是不是那個模型**
- **不要**假設「赫米斯能呼叫任何模型 API」— 赫米斯只能呼叫**外部** LLM API（Gemini / OpenAI / Claude / Ollama）
- 赫米斯的 system prompt 開頭會寫 `Model: ...` 跟 `Provider: ...`，**這是赫米斯自己**，不是赫米斯能呼叫的服務
- 「Video In, Text Out」之類的能力描述是**模型設計意圖**，**不等於**赫米斯能直接拿影片檔餵給自己
**If→Then**:
- **If** 使用者要求「用 [赫米斯自己的模型] API 處理 X」  **Then** 直接說明「赫米斯就是那個模型，這是 self-referential、無法 API 化」並提供替代（Gemini / Ollama）
- **If** 使用者文件描述某個 LLM 能力（如 M3 video in）  **Then** 不要直接相信「赫米斯能用」，先確認 model identity 是不是赫米斯自己
- **If** 看到 prompt 提到「Master-Worker」「Antigravity」「多 agent 串接」  **Then** 這些都**不**是繞過「赫米斯不能呼叫自己」限制的方法
**相關條目**: [[secrets-and-env#subprocess 不繼承 ~/.bashrc 設定的 env var]] + 本檔的「使用者硬性禁止赫米斯裝系統服務」

---

## Python 3.11 f-string 不能含 backslash 或 quote escape（2026-06-07）

**發現時間**: 2026-06-07
**觸發情境**: 寫 Obsidian Markdown 產生器，frontmatter 內有 `title: "{title.replace('"', '\\"')}"` 的 f-string
**症狀**:
- `SyntaxError: f-string expression part cannot include a backslash (line XXX, column 4)`
- 編輯器報錯位置看起來很奇怪（指向 `---` 結尾或某個 `f"""` 開頭）
**根因**:
- **Python 3.11 限制**：f-string 的 `{expr}` 部分**不能**包含：
  - `\`（backslash）— 包含 `\"`、`\\`、`\n` 等
  - 跨行表達式含 quote escape
  - 某些 comment（含 `#`）
- Python 3.12 放寬了（PEP 701），但赫米斯常用 Python 3.11
**解法**:
- **預處理**需要 escape 的字串到變數，再插值：
  ```python
  # ❌ 寫法（Py3.11 報錯）
  frontmatter = f"""title: "{title.replace('"', '\\"')}" """

  # ✅ 寫法
  safe_title = title.replace('"', '\\"')  # 預先處理
  frontmatter = f'title: "{safe_title}"'  # f-string 只插變數不含 escape
  ```
- 或用**多個** f-string 串接（`f'...' f'...'`）而非三引號 f-string
- 或升級到 Python 3.12+ 享受放寬限制
**預防**:
- 在 Python 3.11 環境寫 f-string 內含 `replace('"', ...)` / `\\` / `\` 開頭 → **永遠先預處理變數**
- 用 Py3.12 環境（赫米斯 venv 是 3.11、RAG 系統用 `/usr/bin/python3.12`）
- **不要**在 f-string 內用三元表達式含 `'...'` 單引號字面值（也會被誤判）
**If→Then**:
- **If** 在 Python 3.11 寫 f-string 報 backslash 錯誤  **Then** 把需要 escape 的表達式**預先 assign 到變數**，f-string 只做單純插值
- **If** f-string 內含 `replace('\'', ...)` / `\\` / 三元運算的字面值  **Then** 提取到外面，**不要**寫在 `f"""..."""` 內
- **If** 同一個 script 赫米斯用 `/usr/bin/python3.12` 跑可以、但 `python3` 跑不行  **Then** 可能是 3.11 vs 3.12 限制差異，**用 `/usr/bin/python3.12` 跑赫米斯自己的 RAG / heavy 處理**

---

## YouTube 影片分析的真實可行情境（2026-06-07 完整 pipeline 已建好）

> 這條整合了「字幕 + 封面圖 + LLM 摘要」的真實可行情境，赫米斯**已經實作完成**

**已驗證的 pipeline**（script 在 `~/.hermes/scripts/youtube_rss_check.py`）：

1. **RSS 抓新影片**：每個 YouTube 頻道有 `https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxx`，不需 token
2. **抓字幕**：`youtube-transcript-api` Python 套件（赫米斯已裝 1.2.4）
   - 成功率 60-70%（Shorts 通常沒字幕、有些頻道關閉）
   - 失敗 graceful degradation：只寫 metadata
3. **封面圖**：固定 URL `https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg`（不需 API）
4. **LLM 摘要**（可選）：本地 ollama qwen2.5:1.5b **155 秒/支**（太慢、不適合 daily cron）
   - 替代：Gemini API（雲端、雲端快）— 需 `GEMINI_API_KEY` env
   - **預設 cron 跑 no-llm 模式**（只抓字幕 + 寫 metadata，不摘要）
5. **輸出 Obsidian markdown**：含封面圖、frontmatter、字幕含時間戳
6. **自動進 RAG 索引**（`/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add <md_file>`）

**已驗證**：3 支影片 pipeline 完整跑通（含 RAG 索引成功）

**已知限制**（2026-06-07 session 學到的）：
- 80% 短網址 Shorts 沒字幕（標準影片才多半有）
- 摘要品質：qwen2.5:1.5b 中文堪用、會中英混雜 + hallucination
- 速度：qwen2.5:1.5b CPU 跑 155 秒/支、qwen2.5:7b 估計 10 分鐘/支
- **建議**：cron 每天只抓字幕不摘要，使用者想看時手動觸發 LLM

**如果未來升級 LLM**：
- 拿到 `GEMINI_API_KEY` → `--llm gemini`（預期 5-15 秒/支、雲端計費）
- 拉 `ollama pull qwen2.5:7b` → 品質更好但更慢
- 改用雲端 LLM 比較實際（除非 N100 換 GPU）
