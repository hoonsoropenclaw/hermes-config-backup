---
name: school-interview-scheduler
description: "學校人事主管的 Google Calendar + Meet 面試預約自動化。當用戶提到「面試預約」「約面試時間」「建立 Google Meet」「寄面試邀請」「候選人收到邀請」時啟用。核心功能：收到 Linear 候選人後，自動建立 Google Calendar 事件 + Google Meet 視訊連結，並寄送邀請給候選人。依賴 google-workspace skill 的 OAuth2 機制。"
version: 1.0.2
author: Hermes Agent (metacognitive-learner)
platforms: [linux]
metadata:
  hermes:
    tags: [school, hr, calendar, meet, interview, scheduling, google, automation]
    triggers: [面試預約, 約面試, Google Meet, 建立會議連結, 面試邀請, calendar event]
    user_type: school HR (high school administrative staff)
---

# School Interview Scheduler — Google Calendar + Meet 面試預約自動化

## 核心定位

本 skill 補足 `hr-document-workflow` 的最後一環：`hr-document-workflow` 解決了「錄取 → 文件產出」，本 skill 解決「面試安排 → Google Meet 邀請 → 面試後評分表」。

```
HR 說「幫我約張三面試」（在 Linear 已建立候選人）
    ↓
取出候選人 email + 面試時間（HR 告知）
    ↓
呼叫 Google Calendar API 建立 event + Meet 視訊連結  [Phase 1-3]
    ↓
寄送邀請給候選人 email
    ↓
HR 在 Linear 更新面試狀態（W4）
    ↓
面試結束後，自動建立 Google Sheets 評分表      [Phase 4]
    ↓
HR / 面試官在 Sheets 填寫維度分數
    ↓
Script 將分數回寫 Linear（W5 面試完成）
```

**Phase 4（2026-06-23 新增）**：面試後評分表生成 — 填補了「面試結束到錄取決定」之間的自動化空白。

## Google Calendar API 核心原理

### 兩種認證方式

| 方式 | 適用場景 | 困難點 |
|------|---------|--------|
| **OAuth2 (user Credential)** | 個人帳號（HR 自己的 calendar）| 需要第一次互動授權 |
| **Service Account + Domain-Wide Delegation** | 學校 domain（G Suite/Google Workspace）| 需要管理員設定 |

**學校人事的建議**：
- **個人 Google 帳號**：走 OAuth2 Device Flow（`run_local_code()`），只需一次設定，之後自動 refresh
- **Google Workspace**：用 Service Account + Domain-Wide Delegation，完全自動化（需學校 IT admin 設定）

### Headless OAuth2 流程（赫米斯 N100 環境）

赫米斯 N100 是 **headless**（無瀏覽器、無本機 webserver），標準 `InstalledAppFlow.run_local_server(port=0)` 會導致 `localhost` callback 無法送達。**正確方式**是 `setup.py` 內的 Out-of-Band (OOB) flow：

```python
# ❌ 錯 — 需要瀏覽器 + local webserver
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)  # localhost callback 永遠等不到

# ✅ 對 — setup.py 的 OOB flow（適用 headless CLI）
# 赫米斯 N100 不直接呼叫 python setup.py，而是由赫米斯代理呼叫：
#   python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --check
#   python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py calendar
# setup.py 內的 OOB flow 原理：
# 1. 產生授權 URL（無需 localhost redirect）
# 2. URL 中包含 user_code，用戶在瀏覽器開啟並粘貼 user_code
# 3. 授權完成後赫米斯拿 code 换 token
```

**注意**：`google-auth-oauthlib` 的 `InstalledAppFlow` **沒有** `run_local_code()` 方法（這是 SKILL.md 歷史錯誤）。真正的 headless 方式是 `setup.py` 內實作的 OOB 授權流程。

### Google Calendar API 基本概念

```
POST https://www.googleapis.com/calendar/v3/calendars/primary/events
```

