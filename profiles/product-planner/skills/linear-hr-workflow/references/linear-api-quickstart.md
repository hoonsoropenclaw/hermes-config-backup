# Linear API Quickstart (2026-06-09)

## 核心事實

| 項目 | 值 |
|------|-----|
| Endpoint | `https://api.linear.app/graphql` |
| 認證 | Personal API Key — `Authorization: Bearer <key>` |
| 格式 | GraphQL（不是 REST） |
| Python 整合 | Raw `requests`（不走 `linear-api` pip 包） |
| 原因 | System Python 3.11 有 PEP 668，無法 `pip install linear-api` |

## 驗證 API Key

```python
import os, requests
key = os.getenv('LINEAR_API_KEY')
r = requests.post('https://api.linear.app/graphql',
    headers={'Authorization': key, 'Content-Type': 'application/json'},
    json={'query': '{ viewer { id email name } }'})
print(r.json())
# 預期：{'data': {'viewer': {'id': '...', 'email': '...', 'name': '...'}}}
# 401：key 過期或無效
# 200 但 errors：有 GraphQL 語法錯誤
```

## 查詢 Teams

```python
query = """
{
  teams(first: 10) {
    nodes { id name identifier }
  }
}
"""
r = requests.post('https://api.linear.app/graphql',
    headers=HEADERS, json={'query': query})
teams = r.json()['data']['teams']['nodes']
```

## 建立 Issue（mutation）

```python
mutation = """
mutation issueCreate($title: String!, $teamId: String!, $description: String) {
  issueCreate(input: {title: $title, teamId: $teamId, description: $description}) {
    success
    issue { id identifier title state { name } }
  }
}
"""
r = requests.post('https://api.linear.app/graphql', headers=HEADERS, json={
    'query': mutation,
    'variables': {
        'title': '【代理】數學代課老師 - 張三',
        'teamId': team_id,
        'description': '## 候選人資料\n- 應徵科目：數學\n- 教師證：有\n- 可到職日：2026-09-01'
    }
})
issue = r.json()['data']['issueCreate']['issue']
```

## 常見錯誤

| 錯誤 | 原因 | 解法 |
|------|------|------|
| `401 Unauthorized` | API key 過期/無效 | Linear Settings → API → 重新產生 key，更新 `~/.hermes/.env` |
| `403 Forbidden` | 帳號無該 workspace 權限 | 確認 key 來自正確 workspace |
| GraphQL errors array | 語法/欄位名錯誤 | 檢查 query 語法，Linear 嚴格 schema |
| `{}` 空回應 | network timeout 或 blocking | 增加 timeout 或檢查 proxy 設定 |

## 與 GitHub 整合

Linear ↔ GitHub 雙向同步：
- **Linear → GitHub**：在 PR description 寫 `Closes LINEAR-123`，PR merge 時自動 close Linear issue
- **GitHub → Linear**：在 Linear 建立 issue 時可自動建立 branch

## 學校 HR 應用場景

1. **候選人追蹤**：每個求職者建立一個 Linear issue
2. **面試流程**：用 Linear cycle 管理面試階段
3. **代理教師**：即時需求，用 `linear.new` 語法快速建立

## 參考資源

- Linear 開發者文檔：https://linear.app/developers/graphql
- linear-api PyPI：https://pypi.org/project/linear-api（需要 venv 才能安裝）
- dltHub Linear pipeline：https://dlthub.com/context/source/linear