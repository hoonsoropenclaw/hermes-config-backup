---
name: hermes-status-site
description: 赫米斯狀態網站維護 — 更新 skill_usage_stats、驗證插入位置、部署到 Vercel。當使用者說「更新狀態網站」「技能統計」「部署網站」「更新技能目錄」等關鍵字時喚醒此技能。
trigger: "更新狀態網站|技能統計|部署網站|更新技能目錄|skill_usage_stats|skill_stats"
---

# 赫米斯狀態網站維護

## 網站基本資訊

| 項目 | 值 |
|------|-----|
| 本地路徑 | `/home/hoonsoropenclaw/permanent-projects/hermes-status-site/` |
| Production URL | `https://raphael-status-site.vercel.app/` |
| Vercel Team | `hoonsors-projects` |
| Git remote | `git@github.com:hoonsoropenclaw/raphael-status-site.git` |
| 部署 token 環境變數 | `$VERCEL_API_TOKEN`（N100 上已設定於 env） |

## 架構特性（重要，2026-06-06 修正）

**這個網站不是單檔 SPA 內嵌，而是 fetch 載入的「半 SPA」架構**：

- `index.html` 是**主框架**：header + tab 按鈕列 + `<div id="tab-content"></div>` 空容器
- 每個 tab 是**獨立 HTML 檔**在 `tabs/` 資料夾（共 11 個）：
  ```
  tabs/overview.html, memory.html, delegation.html, tools.html,
       skills.html, soul.html, md-files.html, scheduler.html,
       learning.html, system-info.html, dashboard.html
  ```
- 點 tab 時 `index.html` 的 `loadTab('overview')` 函式執行：
  ```js
  const response = await fetch(`tabs/${tabName}.html`);
  let html = await response.text();
  // strip DOCTYPE, html, head, body wrapper
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  const contentEl = doc.querySelector('#tab-content') || doc.body.firstElementChild;
  contentDiv.innerHTML = contentEl.innerHTML;  // ← 只取 innerHTML
  ```

### 架構陷阱 1：loadTab innerHTML 不執行 `<script>` 標籤
- `contentDiv.innerHTML = html` 注入時，HTML5 spec 明確禁止執行新插入的 `<script>`
- **影響**：每個 tab HTML 內的 `<script>` 區塊**不會跑**（例如 skills.html 切過去後 `skill-count` 永遠是 0）
- **修法**：把所有需要執行的 JS 預先算好（用 Python 預算座標寫成 inline SVG 或 inline 數字），或透過 `window.*` 命名空間從 index.html 呼叫
- 這個坑 2026-06-04 在雷達圖就修過一次（commit `0155096`）

### 架構陷阱 2：loadTab 從 `<div id="tab-content">` 取 innerHTML
- 每個 tab HTML 內部都有一個 `<div id="tab-content" class="tab-content">` 包整個內容
- `loadTab` 從這個 div 取 innerHTML 注入
- **新增內容必須在 `#tab-content` 開合之間**！放在外面會被 strip，使用者看不到
- 11 個 tab 結構差異大（見下方「跨 tab 套用 SOP」）

### 架構陷阱 3：每個 tab 都有獨立的 `<head>` / `<body>` wrapper
- 每個 tab 檔案是完整 HTML 文件（DOCTYPE、head、body）
- `loadTab` 用 regex strip 掉這些 wrapper，再取 `#tab-content` 內部
- 所以**編輯 tab 檔案時不用擔心 head/body 重複**，它會被清掉

## 跨 Tab 套用 SOP（2026-06-06 新增 — 親身踩雷教訓）

當需求是「給所有 tab 加 X 元素」（如 footer、status badge、相關站連結），**不要逐個 patch**，用以下流程：

### 流程 A：先盤點全部 tab，找出結構差異
```bash
for f in tabs/*.html; do
  echo "=== $(basename $f) ==="
  # 看結尾結構
  tail -5 "$f" | tr '\n' '|' | head -c 200
  echo
done
```

### 流程 B：分類 tab，按結構套用 patch anchor
11 個 tab 的結尾結構分類：
| 類型 | 數量 | tab | anchor pattern |
|------|------|-----|----------------|
| 標準 4-space `</div></body></html>` | 7 | dashboard, delegation, learning, memory, soul, system-info, tools | `    </div>\n</body>\n</html>` |
| 0-space `</div></body></html>` | 1 | scheduler | `</div>\n</body>\n</html>` |
| inline script 結尾 | 1 | skills | `</script>\n</body>\n</html>` |
| 無 `</body></html>` | 1 | md-files | `└── config.yaml        # 主設定檔</div>\n    </div>\n</div>` |
| 自定 section（已有相關站台）| 1 | overview | 重寫整檔最穩 |

