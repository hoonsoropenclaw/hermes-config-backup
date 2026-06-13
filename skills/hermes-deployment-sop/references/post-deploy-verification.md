---
title: deployment-verification-sop (demoted to reference)
source_skill: deployment-verification-sop (archived 2026-06-13)
date_consolidated: "2026-06-13"
---

# 部署驗證 SOP (Deployment Verification SOP)

> 任何對外有副作用的部署/推送/啟動,完成後**必須**走這個 SOP,才能回報「完成」。
> 2026-06-06 從 dashboard 部署慘案（user 看到 `ERR_NAME_NOT_RESOLVED`）建立。

## 觸發條件（任一符合即觸發）

- 跑 `vercel --prod` / `vercel deploy` / netlify deploy
- `gh repo create` / `git push` 到 public/private remote
- 設了 cron job 並標記為 active
- 註冊了 webhook / API key / 第三方服務帳號
- 改了 `~/.hermes/config.yaml` / `.env` 並重啟 gateway
- 使用者說「部署」「推送」「上線」「apply」「activate」「讓它跑」「先驗證後啟動」「確認可以打開」

**自我檢查**: 這次操作會不會讓使用者在「他自己的環境」看到東西？（是 → 走 SOP；否 → 不用）

## 核心原則（背下來）

1. **「我能跑」≠「使用者能跑」**
   - 我從 N100 curl 200 / git push 成功 / vercel 顯示 Ready,**不代表**使用者從他家/公司瀏覽器能打開
   - 原因: DNS propagation、地理位置、使用者的 DNS resolver cache、ISP 路由

2. **「單管道驗證」≠「多管道驗證」**
   - 一個 curl 200 不夠,要做多 DNS 解析 + 外部節點 + headless browser 視覺確認
   - 至少 3 個獨立驗證點全部通過才能回報

3. **「自報」≠「驗證」**
   - Vercel CLI 顯示 `Ready`、git push 顯示 `To github.com`、`vercel projects ls` 顯示專案 — 這些是**系統自報**,不是**我親自驗證**
   - 必須用 **獨立工具**（curl / dig / browser）重新確認,不能只信 CLI 輸出

4. **「部署 URL」≠「給使用者的 URL」**
   - 隨機 hash URL（`dashboard-seven-lac-35.vercel.app`）跟 alias URL 在新部署後 5-10 分鐘內可能 401 / 還沒 propagation
   - **唯一穩定的 URL 是「主要 domain」**（`xxx.vercel.app` 形式,指向專案永久 alias）
   - 給使用者的永遠是「主要 domain」,不是當次部署的隨機 hash URL

## 標準 4 步驗證 SOP

任何對外部署完成後,跑這 4 步,**全部通過**才回報使用者。

### Step 1 — 主要 domain HTTP 200

```bash
# 給 Vercel 範例（Netlify / Cloudflare Pages / 其他平台對應改 domain）
curl -s -o /dev/null -w "HTTP %{http_code}, time %{time_total}s, size %{size_download}B\n" \
  https://<project-name>.vercel.app
# 預期: HTTP 200, size > 0
```

### Step 2 — 多 DNS 解析（模擬使用者可能用的 DNS）

```bash
for dns in 1.1.1.1 8.8.8.8 9.9.9.9; do
  ip=$(dig +short @${dns} <project-name>.vercel.app A 2>/dev/null | head -1)
  echo "  $dns: $ip"
done
# 預期: 3 個都解析得到 IP（不一定相同,Vercel 用 anycast）
```

### Step 3 — 平台 API 確認「真的進 production」

```bash
# Vercel 範例
curl -H "Authorization: Bearer $VERCEL_API_TOKEN" \
  "https://api.vercel.com/v9/projects/<project-name>" | \
  jq '.targets.production | {alias, aliasAssigned, readyState}'

# 預期: readyState="READY", aliasAssigned 是 timestamp（不是 null）
# 若只有 READY 沒 PROMOTED → 還沒進 production,要等
```

### Step 4 — Headless browser 視覺確認

不是只有 200 / DOM 對,還要：
- 用 `browser_navigate` 開啟 production URL
- 跑 `browser_console` 確認沒有 JS error（要 `total_errors: 0`）
- 跑 `browser_console(expression="...")` 抓關鍵 DOM 元素,確認 JS 跑得起來（例如 SVG 是否真的 render、React 是否真的 hydrate）

**只信「截圖 + console 沒錯 + DOM 元素存在」三項全部。**

## 回報給使用者的格式

```markdown
### 完成
- ✅ <做了什麼>

### 給你的 URL
**主網址**：https://<project>.vercel.app
（不是 hash URL,是永久 alias,直接加書籤可用）

### 我自己驗證過
| 項目 | 結果 |
|------|------|
| 主要 domain HTTP 200 | ✅ |
| 多 DNS 解析 | ✅ 1.1.1.1 / 8.8.8.8 / 9.9.9.9 都查到 |
| Vercel readyState | ✅ PROMOTED |
| Headless browser 視覺 | ✅ 截圖 + console 無錯 |

### ⚠️ 如果你打不開
- 試 Chrome 無痕 `Ctrl+Shift+N`
- 或改電腦 DNS 為 `1.1.1.1`
- 等 5-30 分鐘（DNS 同步全球需要時間）
```

## 預防清單

部署前問自己：
- [ ] 我清楚使用者在哪裡（家裡 / 公司 / 出差）？可能用什麼 DNS？
- [ ] 我有 2 個以上獨立的驗證管道（curl + dig + browser）？
- [ ] 我會給「主要 domain」而不是「當次部署 hash URL」？
- [ ] 我有等 5 分鐘讓 DNS propagation 穩定才回報？

## If→Then 速查

- **If** 部署 Vercel 後我從 N100 curl 200 **Then** 還沒完,要走 4 步 SOP 才能回報「使用者可用」
- **If** 使用者回報 URL 打不開（`ERR_NAME_NOT_RESOLVED` 或 401）**Then** 第一個懷疑點是 DNS propagation,**不是**部署失敗,告知等 5-30 分鐘或用無痕模式
- **If** 給使用者 Vercel URL **Then** 永遠給「主要 domain」(`<project>.vercel.app`),不是隨機 hash URL
- **If** 看到 CLI 自報「成功」**Then** 還是要用獨立工具（curl/dig/browser）親自驗證,**不信** CLI 自我報告
- **If** 改了使用者會依賴的東西（部署、cron、config、API key）**Then** 走「先驗證後啟動」SOP,**不要**直接回報「完成」

## 與其他 skill 的關係

- 技術細節（DNS propagation 機制、alias 401 常態、gh repo create --source 限制）見 `trial-and-error/references/by-category/vercel-deployment.md` 跟 `gh-cli-and-github.md`
- 本 skill 負責「**流程 SOP**」,不重複技術細節
- 改 deployment 流程時,先看本 skill 的 SOP,**技術細節再去翻** trial-and-error

## 變更記錄

- 2026-06-06 v1.0.0 — 從 dashboard 部署慘案（user 截圖 `ERR_NAME_NOT_RESOLVED`）建立。4 步 SOP + 回報格式 + 預防清單
