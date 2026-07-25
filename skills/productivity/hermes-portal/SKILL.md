---
name: hermes-portal
description: |
  Hermes Portal 評價網站完整工作流 umbrella — 任務完成後上傳作品、對作品做 AI 預評、處理 401 / 多行 .env.local / cron silent failure 等常見雷區。
  **Class-level skill** — 涵蓋兩個面向：(1) 上傳端（`portal-auto-upload` 全部 SOP）、(2) 評審端（`portal-judge-agent` 全部 SOP）。
  **觸發**：任務完成、要上傳評價網站、要評價某個作品、A/B 比較、A→B 修改前/後評分。
  **必讀 SOP 入口**：canonical URL = `https://hermes-portal.vercel.app/`、Vercel Project ID `prj_uUsJw3x4NZCofkO1KKFT7viCNvLD`、API endpoint `/api/works` (POST) 與 `/api/evaluations/{work_id}` (POST)。
version: 1.0.0
author: Hermes Agent (curator consolidation 2026-07-04)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes-portal, 評價網站, 上傳, 評審, AI-judge, llm-as-judge, A-B-test, A-B-comparison, 自動上傳, Vercel]
    related_skills: [portal-judge-agent]
    triggers: [任務完成, 網站部署, 程式完成, 圖片產出, 簡報完成, 上傳 portal, 評價, AI 評審, A/B 比較, 修改前/後]
---

# Hermes Portal — 評價網站完整工作流 (Class-Level Umbrella)

## 何時使用

**任一符合即載入**：
- 任務完成（網站/程式/圖片/簡報/文件）→ 走「上傳端」
- 赫米斯派遣子代理評價作品 / 要 AI 預評 → 走「評審端」
- A→B 修改前/後比較評分 → 走「評審端 A/B 模式」
- `eval-sync` cron 失敗、`last_status: ok` 但從未實際上傳 → 走「常見雷區」

---

## 上傳端 — 任務完成自動上傳 SOP（原 `portal-auto-upload` 內容）

### 目標網站

| 項目 | 值 |
|------|-----|
| **Canonical URL** | `https://hermes-portal.vercel.app/` |
| API Endpoint | `POST https://hermes-portal.vercel.app/api/works` |
| Vercel Project ID | `prj_uUsJw3x4NZCofkO1KKFT7viCNvLD` |
| Project Name | `hermes-portal` |
| Auth Header | `X-Agent-Key` |

**⚠️ 注意**：
- **Canonical URL = `hermes-portal.vercel.app`**（舊 deployment hash URL `hermes-portal-akqkd6vpj-...vercel.app` 已過時、會 401 protected）。永遠用 canonical。
- hermes-portal（評價網站）≠ hermes-status-site（自身狀態網站）。兩個是不同的 Vercel 專案、使用不同的 API key。
- 永久路徑 `Y:\permanent-projects\hermes-portal` = `/home/hoonsoropenclaw/permanent-projects/hermes-portal`。

### 上傳時機（必上傳）

每當完成以下類型任務時，**必須**上傳：
- ✅ 網站部署完成
- ✅ 程式碼完成（GitHub repo 建立）
- ✅ 圖片/設計產出
- ✅ 簡報文件完成
- ✅ 資料分析結果
- ✅ 報告產出

### 上傳方式（curl 直接上傳）

```bash
AGENT_API_KEY=$(awk -F= '/^AGENT_API_KEY=/{print $2; exit}' /home/hoonsoropenclaw/permanent-projects/hermes-portal/.env.local)
curl -X POST https://hermes-portal.vercel.app/api/works \
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

### 欄位規格

| 欄位 | 必填 | 說明 |
|------|------|------|
| `title` | ✅ | 作品標題，最多 200 字 |
| `description` | ❌ | 詳細描述、功能說明、技術棧 |
| `tags` | ❌ | 標籤陣列（語言、框架、工具） |
| `skill_used` | ❌ | 使用的技能名稱 |
| `links` | ❌ | 連結陣列；`type` 可選 `weblink` / `github` / `figma` / `pdf` / `demo` / `other` |

### 上傳後 SOP

1. **完成任務** → 產出實體成果
2. **立即上傳** → 用 `POST /api/works`
3. **記錄 response** → 保存返回的 `id`
4. **口頭告知使用者** → 附上作品 URL `https://hermes-portal.vercel.app/work?id=<work_id>`
5. **長期追蹤** → 作品 > 7 天未獲評價時主動提醒

