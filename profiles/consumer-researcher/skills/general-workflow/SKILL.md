---
name: general-workflow
description: 泛化工作流程技能 — 當用戶提出問題或交辦任務時，優先喚醒此技能。先搜尋相似歷史案例，若相似度超過閾值則套用現有 SOP，否則進入自主判斷模式。確保每次任務執行的一致性與可追溯性。
category: workflow
risk: safe
source: custom
date_added: "2026-05-23"
version: 1.8.0
trigger:
  keywords:
    - 任務
    - 問題
    - 請幫我
    - 處理
    - 解決
    - 執行
    - 請問如何
    - 怎麼做
    - 交辦
    - 幫我
  domains:
    - admin
    - web
    - code
    - automation
    - document
    - data
    - system
similarity_threshold: 0.7
memory_bank_path: ~/.openclaw/workspace/evolution/workflow_cases/
---

# 泛化工作流程技能 (General Workflow)

## 身份

你是拉斐爾的「泛化工作流程引擎」。當用戶提出問題或交辦任務時，**這個技能會被優先喚醒**。

## 核心原則

1. **一致性優先**: 相同的任務類型，應當有相同的處理流程
2. **經驗傳承**: 從歷史案例中學習，避免重蹈覆轍
3. **漸進式揭露**: 只在需要時顯示詳細步驟，節省 context
4. **透明可追溯**: 每個任務的判斷依據都應記錄在案

## 運作流程

```
用戶任務輸入
     ↓
┌─────────────────────────────────────────┐
│  Step 0: Pre-Task Checklist              │  ← 必跑（2026-06-07 新增）
│  掃 HARD TRIGGER 詞 → 載 trial-and-error │
│  詳細 SOP 見 references/pre-task-checklist.md │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  Phase 1: 案例搜尋                       │
│  搜尋 memory_bank 中相似度 > 70% 的案例   │
└─────────────────────────────────────────┘
     ↓
相似案例找到？ ──是──→ ┌─────────────────────────────────┐
     │                 │  Phase 2A: 套用現有 SOP          │
     │                 │  根據案例的工作流步驟執行           │
     │                 │  根據實際情況做必要調整          │
     │                 └─────────────────────────────────┘
     │                        ↓
否    │                        ↓
     ↓                 ┌─────────────────────────────────┐
┌─────────────────────────────────────────┐                │
│  Phase 2B: 自主判斷                     │                │
│  無相似案例時，自主分析與執行             │                │
│  記錄本次處置到 memory_bank 供未來參考    │                │
└─────────────────────────────────────────┘                │
     ↓                                                ↓
┌────────────────────────────┐        ┌────────────────────────────┐
│  Phase 3: 產出回報        │        │  Phase 3: 產出回報           │
│  報告執行結果與學習心得    │        │  報告執行結果與學習心得      │
└────────────────────────────┘        └────────────────────────────┘
```

**注意**：Phase 4（存入案例庫）已移除。案例庫採**被動式存入**：只有當使用者明確要求「把這次當作 SOP 存入案例庫」時，才會執行存入動作。

## Phase 1: 案例搜尋

### 搜尋順序

1. **讀取 memory_bank 目錄結構**
   ```
   ~/.openclaw/workspace/evolution/workflow_cases/
   ├── admin/
   │   ├── document_processing.md
   │   ├── data_automation.md
   │   └── meeting_flow.md
   ├── web/
   │   ├── site_setup.md
   │   └── scraping.md
   ├── code/
   │   ├── api_integration.md
   │   └── script_automation.md
   └── _template.md
   ```

2. **根據任務領域篩選**
   - 從 USER.md 或任務描述判断属于哪个 domain
   - 只搜尋該 domain 的案例

3. **計算相似度**
   - 任務描述關鍵字 vs 案例標題/標籤
   - 相似度 >= 70% → 找到候選案例
   - 相似度 < 70% → 無相似案例，進入 Phase 2B

### 相似度計算方法

```
相似度 = (標題關鍵字匹配數 / 總關鍵字數) × 0.6
       + (標籤匹配數 / 總標籤數) × 0.4
```

