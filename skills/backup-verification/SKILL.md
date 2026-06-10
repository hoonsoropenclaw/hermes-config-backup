name: backup-verification
description: "備份驗證自動化 — 驗證 tar.gz 備份是否真的可還原。Level 1: 完整性檢查 → Level 2: 擷取測試 → Level 3: 內容驗證。"
version: 1.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [backup, verification, restore, automation, cron]
    triggers: [hermes-cron, backup, restore]
---

# 備份驗證自動化

## 為什麼需要這個技能

> **統計**：30-40% 的組織從未測試備份，直到災難恢復時才發現失敗。（CubePath）

赫米斯每天備份，但從未驗證備份是否真的可還原。備份而不驗證 = 沒有備份。

## 三層驗證模型

| 等級 | 測試 | 適用時機 |
|------|------|----------|
| **L1** | 完整性：tar -tzf + sha256sum | 每次備份後自動跑 |
| **L2** | 擷取：tar -xzf 到暫存目錄 | 每天一次 |
| **L3** | 內容驗證：檢查關鍵檔案存在且結構正確 | 每週一次 |

## 關鍵檔案清單

備份還原時，這些檔案必須存在且有效：

```
config.yaml              # 赫米斯設定
cron/jobs.json           # cron jobs 設定
memories/MEMORY.md        # 長期記憶
memories/SOUL.md          # 超級學習者人格
memories/USER.md          # 使用者資訊
memories/HEARTBEAT.md     # 心跳/任務清單
memories/IDENTITY.md      # 代理身份卡
memories/AGENTS.md        # 工作區說明
scripts/backup_hermes.sh  # 備份腳本（還原時需要）
scripts/restore_hermes.sh # 還原腳本
```

## 驗證腳本使用方式

### 快速驗證（每次備份後）
```bash
bash ~/.hermes/skills/backup-verification/scripts/verify_backup.sh \
  ~/.hermes/backups/hermes_backup_20260607_030000_full.tar.gz
```

### 完整驗證（含內容檢查）
```bash
bash ~/.hermes/skills/backup-verification/scripts/verify_backup.sh \
  ~/.hermes/backups/hermes_backup_20260607_030000_full.tar.gz \
  --full
```

### 自動化整合（建議加入 cron）
建議每天 04:00（備份完成後 1 小時）執行 Level 2 驗證：
```bash
# 在 crontab 中新增
0 4 * * * bash ~/.hermes/skills/backup-verification/scripts/verify_backup.sh \
  ~/.hermes/backups/$(ls -t ~/.hermes/backups/hermes_backup_*_full.tar.gz | head -1) \
  --full
```

## 失敗時的處理

| 錯誤類型 | 原因 | 處理 |
|----------|------|------|
| `tar: Unexpected EOF` | 下載不完整或磁碟損壞 | 刪除損壞的 tar，重新備份 |
| `sha256 mismatch` | 傳輸過程損壞 | 刪除並重新下載 |
| `config.yaml missing` | 備份範圍設定錯誤 | 檢查 backup_hermes.sh 的檔案清單 |
| `jobs.json corrupt` | JSON 解析失敗 | 手動檢查並修復 |

## If→Then 規則

**If** 備份驗證失敗（Level 1 或 Level 2）
**Then** 立即產生 alert，標記這次備份為「不可用」，並在下一個 cron cycle 重新備份
**Then** 保留失敗的 tar.gz 供人工審查（不要自動刪除）

**If** 連續 2 次備份驗證失敗
**Then** 觸發緊急維修流程（檢查磁碟空間、網路穩定性、GPG 加密狀態）

**If** 備份驗證成功
**Then** 將驗證結果寫入 `~/.hermes/logs/backup_verify.log`（时间戳 + 大小 + 關鍵檔案數）