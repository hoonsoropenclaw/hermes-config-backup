---
name: hr-automation-workflow
description: HR 工作流自動化 — 履歷篩選、面試準備、入職報到的端到端自動化腳本。適用於學校人事（高中）場景，用 Python + AI API 實現無需昂貴 SaaS 的自動化。
version: 1.0.0
author: Hermes metacognitive-learner
platforms: [linux]
triggers: [hr, 人事, 招聘, 面試, 入職, 自動化]
---

# HR Automation Workflow — 履歷→面試→入職自動化

## 誰需要這個技能

高中人事主管（用戶場景）：
- 需要處理大量師生家長的行政請求
- 預算有限，無法使用昂貴的 Enterprise HR SaaS
- 需要自動化重複性任務（篩選履歷、生成面試問題、追蹤入職進度）

> **參考文件**：`references/school-hr-automation.md` — 學校 HR 特殊上下文、代理教師填補流程、與 anthropic-* 技能整合對照表

## 三階段工作流

```
階段 1：履歷篩選 (Resume Screening)
  └→ 輸入：候選人履歷（PDF/DOCX）
  └→ 處理：AI 解析 → 結構化資料 → 匹配度評分
  └→ 輸出：候選人排名表 + 詳細評估報告

階段 2：面試準備 (Interview Prep)
  └→ 輸入：候選人資料 + 應徵職位
  └→ 處理：生成个性化問題 → 建立評分rubric
  └→ 輸出：面試問題清單 + 評分標準

階段 3：入職追蹤 (Onboarding Tracker)
  └→ 輸入：新進人員名單
  └→ 處理：生成入職文件 → 追蹤待辦事項 → 發送提醒
  └→ 輸出：入職進度儀表板
```

## 核心腳本

### 履歷解析器 (resume_parser.py)

