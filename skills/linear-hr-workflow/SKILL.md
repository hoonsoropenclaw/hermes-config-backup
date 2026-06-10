---
name: linear-hr-workflow
description: "Linear API + GitHub 整合工作流，用於學校人事招聘自動化。觸發於用戶提到 Linear、GitHub Issues、學校招聘、教師招募時啟用。核心能力：GraphQL API 操作、HR 工作流整合、gh CLI 自動化。"
version: 1.1.0
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
- **認證**：Personal API Key（`Authorization: Bearer ***`
- **端點**：`https://api.linear.app/graphql`
- **格式**：GraphQL（不是 REST）
- **Python 整合**：用 `requests` 庫直接發 GraphQL mutation/query（`linear-api` pip 包需要 venv，hermes 預設用 system python3.11）

### Rate Limiting
| 認證方式 | 限制 | 期間 |
|---------|------|------|
| API key | 2,500 requests | 1 小時 |
| OAuth App | 5,000 requests | 1 小時 |

**避免被限流的最佳實踐**：
1. 永遠指定分頁 limit（如 `first: 10` 而非預設 50）— 預設分頁 50 條會乘以 connection 數產生大量複雜度點數
2. 用 webhooks 取代 polling（Linear 建議）
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
3. **即時建立（linear.new）**：URL 語法直接開啟 Linear issue 建立頁面 + 預填標題/描述

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
mutation issueCreate($title: String!, $teamId: String!, $description: String) {
  issueCreate(input: {title: $title, teamId: $teamId, description: $description}) {
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

### W4：批次建立多個候選人追蹤（暑期大量徵才）

```python
# 一次 GraphQL 請求建立最多 50 個 issue（Linear 上限）
mutation_batch_create = """
mutation issueBatchCreate($teamId: String!, $createBulk0: IssueCreateInput!, $createBulk1: IssueCreateInput!, $createBulk2: IssueCreateInput!) {
  issueBatchCreate(input: {teamId: $teamId, issues: [$createBulk0, $createBulk1, $createBulk2]}) {
    success
    issues { id identifier title state { name } }
  }
}
"""

candidates = [
    {'title': '【代理】數學代課老師 - 張三', 'description': '10年經驗，可立即到職'},
    {'title': '【代理】英文代課老師 - 李四', 'description': '5年經驗，暑期可到職'},
    {'title': '【代理】理化代課老師 - 王五', 'description': '實驗室專長，9月可到職'},
]

r = requests.post('https://api.linear.app/graphql', headers=HEADERS, json={
    'query': mutation_batch_create,
    'variables': {
        'teamId': hr_team['id'],
        'createBulk0': {'title': candidates[0]['title'], 'description': candidates[0]['description']},
        'createBulk1': {'title': candidates[1]['title'], 'description': candidates[1]['description']},
        'createBulk2': {'title': candidates[2]['title'], 'description': candidates[2]['description']},
    }
})
issues = r.json()['data']['issueBatchCreate']['issues']
print(f"Created {len(issues)} issues")
```

### W5：更新求職者狀態（面試進度管理）

```python
# 面試後更新候選人狀態：待複審 → 已錄取
mutation_update_issue = """
mutation issueUpdate($id: String!, $stateId: String!) {
  issueUpdate(id: $id, input: {stateId: $stateId}) {
    success
    issue { id identifier title state { name } }
  }
}
"""

# 假設狀態 ID（實際需先查詢）
# stateId = "已錄取狀態的 UUID"
r = requests.post('https://api.linear.app/graphql', headers=HEADERS, json={
    'query': mutation_update_issue,
    'variables': {
        'id': issue['id'],  # W2/W4 建立後的 issue id
        'stateId': "desired_state_id"
    }
})
updated = r.json()['data']['issueUpdate']['issue']
print(f"Updated: {updated['identifier']} → {updated['state']['name']}")
```

### W6：查詢並分頁處理大量候選人

```python
# 分頁查詢 HR Team 下的所有候選人 issue
query_issues_paginated = """
query HRIssues($teamId: String!, $after: String) {
  issues(first: 10, after: $after, filter: {team: {id: {eq: $teamId}}}) {
    pageInfo { hasNextPage endCursor }
    nodes { id identifier title state { name } assignee { name } updatedAt }
  }
}
"""

cursor = None
all_issues = []
while True:
    r = requests.post('https://api.linear.app/graphql', headers=HEADERS, json={
        'query': query_issues_paginated,
        'variables': {'teamId': hr_team['id'], 'after': cursor}
    })
    data = r.json()['data']['issues']
    all_issues.extend(data['nodes'])
    if not data['pageInfo']['hasNextPage']:
        break
    cursor = data['pageInfo']['endCursor']

print(f"Total: {len(all_issues)} candidates")
# 過濾出「待複審」狀態的候選人
pending = [i for i in all_issues if i['state']['name'] == '待複審']
print(f"Pending review: {len(pending)}")
```

### W7：linear.new URL 即時建立 + GitHub Branch

```python
# linear.new 語法：直接開啟 Linear 預填建立頁面（不需要 API call）
# 格式：https://linear.new/issue/線性workspace-標題?description=...
# 實際 URL 編碼後開啟瀏覽器
import urllib.parse, webbrowser

title = "【代理】數學代課老師 - 張三"
description = "## 候選人資料\n- 科目：數學\n- 可到職日：2026-09-01"

url = f"https://linear.new/issue/linear/{urllib.parse.quote(title)}?description={urllib.parse.quote(description)}"
webbrowser.open(url)
# 同時自動建立 GitHub branch（Linear 內建 linear.new 按鈕）
```

## If→Then 規則

**If** 用戶提到「學校招聘」「代理教師」「代課老師」「面試名單」
**Then** 啟動 `linear-hr-workflow` skill，引導用以下順序：
1. 確認 Linear API key 是否已設定（`~/.hermes/.env` 的 `LINEAR_API_KEY`）
2. 若無，引導用戶建立並存入
3. 用 W1 確認 HR team ID
4. 用 W2/W3 建立追蹤

**If** 要從 GitHub Issue 同步候選人資訊到 Linear
**Then** 使用 `linear.new` URL 語法建立 branch 再建立 Linear issue（不是直接建立）

**If** Linear API 回 401
**Then** API key 過期或無效 → 引導用戶重新產生 key 並更新 `~/.hermes/.env`

**If** 要快速建立多個候選人追蹤（批量，≥3 個）
**Then** 用 W4 `issueBatchCreate`（一次最多 50 個），不要分開建立

**If** 需要更新候選人面試進度狀態
**Then** 用 W5 `issueUpdate` mutation，不要刪除重建

**If** 要查詢大量歷史候選人（>10 個）
**Then** 用 W6 cursor-based 分頁，不要一次抓取全量（被限流）

**If** 要做即時代理教師招募（電話/Line 收到簡歷）
**Then** 用 W7 `linear.new` URL 語法，開瀏覽器 + GitHub branch 一次完成

**If** 要接收 Linear 內即時狀態變化通知（不用 polling）
**Then** 設定 Webhook：Linear Settings → API → Webhooks → 建立並指向你家伺服器的 `/webhook` 端點

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
4. **批次建立上限**：每個 `issueBatchCreate` 最多 50 個 issue
5. **Cursor 分頁必需**：大量查詢不可省略 `first` + `after` 否則觸發複雜度上限

## 支援檔案

- **`references/linear-api-quickstart.md`** — Linear GraphQL API 核心語法、驗證脚本、常見錯誤對照表