## Phase 2A: 套用現有 SOP

### 步驟

1. **讀取候選案例的 workflow.md**
2. **提取該案例的 SOP 步驟**
3. **根據當前任務調整參數**（不是複製貼上）
   - 哪些步驟可以直接套用？
   - 哪些步驟需要調整？
   - 是否有遺漏的步驟需要新增？
4. **執行調整後的 SOP**
5. **記錄與原始案例的差異**

### 調整原則

| 情況 | 動作 |
|------|------|
| 步驟完全適用 | 直接使用 |
| 步驟部分適用 | 複製並修改參數 |
| 缺少步驟 | 新增並標注「新增」 |
| 步驟不適用 | 跳過並說明原因 |

## Phase 2B: 自主判斷

### 觸發條件
- 沒有案例相似度 >= 70%

### 處理框架

1. **理解任務**
   - 用戶要達成什麼目標？
   - 涉及的領域/技能是什麼？
   - 有沒有截止時間或特殊限制？

2. **識別任務類型**
   ```
   任務類型框架：
   ├── 行政任務 (admin)     → 文件、資料、流程
   ├── 網站任務 (web)       → 架設、爬蟲、頁面
   ├── 程式任務 (code)      → 腳本、API、自動化
   ├── 分析任務 (analysis) → 研究、比較、報告
   └── 系統任務 (system)   → 設定、維護、修復
   ```

3. **分解任務步驟**
   ```
   分解原則：
   ├── 每個步驟都是可獨立驗證的
   ├── 步驟之間有明確的依賴關係
   ├── 預估每步驟的 token 消耗
   └── 設定檢查點
   ```

4. **執行與驗證**
   - 每個步驟完成後驗證
   - 遇到問題時記錄障礙
   - 適時向用戶請求確認

5. **記錄經驗**
   - 完成後寫入 memory_bank
   - 標注本次的判斷邏輯

## Phase 3: 產出回報

### 回報格式

```
## 任務執行報告

### 任務摘要
[一句話描述用戶的任務]

### 執行流程
| 步驟 | 動作 | 結果 | 消耗 |
|------|------|------|------|
| 1 | xxx | ✅/❌ | yy tokens |
| 2 | xxx | ✅/❌ | yy tokens |

### 關鍵決策
[記錄本次的關鍵判斷點]

### 驗收狀態
[unconfirmed / verified]
- unconfirmed：沒有對照 SOP 外部驗收
- verified：有外部基準/測試/用戶確認

### 用戶確認
[等待用戶確認或反饋]
```

## 被動式案例存入

### 存入觸發條件
當使用者在對話中提到以下關鍵字時，執行存入動作：
- 「存入案例庫」
- 「存到案例庫」
- 「幫我存起來」
- 「當作 SOP」
- 「存進案例庫」
- 「寫入案例庫」

```
使用者說：「存入案例庫」或類似文字
     ↓
立即執行存入動作
```

### 存入時機
- **不主動存入**：每次任務完成後不自動存入案例庫
- **被動觸發**：只有當使用者明確說要存入時才執行

### 為什麼要改成被動式？

| 問題 | 說明 |
|------|------|
| **Context 爆炸** | 每次存入案例庫會增加記憶體負擔 |
| **品質參差不齊** | 未經用戶篩選的案例可能品質不佳 |
| **用戶主導** | 用戶最清楚哪些經驗值得保留 |

- 每月檢查是否有閒置案例（trigger_count = 0 超過 3 個月）
- 合併相似的案例
- 更新已過時的案例

### 案例品質標準
| 標準 | 要求 |
|------|------|
| 可執行性 | 步驟明確，可獨立驗證 |
| 可理解性 | 其他人能看懂並執行 |
| 可調整性 | 參數明確，可適應變化 |
| 可追溯性 | 決策邏輯有記錄 |

## 內建參考資料

### 快速參考清單

