# Workspace Folder Layout 相關踩雷（從 ~/.hermes/ 28→23 整理歸納）

> 觸發：使用者說「X 資料夾看起來很亂」「要清理根目錄」「要按規則分類」「路徑該放哪」時讀這份。

---

### 根目錄檔案盤點三類法（2026-06-10 從 ~/.hermes/ 整理歸納）

**症狀**：看到根目錄「很亂」、不知道哪些檔該清、哪些該留、哪些是 hermes 系統設計的不能動

**根因**：根目錄是「hermes 內部（hardcode 路徑）+ 使用者第三方（OAuth 憑證、metadata、工具設定）」的混雜區，沒有明顯分類標記，光看檔名無法分辨。

**解法**（**3 類法**）：

1. **先列**：`find <dir> -maxdepth 1 -type f` + `-type d` 列所有
2. **找設計意圖**：grep hermes 原始碼（`*.py`）找每個檔案 hardcode 引用位置 → 確認是不是 hermes 系統設計
3. **分 3 類**：
   - 🔵 **hermes 系統設計**（不可動）：
     - 配置：`config.yaml`、`.env`、`auth.json`、`.install_method`
     - 狀態：`state.db` + shm + wal（SQLite WAL 模式配套）
     - 讀寫歷史：`.hermes_history`（prompt_toolkit readline 歷史，UI-TUI README 明寫在 `~/.hermes/.hermes_history`）
     - 內建快取：`models_dev_cache.json` 等（hermes `get_hermes_home() / "..."` 寫死路徑）
     - 鎖定檔：`*.lock`、PID、`auth.lock` 等（advisory flock 機制，0 bytes 是正常的）
   - 🟠 **hermes 內建但用不到**（保留觀察）：`kanban.db`（Kanban 系統，可重 init）、`*.init.lock`（init 完成後過期鎖殘留）
   - 🟡 **使用者/第三方**（可搬/可選）：自建 OAuth token、第三方 metadata、工具設定檔
4. **交叉驗證**：跟備份腳本 `hermes-backup-v4.sh` 排除清單對照（hermes-backup-design-pitfalls Rule 12「對任何資料備份前，先查能不能 rebuild」）

**預防**：
- 不要憑印象答「這個檔不重要」先 grep 找 hardcode 引用再說
- 用 `hermes-backup-coverage-check.sh`（v4.6 起）每日掃路徑變動、跟 v4 同步清單比對

**If→Then**：
- **If** 接到「X 資料夾看起來很亂」 **Then** 用 grep 路徑 hardcode + cross-check 找設計意圖、不憑印象答
- **If** 任何根目錄盤點 **Then** 必分「系統設計/內建但用不到/使用者第三方」三類
- **If** 清理某個檔之前 **Then** 跑 `hermes status` 跟 `ls -la` 確認不是 hermes 正在用的
- **If** 改完路徑/搬檔 **Then** 跑 `hermes --version` 確認 hermes 仍能正常啟動（避免動到 hermes 讀的檔）

**相關條目**：
- [[hermes-internal#SOUL.md 永遠在 HERMES_HOME 根目錄、不在 memories/]]
- [[hermes-backup-design-pitfalls#v4 備份腳本只列 7 個目錄+1 個檔,但 ~/.hermes/ 根目錄有 20+ 個路徑]]
- [[hermes-backup-strategy#hermes-backup-coverage-check.sh 設計:3 層檢查 + EXCLUDE 清單明確]]
- [[hermes-backup-sop#改任何備份腳本必同步改 INVENTORY.md + SKILL.md §14.1 改檔對照表]]