### 自動排程檢查

- **腳本**：`/home/hoonsoropenclaw/scripts/portal_upload_check.sh`
- **Cron**：`0 9 * * *`（每日台灣時間 09:00）
- **用途**：檢查所有作品是否有評價、記錄未獲評價的作品

---

## 評審端 — AI 評審子代理 SOP（原 `portal-judge-agent` 內容）

### 啟動前 SOP（主 session 必做）

**絕對不要在以下情境未確認就派 subagent 評估**：

1. **使用者還沒明確說「評一下」或「A→B 比較」** — 浪費 subagent + token
2. **評估對象還沒部署到 production** — 評 preview URL 沒有意義
3. **使用者對評估方式有疑慮** — 兩個 subagent 浮動 ±0.3、單次 A→B 比較不能下硬結論

**正確啟動流程**：
- 收到任務「幫我改 X 網站」
- 先改完、部署、curl 驗證
- **才問 user**：「要 A→B 比較嗎？」（不是自作主張派 subagent）
- 等 user 確認才 `delegate_task` 派 subagent 載入本 skill

**If** 使用者說「不用評分」「先這樣」「你判斷就好」**Then** 絕對不要派 subagent 評、只回報修改內容 + 部署驗證結果。

### 互動 tab 數量下限

- **單次評分**：至少互動 50% 的 tab。如果整站有 N 個 tab、至少 ⌈N/2⌉ 個
  - 11 tabs → 至少 6 個
  - 5 tabs → 至少 3 個
- **A/B 比較**：兩輪互動 tab 集合必須完全一致、都要 ≥50% 下限
- **互動定義**：點擊/切換 tab 載入內容、驗證 console 0 error、視覺確認非破版。**只看 tab 標題不算互動。**

### 評分標準（三維度 1-10）

| 維度 | 評估什麼 |
|------|---------|
| **設計感 `score_design`** | 視覺與美學：配色、字型、留白、層次 |
| **實用性 `score_practical`** | 功能與解決問題：edge case 處理、完成度 |
| **直覺性 `score_intuitive`** | 學習成本：是否一眼能懂、需不需要文件 |

**5-6 分**：中等、看起來「能看」/「能用」沒大毛病
**7-8 分**：良好、有小細節
**9-10 分**：頂級、有強烈風格 / 完整解決痛點 / 零學習成本

### 評價工作流（嚴格遵守）

#### Step 0：資產完整性檢查（必跑）

```bash
# 1. 主站 200
curl -sI <URL> | head -1

# 2. 所有引用的 css/js 都 200
grep -rE 'href="[^"]+"|src="[^"]+"' <work_html_or_description> \
  | grep -oE '"[^"]+\.(css|js)"' | tr -d '"' | sort -u \
  | while read f; do
      code=$(curl -s -o /dev/null -w "%{http_code}" "<URL>/$f")
      echo "<URL>/$f: HTTP $code"
    done

# 3. 所有 tab 都 200（如果是 tab-based 站）
for tab in <tab_list>; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "<URL>/tabs/$tab.html")
  echo "<URL>/tabs/$tab.html: HTTP $code"
done

# 4. cache-busting 抓主 HTML
curl -s "<URL>?cb=$(date +%s)" | grep -oE '<title>[^<]+</title>'
```

**如果有任何 curl 404**：立刻中斷評分、回報「資產完整性檢查失敗」、不要繼續評。

#### Step 0.5：清除快取

**URL 必加 cache buster**：`https://<work-url>?nocache=<UNIX_TIMESTAMP>`
**A/B 比較時**：兩輪 URL 的 `nocache` 值必須不同
**不依賴 subagent 自己清 cache**

#### Step 1-5：拿作品 → 看作品（必須瀏覽器互動）→ 打分（給理由）→ 寫 feedback → POST 評價 → 回報

