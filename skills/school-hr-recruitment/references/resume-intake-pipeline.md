# Resume Intake Pipeline — W9 Reference

## 端到端 Pipeline

```
履歷 PDF（email attachment 或 URL）
    ↓
Step 1: 文字提取（系統 Python /usr/bin/python3 + pdfminer.six）
    ↓
Step 2: LLM 結構化解析（MiniMax API → JSON）
    ↓
Step 3: 建立 Linear 候選人追蹤 issue（W2 mutation）
    ↓
候選人狀態：待聯繫
```

## 環境差異

| 環境 | Python 路徑 | pdfplumber | pdfminer | 可用 |
|-------|------------|------------|----------|------|
| hermes-agent venv | `~/.hermes/hermes-agent/venv/bin/python3` | ❌ | ❌ | ❌ |
| System Python | `/usr/bin/python3` | ✅ | ✅ | ✅ |

**驗證命令**：
```bash
/usr/bin/python3 -c "import pdfplumber; print('pdfplumber ok')"
/usr/bin/python3 -c "import pdfminer; print('pdfminer ok')"
```

## 履歷 Intake 腳本（完整可執行）

`~/bin/resume-to-linear.py`：
```python
#!/usr/bin/python3
"""履歷 PDF → Linear 候選人追蹤

用法: resume-to-linear.py <resume.pdf> <linear_team_id>

依賴:
  - 系統 Python (/usr/bin/python3) 含 pdfminer.six
  - MINIMAX_API_KEY, LINEAR_API_KEY 在 ~/.hermes/.env
  - python-docx (系統 Python)

  安裝依賴: /usr/bin/pip3 install pdfminer.six python-docx requests
"""

import sys, os, re, json, subprocess
from pathlib import Path
from pdfminer.high_level import extract_text

def extract_pdf_text(pdf_path):
    """用 pdfminer 提取履歷文字（掃描件回傳空字串）"""
    text = extract_text(pdf_path)
    if not text.strip():
        # 嘗試 OCR
        return None  # marker-pdf 未安裝，標記需人工
    return text

def parse_resume_llm(text):
    """用 MiniMax API 結構化解析"""
    import requests
    prompt = f"""從以下履歷中結構化提取欄位，只輸出 JSON：

{{
  "name": "候選人姓名",
  "email": "電子郵件",
  "phone": "聯絡電話",
  "position": "應徵職位",
  "education": "最高學歷",
  "experience": "主要工作經歷（100字內）"
}}

履歷文字：
{text[:4000]}
"""
    resp = requests.post(
        'https://api.minimax.chat/v1/text/chatcompletion_pro',
        headers={'Authorization': f"Bearer {os.getenv('MINIMAX_API_KEY')}"},
        json={'model': 'MiniMax-Text-01', 'messages': [{'role': 'user', 'content': prompt}]}
    )
    raw = resp.json()['choices'][0]['message']['content']
    # 去除 markdown code block
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)

def create_linear_issue(candidate, team_id):
    """用 GraphQL 建立 Linear issue"""
    import requests
    mutation = """
    mutation issueCreate($title: String!, $teamId: String!, $description: String) {
      issueCreate(input: {title: $title, teamId: $teamId, description: $description}) {
        success
        issue { id identifier title }
      }
    }
    """
    resp = requests.post(
        'https://api.linear.app/graphql',
        headers={'Authorization': os.getenv('LINEAR_API_KEY'), 'Content-Type': 'application/json'},
        json={'query': mutation, 'variables': {
            'title': f"【求職】{candidate['position']} - {candidate['name']}",
            'teamId': team_id,
            'description': f"## 候選人資料\n"
                           f"- 姓名：{candidate['name']}\n"
                           f"- Email：{candidate['email']}\n"
                           f"- 電話：{candidate['phone']}\n"
                           f"- 應徵職位：{candidate['position']}\n"
                           f"- 學歷：{candidate['education']}\n\n"
                           f"## 經歷\n{candidate['experience']}"
        }}
    )
    return resp.json()

if __name__ == '__main__':
    pdf_path, team_id = sys.argv[1], sys.argv[2]
    print(f"Extracting: {pdf_path}")
    text = extract_pdf_text(pdf_path)
    if text is None:
        print("❌ 掃描件 PDF，無法自動提取。請手動建立 Linear issue。")
        sys.exit(1)
    print("✅ PDF text extracted")
    candidate = parse_resume_llm(text)
    print(f"✅ Parsed: {candidate['name']} / {candidate['position']}")
    result = create_linear_issue(candidate, team_id)
    if result.get('data', {}).get('issueCreate', {}).get('success'):
        issue = result['data']['issueCreate']['issue']
        print(f"✅ Linear issue created: {issue['identifier']} - {issue['title']}")
    else:
        print(f"❌ Error: {result}")
```

## 暑期批次處理

對於暑期密集招聘（一次多份履歷）：

```bash
#!/usr/bin/bash
# 批次處理目錄中所有 PDF
for pdf in /path/to/resumes/*.pdf; do
    /usr/bin/python3 ~/bin/resume-to-linear.py "$pdf" "YOUR_TEAM_ID"
done
```

或 Python 平行處理：
```python
from concurrent.futures import ThreadPoolExecutor
import subprocess

pdfs = list(Path("/path/to/resumes").glob("*.pdf"))
with ThreadPoolExecutor(max_workers=4) as ex:
    results = list(ex.map(lambda p: subprocess.run(
        ['/usr/bin/python3', str(p), 'YOUR_TEAM_ID']
    ), pdfs))
```

## 常見問題

| 問題 | 解法 |
|------|------|
| `ModuleNotFoundError: No module named 'pdfplumber'` | 用 `/usr/bin/python3` 而非 venv python |
| PDF 文字是空的（掃描件） | marker-pdf 未安裝，需手動 OCR 或用 `pytesseract` |
| LLM 解析 JSON 格式錯誤 | 增加 prompt 中的 JSON 格式範例 |
| Linear API 401 | API key 過期，重新設定 `LINEAR_API_KEY` |