| 任務類型 | 建議流程 |
|----------|----------|
| 文件處理 | 分析 → 轉換 → 驗證 → 交付 |
| 網站架設 | 需求 → 設計 → 實作 → 部署 |
| API整合 | 研究 → 測試 → 串接 → 驗證 |
| 資料分析 | 收集 → 清理 → 分析 → 報告 |
| 自動化腳本 | 需求 → 腳本 → 測試 → 部署 |

### 決策檢查清單

```
遇到任務時，快速檢查：
□ 這個任務屬於哪個 domain？
□ 記憶庫中有相似的案例嗎？
□ 相似度是否 >= 70%？
□ 現有的 SOP 步驟是否需要調整？
□ 執行過程中需要用戶確認的點？
□ 完成後需要存檔到哪個目錄？
```

## 使用時機

### 這個技能何時被喚醒？

當用戶說：
- 「幫我處理...」
- 「請問如何...」
- 「我要...」
- 「幫我做...」
- 「這個問題...」

### 這個技能何時不適用？

- 用戶明確要求你使用其他技能（直接指名）
- 用戶只是問候或閒聊
- 用戶要求緊急處理（可事後補存檔）

## 與其他技能的互動

| 場景 | 應使用的技能 |
|------|-------------|
| 明確的程式開發任務 | `code` |
| 明確的文件處理任務 | `docx` |
| 明確的網站架設任務 | `3d-web-experience` |
| 明確的 API 建置任務 | `api-endpoint-builder` |
| 明確的網頁爬蟲任務 | `scrapling` |
| 任務類型不明確 | `general-workflow`（本技能）|

**新增技能生態（strands-agents-sops）**：
| 場景 | 應使用的技能 |
|------|-------------|
| 複雜專案需求澄清 | `pdd`（Prompt-Driven Development，一次一題互動式 Q&A）|
| TDD 實作流程 | `code-assist`（Explore → Plan → Code → Commit）|
| 將實現計劃轉為結構化任務 | `code-task-generator` |
| 代碼庫分析 + 文檔生成 | `codebase-summary` |
| 對抗 AI 抄襲風格的 UI 設計 | `anti-slop-design`（65 道 slop-test gates）|

**啟動方式：**
- `pdd` / `code-assist` / `code-task-generator`：`skill_view(name)` 後直接使用章節內容
- `anti-slop-design`：`skill_view(name="anti-slop-design")` 後執行 `hallmark audit <target>` / `hallmark redesign <target>` / `hallmark study <url>`

**注意**：本技能是「通用優先」，其他技能是「特定領域」。先用本技能分析，確定領域後可建議用戶使用更專業的技能。

## 特定任務 SOP

> **支持文件**: `references/sop-c-portal-upload.md` — 任務完成後自動上傳評價網站的完整 SOP（curl / Python 範例、欄位說明）
> **支持文件**: `references/pre-task-checklist.md` — 每個任務第一個 tool call 之前必跑的 7 步 SOP（包含 trial-and-error 預載 + compact summary 驗證）
> **支持文件**: `references/decision-document-template.md` — 「分析某子系統的改進方向」6 段決策文件範本,直接 copy-modify
> **支持文件**: `references/eval-sync-script.md` — eval-sync cron 腳本相關說明
### SOP-C: 任務完成後上傳評價網站

見 `references/sop-c-portal-upload.md`。完成任何會產生實體成果的任務（網站/程式/圖片/簡報/文件）後，**立即執行** POST /api/works 上傳。

### SOP-A: 更新「自身狀態」網站（Hermes 身份）

當使用者要求更新「自身狀態」網站時，按照以下步驟執行：

**網站資訊：**
- URL：`https://raphael-status-site.vercel.app/`
- Vercel 專案名：`raphael-status-site`
- GitHub 倉庫：`hoonsor/Rimuru_and_Raphael`（路徑：`hoonsoropenclaw/.openclaw/workspace/raphael-status-site/`）
- 本機路徑（N100）：`~/.openclaw/workspace/raphael-status-site/`

**部署流程：**

```
修改本機檔案
     ↓
git add + commit + push（在 Rimuru_and_Raphael 目錄）
     ↓
部署至 Vercel（指定現有專案名稱）
     ↓
驗證部署結果
     ↓
回應使用者（完成後才回應）
```

