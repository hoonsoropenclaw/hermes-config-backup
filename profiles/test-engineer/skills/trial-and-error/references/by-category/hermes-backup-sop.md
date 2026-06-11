# Hermes 全狀態備份 SOP（從 INVENTORY.md 設計歸納）

> 觸發：使用者說「改備份腳本」「加新 rsync 段」「INVENTORY.md 怎麼維護」「改檔對照表要含哪些」時讀這份。

---

### 改任何備份腳本必同步改 INVENTORY.md + SKILL.md §14.1 改檔對照表（2026-06-10 從建立 INVENTORY.md 歸納）

**症狀**：改 `hermes-backup-v4.sh` 加新 rsync 段、但忘記同步 SKILL.md 改檔對照表、第二次就忘記這個目錄的 rsync 段、文件跟程式碼 drift；多檔案/多腳本共用同一份清單時、沒 single source of truth 容易出錯

**根因**：
1. 備份設計是「跨多檔案同步變動」（v4 腳本 + coverage check + SKILL.md + INVENTORY.md），任何一個忘了改、其他就 drift
2. 沒 single source of truth：v4 腳本 hardcode 同步清單、coverage check 解析 v4 腳本反推、SKILL.md §14.1 又寫一份 — 三處都不同步風險

**解法**（4 步）：
1. **建 `~/.hermes/docs/INVENTORY.md` 作為 single source of truth**：v4 同步清單、EXCLUDE 清單、改檔對照表都在這
2. **`hermes-backup-v4.sh` 改必同步更新 INVENTORY.md**：根目錄單檔 array、13 個 rsync 段、所有排除規則
3. **`hermes-backup-coverage-check.sh` 改必同步更新 INVENTORY.md**：EXCLUDE 列表、預期同步清單解析邏輯
4. **`agent-system-backup/SKILL.md` §14.1 改檔對照表必含 INVENTORY.md + coverage check script**：未來改任何備份相關都會被引導到 INVENTORY.md

**預防**：
- 任何 multi-file 同步設計都必建「INVENTORY.md single source of truth + 改檔對照表」
- 改完必跑 `bash hermes-backup-v4.sh --dry-run` + `bash hermes-backup-coverage-check.sh` 雙驗證
- 變更記錄寫 INVENTORY.md §「變更記錄」段（v4.5 / v4.6 / v4.6.1）
- SKILL.md §14 改檔對照表是「給未來 AI 必看」、任何備份架構改動都必同步

**If→Then**：
- **If** 改任何備份腳本 **Then** 必同步更新 INVENTORY.md（single source of truth）
- **If** 任何 multi-file 同步設計 **Then** 必建 INVENTORY.md + 改檔對照表
- **If** 改檔忘記同步 **Then** 跑 coverage check 會抓到（daily cron 不會放過 drift）
- **If** INVENTORY.md drift 超過 7 天沒修 **Then** 該架構已經不可信、要全部重對

**相關條目**：
- [[hermes-backup-design-pitfalls#v4 備份腳本只列 7 個目錄+1 個檔,但 ~/.hermes/ 根目錄有 20+ 個路徑]]
- [[hermes-backup-strategy#hermes-backup-coverage-check.sh 設計:3 層檢查 + EXCLUDE 清單明確]]
- [[workspace-folder-layout#根目錄檔案盤點三類法]]
