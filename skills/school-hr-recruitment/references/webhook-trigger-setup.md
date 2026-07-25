# Linear Webhook → HR Document 自動化觸發設定

## 為什麼需要 Webhook 觸發

`hr-document-automation` skill 存在且功能完整，但**只能被動等待用戶說「幫我產生 OO 老師的錄取通知書」**。學校人事實際流程是：HR 在 Linear 更新候選人狀態（面試 → 錄取）→ 應該自動觸發文件生成。這就是本檔要填補的觸發缺口。

## 最速落地架構：Pipedream（不需要自架 Server）

```
Linear issue state 變「錄取」
    ↓ (Linear Webhook)
Pipedream workflow trigger (Linear - Issue Updated)
    ↓
HTTP POST → 赫米斯 CLI (hermes chat -q "..." --cli --quiet)
    ↓
hr-document-automation skill 執行
    ↓
產出 .docx → 發 email 通知 HR
```

### 替代方案對比

| 方案 | 優點 | 缺點 |
|------|------|------|
| **Pipedream（推薦）** | 不需自架 server、有 Linear instant trigger、免費額度够用 | 依賴第三方、Linear API key 需給 Pipedream |
| n8n | 開源、可自架 | 需要自己的 VPS/server |
| 自架 Webhook Server | 完全控制 | 需要固定 IP + 域名、過度複雜 |
| Cron polling | 簡單 | 不即時、浪費 API quota |

## Pipedream 設定步驟

### Step 1：建立 Pipedream workflow

1. 前往 https://pipedream.com → Sign up（可用 GitHub 登入）
2. New Workflow → 搜尋 "Linear" → 選擇 **Linear - New Issue Updated (Instant)**
3. 連接 Linear API Key（Personal API Key，格式：`lin_api_xxx`，**不需要 Bearer 前綴**）

### Step 2：設定 Trigger Filter（只捕「錄取」狀態）

```
Condition: state.name equals "錄取"
```

这样只有當候選人狀態改為「錄取」才觸發，不會在每次編輯都觸發。

### Step 3：新增 HTTP Request Step（呼叫赫米斯）

```javascript
// Pipedream Node.js code step
export default defineComponent({
  async run({ steps, $ }) {
    const issue = steps.trigger.event.issue;
    const title = issue.title;           // 例如：「【代理】數學代課老師 - 張三」
    const stateName = issue.state.name;   // 應該是「錄取」
    const identifier = issue.identifier;  // 例如：「HR-42」
    
    // 呼叫赫米斯 CLI
    const axios = require('axios');
    const { exec } = require('child_process');
    
    const hermesCmd = `hermes chat -q "請幫我產生 ${title} 的錄取通知書。候選人狀態：${stateName}，Linear ID：${identifier}。請從 Linear API 抓取完整候選人資料並產出 .docx。" --cli --quiet`;
    
    return new Promise((resolve, reject) => {
      exec(hermesCmd, { timeout: 120000 }, (err, stdout, stderr) => {
        if (err) {
          console.error('Hermes error:', stderr);
          reject(err);
        } else {
          console.log('Hermes output:', stdout);
          resolve(stdout);
        }
      });
    });
  },
})
```

### Step 4：新增 Email 通知 Step（完成後通知 HR）

在 Pipedream workflow 最後加一個 Email action（Zoho / Gmail / SMTP），通知 HR「候選人錄取通知書已產生，請至以下連結下載」。

## 赫米斯端對接設定

### 確保 hermes CLI 可以在 headless 環境運行

Webhook 觸發的 HTTP call 會在 Pipedream 的 server 執行，所以：

1. 赫米斯 CLI 必須能從 command line 運行（不需要 TTY）：
```bash
hermes chat -q "任務描述" --cli --quiet
```

2. API key 必須可在 server 環境取用（建議用 `~/.hermes/.env`）。

### 驗證 Webhook 成功的方法

在 Pipedream workflow 加入 Email step，內容包含：
- 候選人姓名
- 產出的 .docx 檔案路徑
- 時間戳

## 已知限制

1. **Pipedream 免費額度**：每月 10,000 觸發、100 個 workflow，對學校 HR 足夠（每學期候選人 < 100 人）
2. **線性成長假設**：暑期大量招聘時（> 50 人/天）可能超出額度，這時需要升級或換 n8n 自架
3. **Server 環境限制**：Pipedream 跑 Node.js，不能跑需要 GUI 的程式
4. **赫米斯 API key 安全**：LINEAR_API_KEY 和 HERMES_API_KEY 都要存在 Pipedream 的環境變數中

## If→Then 觸發規則（本 skill 內）

**If** Linear issue 的 `state.name` 變為「錄取」
**Then** Pipedream webhook 觸發 → HTTP POST 赫米斯 CLI → hr-document-automation skill 執行

**If** 學校沒有使用 Pipedream / 不想用第三方
**Then** 建議用 `linear-hr-workflow` 的 W6 cursor-based polling，每小時查一次「錄取」狀態的 issue，主動生成文件（犧牲即時性換取簡單）

**If** 要接收 Linear 即時狀態變化通知（不用 polling）
**Then** 設定 Webhook：Linear Settings → API → Webhooks → 建立並指向你家伺服器的 `/webhook/linear` 端點（需要固定 IP + 域名）

## 與 linear-hr-workflow 的關係

- `linear-hr-workflow` W7：`linear.new` URL 即時建立候選人追蹤（手動）
- `linear-hr-workflow` Webhook 章節（本檔）：狀態變化自動觸發文件生成（自動）
- `hr-document-automation`：接收觸發後產出 DOCX

這三個構成完整的「手動建立 → 自動追蹤 → 自動產出」HR pipeline。
