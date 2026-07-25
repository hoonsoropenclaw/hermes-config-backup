# 面試評分表生成 — Phase 4 實作參考

**檔案**: `references/interview-scorecard-phase4.md`
**建立**: 2026-06-23（metacognitive-learner cycle）
**用途**: Phase 4 評分表生成的技術實作細節

---

## 完整 Phase 4 工作流

```
用戶：「面試完了，要建立評分表」
    ↓
1. 從 Google Calendar event 取出 attendees（候選人 email + 面試時間）
2. 在 Google Sheets 建立 templated scorecard（新 spreadsheet）
3. 把候選人資訊（姓名/時間/職位）填入 sheet header
4. 寄送 Sheets URL 給面試官（用 himalaya 或直接日曆邀請）
    ↓
面試官在 Sheets 填寫維度分數（1-5 分）
    ↓
HR 或赫米斯 script 從 Sheets 讀取分數
    ↓
將分數回寫 Linear 候選人 record（W5）
    ↓
根據門檻（總分 ≥ 20/25）給出「建議錄取 / 不建議 / 再議」
```

---

## 技術棧確認（2026-06-23 N100 實測）

| 組件 | 狀態 |
|------|------|
| `google-api-python-client` | ✅ 已安裝 |
| `google-auth` | ✅ 已安裝（google-api-python-client 依賴） |
| `openpyxl` | ❌ 需 `uv pip install openpyxl`（Python 3.11 相容）|
| `pandas` | ❌ 未安裝 |
| `gspread` | ❌ 未安裝 |
| Linear GraphQL API | ✅ 可用（需 `LINEAR_API_KEY`） |

---

## Google Sheets API 核心呼叫

### 建立評分表（`spreadsheets.create`）

```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
service = build('sheets', 'v4', credentials=creds)

# 建立新 spreadsheet
body = {
    'properties': {'title': '【面試評分】張三 - 數學教師 - 2026-06-20'},
    'sheets': [{
        'properties': {'title': '評分表'},
        'data': [{
            'range': 'A1:G7',
            'values': [
                ['【面試評分表】'],
                ['候選人', '張三', '', '職位', '數學教師'],
                ['面試時間', '2026-06-20 10:00', '', '面試官', '(待填)'],
                [''],
                ['維度', '分數（1-5）', '備註'],
                ['專業知識', '', ''],
                ['表達能力', '', ''],
                ['態度與價值觀', '', ''],
                ['適任性', '', ''],
                ['總分', '=SUM(B6:B9)', ''],
                ['建議', '=IF(B10>=20,"建議錄取",IF(B10>=15,"再議","不建議"))', ''],
            ]
        }]
    }]
}
result = service.spreadsheets().create(body=body).execute()
spreadsheet_id = result['spreadsheetId']
spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
```

### 從 Calendar Event 取候選人資訊

```python
# event_id 來自 create_interview.py 的輸出
event = service.events().get(
    calendarId='primary',
    eventId=event_id,
    fields='attendees,start,summary'
).execute()

attendees = event.get('attendees', [])
candidate = next((a for a in attendees if a.get('email') != HR_EMAIL), None)
start_time = event['start']['dateTime']
summary = event.get('summary', '')
# 從 summary 取出職位：「【面試】張三 - 數學教師」
position = summary.split(' - ', 1)[-1] if ' - ' in summary else ''
```

### 將分數回寫 Linear

```python
import urllib.request
import json

query = """
mutation UpdateCandidate($candidateId: String!, $input: CandidateUpdateInput!) {
  candidateUpdate(id: $candidateId, input: $input) {
    id
  }
}
"""
variables = {
    "candidateId": "CANDIDATE_DB_ID",
    "input": {
        "state": "done",          # W5 面試完成
        "score": 22,             # 總分（1-25）
        "feedback": "專業知識佳，表達清晰，建議錄取"
    }
}

data = json.dumps({"query": query, "variables": variables}).encode()
req = urllib.request.Request(
    "https://api.linear.app/graphql",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + LINEAR_API_KEY
    }
)
with urllib.request.urlopen(req) as resp:
    print(json.load(resp))
```

---

## 維度設計（標準化）

| 維度 | 評分標準（5=最佳） |
|------|------------------|
| 專業知識（25%）| 5=完整掌握學科知識，能深入淺出 / 3=基本正確但深度不足 / 1=明顯錯誤 |
| 表達能力（25%）| 5=邏輯嚴謹、口齒清晰 / 3=基本能傳達 / 1=表達混亂 |
| 態度與價值觀（25%）| 5=積極配合、價值觀與學校契合 / 3=被動配合 / 1=消極或價值觀不合 |
| 適任性（25%）| 5=完全適應學校文化 / 3=基本適應 / 1=明顯格格不入 |
| **門檻** | **總分 ≥ 20/25 → 建議錄取 / 15-19 → 再議 / <15 → 不建議** |

---

## 依賴 Phase 4 的 Scripts

待本 skill 的 SKILL.md version 升至 `1.1.0` 後，應新增：
- `scripts/create_scorecard.py` — 根據 Calendar event 建立 Sheets 評分表
- `scripts/update_scorecard.py` — 從 Sheets 讀取分數並回寫 Linear

---

## 已知限制

1. **LINEAR_API_KEY 未設定**：Phase 4 的「回寫 Linear」依賴此 key，需先確認 `~/.hermes/.env.local` 有設定
2. **`openpyxl` 未安裝**：`minimax-xlsx` skill 的 `.xlsx` 驗證需要先 `uv pip install openpyxl`
3. **Sheet template 非結構化**：目前無 standard template，Phase 4 script 需自己建立 layout