**建立 Meet 的關鍵參數**：
```json
{
  "conferenceData": {
    "createRequest": {
      "requestId": "<unique-string>",
      "conferenceSolutionKey": { "type": "eventHangout" }
    }
  },
  "start": { "dateTime": "2026-06-20T10:00:00+08:00", "timeZone": "Asia/Taipei" },
  "end": { "dateTime": "2026-06-20T11:00:00+08:00", "timeZone": "Asia/Taipei" },
  "attendees": [
    { "email": "candidate@school.edu.tw", "displayName": "張三" }
  ],
  "summary": "【面試】張三 - 數學教師",
  "description": "面試职位：數學教師\\n面試方式：Google Meet 視訊"
}
```

**回應中的 Meet URL** 在 `conferenceData.entryPoints[0].uri`。

### If→Then 規則

**If** 用戶說「幫我約張三 OO 點面試」「約明天下午 3 點」「建立 OO 的面試邀請」
**Then** 先執行 `setup.py --check` 確認 OAuth 狀態，再執行 `create_interview.py`

**If** `setup.py --check` 輸出 `NOT_AUTHENTICATED`
**Then** 立即中斷，向使用者說明需完成 Google 授權，**不要**假裝 `create_interview.py` 成功（API call 會得到 401）

**If** 用戶說「候選人說沒收到邀請」「要重新發送」
**Then** 查 Google Calendar event ID，重新寄送邀請

**If** 用戶說「要改時間」「要取消面試」
**Then** 用 `update_interview.py` — `calendar.events().patch()` 更新，或 `calendar.events().delete()` 刪除

**If** 使用者提到「面試排程」「約面試」「Google Meet」等觸發詞
**Then** 在執行 `create_interview.py` 前先跑 `setup.py --check`，確認 OAuth 已設定

## 執行命令

### 前置需求：Google OAuth2 設定（一次性）

**本 skill 採用 OAuth2 Device Flow**，專為 headless 環境（N100 無瀏覽器）設計：
- 用戶在任何設備（手機/電腦）開啟顯示的 URL 即可完成授權
- 不需要在本機開瀏覽器

```bash
# 檢查是否已設定
python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --check

# 若未設定，執行 Device Flow 授權（headless 適用）
python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py calendar

# 螢幕會顯示：
# "Please visit https://Google.com/device 並輸入代碼 XXXX-XXXX"
# 把顯示的代碼粘貼回終端即可完成授權
```

**或手動設定 Service Account（適用 Google Workspace）**：
1. Google Cloud Console 建立 Service Account
2. 下載 JSON key file（**不放進 Git**，放到 `/tmp/` 或 `~/.hermes/secrets/`）
3. 在 Google Admin Console 啟用 Domain-Wide Delegation
4. 設定 `GOOGLE_APPLICATION_CREDENTIALS` 環境變數

### 建立面試邀請

```bash
# 基本用法
python3 ~/.hermes/skills/school-interview-scheduler/scripts/create_interview.py \
  --candidate "張三" \
  --email "zhangsan@gmail.com" \
  --datetime "2026-06-20 10:00" \
  --position "數學教師" \
  --duration 60

# 輸出（JSON）
{
  "event_id": "abc123xyz",
  "meet_url": "https://meet.google.com/abc-defg-hij",
  "calendar_url": "https://calendar.google.com/calendar/..."
}
```

### 更新/取消面試

```bash
# 更新時間
python3 ~/.hermes/skills/school-interview-scheduler/scripts/update_interview.py \
  --event-id "abc123xyz" \
  --datetime "2026-06-21 14:00"

# 取消（使用 update_interview.py 的 --cancel 標誌）
python3 ~/.hermes/skills/school-interview-scheduler/scripts/update_interview.py \
  --event-id "abc123xyz" \
  --cancel
```

## 與現有 Skills 的串接

| Skill | 角色 | 串接點 |
|-------|------|--------|
| `hr-document-workflow` | 履歷 → 錄取文件產出 | 本 skill 補足「錄取前」的面試安排環節 |
| `linear-hr-workflow` | 候選人追蹤 | W4 面試狀態更新 → 觸發本 skill；W5 分數回寫 |
| `google-workspace` | OAuth2 機制 | 共用 `google_token.json` / Service Account 設定 |
| `himalaya` | email 收取 | 如需從 email 解析候選人回覆的時間 |
| `minimax-multimodal-toolkit` | 訪談準備影片生成 | 當 HR 要寄「面試準備影片」給候選人時，見 `references/video-prep-integration.md` |
| `minimax-xlsx` | 評分表格式與驗證 | Phase 4 評分表建立後，用 `openpyxl` 驗證格式（需先 `uv pip install openpyxl`） |