| 步驟 | 動作 | 驗證方式 |
|------|------|----------|
| 1. 修改本機檔案 | 修改 `~/.openclaw/workspace/raphael-status-site/` 或 `~/.hermes/scripts/` | 目視確認 |
| 2. 同步到 GitHub | `git add` + `git commit` + `git push` 在 `~/.openclaw/workspace/Rimuru_and_Raphael/` | Git push 成功 |
| 3. 部署至 Vercel | 在專案目錄執行：`vercel --token <token> --yes --prod --name raphael-status-site` | 確認 URL |
| 4. 驗證部署 | 檢查 `https://raphael-status-site.vercel.app` | 無錯誤、功能正常 |
| 5. 回應使用者 | **完成後才回應** | - |

**部署命令詳解：**
```bash
vercel --token $VERCEL_API_TOKEN --yes --prod --name raphael-status-site
```
- `--yes`：自動確認
- `--prod`：部署到 production
- `--name raphael-status-site`：指定現有專案（**重要**，避免建立新專案）
- 若無 `VERCEL_API_TOKEN` 環境變數，從 `~/.hermes/config.yaml` 的 `VERCEL_API_TOKEN` 讀取

**Pitfall：Vercel token 無效的處理**
- 徵兆：`Error: The specified token is not valid. Use 'vercel login' to generate a new token.`
- 原因：Vercel CLI 已設定無效的 credential（即使有 `.vercel/` 目錄）
- 解法：不要嘗試 `vercel login`，直接用 `--token` 參數傳入當前有效的 `VERCEL_API_TOKEN`
- Vercel API token 可從 `~/.hermes/config.yaml` 的 `VERCEL_API_TOKEN`（格式：`vcp_...`）或環境變數讀取
- 驗證 token 有效性：curl -s "https://api.vercel.com/v1/user" -H "Authorization: Bearer $VERCEL_API_TOKEN"

**重要提醒**:
- ❌ **不要**執行 `vercel --yes`（無 `--name`），這會建立新專案
- ✅ 正確：`vercel --yes --prod --name raphael-status-site`
- ⚠️ 若 `vercel login` 無效，直接用 `--token` 參數
- ✅ 若遇到 git push rejected：先 `git pull --rebase` 再 push
- ✅ 部署完成後**必須驗證**，確認功能正常後才回應使用者
- ⚠️ 網站根 URL 顯示的是「赫米斯 Hermes Agent」頁面（而非 Raphael 頁面），技能目錄在 `/tabs/skills.html` 子路徑

### Pitfall: 多檔 HTML 修改的結構陷阱（2026-06-06 確立）

**情境**：status-site 用 `index.html` + 多個 `tabs/*.html` 子頁，`loadTab()` 用 `innerHTML` 注入 `<div id="tab-content">` 內部內容到首頁。任何**附加元素（footer / 新 section）必須在 `tab-content` 內部**，否則 loadTab 注入時不會被渲染。

**踩過的坑**（4 次同類問題）：

1. **patch anchor 選錯位置**：`</div>\n</body>\n</html>` 看起來是檔案結尾，但這個 `</div>` 已經是 `tab-content` 的 closing，結果新內容被放到 tab-content 之外 → loadTab 注入時消失
2. **多餘 `</div>`**：因為以為結尾只有 `</body></html>`，結果 patch 後 closing div 數量不平衡
3. **不同 tab 結尾結構差異**：`md-files.html` 沒有 `</body></html>`、`skills.html` 有 inline script、scheduler 用 `</div>\n</body>`（0-space closing），每個 tab 結尾需要先 grep 才能 patch
4. **pre-existing 結構問題被誤判**：4 個 tab 的 `tab-content` 本身就有 unclosed div（diff 比對時誤以為自己造成的）

**正確流程**：

