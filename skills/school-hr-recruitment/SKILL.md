---
name: school-hr-recruitment
description: |
  台灣學校人事主管的 HR 完整工作流 umbrella — 涵蓋候選人追蹤（Linear API + GitHub）與文件生成（DOCX offer letter / 聘用合約）。
  **Class-level skill** — 涵蓋三個面向：(1) 候選人 intake（履歷 PDF → Linear record）、(2) 候選人追蹤（GraphQL API 操作）、(3) 文件生成（從 Linear 抓資料 → 填充 DOCX 模板）。
  **觸發**：錄取通知書、聘用合約、面試通知、offer letter、employment contract、教師聘用、代理教師、代課老師、學校招聘、教師招募。
version: 1.0.0
author: Hermes Agent (curator consolidation 2026-07-04)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hr, document, offer-letter, employment-contract, automation, school, taiwan, linear, github, GraphQL, 教師聘用, 代理教師]
    related_skills: [himalaya, minmax-music-gen]
    triggers: [錄取通知書, 聘用合約, 面試通知, offer letter, employment contract, 教師聘用, 代理教師, 代課, 學校招聘, 教師招募]
    user_type: school HR (high school administrative staff)
---

# School HR Recruitment — 完整工作流 (Class-Level Umbrella)

## 何時使用

**任一符合即載入**：
- 用戶提到「錄取通知書」「offer letter」「聘用合約」「employment contract」「教師聘用」「代理教師」
- 用戶提到「學校招聘」「教師招募」「HR workflow」
- 候選人在 Linear 內狀態改為「錄取」→ 需要自動生成文件
- 收到求職者履歷（PDF/DOCX）→ 需要建追蹤
- 暑期批次建立候選人追蹤

---

## 完整工作流

```
候選人通過面試
    ↓
HR 在 Linear 建立/更新 Issue（候選人狀態 → "錄取"）
    ↓
觸發本 skill 的「候選人追蹤」段
    ↓
從 Linear API 抓候選人資料（姓名、職位、薪資、到職日）
    ↓
觸發本 skill 的「文件生成」段
    ↓
填充 offer letter / employment contract 模板
    ↓
產出 .docx 文件
    ↓
HR 審核 → 發送給候選人
```

### 兩種文件類型

| 文件類型 | 用途 | 觸發時機 |
|---------|------|---------|
| **Offer Letter（錄取通知書）** | 告知錄取、條件、確認意願 | 決定錄取後、簽約前 |
| **Employment Contract（聘用合約）** | 法律約束、聘用條件細節 | 候選人接受 offer 後 |

### 台灣學校教師文件的關鍵欄位

**基本欄位（雙語）**：
- `候選人姓名` / Candidate Name
- `職位` / Position（如：代理教師、兼課教師）
- `應聘期間` / Employment Period（如：2026-08-01 ~ 2027-07-31）
- `授課科目/級別` / Subject/Grade
- `月薪` / Monthly Salary（含級距說明）
- `到職日` / Start Date
- `學校名稱` / School Name
- `用人單位主管` / Hiring Manager

**代理教師（即時代課）特殊欄位**：
- `代理期間` / Substitution Period（原教師請假原因）
- `代理原因` / Reason（如：留職停薪、產假、病假）
- `鐘點費率` / Hourly Rate（如：代課鐘點費）

---

## 候選人追蹤（原 `linear-hr-workflow` 內容）

### Linear API 架構

- **認證**：Personal API Key（**無 `Bearer` 前綴**，`Authorization: <key>` 直接放 key）
- **端點**：`https://api.linear.app/graphql`
- **格式**：GraphQL（不是 REST）
- **Python 整合**：用 `requests` 庫直接發 GraphQL mutation/query

> ⚠️ **常見錯誤**：不要寫 `Authorization: f'Bearer {key}'` — Linear API 不是 OAuth 2.0，沒有 Bearer token。

### Rate Limiting

| 認證方式 | 限制 | 期間 |
|---------|------|------|
| API key | 2,500 requests | 1 小時 |
| OAuth App | 5,000 requests | 1 小時 |

**避免被限流**：
1. 永遠指定分頁 limit（`first: 10` 而非預設 50）
2. 用 webhooks 取代 polling（Linear 建議）
3. 用 `updatedAt` 排序而非 `createdAt`
4. 監控 `X-RateLimit-Requests-Remaining` header

### W1：建立教師招聘候選人追蹤

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

