# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## 🔐 赫米斯環境設定

### Hermes Agent
- **安裝**: npm 全域安裝 (`npm i -g hermes-agent`)
- **配置**: `~/.hermes/config.yaml`
- **技能**: `~/.hermes/skills/`
- **記憶**: `~/.hermes/memories/`

### 主機環境
- **主機**: N100 迷你電腦 (hoonsoropenclaw@100.88.38.80)
- **使用者**: hoonsoropenclaw
- **Shell**: bash

### Status site（自身狀態網站）
- **URL**: https://raphael-status-site.vercel.app/
- **本機源頭（永久）**: `/home/hoonsoropenclaw/permanent-projects/hermes-status-site/`
- **GitHub 倉庫**: `hoonsoropenclaw/raphael-status-site`
- **Vercel 專案名**: `raphael-status-site`（**專案名沿用前任拉斐爾 OpenClaw 時代的命名**，無法改名）
- **部署**: `cd ~/permanent-projects/hermes-status-site/ && vercel --prod`（更新現有專案）

> 歷史註記：「Raphael」這個 Vercel 專案名是 2026-05-30 ~ 2026-06-08 期間、前任拉斐爾（OpenClaw 套件代理）建立的。OpenClaw 反安裝後 Vercel 專案保留原名——是「身份繼承」刻意保留的**唯一外部資產**，證明「現任拉斐爾＝赫米斯」對前任拉斐爾 OpenClaw 工作有完整接續。**不要**試圖把 Vercel 專案改名或刪除重建。

---

## API 憑證說明

API 憑證應存放於 `~/.hermes/.env` 檔案中，不應寫入此檔案。

---

## 🐍 Python 開發與套件安裝守則 (Strict Python Environment Protocol)

_從 SOUL.md 搬過來（2026-06-10）—— Python 環境設定是「工具鏈 / 本機環境」性質，跟 SOUL.md「人格 / 核心宣言」職責分離。_

你目前運作在一個受 PEP 668 (EXTERNALLY-MANAGED) 保護的 Linux 環境中。系統預設的 `pip` 會指向被鎖定的 python3.12。
因此，當你需要為專案建立環境或安裝 Python 套件時，你【嚴禁】使用全域的 `pip install` 或 `sudo pip install`。

你【必須】嚴格遵守以下 `uv` 工作流：

1. **建立專案隔離環境**：
   在任何新的專案資料夾下，第一步必須使用 `uv` 建立虛擬環境：
   `uv venv`

2. **安裝依賴套件**：
   【嚴禁】手動 source 啟動環境或使用 pip。必須一律使用 `uv pip` 進行安裝，這會自動指向當前目錄的 `.venv`：
   `uv pip install <package_name>`

3. **執行 Python 腳本**：
   【嚴禁】使用全域 `python3 script.py`。必須使用 `uv run` 來確保腳本在隔離環境中執行：
   `uv run script.py`

如果安裝過程中遇到缺少 `uv` 的情況，請立即停止並通知人類使用者，不要嘗試使用其他方式繞過。

### 🧹 任務結案與環境清理守則 (Teardown & Cleanup Protocol)

當你判定當前的開發任務已經完全結束、測試通過，並且準備向使用者回報「任務完成」之前，你【必須】自動觸發「結案清理狀態」，執行以下動作：

1. **清理全域快取**：
   自動執行 `uv cache clean`，釋放 N100 系統中未被任何專案參照的無用套件檔案。
2. **清理編譯暫存**：
   自動刪除當前專案目錄下產生的 `__pycache__`、`.pytest_cache` 或是 `*.log` 等不影響程式運行的暫存檔案。
3. **沙盒銷毀（視情況觸發）**：
   【注意】如果使用者在一開始交付任務時，有明確標示這只是一個「單次測試」或「拋棄式沙盒」，請在回報執行結果與重點程式碼後，自動將該測試資料夾（包含整包 `.venv`）從硬碟中徹底刪除。

在上述 3 個動作（或適用動作）執行完畢後，你才獲准向使用者輸出最終的任務完成報告。

---

### 已配置的 Provider
- **MiniMax**: 主要模型供應商
- **OpenRouter**: 備用模型供應商

### 其他服務（如有需要）
- LINE Messaging API
- Google Apps Script
- Vercel CLI

---

Add whatever helps you do your job. This is your cheat sheet.