**Step 5：POST 評價（注意：POST 不需 X-Agent-Key、GET /sync 才是 agent 用的）**

```bash
curl -X POST "https://hermes-portal.vercel.app/api/evaluations/{work_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "score_design": <int 1-10>,
    "score_practical": <int 1-10>,
    "score_intuitive": <int 1-10>,
    "feedback": "<200-400 字繁體中文回饋>"
  }'
```

- POST 端點會把 `reviewed_by` 自動寫成 `'owner'`（**這是 portal 已知 bug**，見 trial-and-error）
- 評價寫入後**自己 verify 一次**：再用 `GET /api/works/{work_id}` 看 evaluations 列表

#### Step 6：回報結構

```
=== 評價完成 ===
Work: <title> (id: <work_id>)
URL: <evaluated url>
評審: portal-judge-agent-v1

評分:
- 設計感 (score_design): X/10 — <一句話理由>
- 實用性 (score_practical): Y/10 — <一句話理由>
- 直覺性 (score_intuitive): Z/10 — <一句話理由>
- 平均: (X+Y+Z)/3

Feedback 重點:
- 優點: <1-2 點>
- 問題: <1-3 點>
- 建議: <1-2 點>

驗證:
- POST 狀態: <201 / 失敗>
- DB 確認: <有出現 / 沒出現>
- Console error 數: <N>
```

### A/B 比較協議（修改前 vs 修改後）

**強制格式**（Step 6 報告必含）：

```
=== A/B 評價結果 ===
                    A 輪 (<時間>)  |  B 輪 (<時間>)
設計感              <a>/10         |  <b>/10      (Δ ?)
實用性              <a>/10         |  <b>/10      (Δ ?)
直覺性              <a>/10         |  <b>/10      (Δ ?)
平均                <a>/10         |  <b>/10      (Δ ?)
Console error       <a>            |  <b>

=== 設計修改是否真的提升 ===
<yes / no / partial> — 解釋

=== 副作用 / 新問題 ===
<列出>

=== Console error 對比 ===
A 輪: <N> | B 輪: <N>  ✅ / ⚠️ / ❌
```

**A/B 評審必遵守的 5 條**：
1. 兩個 URL 的 `?nocache=<ts>` 必須不同
2. 互動 tab 數量兩輪要一致（A 看 4 個、B 也看 4 個）
3. 不能只評修改的 tab（要看整站）
4. 給分要有理由、不是憑感覺
5. **AI 評審 ±0.3 浮動 — Δ < 0.6 不能當作「修改有效」的硬證據**

可信分數區間範例：
- A 輪 7.3 → 區間 [7.0, 7.6]
- B 輪 7.7 → 區間 [7.4, 8.0]
- 有重疊 [7.4, 7.6] → 嚴格說不算顯著改善
- 若 A、B 區間完全分離（如 A [5.0, 5.3] vs B [7.0, 7.3]）才可下「有效」結論

### 評審公約

**AI 評審的限制（自覺）**：
- 我不是設計師也不是工程師 — 我看「看起來怎樣」和「用起來怎樣」
- 我沒有你的品味 — 我給 8 分可能你覺得 6 分
- **評分是「客觀基準線」不是「最終意見」** — 使用者的評分永遠優先

**會避開的事**：
- 不打政治/倫理分
- 不評作者意圖（只評成品）
- 不重複之前評過的維度
- 不打超過 95 字的分數後小數（避免偽精度）

---

## 常見雷區與限制

### 已知限制

- ❌ **AI 評審 ±0.3 浮動** — A 輪 7.3 → B 輪 7.7（Δ+0.4）在浮動範圍內、不能當作修改有效的硬證據
- ❌ **POST 需要真實 key、GET 200 不代表 POST 能成功** — `GET /api/works` 只驗格式（key 太短會被視為格式錯誤 → 400，但 mask 值 `***` 有時被視為有效格式 → 200）；`POST /api/works` 才真的需要正確 key
- ❌ **subagent browser cache 殘影** — 線上 css 404 但截圖還是深色風格（必加 `?nocache=<ts>`）
- ❌ **portal DB `reviewed_by: 'owner'` 寫死** — 評價者身份欄位不存在、AI 評 vs 人評無法區分（除非改 API）
- ❌ **Vercel `vercel ls` 舊 deployment 內容撈不到** — 必須 fallback 用 GitHub raw URL
- ❌ **subagent 跳過某些 tab 不報** — 互動下限 ≥50% 強制

