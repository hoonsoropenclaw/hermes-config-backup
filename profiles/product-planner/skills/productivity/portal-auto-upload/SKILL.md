---
name: portal-auto-upload
description: "任務完成後自動上傳成果至 Hermes Portal 評價網站。處理任何會產出網站/程式/圖片/簡報的任務時，必須載入此技能。"
version: 1.1.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [hermes-portal, 自動上傳, 評價網站, 工作流程]
    related-skills: [portal-judge-agent]
    triggers: [任務完成, 網站部署, 程式完成, 圖片產出, 簡報完成]
---

# 評價網站自動上傳 SOP

完成任何會產生實體成果的任務（網站、程式、圖片、簡報、文件等）後，**立即**執行上傳流程。

## 目標網站

| 項目 | 值 |
|------|-----|
| **Canonical URL** | `https://hermes-portal.vercel.app/` |
| API Endpoint | `POST https://hermes-portal.vercel.app/api/works` |
| Vercel Project ID | `prj_uUsJw3x4NZCofkO1KKFT7viCNvLD` |
| Project Name | `hermes-portal` |
| Auth Header | `X-Agent-Key` |

**⚠️ 注意**：
- **Canonical URL = `hermes-portal.vercel.app`**（2026-06-07 確認生效的 alias）。**舊 deployment URL `hermes-portal-akqkd6vpj-...vercel.app` 已過時** — 它是 22h 前的某次 deployment hash，現在都 401 protected。**永遠用 canonical URL**。
- hermes-portal（評價網站）≠ hermes-status-site（自身狀態網站）。兩個是不同的 Vercel 專案，使用不同的 API key。
- **永久路徑** `Y:\permanent-projects\hermes-portal` = `/home/hoonsoropenclaw/permanent-projects/hermes-portal`（跟 Vercel 專案名 `hermes-portal` 一致、但跟 status site 那邊的「永久路徑叫 hermes-status-site 但 Vercel 叫 raphael-status-site」歷史錯誤不同）。

## 評價閉環（與 portal-judge-agent 配合）

上傳作品後，建議依序觸發評價鏈：

1. **上傳完成**（本技能的 Step 1-3）
2. **觸發 AI 預評**：delegate_task 載入 `portal-judge-agent` 技能對作品評分（評分只入 DB 或只回報告、由主 session 決定）
3. **通知使用者**：用「赫米斯自評 X/Y/Z、上 portal https://hermes-portal.vercel.app/work?id=<work_id> 看、要不要親自打分」訊息通知

**A/B 評審模式**（修改前 vs 修改後）：
- A 輪：先讓 subagent 評一次（基準分）
- 赫米斯主 session 根據 feedback 修改
- B 輪：subagent 重新評，**必須遵守 portal-judge-agent 的 A/B 比較協議**（URL 加 `?nocache=<ts>` 強制清 cache）

**已知限制**（與 portal-judge-agent 同步）：
- ❌ subagent browser cache 殘影 — 必須 URL 加 `?nocache=<timestamp>` 強制不讀 cache
- ❌ portal API 寫死 `reviewed_by: 'owner'` — 暫時用 feedback 內容區分 AI 評 vs 人評
- ❌ **AI 評審 ±0.3 浮動** — A 輪 7.3 → B 輪 7.7（Δ+0.4）**在浮動範圍內、不能當作修改有效的硬證據**。若要 A/B 比較可信：A、B 各評 3 次取平均 + URL 強制 nocache + 固定 tab 集合 + Δ ≥ 0.6 才宣稱有效。詳細見 portal-judge-agent 的「A/B 比較協議」跟 trial-and-error `hermes-internal.md` 的「LLM-as-judge AI 評審本身有 ±0.3 分浮動」條目。

## 相關技能

- `portal-judge-agent` — **姊妹技能**。本技能負責「赫米斯把作品推上 portal」，`portal-judge-agent` 負責「AI 評審評價作品」。兩者串起來形成完整閉環。

## 上傳時機

每當完成以下類型任務時，**必須**上傳：
- ✅ 網站部署完成
- ✅ 程式碼完成（GitHub repo 建立）
- ✅ 圖片/設計產出
- ✅ 簡報文件完成
- ✅ 資料分析結果
- ✅ 報告產出

## 上傳方式

### curl 直接上傳

```bash
AGENT_API_KEY=$(grep AGENT_API_KEY /home/hoonsoropenclaw/hermes-portal/.env.local | cut -d'=' -f2)
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

### Python

```python
import urllib.request, json

