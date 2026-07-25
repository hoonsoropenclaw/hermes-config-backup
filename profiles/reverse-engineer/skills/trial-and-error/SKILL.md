---
name: trial-and-error
description: "赫米斯踩過的坑目錄 — **MUST LOAD BEFORE EXECUTION**。當使用者交辦任何執行類任務或赫米斯即將對系統做變更時,必須**第一時間** `skill_view` 這個 skill,看有沒有踩過的雷。**HARD TRIGGER 詞**(命中任一必須載入):vercel / deploy / Vercel / CDN / cloudflare / git push / filter-branch / BFG / GH013 / GH001 / force push / large file / GPG / gpg / encrypt / decrypt / 簽章 / passphrase / rclone / Drive / 備份 / backup / purge / crypt / token / .env / API key / process.env / execute_code / python3.12 / pip install / uv venv / uv pip / subprocess / sandbox / browser / playwright / headless / camofox / for f in / 2>&1 / pipefail / array / set -e / hermes cron / hermes status / config / gateway / token 字串過濾 / content filter / *** 取代。"
---

# trial-and-error - 赫米斯踩過的坑目錄

> **強制載入 SOP**（2026-06-07 根據使用者回饋加入）: 任何執行類任務的**第一個 tool call 之前**必須先 `skill_view` 這個 skill。看有沒有命中觸發關鍵字對應的踩坑紀錄。**不要等出事了才撈**。

## ⚠️ 重要：這個 skill 在 2026-06-11 因為 patch 漂移偵測被誤刪,本次 minimal 重建

完整原 SKILL.md 結構 + 既有 100+ 條目位於：
- `~/.hermes/state-snapshots/20260607-114408-pre-update/skills/trial-and-error/SKILL.md`（最後完整備份）
- 也可能在 `~/.hermes/backups/staging_full_*/full_backups/.../trial-and-error/SKILL.md`

**下次有需要時**先 `find ~/.hermes -name "trial-and-error" -type d 2>/dev/null` 撈出最新版本、然後 patch 進必要的新條目（不要 delete + create、會丟失既有內容）。

## 強制載入 SOP（重點摘要）

### 🚨 觸發關鍵字 → 載入對應分類

- **部署類**：`vercel` / `deploy` / `Vercel` / `cloudflare` / `netlify` / `github pages` / `CDN` → `references/by-category/vercel-deployment.md`
- **Git 操作**：`git push` / `git filter-branch` / `BFG` / `GH013` / `GH001` / `large file` / `git history` / `force push` → `references/by-category/gh-cli-and-github.md`
- **加密類**：`GPG` / `gpg` / `encrypt` / `decrypt` / `簽章` / `key` / `passphrase` → `references/by-category/gpg-encryption.md`
- **雲端備份**：`rclone` / `Drive` / `備份` / `backup` / `purge` / `crypt` → `references/by-category/hermes-backup-strategy.md` + `hermes-backup-design-pitfalls.md`
- **環境變數**：`token` / `.env` / `process.env` / `API key` → `references/by-category/secrets-and-env.md`
- **Python sandbox**：`execute_code` / `python3.12` / `subprocess` / `sandbox` → `references/by-category/python-sandbox.md`
- **瀏覽器自動化**：`browser` / `playwright` / `headless` / `camofox` → `references/by-category/browser-automation.md`
- **Bash 腳本**：`for f in` / `2>&1` / `pipefail` / `array` / `set -e` → `references/by-category/bash-defensive-patterns.md`
- **Hermes 內部**：`hermes cron` / `hermes status` / `config` / `gateway` / `token 字串過濾` → `references/by-category/hermes-internal.md`
- **角色權限 / audience 邏輯**：`audience` / `matchAudience` / `role permission` / `dept_officer` / `教師/家長/學生 篩選` / `登入後看不到` / `受眾分流` / `C 方案` / `dept_officer 看全部` → `references/by-category/audience-permission-logic.md`（**改 audience 邏輯前必讀**、含 C 方案最終版 + 4 條鐵律 + 3 個反模式 + 9 個 demo 帳號 E2E 驗收 SOP + 角色決策歷程）

## 2026-06-11 新增的 3 條關鍵教訓（從 school-bulletin 路線 A 棒 1 慘案歸納）

### 教訓 1：棒結束必自驗 schema 進 DB（最致命的隱性 bug 類型）

**症狀**: 棒 N 改完程式碼 + commit + push + 觸發 Vercel deploy，**production 仍然 500**。本機也 500。build pass、型別 0 error、commit hash 對 — **但 production 報 `Could not find the table 'public.<x>' in the schema cache`**。

