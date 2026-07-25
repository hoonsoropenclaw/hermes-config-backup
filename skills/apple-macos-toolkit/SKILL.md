---
name: apple-macos-toolkit
description: "macOS 工具組 — Apple Notes / Reminders / FindMy / iMessage / computer-use 等 Apple 生態系 CLI 與自動化工具的統一入口。當使用者說「macOS」「Apple」「自動化 mac」「Notes」「Reminders」「FindMy」「iMessage」「驅動 Mac 桌面」時載入。每個工具仍維持獨立 skill（便於精準觸發），本 skill 是統一參考入口。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macos, apple, automation, notes, reminders, findmy, imessage, computer-use, toolkit, umbrella]
    related_skills: [obsidian, browser]
    triggers: [macOS, Apple, 自動化 mac, Notes, Reminders, FindMy, iMessage, 驅動 Mac 桌面, computer_use]
---

# Apple / macOS Toolkit

> **2026-06-20 整合**：本 skill 整合 5 個原本獨立的 macOS 工具 skill 為單一 umbrella。每個工具仍維持獨立 skill（便於精準觸發 + 小 context footprint），本 skill 提供統一入口 + 完整 reference 文件。

## 何時使用本 skill

當使用者問到任一 macOS 工具時觸發：
- Apple Notes（memo CLI）
- Apple Reminders（remindctl CLI）
- Find My / AirTags（AppleScript）
- iMessage / SMS（imsg CLI）
- macOS 桌面自動化（computer_use 工具）

**如果只是要用其中一個工具，建議直接載入對應 skill 較省 context**：
- `apple-notes`、`apple-reminders`、`findmy`、`imessage`、`macos-computer-use`

本 skill 是統一參考入口，內容完整但較大。

## 工具總覽

| 工具 | CLI / 機制 | 用於 | 觸發詞 |
|------|------------|------|--------|
| **Apple Notes** | `memo` (Homebrew) | 新增/搜尋/編輯 Notes | 「記事」「Notes」「iCloud 筆記」|
| **Apple Reminders** | `remindctl` (Homebrew) | 新增/列表/完成 Reminders | 「提醒事項」「Reminders」「Todo」|
| **Find My** | AppleScript + screen capture | 追蹤 Apple 裝置 / AirTag 位置 | 「FindMy」「AirTag」「找手機」|
| **iMessage** | `imsg` (Homebrew) | 收發 iMessage / SMS | 「iMessage」「SMS」「傳訊息」|
| **macOS Computer Use** | `computer_use` 工具 | 背景驅動 Mac 桌面（截圖、滑鼠、鍵盤） | 「驅動 macOS」「computer_use」「自動化 Mac 桌面」|

## 共通前置條件

全部都需要：
- **macOS** 系統
- 對應的 Apple 系統偏好設定權限（Full Disk Access、Automation、Screen Recording）
- 大部分需要 `brew install` CLI 工具

詳細各工具的安裝與權限要求見對應 reference 檔。

## 各工具詳細 reference

完整內容（從原 skill 保留）見：

- `references/apple-notes.md` — Apple Notes 完整 SOP（2.1KB）
- `references/apple-reminders.md` — Apple Reminders 完整 SOP（3.6KB）
- `references/findmy.md` — Find My 完整 SOP（3.7KB）
- `references/imessage.md` — iMessage 完整 SOP（2.4KB）
- `references/macos-computer-use.md` — macOS 桌面自動化完整 SOP（7.3KB）

## 整合決策紀錄

**為什麼合併？**
- 5 個 skill 都很薄（2-7KB），加總 ~19KB，與其分散載入、不如統一入口
- 都觸發「macOS」這個 context，便於 agent 一次找齊相關工具
- 個別 skill 仍保留以利精準觸發（小 context footprint）
- reference 檔保留原始 SKILL.md 內容（frontmatter 完整、無失真）

**為什麼不整個砍掉獨立 skill？**
- 各 skill 的觸發詞明確（例如「Apple Reminders」vs「iMessage」），獨立觸發更精準
- 各 CLI 工具安裝/權限要求不同，分開管理較乾淨
- Agent 若只問其中一個、context 越小越好
