---
name: portal-auto-upload
description: "任務完成後自動上傳成果至 Hermes Portal 評價網站。處理任何會產出網站/程式/圖片/簡報的任務時，必須載入此技能。"
version: 1.0.0
tags: [hermes-portal, 自動上傳, 評價網站, 工作流程]
---

# 評價網站自動上傳 SOP

完成任何會產生實體成果的任務（網站、程式、圖片、簡報、文件等）後，**立即**執行以下流程。

## 目標網站

- **URL**: https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/
- **API Endpoint**: `POST https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works`
- **Auth Header**: `X-Agent-Key`（值在 `/home/hoonsoropenclaw/hermes-portal/.env.local` 的 `AGENT_API_KEY`）

## 上傳時機

每當完成以下類型任務時，**必須**上傳：
- ✅ 網站部署完成
- ✅ 程式碼完成（GitHub repo 建立）
- ✅ 圖片/設計產出
- ✅ 簡報文件完成
- ✅ 資料分析結果
- ✅ 報告產出

## 上傳方式

### 方法一：curl 直接上傳

```bash
curl -X POST https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: $AGENT_API_KEY" \
  -d '{
    "title": "作品標題",
    "description": "作品描述",
    "tags": ["tag1", "tag2"],
    "skill_used": ["skill-name"],
    "links": [
      {"url": "https://...", "label": "網站", "type": "weblink"},
      {"url": "https://...", "label": "GitHub", "type": "github"}
    ]
  }'
```

### 方法二：使用 Python（方便處理動態內容）

```python
import urllib.request, json, os

def upload_to_portal(title, description, tags, skill_used, links):
    with open('/home/hoonsoropenclaw/hermes-portal/.env.local') as f:
        for line in f:
            if line.startswith('AGENT_API_KEY='):
                api_key = line.strip().split('=', 1)[1]

    data = json.dumps({
        'title': title,
        'description': description,
        'tags': tags,
        'skill_used': skill_used,
        'links': links
    }).encode()

    req = urllib.request.Request(
        'https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works',
        data=data,
        headers={
            'Content-Type': 'application/json',
            'X-Agent-Key': api_key
        },
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# 使用範例
result = upload_to_portal(
    title='網站標題',
    description='這是一個什麼網站，功能和技術栈',
    tags=['python', 'react'],
    skill_used=['web-dev', 'python'],
    links=[
        {'url': 'https://my-site.vercel.app', 'label': '網站', 'type': 'weblink'},
        {'url': 'https://github.com/user/repo', 'label': 'GitHub', 'type': 'github'}
    ]
)
print(result)
```

## 任務完成後的 SOP 步驟

1. **完成任務** → 產出實體成果
2. **立即上傳** → 用 `POST /api/works` 將作品上傳評價網站
3. **記錄 response** → 保存返回的 `id`，用於追蹤評價狀態
4. **口頭告知使用者** → 明確告知已完成上傳，並附上作品 URL
5. **長期追蹤** → 如果作品 > 7 天未獲得評價，主動提醒使用者

## 欄位規格

| 欄位 | 必填 | 說明 |
|------|------|------|
| `title` | ✅ | 作品標題，最多 200 字 |
| `description` | ❌ | 詳細描述、功能說明、技術栈 |
| `tags` | ❌ | 標籤陣列（語言、框架、工具） |
| `skill_used` | ❌ | 使用的技能名稱（與 SKILL.md 名稱一致） |
| `links` | ❌ | 連結陣列 |

**links.type 可選值**: `weblink`, `github`, `figma`, `pdf`, `demo`, `other`

## 排程自動檢查

- **腳本路徑**: `/home/hoonsoropenclaw/scripts/portal_upload_check.sh`
- **Cron**: `0 9 * * *`（每日台灣時間 09:00）
- **用途**: 檢查所有作品是否有評價，記錄未獲評價的作品

## 注意事項

- 新上傳作品 status 預設為 `review`（待審核）
- 如果一次任務有多個獨立產出，分開上傳
- 如果是部署到 Vercel 的網站，URL 格式應為 `https://*.vercel.app`
- GitHub 連結 type 填 `github`，網站連結填 `weblink`