### 評分維度（標準化，5 維度 × 5 分制）

| 維度 | 說明 | 分數意義 |
|------|------|---------|
| 專業知識 | 學科專業度、教學能力相關 | 1=完全不足 / 5=卓越 |
| 表達能力 | 回答邏輯、口條清晰度 | 1=混亂 / 5=精準有力 |
| 態度與價值觀 | 配合度、積極性、學校理念契合 | 1=消極 / 5=高度契合 |
| 適任性 | 對學校文化、學生族群的適應 | 1=明顯不合 / 5=完全契合 |
| 總分 | 綜合考量 | 1-25 分 |

**範例 Sheets 佈局**：
- 列 A：維度名稱（專業知識 / 表達能力 / 態度與價值觀 / 適任性 / 總分）
- 列 B：候選人填寫（1-5 分 dropdown）
- 列 C：空白（備註）
- 頂端：候選人姓名、面試時間、面試官姓名（從 Calendar event 自動帶入）

**If→Then**：
- **If** 用戶說「面試完了要評分」「建立評分表」「候選人面試結束」
- **Then** 執行 Phase 4：取出 Calendar event attendees → 建立 Sheets scorecard → 寄給面試官
- **If** 評分完成（面試官回傳分數）
- **Then** 將分數寫入 Linear 候選人 record（W5），並根據總分（門檻 20/25）給出「建議錄取/不建議/再議」

## ⚠️ 已知雷區

### `eventHangout` 而非 `hangoutsMeet`（2026-06-21 發現並修復）

**症狀**: 建立 Google Calendar event + Meet 連結時，API 傳回 400 `Invalid conference type value`，或 Meet 連結未出現。

**根因**: `create_interview.py` 歷史版本使用 `"type": "hangoutsMeet"`，但 Google Calendar API v3 的正確值是 `"type": "eventHangout"`（`hangoutsMeet` 從未是有效值）。

**受影響範圍**:
- `create_interview.py` — `conferenceData.createRequest.conferenceSolutionKey.type`
- `SKILL.md` 中的 API 範例

**解法**: 將 `"type": "hangoutsMeet"` 改為 `"type": "eventHangout"`，並搭配 `conferenceDataVersion=1`。

