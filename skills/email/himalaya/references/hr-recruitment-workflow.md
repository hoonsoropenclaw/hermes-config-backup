# HR Recruitment Email Workflow — for school HR (himalaya)

學校人事主管（高中）使用 himalaya 做招募候選人溝通的 workflow。

## 核心原理

學校 HR 與企業 HR 的差異：
- **代理教師（即時代課）**：即時性高，不可走一般 44 天招聘週期
- **規模小**：每次只聘 1-3 人，大型 ATS 過度複雜
- **暑期密集**：學期結束前後需要快速補充大量教師

`himalaya` 可批次發送個人化 email，結合 `linear-hr-workflow` 可同時更新候選人狀態。

## 前提條件

1. `himalaya` 已設定（IMAP/SMTP）
2. `LINEAR_API_KEY` 已設定（用於整合 Linear 狀態更新）
3. 學校 HR email 已配置（如 `hr@school.edu.tw`）

## 批次發送招募 email（Python 腳本）

```python
#!/usr/bin/env python3
"""send_hr_emails.py — 批次發送 HR 招募 email"""

import subprocess, os

# 候選人資料（從 Linear API 或 CSV 讀取）
candidates = [
    {'name': '張三', 'email': 'zhangsan@mail.com', 'subject': '【面試邀請】數學代理教師', 'position': '數學代理教師', 'interview_time': '6/20（五）上午 10:00', 'school': '某某高中'},
    {'name': '李四', 'email': 'lisi@mail.com', 'subject': '【面試邀請】英文代理教師', 'position': '英文代理教師', 'interview_time': '6/21（六）上午 10:00', 'school': '某某高中'},
]

for c in candidates:
    email_body = f"""親愛的 {c['name']} 您好：

恭喜您通過初審，誠摯邀請您於 {c['interview_time']} 到 {c['school']} 參加{c['position']}面試。

面試地點：{c['school']} 人事室
攜帶文件：教師證、身分證、學歷證明

如有任何問題，請回覆此信。

{os.getenv('HR_SIGNATURE', '學校人事處')}"
    
    # 用 himalaya stdin pipe 發送（無需互動式編輯器）
    cmd = f'''cat << 'MAILEOF' | himalaya template send
From: hr@school.edu.tw
To: {c['email']}
Subject: {c['subject']} - {c['name']}

{email_body}
MAILEOF'''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ Sent to {c['name']} <{c['email']}>")
    else:
        print(f"✗ Failed: {result.stderr}")
```

## 個人化 Offer Letter 範本

```bash
cat << 'EOF' | himalaya template send
From: hr@school.edu.tw
To: CANDIDATE_EMAIL
Subject: 【錄取通知】代理教師 - NAME 您好

親愛的 NAME 您好：

恭喜您通過面試，正式錄取為本校 CURRICULUM 代理教師。

【僱用條件】
- 職務：CURRICULUM 代理教師
- 到職日：START_DATE
- 薪資：依學校代理教師薪資規定

請於到職日前回覆此信確認報到。

如有任何問題，請聯繫人事室。

學校人事處
DATE
EOF
```

## 拒絕通知範本（保留人味）

> ⚠️ 自動化拒絕郵件在教師招募中有風險。研究顯示（Teach Away 2026）：機械化制式格式會損害學校聲譽。候選人越深入招募流程，拒絕信越需要個人化。

```bash
cat << 'EOF' | himalaya template send
From: hr@school.edu.tw
To: CANDIDATE_EMAIL
Subject: Re: 【應徵】POSITION - 感謝您的投入

親愛的 NAME 您好：

感謝您投入時間申請我校 POSITION 職位。您豐富的經驗和背景讓我們印象深刻。

經過審慎討論，我們決定暫不進入下一階段。這不是對您能力的否定，而是我們目前職缺與您的時間安排未能完全匹配。

您的聯絡方式已存入我們的人才庫，未來有合適機會時會再與您聯繫。

感謝您對我校教育的熱忱，祝順利。

學校人事處
DATE
EOF
```

## 與 Linear 整合（狀態同步）

每次 email 狀態變化時，同步更新 Linear issue：

```python
import requests, os

LINEAR_API_KEY = os.getenv('LINEAR_API_KEY')
HEADERS = {'Authorization': LINEAR_API_KEY, 'Content-Type': 'application/json'}

def update_linear_state(issue_id, new_state_name):
    """根據 email 動作更新 Linear issue 狀態"""
    # 先查 state ID
    query = '{ states(first: 20) { nodes { id name } } }'
    r = requests.post('https://api.linear.app/graphql', headers=HEADERS, json={'query': query})
    states = r.json()['data']['states']['nodes']
    state_id = next((s['id'] for s in states if s['name'] == new_state_name), None)
    
    if state_id:
        mutation = 'mutation issueUpdate($id: String!, $stateId: String!) { issueUpdate(id: $id, input: {stateId: $stateId}) { success } }'
        requests.post('https://api.linear.app/graphql', headers=HEADERS, json={
            'query': mutation, 'variables': {'id': issue_id, 'stateId': state_id}
        })

# 使用場景：
# - 發送「面試邀請」email → update_linear_state(issue_id, '待複審')
# - 發送「錄取通知」email → update_linear_state(issue_id, '已錄取')
# - 發送「未錄取」email → update_linear_state(issue_id, '未錄取')
```

## 查詢 HR 相關郵件

```bash
# 查閱所有 HR 相關郵件（面試邀請/回覆/offer letter 回覆）
himalaya envelope list --output json --page 1 --page-size 50 | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
keywords = ['面試', 'offer', '代理', '教師', '錄取', '未錄取']
for e in data:
    subject = e.get('subject', '')
    if any(k in subject for k in keywords):
        print(f\"{e['id']} | {e['date']} | {subject}\")
"
```

## If→Then 規則

**If** 收到代理教師簡歷且要快速發面試邀請
**Then** 用 himalaya stdin pipe 批次發送含候選人姓名/職位/時間的個人化邀請，不用手動一封封寫

**If** 需要一次發送多封錄取通知/offer letter
**Then** 用 Python 迴圈 + himalaya stdin pipe，每封 personal化（姓名、科目、到職日、學校名），不要複製貼上

**If** 要發送「未錄取」通知但希望保留人味
**Then** 避免完全自動化的制式格式，在 email 中加入「感謝您投入的時間」等個人化語句

**If** 學校 HR 想用 CLI 完全自動化發送招募 email
**Then** 整合 `himalaya` + `linear-hr-workflow`：email 發出後同步更新 Linear issue 狀態

**If** 要從 himalaya 查閱所有 HR 相關郵件
**Then** 用 `himalaya envelope list --output json` + grep 關鍵字過濾，不要手動一頁頁翻

## 限制

1. **himalaya template send 需要 stdin pipe**：不要用 `himalaya message write`（需要互動式編輯器）
2. **Gmail 需要 App Password**：若使用 Gmail，須先在 Google 帳號設定 App Password
3. **學校 mail server 可能限制發送頻率**：大量發送時注意速率
4. **LINEAR_API_KEY 需另外設定**：himalaya skill 只處理 email，Linear 狀態同步需另外設定