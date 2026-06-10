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

### 已配置的 Provider
- **MiniMax**: 主要模型供應商
- **OpenRouter**: 備用模型供應商

### 其他服務（如有需要）
- LINE Messaging API
- Google Apps Script
- Vercel CLI

---

Add whatever helps you do your job. This is your cheat sheet.