### ⚠️ 401 錯誤排查 SOP（cron 端最常見）

若 POST /api/works 返回 `401 Unauthorized`，**不要直接假設是 key 錯誤**，依序執行：

**Step 1：確認 Deployment 狀態** — Vercel Dashboard → hermes-portal → Deployments → 必須 `Ready`
**Step 2：檢查 Vercel 環境變數** — Settings → Environment Variables；`AGENT_API_KEY` 必須存在、值必須與本機 `.env.local` 完全一致、Scope 必須包含 `Production`
**Step 3：手動親自打字輸入 key** — OCR 顯示正確但仍 401 → Edit `AGENT_API_KEY` → 手動打字輸入 → 等 2-3 分鐘
**Step 4：本地讀取 `.env.local` 的多行陷阱** — 改用 `awk -F= '/^AGENT_API_KEY=/{print $2; exit}'`，不要 `grep | cut`（多行同名變數陷阱，會讀到 mask 值）
**Step 5：強制完整重建（Vercel build cache 損壞）** — `vercel --token <TOKEN> --prod --yes`

### POST vs GET：401 Silent Failure Pattern（重要！）

**症狀**：cron `last_status: ok` 但從未實際上傳任何作品。

**根因鏈**：
```
1. .env.local 有多行 AGENT_API_KEY（含 mask 值）
2. grep | cut 讀到第一行 = mask 值（"***"）
3. cron script 用舊 deployment URL（已 401 protected）
4. GET /api/works 只驗格式 → "***" 被視為有效 → HTTP 200
5. POST /api/works 需要真實 key → "***" → HTTP 401
6. set -e + curl -s → 401 不阻斷 → script 看似成功（exit 0）
```

**完整案例 + 修復清單**：見 `references/post-vs-get-401-silent-failure.md`
**多行 .env.local 陷阱**：見 `references/multiline-env-local.md`
**eval-sync 腳本 401 排查**：見 `references/eval-sync-script.md`

### 評價閉環 SOP（與子代理串接）

上傳作品後，建議依序觸發評價鏈：
1. **上傳完成**（本 skill 的上傳端 SOP）
2. **觸發 AI 預評**：`delegate_task` 載入本 skill 對作品評分
3. **通知使用者**：「赫米斯自評 X/Y/Z、上 portal https://hermes-portal.vercel.app/work?id=<work_id> 看、要不要親自打分」

**觸發判斷**：不是每個作品都觸發 — 只在「這個作品值得赫米斯要求被評」時觸發（例如完整的網站/應用，**不是** 5 行 bash 腳本 / 1 頁 demo）。判斷標準是「使用者會想看嗎？」。

---

## 驗證修復

```bash
# 確認 key 不是 mask
KEY=$(awk -F= '/^AGENT_API_KEY=/{print $2; exit}' /home/hoonsoropenclaw/permanent-projects/hermes-portal/.env.local | tr -d ' ')
echo "KEY length: ${#KEY}"   # 預期 > 20

# 確認 GET 和 POST 狀態
curl -s -o /dev/null -w "GET: %{http_code}\n" -X GET "https://hermes-portal.vercel.app/api/works" -H "X-Agent-Key: $KEY"
curl -s -o /dev/null -w "POST: %{http_code}\n" -X POST "https://hermes-portal.vercel.app/api/works" \
  -H "X-Agent-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"title":"verification-test","description":"cron verify","status":"published","tags":["test"],"skill_used":["test"]}'
```

---

## 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-07-04 | curator 整合：`portal-auto-upload`（上傳端）+ `portal-judge-agent`（評審端）合併為一個 class-level umbrella skill。原本兩個 skill 歸檔。 |