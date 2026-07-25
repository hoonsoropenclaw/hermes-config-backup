# Vercel 部署流程與路徑陷阱

## 赫米斯狀態網站部署 SOP

### 兩個部署層次（容易混淆）

| 動作 | 命令 | 用途 |
|------|------|------|
| 更新 Git 倉庫 | `git add . && git commit -m "..." && git push origin main` | 讓 Vercel 能從 GitHub 建構 |
| 直接部署到 Vercel | `vercel --token $VERCEL_API_TOKEN --yes --prod --name raphael-status-site` | 繞過 Git，直接上傳本地檔案 |

**重要教訓**：直接用 `vercel --prod` 部署會覆蓋 Vercel 專案（`prj_6FcNdvnHwPoXdkjr5csknUVJ5bUX`），不管 Git 倉庫是哪個。只要 `--name raphael-status-site` 相同，就會更新同一個 production URL。

### 路徑陷阱（已發生的錯誤）

**問題**：`skill_usage_stats.py` 中的 `SKILLS_TAB` 路徑指向錯誤的網站
```
錯誤：SKILLS_TAB = Path.home() / ".openclaw/workspace/raphael-status-site/tabs/skills.html"
正確：SKILLS_TAB = Path.home() / "hermes-status-site" / "tabs" / "skills.html"
```

**影響**：更新了拉斐爾的 `skills.html`，卻部署到赫米斯的 Vercel 專案，造成內容錯乱。

**預防原則**：
- 赫米斯網站路徑：`/home/hoonsoropenclaw/hermes-status-site/`
- 拉斐爾網站路徑：`/home/hoonsoropenclaw/.openclaw/workspace/Rimuru_and_Raphael/.../raphael-status-site/`
- 任何腳本要更新網站 HTML 前，先確認 `SKILLS_TAB` 或 `STATS_FILE` 等路徑指向正確的網站

### 完整部署流程（赫米斯網站）

```bash
# 1. 確認目前所在目錄是正確的網站
pwd
# 預期：/home/hoonsoropenclaw/hermes-status-site

# 2. 執行統計腳本（更新本地 HTML）
python3 ~/.hermes/scripts/skill_usage_stats.py

# 3. Git commit（這樣 GitHub 也有最新版本）
git add tabs/skills.html
git commit -m "feat: 更新技能呼叫統計"
git push origin main

# 4. 部署到 Vercel（直接上傳本地檔案，繞過 Git）
cd /home/hoonsoropenclaw/hermes-status-site
vercel --token $VERCEL_API_TOKEN --yes --prod --name raphael-status-site

# 5. 驗證部署結果
# 生產 URL: https://raphael-status-site.vercel.app
```

### 驗證技能統計區塊存在

```bash
# 確認技能呼叫統計已寫入 HTML
grep -c "🦞 技能呼叫統計" /home/hoonsoropenclaw/hermes-status-site/tabs/skills.html
# 預期輸出：3（頁面中有3處出現）

# 確認資料筆數
grep -c "共.*個技能" /home/hoonsoropenclaw/hermes-status-site/tabs/skills.html
# 預期輸出：1
```

### 確認部署內容正確（瀏覽器驗證）

目標 URL：`https://raphael-status-site.vercel.app/tabs/skills.html`

預期元素：
- 🦞 技能呼叫統計（出現在頁面中）
- 搜尋框：`<input type="text" placeholder="搜尋技能名稱...">`
- 排序下拉：`<select>` 包含「按累計呼叫排序（高→低）」
- 統計表格：`<table>` 含「累計呼叫」欄位

如果看不到這些元素，說明部署了舊版或錯誤的內容。

### Cron Job 更新頻率

目前的 `skill-usage-daily` cron job 每天 00:00 執行 `skill_usage_stats.py`：
- 更新 `~/.hermes/skills/skill_stats.json`
- 更新 `/home/hoonsoropenclaw/hermes-status-site/tabs/skills.html`

但不會自動部署到 Vercel。如需自動部署，需在 cron job 中加入 `vercel --prod` 命令。