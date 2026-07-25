# pending/ 交付架構陷阱（2026-06-24）

## 觀察

`~/.hermes/skill-usage/pending/20260616_125207_dc21b806.txt` 存在，mtime 為 2026-06-16，至今（2026-06-24）已超過 48 小時仍為 `pending` 狀態。

## 根因

cron-based sub-agent（`metacognitive-learner-24h`）執行 `post_delivery.py --write` 時：
1. `post_delivery.py` 分析 session tool_call 分佈
2. 生成的「標準評分邀請」寫入 `pending/<session_id>.txt`
3. 但 sub-agent **沒有 Telegram send 能力**，無法主動交付給使用者
4. 若 main session（telegram user 觸發）不主動檢查 `pending/`，entry 就會永久 pending

這不是「忘記執行」的問題，是**單向寫入、无人讀取**的架構性陷阱。

## 驗證命令

```bash
# 檢查是否有長期 pending 的 entry
find ~/.hermes/skill-usage/pending/ -name "*.txt" -mtime +1 -exec ls -la {} \;

# 正常狀態：pending/ 應該恆為空
ls ~/.hermes/skill-usage/pending/
```

## 修復方向

main session 啟動時自動檢查並交付所有 pending 邀請（需要 Hermes main session 實作，cron 無法替代）。

## If→Then

**If** `pending/` 有任何 `.txt` 檔且 mtime 超過 24 小時
**Then** 這幾乎可以確定是架構性空轉——立却在下次 main session 補發，並在 skill 文件記錄此限制