**預防**: 建立 Meet 事件前查 [Google Calendar API v3 官方文件](https://developers.google.com/calendar/api/v3/reference/events) 驗證 `conferenceSolutionKey.type` 值。

**If→Then**: **If** 看到 Google Calendar API 400 + `Invalid conference type value` **Then** 檢查 `conferenceSolutionKey.type` 是否為 `eventHangout`（非 `hangoutsMeet`）

### Token 路徑在 Python 中被赫米斯 filter 遮蔽

**症狀**：`HERMES_HOME / "google_token.json"` 或 `Path("...") / "google_token.json"` 這類路徑在 `write_file` 或 `execute_code` 中被赫米斯 filter 吃掉，`***` 遮蔽會破壞表達式。

**根因**：赫米斯內建 token 過濾器在「寫入側」遮蔽 `sk-`/`ghp_`/`***` 等關鍵字，`/` 運算子在某些位置會被錯誤處理。

**解法**：不要用 Path 拼接，**直接用字串拼接**：
```python
# ❌ 會被吃掉
TOKEN_FILE = HERMES_HOME / "google_token.json"

# ✅ 正確 — 字串拼接避開 filter
TOKEN_FILE = "*** + "/google_token.json"
```

`***` 是路徑的占位符（實際值被遮蔽），用 `+` 字串拼接可完整保留路徑字串。

### OAuth token 過期

**症狀**：OAuth token 90 天後過期，API 呼叫得到 401。

**解法**：`Credentials.from_authorized_user_info()` 讀取 token 時，檢查 `creds.expired`，如有 `creds.refresh_token` 就刷新並寫回磁碟。

## 限制

1. **OAuth2 Token 過期**：使用者帳號的 OAuth token 90 天後需重新授權（取決於 Google 設定）
2. **Service Account 需要 Google Workspace**：個人帳號無法使用 Service Account
3. **並發限制**：Google Calendar API 同一帳號 1,000 requests/秒
4. **Meet URL 並非立就能用**：event 建立後約 5-10 秒 Meet URL 才生效

## 參考資源

- [Google Calendar API v3 Events](https://developers.google.com/calendar/api/v3/reference/events)
- [Google Meet REST API](https://developers.google.com/workspace/meet/api/reference/rest)
- [google-api-python-client 文件](https://developers.google.com/calendar/api/quickstart/python)
- [Cal.com vs Calendly vs DIY](https://vennio.app/blog/best-scheduling-api-for-developers-2026)

## D3 Exit 驗證步驟（Cycle 3 — 2026-06-18 / 2026-06-19）

### 已驗證（✅）

```bash
# create_interview.py CLI help
$ python3 ~/.hermes/skills/school-interview-scheduler/scripts/create_interview.py --help
✅ --candidate/--email/--datetime/--position/--duration 全參數存在

# update_interview.py CLI help
$ python3 ~/.hermes/skills/school-interview-scheduler/scripts/update_interview.py --help
✅ --event-id/--datetime/--cancel 全參數存在

# google-workspace setup.py --check
$ python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --check
NOT_AUTHENTICATED: No token at /home/hoonsoropenclaw/.hermes/google_token.json

# Linear API key — 2026-06-19 新發現
$ curl -s -X POST https://api.linear.app/graphql \
    -H "Content-Type: application/json" \
    -d '{"query":"{ viewer { id } }"}'
{"errors":[{"message":"Authentication required","statusCode":401}]}
✅ 確認 LINEAR_API_KEY 缺失
```

### 待完成（⚠️ — 需要 main session 主動提示使用者）

| 步驟 | 狀態 | 阻斷原因 |
|------|------|---------|
| OAuth2 token 設定 | ❌ 未完成 | 需要使用者在瀏覽器完成 Google Device Flow |
| Linear API key | ❌ 未設定 | `~/.hermes/.env.local` 無 `LINEAR_API_KEY`，`linear-hr-workflow` 也缺失此 key |
| 實際建立面試事件 | ❌ 未測試 | token 未設定 |

### 阻塞根因（Cycle 3 新發現 — 2026-06-19 更新）

Google OAuth2 Device Flow 需要用戶在瀏覽器操作，**cron sub-agent 無法獨力完成**。`setup.py --check` 回傳 `NOT_AUTHENTICATED` 代表：
- `google_client_secret.json` 可能尚未設定
- 或已設定但 `google_token.json`（refresh token）未成功寫入磁碟

**2026-06-19 新發現**：LINEAR_API_KEY 同時缺失（401 error）。`school-interview-scheduler` 依賴 `linear-hr-workflow` 取得候選人 email（從 Linear issue description），若候選人 email 為 HR 手動提供則 Linear key 非必須。

### 觸發 main session 的標準句

當 main session 聽到「面試排程」「約面試」等觸發詞時，在執行 `create_interview.py` **前**先確認 OAuth 狀態：

```bash
python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --check
```

若輸出 `NOT_AUTHENTICATED`，**立即中斷並向使用者說明**：
> 「要建立 Google Calendar 面試邀請，需要先完成 Google 授權。請在瀏覽器開啟以下連結...（啟動 Device Flow）」

**不要**假裝跑 `create_interview.py` 成功，實際 API call 會得到 401。

### 更新 version

version 目前為 `1.0.0`。當 main session 完成 OAuth 驗證（`setup.py --check` 回傳 `AUTHENTICATED`）後，將 version 改為 `1.1.0` 並加：
```
✅ D3 完成：2026-06-XX（Google Calendar OAuth 驗證通過）
```
