# 使用者自訂 keyword 觸發規則 SOP（2026-06-09 啟用）

> HERMES 沒有內建 user-defined macro。所有「之後我說 X 時請執行 Y」的跨 session 規則都透過這套 agent-level 機制實作。

## 觸發流程（agent 收到訊息時）

```
收到訊息
  ↓
掃訊息含不含「@<關鍵字>」（@ 是慣例前綴、Telegram/LINE 都吃、不要用 / 避免跟 slash command 撞）
  ↓ 命中
讀 AGENTS.md 開頭「🎯 使用者自訂 keyword 觸發規則」表的對應列
  ↓
按該列的「觸發行為」描述執行
  ↓
結尾報告「跑了什麼、改了什麼」
```

## 目前啟用的 keyword（2026-06-09 狀態）

| Keyword | 觸發行為 | 模式 |
|---|---|---|
| `@學習` | 1. 掃此次對話試誤 → 跟 `trial-and-error` skill 既有條目去重 → 只新增沒重複的 L2 條目到 `references/by-category/` 對應分類<br>2. 對話摘要篩出「跨 session 重要事項」→ 視情況更新 MEMORY.md / AGENTS.md<br>3. 結束時**統一報告**改了哪些檔 | **B 模式**：有把握的真新教訓直寫、結尾報告；沒把握的問使用者確認 |
| `@刷新` | 跑 `hermes status` + `ls ~/.hermes/memories/` + 報告系統狀態 | 預留未啟用 |
| `@備份` | 跑 `~/.hermes/scripts/hermes-backup-v4.sh` → 報告備份結果 | 預留未啟用 |

## 三種觸發模式（給未來參考）

| 模式 | 行為 | 適用情境 |
|---|---|---|
| **A** 確認優先 | 每次都列清單等使用者逐一勾選 | 高風險任務（清資料、刪檔、動 config） |
| **B** 直寫+報告 | 有把握的真新教訓直寫、結尾報告；沒把握的問確認 | **中風險**（像 @學習 寫進 trial-and-error、可回退） |
| **C** 寬鬆 | 看到訊息就動、不需等確認 | 低風險（讀檔、跑 status、列清單） |

## 新增 keyword 的 SOP（給未來自己看）

使用者說「之後我說 X 時請執行 Y」時：

1. **當下就在 `~/.hermes/memories/AGENTS.md` 開頭的 keyword 表格新增一行**——不要等、不要只回對話
2. **如果是多步驟 SOP**（像 @學習 4 步流程）：建 reference file（像本檔或 `~/.hermes/skills/trial-and-error/references/adding-entries-sop.md`），AGENTS.md 表格該列寫「完整 SOP 見 references/sops/<name>.md」
3. **跑 `grep` 驗證**寫入了——不靠 patch 工具的成功訊息
4. **如果 SOP 是新類別的**（不是已有 skill 能管的）：考慮建獨立 skill，避免 AGENTS.md 表格膨脹
5. **驗證 SOP 真的可被新 session 讀到並執行**：把表格內容寫成「新 session 也能直接執行」的具體指令（具體路徑、預期輸出），不要寫敘述性語句

## If→Then 速查

- **If** 收到「之後我說 X 時請執行 Y」**Then** 當下在 AGENTS.md 開頭表格新增一行 + `grep` 驗證
- **If** keyword 觸發的 SOP 超過 3 步 **Then** 建 reference file 拆出去
- **If** 不確定該用 A/B/C 哪個模式 **Then** 預設 B（@學習 模式），使用者後續要求可調
- **If** 觸發的行為改了系統狀態（動了檔、跑 cron、砍東西）**Then** 結尾一定要報告改了什麼（不要只說「跑完了」）
- **If** 發現既有 keyword 表格的 SOP 指向不存在的檔 **Then** 立刻補建（AGENTS.md 不能指向虛無）
- **If** 觸發失敗（找不到 skill、找不到檔）**Then** 不要硬擺、誠實說「這個 SOP 還沒寫完」+ 給建議怎麼補

## 相關檔案

- `~/.hermes/memories/AGENTS.md` — keyword 表格的 source of truth（每次啟動讀）
- `~/.hermes/skills/trial-and-error/SKILL.md#新增條目 SOP` — @學習 4 步流程精簡版
- `~/.hermes/skills/trial-and-error/references/adding-entries-sop.md` — @學習 完整版（決策樹、常見錯誤、If→Then 速查）

## 設計決策的「為什麼」（給未來 audit 用）

| 決策 | 為什麼這樣選 |
|---|---|
| 用 `@` 前綴不用 `/` | `/` 在 Telegram/Discord 會被當 slash command、`@` 不會衝突且 platform 通用 |
| 寫進 AGENTS.md 不寫進 SOUL.md | AGENTS.md 是「行為/觸發規則」段、SOUL.md 是「人格/價值觀」段，職責分離 |
| 不建 cron / webhook | cron 是「獨立進程」、不是「會話內觸發」，會失去對話脈絡 |
| 預設 B 模式 | 跟 trial-and-error 既有 SOP 一致（@學習是 mid-task 行為、需要快速迭代、但又不能太寬鬆誤寫） |
| 不建獨立 `keyword-triggers` skill | 目前只 1 條啟用、AGENTS.md 表格就放得下；等 3+ 條 SOP 都成型再獨立 |