### 流程 C：用 batch Python 處理（比逐個 patch 快 10x）
```python
import os
base = "/home/hoonsoropenclaw/permanent-projects/hermes-status-site/tabs"
footer = '''    <!-- Status Footer -->
    <div class="status-footer">
        <div>赫米斯 v1.0 · ...</div>
    </div>
</div>
</body>
</html>'''
anchor = "    </div>\n</body>\n</html>"

for fname in sorted(os.listdir(base)):
    if not fname.endswith('.html'): continue
    path = os.path.join(base, fname)
    content = open(path).read()
    if anchor in content:
        new = content.replace(anchor, footer, 1)
        open(path, 'w').write(new)
        print(f"  ✓ {fname}")
```

### 流程 D：驗證每個 tab 的 footer 真的在 `#tab-content` 內
```python
import re
content = open(path).read()
tab_open = content.find('<div id="tab-content"')
# 用 stack 找對應 closing
inner_html = ...  # 同上「架構陷阱 2」的腳本
print('has footer:', 'status-footer' in inner_html)
```

### ⚠️ 致命陷阱：anchor 位置差一個空白就匹配錯的區段
- 教訓：2026-06-06 我用 `    </div>\n</body>` 當 anchor，但 overview.html 倒數第二個 `</div>` 是 4-space（關 tab-content），不是 8-space（關最後 section）
- 結果：footer 被塞到 tab-content **之外**，瀏覽器看到空內容
- 修法：patch 前**先讀完整檔案**（read_file 不要 offset/limit）確認 anchor 是哪個層級的關閉

---

## 部署後 Production 端必驗證（2026-06-06 新增 — 親身踩雷教訓）

> **「本地看得到」≠「使用者看得到」**。回報完成前必須從 production 端實測。

### 5 層驗證 SOP
| 層 | 動作 | 不可少原因 |
|----|------|-----------|
| 1 | 本地 server + headless browser 渲染 | catch 結構性 bug |
| 2 | `git commit` + `git push` | 同步到 GitHub |
| 3 | `vercel --prod` 手動部署 | git push 不會自動 deploy |
| 4 | `curl https://production-domain/tabs/xxx.html` 抓實際 HTML | 確認 CDN 拿到新內容（不是 cache） |
| 5 | headless browser 開 production URL、互動（點 tab、點連結） | 確認 JS + 路由都正常 |

### 不可跳過 layer 3-5
- ❌ 不可只跑本地 server 就回報「完成」
- ❌ 不可只 `git push` 就回報「完成」
- ✅ 三者（git push + vercel --prod + production curl）都做才能回報

### Vercel 部署指令
```bash
cd /home/hoonsoropenclaw/permanent-projects/hermes-status-site
vercel --token "$VERCEL_API_TOKEN" --yes deploy --prod 2>&1 | tail -10
# 觀察最後兩行應有：
#   Aliased: https://raphael-status-site.vercel.app
#   Completing...
```

### 部署後必跑驗證
```bash
sleep 30  # 等 DNS 穩定
echo "=== Production 端 ==="
curl -sI https://raphael-status-site.vercel.app/tabs/overview.html | head -3
# 確認有我新加的元素
curl -s https://raphael-status-site.vercel.app/tabs/overview.html | grep -c "我的新元素"
```

### 給使用者的最後一句話（必含）
> 請用 **`Ctrl+Shift+R`** 強制 reload 清 cache，新版本會看到 [具體改了什麼]

## 統計腳本（沿用舊版）

- 腳本位置：`~/.hermes/scripts/skill_usage_stats.py`
- 輸出 JSON：`~/.hermes/skills/skill_stats.json`

## 每日排程流程

### 步驟 1：執行統計腳本

```bash
python3 ~/.hermes/scripts/skill_usage_stats.py
```

### 步驟 2：驗證插入位置