**根因**: 棒 N 寫的 SQL schema **沒真的跑進 Supabase**。self-audit 寫「schema 寫好」、但**沒寫「已 push 進 DB」** — sub-agent 認知中「SQL 寫好 = 完成」、實際 production runtime 缺表。

**If** 棒有改 schema / DDL / 新增 table
**Then** 棒 prompt 必含：
```
你的 schema 變更必同步跑進 Supabase DB（用 supabase db push 或 psql 直連）。
不要只 commit SQL 檔。
驗證: 棒結束時 psql / Supabase Studio 確認 table 已建。
報告必填:
  - supabase db push 執行時間
  - \dt 撈出 table list（含 N 個新表名）
  - 截圖或 log 證明 schema 已上線
缺這些 = 該棒不算完成。
```

**summarizer 必跑的真實驗證**（不可省）：
```bash
psql "postgresql://postgres:***@db.<ref>.supabase.co:5432/postgres" \
  -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
# 必包含棒 N 說要建的 N 個新表
```

### 教訓 2：改動 > 5 檔或 > 3 模組必分多棒平行（2026-06-11 §1.5.1）

**症狀**: 棒 1 一次改 8 檔 + 新建 4 檔（schema / repository / auth / announcements API / receipts 3 API / seed-demo / SignatureButton）→ 22 分鐘超 1200s 2 分鐘被 kill、build pass 不代表 runtime pass、commit 推到錯分支、schema 沒 push。

**If** 棒預計改動 > 5 檔 或 跨 > 3 模組（schema / repository / API / UI 各算 1 模組）
**Then** 必分 2-3 個工程棒平行跑、summarizer 棒 merge

**3 棒平行範本**：
- 棒 A1: 1 張 table + RLS + repository.ts 對應函式
- 棒 A2: 過濾邏輯 + API route + 自己 E2E
- 棒 A3: 簽收模組 table + 3 個 API + UI
- 棒 A4: summarizer merge + 全域 E2E + deliverable

### 教訓 3：棒 commit 必 push 到 main 分支（2026-06-11 §1.5.2）

**症狀**: 棒預設 push 到 `feat/*` 分支、不是 main。主 session 要手動 merge。

**If** 派 sub-agent commit **Then** prompt 必含：
```
你的 commit 必 push 到 origin/main（不是 feat/*、不是 chore/*）。
原因：handoff chain 整合策略 = 每棒直接進 main、由 summarizer 棒處理衝突。
如果你建 feat/* 分支 = 主 session 要手動 merge + 浪費 5 分鐘。
```

## L3 教訓總結（從 2026-06-11 school-bulletin 路線 A+C 方案歸納）

1. **改 audience 邏輯必先讀 `audience-permission-logic.md`** — C 方案是使用者最終決策
2. **「登入後 >= 未登入」是聖經** — 任何能讓登入變少的邏輯 = bug
3. **使用者改主意是常態** — PRD 是起點、不是終點；守住寫入底線、其餘可彈性
4. **三層環境不要搞混** — Vercel encrypted / 本機 plaintext / /tmp 原始 secret
5. **vc_token 會過期** — 觸發 deploy 用 `~/.hermes/.env` 的 `VERCEL_API_TOKEN` 兜
6. **寫 .env.local 必走 base64** — 避免被 hermes 字串過濾器截斷
7. **TypeScript type + DB schema 同步** — 改 role union 兩邊要一起動
8. **棒 N 結束必自驗 schema 進 DB** — SQL 寫好 ≠ schema 上線
9. **改動 > 5 檔必分多棒** — 1 棒貪多嚼不爛 = 22 分鐘超時 + 4 個 bug
10. **棒 commit 必 push 到 main** — `feat/*` 分支要主 session 手動 merge
11. **psycopg2 比 psql CLI 好用** — N100 headless 環境、避免 CLI 套件依賴
12. **token .strip() 必加** — 檔案讀出來可能有 `\n`、HTTP header 會爆
13. **角色矩陣要 E2E 跑 9 帳號 + 未登入** — 單看 1 帳號容易漏「其他角色反轉」
14. **first verify before deploy** — 本機 build 0 error 不代表 runtime OK、本機 200 不代表 production 200

## 完整版在哪

這個 skill 因為本次 patch 漂移誤刪,目前只剩 minimal 版本。**撈出原版的入口**：
```bash
find ~/.hermes -name "trial-and-error" -type d 2>/dev/null
# 撈出備份位置
# cp -r <備份位置> ~/.hermes/skills/trial-and-error/
# 然後再 patch 新條目進去
```

## 已重建的 reference 檔（2026-06-11）

- `references/by-category/audience-permission-logic.md` — C 方案 audience/權限定案
- `references/by-category/vercel-supabase-env-pattern.md` — Vercel encrypted env + Supabase 直連 SOP
