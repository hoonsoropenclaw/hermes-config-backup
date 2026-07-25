# hermes-dojo — Layer 3 自我改進系統

**Repository**: Yonkoo11/hermes-dojo  
**License**: MIT  
**Context**: 2026-03 Hermes Agent Hackathon 作品  
**Core loop**: `measure → identify weakness → evolve → report`

## 架構

```
hermes-dojo/
├── SKILL.md              # 主 skill（/dojo analyze/improve/auto 命令）
├── scripts/
│   ├── monitor.py        # 讀 state.db，計算指標
│   ├── analyzer.py      # 分類失敗根因，排名弱點
│   ├── fixer.py          # 修補技能，創建新技能，執行 self-evolution
│   ├── reporter.py       # 生成 CLI/Telegram 報告
│   └── tracker.py        # 儲存/取出學習曲線數據
```

## 與赫米斯現有架構的關係

| 赫米斯現有能力 | 覆蓋情況 |
|----------------|---------|
| metacognitive-learner（每 2 小時） | 覆蓋 Phase 1-4 學習流程，但**無自動失敗信號輸入** |
| trial-and-error skill | 被動累積（依賴 session 踩坑 + 手動入庫） |
| hermes-self-improvement（本文檔） | 理論框架，無實作工具 |
| automated-sop-validation | Layer 2.5 產出格式檢查，**不追蹤失敗** |

hermes-dojo 填補的是：**從 state.db 自動讀取失敗信號 → 自動驅動技能改進**，而非依賴用戶反饋或每 2 小時掃描。

## 安裝方式（待驗證）

```bash
# 方式 1：從 GitHub clone 到 skills 目錄
cd ~/.hermes/skills
git clone https://github.com/Yonkoo11/hermes-dojo.git hermes-dojo

# 方式 2：手動建立對應目錄
mkdir -p ~/.hermes/skills/hermes-dojo
# 然後從 GitHub raw content 取得 SKILL.md 和 scripts/
```

## 觸發命令

| 命令 | 行為 |
|------|------|
| `/dojo analyze` | 分析近期 session 的失敗模式 |
| `/dojo improve` | 修補最弱的技能 + 執行 self-evolution |
| `/dojo report` | 生成改進報告 |
| `/dojo history` | 顯示學習曲線 |
| `/dojo auto` | 建立 overnight cron（analyze → improve → report）|

## 關鍵洞察

> "Your AI agent makes the same mistakes every day. You correct it, it forgets next session."

這句話精確描述了赫米斯 trial-and-error 的被動性：條目需要「人為觸發写入」，但沒有人主動追蹤「連續幾個 cycle 同一坑都在踩」並自動驅動修復。hermes-dojo 的 `tracker.py` 正是這個自動追蹤層。

## 與赫米斯的整合評估

**優點**：
- Layer 3 閉環自動化，填補當前最大缺口
- 直接用現有 state.db，無需新基礎建設
- MIT license 可自由改寫

**待確認**：
- 是否與赫米斯 cron 系統相容（hermes-dojo 的 `/dojo auto` 可能假設有自己的 cron 機制）
- `fixer.py` 的自我修補邏輯是否安全（防止破壞性修改）
- 是否需要 Python 環境相依（需在 N100 上驗證）

## If→Then

**If** hermes-dojo 部署成功 **Then** 每日自动追踪「哪些技能連續失敗」，不需依賴用戶反饋或手動寫 trial-and-error

**If** hermes-dojo 報告「某技能 3+ cycle 未改善」**Then** 該技能進入緊急修復狀態，優先於新技能學習