```python
#!/usr/bin/env python3
"""
HR Automation: 履歷解析與評分
輸入: 履歷檔案 (PDF/DOCX)
輸出: 結構化 JSON + 匹配度分數
"""

import json
import re
from pathlib import Path

def extract_text_from_resume(filepath: str) -> str:
    """從履歷檔案提取文字"""
    if filepath.endswith('.pdf'):
        try:
            import pymupdf
            doc = pymupdf.open(filepath)
            return '\n'.join(page.get_text() for page in doc)
        except ImportError:
            return "[pymupdf not installed - pip install pymupdf]"
    elif filepath.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(filepath)
            return '\n'.join(p.text for p in doc.paragraphs)
        except ImportError:
            return "[python-docx not installed - pip install python-docx]"
    return ""

def parse_resume(text: str) -> dict:
    """解析履歷文字，提取關鍵欄位"""
    # 姓名（第一行通常是姓名）
    lines = text.strip().split('\n')
    name = lines[0].strip() if lines else "Unknown"
    
    # 電話（多種格式）
    phone_match = re.search(r'[\d\(\)\-\s]{10,}', text)
    phone = phone_match.group(0).strip() if phone_match else ""
    
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""
    
    # 學歷（簡單關鍵字匹配）
    education_keywords = ['大學', '學院', '碩士', '博士', '学士', '硕士', '博士', 'Bachelor', 'Master', 'PhD']
    education = [kw for kw in education_keywords if kw in text]
    
    # 經驗年資（簡單估算）
    year_patterns = [
        r'(\d+)\s*年.*經驗',
        r'(\d+)\s*years?\s*experience',
        r'經驗\s*(\d+)\s*年'
    ]
    years_exp = 0
    for pattern in year_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            years_exp = int(match.group(1))
            break
    
    return {
        "name": name,
        "phone": phone,
        "email": email,
        "education": education,
        "years_experience": years_exp,
        "raw_text": text[:500]  # 前500字作為預覽
    }

def score_candidate(resume_data: dict, job_requirements: dict) -> dict:
    """根據職缺要求評分候選人"""
    score = 0
    max_score = 100
    
    # 學歷分數（根據要求的學歷層級）
    required_edu = job_requirements.get('min_education', '學士')
    edu_levels = ['高中', '專科', '學士', '碩士', '博士']
    try:
        required_idx = edu_levels.index(required_edu)
        actual_idx = 0
        for edu in resume_data.get('education', []):
            if edu in edu_levels:
                actual_idx = max(actual_idx, edu_levels.index(edu))
        score += 30 if actual_idx >= required_idx else 15
    except ValueError:
        score += 15  # 預設分數
    
    # 經驗分數
    required_years = job_requirements.get('min_years', 0)
    actual_years = resume_data.get('years_experience', 0)
    if actual_years >= required_years:
        score += 40
    elif actual_years >= required_years * 0.7:
        score += 25
    else:
        score += 10
    
    # 技能匹配（簡單計數）
    skills = job_requirements.get('required_skills', [])
    text_lower = resume_data.get('raw_text', '').lower()
    matched_skills = sum(1 for skill in skills if skill.lower() in text_lower)
    score += min(30, matched_skills * 10)
    
    return {
        **resume_data,
        "match_score": score,
        "max_score": max_score,
        "match_percentage": round(score / max_score * 100, 1)
    }

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 resume_parser.py <resume_file> [job_requirements_json]")
        print("Example: python3 resume_parser.py resume.pdf '{\"min_education\":\"學士\",\"min_years\":2}'")
        sys.exit(1)
    
    filepath = sys.argv[1]
    job_req = {"min_education": "學士", "min_years": 0, "required_skills": []}
    if len(sys.argv) >= 3:
        job_req = json.loads(sys.argv[2])
    
    text = extract_text_from_resume(filepath)
    if not text:
        print(json.dumps({"error": "Could not extract text from file"}))
        return
    
    resume_data = parse_resume(text)
    scored = score_candidate(resume_data, job_req)
    print(json.dumps(scored, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

### 面試問題生成器 (interview_generator.py)

```python
#!/usr/bin/env python3
"""
HR Automation: 根據候選人背景生成面試問題
輸入: 候選人資料 JSON + 職位
輸出: 個性化面試問題清單 + 評分rubric
"""

import json
import sys

DEFAULT_QUESTIONS = {
    "behavioral": [
        "請分享一個你克服困難的經驗。",
        "描述一次你需要與不同背景的人合作的情況。",
        "告訴我你如何處理期限緊迫的任務。",
    ],
    "situational": [
        "如果遇到不確定的情況，你會如何做決定？",
        "描述一次你需要在有限資源下完成任務的經驗。",
    ],
    "role_specific": {
        "行政": [
            "你如何處理多項任務同時進行的壓力？",
            "舉例說明你如何確保文件管理的準確性。",
        ],
        "教學": [
            "你如何設計一個吸引學生注意力的教案？",
            "描述一次你需要個別輔導學生的經驗。",
        ],
        "輔導": [
            "你如何建立與學生的信任關係？",
            "面對有情緒困擾的學生，你會如何處理？",
        ]
    }
}

def generate_interview_questions(candidate_data: dict, role: str) -> dict:
    """根據候選人背景和職位生成問題"""
    questions = {
        "candidate_name": candidate_data.get("name", "Unknown"),
        "role": role,
        "questions": []
    }
    
    # 加入通用問題
    for q in DEFAULT_QUESTIONS["behavioral"]:
        questions["questions"].append({"type": "behavioral", "question": q})
    
    for q in DEFAULT_QUESTIONS["situational"]:
        questions["questions"].append({"type": "situational", "question": q})
    
    # 加入職位特定問題
    role_category = "行政"  # 預設
    for key in DEFAULT_QUESTIONS["role_specific"]:
        if key in role:
            role_category = key
            break
    
    for q in DEFAULT_QUESTIONS["role_specific"].get(role_category, []):
        questions["questions"].append({"type": "role_specific", "question": q})
    
    # 根據候選人背景加入個人化問題
    years_exp = candidate_data.get("years_experience", 0)
    if years_exp > 3:
        questions["questions"].append({
            "type": "leadership",
            "question": "你曾經帶領團隊完成什麼專案？如何做到的？"
        })
    
    # 評分rubric
    questions["rubric"] = {
        "1": "未達預期 - 回答模糊、缺乏具體例子",
        "2": "部分符合 - 有基本概念但不够深入",
        "3": "符合預期 - 回答完整、有具體例子支持",
        "4": "超出預期 - 回答深入、展現系統性思考"
    }
    
    return questions