def upload_to_portal(title, description, tags, skill_used, links):
    # 讀取 API key
    env_path = '/home/hoonsoropenclaw/hermes-portal/.env.local'
    with open(env_path) as f:
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
        "method": "POST"
        )

        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
        ```

        ## 版本歷史

        - **v1.2.0** (2026-06-07): 修正目標網站 canonical URL（去 akqkd6vpj hash 過時 URL、加 Vercel Project Name 跟永久路徑說明）、已知限制加第 3 條「AI 評審 ±0.3 浮動」明確警示
        - **v1.1.0** (2026-06-07): 加入評價閉環 SOP（與 portal-judge-agent 串接）、A/B 評審模式、避坑警示

        ## 欄位規格

| 欄位 | 必填 | 說明 |
|------|------|------|
| `title` | ✅ | 作品標題，最多 200 字 |
| `description` | ❌ | 詳細描述、功能說明、技術棧 |
| `tags` | ❌ | 標籤陣列（語言、框架、工具） |
| `skill_used` | ❌ | 使用的技能名稱 |
| `links` | ❌ | 連結陣列 |

**links.type 可選值**: `weblink`, `github`, `figma`, `pdf`, `demo`, `other`

## 任務完成後的 SOP 步驟

1. **完成任務** → 產出實體成果
2. **立即上傳** → 用 `POST /api/works` 將作品上傳評價網站
3. **記錄 response** → 保存返回的 `id`，用於追蹤評價狀態
4. **口頭告知使用者** → 明確告知已完成上傳，並附上作品 URL
5. **長期追蹤** → 如果作品 > 7 天未獲得評價，主動提醒

## （可選）上傳後順手觸發 AI 預評

如果想讓赫米斯**自動拿到 AI 評審的預評分數**（不等使用者人工登入評），上傳完成後可 spawn 評價子代理：

- 載入 `~/.hermes/skills/portal-judge-agent/SKILL.md`
- 把剛剛上傳拿到的 `work_id` 傳給子代理
- 子代理會用 browser 實際看作品、打三維度分（設計感/實用性/直覺性）、寫 200-400 字 feedback
- **預設不 POST 進 Supabase**（portal 寫死 `reviewed_by: 'owner'` 無法區分 AI/人評，等 portal schema 修好才能自動入庫）
- 報告回給主 session 給使用者看，由使用者決定是否要親自登入 portal 確認 / 推翻

**觸發判斷**：不是每個作品都觸發 — 只在「這個作品值得赫米斯要求被評」時觸發（例如完整的網站/應用，**不是** 5 行 bash 腳本 / 1 頁 demo）。判斷標準是「使用者會想看嗎？」。

## 自動排程檢查

- **腳本路徑**: `/home/hoonsoropenclaw/scripts/portal_upload_check.sh`
- **Cron**: `0 9 * * *`（每日台灣時間 09:00）
- **用途**: 檢查所有作品是否有評價，記錄未獲評價的作品

### 支援檔案
- `references/eval-sync-script.md` — 評價同步腳本（sync_evaluations.py）說明與 401 問題排查
- `references/multiline-env-local.md` — 多行 `.env.local` 陷阱的詳細案例與修復記錄（從 portal-401-troubleshoot 吸收）

---

## ⚠️ 401 錯誤排查（SOP 摘要）

若 POST /api/works 返回 `401 Unauthorized`，**不要直接假設是 key 錯誤**，依序執行：

### Step 1：確認 Deployment 狀態
Vercel Dashboard → hermes-portal → Deployments。
- ❌ `Building` / `Error` → 等
- ✅ `Ready` → 進 Step 2

### Step 2：檢查 Vercel 環境變數
Vercel Dashboard → hermes-portal → Settings → Environment Variables。
- `AGENT_API_KEY` 必須存在且只有一行
- 值必須與本機 `/home/hoonsoropenclaw/hermes-portal/.env.local` 完全一致
- Scope 必須包含 `Production`（否則 `hermes-portal-akqkd6vpj-...vercel.app` 吃不到）

### Step 3：懷疑隱藏字元 → 手動輸入
OCR 顯示正確但仍 401 → 在 Vercel Dashboard → Edit `AGENT_API_KEY` → **手動親自打字輸入**（不要複製貼上）→ Save → 等 2-3 分鐘 → 再測試。

### Step 4：本地讀取 `.env.local` 的多行陷阱（最常見 cron 端 401 原因）

**症狀**：`grep AGENT_API_KEY .env.local` 能看到正確的值，但腳本送 API 仍 401。

**根因**：`.env.local` 內**多行同名變數**（Vercel CLI 部署、Supabase migration、手動追加都可能造成）。`grep | cut` 會匹配多行，`split("=", 1)[1]` 可能回傳錯的那行（空、過期值、另一個環境值）。

**驗證**：
```bash
grep -c "^AGENT_API_KEY=" /home/hoonsoropenclaw/hermes-portal/.env.local
# 若輸出 > 1 → 多行問題確認
```

**正確做法**（`awk` 取第一個匹配並 `exit`）：
```bash
API_KEY=$(awk -F= '/^AGENT_API_KEY=/{print $2; exit}' /home/hoonsoropenclaw/hermes-portal/.env.local)
```

**完整案例 + 4 種修復方案（awk / re.search / dotenv / 清重複行）+ 偵測訊號**見 `references/multiline-env-local.md`。

### Step 5：強制完整重建（Vercel build cache 損壞）

若環境變數看似都正確但仍 401，舊的 build 可能快取了錯誤的 `process.env`。**不要用 Dashboard 的 Redeploy 按鈕**：
```bash
cd /home/hoonsoropenclaw/hermes-portal
vercel --token <VERCEL_TOKEN> --prod --yes   # 強制 clean rebuild
```
部署後新 URL 自動 alias 到 `hermes-portal.vercel.app`，API 呼叫時用 canonical URL 即可。

### 驗證修復
```bash
curl -s -X POST "https://hermes-portal.vercel.app/api/works" \
  -H "Content-Type: application/json" \
  -H "x-agent-key: $AGENT_API_KEY" \
  -d '{"title":"verification test","description":"test","status":"published","tags":["test"],"skill_used":["test"]}' \
  -w "\nHTTP_CODE: %{http_code}"
# 預期：HTTP_CODE: 201 + {"data":{"id":...}}
```