### W3：GitHub Issue 同步到 Linear

```bash
# 當收到求職者 email 時，自動在 Linear 建立追蹤
gh issue create \
  --title "【求職】數學代課 - 李四" \
  --body "## 來自求職者的自動通知\n- 科目：數學\n- 教師證：有\n- 可到職：立即" \
  --label "hr-recruitment"
```

### W4：批次建立多個候選人追蹤（暑期大量徵才）

```python
mutation_batch_create = """
mutation issueBatchCreate($teamId: String!, $createBulk0: IssueCreateInput!, $createBulk1: IssueCreateInput!, $createBulk2: IssueCreateInput!) {
  issueBatchCreate(input: {teamId: $teamId, issues: [$createBulk0, $createBulk1, $createBulk2]}) {
    success
    issues { id identifier title state { name } }
  }
}
"""

# 一次最多 50 個 issue（Linear 上限）
```

### W5：更新求職者狀態（面試進度管理）

```python
mutation_update_issue = """
mutation issueUpdate($id: String!, $stateId: String!) {
  issueUpdate(id: $id, input: {stateId: $stateId}) {
    success
    issue { id identifier title state { name } }
  }
}
"""
```

### W6：分頁查詢大量候選人

```python
query_issues_paginated = """
query HRIssues($teamId: String!, $after: String) {
  issues(first: 10, after: $after, filter: {team: {id: {eq: $teamId}}}) {
    pageInfo { hasNextPage endCursor }
    nodes { id identifier title state { name } assignee { name } updatedAt }
  }
}
"""
```

### W7：linear.new URL 即時建立 + GitHub Branch

```python
import urllib.parse, webbrowser
url = f"https://linear.new/issue/linear/{urllib.parse.quote(title)}?description={urllib.parse.quote(description)}"
webbrowser.open(url)
```

### W8：Linear Webhook → 自動化 HR 文件觸發

當候選人狀態改為「錄取」時，Linear 自動 POST 到 Webhook 端點，端點：
1. 解析 issue identifier
2. 查 Linear API 抓完整候選人資料
3. 呼叫 `hermes chat --cli -q "產生錄取通知書..."`
4. 產出 .docx 存入指定目錄
5. 發 email 通知 HR

**完整 Pipeline 見**：`references/webhook-trigger-setup.md`

### W9：候選人履歷 Intake（履歷 PDF → Linear 候選人 record）

**⚠️ Python 環境警告**：所有 PDF 處理腳本必須使用系統 Python（`/usr/bin/python3`），**不是** hermes-agent venv python。hermes-agent venv 的 python3 缺少 pdfplumber/pdfminer。

**正確 shebang**：
```bash
#!/usr/bin/python3    # ✅ 系統 Python，有 pdfplumber/pdfminer
#!/usr/bin/env python3 # ❌ 會進 hermes-agent venv，缺少 PDF 套件
```

**Step 1 — 提取履歷 PDF 文字**：
```python
from pdfminer.high_level import extract_text
text = extract_text(sys.argv[1])  # 履歷 PDF 路徑
print(text[:2000])  # 取前 2000 字給 LLM 結構化用
```

**Step 2 — LLM 結構化解析**：
```python
import requests, os, json
prompt = f"""從以下履歷文字中，結構化提取：姓名、Email、電話、應徵職位、學歷、工作經歷。
只輸出 JSON，格式：{{"name","email","phone","position","education","experience"}}

履歷文字：
{text[:3000]}
"""
resp = requests.post(
    'https://api.minimax.chat/v1/text/chatcompletion_pro',
    headers={'Authorization': f'Bearer {os.getenv("MINIMAX_API_KEY")}'},
    json={'model': 'MiniMax-Text-01', 'messages': [{'role': 'user', 'content': prompt}]}
)
result = json.loads(resp.json()['choices'][0]['message']['content'])
```

**Step 3 — 建立 Linear 候選人追蹤**（使用 W2/W4 mutation）

**完整 Pipeline 見**：`references/resume-intake-pipeline.md`

---

## 文件生成（原 `hr-document-automation` 內容）

### 整合架構

| Skill | 職責 | 實際狀態 |
|-------|------|---------|
| `linear-hr-workflow`（已合併於本 skill） | 候選人追蹤、狀態更新、GraphQL API | ✅ |
| `python-docx` (python3.12) | DOCX 文件生成 | ✅ **主要 pipeline**（dotnet 未裝，minmax-docx C# 備援失效） |
| `anthropic-draft-content` | 生成專業文案（填入模板的內容） | ✅ 可用 |