def main():
    if len(sys.argv) < 2:
        # 示範模式
        demo_candidate = {
            "name": "王小明",
            "years_experience": 5,
            "education": ["學士"]
        }
        result = generate_interview_questions(demo_candidate, "行政助理")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    candidate_data = json.loads(sys.argv[1])
    role = sys.argv[2] if len(sys.argv) > 2 else "行政"
    result = generate_interview_questions(candidate_data, role)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

### 入職追蹤器 (onboarding_tracker.py)

```python
#!/usr/bin/env python3
"""
HR Automation: 入職進度追蹤
輸入: 新進人員名單
輸出: 進度儀表板 + 待辦事項列表
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_ONBOARDING_TASKS = [
    {"task": "缴交证件复印件", "deadline_days": 1, "owner": "新進人員"},
    {"task": "填寫人事資料表", "deadline_days": 1, "owner": "新進人員"},
    {"task": "領取識別證", "deadline_days": 1, "owner": "人事"},
    {"task": "分配辦公位置", "deadline_days": 1, "owner": "總務"},
    {"task": "加入LINE群組", "deadline_days": 1, "owner": "新進人員"},
    {"task": "介绍部門同事", "deadline_days": 3, "owner": "直屬主管"},
    {"task": "安排設施培訓", "deadline_days": 5, "owner": "總務"},
    {"task": "確認第一個月目標", "deadline_days": 7, "owner": "直屬主管"},
    {"task": "完成試用期評估", "deadline_days": 90, "owner": "直屬主管"},
]

def create_onboarding_tracker(new_hires: list) -> dict:
    """為每位新進人員建立入職追蹤"""
    today = datetime.now()
    tracker = {
        "generated_at": today.isoformat(),
        "total_new_hires": len(new_hires),
        "new_hires": []
    }
    
    for hire in new_hires:
        start_date = datetime.fromisoformat(hire.get("start_date", today.isoformat()))
        hire_record = {
            "name": hire.get("name"),
            "position": hire.get("position"),
            "start_date": start_date.strftime("%Y-%m-%d"),
            "tasks": []
        }
        
        for task_template in DEFAULT_ONBOARDING_TASKS:
            deadline = start_date + timedelta(days=task_template["deadline_days"])
            days_until = (deadline - today).days
            
            hire_record["tasks"].append({
                "task": task_template["task"],
                "deadline": deadline.strftime("%Y-%m-%d"),
                "days_until": days_until,
                "status": "pending" if days_until >= 0 else "overdue",
                "owner": task_template["owner"]
            })
        
        # 計算進度
        completed = sum(1 for t in hire_record["tasks"] if t["status"] == "completed")
        total = len(hire_record["tasks"])
        hire_record["progress"] = f"{completed}/{total}"
        
        tracker["new_hires"].append(hire_record)
    
    return tracker

def print_tracker_dashboard(tracker: dict):
    """列印追蹤儀表板"""
    print(f"📋 入職追蹤儀表板 — 生成時間: {tracker['generated_at']}")
    print(f"總人數: {tracker['total_new_hires']}")
    print("=" * 60)
    
    for hire in tracker["new_hires"]:
        print(f"\n👤 {hire['name']} ({hire['position']})")
        print(f"   入職日期: {hire['start_date']} | 進度: {hire['progress']}")
        
        urgent = [t for t in hire["tasks"] if 0 <= t["days_until"] <= 3]
        if urgent:
            print("   ⚠️  近期待辦:")
            for t in urgent:
                print(f"      - {t['task']} (截止: {t['deadline']}, {t['owner']})")
        
        overdue = [t for t in hire["tasks"] if t["status"] == "overdue"]
        if overdue:
            print("   🔴 逾期:")
            for t in overdue:
                print(f"      - {t['task']} (截止: {t['deadline']})")

def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            new_hires = json.load(f)
    else:
        # 示範資料
        new_hires = [
            {"name": "王小明", "position": "行政助理", "start_date": "2026-06-01"},
            {"name": "陳大明", "position": "輔導老師", "start_date": "2026-06-03"},
        ]
    
    tracker = create_onboarding_tracker(new_hires)
    print_tracker_dashboard(tracker)
    
    # 同時輸出 JSON
    print("\n\n--- JSON OUTPUT ---")
    print(json.dumps(tracker, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

## 安裝依賴

```bash
# 履歷解析需要的套件
pip install pymupdf python-docx

