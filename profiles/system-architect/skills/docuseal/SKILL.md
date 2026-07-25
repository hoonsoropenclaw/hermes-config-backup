---
name: docuseal
description: DocuSeal - 開源數位文件簽署平台，可作為 DocuSign 替代方案。支援 PDF 表單建立、批量發送、API 整合、電子簽名。適用於學校公文簽核、聘僱合約、表單收集等場景。
---

# DocuSeal - 數位文件簽署系統

## 概述

DocuSeal 是一個開源的數位文件簽署平台（DocuSign 替代方案），支援 Docker 快速部署，提供完整的文件簽署流程自動化。

**官方網站**: https://www.docuseal.com  
**線上演示**: https://demo.docuseal.tech  
**GitHub**: https://github.com/docusealco/docuseal

## 核心功能

- ✅ PDF 表單建立（WYSIWYG 編輯器）
- ✅ 12 種欄位類型（簽名、日期、檔案上傳、核取方塊等）
- ✅ 多人填寫（Multiple submitters per document）
- ✅ 自動化 Email（SMTP 整合）
- ✅ 多种儲存後端（磁碟、AWS S3、Google Storage、Azure）
- ✅ API + Webhooks 整合
- ✅ 快速部署（Docker 一鍵部署）
- ✅ 公司 Logo + 白牌
- ✅ 批量發送（CSV/XLSX）
- ✅ SSO / SAML
- ✅ 嵌入式簽署表單（React/Vue/Angular/JS）

## 部署方式

### Docker 單機部署（最簡單）

```bash
docker run --name docuseal -p 3000:3000 -v .:/data docuseal/docuseal
```

### docker-compose 部署（自動 HTTPS）

```bash
curl https://raw.githubusercontent.com/docusealco/docuseal/master/docker-compose.yml > docker-compose.yml
sudo HOST=your-domain-name.com docker compose up
```

### 其他快速部署選項

- **Railway**: `https://railway.com/deploy/IGoDnc`
- **DigitalOcean**: `https://cloud.digitalocean.com/apps/new?repo=...`
- **Render**: `https://render.com/deploy?repo=...`
- **Heroku**: `https://heroku.com/deploy?template=...`

## API 基本操作

DocuSeal 提供 RESTful API，可用於與學校系統整合。

### 建立範本（HTML 方式）

```http
POST /api/templates
Content-Type: application/json

{
  "name": "新進教師聘僱合約",
  "html": "<html><body>...</body></html>"
}
```

### 欄位標籤格式

在 HTML 中使用 `docuseal` 屬性：

| 欄位類型 | 語法 | 說明 |
|----------|------|------|
| 文字輸入 | `<input type="text" name="name" docuseal="text">` | 一般文字 |
| 簽名 | `<input type="text" name="sig" docuseal="signature">` | 電子簽名 |
| 日期 | `<input type="date" docuseal="date">` | 日期選擇 |
| 核取方塊 | `<input type="checkbox" docuseal="checkbox">` | 是/否選項 |
| 檔案上傳 | `<input type="file" docuseal="file">` | 附加檔案 |

### DOCX/PDF 範本欄位標籤

在文件中嵌入這些標籤：

| 標籤 | 類型 |
|------|------|
| `{{signature}}` | 簽名欄位 |
| `{{date}}` | 日期欄位 |
| `{{text:field_name}}` | 文字輸入 |
| `{{checkbox:option1}}` | 核取方塊 |

### 批量發送

```csv
# data.csv
email,name,department
teacher1@school.edu.tw,王小明,數學組
teacher2@school.edu.tw,陳大同,國文科
```

上傳 CSV 選擇模板，系統自動批量發送至每位 submitter。

### Webhooks

DocuSeal 支援 Webhooks，可在以下事件觸發通知：

- `form.opened` - 文件被開啟
- `form.completed` - 文件完成簽署
- `form.declined` - 文件被拒絕
- `form.expired` - 文件過期

```json
{
  "event": "form.completed",
  "submission_id": 1,
  "template_id": 1,
  "completed_at": "2023-12-14T15:49:21.701Z",
  "values": [
    {"field": "Full Name", "value": "John Doe"}
  ]
}
```

## 學校應用場景

### 1. 新進教師聘僱流程

1. 建立聘僱合約範本（包含簽名、日期欄位）
2. 批量發送至所有新進教師
3. 追蹤完成狀態
4. 自動發送提醒

### 2. 公文簽核自動化

- 將傳統列印 → 簽名 → 掃描流程改為線上簽署
- 所有文件自動歸檔

### 3. 家長同意書收集

- 建立同意書範本
- 批量發送至家長
- 手機即可填寫

## Python SDK 整合

```python
import requests

DOCUSEAL_URL = "https://your-docuseal.example.com"
API_KEY = "your-api-key"

def create_template(name, html_content):
    response = requests.post(
        f"{DOCUSEAL_URL}/api/templates",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"name": name, "html": html_content}
    )
    return response.json()

def send_for_signature(template_id, emails):
    response = requests.post(
        f"{DOCUSEAL_URL}/api/submissions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "template_id": template_id,
            "submitters": [{"email": email} for email in emails]
        }
    )
    return response.json()
```

## 限制與考量

- License: AGPLv3 + Section 7(b) Additional Terms
- 自託管版本需要自行維護伺服器
- 繁體中文UI支援（14種語言）

---

*最後更新：2026-05-07*