### Step 1：確認 Linear API Key

```python
import os, requests
LINEAR_API_KEY = os.getenv('LINEAR_API_KEY')
HEADERS = {
    'Authorization': LINEAR_API_KEY,
    'Content-Type': 'application/json'
}
# 驗證
r = requests.post('https://api.linear.app/graphql',
    headers=HEADERS,
    json={'query': '{ viewer { id email name } }'})
if r.ok:
    print("✅ Linear API connected")
else:
    print("❌ Linear API error:", r.text)
```

### Step 2：從 Linear 抓候選人資料

```python
query_candidates = """
query {
  issues(first: 20, filter: {
    team: { id: { eq: "YOUR_TEAM_ID" } }
    labels: { name: { eq: "錄取" } }
  }) {
    nodes {
      id identifier title
      priority
      dueDate
      state { name }
      assignee { name email }
    }
  }
}
"""
r = requests.post('https://api.linear.app/graphql',
    headers=HEADERS, json={'query': query_candidates})
candidates = r.json()['data']['issues']['nodes']
print(f"找到 {len(candidates)} 位錄取候選人")
```

### Step 3：產出 Offer Letter

```python
from docx import Document
from datetime import date

def generate_offer_letter(candidate_name, position, salary, start_date, school_name):
    doc = Document()

    doc.add_heading(f'錄取通知書 / Offer Letter', 0)
    doc.add_paragraph(f'日期/Date: {date.today().strftime("%Y年%m月%d日")}')
    doc.add_paragraph(f'親愛的 {candidate_name}：')
    doc.add_paragraph(
        f'恭喜您通過「{position}」一職的面試，我們誠摯邀請您加入 {school_name}。')

    doc.add_heading('聘用條件 / Employment Terms', level=1)
    table = doc.add_table(rows=5, cols=2)
    table.style = 'Light Grid Accent 1'

    data = [
        ('職位 / Position', position),
        ('到職日 / Start Date', start_date),
        ('月薪 / Monthly Salary', salary),
        ('聘用期間 / Employment Period', f'{start_date} ~ {int(start_date[:4])+1}-07-31'),
        ('適用法規 / Applicable Law', '教師法、教育部代理教師注意事項')
    ]
    for i, (key, val) in enumerate(data):
        table.rows[i].cells[0].text = key
        table.rows[i].cells[1].text = val

    doc.add_paragraph(f'請在收到此通知後 5 個工作天內回覆是否接受此錄取。')
    doc.add_paragraph(f'若有任何問題，請聯繫人事部門。')
    doc.add_paragraph(f'\n{school_name} 人事部門')

    return doc
```

### Step 4：產出 Employment Contract（代理教師）

```python
def generate_employment_contract_substitute(
    candidate_name, subject, hourly_rate,
    substitution_reason, period, school_name):
    """代理教師聘用合約（鐘點制）"""
    doc = Document()

    doc.add_heading('代理教師聘用合約', 0)
    doc.add_heading('Employment Contract for Substitute Teacher', level=2)

    doc.add_paragraph(f'甲方（學校）: {school_name}')
    doc.add_paragraph(f'乙方（教師）: {candidate_name}')

    doc.add_heading('第一條 聘用期間', level=1)
    doc.add_paragraph(f'甲方聘乙方為代理教師，代理期間：{period}')
    doc.add_paragraph(f'代理原因：{substitution_reason}')

    doc.add_heading('第二條 授課科目', level=1)
    doc.add_paragraph(f'乙方應授科目：{subject}')

    doc.add_heading('第三條 鐘點費', level=1)
    doc.add_paragraph(f'鐘點費率：每節 {hourly_rate} 元（含勞健保）')
    doc.add_paragraph(f'計算方式：實際授課節數 × 鐘點費率')

    doc.add_heading('第四條 權利義務', level=1)
    doc.add_paragraph('乙方應遵守學校規章、履行教師職責、參加校內會議及研習活動。')

    doc.add_paragraph('\n\n甲方簽章：________________     日期：____________')
    doc.add_paragraph('乙方簽章：________________     日期：____________')

    return doc
```

### 完整 CLI 工具

