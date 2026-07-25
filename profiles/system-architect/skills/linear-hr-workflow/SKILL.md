---
name: linear-hr-workflow
description: "Linear API + GitHub 整合工作流，用於學校人事招聘自動化。觸發於用戶提到 Linear、GitHub Issues、學校招聘、教師招募時啟用。核心能力：GraphQL API 操作、HR 工作流整合、gh CLI 自動化。"
version: 1.0.0
author: Hermes Agent (metacognitive-learner)
platforms: [linux]
metadata:
  hermes:
    tags: [linear, github, hr, workflow, automation, school]
    triggers: [linear, GitHub Issues, 學校招聘, 教師招募, HR workflow]
    user_type: school HR (high school administrative staff)
---

# Linear HR Workflow Skill

學校人事主管的 Linear API + GitHub 整合工作流。

## 核心原理

### Linear API 架構
- **認證**：Personal API Key（`Authorization: Bearer <key>`）
- **端點**：`https://api.linear.app/graphql`
- **格式**：GraphQL（不是 REST）
- **Python 整合**：用 `requests` 庫直接發 GraphQL mutation/query（`linear-api` pip 包需要 venv，hermes 預設用 system python3.11）

### Rate Limiting（2026-06-10 更新）
| 認證方式 | 限制 | 期間 |
|---------|------|------|
| API key | 2,500 requests | 1 小時 |
| OAuth App | 5,000 requests | 1 小時 |

**避免被限流的最佳實踐**：
1. 永遠指定分頁 limit（如 `first: 10` 而非預設 50）— 預設分頁 50 條會乘以 connection 數產生大量複雜度點數
2. 用 webhooks 取代 polling（線性 API 建議）
3. 用 `updatedAt` 排序而非 `createdAt`
4. 監控 `X-RateLimit-Requests-Remaining` header

**複雜度計算**：
- 單一 query 上限：10,000 點
- 簡單屬性：0.1 point/個
- Connections：乘以分頁參數（預設 50）

**如果被限流**（HTTP 400, code: RATELIMITED）：
- 檢查 `X-RateLimit-Requests-Reset` header，等時間到後再重試
- 或聯繫 Linear support 申請提升限制

### 與 GitHub 的整合模式
Linear ↔ GitHub 是雙向同步：
1. **Linear → GitHub**：建立 issue 後自動建立 branch（`linear.new` 語法）
2. **GitHub → Linear**：PR merge 時自動 close Linear issue

### 學校 HR 的獨特需求
學校 HR 與企業 HR 最大的差異：
- **代理教師（即時代課）**：即時性高，不可走一般 44 天招聘週期
- **規模小**：每次只聘 1-3 人，大型 ATS 過度複雜
- **暑期密集**：學期結束前後需要快速補充大量教師

## 安裝與設定

### 1. 取得 Linear API Key
1. 登入 Linear → 右上角頭像 → Settings → API
2. 建立 Personal API Key
3. 存入 `~/.hermes/.env`：`LINEAR_API_KEY=lin_api_xxxxx`

### 2. 驗證 API Key
```bash
python3 -c "
import os, requests
key = os.getenv('LINEAR_API_KEY')
r = requests.post('https://api.linear.app/graphql',
    headers={'Authorization': key, 'Content-Type': 'application/json'},
    json={'query': '{ viewer { id email name } }'})
print(r.json())
"
```

### 3. 確認 GitHub CLI 已登入
```bash
gh auth status
# 輸出應顯示：✓ Logged in to github.com account hoonsoropenclaw
```

## 工作流程

### W1：建立教師招聘候選人追蹤（最基礎場景）

```python
import os, requests

LINEAR_API_KEY = os.getenv('LINEAR_API_KEY')
HEADERS = {
    'Authorization': LINEAR_API_KEY,
    'Content-Type': 'application/json'
}

# 查詢 HR Team ID
query_teams = """
{
  teams(first: 10) {
    nodes { id name identifier }
  }
}
"""
r = requests.post('https://api.linear.app/graphql',
    headers=HEADERS, json={'query': query_teams})
teams = r.json()['data']['teams']['nodes']
hr_team = next((t for t in teams if 'hr' in t['name'].lower() or '人事' in t['name'].lower()), teams[0])
print(f"HR Team: {hr_team['name']} ({hr_team['id']})")
```

### W2：建立求職者追蹤 Issue

```python
mutation_create_issue = """
mutation issueCreate(\$title: String!, \$teamId: String!, \$description: String) {
  issueCreate(input: {title: \$title, teamId: \$teamId, description: \$description}) {
    success
    issue { id identifier title state { name } }
  }
}
"""

# 徵才：數學代課老師
r = requests.post('https://api.linear.app/graphql', headers=HEADERS, json={
    'query': mutation_create_issue,
    'variables': {
        'title': '【代理】數學代課老師 - 張三',
        'teamId': hr_team['id'],
        'description': '## 候選人資料\n- 應徵科目：數學\n- 可到職日：2026-09-01\n- 教師證：有\n\n## 獵頭摘要\n10 年教學經驗，擅長國中數學，寒假後可到職。'
    }
})
issue = r.json()['data']['issueCreate']['issue']
print(f"Created: {issue['identifier']} - {issue['title']}")
```

### W3：GitHub Issue 同步到 Linear（用於獵頭自動化）

```bash
# 當收到求職者 email 時，自動在 Linear 建立追蹤
# 觸發鉤子：收到特定 label 的 email
gh issue create \
  --title "【求職】數學代課 - 李四" \
  --body "## 來自求職者的自動通知\n- 科目：數學\n- 教師證：有\n- 可到職：立即" \
  --label "hr-recruitment"
```

## If→Then 規則

**If** 用戶提到「學校招聘」「代理教師」「代課老師」「面試名單」
**Then** 啟動 `linear-hr-workflow` skill，引導用以下順序：
1. 確認 Linear API key 是否已設定（`~/.hermes/.env` 的 `LINEAR_API_KEY`）
2. 若無，引導用戶建立並存入
3. 用 W1 確認 HR team ID
4. 用 W2/W3 建立追蹤

**If** 要從 GitHub Issue 同步候選人資訊到 Linear
**Then** 使用 `linear.new` 語法建立 branch 再建立 Linear issue（不是直接建立）

**If** Linear API 回 401
**Then** API key 過期或無效 → 引導用戶重新產生 key 並更新 `~/.hermes/.env`

**If** 要快速建立多個候選人追蹤（批量）
**Then** 用 batch mutation（一次 query 包含多個 mutation），不要分開建立

## 依賴的現有 Skills

本 skill 不替代而是整合以下現有 skills：

| 現有 Skill | 整合方式 |
|-----------|----------|
| `anthropic-draft-content` | 生成職缺描述（用於 Linear issue description） |
| `anthropic-customer-research` | 評估候選人背景 |
| `anthropic-call-prep` | 面試準備 |
| `anthropic-compliance-check` | 確認教師任用法規限制 |
| `github` | gh CLI 操作 |

## 限制與已知問題

1. **System Python 無法安裝 linear-api pip**：使用 raw `requests` 庫發 GraphQL
2. **無 Linear API Key 時無法運作**：需要用戶手動設定
3. **學校法規限制**：教師任用有法律程序，自動化只能輔助追蹤，無法完全取代正規流程

## 支援檔案

- **`references/linear-api-quickstart.md`** — Linear GraphQL API 核心語法、驗證脚本、常見錯誤對照表