# SOP-C: 任務完成後上傳評價網站

## 觸發條件

完成任何會產生實體成果的任務（網站/程式/圖片/簡報/文件）後，**立即執行**。不要等到下次對話。

## 目標網站

- **URL**: `https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/`
- **API**: `POST https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works`
- **Auth**: Header `X-Agent-Key`，值在 `/home/hoonsoropenclaw/hermes-portal/.env.local` 的 `AGENT_API_KEY`

## 上傳格式（curl）

```bash
curl -X POST https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: $AGENT_API_KEY" \
  -d '{
    "title": "作品標題",
    "description": "作品描述（功能說明、技術栈）",
    "tags": ["python", "react"],
    "skill_used": ["skill-name"],
    "links": [
      {"url": "https://...", "label": "網站", "type": "weblink"},
      {"url": "https://github.com/...", "label": "GitHub", "type": "github"}
    ]
  }'
```

## 欄位說明

| 欄位 | 必填 | 說明 |
|------|------|------|
| `title` | ✅ | 作品標題，最多 200 字 |
| `description` | ❌ | 功能說明、技術栈 |
| `tags` | ❌ | 語言、框架、工具陣列 |
| `skill_used` | ❌ | 使用的技能名稱（與 SKILL.md 名稱一致） |
| `links` | ❌ | 連結陣列 |

**links.type 可選值**: `weblink`, `github`, `figma`, `pdf`, `demo`, `other`

## 狀態

新上傳作品 `status` 預設為 `review`（待審核）。

## Python 上傳範例

```python
import urllib.request, json

def upload_to_portal(title, description, tags, skill_used, links):
    # 讀取 AGENT_API_KEY
    env_path = '/home/hoonsoropenclaw/hermes-portal/.env.local'
    api_key = None
    with open(env_path) as f:
        for line in f:
            if line.startswith('AGENT_API_KEY='):
                api_key = line.strip().split('=', 1)[1]
                break

    data = json.dumps({
        'title': title,
        'description': description,
        'tags': tags or [],
        'skill_used': skill_used or [],
        'links': links or []
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
    description='這是什麼網站，功能和技術栈',
    tags=['python', 'react'],
    skill_used=['web-dev'],
    links=[
        {'url': 'https://my-site.vercel.app', 'label': '網站', 'type': 'weblink'},
        {'url': 'https://github.com/user/repo', 'label': 'GitHub', 'type': 'github'}
    ]
)
print(result['data']['id'])
```

## 每日排程自動檢查

- **腳本**: `/home/hoonsoropenclaw/scripts/portal_upload_check.sh`
- **Cron**: `0 9 * * *`（每日台灣時間 09:00）
- **功能**: 檢查所有作品的評價狀態，記錄未獲得評價的作品
- **Cron Job ID**: `1f8020b9485e`

## 關鍵原則

1. **立即上傳**：任務完成後馬上執行，不要延遲
2. **記錄 id**：保存返回的 `id`，用於追蹤評價狀態
3. **告知使用者**：明確告知已完成上傳，並附上作品 URL
4. **長期追蹤**：如果作品 > 7 天未獲得評價，主動提醒使用者

---

## ⚠️ 401 Unauthorized 故障排查（2026-06-04 更新）

### 典型徵兆

| 測試 | 結果 | 意義 |
|------|------|------|
| `GET /api/works` | 200 | server 正常，env var 有讀到 |
| `POST /api/works` | 401 `Invalid or missing X-Agent-Key` | `process.env.AGENT_API_KEY` 比對失敗 |

### 根本原因

`POST` handler 呼叫 `key === process.env.AGENT_API_KEY`，當後者為 `undefined` 或含隱形字元時，永遠比對失敗。明明 Vercel Dashboard 已設定，deployment 也是 Ready，但 server function 執行時的注入值有問題。

### 排查步驟

```bash
# Step 1: 確認本機 key
cat /home/hoonsoropenclaw/hermes-portal/.env.local | grep AGENT_API_KEY

# Step 2: 測試 GET（不需要 auth）
curl -s -w "\nHTTP_CODE: %{http_code}\n" \
  "https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works"

# Step 3: 測試 POST（需要 auth）
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST \
  "https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works" \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: hms_hermes_portal_secret_key_2026" \
  -d '{"title": "test"}'

# Step 4: OCR 截圖確認 Vercel env var 值
tesseract /home/hoonsoropenclaw/Snapshot/1150604-01.png stdout --psm 6
```

### 診斷矩陣

| GET | POST | 原因 |
|-----|------|------|
| 200 | 401 | `AGENT_API_KEY` 注入值有隱形字元/編碼問題（最常見）|
| 200 | 200 | ✅ 正常，問題解決 |
| 401/500 | - | server 有問題，env var 完全讀不到 |

### 解決方向（按順序）

1. **刪除後重建**：Vercel Dashboard → 刪除 `AGENT_API_KEY` row → 重新新增（確保值乾淨）
2. **確認 Scope**：Scope 必須包含 `Production`（不能只設在 Preview）
3. **等待生效**：redeploy 後等 2-3 分鐘再測，不要立刻測
4. **加 logging**：在 API handler 加入 `console.log('AGENT_API_KEY:', process.env.AGENT_API_KEY)`，redeploy 後查 Vercel logs 看實際注入值
5. **檢查本機檔案**：用 `xxd /home/hoonsoropenclaw/hermes-portal/.env.local | tail` 確認無 BOM/隱形字元