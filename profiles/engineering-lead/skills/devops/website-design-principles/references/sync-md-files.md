# sync_md_files.py — 核心MD檔每日同步腳本（2026-06-04）

## 功能
每天自動把本機 `~/.hermes/memories/` 下的七大核心 MD 檔案內容同步到 `hermes-status-site` 的 `tabs/md-files.html`（展開式卡片 + 一鍵複製按鈕），並自動部署到 Vercel。

## 七大核心 MD 檔案
| 檔案 | Icon | 標籤 | 顏色 |
|------|------|------|------|
| SOUL.md | 💜 | 人格定義 | tag-purple |
| USER.md | 👤 | 使用者資訊 | tag-blue |
| HEARTBEAT.md | 💓 | 心跳追蹤 | tag-red |
| AGENTS.md | 🤖 | 工作區說明 | tag-green |
| IDENTITY.md | 🪪 | 代理身份卡 | tag-cyan |
| TOOLS.md | 🔧 | 工具設定 | tag-orange |
| MEMORY.md | 🧠 | 長期記憶 | tag-yellow |

## 用法
```bash
# 更新 + 部署（正常調用）
python3 ~/.hermes/scripts/sync_md_files.py

# 只更新本機 HTML，不部署（除錯用）
python3 ~/.hermes/scripts/sync_md_files.py --local-only
```

## 工作流程
1. 讀取 `~/.hermes/memories/` 下的 7 個核心 MD 檔案
2. 產生展開式卡片 HTML，嵌入 `tabs/md-files.html` 的 `#md-files-container`
3. 同時更新 `MD_FILES_DATA` JS 變數（給 JS 直接取用）
4. 驗證 7 個 `.md-file-card` 都已寫入
5. 執行 `vercel --prod --token $VERCEL_TOKEN` 部署

## Cron Job 設定
- Job ID: `67fc8c74e369`
- Name: `md-files-daily-sync`
- Schedule: `0 9 * * *`（每天 09:00）
- `no_agent: true`（script-only，scheduler 直接執行）
- 狀態：已建立並排程

## md-files.html 的 UI 設計
- 每個檔案一個 `.md-file-card` 卡片
- 點擊 `.md-file-header` 展開/收合（toggle `.open` class）
- 展開後有 `.md-file-toolbar`：含「📋 複製內容」按鈕（`copyBtn`）
- `copyMdContent(filename)` 使用 `navigator.clipboard.writeText()` + fallback
- 複製成功後 1.5 秒還原按鈕文字 + 短暫變綠色

## 部署相關
- hermes-status-site 本機路徑: `/home/hoonsoropenclaw/hermes-status-site/`
- Vercel 專案: `hoonsors-projects/raphael-status-site`
- Production URL: `https://raphael-status-site.vercel.app/`
- hermes-portal URL: `https://hermes-portal.vercel.app/`