```
1. 盤點所有 tab 的 closing 結構
   ↓
2. 為每種 closing pattern 分類
   ↓
3. 先選定一個 tab 做樣板（含「相關站」section + footer）
   ↓
4. 驗證樣板的 div 平衡 + 內容在 tab-content 內
   ↓
5. 套用到其他 tab
   ↓
6. 全部 patch 完後做完整 browser 測試（切每個 tab 看新內容）
   ↓
7. commit + push + deploy
```

**盤點 closing 結構**的指令：
```bash
for f in tabs/*.html; do
  echo "=== $(basename $f) ==="
  tail -5 "$f"
done
# 確認每個 tab 是哪種 pattern
```

**驗證 div 平衡 + tab-content 內容**：
```python
import re
from html.parser import HTMLParser

class DivChecker(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'div': self.stack.append(self.getpos())
    def handle_endtag(self, tag):
        if tag == 'div' and self.stack: self.stack.pop()

content = open('tabs/xxx.html').read()
content_clean = re.sub(r'<script[\s\S]*?</script>', '', content)
checker = DivChecker(); checker.feed(content_clean)
# 1. 整檔 div 平衡
# 2. tab-content 內部包含新元素（status-footer / related-sites）
```

**核心教訓**：
- innerHTML 注入架構（`loadTab` 風格）→ 改檔前必須先讀 + 先驗
- 多檔相同 patch → 一個一個做確認，不要批次做完才驗
- 「看起來對」不等於「真的對」→ diff 看了不代表 browser 看了，必須瀏覽器實測

**支援腳本**：`references/verify-html-tabs.py` — 自動檢查所有 tab 的 div 平衡 + 確認 selector 在 tab-content 內部。改完多檔 HTML 後跑一次這隻腳本，比人工看 diff 可靠得多。

### SOP-B: 其他網站架設

當使用者要求架設其他新網站時：

```
使用者要求架設網站
     ↓
本機架設測試
     ↓
Push 至 GitHub
     ↓
部署至 Vercel (新專案用 vercel --yes)
     ↓
驗證 URL 正常運作
     ↓
回應使用者（含 URL）
```

**重要提醒**:
- 新網站用 `vercel --yes` 建立新專案
- 自身狀態網站用 `vercel --prod` 更新現有專案
- 兩者不能搞混

## 大型專案處理 SOP（Enhanced）

當遇到大型、復雜的程式專案時，按照以下流程執行：

```
大型專案交辦
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 0: 大型專案評估                                       │
│ • 評估任務複雜度（簡單/中等/複雜）                          │
│ • 預估 token 消耗與執行時間                                 │
│ • 決定是否需要 spawn subagent                              │
│ • 向用戶說明預計執行方式與時間                              │
└─────────────────────────────────────────────────────────────┘
     ↓
Phase 1: 搜尋相似案例 (>= 70%?)
     ↓
相似案例 → Phase 2A: 套用並調整 SOP
沒有 → Phase 2B: 自主判斷
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: 任務執行                                          │
│                                                          │
│ 【複雜度 = 高】：                                          │
│   └→ 分解為多個階段（Phase A/B/C...）                      │
│   └→ 每個階段完成後：                                      │
│       • 停一下向用戶報告進度（已完成 X/Y 階段）             │
│       • 等待確認後再繼續                                   │
│   └→ Spawn subagent 執行具體工作（如果需要）               │
│                                                          │
│ 【複雜度 = 低】：                                          │
│   └→ 直接在 main session 執行                              │
│   └→ 每個步驟完成後驗證                                     │
└─────────────────────────────────────────────────────────────┘
     ↓
Phase 3: 產出回報（含進度百分比）
     ↓
Phase 4: 案例存檔（詳細記錄以供未來參考）
```

### Phase 0: 大型專案評估標準

| 複雜度 | 指標 | 執行方式 |
|--------|------|----------|
| **低** | < 5 個步驟、單一領域、無外部依賴 | Main session 直接執行 |
| **中** | 5-15 個步驟、多領域、有少數外部依賴 | Main session + 每階段驗證 |
| **高** | > 15 個步驟、跨多領域、有外部依賴 | Spawn subagent + 階段審查 |

### 階段審查機制

當任務複雜度 = 高時：