- `scripts/generate_offer_letter.py` — offer letter 生成（已驗證 Cycle 1 — 2026-06-18）
- `scripts/generate_contract_substitute.py` — contract 生成（已驗證）
- `scripts/generate_docs.py` — 通用入口

**驗證命令**：
```bash
python3.12 ~/.hermes/skills/school-hr-recruitment/scripts/generate_offer_letter.py \
    "王小明" "代理數學教師" "45000" "2026-08-01" "台北市立第一高級中學" /tmp/test_offer.docx
# 預期: Generated: /tmp/test_offer.docx (~37KB)
```

---

## 環境與依賴

| 依賴 | 狀態 | 安裝方式 |
|------|------|---------|
| `LINEAR_API_KEY` | ✅ 寫入 `~/.hermes/.env` | 從 Linear → Settings → API 建立 |
| python-docx (python3.12) | ✅ 已驗證 | `/usr/bin/python3 -m pip install python-docx --break-system-packages` |
| minimax-docx skill | ⚠️ dotnet 未裝 | C# OpenXML 備援失效；改用 python-docx (python3.12) |
| `himalaya` email CLI | ✅ 已有 | `~/bin/himalaya` v1.2.0（官方 install.sh） |
| `pdfminer.six` | ✅ 已有 | `uv pip install pdfminer.six --break-system-packages` |
| `pytesseract` | ✅ 已有 | `uv pip install pytesseract --break-system-packages` |
| `tesseract` OCR | ✅ 已有 | `/usr/bin/tesseract` 5.3.4 |

---

## 整合的其他 Skills

本 skill 不替代而是整合：

| Skill | 串接方式 |
|-------|---------|
| `himalaya` | 發送招募 email（面試邀請、offer letter、拒絕通知）並與 Linear 狀態同步 |
| `anthropic-draft-content` | 生成職缺描述（用於 Linear issue description） |
| `anthropic-customer-research` | 評估候選人背景 |
| `anthropic-call-prep` | 面試準備 |
| `anthropic-compliance-check` | 確認教師任用法規限制 |
| `github` | gh CLI 操作 |

---

## 限制與已知問題

1. **LINEAR_API_KEY 需手動設定** — 第一次使用前需在 `~/.hermes/.env` 設定
2. **學校法律審查** — 正式聘用合約建議通過學校法規部門審查，不完全依赖自動生成
3. **代理人教師特約** — 鐘點制代理教師的勞健保計算是另一套邏輯（見 HR 單位規定）
4. **System Python 無法安裝 linear-api pip**：使用 raw `requests` 庫發 GraphQL
5. **批次建立上限**：每個 `issueBatchCreate` 最多 50 個 issue
6. **Cursor 分頁必需**：大量查詢不可省略 `first` + `after` 否則觸發複雜度上限
7. **hermes-agent venv 缺少 PDF 套件**：所有 PDF 處理腳本（pdfplumber、pdfminer）都在系統 Python（`/usr/bin/python3`），不在 hermes-agent venv
8. **marker-pdf 未安裝**：OCR-based PDF 處理依賴 `marker-pdf`（未安裝），掃描件履歷需要用 `pytesseract` 或手動處理

---

## 觸發 If→Then 規則

**If** 用戶提到「錄取通知書」「offer letter」「聘用合約」「employment contract」「教師聘用」**Then** 啟動本 skill 的「文件生成」段
**If** 用戶提到「學校招聘」「代理教師」「代課老師」「面試名單」**Then** 啟動本 skill 的「候選人追蹤」段
**If** 用戶說「幫我產生 OO 老師的錄取通知書」**Then** 走「文件生成」段、查 Linear 找候選人資料 → 填充模板 → 產出 .docx
**If** 候選人狀態從「複試」改為「錄取」**Then** 觸發 W8 Webhook 自動生成文件
**If** 候選人在 Linear 的狀態不是「錄取」**Then** 先提示「請先在 Linear 將候選人狀態改為『錄取』再生成文件」
**If** 學校人事法規有特殊要求 **Then** 在產出後提醒「此文件需經學校法規部門審查後方可正式使用」
**If** Linear API call 返回 `401 AUTHENTICATION_ERROR` **Then** `LINEAR_API_KEY` 未設定或已失效，需從 `linear.app/settings/account/security` 建立新的 Personal API key

---

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-07-04 | curator 整合：`linear-hr-workflow`（候選人追蹤）+ `hr-document-automation`（文件生成）合併為一個 class-level umbrella skill。原本兩個 skill 歸檔。 |