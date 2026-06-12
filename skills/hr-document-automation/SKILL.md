---
name: hr-document-automation
description: "HR 文件自動生成工作流 — 整合候選人追蹤（Linear）與文件生成（DOCX）。當用戶提到「錄取通知書」「聘用合約」「面試通知」「offer letter」「employment contract」「教師聘用」時啟用。核心功能：台灣學校教師聘用文件自動生成、從 Linear 候選人資料一鍵產出 DOCX。"
version: 1.0.0
author: Hermes Agent (metacognitive-learner)
platforms: [linux]
metadata:
  hermes:
    tags: [hr, document, offer-letter, employment-contract, automation, school, taiwan]
    triggers: [錄取通知書, 聘用合約, 面試通知, offer letter, employment contract, 教師聘用, 代理教師, 代課]
    user_type: school HR (high school administrative staff)
---

# HR Document Automation Skill

台灣學校人事主管的 HR 文件自動生成工作流。

## 核心原理

### 完整工作流

```
候選人通過面試
    ↓
HR 在 Linear 建立/更新 Issue（候選人狀態 → "錄取"）
    ↓
觸發 hr-document-automation skill
    ↓
從 Linear API 抓候選人資料（姓名、職位、薪資、到職日）
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

根據 Taiwan 勞動部規定 + 教育 部規定，學校教師聘用文件必備欄位：

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

## 整合架構

### 現有 Skills 的角色

| Skill | 職責 |
|-------|------|
| `linear-hr-workflow` | 候選人追蹤、狀態更新、GraphQL API |
| `minimax-docx` | DOCX 文件生成（C# OpenXML） |
| `anthropic-draft-content` | 生成專業文案（填入模板的內容） |

### 不替代而是整合

本 skill **不複製** `linear-hr-workflow` 的 API 整合代碼，**不複製** `minimax-docx` 的文檔生成代碼，而是串接兩者。

## 觸發 If→Then 規則

**If** 用戶提到「錄取通知書」「offer letter」「聘用合約」「employment contract」「教師聘用」
**Then** 啟動 `hr-document-automation` skill

**If** 候選人狀態從「複試」改為「錄取」（在 Linear）
**Then** 自動提示 HR 可以生成 offer letter

**If** 用戶說「幫我產生 OO 老師的錄取通知書」
**Then** 查 Linear 找候選人資料 → 填充模板 → 產出 .docx

## 使用流程

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
# 查 "錄取" 狀態的 Issue（假設 HR Team ID 已知道）
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
    
    # 標題
    doc.add_heading(f'錄取通知書 / Offer Letter', 0)
    
    # 日期
    doc.add_paragraph(f'日期/Date: {date.today().strftime("%Y年%m月%d日")}')
    
    # 收件人
    doc.add_paragraph(f'親愛的 {candidate_name}：')
    doc.add_paragraph(
        f'恭喜您通過「{position}」一職的面試，我們誠摯邀請您加入 {school_name}。')
    
    # 聘用條件
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
    
    # 結尾
    doc.add_paragraph(
        f'請在收到此通知後 5 個工作天內回覆是否接受此錄取。')
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
    
    # 甲乙方
    doc.add_paragraph(f'甲方（學校）: {school_name}')
    doc.add_paragraph(f'乙方（教師）: {candidate_name}')
    
    # 聘用條款
    doc.add_heading('第一條 聘用期間', level=1)
    doc.add_paragraph(f'甲方聘乙方為代理教師，代理期間：{period}')
    doc.add_paragraph(f'代理原因：{substitution_reason}')
    
    doc.add_heading('第二條 授課科目', level=1)
    doc.add_paragraph(f'乙方應授科目：{subject}')
    
    doc.add_heading('第三條 鐘點費', level=1)
    doc.add_paragraph(
        f'鐘點費率：每節 {hourly_rate} 元（含勞健保）')
    doc.add_paragraph(f'計算方式：實際授課節數 × 鐘點費率')
    
    doc.add_heading('第四條 權利義務', level=1)
    doc.add_paragraph(
        '乙方應遵守學校規章、履行教師職責、參加校內會議及研習活動。')
    
    # 簽署欄
    doc.add_paragraph('\n\n甲方簽章：________________     日期：____________')
    doc.add_paragraph('乙方簽章：________________     日期：____________')
    
    return doc
```

## 模板檔案（可客製化）

建議將通用模板存於 `~/.hermes/skills/hr-document-automation/templates/`：

```
templates/
├── offer_letter_代理教師.docx    # 代理教師錄取通知書模板
├── offer_leter_兼任教師.docx     # 兼任教師模板
├── contract_代理教師_鐘點制.docx  # 鐘點制代理合約
└── contract_代理教師_月薪制.docx   # 月薪制代理合約
```

## 限制與已知問題

1. **系統 Python 無法 pip install python-docx** — 使用 `minimax-docx` 的 C# OpenXML 方式
2. **LINEAR_API_KEY 需手動設定** — 第一次使用前需在 `~/.hermes/.env` 設定
3. **學校法律審查** — 正式聘用合約建議通過學校法規部門審查，不完全依赖自動生成
4. **代理人教師特約** — 鐘點制代理教師的勞健保計算是另一套邏輯（見 HR 單位規定）

## 依賴的現有 Skills

本 skill 整合以下現有 skills：

| Skill | 串接方式 |
|-------|---------|
| `linear-hr-workflow` | 用 GraphQL 查詢候選人資料 |
| `minimax-docx` | 用 C# OpenXML SDK 產出 .docx |
| `anthropic-draft-content` | 生成專業中文文案填入模板 |
| `anthropic-compliance-check` | 驗證文件符合台灣勞動法規 |

## If→Then 規則

**If** 用戶提到「產生錄取通知書」且有候選人姓名
**Then** 查 Linear API → 抓候選人狀態 → 確認是「錄取」→ 產出 .docx

**If** 用戶提到「代理教師聘用合約」且有鐘點費率
**Then** 使用 `generate_employment_contract_substitute()` 函數

**If** 候選人在 Linear 的狀態不是「錄取」
**Then** 先提示「請先在 Linear 將候選人狀態改為『錄取』再生成文件」

**If** 學校人事法規有特殊要求
**Then** 在產出後提醒「此文件需經學校法規部門審查後方可正式使用」