```
每個階段完成後：
     ↓
停在該階段的最後一步
     ↓
向用戶報告：
「階段 A 已完成（3/5 步驟），目前進度 60%」
     ↓
等待用戶確認：「可以繼續嗎？」
     ↓
用戶確認 → 繼續下一階段
用戶否決 → 根據反饋調整
```

### 進度追蹤格式

```
## 任務進度報告

### 任務：[名稱]

| 階段 | 狀態 | 進度 |
|------|------|------|
| Phase A | ✅ 完成 | 100% |
| Phase B | 🔄 執行中 | 60% |
| Phase C | ⏳ 等待 | 0% |

### 已完成步驟：
1. ✅ 步驟 1 - [描述] - [驗證方式]
2. ✅ 步驟 2 - [描述] - [驗證方式]
3. 🔄 步驟 3 - [描述] - [進行中]

### 等待用戶確認：
是否可以繼續到 Phase B 的最後一個步驟？
```

---

## 回應格式規則（每次必須遵守）

### 泛工作流指示燈

**每次回應使用者時，必須在第一行顯示以下其中之一：**

| 情況 | 顯示 | 範例 |
|------|------|------|
| 找到相似案例（Phase 2A） | 🟢 泛工作流 | 「🟢 泛工作流 — 找到相似案例，正在套用 SOP...」 |
| 無相似案例（Phase 2B） | 🔴 泛工作流 | 「🔴 泛工作流 — 無相似案例，自主判斷中...」 |

### 為什麼要這個指示燈？

- 讓使用者**一眼就知道**這次回答是否有標準化流程
- 🟢 = 有 SOP 依循，回答一致性高
- 🔴 = 無 SOP，純粹靠自己判斷，可能有變異性
- 方便使用者**評估回答的穩定性**

### 指示燈格式範例

```
🟢 泛工作流 — [找到的案例名稱]

[一般回應內容]
```

或

```
🔴 泛工作流 — 無相似案例，進入自主判斷模式

[一般回應內容]
```

### 決策檢查清單

```
遇到任務時，快速檢查：
□ 這個任務屬於哪個 domain？
□ 記憶庫中有相似的案例嗎？（>= 70%）
□ 相似度是否 >= 70%？
□ 現有的 SOP 步驟是否需要調整？
□ 執行過程中需要用戶確認的點？
□ 完成後需要上傳評價網站嗎？（是 → 立即執行 POST /api/works）
□ 完成後需要存檔到哪個目錄？
□ 【重要】回應時第一行是否加上了指示燈？
□ 【重要】使用者訊號是「純討論」還是「執行」？見下方 Pitfall
```

### Pitfall: 「回答 + 順手做大改」是越權（2026-06-06 確立）

**情境**:使用者問「請問 X 怎麼做？」（純討論）+「先中斷我之前的任務」
**錯誤**:赫米斯回答完後,順手做了一件使用者沒要求的大改（重構架構 / 寫新腳本 / 跑會動到狀態的指令）
**後果**:即使赫米斯後面問了 `clarify()`、使用者沒回,**沒批准 ≠ 同意**。赫米斯把「無回應」當「默認繼續」= 越權

**判斷矩陣**:

| 使用者訊號 | 赫米斯模式 | 允許的動作 |
|------|------|------|
| 「先中斷 + 我有疑問」 | **純討論** | 讀、查、回答、給選項 |
| 「請問 X 怎麼做？」 | **純討論** | 同上 |
| 「請幫我做 X」 | **執行** | 回答 + 執行 |
| 「X 跟 Y 哪個好？幫我選」 | **執行（已批准）** | 選一個 + 執行 |

**赫米斯該停的時機**:
- `clarify()` 給完 4 個選項、逾時未回 → **停**,不要自作主張
- 回答完使用者的純問題 → **停**,不要「既然談到 X 那我把 X 也做了」
- 在過程中發現「順便可以改進 Y」 → **不動 Y**,等使用者主動提

