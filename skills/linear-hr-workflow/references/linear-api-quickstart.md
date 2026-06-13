# Linear API Quickstart & Troubleshooting

## 2026-06-13 新增：API Key 驗證腳本

LINEAR_API_KEY 目前**未設定**於 `~/.hermes/.env`。使用此 skill 前必須完成設定。

### 步驟 1：確認 Key 是否存在

```bash
grep LINEAR_API_KEY ~/.hermes/.env && echo "EXISTS" || echo "MISSING"
```

### 步驟 2：若不存在，引導用戶取得並存入

1. 登入 Linear → 右上角頭像 → Settings → API
2. **注意**：Linear 有兩處 API 頁面：
   - `Settings > Account > Security & access > Personal API keys` ← **個人 key（用這個）**
   - `Settings > API` ← **只顯示 OAuth App 和 workspace key，沒有個人 key**
3. 建立 Personal API Key（任意名稱）
4. 存入 `~/.hermes/.env`：`LINEAR_API_KEY=lin_api_...`
5. 驗證：`python3 -c "import os,requests; r=requests.post('https://api.linear.app/graphql',headers={'Authorization':os.getenv('LINEAR_API_KEY'),'Content-Type':'application/json'},json={'query':'{ viewer { id name } }'}); print(r.json())"`

---

## ⚠️ Authorization Header 格式（重要修正）

**Linear API Key 不使用 `Bearer` 前綴**。正確格式：

```python
# ✅ 正確
HEADERS = {
    'Authorization': LINEAR_API_KEY,   # 直接放 key，無 Bearer
    'Content-Type': 'application/json'
}

# ❌ 錯誤（不要用）
HEADERS = {
    'Authorization': f'Bearer {LINEAR_API_KEY}',  # Linear 不接受 Bearer
    'Content-Type': 'application/json'
}
```

**根因**：Linear API 文件使用 `Authorization: $LINEAR_API_KEY`（無 Bearer），GraphQL API 不是 OAuth 2.0 flow。

---

## 常見錯誤對照表

| 錯誤訊息 | 原因 | 解法 |
|---------|------|------|
| `{"errors":[{"code":"unauthorized","type":"UnauthorizedException"}]}` | API key 無效或過期 | 重新取得 key 並更新 `~/.hermes/.env` |
| `{"errors":[{"code":"not_found","type":"NotFoundException"}]}` | Team ID 或 Issue ID 不存在 | 確認 team id：`teams(first:10)` query |
| `{"errors":[{"code":"validation_error","type":"ValidationException"}]}` | GraphQL 變數格式錯誤 | 檢查必填欄位（如 `teamId`） |
| HTTP 400 + `RATELIMITED` | 每小時 2,500 次限制 | 等 `X-RateLimit-Requests-Reset` 時間到 |
| `{"errors":[{"code":"complexity_limit"}]}` | 複雜度點數超標 | 減少 `first:N` 的 N 值 |

---

## Python 驗證腳本（含錯誤處理）

```python
import os, requests

def verify_linear_api_key():
    key = os.getenv('LINEAR_API_KEY')
    if not key:
        print("ERROR: LINEAR_API_KEY not found in environment")
        return False
    
    r = requests.post(
        'https://api.linear.app/graphql',
        headers={'Authorization': key, 'Content-Type': 'application/json'},
        json={'query': '{ viewer { id name email } }'}
    )
    data = r.json()
    
    if 'errors' in data:
        error = data['errors'][0]
        print(f"API Error: {error['code']} - {error.get('message', '')}")
        return False
    
    viewer = data['data']['viewer']
    print(f"✅ Connected as: {viewer['name']} ({viewer['email']})")
    return True

if __name__ == '__main__':
    verify_linear_api_key()
```
