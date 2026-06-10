---
name: Connection Resilience
slug: connection-resilience
version: 1.0.0
homepage: 
description: 連線恢復專家 - 監控對話中斷、自動恢復、保護長時間任務。當回應中斷時自動重連，確保 N100 代理 24/7 穩定運行。
changelog: Initial release
---

## When to Use

用戶反映回應中斷、對話無回應、或連線不穩定的情況。

## 問題分析

### 常見中斷原因

| 原因 | 徵兆 | 解決方向 |
|------|------|----------|
| Session 檔案鎖定 | 回應延遲、 無法寫入 | 清理鎖定、調整 Timeout |
| 網路不穩定 | 偶發性超時 | 增加重試機制 |
| 子代理競爭 | 5/5 插槽滿、spawn 被阻擋 | 調整並行策略 |
| Gateway 負載過高 | 回應變慢 | 分散負載、重啟服務 |
| 長時間任務中斷 | 正在執行的任務消失 | checkpoint + 恢復 |

## 技能組成

```
connection-resilience/
├── SKILL.md                          # 本檔案
├── monitor.sh                        # 連線監控腳本（cron 每分鐘執行）
├── recover.sh                       # 中斷恢復腳本
├── session_guardian.sh               # Session 看門狗
└── status_tracker.json              # 狀態追蹤
```

## 工作原理

### 三層保護機制

```
Layer 1: 預防 (Prevention)
└── monitor.sh 每分鐘檢查 session 狀態、API 額度、gateway 響應

Layer 2: 檢測 (Detection)  
└── 發現異常立即記錄並觸發警報

Layer 3: 恢復 (Recovery)
└── recover.sh 自動執行恢復流程
```

## 使用方式

### 1. 啟動監控
```bash
# 加入 crontab 每分鐘執行
* * * * * bash /home/hoonsoropenclaw/.openclaw/workspace/skills/connection-resilience/monitor.sh
```

### 2. 手動檢查狀態
```bash
bash /home/hoonsoropenclaw/.openclaw/workspace/skills/connection-resilience/monitor.sh status
```

### 3. 強制恢復
```bash
bash /home/hoonsoropenclaw/.openclaw/workspace/skills/connection-resilience/recover.sh force
```

## 恢復腳本邏輯

```
recover.sh 執行流程：
1. 檢查 gateway 是否存活
2. 若 gateway 無響應 → 嘗試重啟
3. 檢查 session 鎖定
4. 若鎖定超過 5 分鐘 → 強制釋放
5. 檢查子代理狀態
6. 若有任務中斷 → 重新放入排程
7. 發送恢復報告到 Telegram
```

## 預防最佳實踐

1. **不要一次請求太多** - 拆分成小任務
2. **長時間任務用 Cron** - 不要依賴單次對話
3. **重要任務留 checkpoint** - 方便從中斷點恢復
4. **定期重啟 Gateway** - 避免記憶體洩漏
5. **超過 180s 的同步任務用 `terminal(background=true)` 跑**（2026-06-07 新增）— 避免 foreground timeout 把已經在做的事殺掉
   - 例：`rsync 9000+ skill 到 GitHub staging`、`git push 大 commit`、`rclone sync 整個目錄`
   - 用法：`terminal(background=true, notify_on_complete=true)` + `process(action='wait', timeout=180)`
   - 配 `process(action='poll')` 看進度、`process(action='wait')` 等完成
   - 看完整輸出用 `process(action='log')`

## 與其他技能的互動

- 與 `endless_learning` 配合：確保學習任務不中斷
- 與 `system_expert` 配合：系統層級問題診斷
- 與 `memory-mcp` 配合：保護長期記憶完整性

## 觸發條件

當偵測到以下情況時，自動觸發恢復：

- Gateway 響應時間 > 30 秒
- Session 鎖定時間 > 5 分鐘
- 子代理連續 3 次 spawn 失敗
- API 額度即將用盡（< 5%）