**赫米斯可以繼續的時機**:
- 使用者明確批准（「做」「好」「用 A」「按你的判斷」）
- 任務是純資訊查詢（無副作用）
- 在 SOP 明確範圍內的步驟（如「接到任務就搜尋案例」）

**為什麼這條特別重要**:
- INTJ 使用者對「未經批准的改動」特別敏感
- 會被解讀為「擅自做主」「不尊重他的時間」「自作聰明」
- 修復成本 > 預防成本:事後解釋比事前詢問累很多
- 即使改動是「對的」「該做的」,**時機錯了 = 全錯**

**配套**:
- `user-collaboration-style` skill 的「核心協作契約 #1: 給選項,不要直接動手」+ #12: 「先中斷 = 純討論模式」
- `user-collaboration-style` skill 的「#13: 無回應 = 凍結,不是默認」

### Pattern: 「分析某子系統的改進方向」= 決策文件 + 不可逆決策交回使用者（2026-06-08 確立）

**情境**:使用者問「請分析 X 可以改進的方向」「X 的設計有什麼可改進之處」「某個 skill / cron / 子系統 怎麼強化」

**錯誤**:直接把分析結果用自然語言段落講完,沒有結構、沒有決策、沒有「哪些是 L3 教訓、哪些是單次結論、哪些不可逆」的分流

**正確做法**:**產出「決策文件」(Decision Document)**,6 段固定結構 + 把不可逆決策交回使用者

**6 段結構**（順序固定）:

1. **現狀盤點** — 從實測資料來的 evidence-based 表格（不是 LLM 印象）
2. **缺口識別** — 從失敗模式 / 觀察到的盲點 / 元層級問題回推
3. **改進方向** — 每條含「目標 / 實作 / 預期效益 / 風險 / 工作量」
4. **優先順序** — 表格化,給使用者的決策矩陣
5. **需要使用者決策的點** — **不可逆決策獨立成段**,明確「我不會自作主張」
6. **不進記憶的決策** — 哪些分析本身/建議本身不入 MEMORY.md（按使用者「對話紀錄保留原則」）

**Why this works**:
- 使用者要的是「**決策輔助**」不是「**完整報告**」— 把決策點獨立成段,他可以直接跳到那
- 結構化 = 任何時候可被引用、可被驗證、可被反駁
- 「不進記憶」段落 = 自動遵守使用者 Rule 6「預設不寫」、不污染長期記憶
- 第 5 段 = 自動遵守 Rule 1 + Rule 12（純討論模式,給選項不動手）

**觸發訊號**（任一符合就採本 pattern）:
- 「X 可以怎麼改進」「分析 X 的改進方向」「X 怎麼強化」「X 還缺什麼」
- 「review 一下 X」「audit X」「X 目前的狀態」
- 使用者剛發現一個子系統的盲點,問「還有什麼類似的」

**反例**（不要這樣做）:
- 「無盡學習系統的改進方向我想到 3 點:1. 2. 3.」 → 沒結構,沒決策點
- 整篇分析沒有「需要使用者決策」段落 → 越權
- 把所有內容都寫進 MEMORY.md → 違反 Rule 6
- 跑 metacognitive-learner cycle 把分析結果寫成 SOP → 純討論模式不該自作主張學習

**配套**:
- `references/decision-document-template.md` — 完整 6 段範本,可直接 copy-modify
- `user-collaboration-style` skill 的 Rule 1（給選項）+ Rule 6（預設不寫）+ Rule 12（純討論模式）+ Rule 14（先建 todo）

**If→Then**:
- **If** 使用者問「X 可以怎麼改進 / 改進方向 / review」 **Then** 產出 6 段決策文件,不要用 LLM 敘事段落
- **If** 6 段決策文件完成 **Then** 結尾必含「我先停這、不自作主張動手」的明確標記
- **If** 使用者挑了某些方向要執行 **Then** 走 Rule 14「先建 todo 計畫 + 給摘要 + 逐個執行」

---

### Pitfall: 「使用者要卸載 X」必須走 4 階段 SOP（2026-06-08 確立）