# 全部安裝（建議）
pip install pymupdf python-docx openpyxl
```

## 使用範例

```bash
# 1. 解析履歷
python3 resume_parser.py "candidate_resume.pdf" '{"min_education":"學士","min_years":2,"required_skills":["文書處理","溝通"]}'

# 2. 生成面試問題
python3 interview_generator.py '{"name":"王小明","years_experience":5,"education":["學士"]}' "行政助理"

# 3. 追蹤入職進度
echo '[{"name":"王小明","position":"行政助理","start_date":"2026-06-01"}]' > new_hires.json
python3 onboarding_tracker.py new_hires.json
```

## If→Then 規則

- **If** 用戶提到「處理履歷」、「篩選候選人」
- **Then** 載入 `hr-automation-workflow` 技能，使用 `resume_parser.py` + `interview_generator.py`

- **If** 用戶提到「新進人員」、「入職流程」、「追蹤入職」
- **Then** 載入 `hr-automation-workflow` 技能，使用 `onboarding_tracker.py`

- **If** 需要處理大量履歷（>10份）
- **Then** 先批次轉換為文字，再批次評分，最后排序輸出

## 學校 HR 特殊上下文

學校人事（高中）與企業 HR 有關鍵差異，自動化設計必須因應：

| 維度 | 企業 HR | 學校 HR（高中）|
|------|---------|----------------|
| 招聘規模 | 每次數十人 | 每次 1-5 人 |
| 時效性 | 數週~數月招聘週期 | **代理教師需 24-48 小時內找到** |
| 主要痛點 | 人才庫管理 | **即時代課老師填補** |
| 法規限制 | 勞基法 | 教師法、代理教師辦法、各縣市教育局規定 |
| 薪資談判 | 區間灵活 | **鐘點費/月薪制，有法定上限** |

**學校 HR 最高優先自動化**：代理教師（即代課老師）快速填補，因企業 ATS 不適合這個場景。

### 與 anthropic-* 技能的整合

這個技能的腳本並非要取代企業 SaaS，而是彌補預算限制。實際執行時，**先用現有 anthropic-* 技能做分析和生成，再用人權腳本做結構化處理**：

```
收到候選人履歷
  → anthropic-explore-data（結構化分析）
  → anthropic-customer-research（背景調查）
  → anthropic-draft-content（生成溝通信）
  → hr-automation-workflow（履歷解析 + 評分）
  → anthropic-call-prep（面試準備 brief）
```

## 相關技能

- `job-post-builder`：建立招聘套件（職缺描述、面談 guide）
- `smb-onboard`：入職流程模板
- `python-anti-patterns`：避免常見 Python 陷阱
- `python-resilience`：增強腳本的錯誤處理