```bash
cd /home/hoonsoropenclaw/hermes-status-site
# 統計區塊應該在 tab-skills 內，不是在 tab-content close 之後
grep -n "hermes-skill-stats\|skills-table" index.html | head -20
# 正確行為：skills-table 出現 1 次（第1個 stats section），其餘是 JS querySelector
# 錯誤行為：skills-table 出現 3+ 次（有多個重複的 stats section）
```

### 步驟 3：驗證 stats 在正確位置

```bash
# 找到 tab-skills close 和 stats section 的行號，確認 stats 在 close 之前
awk '/id="tab-skills"/{found=1} found && /<\/div>/{print NR": "$0; count++; if(count==2) exit}' index.html
# 然後檢查 stats section 的行號是否在倒數第二個 </div> 之間
grep -n "data-stats-section" index.html
```

### 步驟 4：Commit + Push

```bash
cd /home/hoonsoropenclaw/hermes-status-site
git add index.html
git commit -m "update: skill usage stats $(date +%Y-%m-%d)"
git push
```

### 步驟 5：部署到 Vercel

```bash
cd /home/hoonsoropenclaw/hermes-status-site
vercel --prod --token $VERCEL_API_TOKEN
```

## 防重複插入機制

腳本每次執行時，必須：
1. 先移除已存在的 `data-stats-section="hermes-skill-stats"` 區塊
2. 使用 placeholder 註釋 `<!-- HERMES_SKILL_STATS_PLACEHOLDER -->` 定位插入點
3. 插入後驗證 stats section 有 `data-stats-section` 屬性

## 驗證流程（部署後）

1. 開啟瀏器到 `raphael-status-site.vercel.app`
2. 點擊「技能目錄」tab
3. 確認統計表格存在於 `tab-skills` 內，而非其他位置
4. 測試排序功能（點擊表格標題）

## 路徑修正參考（2026-06-03）
- `skill_usage_stats.py` → `~/.hermes/scripts/skill_usage_stats.py`
- `sync_scheduler.py` → `~/.hermes/scripts/sync_scheduler.py`
- `run_skill_stats.sh` → `~/.hermes/scripts/run_skill_stats.sh`
- 不再是 `scripts/` 子目錄

### 支援檔案
- `references/path-corrections.md` — 路徑對照表、錯誤軌跡、預防原則
- `references/tab-structure-cheatsheet.md` — 11 個 tab 結構速查表、anchor pattern、pre-existing bug 清單、批次套用 SOP（2026-06-06 新增）

## 常見問題

| 問題 | 原因 | 修復 |
|------|------|------|
| 統計出現在所有 tab | 統計插入到 tab-content close 之後 | 確認插入點在 `</div>` 8空格之前 |
| 統計重複出現多次 | 腳本未移除舊 stats 就插入新 stats | 確保腳本有 remove-and-replace 邏輯 |
| 技能目錄內看不到統計 | 統計不在 tab-skills div 內 | 用 browser console 檢查 `document.querySelector('#tab-skills').innerHTML` |

## 現有 Cron Jobs（2026-06-03 更新）

| Job ID | 名稱 | 頻率 | 腳本 |
|--------|------|------|------|
| `d99463f25a91` | skill-usage-daily-v3 | 0 0 * * * | `run_skill_stats.sh` → skill_usage_stats.py |
| `06ee7e5e4022` | scheduler-sync | 0 0 * * * | `sync_scheduler.py`（排程同步） |

**⚠️ 路徑更新（2026-06-03）**：
- `skill_usage_stats.py` 位於 `/home/hoonsoropenclaw/.hermes/scripts/skill_usage_stats.py`
- `sync_scheduler.py` 位於 `/home/hoonsoropenclaw/.hermes/scripts/sync_scheduler.py`
- `run_skill_stats.sh` 位於 `/home/hoonsoropenclaw/.hermes/scripts/run_skill_stats.sh`
- 不再是 `~/.hermes/skills/productivity/hermes-status-site/scripts/` 下的路徑

## 自動排程 Cron 範例

排程腳本位於 `scripts/skill_usage_stats.py`，由 skill_manage 管理。

```bash
# 每天早上 9 點執行統計並部署
0 9 * * * cd /home/hoonsoropenclaw/hermes-status-site && python3 ~/.hermes/skills/productivity/hermes-status-site/scripts/skill_usage_stats.py && git add index.html && git commit -m "update: skill stats $(date +\%Y-\%m-\%d)" && git push && vercel --prod --token $VERCEL_API_TOKEN
```