**情境**:使用者說「幫我卸載 / 移除 / 反安裝 X」,且 X 是 hermes / agent / 生產服務 正在依賴的東西（process 還在跑、config 還在讀、MCP 還在連、cron 還在用、token 是它發的）
**錯誤**:赫米斯直接跑 `npm uninstall`、`systemctl disable --now`、或 `rm -rf`,以為「卸載就是卸載」
**後果**:X 提供的 MCP、cron、token、config 全部一起被砍 → agent 自己、別的服務、cron 任務 cascade failure。事後不可逆（雖然有備份,但 restore 要花時間 + 重啟所有依賴鏈）

**正解**:**先載入 `coupled-infra-removal-sop` skill**（如果存在;或用其 4 階段流程手動跑）:
1. **依賴盤點** — 列出 X 跟哪些東西耦合（process / systemd / cron / config / MCP / token）
2. **備份 + 路徑轉移** — 純複製到外部位置,改腳本讀新位置
3. **健康驗證** — 10 項檢查全綠才進下一步
4. **規劃** — 寫多方案（不可逆/半可逆/最保險）給使用者簽核,才能動

**判斷訊號**:如果使用者的「卸載 X」這句話,搭配以下任一,**必須走 SOP**:
- X 是某個 CLI 工具 / service / daemon
- X 提供 token / OAuth 流程 / API key
- X 是某個 MCP 的 backend
- crontab / systemd 有指向 X 的 entry
- agent 的 `~/.hermes/config.yaml` 有引用 X

**If** 使用者要卸載的東西、agent 自己正在用 **Then** 不要直接下 `uninstall` 指令、先依賴盤點
**If** 盤點發現耦合度 > 5 個層面 **Then** 給 3 個風險分級方案而不是 1 個
**If** 規劃文件沒給至少 3 個方案 + 沒經使用者批准 **Then** 不動手

**配套**:
- 詳細 SOP: `coupled-infra-removal-sop` skill（2026-06-08 新建）
- 完整案例: 2026-06-08 OpenClaw 移除計畫（11 cron + 3 MCP + 1 OAuth + 1 status site 源頭）

---

## 版本變更記錄

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-05-23 | 初始版本 |
| 1.1.0 | 2026-05-23 | 新增 SOP-A（自身狀態網站更新）、SOP-B（其他網站架設）|
| 1.2.0 | 2026-05-23 | 新增大型專案處理 SOP（Phase 0 評估、階段審查、進度追蹤）|
| 1.3.0 | 2026-05-23 | 新增回應指示燈規則（🟢/🔴 泛工作流）|
| 1.4.0 | 2026-06-02 | 新增 strands-agents-sops 生態系技能表（pdd/code-assist/anti-slop-design）|
| 1.5.0 | 2026-06-03 | 新增 SOP-C（任務完成後上傳評價網站），決策檢查清單加入「完成後需要上傳評價網站嗎」 |
| 1.6.0 | 2026-06-06 | 新增「Pitfall: 多檔 HTML 修改的結構陷阱」+ 驗證腳本 `verify-html-tabs.py`。教訓：innerHTML 注入架構下，附加元素必須在 tab-content 內部；多檔 patch 需先盤點 closing 結構差異再動手 |
| 1.7.0 | 2026-06-06 | 新增「Pitfall: 回答 + 順手做大改是越權」— 使用者進「純討論模式」時赫米斯不該自作主張做副作用動作；`clarify()` 無回應 = 凍結,不是默認。配套 user-collaboration-style #12、#13 |
| 1.8.0 | 2026-06-08 | 新增「Pitfall: 使用者要卸載 X 必須走 4 階段 SOP」— 卸載被 agent 依賴的服務時必走 4 階段（盤點/備份/驗證/規劃）。配套新 skill `coupled-infra-removal-sop` |
| 1.9.0 | 2026-06-08 | 新增「Pattern: 分析某子系統的改進方向 = 決策文件 + 不可逆決策交回使用者」— 6 段固定結構（現狀盤點/缺口識別/改進方向/優先順序/需使用者決策/不進記憶的決策）。配套 `references/decision-document-template.md` 可直接 copy-modify |